"""
Prueba del módulo técnico completo.
Requiere AAPL cargada en DuckDB.
Correr desde la raíz: python -m engine.technical.test_technical
"""

from engine.db.connection import get_connection, close_connection
from engine.db.queries import get_prices
from engine.technical.signals import analyze, summary


def main():
    conn = get_connection()

    df = get_prices(conn, "AAPL")
    if df.is_empty():
        print("Sin datos de precios. Corre test_data.py primero.")
        return

    print(f"Analizando AAPL — {len(df)} sesiones de datos\n")

    signals = analyze(df)
    result  = summary(signals)

    # ── Señales individuales ───────────────────────────────────────────────
    icons = {"buy": "▲", "sell": "▼", "neutral": "●"}
    colors = {"buy": "\033[92m", "sell": "\033[91m", "neutral": "\033[93m"}
    reset = "\033[0m"

    print(f"{'─'*60}")
    print(f"  SEÑALES TÉCNICAS — AAPL")
    print(f"{'─'*60}")
    for s in signals:
        icon  = icons[s["signal"]]
        color = colors[s["signal"]]
        print(f"  {color}{icon} {s['indicator']:20s}{reset}  {s['note']}")

    # ── Consenso ──────────────────────────────────────────────────────────
    print(f"\n{'─'*60}")
    c = result["consensus"]
    color = colors[c]
    print(f"  CONSENSO: {color}{c.upper():8s}{reset}  "
          f"(score {result['score']:+.2f}  |  "
          f"▲{result['buy']} ▼{result['sell']} ●{result['neutral']})")
    print(f"{'─'*60}\n")

    close_connection()


if __name__ == "__main__":
    main()
