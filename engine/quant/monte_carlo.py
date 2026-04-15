"""
Monte Carlo con Geometric Brownian Motion (GBM) + volatilidad GARCH.

¿Por qué GBM?
  Modelo estándar de precios en finanzas cuantitativas desde Black-Scholes (1973).
  Asume que los retornos log-normales son independientes e idénticamente distribuidos.
  Con GARCH le inyectamos volatilidad dinámica en lugar de constante.

  dS = μ·S·dt + σ·S·dW
  S(t+1) = S(t) · exp((μ - σ²/2)·dt + σ·√dt·Z),  Z ~ N(0,1)

Uso en la industria:
  - Value at Risk (VaR): percentil 5% de la distribución de precios futuros
  - Conditional VaR (CVaR / Expected Shortfall): pérdida esperada más allá del VaR
  - Pricing de opciones europeas
  - Stress testing
  - Generación de escenarios para portafolios
"""

import numpy as np
import polars as pl
from scipy import stats


def run_monte_carlo(
    current_price: float,
    daily_vol_pct: float,      # volatilidad diaria en % (de GARCH forecast)
    horizon: int = 30,         # días hacia adelante
    simulations: int = 10_000, # número de trayectorias
    drift: float | None = None, # μ diario en %; None → usa retorno histórico
    returns: np.ndarray | None = None,  # retornos históricos para calcular drift
    seed: int | None = 42,
) -> dict:
    """
    Simula `simulations` trayectorias de precio usando GBM.

    Parámetros:
        current_price : precio actual (S0)
        daily_vol_pct : volatilidad diaria en % (output de GARCH)
        horizon       : días a simular
        simulations   : número de paths
        drift         : retorno diario esperado en % (None = usa histórico)
        returns       : array de retornos históricos para calcular drift
        seed          : semilla para reproducibilidad

    Devuelve:
        {
          "paths"          : ndarray (simulations x horizon) — todas las trayectorias
          "final_prices"   : ndarray (simulations,) — precio final de cada path
          "expected_price" : float — mediana de precios finales
          "mean_price"     : float — media de precios finales
          "var_5"          : float — Value at Risk 5% (peor 5% de escenarios)
          "var_1"          : float — Value at Risk 1%
          "cvar_5"         : float — Expected Shortfall 5%
          "percentiles"    : dict — percentiles clave de la distribución final
          "prob_above"     : float — probabilidad de terminar sobre el precio actual
          "prob_below"     : float — probabilidad de terminar bajo el precio actual
        }
    """
    rng = np.random.default_rng(seed)

    # Drift: retorno diario esperado en %
    if drift is None:
        if returns is not None and len(returns) > 0:
            mu = float(np.mean(returns))   # promedio histórico en %
        else:
            mu = 0.0
    else:
        mu = drift

    # Pasar de % a decimal para GBM
    sigma = daily_vol_pct / 100
    mu_dec = mu / 100

    dt = 1  # paso diario

    # Generar shocks aleatorios: shape (simulations, horizon)
    Z = rng.standard_normal((simulations, horizon))

    # GBM: retornos logarítmicos
    log_returns = (mu_dec - 0.5 * sigma**2) * dt + sigma * np.sqrt(dt) * Z

    # Trayectorias de precio acumuladas
    price_paths = current_price * np.exp(np.cumsum(log_returns, axis=1))

    # Precio al final del horizonte
    final_prices = price_paths[:, -1]

    # ── Métricas de riesgo ────────────────────────────────────────────────
    var_5  = float(np.percentile(final_prices, 5))
    var_1  = float(np.percentile(final_prices, 1))
    cvar_5 = float(final_prices[final_prices <= var_5].mean()) if (final_prices <= var_5).any() else var_5

    pct_keys = [1, 5, 10, 25, 50, 75, 90, 95, 99]
    percentiles = {p: round(float(np.percentile(final_prices, p)), 2) for p in pct_keys}

    prob_above = float((final_prices > current_price).mean())
    prob_below = 1.0 - prob_above

    return {
        "paths":           price_paths,
        "final_prices":    final_prices,
        "current_price":   current_price,
        "horizon":         horizon,
        "simulations":     simulations,
        "expected_price":  round(float(np.median(final_prices)), 2),
        "mean_price":      round(float(np.mean(final_prices)), 2),
        "std_price":       round(float(np.std(final_prices)), 2),
        "var_5":           round(var_5, 2),
        "var_1":           round(var_1, 2),
        "cvar_5":          round(cvar_5, 2),
        "percentiles":     percentiles,
        "prob_above":      round(prob_above, 4),
        "prob_below":      round(prob_below, 4),
        "daily_vol_pct":   daily_vol_pct,
        "drift_pct":       mu,
    }


def price_cone(mc_result: dict) -> dict:
    """
    Extrae el 'cono de precios' día a día: rango de percentiles por sesión.
    Útil para graficar en la UI.

    Devuelve dict con listas de longitud `horizon`:
        p5, p25, p50, p75, p95
    """
    paths = mc_result["paths"]   # (simulations, horizon)
    return {
        "p5":  np.percentile(paths, 5,  axis=0).round(2).tolist(),
        "p25": np.percentile(paths, 25, axis=0).round(2).tolist(),
        "p50": np.percentile(paths, 50, axis=0).round(2).tolist(),
        "p75": np.percentile(paths, 75, axis=0).round(2).tolist(),
        "p95": np.percentile(paths, 95, axis=0).round(2).tolist(),
    }
