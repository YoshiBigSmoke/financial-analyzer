"""
Modelo GARCH(1,1) para forecasting de volatilidad.

¿Por qué GARCH en finanzas?
  Los retornos financieros exhiben "volatility clustering":
  períodos de alta volatilidad tienden a seguirse de alta volatilidad
  y viceversa. ARIMA asume varianza constante; GARCH la modela dinámicamente.

  Usado en: desks de opciones, risk management (VaR), margin calculations.

Modelo:
  r_t = μ + ε_t
  ε_t = σ_t * z_t,  z_t ~ N(0,1)
  σ²_t = ω + α * ε²_{t-1} + β * σ²_{t-1}

  Donde:
    ω (omega) : varianza base incondicional
    α (alpha) : peso del shock pasado
    β (beta)  : persistencia de la volatilidad
    α + β < 1 → proceso estacionario (se revierte a la media)
"""

import numpy as np
import polars as pl
from arch import arch_model


def _log_returns(prices: pl.Series) -> np.ndarray:
    """Log retornos diarios: ln(P_t / P_{t-1}) * 100 (en % para estabilidad numérica)."""
    arr = prices.cast(pl.Float64).to_numpy()
    return np.diff(np.log(arr)) * 100


def fit_garch(
    prices: pl.Series,
    p: int = 1,
    q: int = 1,
    dist: str = "studentst",  # 't' captura colas pesadas (más realista que Normal)
) -> dict:
    """
    Ajusta un modelo GARCH(p,q) a los precios y devuelve el resultado.

    Parámetros:
        prices : serie de precios de cierre (adj_close)
        p      : orden del término ARCH (shocks pasados)
        q      : orden del término GARCH (varianza pasada)
        dist   : distribución de errores. 'studentst' > 'normal' en finanzas

    Devuelve dict con:
        model      : objeto fitted del arch
        returns    : log retornos usados
        params     : parámetros estimados (omega, alpha, beta, nu)
        persistence: alpha + beta (< 1 = estacionario)
        half_life  : días para que un shock se reduzca a la mitad
    """
    returns = _log_returns(prices)

    am = arch_model(returns, vol="Garch", p=p, q=q, dist=dist, rescale=False)
    res = am.fit(disp="off", show_warning=False)

    params = res.params
    alpha = params.get("alpha[1]", 0)
    beta  = params.get("beta[1]", 0)
    persistence = alpha + beta

    # Half-life: número de días para que la varianza regrese a la media
    half_life = np.log(0.5) / np.log(persistence) if 0 < persistence < 1 else np.inf

    return {
        "model":       res,
        "returns":     returns,
        "params":      dict(params),
        "persistence": round(persistence, 4),
        "half_life":   round(half_life, 1) if np.isfinite(half_life) else None,
        "aic":         round(res.aic, 2),
        "bic":         round(res.bic, 2),
    }


def forecast_volatility(garch_result: dict, horizon: int = 30) -> dict:
    """
    Genera forecast de volatilidad para los próximos `horizon` días.

    Devuelve dict con:
        daily_vol   : volatilidad diaria (%) por día
        annual_vol  : volatilidad anualizada (%) por día
        avg_daily   : promedio de vol diaria en el horizonte
        avg_annual  : promedio de vol anualizada en el horizonte
    """
    res = garch_result["model"]
    fc  = res.forecast(horizon=horizon, reindex=False)

    # variance forecast → desviación estándar
    var_forecast = fc.variance.values[-1]          # shape: (horizon,)
    daily_vol    = np.sqrt(var_forecast)           # en % (porque retornos en %)
    annual_vol   = daily_vol * np.sqrt(252)        # anualizar

    return {
        "horizon":    horizon,
        "daily_vol":  daily_vol.tolist(),
        "annual_vol": annual_vol.tolist(),
        "avg_daily":  round(float(daily_vol.mean()), 4),
        "avg_annual": round(float(annual_vol.mean()), 4),
    }
