"""
Pipeline principal: descarga todo lo de un ticker y lo guarda en DuckDB.
Un solo punto de entrada para el engine.
"""

import sys
import time
import duckdb
from engine.data.fetcher_company import (
    fetch_company_info,
    fetch_income_statement,
    fetch_balance_sheet,
    fetch_cash_flow,
)
from engine.data.fetcher_prices import fetch_prices
from engine.db.queries import (
    upsert_company,
    insert_prices,
    upsert_income_statement,
    upsert_balance_sheet,
    upsert_cash_flow,
    get_prices,
)


def _log(msg: str) -> None:
    """Logs van a stderr para no contaminar el JSON que va a stdout."""
    print(msg, file=sys.stderr, flush=True)


def _retry(fn, retries: int = 3, delay: float = 8.0, label: str = ""):
    """
    Ejecuta fn() con reintentos automáticos si hay rate limit de Yahoo.
    """
    for attempt in range(retries):
        try:
            return fn()
        except Exception as e:
            msg = str(e).lower()
            is_rate_limit = "rate limit" in msg or "too many requests" in msg or "429" in msg
            if is_rate_limit and attempt < retries - 1:
                wait = delay * (attempt + 1)
                _log(f"[rate limit] {label} — reintentando en {wait:.0f}s...")
                time.sleep(wait)
                # Resetear sesión para forzar nuevas cookies
                from engine.data.yf_session import reset_session
                reset_session()
            else:
                raise


def _try_financials(conn, ticker: str) -> bool:
    """
    Intenta descargar estados financieros + company info.
    Devuelve True si tuvo éxito, False si falló (rate limit u otro).
    No lanza excepción — el pipeline siempre sigue.
    """
    try:
        _log(f"[{ticker}] Descargando info de empresa...")
        company = _retry(lambda: fetch_company_info(ticker), retries=2, delay=5, label="company info")
        upsert_company(conn, company)

        _log(f"[{ticker}] Descargando estados financieros anuales...")
        for row in _retry(lambda: fetch_income_statement(ticker, quarterly=False), retries=2, delay=5, label="income stmt"):
            upsert_income_statement(conn, row)
        for row in _retry(lambda: fetch_balance_sheet(ticker, quarterly=False), retries=2, delay=5, label="balance sheet"):
            upsert_balance_sheet(conn, row)
        for row in _retry(lambda: fetch_cash_flow(ticker, quarterly=False), retries=2, delay=5, label="cash flow"):
            upsert_cash_flow(conn, row)

        _log(f"[{ticker}] Descargando estados financieros trimestrales...")
        for row in _retry(lambda: fetch_income_statement(ticker, quarterly=True), retries=2, delay=5, label="income stmt Q"):
            upsert_income_statement(conn, row)
        for row in _retry(lambda: fetch_balance_sheet(ticker, quarterly=True), retries=2, delay=5, label="balance sheet Q"):
            upsert_balance_sheet(conn, row)
        for row in _retry(lambda: fetch_cash_flow(ticker, quarterly=True), retries=2, delay=5, label="cash flow Q"):
            upsert_cash_flow(conn, row)

        return True

    except Exception as e:
        _log(f"[{ticker}] ⚠️  Financials no disponibles: {e}")
        _log(f"[{ticker}]    Continuando con precios + técnico + cuant.")
        return False


def load_ticker(conn: duckdb.DuckDBPyConnection, ticker: str, period: str = "5y") -> None:
    ticker = ticker.upper()

    # 1. Precios — endpoint v8 directo, NO necesita crumb
    _log(f"[{ticker}] Descargando precios ({period})...")
    prices_df = fetch_prices(ticker, period=period)
    if not prices_df.is_empty():
        insert_prices(conn, prices_df)
        _log(f"[{ticker}] {len(prices_df)} filas de precios guardadas.")
    else:
        # Si Yahoo está con rate limit, verificar si hay datos cacheados en DB
        cached = get_prices(conn, ticker)
        if not cached.is_empty():
            _log(f"[{ticker}] ⚠️  Yahoo rate limited — usando {len(cached)} filas cacheadas.")
        else:
            raise RuntimeError(
                f"Sin datos de precios para {ticker}. "
                "Yahoo Finance puede estar con rate limit — intenta en unos minutos."
            )

    # 2. Financials — via yfinance + crumb; tolerante a rate limit
    _try_financials(conn, ticker)

    _log(f"[{ticker}] Listo.")
