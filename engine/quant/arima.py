"""
Modelo ARIMA para forecasting de retornos.

¿Por qué ARIMA en finanzas?
  ARIMA (AutoRegressive Integrated Moving Average) captura autocorrelación
  en series de tiempo. En retornos financieros su poder predictivo es limitado
  (mercados eficientes), pero sirve como:
    - Baseline de comparación para otros modelos
    - Detección de autocorrelación residual (diagnóstico)
    - Forecasting de series macroeconómicas más predecibles

  Se usa con auto-selección de parámetros (p,d,q) vía criterio de información AIC.

Nota: los precios son no-estacionarios (tienen raíz unitaria).
  ARIMA trabaja sobre los RETORNOS (diferencia de log-precios), no los precios.
  El forecast de retorno luego se convierte a precio proyectado.
"""

import numpy as np
import polars as pl
import warnings
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.stattools import adfuller
from itertools import product


def _log_returns(prices: pl.Series) -> np.ndarray:
    arr = prices.cast(pl.Float64).to_numpy()
    return np.diff(np.log(arr)) * 100


def adf_test(returns: np.ndarray) -> dict:
    """
    Test de Dickey-Fuller aumentado: verifica estacionariedad.
    p-value < 0.05 → estacionaria (rechaza raíz unitaria) → ARIMA válido.
    """
    result = adfuller(returns, autolag="AIC")
    return {
        "statistic": round(result[0], 4),
        "p_value":   round(result[1], 4),
        "stationary": result[1] < 0.05,
    }


def _select_order(returns: np.ndarray, max_p: int = 3, max_q: int = 3) -> tuple[int, int]:
    """
    Selecciona (p, q) óptimos minimizando AIC.
    d=0 porque ya estamos en retornos (estacionarios).
    """
    best_aic = np.inf
    best_order = (1, 0, 1)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for p, q in product(range(max_p + 1), range(max_q + 1)):
            if p == 0 and q == 0:
                continue
            try:
                m = ARIMA(returns, order=(p, 0, q)).fit()
                if m.aic < best_aic:
                    best_aic   = m.aic
                    best_order = (p, 0, q)
            except Exception:
                continue

    return best_order


def fit_arima(
    prices: pl.Series,
    order: tuple[int, int, int] | None = None,
    auto: bool = True,
) -> dict:
    """
    Ajusta ARIMA a los log-retornos.

    Parámetros:
        prices : serie de precios de cierre
        order  : (p, d, q) manual. Si None y auto=True, se selecciona por AIC
        auto   : seleccionar orden automáticamente

    Devuelve dict con el modelo ajustado y métricas.
    """
    returns = _log_returns(prices)

    adf = adf_test(returns)

    if order is None:
        if auto:
            order = _select_order(returns)
        else:
            order = (1, 0, 1)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        model = ARIMA(returns, order=order).fit()

    return {
        "model":     model,
        "returns":   returns,
        "order":     order,
        "aic":       round(model.aic, 2),
        "bic":       round(model.bic, 2),
        "adf":       adf,
    }


def forecast_returns(arima_result: dict, horizon: int = 10) -> dict:
    """
    Genera forecast de retornos para `horizon` días.
    Convierte los retornos proyectados a precios usando el último precio conocido.

    Devuelve:
        {
          "forecast_returns" : list[float]  — retorno diario en %
          "forecast_cum"     : list[float]  — retorno acumulado en %
          "conf_int_lower"   : list[float]  — intervalo de confianza 95% inferior
          "conf_int_upper"   : list[float]  — intervalo de confianza 95% superior
        }
    """
    model = arima_result["model"]

    fc = model.get_forecast(steps=horizon)
    mean_ret  = fc.predicted_mean.tolist()
    conf = fc.conf_int(alpha=0.05)
    if hasattr(conf, "iloc"):
        lower_ret = conf.iloc[:, 0].tolist()
        upper_ret = conf.iloc[:, 1].tolist()
    else:
        lower_ret = conf[:, 0].tolist()
        upper_ret = conf[:, 1].tolist()

    # Retorno acumulado
    cum = np.cumsum(mean_ret).tolist()

    return {
        "horizon":          horizon,
        "forecast_returns": [round(r, 4) for r in mean_ret],
        "forecast_cum":     [round(c, 4) for c in cum],
        "conf_int_lower":   [round(r, 4) for r in lower_ret],
        "conf_int_upper":   [round(r, 4) for r in upper_ret],
        "order":            arima_result["order"],
        "aic":              arima_result["aic"],
    }


def returns_to_prices(
    current_price: float,
    forecast_returns_pct: list[float],
    lower_pct: list[float],
    upper_pct: list[float],
) -> dict:
    """
    Convierte forecast de retornos (en %) a precios proyectados.
    Usa GBM: P(t+n) = P(t) * exp(sum(r_i / 100))
    """
    def _proj(rets):
        prices = []
        p = current_price
        for r in rets:
            p = p * np.exp(r / 100)
            prices.append(round(p, 2))
        return prices

    return {
        "prices":       _proj(forecast_returns_pct),
        "prices_lower": _proj(lower_pct),
        "prices_upper": _proj(upper_pct),
    }
