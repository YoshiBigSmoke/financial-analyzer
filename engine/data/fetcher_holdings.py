"""
Fetchers alternativos de holdings para ETFs.
Vanguard e iShares tienen APIs públicas que devuelven más posiciones que yfinance (que limita a 10).
Arquitectura: cada proveedor tiene su función, fetch_holdings() elige cuál usar según fund_family.
Fallback siempre a yfinance si la fuente falla.
"""

import csv
import io
import sys
import requests

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
}


# ── Vanguard ───────────────────────────────────────────────────────────────

def fetch_vanguard_holdings(ticker: str) -> list[dict] | None:
    """
    API pública de Vanguard — solo necesita el ticker.
    Devuelve todos los holdings disponibles ordenados por peso descendente.
    """
    url = (
        f"https://investor.vanguard.com/investment-products/etfs"
        f"/profile/api/{ticker.upper()}/portfolio-holding/stock"
    )
    try:
        r = requests.get(url, headers=_HEADERS, timeout=15)
        if r.status_code != 200:
            print(f"[holdings:vanguard] HTTP {r.status_code} para {ticker}", file=sys.stderr)
            return None

        data = r.json()

        holding_list = _dig(data, "fund", "entity") or []

        if not holding_list:
            print(f"[holdings:vanguard] Sin holdings en la respuesta para {ticker}", file=sys.stderr)
            return None

        holdings = []
        for h in holding_list:
            weight = h.get("percentWeight")
            symbol = h.get("ticker") or ""
            name   = h.get("longName") or h.get("shortName") or ""
            if weight is None or not symbol:
                continue
            try:
                w = float(weight)
            except (ValueError, TypeError):
                continue
            holdings.append({
                "symbol": str(symbol).strip(),
                "name":   str(name).strip(),
                "weight": round(w, 2),
            })

        holdings.sort(key=lambda x: x["weight"], reverse=True)
        return holdings or None

    except Exception as e:
        print(f"[holdings:vanguard] Error: {e}", file=sys.stderr)
        return None


# ── iShares (BlackRock) ────────────────────────────────────────────────────

# Mapa ticker → (product_id, slug) para los iShares ETFs más usados
_ISHARES = {
    "IVV":  ("239726", "ishares-core-s-p-500-etf"),
    "AGG":  ("239458", "ishares-core-us-aggregate-bond-etf"),
    "LQD":  ("239566", "ishares-iboxx-investment-grade-corporate-bond-etf"),
    "HYG":  ("239565", "ishares-iboxx-high-yield-corporate-bond-etf"),
    "EFA":  ("239623", "ishares-msci-eafe-etf"),
    "EEM":  ("239637", "ishares-msci-emerging-markets-etf"),
    "IEMG": ("264659", "ishares-core-msci-emerging-markets-etf"),
    "ACWI": ("251910", "ishares-msci-acwi-etf"),
    "IWM":  ("239710", "ishares-russell-2000-etf"),
    "IWF":  ("239706", "ishares-russell-1000-growth-etf"),
    "IWD":  ("239707", "ishares-russell-1000-value-etf"),
    "IJH":  ("239763", "ishares-core-s-p-mid-cap-etf"),
    "IJR":  ("239764", "ishares-core-s-p-small-cap-etf"),
    "SHY":  ("239452", "ishares-1-3-year-treasury-bond-etf"),
    "IEF":  ("239455", "ishares-7-10-year-treasury-bond-etf"),
    "TLT":  ("239454", "ishares-20-year-treasury-bond-etf"),
    "SGOV": ("325423", "ishares-0-3-month-treasury-bond-etf"),
    "GOVT": ("291320", "ishares-us-treasury-bond-etf"),
    "MUB":  ("239766", "ishares-national-muni-bond-etf"),
}


def fetch_ishares_holdings(ticker: str) -> list[dict] | None:
    """
    Descarga el CSV público de iShares — usa un mapa de ticker → product_id.
    Devuelve todos los holdings equity con su peso porcentual.
    """
    entry = _ISHARES.get(ticker.upper())
    if not entry:
        return None  # ticker no conocido, no intentamos

    product_id, slug = entry
    url = (
        f"https://www.ishares.com/us/products/{product_id}/{slug}"
        f"/1467271812596.ajax?fileType=csv&tab=portfolio"
    )
    try:
        r = requests.get(url, headers=_HEADERS, timeout=15)
        if r.status_code != 200:
            print(f"[holdings:ishares] HTTP {r.status_code} para {ticker}", file=sys.stderr)
            return None

        # El CSV empieza con ~9 líneas de metadata antes del header real.
        # ETFs de equity tienen "Ticker" como primera columna; bond ETFs arrancan con "Name".
        text = r.content.decode("utf-8-sig")
        lines = text.splitlines()
        header_idx = next(
            (
                i for i, ln in enumerate(lines)
                if ln.startswith('"Ticker"') or ln.startswith("Ticker")
                or ln.startswith('"Name"')   or ln.startswith("Name,")
            ),
            None,
        )
        if header_idx is None:
            print(f"[holdings:ishares] Header no encontrado para {ticker}", file=sys.stderr)
            return None

        reader = csv.DictReader(io.StringIO("\n".join(lines[header_idx:])))
        has_ticker = "Ticker" in (reader.fieldnames or [])
        holdings = []
        for row in reader:
            name  = (row.get("Name") or "").strip().strip('"')
            raw_w = (row.get("Weight (%)") or "").strip().strip('"').replace(",", ".")
            if not name or name in ("-", ""):
                continue
            try:
                weight = round(float(raw_w), 2)
            except (ValueError, TypeError):
                continue
            if weight <= 0:
                continue
            if has_ticker:
                sym = (row.get("Ticker") or "").strip().strip('"')
                if not sym or sym == "-":
                    continue
            else:
                # Bond holdings: usa ISIN como símbolo si existe, si no trunca el nombre
                sym = (row.get("ISIN") or "").strip().strip('"') or name[:12]
            holdings.append({"symbol": sym, "name": name, "weight": weight})

        holdings.sort(key=lambda x: x["weight"], reverse=True)
        return holdings or None

    except Exception as e:
        print(f"[holdings:ishares] Error: {e}", file=sys.stderr)
        return None


# ── Dispatcher público ─────────────────────────────────────────────────────

def fetch_holdings(ticker: str, fund_family: str | None) -> list[dict] | None:
    """
    Punto de entrada principal.
    Elige el fetcher según la familia del fondo y devuelve todos los holdings disponibles.
    Retorna None si no se puede obtener más que yfinance (el caller usará el fallback).
    """
    family = (fund_family or "").lower()

    if "vanguard" in family:
        return fetch_vanguard_holdings(ticker)

    if "ishares" in family or "blackrock" in family:
        return fetch_ishares_holdings(ticker)

    # Para Invesco (QQQ), SPDR (SPY/XLK), Schwab, etc. → fallback a yfinance por ahora
    return None


# ── Utilidad interna ───────────────────────────────────────────────────────

def _dig(d: dict, *keys):
    """Navega un dict anidado de forma segura. Retorna None si alguna clave no existe."""
    for k in keys:
        if not isinstance(d, dict):
            return None
        d = d.get(k)
    return d
