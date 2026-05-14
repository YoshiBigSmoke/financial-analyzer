"""
Extrae datos específicos de ETFs desde yfinance.
Detecta si un ticker es ETF vía quoteType y devuelve
holdings, sectores, expense ratio, retornos y veredicto.
"""

import warnings
import yfinance as yf

warnings.filterwarnings("ignore")

# ── Mapeo de sectores a nombres legibles ──────────────────────────────────

_SECTOR_NAMES = {
    "technology":            "Tecnología",
    "consumer_cyclical":     "Consumo Discrecional",
    "consumer_defensive":    "Consumo Básico",
    "financial_services":    "Servicios Financieros",
    "healthcare":            "Salud",
    "industrials":           "Industriales",
    "communication_services":"Comunicaciones",
    "energy":                "Energía",
    "basic_materials":       "Materiales",
    "realestate":            "Bienes Raíces",
    "utilities":             "Utilities",
}


# ── Helpers ────────────────────────────────────────────────────────────────

def _parse_er(raw) -> float | None:
    """
    Convierte netExpenseRatio a porcentaje float.
    yfinance devuelve 0.18 para significar 0.18% (ya es porcentaje).
    """
    if raw is None:
        return None
    if isinstance(raw, str):
        return float(raw.replace("%", "").strip())
    return float(raw)   # 0.18 → 0.18% directo


def _pct(v) -> float | None:
    """Convierte retornos de decimal a porcentaje cuando aplica."""
    if v is None:
        return None
    v = float(v)
    return v * 100 if abs(v) < 5 else v


def _score(er_pct, cat_er_pct, aum, r3y, turnover) -> dict:
    score = 0
    notes = []

    # 1. Expense ratio vs categoría
    if er_pct is not None:
        if cat_er_pct and cat_er_pct > 0:
            if er_pct < cat_er_pct * 0.4:
                score += 3
                notes.append(f"Muy barato vs categoría ({er_pct:.2f}% vs avg {cat_er_pct:.2f}%)")
            elif er_pct < cat_er_pct * 0.8:
                score += 2
                notes.append(f"Bajo costo vs categoría ({er_pct:.2f}% vs avg {cat_er_pct:.2f}%)")
            elif er_pct <= cat_er_pct:
                score += 1
                notes.append(f"En línea con la categoría ({er_pct:.2f}% vs avg {cat_er_pct:.2f}%)")
            else:
                score -= 1
                notes.append(f"Más caro que su categoría ({er_pct:.2f}% vs avg {cat_er_pct:.2f}%)")
        else:
            if er_pct < 0.10:
                score += 3
                notes.append(f"Expense ratio excelente: {er_pct:.2f}%")
            elif er_pct < 0.25:
                score += 2
                notes.append(f"Expense ratio competitivo: {er_pct:.2f}%")
            elif er_pct < 0.60:
                score += 1
                notes.append(f"Expense ratio moderado: {er_pct:.2f}%")
            else:
                score -= 1
                notes.append(f"Expense ratio elevado: {er_pct:.2f}%")

    # 2. AUM / liquidez
    if aum:
        if aum > 50e9:
            score += 2
            notes.append(f"AUM muy grande (${aum/1e9:.0f}B) — máxima liquidez")
        elif aum > 5e9:
            score += 1
            notes.append(f"AUM sólido (${aum/1e9:.1f}B)")
        elif aum > 500e6:
            notes.append(f"AUM aceptable (${aum/1e6:.0f}M)")
        else:
            score -= 1
            notes.append(f"AUM pequeño (${aum/1e6:.0f}M) — revisar liquidez y spread")

    # 3. Retorno 3Y
    if r3y is not None:
        if r3y > 15:
            score += 2
            notes.append(f"Retorno 3Y excepcional: +{r3y:.1f}%/año")
        elif r3y > 8:
            score += 1
            notes.append(f"Retorno 3Y sólido: +{r3y:.1f}%/año")
        elif r3y > 0:
            notes.append(f"Retorno 3Y moderado: +{r3y:.1f}%/año")
        else:
            score -= 1
            notes.append(f"Retorno 3Y negativo: {r3y:.1f}%/año")

    # 4. Turnover (bajo = eficiente en costos de fricción)
    if turnover is not None:
        if turnover < 0.10:
            score += 1
            notes.append(f"Turnover muy bajo ({turnover*100:.0f}%) — eficiente y tax-friendly")
        elif turnover > 0.80:
            score -= 1
            notes.append(f"Turnover alto ({turnover*100:.0f}%) — costos ocultos de trading")

    # Veredicto
    if score >= 7:
        verdict, color = "Excelente",             "green"
    elif score >= 5:
        verdict, color = "Muy bueno",             "green"
    elif score >= 3:
        verdict, color = "Bueno",                 "green"
    elif score >= 1:
        verdict, color = "Aceptable",             "yellow"
    elif score >= -1:
        verdict, color = "Caro para lo que ofrece", "orange"
    else:
        verdict, color = "No recomendado",        "red"

    return {"score": score, "verdict": verdict, "color": color, "notes": notes}


# ── API pública ────────────────────────────────────────────────────────────

def is_etf(ticker: str) -> bool:
    t = yf.Ticker(ticker)
    return t.info.get("quoteType", "") == "ETF"


def fetch_etf(ticker: str) -> dict | None:
    """
    Retorna el dict completo de análisis ETF, o None si el ticker no es un ETF.
    """
    t    = yf.Ticker(ticker)
    info = t.info

    if info.get("quoteType", "") != "ETF":
        return None

    # ── Expense ratio ──────────────────────────────────────────────────────
    er_pct     = _parse_er(info.get("netExpenseRatio"))
    cat_er_pct = None
    turnover   = None

    try:
        ops = t.funds_data.fund_operations
        er_row = ops.loc["Annual Report Expense Ratio"]
        if er_pct is None:
            er_pct = float(er_row.iloc[0]) * 100
        cat_val = float(er_row.iloc[1])
        cat_er_pct = cat_val * 100 if cat_val < 1 else cat_val

        turn_row   = ops.loc["Annual Holdings Turnover"]
        turnover   = float(turn_row.iloc[0])
        total_assets_ops = float(ops.loc["Total Net Assets"].iloc[0])
    except Exception:
        total_assets_ops = None

    # ── Holdings (top 10) ─────────────────────────────────────────────────
    holdings = []
    try:
        df = t.funds_data.top_holdings.reset_index()
        for _, row in df.head(10).iterrows():
            holdings.append({
                "symbol":  str(row.get("Symbol", row.iloc[0])),
                "name":    str(row.get("Name",   row.iloc[1])),
                "weight":  round(float(row.get("Holding Percent", row.iloc[2])) * 100, 2),
            })
    except Exception:
        pass

    # ── Sectores ──────────────────────────────────────────────────────────
    sectors = []
    try:
        raw = t.funds_data.sector_weightings or {}
        for key, val in sorted(raw.items(), key=lambda x: x[1], reverse=True):
            if val and val > 0:
                sectors.append({
                    "key":    key,
                    "name":   _SECTOR_NAMES.get(key, key.replace("_", " ").title()),
                    "weight": round(float(val) * 100, 2),
                })
    except Exception:
        pass

    # ── Asset allocation ──────────────────────────────────────────────────
    asset_classes = {}
    try:
        ac = t.funds_data.asset_classes or {}
        asset_classes = {
            "stocks": round(float(ac.get("stockPosition", 0)) * 100, 2),
            "bonds":  round(float(ac.get("bondPosition",  0)) * 100, 2),
            "cash":   round(float(ac.get("cashPosition",  0)) * 100, 2),
            "other":  round(float(ac.get("otherPosition", 0) +
                                  ac.get("preferredPosition", 0) +
                                  ac.get("convertiblePosition", 0)) * 100, 2),
        }
    except Exception:
        pass

    # ── Retornos ──────────────────────────────────────────────────────────
    r3y = _pct(info.get("threeYearAverageReturn"))
    r5y = _pct(info.get("fiveYearAverageReturn"))
    ytd = info.get("ytdReturn")

    performance = {
        "ytd":  round(float(ytd), 2) if ytd is not None else None,
        "3y":   round(r3y, 2)        if r3y is not None else None,
        "5y":   round(r5y, 2)        if r5y is not None else None,
        "beta": round(float(info.get("beta3Year")), 3) if info.get("beta3Year") else None,
    }

    # ── AUM ───────────────────────────────────────────────────────────────
    aum = info.get("totalAssets") or (total_assets_ops * 1e6 if total_assets_ops else None)

    # ── Costo anual sobre $10k ─────────────────────────────────────────────
    annual_cost_10k = round(10_000 * er_pct / 100, 2) if er_pct else None

    # ── Veredicto ─────────────────────────────────────────────────────────
    verdict = _score(er_pct, cat_er_pct, aum, r3y, turnover)

    return {
        "quote_type": "ETF",
        "ticker":     ticker,
        "name":       info.get("longName", ticker),
        "fund_family":info.get("fundFamily"),
        "category":   info.get("category") or info.get("categoryName"),
        "legal_type": t.funds_data.fund_overview.get("legalType"),
        "aum":        aum,
        "volume_avg": info.get("averageVolume"),
        "dividend_yield": round(float(info.get("yield", 0)) * 100, 2) if info.get("yield") else None,
        "expense_ratio":    er_pct,
        "cat_expense_ratio":cat_er_pct,
        "annual_cost_10k":  annual_cost_10k,
        "turnover":         round(turnover * 100, 1) if turnover else None,
        "valuation": {
            "pe": round(float(info.get("trailingPE")), 2) if info.get("trailingPE") else None,
            "pb": round(float(info.get("priceToBook")), 3) if info.get("priceToBook") else None,
        },
        "performance":   performance,
        "holdings":      holdings,
        "sectors":       sectors,
        "asset_classes": asset_classes,
        "verdict":       verdict,
    }
