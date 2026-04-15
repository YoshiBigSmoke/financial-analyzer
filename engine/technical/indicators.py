"""
Indicadores técnicos usando TA-Lib (C internamente).

Grupos cubiertos:
  - Tendencia  : SMA, EMA, MACD
  - Momentum   : RSI, Stochastic, CCI, Williams %R
  - Volatilidad: Bollinger Bands, ATR
  - Volumen    : OBV, MFI
"""

import numpy as np
import talib
import polars as pl


# ── Helpers ───────────────────────────────────────────────────────────────

def _to_np(series: pl.Series) -> np.ndarray:
    """Convierte Polars Series a numpy float64 (lo que necesita TA-Lib)."""
    return series.cast(pl.Float64).to_numpy()


# ── Tendencia ─────────────────────────────────────────────────────────────

def sma(close: pl.Series, period: int = 20) -> pl.Series:
    """Simple Moving Average."""
    result = talib.SMA(_to_np(close), timeperiod=period)
    return pl.Series(f"sma_{period}", result)


def ema(close: pl.Series, period: int = 20) -> pl.Series:
    """Exponential Moving Average."""
    result = talib.EMA(_to_np(close), timeperiod=period)
    return pl.Series(f"ema_{period}", result)


def macd(
    close: pl.Series,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> dict[str, pl.Series]:
    """
    MACD → devuelve dict con:
      macd, macd_signal, macd_hist
    """
    m, s, h = talib.MACD(_to_np(close), fastperiod=fast, slowperiod=slow, signalperiod=signal)
    return {
        "macd":        pl.Series("macd", m),
        "macd_signal": pl.Series("macd_signal", s),
        "macd_hist":   pl.Series("macd_hist", h),
    }


# ── Momentum ──────────────────────────────────────────────────────────────

def rsi(close: pl.Series, period: int = 14) -> pl.Series:
    """Relative Strength Index."""
    result = talib.RSI(_to_np(close), timeperiod=period)
    return pl.Series(f"rsi_{period}", result)


def stochastic(
    high: pl.Series,
    low: pl.Series,
    close: pl.Series,
    fastk: int = 14,
    slowk: int = 3,
    slowd: int = 3,
) -> dict[str, pl.Series]:
    """
    Stochastic Oscillator → devuelve dict con:
      stoch_k, stoch_d
    """
    k, d = talib.STOCH(
        _to_np(high), _to_np(low), _to_np(close),
        fastk_period=fastk, slowk_period=slowk, slowd_period=slowd,
    )
    return {
        "stoch_k": pl.Series("stoch_k", k),
        "stoch_d": pl.Series("stoch_d", d),
    }


def cci(
    high: pl.Series,
    low: pl.Series,
    close: pl.Series,
    period: int = 20,
) -> pl.Series:
    """Commodity Channel Index."""
    result = talib.CCI(_to_np(high), _to_np(low), _to_np(close), timeperiod=period)
    return pl.Series(f"cci_{period}", result)


def williams_r(
    high: pl.Series,
    low: pl.Series,
    close: pl.Series,
    period: int = 14,
) -> pl.Series:
    """Williams %R."""
    result = talib.WILLR(_to_np(high), _to_np(low), _to_np(close), timeperiod=period)
    return pl.Series(f"willr_{period}", result)


# ── Volatilidad ───────────────────────────────────────────────────────────

def bollinger_bands(
    close: pl.Series,
    period: int = 20,
    nbdev: float = 2.0,
) -> dict[str, pl.Series]:
    """
    Bollinger Bands → devuelve dict con:
      bb_upper, bb_middle, bb_lower
    """
    upper, middle, lower = talib.BBANDS(
        _to_np(close), timeperiod=period, nbdevup=nbdev, nbdevdn=nbdev,
    )
    return {
        "bb_upper":  pl.Series("bb_upper", upper),
        "bb_middle": pl.Series("bb_middle", middle),
        "bb_lower":  pl.Series("bb_lower", lower),
    }


def atr(
    high: pl.Series,
    low: pl.Series,
    close: pl.Series,
    period: int = 14,
) -> pl.Series:
    """Average True Range — mide volatilidad absoluta."""
    result = talib.ATR(_to_np(high), _to_np(low), _to_np(close), timeperiod=period)
    return pl.Series(f"atr_{period}", result)


# ── Volumen ───────────────────────────────────────────────────────────────

def obv(close: pl.Series, volume: pl.Series) -> pl.Series:
    """On-Balance Volume."""
    result = talib.OBV(_to_np(close), _to_np(volume).astype(float))
    return pl.Series("obv", result)


def mfi(
    high: pl.Series,
    low: pl.Series,
    close: pl.Series,
    volume: pl.Series,
    period: int = 14,
) -> pl.Series:
    """Money Flow Index — RSI con volumen."""
    result = talib.MFI(
        _to_np(high), _to_np(low), _to_np(close),
        _to_np(volume).astype(float),
        timeperiod=period,
    )
    return pl.Series(f"mfi_{period}", result)
