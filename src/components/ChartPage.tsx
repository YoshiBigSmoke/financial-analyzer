import { PriceChart } from "./PriceChart";
import "./ChartPage.css";

interface PriceRow {
  date: string; open: number; high: number; low: number; adj_close: number; volume: number;
}
interface Props {
  prices:      PriceRow[];
  quantData?:  Record<string, unknown> | null;
  ticker:      string;
}

function fmtVol(v: number): string {
  if (v >= 1e9) return `${(v / 1e9).toFixed(2)}B`;
  if (v >= 1e6) return `${(v / 1e6).toFixed(2)}M`;
  if (v >= 1e3) return `${(v / 1e3).toFixed(1)}K`;
  return String(v);
}

export function ChartPage({ prices, quantData, ticker }: Props) {
  if (prices.length === 0) {
    return <div style={{ color: "var(--text-muted)", padding: 24 }}>Sin datos de precios.</div>;
  }

  const last    = prices[prices.length - 1];
  const prev    = prices[prices.length - 2];
  const change  = last.adj_close - prev.adj_close;
  const changePct = (change / prev.adj_close) * 100;
  const isUp    = change >= 0;

  // High/Low de los últimos 52 semanas (~252 sesiones)
  const last252 = prices.slice(-252);
  const high52  = Math.max(...last252.map(p => p.high));
  const low52   = Math.min(...last252.map(p => p.low));

  // Cone del Monte Carlo si está disponible
  const cone    = quantData?.cone as { p5: number[]; p25: number[]; p50: number[]; p75: number[]; p95: number[] } | undefined;
  const horizon = quantData?.horizon as number | undefined;

  // Bandas d15 / d30 — extraídas del cone MC
  const band15  = cone ? { lo: cone.p25[14], mid: cone.p50[14], hi: cone.p75[14] } : null;
  const band30  = cone ? { lo: cone.p25[29], mid: cone.p50[29], hi: cone.p75[29] } : null;

  return (
    <div className="chart-page">
      {/* ── Strip de precio ─────────────────────────────────── */}
      <div className="price-strip">
        <div className="price-main">
          <span className="price-ticker mono">{ticker}</span>
          <span className="price-value mono">${last.adj_close.toFixed(2)}</span>
          <span className={`price-change mono ${isUp ? "text-green" : "text-red"}`}>
            {isUp ? "▲" : "▼"} {Math.abs(change).toFixed(2)} ({Math.abs(changePct).toFixed(2)}%)
          </span>
          <span className="text-muted price-date">{last.date}</span>
        </div>
        <div className="price-stats">
          <div className="stat">
            <span className="stat-label">Apertura</span>
            <span className="stat-value mono">${last.open.toFixed(2)}</span>
          </div>
          <div className="stat">
            <span className="stat-label">Máximo</span>
            <span className="stat-value mono text-green">${last.high.toFixed(2)}</span>
          </div>
          <div className="stat">
            <span className="stat-label">Mínimo</span>
            <span className="stat-value mono text-red">${last.low.toFixed(2)}</span>
          </div>
          <div className="stat">
            <span className="stat-label">Volumen</span>
            <span className="stat-value mono">{fmtVol(last.volume)}</span>
          </div>
          <div className="stat">
            <span className="stat-label">52W High</span>
            <span className="stat-value mono text-green">${high52.toFixed(2)}</span>
          </div>
          <div className="stat">
            <span className="stat-label">52W Low</span>
            <span className="stat-value mono text-red">${low52.toFixed(2)}</span>
          </div>
          {band15 && (
            <div className="stat stat-band">
              <span className="stat-label">🎯 Banda d15</span>
              <span className="stat-value mono" style={{ display: "flex", flexDirection: "column", gap: 1 }}>
                <span className="text-green"  style={{ fontSize: 11 }}>↑ ${band15.hi.toFixed(2)}</span>
                <span className="text-accent" style={{ fontSize: 12, fontWeight: 700 }}>${band15.mid.toFixed(2)}</span>
                <span className="text-red"    style={{ fontSize: 11 }}>↓ ${band15.lo.toFixed(2)}</span>
              </span>
            </div>
          )}
          {band30 && (
            <div className="stat stat-band">
              <span className="stat-label">🔭 Banda d30</span>
              <span className="stat-value mono" style={{ display: "flex", flexDirection: "column", gap: 1 }}>
                <span className="text-green"  style={{ fontSize: 11 }}>↑ ${band30.hi.toFixed(2)}</span>
                <span className="text-accent" style={{ fontSize: 12, fontWeight: 700 }}>${band30.mid.toFixed(2)}</span>
                <span className="text-red"    style={{ fontSize: 11 }}>↓ ${band30.lo.toFixed(2)}</span>
              </span>
            </div>
          )}
        </div>
      </div>

      {/* ── Gráfica ─────────────────────────────────────────── */}
      <div className="chart-wrap">
        <PriceChart
          prices={prices}
          cone={cone}
          horizon={horizon}
        />
      </div>
    </div>
  );
}
