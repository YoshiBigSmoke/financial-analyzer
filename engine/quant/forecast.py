import sys
"""
Pipeline de forecasting cuantitativo.
Orquesta GARCH + Monte Carlo + ARIMA en un solo resultado.
"""

import duckdb
import polars as pl
from engine.db.queries import get_prices
from engine.quant.garch import fit_garch, forecast_volatility
from engine.quant.monte_carlo import run_monte_carlo, price_cone
from engine.quant.arima import fit_arima, forecast_returns, returns_to_prices


def run_forecast(
    conn: duckdb.DuckDBPyConnection,
    ticker: str,
    horizon: int = 30,
    simulations: int = 10_000,
) -> dict | None:
    """
    Ejecuta el análisis cuantitativo completo para un ticker.

    Parámetros:
        conn        : conexión DuckDB
        ticker      : símbolo bursátil
        horizon     : días a proyectar
        simulations : paths en Monte Carlo

    Devuelve:
        {
          "ticker"       : str,
          "current_price": float,
          "horizon"      : int,
          "garch"        : dict — parámetros y volatilidad proyectada,
          "monte_carlo"  : dict — distribución de precios futuros,
          "cone"         : dict — cono de precios día a día,
          "arima"        : dict — forecast de retornos y precios,
        }
    """
    ticker = ticker.upper()

    df = get_prices(conn, ticker)
    if df.is_empty():
        print(f"[{ticker}] Sin datos de precios.", file=sys.stderr, flush=True)
        return None

    prices = df["adj_close"]
    current_price = float(prices[-1])

    # ── GARCH ──────────────────────────────────────────────────────────────
    print(f"[{ticker}] Ajustando GARCH(1,1)...", file=sys.stderr, flush=True)
    garch_fit = fit_garch(prices)
    garch_fc  = forecast_volatility(garch_fit, horizon=horizon)

    # Volatilidad promedio proyectada (en %) para el Monte Carlo
    avg_vol = garch_fc["avg_daily"]

    # ── Monte Carlo ────────────────────────────────────────────────────────
    print(f"[{ticker}] Corriendo Monte Carlo ({simulations:,} simulaciones)...", file=sys.stderr, flush=True)
    mc = run_monte_carlo(
        current_price  = current_price,
        daily_vol_pct  = avg_vol,
        horizon        = horizon,
        simulations    = simulations,
        returns        = garch_fit["returns"],
    )
    cone = price_cone(mc)

    # ── ARIMA ──────────────────────────────────────────────────────────────
    print(f"[{ticker}] Ajustando ARIMA (selección automática)...", file=sys.stderr, flush=True)
    arima_fit = fit_arima(prices)
    arima_fc  = forecast_returns(arima_fit, horizon=horizon)
    arima_prices = returns_to_prices(
        current_price        = current_price,
        forecast_returns_pct = arima_fc["forecast_returns"],
        lower_pct            = arima_fc["conf_int_lower"],
        upper_pct            = arima_fc["conf_int_upper"],
    )

    # Remover arrays grandes que no son serializables fácilmente
    mc_clean = {k: v for k, v in mc.items() if k not in ("paths", "final_prices")}

    return {
        "ticker":        ticker,
        "current_price": current_price,
        "horizon":       horizon,
        "garch": {
            "params":      garch_fit["params"],
            "persistence": garch_fit["persistence"],
            "half_life":   garch_fit["half_life"],
            "aic":         garch_fit["aic"],
            "forecast":    garch_fc,
        },
        "monte_carlo": mc_clean,
        "cone":        cone,
        "arima": {
            "order":   arima_fc["order"],
            "aic":     arima_fc["aic"],
            "adf":     arima_fit["adf"],
            "returns": arima_fc,
            "prices":  arima_prices,
        },
    }
