/**
 * Datos de prueba para modo navegador (sin Tauri).
 * Se usan cuando la app corre con `npm run dev` en el browser.
 * Los datos son reales de VOO y AAPL obtenidos del engine.
 */

const MOCK_TICKER = "VOO";

// ── Fundamental (ETF) ──────────────────────────────────────────────────────
const MOCK_FUNDAMENTAL_ETF = {
  quote_type:     "ETF",
  ticker:         "VOO",
  name:           "Vanguard S&P 500 ETF",
  fund_family:    "Vanguard",
  category:       "Large Blend",
  legal_type:     "Exchange Traded Fund",
  inception_date: "2000-11-12",
  index_tracked:  null,
  aum:            1600156336128,
  volume_avg:     9455369,
  price:          687.73,
  nav:            682.43,
  premium_discount: 0.777,
  week52_high:    689.10,
  week52_low:     529.11,
  dividend_yield: 1.08,
  expense_ratio:  0.03,
  cat_expense_ratio: 0.72176997,
  annual_cost_10k: 3.0,
  turnover:       2.0,
  valuation: { pe: 29.69, pb: 1.76 },
  performance: { ytd: 5.69, "1y": null, "3y": 23.4, "5y": 14.2, beta: 1.0 },
  holdings: [
    { symbol: "NVDA", name: "NVIDIA Corp",           weight: 7.58 },
    { symbol: "AAPL", name: "Apple Inc",              weight: 6.67 },
    { symbol: "MSFT", name: "Microsoft Corp",         weight: 4.92 },
    { symbol: "AMZN", name: "Amazon.com Inc",         weight: 3.64 },
    { symbol: "GOOGL", name: "Alphabet Inc Class A",  weight: 3.00 },
    { symbol: "AVGO", name: "Broadcom Inc",           weight: 2.63 },
    { symbol: "GOOG", name: "Alphabet Inc Class C",   weight: 2.40 },
    { symbol: "META", name: "Meta Platforms Inc",     weight: 2.24 },
    { symbol: "TSLA", name: "Tesla Inc",              weight: 1.87 },
    { symbol: "BRK-B", name: "Berkshire Hathaway B", weight: 1.57 },
  ],
  sectors: [
    { key: "technology",             name: "Tecnología",              weight: 33.62 },
    { key: "financial_services",     name: "Servicios Financieros",   weight: 12.21 },
    { key: "communication_services", name: "Comunicaciones",          weight: 10.50 },
    { key: "consumer_cyclical",      name: "Consumo Discrecional",    weight: 10.02 },
    { key: "healthcare",             name: "Salud",                   weight:  9.48 },
    { key: "industrials",            name: "Industriales",            weight:  8.48 },
    { key: "consumer_defensive",     name: "Consumo Básico",          weight:  5.26 },
    { key: "energy",                 name: "Energía",                 weight:  4.02 },
    { key: "utilities",              name: "Utilities",               weight:  2.55 },
    { key: "realestate",             name: "Bienes Raíces",           weight:  1.95 },
    { key: "basic_materials",        name: "Materiales",              weight:  1.91 },
  ],
  asset_classes: { stocks: 99.86, bonds: 0.0, cash: -0.03, other: 0.17 },
  alternatives: ["IVV (0.03%)", "SPY (0.09%)"],
  verdict: {
    score:   8,
    verdict: "Excelente",
    color:   "green",
    notes: [
      "Costo muy por debajo de categoría: 0.03% vs promedio 0.72%",
      "Fondo muy grande ($1600B) — spread mínimo, máxima liquidez",
      "Retorno 3Y anualizado excepcional: +23.4%",
      "Rotación muy baja (2%) — eficiente y tax-friendly",
      "Paga dividendo: 1.08% anual",
    ],
  },
};

// ── Precios (últimas 10 velas de muestra) ──────────────────────────────────
const MOCK_PRICES = Array.from({ length: 60 }, (_, i) => {
  const base = 650 + i * 0.6;
  const noise = (Math.sin(i * 0.8) * 8) + (Math.cos(i * 0.3) * 5);
  const open  = parseFloat((base + noise).toFixed(2));
  const close = parseFloat((open + (Math.random() - 0.48) * 6).toFixed(2));
  const high  = parseFloat((Math.max(open, close) + Math.random() * 3).toFixed(2));
  const low   = parseFloat((Math.min(open, close) - Math.random() * 3).toFixed(2));
  const date  = new Date(2025, 0, 1 + i).toISOString().slice(0, 10);
  return { date, open, high, low, adj_close: close, volume: Math.floor(8e6 + Math.random() * 4e6) };
});

// ── Técnico ────────────────────────────────────────────────────────────────
const MOCK_TECHNICAL = {
  signals: [
    { name: "SMA 20",        value: "692.40", signal: "BUY",     strength: 0.8 },
    { name: "SMA 50",        value: "678.10", signal: "BUY",     strength: 0.7 },
    { name: "SMA 200",       value: "641.80", signal: "BUY",     strength: 0.9 },
    { name: "RSI (14)",      value: "58.3",   signal: "NEUTRAL",  strength: 0.5 },
    { name: "MACD",          value: "3.21",   signal: "BUY",     strength: 0.6 },
    { name: "Bollinger",     value: "mid",    signal: "NEUTRAL",  strength: 0.5 },
    { name: "Stochastic",    value: "62.1",   signal: "NEUTRAL",  strength: 0.4 },
    { name: "ATR (14)",      value: "8.42",   signal: "NEUTRAL",  strength: 0.5 },
  ],
  consensus: { signal: "BUY", buy: 4, neutral: 4, sell: 0, strength: 0.68 },
};

// ── Cuantitativo ───────────────────────────────────────────────────────────
const _cone = Array.from({ length: 30 }, (_, i) => 687.73 + i * 0.6);
const MOCK_QUANT = {
  ticker:        "VOO",
  current_price: 687.73,
  horizon:       126,
  garch: {
    params:      { mu: 0.12, omega: 0.03, "alpha[1]": 0.09, "beta[1]": 0.89, nu: 8.5 },
    persistence: 0.98,
    half_life:   50.2,
    aic:         4100.0,
    forecast: {
      horizon:    30,
      avg_daily:  0.95,
      avg_annual: 15.1,
      daily_vol:  Array.from({ length: 30 }, () => 0.95),
      annual_vol: Array.from({ length: 30 }, () => 15.1),
    },
  },
  monte_carlo: {
    current_price:  687.73,
    horizon:        126,
    simulations:    100000,
    expected_price: 718.40,
    mean_price:     725.10,
    std_price:      95.30,
    var_5:          572.10,
    var_1:          530.20,
    cvar_5:         548.80,
    prob_above:     0.68,
    prob_below:     0.32,
    daily_vol_pct:  0.95,
    drift_pct:      0.055,
    percentiles:    { "1": 530, "5": 572, "10": 600, "25": 650, "50": 718, "75": 790, "90": 860, "95": 910, "99": 1010 },
    scenarios: [
      { key: "muy_alcista", label: "Muy alcista", icon: "🚀", range: "> +20%",        prob: 0.18, avg_price: 870 },
      { key: "alcista",     label: "Alcista",     icon: "📈", range: "+5% a +20%",    prob: 0.32, avg_price: 760 },
      { key: "lateral",     label: "Lateral",     icon: "➡️", range: "−5% a +5%",    prob: 0.28, avg_price: 692 },
      { key: "bajista",     label: "Bajista",     icon: "📉", range: "−20% a −5%",   prob: 0.18, avg_price: 620 },
      { key: "muy_bajista", label: "Muy bajista", icon: "☠️", range: "< −20%",        prob: 0.04, avg_price: 530 },
    ],
    most_probable: "alcista",
  },
  cone: {
    p5:  _cone.map(v => parseFloat((v * 0.90).toFixed(2))),
    p25: _cone.map(v => parseFloat((v * 0.96).toFixed(2))),
    p50: _cone,
    p75: _cone.map(v => parseFloat((v * 1.04).toFixed(2))),
    p95: _cone.map(v => parseFloat((v * 1.11).toFixed(2))),
  },
  arima: {
    order:  [0, 0, 3],
    aic:    4300.0,
    adf:    { statistic: -21.5, p_value: 0.0, stationary: true },
    returns: {
      horizon:          30,
      forecast_returns: Array(30).fill(0.065),
      forecast_cum:     Array.from({ length: 30 }, (_, i) => parseFloat((i * 0.065).toFixed(3))),
      conf_int_lower:   Array(30).fill(-2.6),
      conf_int_upper:   Array(30).fill(2.8),
      order:            [0, 0, 3],
      aic:              4300.0,
    },
    prices: {
      prices:       _cone,
      prices_lower: _cone.map(v => parseFloat((v * 0.60).toFixed(2))),
      prices_upper: _cone.map(v => parseFloat((v * 1.50).toFixed(2))),
    },
  },
};

// ── Macro ──────────────────────────────────────────────────────────────────
const MOCK_MACRO = {
  label:        "Expansión moderada",
  summary:      "Indicadores macro muestran crecimiento sostenido con inflación controlada.",
  signals: [
    { id: "DFF",    name: "Fed Funds Rate",    value: "5.33%",  status: "warning", note: "Tasas elevadas presionan valuaciones" },
    { id: "CPIAUCSL", name: "CPI YoY",         value: "3.1%",   status: "warning", note: "Inflación sobre objetivo del 2%" },
    { id: "UNRATE", name: "Desempleo",         value: "3.9%",   status: "ok",      note: "Mercado laboral sólido" },
    { id: "GDP",    name: "GDP Growth",        value: "2.5%",   status: "ok",      note: "Crecimiento saludable" },
  ],
  etfs: [
    { ticker: "VOO", reason: "S&P500 amplio — exposición core al mercado americano" },
    { ticker: "BND",  reason: "Bonos diversificados — cobertura ante volatilidad" },
    { ticker: "GLD",  reason: "Oro — refugio ante inflación persistente" },
  ],
  last_updated: new Date().toISOString(),
  fetch_errors: {},
};

// ── Dispatcher ─────────────────────────────────────────────────────────────
export function getMockData(command: string, args: Record<string, unknown>): unknown {
  const ticker = (args.ticker as string | undefined)?.toUpperCase() ?? MOCK_TICKER;
  void ticker; // todos los tickers devuelven datos de VOO en modo preview

  switch (command) {
    case "load_ticker":   return { ticker, loaded: true };
    case "fundamental":   return MOCK_FUNDAMENTAL_ETF;
    case "prices":        return MOCK_PRICES;
    case "technical":     return MOCK_TECHNICAL;
    case "quant":         return MOCK_QUANT;
    case "watchlist":     return [];
    case "add_watchlist": return { added: ticker };
    case "macro":         return MOCK_MACRO;
    default:              return {};
  }
}
