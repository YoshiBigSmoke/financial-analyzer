"""
Fetcher: precios históricos OHLCV.

Usa el endpoint v8/finance/chart de Yahoo directamente —
NO requiere crumb ni browser impersonation, solo curl_cffi básico.
Intenta query1 y query2 con reintentos ante 429.
"""

import sys
import time
import polars as pl
import curl_cffi.requests as cr

_PERIOD_MAP = {
    "1y": "1y", "2y": "2y", "5y": "5y", "10y": "10y", "max": "max",
}
_HOSTS = ["query1", "query2"]

_SESSION: cr.Session | None = None


def _get_session() -> cr.Session:
    global _SESSION
    if _SESSION is None:
        _SESSION = cr.Session()
        _SESSION.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
        })
    return _SESSION


def fetch_prices(ticker: str, period: str = "5y") -> pl.DataFrame:
    """
    Descarga precios históricos OHLCV y los devuelve como DataFrame de Polars.
    Intenta query1 y query2, con un reintento de 3s ante 429.
    """
    yf_period = _PERIOD_MAP.get(period, "5y")
    s = _get_session()
    params = {"interval": "1d", "range": yf_period, "includeAdjustedClose": True}

    # (host, delay_antes_de_intentar)
    attempts = [(h, d) for h in _HOSTS for d in (0, 3)]
    r = None
    for host, delay in attempts:
        if delay > 0:
            time.sleep(delay)
        url = f"https://{host}.finance.yahoo.com/v8/finance/chart/{ticker.upper()}"
        try:
            r = s.get(url, params=params, timeout=30)
        except Exception as e:
            print(f"[prices] {host} error de red: {e}", file=sys.stderr)
            r = None
            continue
        if r.status_code == 200:
            break
        print(f"[prices] {host} HTTP {r.status_code}", file=sys.stderr)

    if r is None or r.status_code != 200:
        return pl.DataFrame()

    data = r.json()
    result_list = data.get("chart", {}).get("result", [])
    if not result_list:
        print(f"[prices] Sin datos de chart para {ticker}", file=sys.stderr)
        return pl.DataFrame()

    chart = result_list[0]
    timestamps = chart.get("timestamp", [])
    if not timestamps:
        return pl.DataFrame()

    quotes = chart["indicators"]["quote"][0]
    adj_close_data = chart["indicators"].get("adjclose", [{}])
    adj_close = adj_close_data[0].get("adjclose", []) if adj_close_data else []

    from datetime import timezone, datetime
    dates = [
        datetime.fromtimestamp(ts, tz=timezone.utc).date().isoformat()
        for ts in timestamps
    ]

    n = len(dates)
    opens  = [float(v) if v is not None else None for v in quotes.get("open",   [None]*n)]
    highs  = [float(v) if v is not None else None for v in quotes.get("high",   [None]*n)]
    lows   = [float(v) if v is not None else None for v in quotes.get("low",    [None]*n)]
    closes = [float(v) if v is not None else None for v in quotes.get("close",  [None]*n)]
    vols   = [int(v)   if v is not None else 0    for v in quotes.get("volume", [0]*n)]
    adjs   = [float(v) if v is not None else c
              for v, c in zip(adj_close if adj_close else [None]*n, closes)]

    rows = [
        (d, o, h, l, c, a, v)
        for d, o, h, l, c, a, v in zip(dates, opens, highs, lows, closes, adjs, vols)
        if all(x is not None for x in (o, h, l, c))
    ]

    if not rows:
        return pl.DataFrame()

    ticker_upper = ticker.upper()
    return pl.DataFrame({
        "ticker":    [ticker_upper] * len(rows),
        "date":      pl.Series([r[0] for r in rows]).cast(pl.Date),
        "open":      [r[1] for r in rows],
        "high":      [r[2] for r in rows],
        "low":       [r[3] for r in rows],
        "close":     [r[4] for r in rows],
        "adj_close": [r[5] for r in rows],
        "volume":    [r[6] for r in rows],
    })
