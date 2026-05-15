"""
Extrae datos específicos de ETFs desde yfinance.
Detecta si un ticker es ETF vía quoteType y devuelve análisis completo.
"""

import warnings
from datetime import datetime
import yfinance as yf
from engine.data.fetcher_holdings import fetch_holdings

warnings.filterwarnings("ignore")

# ── Nombres de sectores ────────────────────────────────────────────────────

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

# ── Alternativas baratas por categoría ────────────────────────────────────

_ALTERNATIVES = {
    "large blend":           ["VOO (0.03%)", "IVV (0.03%)", "SPY (0.09%)"],
    "large growth":          ["VUG (0.04%)", "IWF (0.19%)", "QQQ (0.20%)"],
    "large value":           ["VTV (0.04%)", "IVE (0.18%)", "SCHV (0.04%)"],
    "small blend":           ["VB (0.05%)",  "IJR (0.06%)", "SCHA (0.04%)"],
    "small growth":          ["VBK (0.07%)", "IJT (0.18%)"],
    "small value":           ["VBR (0.07%)", "IJS (0.18%)"],
    "mid-cap blend":         ["VO (0.04%)",  "IJH (0.05%)", "MDY (0.24%)"],
    "technology":            ["VGT (0.10%)", "XLK (0.13%)", "FTEC (0.08%)"],
    "health":                ["VHT (0.10%)", "XLV (0.13%)", "FHLC (0.08%)"],
    "financial":             ["VFH (0.10%)", "XLF (0.13%)"],
    "energy":                ["VDE (0.10%)", "XLE (0.13%)"],
    "ultrashort bond":       ["SGOV (0.09%)", "BIL (0.14%)"],
    "short-term bond":       ["BSV (0.04%)",  "SHY (0.15%)"],
    "intermediate-term bond":["BIV (0.04%)",  "IEF (0.15%)", "AGG (0.03%)"],
    "long-term bond":        ["BLV (0.04%)",  "TLT (0.15%)"],
    "world large-stock blend":["VT (0.07%)",  "ACWI (0.33%)"],
    "diversified emerging mkts":["VWO (0.08%)", "EEM (0.68%)", "IEMG (0.09%)"],
}


# ── Helpers ────────────────────────────────────────────────────────────────

def _parse_er(raw) -> float | None:
    if raw is None:
        return None
    if isinstance(raw, str):
        return float(raw.replace("%", "").strip())
    return float(raw)   # yfinance retorna 0.18 = 0.18% ya en porcentaje


def _pct(v) -> float | None:
    """Decimal a porcentaje: 0.234 → 23.4, pero 23.4 → 23.4 (no doble)."""
    if v is None:
        return None
    v = float(v)
    return round(v * 100, 2) if abs(v) < 5 else round(v, 2)


def _score(er_pct, cat_er_pct, aum, r3y, turnover, r1y, dividend_yield, beta) -> dict:
    score = 0
    notes = []

    # 1. Expense ratio vs categoría
    if er_pct is not None:
        if cat_er_pct and cat_er_pct > 0:
            ratio = er_pct / cat_er_pct
            if ratio < 0.3:
                score += 3
                notes.append(f"Costo muy por debajo de categoría: {er_pct:.2f}% vs promedio {cat_er_pct:.2f}%")
            elif ratio < 0.7:
                score += 2
                notes.append(f"Costo menor que la categoría: {er_pct:.2f}% vs promedio {cat_er_pct:.2f}%")
            elif ratio <= 1.1:
                score += 1
                notes.append(f"Costo en línea con la categoría: {er_pct:.2f}% vs promedio {cat_er_pct:.2f}%")
            else:
                score -= 1
                notes.append(f"⚠️ Más caro que su categoría: {er_pct:.2f}% vs promedio {cat_er_pct:.2f}%")
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
                notes.append(f"⚠️ Expense ratio elevado: {er_pct:.2f}%")

    # 2. AUM / liquidez
    if aum:
        if aum > 50e9:
            score += 2
            notes.append(f"Fondo muy grande (${aum/1e9:.0f}B) — spread mínimo, máxima liquidez")
        elif aum > 5e9:
            score += 1
            notes.append(f"AUM sólido: ${aum/1e9:.1f}B")
        elif aum > 500e6:
            notes.append(f"AUM aceptable: ${aum/1e6:.0f}M — liquidez razonable")
        else:
            score -= 1
            notes.append(f"⚠️ AUM pequeño (${aum/1e6:.0f}M) — riesgo de cierre y spread amplio")

    # 3. Retorno 3Y (anualizado)
    if r3y is not None:
        if r3y > 15:
            score += 2
            notes.append(f"Retorno 3Y anualizado excepcional: +{r3y:.1f}%")
        elif r3y > 8:
            score += 1
            notes.append(f"Retorno 3Y anualizado sólido: +{r3y:.1f}%")
        elif r3y > 0:
            notes.append(f"Retorno 3Y anualizado moderado: +{r3y:.1f}%")
        else:
            score -= 1
            notes.append(f"⚠️ Retorno 3Y negativo: {r3y:.1f}%")

    # 4. Retorno 1Y
    if r1y is not None:
        if r1y > 20:
            score += 1
            notes.append(f"Fuerte retorno en el último año: +{r1y:.1f}%")
        elif r1y < -15:
            score -= 1
            notes.append(f"⚠️ Caída fuerte en el último año: {r1y:.1f}%")

    # 5. Turnover (ya está en porcentaje)
    if turnover is not None:
        if turnover < 10:
            score += 1
            notes.append(f"Rotación muy baja ({turnover:.0f}%) — eficiente y tax-friendly")
        elif turnover > 80:
            score -= 1
            notes.append(f"⚠️ Alta rotación ({turnover:.0f}%) — costos ocultos de trading")

    # 6. Dividendo (bonus si yield > 0)
    if dividend_yield and dividend_yield > 0:
        notes.append(f"Paga dividendo: {dividend_yield:.2f}% anual")

    # 7. Beta (riesgo de mercado)
    if beta is not None:
        if beta > 1.5:
            notes.append(f"⚠️ Beta alta ({beta:.2f}) — más volátil que el mercado")
        elif beta < 0.3 and beta >= 0:
            notes.append(f"Beta muy baja ({beta:.2f}) — comportamiento defensivo / descorrelacionado")

    # Veredicto
    if score >= 7:
        verdict, color = "Excelente",              "green"
    elif score >= 5:
        verdict, color = "Muy bueno",              "green"
    elif score >= 3:
        verdict, color = "Bueno",                  "green"
    elif score >= 1:
        verdict, color = "Aceptable",              "yellow"
    elif score >= -1:
        verdict, color = "Caro para lo que ofrece","orange"
    else:
        verdict, color = "No recomendado",         "red"

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
    total_assets_ops = None

    try:
        ops = t.funds_data.fund_operations
        er_row = ops.loc["Annual Report Expense Ratio"]
        if er_pct is None:
            raw_er = float(er_row.iloc[0])
            er_pct = raw_er * 100 if raw_er < 1 else raw_er

        cat_val = float(er_row.iloc[1])
        cat_er_pct = cat_val * 100 if cat_val < 1 else cat_val

        turn_row = ops.loc["Annual Holdings Turnover"]
        raw_turn = float(turn_row.iloc[0])
        turnover = raw_turn * 100 if raw_turn <= 1 else raw_turn

        total_assets_ops = float(ops.loc["Total Net Assets"].iloc[0])
    except Exception:
        pass

    # ── Holdings — fuente primaria: Vanguard/iShares APIs; fallback: yfinance ──
    holdings = fetch_holdings(ticker, info.get("fundFamily")) or []

    if not holdings:
        try:
            df = t.funds_data.top_holdings.reset_index()
            for _, row in df.iterrows():
                holdings.append({
                    "symbol": str(row.get("Symbol", row.iloc[0])),
                    "name":   str(row.get("Name",   row.iloc[1])),
                    "weight": round(float(row.get("Holding Percent", row.iloc[2])) * 100, 2),
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
    asset_classes = {"stocks": 0.0, "bonds": 0.0, "cash": 0.0, "other": 0.0}
    try:
        ac = t.funds_data.asset_classes or {}
        asset_classes = {
            "stocks": round(float(ac.get("stockPosition",     0)) * 100, 2),
            "bonds":  round(float(ac.get("bondPosition",      0)) * 100, 2),
            "cash":   round(float(ac.get("cashPosition",      0)) * 100, 2),
            "other":  round(float(ac.get("otherPosition",     0) +
                                  ac.get("preferredPosition", 0) +
                                  ac.get("convertiblePosition", 0)) * 100, 2),
        }
    except Exception:
        pass

    # ── Retornos ──────────────────────────────────────────────────────────
    r3y = _pct(info.get("threeYearAverageReturn"))
    r5y = _pct(info.get("fiveYearAverageReturn"))
    ytd = info.get("ytdReturn")
    r1y = None
    try:
        ops2 = t.funds_data.fund_operations
        r1y_raw = ops2.loc["1 Year"].iloc[0] if "1 Year" in ops2.index else None
        if r1y_raw is not None:
            r1y = _pct(r1y_raw)
    except Exception:
        pass

    ytd_val = round(float(ytd), 2) if ytd is not None else None

    performance = {
        "ytd":  ytd_val,
        "1y":   r1y,
        "3y":   round(r3y, 2) if r3y is not None else None,
        "5y":   round(r5y, 2) if r5y is not None else None,
        "beta": round(float(info.get("beta3Year")), 3) if info.get("beta3Year") is not None else None,
    }

    # ── AUM ───────────────────────────────────────────────────────────────
    aum = info.get("totalAssets") or (total_assets_ops * 1e6 if total_assets_ops else None)

    # ── Precio, NAV, rango 52 semanas ─────────────────────────────────────
    price    = info.get("regularMarketPrice") or info.get("previousClose")
    nav      = info.get("navPrice")
    w52h     = info.get("fiftyTwoWeekHigh")
    w52l     = info.get("fiftyTwoWeekLow")
    prem_disc = None
    if price and nav and nav > 0:
        prem_disc = round((price - nav) / nav * 100, 3)

    # ── Fecha de inicio ───────────────────────────────────────────────────
    inception_date = None
    try:
        ts = info.get("fundInceptionDate")
        if ts:
            inception_date = datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
    except Exception:
        pass

    # ── Índice rastreado ──────────────────────────────────────────────────
    index_tracked = None
    try:
        overview = t.funds_data.fund_overview
        index_tracked = overview.get("fundBenchmark") or overview.get("legacyProfileBenchmark")
    except Exception:
        pass

    # ── Dividend yield ────────────────────────────────────────────────────
    div_yield = None
    raw_yield = info.get("yield") or info.get("dividendYield")
    if raw_yield is not None:
        raw_yield = float(raw_yield)
        div_yield = round(raw_yield * 100, 2) if raw_yield < 1 else round(raw_yield, 2)

    # ── Alternativas ──────────────────────────────────────────────────────
    category_str = (info.get("category") or "").lower()
    alternatives = None
    for cat_key, alts in _ALTERNATIVES.items():
        if cat_key in category_str or category_str in cat_key:
            alternatives = [a for a in alts if not a.startswith(ticker)]
            break

    # ── Costo anual sobre $10k ────────────────────────────────────────────
    annual_cost_10k = round(10_000 * er_pct / 100, 2) if er_pct else None

    # ── Veredicto ─────────────────────────────────────────────────────────
    verdict = _score(
        er_pct, cat_er_pct, aum, r3y,
        turnover, r1y, div_yield,
        performance.get("beta"),
    )

    return {
        "quote_type":     "ETF",
        "ticker":         ticker,
        "name":           info.get("longName", ticker),
        "fund_family":    info.get("fundFamily"),
        "category":       info.get("category") or info.get("categoryName"),
        "legal_type":     info.get("legalType"),
        "inception_date": inception_date,
        "index_tracked":  index_tracked,
        "aum":            aum,
        "volume_avg":     info.get("averageVolume"),
        "price":          round(float(price), 2) if price else None,
        "nav":            round(float(nav), 4)   if nav   else None,
        "premium_discount": prem_disc,
        "week52_high":    round(float(w52h), 2)  if w52h  else None,
        "week52_low":     round(float(w52l), 2)  if w52l  else None,
        "dividend_yield": div_yield,
        "expense_ratio":     er_pct,
        "cat_expense_ratio": cat_er_pct,
        "annual_cost_10k":   annual_cost_10k,
        "turnover":          round(turnover, 1) if turnover is not None else None,
        "valuation": {
            "pe": round(float(info.get("trailingPE")), 2) if info.get("trailingPE") else None,
            "pb": round(float(info.get("priceToBook")), 3) if info.get("priceToBook") else None,
        },
        "performance":   performance,
        "holdings":      holdings,
        "sectors":       sectors,
        "asset_classes": asset_classes,
        "alternatives":  alternatives,
        "verdict":       verdict,
    }
