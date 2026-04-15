"""
Queries reutilizables para cada tabla.
Todas reciben la conexión como parámetro para no depender del singleton directamente.
"""

import duckdb
import polars as pl
from datetime import date


# ── Companies ──────────────────────────────────────────────────────────────

def upsert_company(conn: duckdb.DuckDBPyConnection, data: dict) -> None:
    conn.execute("""
        INSERT INTO companies (ticker, name, sector, industry, country, exchange, currency, market_cap, description)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT (ticker) DO UPDATE SET
            name        = excluded.name,
            sector      = excluded.sector,
            industry    = excluded.industry,
            country     = excluded.country,
            exchange    = excluded.exchange,
            currency    = excluded.currency,
            market_cap  = excluded.market_cap,
            description = excluded.description,
            updated_at  = now()
    """, [
        data.get("ticker"), data.get("name"), data.get("sector"),
        data.get("industry"), data.get("country"), data.get("exchange"),
        data.get("currency", "USD"), data.get("market_cap"), data.get("description"),
    ])


def get_company(conn: duckdb.DuckDBPyConnection, ticker: str) -> dict | None:
    row = conn.execute("SELECT * FROM companies WHERE ticker = ?", [ticker]).fetchone()
    if row is None:
        return None
    cols = [d[0] for d in conn.description]
    return dict(zip(cols, row))


# ── Prices ─────────────────────────────────────────────────────────────────

def insert_prices(conn: duckdb.DuckDBPyConnection, df: pl.DataFrame) -> None:
    """
    Inserta un DataFrame de Polars con columnas:
    ticker, date, open, high, low, close, adj_close, volume
    Ignora duplicados (ticker, date).
    """
    conn.execute("""
        INSERT INTO prices SELECT * FROM df
        ON CONFLICT (ticker, date) DO NOTHING
    """)


def get_prices(
    conn: duckdb.DuckDBPyConnection,
    ticker: str,
    start: date | None = None,
    end: date | None = None,
) -> pl.DataFrame:
    query = "SELECT * FROM prices WHERE ticker = ?"
    params: list = [ticker]
    if start:
        query += " AND date >= ?"
        params.append(start)
    if end:
        query += " AND date <= ?"
        params.append(end)
    query += " ORDER BY date ASC"
    return conn.execute(query, params).pl()


# ── Financials ─────────────────────────────────────────────────────────────

def upsert_income_statement(conn: duckdb.DuckDBPyConnection, data: dict) -> None:
    conn.execute("""
        INSERT INTO income_statement
            (ticker, period_end, period_type, revenue, gross_profit, operating_income,
             net_income, ebitda, eps_basic, eps_diluted, shares_outstanding)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT (ticker, period_end, period_type) DO UPDATE SET
            revenue             = excluded.revenue,
            gross_profit        = excluded.gross_profit,
            operating_income    = excluded.operating_income,
            net_income          = excluded.net_income,
            ebitda              = excluded.ebitda,
            eps_basic           = excluded.eps_basic,
            eps_diluted         = excluded.eps_diluted,
            shares_outstanding  = excluded.shares_outstanding,
            updated_at          = now()
    """, [
        data["ticker"], data["period_end"], data["period_type"],
        data.get("revenue"), data.get("gross_profit"), data.get("operating_income"),
        data.get("net_income"), data.get("ebitda"), data.get("eps_basic"),
        data.get("eps_diluted"), data.get("shares_outstanding"),
    ])


def upsert_balance_sheet(conn: duckdb.DuckDBPyConnection, data: dict) -> None:
    conn.execute("""
        INSERT INTO balance_sheet
            (ticker, period_end, period_type, total_assets, total_liabilities, total_equity,
             cash_and_equivalents, total_debt, long_term_debt, current_assets, current_liabilities)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT (ticker, period_end, period_type) DO UPDATE SET
            total_assets            = excluded.total_assets,
            total_liabilities       = excluded.total_liabilities,
            total_equity            = excluded.total_equity,
            cash_and_equivalents    = excluded.cash_and_equivalents,
            total_debt              = excluded.total_debt,
            long_term_debt          = excluded.long_term_debt,
            current_assets          = excluded.current_assets,
            current_liabilities     = excluded.current_liabilities,
            updated_at              = now()
    """, [
        data["ticker"], data["period_end"], data["period_type"],
        data.get("total_assets"), data.get("total_liabilities"), data.get("total_equity"),
        data.get("cash_and_equivalents"), data.get("total_debt"), data.get("long_term_debt"),
        data.get("current_assets"), data.get("current_liabilities"),
    ])


def upsert_cash_flow(conn: duckdb.DuckDBPyConnection, data: dict) -> None:
    conn.execute("""
        INSERT INTO cash_flow
            (ticker, period_end, period_type, operating_cash_flow, investing_cash_flow,
             financing_cash_flow, free_cash_flow, capex, dividends_paid)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT (ticker, period_end, period_type) DO UPDATE SET
            operating_cash_flow     = excluded.operating_cash_flow,
            investing_cash_flow     = excluded.investing_cash_flow,
            financing_cash_flow     = excluded.financing_cash_flow,
            free_cash_flow          = excluded.free_cash_flow,
            capex                   = excluded.capex,
            dividends_paid          = excluded.dividends_paid,
            updated_at              = now()
    """, [
        data["ticker"], data["period_end"], data["period_type"],
        data.get("operating_cash_flow"), data.get("investing_cash_flow"),
        data.get("financing_cash_flow"), data.get("free_cash_flow"),
        data.get("capex"), data.get("dividends_paid"),
    ])


# ── Intrinsic Value ────────────────────────────────────────────────────────

def save_intrinsic_value(conn: duckdb.DuckDBPyConnection, data: dict) -> None:
    import json
    conn.execute("""
        INSERT INTO intrinsic_value
            (ticker, model_type, intrinsic_value, current_price, margin_of_safety, assumptions)
        VALUES (?, ?, ?, ?, ?, ?)
    """, [
        data["ticker"], data["model_type"], data["intrinsic_value"],
        data.get("current_price"), data.get("margin_of_safety"),
        json.dumps(data.get("assumptions", {})),
    ])


def get_latest_valuation(conn: duckdb.DuckDBPyConnection, ticker: str) -> dict | None:
    row = conn.execute("""
        SELECT * FROM intrinsic_value
        WHERE ticker = ?
        ORDER BY calculated_at DESC
        LIMIT 1
    """, [ticker]).fetchone()
    if row is None:
        return None
    cols = [d[0] for d in conn.description]
    return dict(zip(cols, row))


# ── Watchlist ──────────────────────────────────────────────────────────────

def add_to_watchlist(conn: duckdb.DuckDBPyConnection, ticker: str, notes: str = "") -> None:
    conn.execute("""
        INSERT INTO watchlist (ticker, notes)
        VALUES (?, ?)
        ON CONFLICT (ticker) DO UPDATE SET notes = excluded.notes
    """, [ticker, notes])


def get_watchlist(conn: duckdb.DuckDBPyConnection) -> list[dict]:
    rows = conn.execute("""
        SELECT w.ticker, c.name, c.sector, w.added_at, w.notes
        FROM watchlist w
        LEFT JOIN companies c ON c.ticker = w.ticker
        ORDER BY w.added_at DESC
    """).fetchall()
    cols = [d[0] for d in conn.description]
    return [dict(zip(cols, r)) for r in rows]
