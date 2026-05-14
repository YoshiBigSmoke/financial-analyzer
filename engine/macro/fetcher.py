"""
Fuentes de datos macro (sin API key):
  - yfinance  → yields del Tesoro (curva de rendimiento)
  - BLS API   → desempleo, CPI (Bureau of Labor Statistics)
  - Derivado  → Regla Sahm (calculada desde UNRATE)

FRED no es accesible sin cuenta; este módulo usa fuentes alternativas
que devuelven los mismos formatos para que el analyzer no cambie.
"""

import warnings
import requests
import yfinance as yf
import pandas as pd
from datetime import datetime


# ── 1. Curva de rendimiento vía yfinance ───────────────────────────────────

def _fetch_yield_curve(limit: int = 24) -> list[dict]:
    """
    Spread 10Y − 13W como proxy del T10Y2Y.
    (La Fed usa 10Y-3M como su indicador primario de recesión.)
    """
    warnings.filterwarnings("ignore")

    df_10y = yf.download("^TNX", period="3y", interval="1wk",
                         progress=False, auto_adjust=True)
    df_3m  = yf.download("^IRX", period="3y", interval="1wk",
                         progress=False, auto_adjust=True)

    c10 = df_10y["Close"].resample("ME").last().dropna().squeeze()
    c3m = df_3m["Close"].resample("ME").last().dropna().squeeze()
    spread = (c10 - c3m).dropna()

    result = []
    for dt, val in spread.tail(limit).items():
        result.append({"date": str(dt)[:10], "value": round(float(val), 3)})
    return result


# ── 2. BLS API (unemployment + CPI) ──────────────────────────────────────

_BLS_URL = "https://api.bls.gov/publicAPI/v1/timeseries/data/"
_BLS_MONTH = {f"M{i:02d}": f"{i:02d}" for i in range(1, 13)}


def _fetch_bls(start_year: str = "2022") -> dict[str, list[dict]]:
    """
    Retorna {series_id: [{date, value}]} ordenado cronológicamente.
    Series: LNS14000000 = UNRATE, CUUR0000SA0 = CPI index
    """
    end_year = str(datetime.now().year)
    payload = {
        "seriesid": ["LNS14000000", "CUUR0000SA0"],
        "startyear": start_year,
        "endyear": end_year,
    }
    resp = requests.post(_BLS_URL, json=payload, timeout=15)
    resp.raise_for_status()

    body = resp.json()
    if body.get("status") != "REQUEST_SUCCEEDED":
        raise ValueError(f"BLS error: {body.get('message', 'unknown')}")

    result: dict[str, list[dict]] = {}
    for series in body["Results"]["series"]:
        sid  = series["seriesID"]
        rows = []
        for obs in reversed(series["data"]):   # BLS devuelve newest-first
            month = _BLS_MONTH.get(obs["period"])
            if month is None:
                continue                        # saltar promedios anuales (M13)
            try:
                rows.append({
                    "date":  f"{obs['year']}-{month}-01",
                    "value": float(obs["value"]),
                })
            except (ValueError, KeyError):
                continue
        result[sid] = rows

    return result


# ── 3. Regla Sahm (computada desde UNRATE) ────────────────────────────────

def _compute_sahm(unrate: list[dict]) -> list[dict]:
    """
    Sahm Rule = 3m_avg(UNRATE) − min(3m_avg(UNRATE)) en los últimos 12 meses.
    Genera una observación por cada mes con suficiente historial (≥15 obs).
    """
    if len(unrate) < 15:
        return []

    vals  = [x["value"] for x in unrate]
    dates = [x["date"]  for x in unrate]

    result = []
    for i in range(14, len(vals)):
        curr_avg = sum(vals[i - 2: i + 1]) / 3
        # mínimo de todos los promedios 3m en la ventana de 12 meses
        window_avgs = [
            sum(vals[j - 2: j + 1]) / 3
            for j in range(max(2, i - 11), i + 1)
        ]
        sahm_val = curr_avg - min(window_avgs)
        result.append({"date": dates[i], "value": round(sahm_val, 3)})

    return result


# ── API pública del módulo ─────────────────────────────────────────────────

def fetch_all(limit: int = 24) -> dict:
    """
    Retorna el mismo contrato que la versión FRED:
      {
        "data":   {series_id: [{date, value}, ...]},
        "errors": {series_id: "mensaje"}
      }
    Series resultantes: T10Y2Y, UNRATE, CPIAUCSL, SAHMREALTIME
    (NAPM/PMI no disponible sin FRED — se omite, el analyzer lo maneja)
    """
    data:   dict[str, list[dict]] = {}
    errors: dict[str, str]        = {}

    # Curva de rendimiento
    try:
        data["T10Y2Y"] = _fetch_yield_curve(limit)
    except Exception as exc:
        errors["T10Y2Y"] = str(exc)
        data["T10Y2Y"]   = []

    # Desempleo + CPI desde BLS
    bls: dict[str, list[dict]] = {}
    try:
        bls = _fetch_bls()
    except Exception as exc:
        errors["bls"] = str(exc)

    data["UNRATE"]   = bls.get("LNS14000000", [])[-limit:]
    data["CPIAUCSL"] = bls.get("CUUR0000SA0", [])[-limit:]

    if not data["UNRATE"]:
        errors["UNRATE"] = errors.get("bls", "sin datos BLS")
    if not data["CPIAUCSL"]:
        errors["CPIAUCSL"] = errors.get("bls", "sin datos BLS")

    # Regla Sahm derivada
    try:
        data["SAHMREALTIME"] = _compute_sahm(bls.get("LNS14000000", []))[-limit:]
    except Exception as exc:
        errors["SAHMREALTIME"] = str(exc)
        data["SAHMREALTIME"]   = []

    # NAPM vacío — el analyzer lo omitirá limpiamente
    data["NAPM"] = []

    return {"data": data, "errors": errors}
