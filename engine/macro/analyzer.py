"""
Determina la fase del ciclo económico a partir de 5 indicadores FRED
y produce la recomendación de ETFs correspondiente.

Scoring:
  Yield Curve:  +2 (>1%), +1 (>0%), -1 (>-0.5%), -2 (≤-0.5%)
  PMI:          +2 (>55), +1 (≥50), -1 (≥47), -2 (<47)
  Sahm Rule:    +1 (<0.25), -1 (≥0.25), -3 (≥0.5)
  CPI YoY:      +1 (<2.5%), 0 (<4%), -1 (≥4%)
  Desempleo:    +1 (estable/baja), 0 (sube <0.3%), -1 (sube ≥0.3%)

Fases por score:  ≥5 expansion_strong | ≥2 expansion | ≥0 late_cycle
                  ≥-2 deceleration    | <-2 recession
"""

_PHASES = {
    "expansion_strong": {
        "label": "Expansión Fuerte",
        "color": "green",
        "icon": "🚀",
        "description": "Economía acelerando. Máximo riesgo = máximo retorno esperado.",
        "etfs": [
            {"ticker": "QQQ", "reason": "Nasdaq 100 — tech lidera expansión fuerte"},
            {"ticker": "XLK", "reason": "Sector tecnología — máximo upside del ciclo"},
            {"ticker": "XLY", "reason": "Consumo discrecional — consumidor confiado"},
            {"ticker": "VOO", "reason": "S&P 500 — diversificación base"},
        ],
    },
    "expansion": {
        "label": "Expansión",
        "color": "green",
        "icon": "📈",
        "description": "Crecimiento moderado sostenido. Balancear growth con base amplia.",
        "etfs": [
            {"ticker": "QQQ", "reason": "Nasdaq — outperforma consistentemente en expansión"},
            {"ticker": "VOO", "reason": "S&P 500 — exposición amplia al mercado"},
            {"ticker": "XLI", "reason": "Industriales — se benefician del ciclo positivo"},
        ],
    },
    "late_cycle": {
        "label": "Ciclo Tardío",
        "color": "yellow",
        "icon": "⚠️",
        "description": "Ciclo madurando. Rotar de growth hacia value y commodities.",
        "etfs": [
            {"ticker": "XLE", "reason": "Energía — históricamente outperforma en late cycle"},
            {"ticker": "XLB", "reason": "Materiales — commodities se aprecian al final del ciclo"},
            {"ticker": "VOO", "reason": "Mantener base, reducir exposición growth"},
        ],
    },
    "deceleration": {
        "label": "Desaceleración",
        "color": "orange",
        "icon": "🔻",
        "description": "Economía enfriando. Aumentar defensivos, reducir riesgo.",
        "etfs": [
            {"ticker": "VOO", "reason": "Reducir exposición total, mantener base"},
            {"ticker": "XLV", "reason": "Healthcare — no-cíclico, demanda inelástica"},
            {"ticker": "XLP", "reason": "Consumer staples — demanda estable en cualquier ciclo"},
        ],
    },
    "recession": {
        "label": "Recesión / Alerta",
        "color": "red",
        "icon": "🚨",
        "description": "Riesgo elevado. Preservar capital. Reentrar agresivo en recuperación.",
        "etfs": [
            {"ticker": "SGOV", "reason": "T-bills 0-3m — máxima seguridad y liquidez"},
            {"ticker": "TLT",  "reason": "Bonos largo plazo — rally típico en recesión"},
            {"ticker": "XLU",  "reason": "Utilities — defensivo máximo, dividendo estable"},
        ],
    },
}


def _latest(series: list[dict]) -> float | None:
    return series[-1]["value"] if series else None


def _last_date(series: list[dict]) -> str | None:
    return series[-1]["date"] if series else None


def _trend(series: list[dict], n: int = 3) -> float | None:
    if len(series) < n + 1:
        return None
    return series[-1]["value"] - series[-1 - n]["value"]


def _cpi_yoy(series: list[dict]) -> float | None:
    if len(series) < 13:
        return None
    curr, prev = series[-1]["value"], series[-13]["value"]
    return (curr - prev) / prev * 100 if prev else None


def analyze(data: dict) -> dict:
    """
    data: {series_id: [{date, value}, ...]}
    Retorna el dict completo con fase, señales y ETFs recomendados.
    """
    score = 0
    signals: dict[str, dict] = {}

    # ── 1. Yield Curve (10Y − 2Y) ─────────────────────────────────────────
    yc = _latest(data.get("T10Y2Y", []))
    if yc is not None:
        if yc > 1.0:
            status, note, delta = "green", "Curva normal — crecimiento sano", +2
        elif yc > 0:
            status, note, delta = "green", "Curva positiva leve", +1
        elif yc > -0.5:
            status, note, delta = "orange", "Curva invertida leve — alerta", -1
        else:
            status, note, delta = "red", "Curva muy invertida — señal recesión", -2
        score += delta
        signals["T10Y2Y"] = {
            "label": "Yield Curve (10Y−2Y)",
            "status": status,
            "value": f"{yc:+.2f}%",
            "note": note,
            "date": _last_date(data["T10Y2Y"]),
        }

    # ── 2. PMI Manufacturero (ISM) ────────────────────────────────────────
    pmi = _latest(data.get("NAPM", []))
    if pmi is not None:
        if pmi > 55:
            status, note, delta = "green", "Expansión fuerte (>55)", +2
        elif pmi >= 50:
            status, note, delta = "yellow", "Expansión moderada (50-55)", +1
        elif pmi >= 47:
            status, note, delta = "orange", "Contracción leve (47-50)", -1
        else:
            status, note, delta = "red", "Contracción seria (<47)", -2
        score += delta
        signals["NAPM"] = {
            "label": "PMI Manufacturero (ISM)",
            "status": status,
            "value": f"{pmi:.1f}",
            "note": note,
            "date": _last_date(data["NAPM"]),
        }

    # ── 3. Regla Sahm ─────────────────────────────────────────────────────
    sahm = _latest(data.get("SAHMREALTIME", []))
    if sahm is not None:
        if sahm >= 0.5:
            status, note, delta = "red", "ACTIVADA — recesión en curso", -3
        elif sahm >= 0.25:
            status, note, delta = "orange", "Zona de alerta (0.25-0.50)", -1
        else:
            status, note, delta = "green", "Normal — sin señal de recesión", +1
        score += delta
        signals["SAHMREALTIME"] = {
            "label": "Regla Sahm (desempleo)",
            "status": status,
            "value": f"{sahm:.2f}",
            "note": note,
            "date": _last_date(data["SAHMREALTIME"]),
        }

    # ── 4. CPI Inflación YoY ──────────────────────────────────────────────
    cpi = _cpi_yoy(data.get("CPIAUCSL", []))
    if cpi is not None:
        if cpi < 2.5:
            status, note, delta = "green", "Inflación controlada — Fed neutral/dovish", +1
        elif cpi < 4.0:
            status, note, delta = "yellow", "Inflación moderada — Fed cautelosa", 0
        else:
            status, note, delta = "red", "Inflación alta — Fed hawkish", -1
        score += delta
        signals["CPIAUCSL"] = {
            "label": "CPI Inflación YoY",
            "status": status,
            "value": f"{cpi:.1f}%",
            "note": note,
            "date": _last_date(data["CPIAUCSL"]),
        }

    # ── 5. Tasa de Desempleo ──────────────────────────────────────────────
    unrate = _latest(data.get("UNRATE", []))
    trend  = _trend(data.get("UNRATE", []), n=3)
    if unrate is not None:
        trend_str = f"  ({trend:+.1f}% 3m)" if trend is not None else ""
        if trend is None or trend <= 0.0:
            status, note, delta = "green", "Estable o bajando — mercado laboral sano", +1
        elif trend < 0.3:
            status, note, delta = "yellow", "Subiendo levemente — monitorear", 0
        else:
            status, note, delta = "red", "Subiendo — deterioro laboral", -1
        score += delta
        signals["UNRATE"] = {
            "label": "Tasa de Desempleo",
            "status": status,
            "value": f"{unrate:.1f}%{trend_str}",
            "note": note,
            "date": _last_date(data["UNRATE"]),
        }

    # ── Fase ──────────────────────────────────────────────────────────────
    if score >= 5:
        phase = "expansion_strong"
    elif score >= 2:
        phase = "expansion"
    elif score >= 0:
        phase = "late_cycle"
    elif score >= -2:
        phase = "deceleration"
    else:
        phase = "recession"

    cfg = _PHASES[phase]
    return {
        "phase":       phase,
        "label":       cfg["label"],
        "color":       cfg["color"],
        "icon":        cfg["icon"],
        "description": cfg["description"],
        "score":       score,
        "etfs":        cfg["etfs"],
        "signals":     signals,
    }
