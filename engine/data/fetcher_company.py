"""
Fetcher: información base de la empresa y estados financieros.
Fuente: yfinance
"""

import yfinance as yf
import polars as pl
from datetime import date
from engine.data.yf_session import get_session


def _ticker(symbol: str):
    """Crea un yf.Ticker con la sesión compartida."""
    session = get_session()
    return yf.Ticker(symbol, session=session) if session else yf.Ticker(symbol)

# ── Mapeos yfinance → schema ───────────────────────────────────────────────

_INCOME_MAP = {
    "Total Revenue":          "revenue",
    "Gross Profit":           "gross_profit",
    "Operating Income":       "operating_income",
    "Net Income":             "net_income",
    "EBITDA":                 "ebitda",
    "Basic EPS":              "eps_basic",
    "Diluted EPS":            "eps_diluted",
    "Basic Average Shares":   "shares_outstanding",
}

_BALANCE_MAP = {
    "Total Assets":                         "total_assets",
    "Total Liabilities Net Minority Interest": "total_liabilities",
    "Stockholders Equity":                  "total_equity",
    "Cash And Cash Equivalents":            "cash_and_equivalents",
    "Total Debt":                           "total_debt",
    "Long Term Debt":                       "long_term_debt",
    "Current Assets":                       "current_assets",
    "Current Liabilities":                  "current_liabilities",
}

_CASHFLOW_MAP = {
    "Operating Cash Flow":      "operating_cash_flow",
    "Investing Cash Flow":      "investing_cash_flow",
    "Financing Cash Flow":      "financing_cash_flow",
    "Free Cash Flow":           "free_cash_flow",
    "Capital Expenditure":      "capex",
    "Common Stock Dividend Paid": "dividends_paid",
}


def _safe(value):
    """Convierte NaN / None a None para evitar problemas en DuckDB."""
    try:
        import math
        if value is None or math.isnan(float(value)):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _extract_period(df, field_map: dict, ticker: str, period_type: str) -> list[dict]:
    """
    Convierte un DataFrame de yfinance (filas=campos, columnas=fechas)
    a lista de dicts listos para insertar en el schema.
    """
    rows = []
    for col in df.columns:
        period_end = col.date() if hasattr(col, "date") else col
        row = {"ticker": ticker, "period_end": period_end, "period_type": period_type}
        for yf_name, schema_name in field_map.items():
            raw = df.loc[yf_name, col] if yf_name in df.index else None
            row[schema_name] = _safe(raw)
        rows.append(row)
    return rows


# ── Funciones públicas ─────────────────────────────────────────────────────

def fetch_company_info(ticker: str) -> dict:
    """
    Devuelve info base de la empresa lista para upsert_company().
    """
    info = _ticker(ticker).info
    return {
        "ticker":      ticker.upper(),
        "name":        info.get("shortName") or info.get("longName"),
        "sector":      info.get("sector"),
        "industry":    info.get("industry"),
        "country":     info.get("country"),
        "exchange":    info.get("exchange"),
        "currency":    info.get("currency", "USD"),
        "market_cap":  _safe(info.get("marketCap")),
        "description": info.get("longBusinessSummary"),
    }


def fetch_income_statement(ticker: str, quarterly: bool = False) -> list[dict]:
    """
    Devuelve lista de dicts para upsert_income_statement().
    quarterly=False → anual, quarterly=True → trimestral.
    """
    t = _ticker(ticker)
    df = t.quarterly_income_stmt if quarterly else t.income_stmt
    period_type = "quarterly" if quarterly else "annual"
    return _extract_period(df, _INCOME_MAP, ticker.upper(), period_type)


def fetch_balance_sheet(ticker: str, quarterly: bool = False) -> list[dict]:
    """
    Devuelve lista de dicts para upsert_balance_sheet().
    """
    t = _ticker(ticker)
    df = t.quarterly_balance_sheet if quarterly else t.balance_sheet
    period_type = "quarterly" if quarterly else "annual"
    return _extract_period(df, _BALANCE_MAP, ticker.upper(), period_type)


def fetch_cash_flow(ticker: str, quarterly: bool = False) -> list[dict]:
    """
    Devuelve lista de dicts para upsert_cash_flow().
    """
    t = _ticker(ticker)
    df = t.quarterly_cashflow if quarterly else t.cashflow
    period_type = "quarterly" if quarterly else "annual"
    return _extract_period(df, _CASHFLOW_MAP, ticker.upper(), period_type)
