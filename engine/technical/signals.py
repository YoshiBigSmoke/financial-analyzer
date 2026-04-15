"""
Señales de trading basadas en los indicadores técnicos.
Devuelve: "buy", "sell" o "neutral" con una razón.

No es consejo financiero — es para análisis personal.
"""

import polars as pl
from engine.technical.indicators import (
    sma, ema, macd, rsi, stochastic,
    bollinger_bands, atr, obv, mfi, cci, williams_r,
)


def _last(series: pl.Series):
    """Último valor no-nulo de la serie."""
    drop = series.drop_nulls()
    return drop[-1] if len(drop) > 0 else None


def analyze(df: pl.DataFrame) -> list[dict]:
    """
    Recibe un DataFrame con columnas: open, high, low, close, adj_close, volume.
    Calcula todos los indicadores y devuelve lista de señales.

    Cada señal:
        {"indicator": str, "signal": "buy"|"sell"|"neutral", "value": float, "note": str}
    """
    close  = df["adj_close"]
    high   = df["high"]
    low    = df["low"]
    volume = df["volume"].cast(pl.Float64)

    signals = []

    # ── RSI ───────────────────────────────────────────────────────────────
    rsi_val = _last(rsi(close, 14))
    if rsi_val is not None:
        if rsi_val < 30:
            sig = "buy";  note = f"RSI {rsi_val:.1f} — sobrevendido"
        elif rsi_val > 70:
            sig = "sell"; note = f"RSI {rsi_val:.1f} — sobrecomprado"
        else:
            sig = "neutral"; note = f"RSI {rsi_val:.1f} — zona neutral"
        signals.append({"indicator": "RSI(14)", "signal": sig, "value": round(rsi_val, 2), "note": note})

    # ── MACD ──────────────────────────────────────────────────────────────
    m = macd(close)
    macd_val  = _last(m["macd"])
    macd_sig  = _last(m["macd_signal"])
    macd_hist = _last(m["macd_hist"])
    if macd_val is not None and macd_sig is not None:
        if macd_val > macd_sig:
            sig = "buy";  note = f"MACD {macd_val:.3f} > Signal {macd_sig:.3f} — cruce alcista"
        else:
            sig = "sell"; note = f"MACD {macd_val:.3f} < Signal {macd_sig:.3f} — cruce bajista"
        signals.append({"indicator": "MACD(12,26,9)", "signal": sig, "value": round(macd_hist or 0, 3), "note": note})

    # ── SMA 50/200 (Golden/Death cross) ───────────────────────────────────
    sma50  = _last(sma(close, 50))
    sma200 = _last(sma(close, 200))
    price  = _last(close)
    if sma50 is not None and sma200 is not None and price is not None:
        if sma50 > sma200:
            sig = "buy";  note = f"SMA50 {sma50:.2f} > SMA200 {sma200:.2f} — golden cross"
        else:
            sig = "sell"; note = f"SMA50 {sma50:.2f} < SMA200 {sma200:.2f} — death cross"
        signals.append({"indicator": "SMA(50/200)", "signal": sig, "value": round(sma50, 2), "note": note})

    # ── Precio vs EMA 20 ──────────────────────────────────────────────────
    ema20 = _last(ema(close, 20))
    if ema20 is not None and price is not None:
        if price > ema20:
            sig = "buy";  note = f"Precio ${price:.2f} sobre EMA20 ${ema20:.2f}"
        else:
            sig = "sell"; note = f"Precio ${price:.2f} bajo EMA20 ${ema20:.2f}"
        signals.append({"indicator": "EMA(20)", "signal": sig, "value": round(ema20, 2), "note": note})

    # ── Bollinger Bands ───────────────────────────────────────────────────
    bb = bollinger_bands(close, 20)
    bb_upper = _last(bb["bb_upper"])
    bb_lower = _last(bb["bb_lower"])
    if bb_upper is not None and bb_lower is not None and price is not None:
        if price < bb_lower:
            sig = "buy";  note = f"Precio bajo la banda inferior (${bb_lower:.2f})"
        elif price > bb_upper:
            sig = "sell"; note = f"Precio sobre la banda superior (${bb_upper:.2f})"
        else:
            sig = "neutral"; note = f"Precio dentro de las bandas (${bb_lower:.2f} – ${bb_upper:.2f})"
        signals.append({"indicator": "Bollinger(20,2)", "signal": sig, "value": round(price, 2), "note": note})

    # ── Stochastic ────────────────────────────────────────────────────────
    stoch = stochastic(high, low, close)
    sk = _last(stoch["stoch_k"])
    sd = _last(stoch["stoch_d"])
    if sk is not None and sd is not None:
        if sk < 20 and sk > sd:
            sig = "buy";  note = f"Stoch K={sk:.1f} saliendo de zona sobrevendida"
        elif sk > 80 and sk < sd:
            sig = "sell"; note = f"Stoch K={sk:.1f} saliendo de zona sobrecomprada"
        else:
            sig = "neutral"; note = f"Stoch K={sk:.1f} D={sd:.1f}"
        signals.append({"indicator": "Stochastic(14,3,3)", "signal": sig, "value": round(sk, 2), "note": note})

    # ── MFI (Money Flow Index) ────────────────────────────────────────────
    mfi_val = _last(mfi(high, low, close, volume, 14))
    if mfi_val is not None:
        if mfi_val < 20:
            sig = "buy";  note = f"MFI {mfi_val:.1f} — flujo de dinero sobrevendido"
        elif mfi_val > 80:
            sig = "sell"; note = f"MFI {mfi_val:.1f} — flujo de dinero sobrecomprado"
        else:
            sig = "neutral"; note = f"MFI {mfi_val:.1f}"
        signals.append({"indicator": "MFI(14)", "signal": sig, "value": round(mfi_val, 2), "note": note})

    # ── ATR (volatilidad) ─────────────────────────────────────────────────
    atr_val = _last(atr(high, low, close, 14))
    if atr_val is not None and price is not None:
        atr_pct = atr_val / price * 100
        note = f"ATR {atr_val:.2f} ({atr_pct:.1f}% del precio) — volatilidad {'alta' if atr_pct > 3 else 'normal'}"
        signals.append({"indicator": "ATR(14)", "signal": "neutral", "value": round(atr_val, 2), "note": note})

    return signals


def summary(signals: list[dict]) -> dict:
    """
    Resume las señales en un consenso general.

    Devuelve:
        {"consensus": "buy"|"sell"|"neutral", "score": float, "buy": int, "sell": int, "neutral": int}
    """
    buys    = sum(1 for s in signals if s["signal"] == "buy")
    sells   = sum(1 for s in signals if s["signal"] == "sell")
    neutral = sum(1 for s in signals if s["signal"] == "neutral")
    total   = len(signals)

    score = (buys - sells) / total if total else 0  # -1.0 a 1.0

    if score > 0.2:
        consensus = "buy"
    elif score < -0.2:
        consensus = "sell"
    else:
        consensus = "neutral"

    return {
        "consensus": consensus,
        "score":     round(score, 2),
        "buy":       buys,
        "sell":      sells,
        "neutral":   neutral,
    }
