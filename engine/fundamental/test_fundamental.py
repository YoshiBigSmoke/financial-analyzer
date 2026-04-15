"""
Prueba del módulo fundamental completo.
Requiere que AAPL ya esté cargada en DuckDB (correr test_data.py antes).
Correr desde la raíz: python -m engine.fundamental.test_fundamental
"""

import json
from engine.db.connection import get_connection, close_connection
from engine.fundamental.ratios import calculate_and_save_ratios
from engine.fundamental.dcf import run_dcf
from engine.fundamental.scoring import run_scoring


def fmt(val, pct=False, dollar=False):
    if val is None:
        return "N/A"
    if dollar:
        return f"${val:,.2f}"
    if pct:
        return f"{val:.2%}"
    return f"{val:.2f}"


def main():
    conn = get_connection()
    ticker = "AAPL"

    # ── Ratios ────────────────────────────────────────────────────────────
    print(f"\n{'─'*50}")
    print(f"  RATIOS FINANCIEROS — {ticker}")
    print(f"{'─'*50}")
    ratios = calculate_and_save_ratios(conn, ticker)

    if ratios:
        print(f"  Período        : {ratios['period_end']} ({ratios['period_type']})")
        print(f"\n  Valuación")
        print(f"    P/E          : {fmt(ratios['pe_ratio'])}")
        print(f"    P/B          : {fmt(ratios['pb_ratio'])}")
        print(f"    P/S          : {fmt(ratios['ps_ratio'])}")
        print(f"    EV/EBITDA    : {fmt(ratios['ev_ebitda'])}")
        print(f"\n  Rentabilidad")
        print(f"    ROE          : {fmt(ratios['roe'], pct=True)}")
        print(f"    ROA          : {fmt(ratios['roa'], pct=True)}")
        print(f"    Margen bruto : {fmt(ratios['gross_margin'], pct=True)}")
        print(f"    Margen op.   : {fmt(ratios['operating_margin'], pct=True)}")
        print(f"    Margen neto  : {fmt(ratios['net_margin'], pct=True)}")
        print(f"\n  Deuda / Liquidez")
        print(f"    D/E          : {fmt(ratios['debt_to_equity'])}")
        print(f"    Current ratio: {fmt(ratios['current_ratio'])}")

    # ── DCF ───────────────────────────────────────────────────────────────
    print(f"\n{'─'*50}")
    print(f"  DCF — {ticker}")
    print(f"{'─'*50}")
    dcf = run_dcf(conn, ticker, discount_rate=0.10, terminal_growth=0.03, years=10)

    if dcf:
        a = dcf["assumptions"]
        print(f"  FCF histórico  : {[f'${v/1e9:.1f}B' for v in a['fcf_history']]}")
        print(f"  Tasa crecim.   : {a['growth_rate']:.2%}")
        print(f"  Tasa descuento : {a['discount_rate']:.2%}")
        print(f"  Crec. terminal : {a['terminal_growth']:.2%}")
        print(f"\n  Valor intrínseco: {fmt(dcf['intrinsic_value'], dollar=True)}")
        print(f"  Precio actual   : {fmt(dcf['current_price'], dollar=True)}")
        mos = dcf["margin_of_safety"]
        if mos is not None:
            label = "DESCUENTO" if mos > 0 else "PRIMA"
            print(f"  Margen seguridad: {mos:.2%} ({label})")

    # ── Scoring ───────────────────────────────────────────────────────────
    print(f"\n{'─'*50}")
    print(f"  SCORING — {ticker}")
    print(f"{'─'*50}")
    score = run_scoring(conn, ticker)

    if score:
        print(f"  Overall: {score['overall']} / 5.0\n")
        for dim in ["valuation", "profitability", "growth", "health"]:
            d = score[dim]
            print(f"  {dim.capitalize():15s}: {d['score']}/5")
            for note in d["notes"]:
                print(f"    · {note}")

    print()
    close_connection()


if __name__ == "__main__":
    main()
