"""
Prueba del módulo quant completo.
Requiere AAPL cargada en DuckDB.
Correr desde la raíz: python -m engine.quant.test_quant
"""

from engine.db.connection import get_connection, close_connection
from engine.quant.forecast import run_forecast


def bar(prob: float, width: int = 30) -> str:
    filled = round(prob * width)
    return "█" * filled + "░" * (width - filled)


def main():
    conn = get_connection()
    result = run_forecast(conn, "AAPL", horizon=30, simulations=10_000)

    if not result:
        return

    ticker = result["ticker"]
    price  = result["current_price"]
    g      = result["garch"]
    mc     = result["monte_carlo"]
    arima  = result["arima"]
    cone   = result["cone"]

    print(f"\n{'═'*60}")
    print(f"  ANÁLISIS CUANTITATIVO — {ticker}  |  Precio actual: ${price:.2f}")
    print(f"  Horizonte: {result['horizon']} días")
    print(f"{'═'*60}")

    # ── GARCH ──────────────────────────────────────────────────────────────
    print(f"\n  GARCH(1,1)  [AIC: {g['aic']}]")
    print(f"  {'─'*54}")
    gp = g["params"]
    print(f"  ω (omega)      : {gp.get('omega', 0):.6f}  (varianza base)")
    print(f"  α (alpha)      : {gp.get('alpha[1]', 0):.4f}  (shock pasado)")
    print(f"  β (beta)       : {gp.get('beta[1]', 0):.4f}  (persistencia)")
    print(f"  α + β          : {g['persistence']:.4f}  (< 1 = estacionario)")
    if g["half_life"]:
        print(f"  Half-life vol  : {g['half_life']} días")
    fc = g["forecast"]
    print(f"\n  Volatilidad proyectada ({fc['horizon']}d):")
    print(f"    Diaria promedio   : {fc['avg_daily']:.3f}%")
    print(f"    Anualizada promedio: {fc['avg_annual']:.2f}%")

    # ── Monte Carlo ────────────────────────────────────────────────────────
    print(f"\n  MONTE CARLO GBM  [{mc['simulations']:,} simulaciones, {mc['horizon']}d]")
    print(f"  {'─'*54}")
    print(f"  Precio esperado (mediana) : ${mc['expected_price']:.2f}")
    print(f"  Precio medio              : ${mc['mean_price']:.2f}")
    print(f"  Desviación estándar       : ${mc['std_price']:.2f}")
    print()
    print(f"  Distribución de precios al día {mc['horizon']}:")
    for p, val in mc["percentiles"].items():
        label = f"  p{p:>2}  ${val:.2f}"
        print(label)
    print()
    print(f"  Value at Risk  5% (VaR)   : ${mc['var_5']:.2f}  (peor 5% de escenarios)")
    print(f"  Exp. Shortfall 5% (CVaR)  : ${mc['cvar_5']:.2f}  (pérdida esperada en ese 5%)")
    print()
    print(f"  P(precio > ${price:.2f})  : {mc['prob_above']:.1%}  {bar(mc['prob_above'])}")
    print(f"  P(precio < ${price:.2f})  : {mc['prob_below']:.1%}  {bar(mc['prob_below'])}")

    # ── ARIMA ──────────────────────────────────────────────────────────────
    print(f"\n  ARIMA{arima['order']}  [AIC: {arima['aic']}]")
    print(f"  {'─'*54}")
    adf = arima["adf"]
    estatus = "estacionaria" if adf["stationary"] else "no estacionaria"
    print(f"  ADF test: p-value={adf['p_value']:.4f} → serie {estatus}")
    prices_proj = arima["prices"]["prices"]
    lower_proj  = arima["prices"]["prices_lower"]
    upper_proj  = arima["prices"]["prices_upper"]
    days = [1, 5, 10, 20, 30]
    print(f"\n  Proyección de precios (ARIMA):")
    print(f"  {'Día':>5}  {'Precio':>10}  {'IC 95% inferior':>16}  {'IC 95% superior':>16}")
    print(f"  {'─'*54}")
    for d in days:
        idx = min(d - 1, len(prices_proj) - 1)
        print(f"  {d:>5}  ${prices_proj[idx]:>9.2f}  ${lower_proj[idx]:>15.2f}  ${upper_proj[idx]:>15.2f}")

    # ── Cono de precios (día 30) ───────────────────────────────────────────
    print(f"\n  CONO DE PRECIOS — Monte Carlo (día 30)")
    print(f"  {'─'*54}")
    print(f"  p5  (pesimista extremo) : ${cone['p5'][-1]:.2f}")
    print(f"  p25 (pesimista)         : ${cone['p25'][-1]:.2f}")
    print(f"  p50 (central / mediana) : ${cone['p50'][-1]:.2f}")
    print(f"  p75 (optimista)         : ${cone['p75'][-1]:.2f}")
    print(f"  p95 (optimista extremo) : ${cone['p95'][-1]:.2f}")
    print(f"\n{'═'*60}\n")

    close_connection()


if __name__ == "__main__":
    main()
