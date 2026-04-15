# Financial Analyzer

A desktop app for analyzing stocks — candlestick charts, fundamental metrics, technical indicators, and Monte Carlo simulations, all running locally on your machine with no API keys or subscriptions needed.

> **Heads up before you use this:** This is a research and exploration tool, not financial advice. The Monte Carlo projections show you a *range of possibilities* based on historical behavior — they're not predicting the future. Don't follow any number this app gives you as gospel. Use it to understand the probability space around a stock, ask better questions, and think in scenarios rather than certainties.

---

## What it does

You type in a ticker (AAPL, NVDA, TSLA, whatever) and the app runs four analyses back to back:

1. **Prices** — downloads up to 5 years of OHLCV data via yfinance and stores it locally in DuckDB so subsequent lookups are instant
2. **Fundamental** — P/E, P/B, profit margins, debt ratios, ROE, and a handful of other value metrics pulled from Yahoo Finance
3. **Technical** — SMA 20/50/200, Bollinger Bands, RSI, MACD, and a signal summary telling you where each indicator stands
4. **Quantitative** — runs 100,000 Monte Carlo simulations using Geometric Brownian Motion with GARCH(1,1) volatility clustering and an ARIMA drift component. The result is a probability cone showing where the price *could* be in the next 30–126 trading days

The chart is interactive: scroll wheel zooms in/out, the scrollbar pans left/right, and you get the MC cone overlaid directly on the candlesticks.

---

## Compatibility

This is where you should read carefully before trying to run it.

### Operating System

| Platform | Status | Notes |
|----------|--------|-------|
| **Linux** | ✅ Works | Developed and tested on Arch Linux with Wayland. Should work on any distro with WebKitGTK |
| **macOS** | ⚠️ Probably works | Tauri uses Safari's WebKit on Mac. The Python engine should work fine. Not tested. |
| **Windows** | ⚠️ Untested | Tauri uses WebView2 (Edge). Main concern is the Python subprocess IPC — may need path tweaks |

If you're on Linux, this should just work. Other platforms might need some adjustment in how the Rust backend spawns the Python process (`src-tauri/src/`).

### Required tools

You need all of these installed before you even try to build:

**Rust**
```
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
```
Any recent stable version works. The project was built with `rustc 1.94`.

**Node.js 18+**
Needed for the React frontend. Install via your package manager or [nvm](https://github.com/nvm-sh/nvm).

**Python 3.11+**
The analysis engine is entirely Python. Older versions might work but are untested.

**TA-Lib C library** (this one trips people up)
TA-Lib has a C core that needs to be installed at the system level before the Python wrapper:

```bash
# Arch / Manjaro
yay -S ta-lib

# Ubuntu / Debian
sudo apt install ta-lib

# macOS
brew install ta-lib

# Or build from source:
wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz
tar xzf ta-lib-0.4.0-src.tar.gz && cd ta-lib
./configure --prefix=/usr && make && sudo make install
```

**WebKitGTK** (Linux only)
```bash
# Arch
sudo pacman -S webkit2gtk-4.1

# Ubuntu / Debian
sudo apt install libwebkit2gtk-4.1-dev
```

---

## Setup

```bash
# 1. Clone
git clone https://github.com/yeoshua58/financial-analyzer.git
cd financial-analyzer

# 2. Python dependencies
pip install -r engine/requirements.txt

# 3. Node dependencies
npm install

# 4. Run in dev mode
npm run tauri dev
```

The first run will compile the Rust binary which takes a few minutes. Every run after that is instant.

To build a distributable binary:
```bash
npm run tauri build
```

---

## Project structure

```
financial-analyzer/
├── src/                    # React + TypeScript frontend
│   └── components/         # Chart, panels (Fundamental, Technical, Quant)
├── src-tauri/              # Rust shell (Tauri 2)
│   └── src/                # IPC bridge between UI and Python engine
├── engine/                 # Python analysis backend
│   ├── commands/           # fundamental.py, technical.py, quant.py
│   └── db/                 # DuckDB connection + schema
└── data/                   # Created at runtime — local DuckDB database
```

The data flow is: React UI → Tauri IPC → Rust → spawns Python subprocess → Python writes JSON to stdout → Rust forwards it back to the UI.

---

## Known limitations

- Data comes from Yahoo Finance via yfinance. If a ticker isn't on Yahoo Finance, it won't work.
- The app downloads data every time you analyze a ticker (subsequent runs use the local cache in DuckDB).
- 100k Monte Carlo simulations take a few seconds on most machines. This is intentional — fewer simulations give less accurate tails.
- Technical analysis signals are mechanical. They don't know about earnings, macro events, or news.

---

## Tech stack

- **Tauri 2** — desktop shell
- **React + TypeScript + Vite** — frontend
- **SVG** — charts rendered in pure SVG, no canvas library
- **Python** — analysis engine (numpy, scipy, statsmodels, TA-Lib, yfinance)
- **DuckDB** — local embedded database for price history
- **Polars** — DataFrames

---

*Built as a personal project for learning quantitative finance and desktop app development.*
