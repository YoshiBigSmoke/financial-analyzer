import sys
"""
Cálculo de ratios financieros a partir de datos en DuckDB.
Guarda los resultados en la tabla financial_ratios.
"""

import duckdb


def _safe_div(a, b):
    """División segura: devuelve None si b es 0 o None."""
    try:
        if a is None or b is None or b == 0:
            return None
        return a / b
    except (TypeError, ZeroDivisionError):
        return None


def _get_latest_price(conn: duckdb.DuckDBPyConnection, ticker: str) -> float | None:
    row = conn.execute("""
        SELECT adj_close FROM prices
        WHERE ticker = ? ORDER BY date DESC LIMIT 1
    """, [ticker]).fetchone()
    return row[0] if row else None


def _get_latest_financials(
    conn: duckdb.DuckDBPyConnection,
    ticker: str,
    period_type: str = "annual",
) -> dict | None:
    """
    Devuelve los datos financieros más recientes combinados
    de las tres tablas (income, balance, cashflow).
    """
    row = conn.execute("""
        SELECT
            i.period_end, i.period_type,
            i.revenue, i.gross_profit, i.operating_income,
            i.net_income, i.ebitda, i.eps_diluted, i.shares_outstanding,
            b.total_assets, b.total_liabilities, b.total_equity,
            b.cash_and_equivalents, b.total_debt, b.current_assets, b.current_liabilities,
            cf.free_cash_flow
        FROM income_statement i
        JOIN balance_sheet b
            ON i.ticker = b.ticker
            AND i.period_end = b.period_end
            AND i.period_type = b.period_type
        LEFT JOIN cash_flow cf
            ON i.ticker = cf.ticker
            AND i.period_end = cf.period_end
            AND i.period_type = cf.period_type
        WHERE i.ticker = ? AND i.period_type = ?
        ORDER BY i.period_end DESC
        LIMIT 1
    """, [ticker, period_type]).fetchone()

    if not row:
        return None

    cols = [
        "period_end", "period_type",
        "revenue", "gross_profit", "operating_income",
        "net_income", "ebitda", "eps_diluted", "shares_outstanding",
        "total_assets", "total_liabilities", "total_equity",
        "cash_and_equivalents", "total_debt", "current_assets", "current_liabilities",
        "free_cash_flow",
    ]
    return dict(zip(cols, row))


def calculate_and_save_ratios(
    conn: duckdb.DuckDBPyConnection,
    ticker: str,
    period_type: str = "annual",
) -> dict | None:
    """
    Calcula todos los ratios financieros para el período más reciente
    y los guarda en la tabla financial_ratios.

    Devuelve el dict de ratios calculados, o None si no hay datos.
    """
    ticker = ticker.upper()
    price = _get_latest_price(conn, ticker)
    fin = _get_latest_financials(conn, ticker, period_type)

    if not fin:
        print(f"[{ticker}] Sin datos financieros para calcular ratios.", file=sys.stderr, flush=True)
        return None

    market_cap = (price * fin["shares_outstanding"]) if (price and fin["shares_outstanding"]) else None

    # Enterprise Value = market_cap + total_debt - cash
    ev = None
    if market_cap is not None and fin["total_debt"] is not None and fin["cash_and_equivalents"] is not None:
        ev = market_cap + fin["total_debt"] - fin["cash_and_equivalents"]

    # Book Value per share
    bvps = _safe_div(fin["total_equity"], fin["shares_outstanding"])

    ratios = {
        "ticker":           ticker,
        "period_end":       fin["period_end"],
        "period_type":      fin["period_type"],
        # ── Valuación ──────────────────────────────────────
        "pe_ratio":         _safe_div(price, fin["eps_diluted"]),
        "pb_ratio":         _safe_div(price, bvps),
        "ps_ratio":         _safe_div(market_cap, fin["revenue"]),
        "ev_ebitda":        _safe_div(ev, fin["ebitda"]),
        # ── Rentabilidad ───────────────────────────────────
        "roe":              _safe_div(fin["net_income"], fin["total_equity"]),
        "roa":              _safe_div(fin["net_income"], fin["total_assets"]),
        "gross_margin":     _safe_div(fin["gross_profit"], fin["revenue"]),
        "operating_margin": _safe_div(fin["operating_income"], fin["revenue"]),
        "net_margin":       _safe_div(fin["net_income"], fin["revenue"]),
        # ── Deuda y liquidez ───────────────────────────────
        "debt_to_equity":   _safe_div(fin["total_debt"], fin["total_equity"]),
        "current_ratio":    _safe_div(fin["current_assets"], fin["current_liabilities"]),
        "quick_ratio":      _safe_div(fin["current_assets"], fin["current_liabilities"]),  # approx sin inventario
    }

    conn.execute("""
        INSERT INTO financial_ratios (
            ticker, period_end, period_type,
            pe_ratio, pb_ratio, ps_ratio, ev_ebitda,
            roe, roa, gross_margin, operating_margin, net_margin,
            debt_to_equity, current_ratio, quick_ratio
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT (ticker, period_end, period_type) DO UPDATE SET
            pe_ratio         = excluded.pe_ratio,
            pb_ratio         = excluded.pb_ratio,
            ps_ratio         = excluded.ps_ratio,
            ev_ebitda        = excluded.ev_ebitda,
            roe              = excluded.roe,
            roa              = excluded.roa,
            gross_margin     = excluded.gross_margin,
            operating_margin = excluded.operating_margin,
            net_margin       = excluded.net_margin,
            debt_to_equity   = excluded.debt_to_equity,
            current_ratio    = excluded.current_ratio,
            quick_ratio      = excluded.quick_ratio,
            updated_at       = now()
    """, [
        ratios["ticker"], ratios["period_end"], ratios["period_type"],
        ratios["pe_ratio"], ratios["pb_ratio"], ratios["ps_ratio"], ratios["ev_ebitda"],
        ratios["roe"], ratios["roa"], ratios["gross_margin"], ratios["operating_margin"], ratios["net_margin"],
        ratios["debt_to_equity"], ratios["current_ratio"], ratios["quick_ratio"],
    ])

    return ratios
