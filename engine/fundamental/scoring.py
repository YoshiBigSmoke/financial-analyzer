import sys
"""
Sistema de scoring tipo Seeking Alpha.
Evalúa una empresa en 4 dimensiones y devuelve un score de 1 a 5 por cada una.

Dimensiones:
  - Valuación   : ¿está cara o barata vs sus propios históricos y el mercado?
  - Rentabilidad: ¿qué tan eficiente es generando utilidades?
  - Crecimiento : ¿crecen sus ingresos y FCF?
  - Salud financiera: ¿qué tan endeudada está?
"""

import duckdb


def _score_valuation(ratios: dict) -> tuple[float, list[str]]:
    """Score 1-5 basado en P/E, P/B, EV/EBITDA."""
    score = 3.0
    notes = []

    pe = ratios.get("pe_ratio")
    if pe is not None:
        if pe < 12:
            score += 1.0; notes.append("P/E bajo (<12): potencialmente subvaluada")
        elif pe < 20:
            score += 0.5; notes.append("P/E razonable (12-20)")
        elif pe > 35:
            score -= 1.0; notes.append("P/E alto (>35): puede estar sobrevaluada")
        elif pe > 50:
            score -= 1.5; notes.append("P/E muy alto (>50): cara")

    pb = ratios.get("pb_ratio")
    if pb is not None:
        if pb < 1.5:
            score += 0.5; notes.append("P/B bajo (<1.5): cotiza cerca del valor en libros")
        elif pb > 8:
            score -= 0.5; notes.append("P/B alto (>8)")

    ev_ebitda = ratios.get("ev_ebitda")
    if ev_ebitda is not None:
        if ev_ebitda < 8:
            score += 0.5; notes.append("EV/EBITDA bajo (<8)")
        elif ev_ebitda > 20:
            score -= 0.5; notes.append("EV/EBITDA alto (>20)")

    return round(max(1.0, min(5.0, score)), 1), notes


def _score_profitability(ratios: dict) -> tuple[float, list[str]]:
    """Score 1-5 basado en márgenes y ROE/ROA."""
    score = 3.0
    notes = []

    roe = ratios.get("roe")
    if roe is not None:
        if roe > 0.20:
            score += 1.0; notes.append(f"ROE excelente ({roe:.1%})")
        elif roe > 0.10:
            score += 0.5; notes.append(f"ROE bueno ({roe:.1%})")
        elif roe < 0:
            score -= 1.5; notes.append(f"ROE negativo ({roe:.1%})")

    net_margin = ratios.get("net_margin")
    if net_margin is not None:
        if net_margin > 0.20:
            score += 1.0; notes.append(f"Margen neto excelente ({net_margin:.1%})")
        elif net_margin > 0.10:
            score += 0.5; notes.append(f"Margen neto bueno ({net_margin:.1%})")
        elif net_margin < 0:
            score -= 1.0; notes.append(f"Margen neto negativo ({net_margin:.1%})")

    op_margin = ratios.get("operating_margin")
    if op_margin is not None and op_margin > 0.15:
        score += 0.5; notes.append(f"Margen operativo sólido ({op_margin:.1%})")

    return round(max(1.0, min(5.0, score)), 1), notes


def _score_growth(conn: duckdb.DuckDBPyConnection, ticker: str) -> tuple[float, list[str]]:
    """Score 1-5 basado en crecimiento de revenue y FCF (últimos 3 años anuales)."""
    score = 3.0
    notes = []

    rows = conn.execute("""
        SELECT i.period_end, i.revenue, cf.free_cash_flow
        FROM income_statement i
        LEFT JOIN cash_flow cf
            ON i.ticker = cf.ticker AND i.period_end = cf.period_end AND i.period_type = cf.period_type
        WHERE i.ticker = ? AND i.period_type = 'annual' AND i.revenue IS NOT NULL
        ORDER BY i.period_end DESC LIMIT 4
    """, [ticker]).fetchall()

    if len(rows) >= 2:
        newest_rev = rows[0][1]
        oldest_rev = rows[-1][1]
        if oldest_rev and oldest_rev > 0:
            rev_growth = (newest_rev / oldest_rev) ** (1 / (len(rows) - 1)) - 1
            if rev_growth > 0.15:
                score += 1.0; notes.append(f"Crecimiento de ingresos fuerte ({rev_growth:.1%} CAGR)")
            elif rev_growth > 0.05:
                score += 0.5; notes.append(f"Crecimiento de ingresos moderado ({rev_growth:.1%} CAGR)")
            elif rev_growth < 0:
                score -= 1.0; notes.append(f"Ingresos en declive ({rev_growth:.1%} CAGR)")

    fcfs = [r[2] for r in rows if r[2] is not None and r[2] > 0]
    if len(fcfs) >= 2:
        fcf_growth = (fcfs[0] / fcfs[-1]) ** (1 / (len(fcfs) - 1)) - 1
        if fcf_growth > 0.10:
            score += 0.5; notes.append(f"FCF creciendo ({fcf_growth:.1%} CAGR)")
        elif fcf_growth < 0:
            score -= 0.5; notes.append(f"FCF en declive ({fcf_growth:.1%} CAGR)")

    return round(max(1.0, min(5.0, score)), 1), notes


def _score_financial_health(ratios: dict) -> tuple[float, list[str]]:
    """Score 1-5 basado en deuda y liquidez."""
    score = 3.0
    notes = []

    d2e = ratios.get("debt_to_equity")
    if d2e is not None:
        if d2e < 0.3:
            score += 1.0; notes.append(f"Deuda muy baja (D/E {d2e:.2f})")
        elif d2e < 1.0:
            score += 0.5; notes.append(f"Deuda manejable (D/E {d2e:.2f})")
        elif d2e > 2.0:
            score -= 1.0; notes.append(f"Deuda alta (D/E {d2e:.2f})")
        elif d2e > 4.0:
            score -= 1.5; notes.append(f"Deuda muy alta (D/E {d2e:.2f})")

    cr = ratios.get("current_ratio")
    if cr is not None:
        if cr >= 2.0:
            score += 0.5; notes.append(f"Liquidez sólida (current ratio {cr:.2f})")
        elif cr < 1.0:
            score -= 1.0; notes.append(f"Liquidez baja (current ratio {cr:.2f})")

    return round(max(1.0, min(5.0, score)), 1), notes


def run_scoring(
    conn: duckdb.DuckDBPyConnection,
    ticker: str,
    period_type: str = "annual",
) -> dict | None:
    """
    Evalúa la empresa en 4 dimensiones y devuelve un reporte de scoring.

    Devuelve:
        {
          "ticker": ...,
          "overall": float (promedio 1-5),
          "valuation":    {"score": float, "notes": [str]},
          "profitability": {...},
          "growth":        {...},
          "health":        {...},
        }
    """
    ticker = ticker.upper()

    row = conn.execute("""
        SELECT pe_ratio, pb_ratio, ps_ratio, ev_ebitda,
               roe, roa, gross_margin, operating_margin, net_margin,
               debt_to_equity, current_ratio, quick_ratio
        FROM financial_ratios
        WHERE ticker = ? AND period_type = ?
        ORDER BY period_end DESC LIMIT 1
    """, [ticker, period_type]).fetchone()

    if not row:
        print(f"[{ticker}] Scoring: sin ratios calculados. Corre calculate_and_save_ratios() primero.", file=sys.stderr, flush=True)
        return None

    cols = [
        "pe_ratio", "pb_ratio", "ps_ratio", "ev_ebitda",
        "roe", "roa", "gross_margin", "operating_margin", "net_margin",
        "debt_to_equity", "current_ratio", "quick_ratio",
    ]
    ratios = dict(zip(cols, row))

    s_val,    n_val    = _score_valuation(ratios)
    s_prof,   n_prof   = _score_profitability(ratios)
    s_growth, n_growth = _score_growth(conn, ticker)
    s_health, n_health = _score_financial_health(ratios)

    overall = round((s_val + s_prof + s_growth + s_health) / 4, 2)

    return {
        "ticker":  ticker,
        "overall": overall,
        "valuation":     {"score": s_val,    "notes": n_val},
        "profitability": {"score": s_prof,   "notes": n_prof},
        "growth":        {"score": s_growth, "notes": n_growth},
        "health":        {"score": s_health, "notes": n_health},
    }
