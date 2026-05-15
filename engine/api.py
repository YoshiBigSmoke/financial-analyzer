"""
Entry point del engine para el IPC con Tauri.
Rust llama: python -m engine.api <comando> <args_json>
Este script imprime JSON a stdout y termina.

Comandos disponibles:
  load_ticker   {"ticker": "AAPL", "period": "5y"}
  fundamental   {"ticker": "AAPL"}
  technical     {"ticker": "AAPL"}
  quant         {"ticker": "AAPL", "horizon": 30}
  watchlist     {}
  add_watchlist {"ticker": "AAPL", "notes": "..."}
  prices        {"ticker": "AAPL"}
  macro         {}   | {"refresh": true}
"""

import sys
import json

from engine.db.connection import get_connection, close_connection
from engine.data.pipeline import load_ticker
from engine.fundamental.ratios import calculate_and_save_ratios
from engine.fundamental.dcf import run_dcf
from engine.fundamental.scoring import run_scoring
from engine.technical.signals import analyze, summary
from engine.db.queries import get_prices, get_watchlist, add_to_watchlist, get_company


def _ok(data):
    print(json.dumps({"ok": True, "data": data}))


def _err(msg):
    print(json.dumps({"ok": False, "error": str(msg)}))


# ── Handlers ───────────────────────────────────────────────────────────────

def cmd_load_ticker(conn, args):
    ticker = args["ticker"].upper()
    period = args.get("period", "5y")
    load_ticker(conn, ticker, period=period)
    _ok({"ticker": ticker, "loaded": True})


def cmd_fundamental(conn, args):
    ticker = args["ticker"].upper()

    # ── Detectar ETF via DB primero (evita llamada extra a yfinance) ──────
    company_row = get_company(conn, ticker)
    is_etf_cached = company_row and company_row.get("sector") == "ETF"

    if is_etf_cached:
        from engine.data.fetcher_etf import fetch_etf
        try:
            etf_data = fetch_etf(ticker)
        except Exception as e:
            etf_data = None
            print(f"[fundamental] fetch_etf error: {e}", file=sys.stderr)

        if etf_data is not None:
            _ok(etf_data)
            return
        # Si fetch_etf falla, devolvemos error claro en vez de panel vacío
        _err(f"No se pudo obtener datos del ETF {ticker}. Intenta en unos segundos.")
        return

    # ── Fallback: detectar ETF via yfinance si no está en DB ─────────────
    from engine.data.fetcher_etf import fetch_etf
    try:
        etf_data = fetch_etf(ticker)
        if etf_data is not None:
            _ok(etf_data)
            return
    except Exception:
        pass

    # ── Análisis fundamental de acción ────────────────────────────────────
    ratios = calculate_and_save_ratios(conn, ticker)
    dcf    = run_dcf(conn, ticker)
    score  = run_scoring(conn, ticker)

    if ratios and "period_end" in ratios:
        ratios["period_end"] = str(ratios["period_end"])

    if company_row and "updated_at" in company_row:
        company_row["updated_at"] = str(company_row["updated_at"])

    _ok({
        "quote_type": "EQUITY",
        "company":  company_row,
        "ratios":   ratios,
        "dcf":      dcf,
        "scoring":  score,
    })


def cmd_technical(conn, args):
    ticker = args["ticker"].upper()
    df = get_prices(conn, ticker)

    if df.is_empty():
        _err(f"Sin datos de precios para {ticker}. Corre load_ticker primero.")
        return

    signals  = analyze(df)
    consensus = summary(signals)
    _ok({"signals": signals, "consensus": consensus})


def cmd_quant(conn, args):
    import warnings
    warnings.filterwarnings("ignore")

    from engine.quant.forecast import run_forecast

    ticker  = args["ticker"].upper()
    horizon = int(args.get("horizon", 30))
    sims    = int(args.get("simulations", 10_000))

    result = run_forecast(conn, ticker, horizon=horizon, simulations=sims)
    if result is None:
        _err(f"Sin datos para {ticker}")
        return

    # Limpiar arrays numpy no serializables
    result.pop("paths", None)
    result.pop("final_prices", None)
    _ok(result)


def cmd_prices(conn, args):
    ticker = args["ticker"].upper()
    df = get_prices(conn, ticker)
    if df.is_empty():
        _ok([])
        return

    rows = df.select(["date", "open", "high", "low", "adj_close", "volume"]).to_dicts()
    for r in rows:
        r["date"] = str(r["date"])
    _ok(rows)


def cmd_watchlist(conn, _args):
    wl = get_watchlist(conn)
    for row in wl:
        row["added_at"] = str(row["added_at"])
    _ok(wl)


def cmd_add_watchlist(conn, args):
    ticker = args["ticker"].upper()
    notes  = args.get("notes", "")
    add_to_watchlist(conn, ticker, notes)
    _ok({"added": ticker})


def cmd_macro(conn, args):
    from engine.macro.fetcher  import fetch_all
    from engine.macro.analyzer import analyze
    from datetime import datetime

    force_refresh = args.get("refresh", False)
    fetch_errors: dict = {}

    # ── Verificar frescura del caché (TTL = 24 h) ─────────────────────────
    cache_stale = True
    try:
        row = conn.execute("SELECT MIN(fetched_at) FROM macro_cache").fetchone()
        oldest = row[0] if row else None
        if oldest is not None:
            if isinstance(oldest, str):
                oldest = datetime.fromisoformat(oldest)
            cache_stale = (datetime.now() - oldest).total_seconds() > 86_400
    except Exception:
        cache_stale = True

    if cache_stale or force_refresh:
        fetched = fetch_all(limit=24)
        series_data = fetched["data"]
        fetch_errors = fetched.get("errors", {})

        conn.execute("DELETE FROM macro_cache")
        for sid, rows in series_data.items():
            for r in rows:
                conn.execute(
                    "INSERT INTO macro_cache (series_id, date, value) VALUES (?, ?, ?)",
                    [sid, r["date"], r["value"]],
                )
    else:
        rows = conn.execute(
            "SELECT series_id, date, value FROM macro_cache ORDER BY series_id, date"
        ).fetchall()
        series_data: dict = {}
        for sid, date, value in rows:
            series_data.setdefault(sid, []).append(
                {"date": str(date), "value": float(value)}
            )

    result = analyze(series_data)

    ts_row = conn.execute("SELECT MAX(fetched_at) FROM macro_cache").fetchone()
    result["last_updated"] = str(ts_row[0]) if ts_row and ts_row[0] else None
    result["fetch_errors"] = fetch_errors

    _ok(result)


# ── Dispatch ───────────────────────────────────────────────────────────────

COMMANDS = {
    "load_ticker":   cmd_load_ticker,
    "fundamental":   cmd_fundamental,
    "technical":     cmd_technical,
    "quant":         cmd_quant,
    "prices":        cmd_prices,
    "watchlist":     cmd_watchlist,
    "add_watchlist": cmd_add_watchlist,
    "macro":         cmd_macro,
}


def main():
    if len(sys.argv) < 2:
        _err("Uso: python -m engine.api <comando> [args_json]")
        return

    command = sys.argv[1]
    args = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}

    if command not in COMMANDS:
        _err(f"Comando desconocido: {command}. Disponibles: {list(COMMANDS)}")
        return

    conn = get_connection()
    try:
        COMMANDS[command](conn, args)
    except Exception as e:
        _err(str(e))
    finally:
        close_connection()


if __name__ == "__main__":
    main()
