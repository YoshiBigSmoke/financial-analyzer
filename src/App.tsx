import { useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { useEngine } from "./hooks/useEngine";
import { FundamentalPanel } from "./components/FundamentalPanel";
import { TechnicalPanel }   from "./components/TechnicalPanel";
import { QuantPanel }       from "./components/QuantPanel";
import { ChartPage }        from "./components/ChartPage";
import { Spinner }          from "./components/Spinner";
import "./App.css";

type Page = "chart" | "fundamental" | "technical" | "quant" | "watchlist";

const NAV: { id: Page; label: string; emoji: string }[] = [
  { id: "chart",       label: "Gráfica",       emoji: "📈" },
  { id: "fundamental", label: "Fundamental",   emoji: "💎" },
  { id: "technical",   label: "Técnico",       emoji: "📊" },
  { id: "quant",       label: "Cuantitativo",  emoji: "🔮" },
  { id: "watchlist",   label: "Watchlist",     emoji: "⭐" },
];

export default function App() {
  const [ticker,      setTicker]      = useState("");
  const [inputVal,    setInputVal]    = useState("");
  const [page,        setPage]        = useState<Page>("fundamental");
  const [loadMsg,     setLoadMsg]     = useState<string | null>(null);
  const [backendOk,   setBackendOk]   = useState<boolean | null>(null);

  const fundamental = useEngine();
  const technical   = useEngine();
  const quant       = useEngine();
  const prices      = useEngine<unknown[]>();

  // ── Ping de prueba ──────────────────────────────────────────
  async function handlePing() {
    try {
      const r = await invoke<string>("ping");
      setBackendOk(r === "pong");
    } catch {
      setBackendOk(false);
    }
  }

  // ── Carga y análisis del ticker ─────────────────────────────
  async function handleAnalyze() {
    const t = inputVal.trim().toUpperCase();
    if (!t) return;
    setTicker(t);
    setPage("chart");
    setLoadMsg(`✨ Buscando ${t} en los mercados...`);

    // 1. Descargar datos
    try {
      await invoke("run_engine", { command: "load_ticker", args: { ticker: t, period: "5y" } });
    } catch (e) {
      setLoadMsg(`Error al cargar: ${e}`);
      return;
    }

    // 2. Análisis secuencial — DuckDB no permite múltiples escritores simultáneos
    setLoadMsg(`📈 Cargando precios de ${t}...`);
    await prices.call("prices", { ticker: t });

    setLoadMsg(`💎 Analizando fundamentos de ${t}...`);
    await fundamental.call("fundamental", { ticker: t });

    setLoadMsg(`📊 Calculando señales técnicas...`);
    await technical.call("technical", { ticker: t });

    setLoadMsg(`🔮 Corriendo 100k simulaciones Monte Carlo...`);
    await quant.call("quant", { ticker: t, horizon: 126, simulations: 100_000 });

    setLoadMsg(null);
  }

  // ── Estado de carga global ──────────────────────────────────
  const isLoading = loadMsg !== null;

  function renderContent() {
    if (isLoading) return <Spinner label={loadMsg ?? "Cargando..."} />;

    if (page === "chart") {
      if (prices.status === "error") return <div className="error-box">{prices.error}</div>;
      if (!prices.data)              return ticker ? <Spinner /> : null;
      return (
        <ChartPage
          prices={prices.data as never}
          quantData={quant.data as never}
          ticker={ticker}
        />
      );
    }

    if (!ticker) {
      return (
        <div className="placeholder">
          <div className="placeholder-emoji">🔭</div>
          <p>Ingresa un ticker para analizar</p>
          <p className="text-muted" style={{ fontSize: 13 }}>busca cualquier acción del mercado</p>
          <div className="placeholder-tickers">
            {["AAPL", "MSFT", "GOOGL", "NVDA", "TSLA", "AMZN"].map(t => (
              <span key={t} className="placeholder-ticker-chip">{t}</span>
            ))}
          </div>
        </div>
      );
    }

    if (page === "fundamental") {
      if (fundamental.status === "error") return <div className="error-box">{fundamental.error}</div>;
      if (!fundamental.data)             return <Spinner />;
      return <FundamentalPanel data={fundamental.data as never} />;
    }

    if (page === "technical") {
      if (technical.status === "error") return <div className="error-box">{technical.error}</div>;
      if (!technical.data)              return <Spinner />;
      return <TechnicalPanel data={technical.data as never} />;
    }

    if (page === "quant") {
      if (quant.status === "error") return <div className="error-box">{quant.error}</div>;
      if (!quant.data)              return <Spinner />;
      return <QuantPanel data={quant.data as never} />;
    }

    if (page === "watchlist") {
      return (
        <div className="placeholder">
          <div className="placeholder-emoji">⭐</div>
          <p>Watchlist — próximamente</p>
          <p className="text-muted" style={{ fontSize: 13 }}>aquí irán tus acciones favoritas</p>
        </div>
      );
    }

    return null;
  }

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="logo">
          <span className="logo-icon">🌸</span>
          <span className="logo-text">FinAnalyzer</span>
        </div>
        <nav className="nav">
          {NAV.map(({ id, label, emoji }) => (
            <button
              key={id}
              className={`nav-item ${page === id ? "active" : ""}`}
              onClick={() => setPage(id)}
              disabled={!ticker && !isLoading}
            >
              <span>{emoji}</span>
              <span>{label}</span>
            </button>
          ))}
        </nav>

        <div className="sidebar-footer">
          <button className="btn-ghost small" onClick={handlePing}>
            {backendOk === null  ? "● Backend"
            : backendOk          ? "● Backend OK"
            : "● Backend error"}
          </button>
          {backendOk !== null && (
            <span style={{ fontSize: 11, color: backendOk ? "var(--green)" : "var(--red)" }}>
              {backendOk ? "Rust activo" : "Sin conexión"}
            </span>
          )}
        </div>
      </aside>

      <main className="main">
        <header className="topbar">
          <div className="search-wrap">
            <input
              className="search"
              placeholder="Ticker... AAPL, MSFT, NVDA"
              value={inputVal}
              disabled={isLoading}
              onChange={e => setInputVal(e.target.value.toUpperCase())}
              onKeyDown={e => e.key === "Enter" && handleAnalyze()}
            />
            <button
              className="btn-primary"
              disabled={isLoading || !inputVal.trim()}
              onClick={handleAnalyze}
            >
              {isLoading ? "Cargando..." : "Analizar"}
            </button>
          </div>
          {ticker && !isLoading && (
            <span className="topbar-ticker mono text-accent">{ticker}</span>
          )}
        </header>

        <section className={`content ${page !== "chart" ? "scrollable" : ""}`}>
          {renderContent()}
        </section>
      </main>
    </div>
  );
}
