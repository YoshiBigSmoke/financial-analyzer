import "./Panel.css";
import "./EtfPanel.css";

// ── Tipos ──────────────────────────────────────────────────────────────────

interface EtfVerdict {
  score:   number;
  verdict: string;
  color:   "green" | "yellow" | "orange" | "red";
  notes:   string[];
}

interface EtfData {
  quote_type:          string;
  ticker:              string;
  name:                string;
  fund_family:         string | null;
  category:            string | null;
  legal_type:          string | null;
  aum:                 number | null;
  volume_avg:          number | null;
  dividend_yield:      number | null;
  expense_ratio:       number | null;
  cat_expense_ratio:   number | null;
  annual_cost_10k:     number | null;
  turnover:            number | null;
  valuation:           { pe: number | null; pb: number | null };
  performance:         { ytd: number | null; "3y": number | null; "5y": number | null; beta: number | null };
  holdings:            Array<{ symbol: string; name: string; weight: number }>;
  sectors:             Array<{ key: string; name: string; weight: number }>;
  asset_classes:       { stocks: number; bonds: number; cash: number; other: number };
  verdict:             EtfVerdict;
}

// ── Helpers ────────────────────────────────────────────────────────────────

const VERDICT_COLOR: Record<string, string> = {
  green:  "var(--green)",
  yellow: "var(--yellow)",
  orange: "#f97316",
  red:    "var(--red)",
};

function fmt(v: number | null | undefined, decimals = 2, suffix = ""): string {
  if (v == null) return "—";
  return `${v.toFixed(decimals)}${suffix}`;
}

function fmtAum(v: number | null): string {
  if (v == null) return "—";
  if (v >= 1e12) return `$${(v / 1e12).toFixed(2)}T`;
  if (v >= 1e9)  return `$${(v / 1e9).toFixed(1)}B`;
  if (v >= 1e6)  return `$${(v / 1e6).toFixed(0)}M`;
  return `$${v.toFixed(0)}`;
}

function fmtVol(v: number | null): string {
  if (v == null) return "—";
  if (v >= 1e6) return `${(v / 1e6).toFixed(1)}M`;
  if (v >= 1e3) return `${(v / 1e3).toFixed(0)}K`;
  return `${v}`;
}

// ── Mini bar horizontal ────────────────────────────────────────────────────

function Bar({ pct, color = "var(--accent)" }: { pct: number; color?: string }) {
  return (
    <div className="etf-bar-track">
      <div className="etf-bar-fill" style={{ width: `${Math.min(pct, 100)}%`, background: color }} />
    </div>
  );
}

// ── Colores por sector ─────────────────────────────────────────────────────

const SECTOR_COLORS: Record<string, string> = {
  technology:             "var(--purple)",
  communication_services: "var(--accent)",
  consumer_cyclical:      "var(--yellow)",
  consumer_defensive:     "#86efac",
  financial_services:     "#60a5fa",
  healthcare:             "#f472b6",
  industrials:            "#fb923c",
  energy:                 "#fbbf24",
  basic_materials:        "#a3e635",
  realestate:             "#818cf8",
  utilities:              "#94a3b8",
};

// ── Componente principal ──────────────────────────────────────────────────

export function EtfPanel({ data }: { data: EtfData }) {
  const vc = VERDICT_COLOR[data.verdict.color] ?? "var(--text-primary)";

  return (
    <div className="panel-grid">

      {/* ── Header ────────────────────────────────────────────── */}
      <div className="card span2">
        <div className="card-header">
          <h2 className="ticker">{data.ticker}</h2>
          <span className="company-name">{data.name}</span>
        </div>
        <div className="tags">
          {data.fund_family && <span className="tag">{data.fund_family}</span>}
          {data.category    && <span className="tag">{data.category}</span>}
          {data.legal_type  && <span className="tag">{data.legal_type}</span>}
        </div>
      </div>

      {/* ── Costo ─────────────────────────────────────────────── */}
      <div className="card">
        <div className="card-title">💰 Costo (Expense Ratio)</div>
        <div className="etf-cost-main">
          <span className="etf-cost-er mono"
            style={{ color: data.expense_ratio != null && data.expense_ratio < 0.2
              ? "var(--green)" : data.expense_ratio != null && data.expense_ratio > 0.6
              ? "var(--red)" : "var(--yellow)" }}>
            {fmt(data.expense_ratio, 2, "% / año")}
          </span>
        </div>
        <table className="ratio-table" style={{ marginTop: 10 }}>
          <tbody>
            <tr>
              <td>Promedio categoría</td>
              <td className="mono">{fmt(data.cat_expense_ratio, 2, "%")}</td>
            </tr>
            <tr>
              <td>Costo con $10,000</td>
              <td className="mono" style={{ color: "var(--accent)" }}>
                {data.annual_cost_10k != null ? `$${data.annual_cost_10k}/año` : "—"}
              </td>
            </tr>
            <tr>
              <td>Turnover cartera</td>
              <td className="mono">{fmt(data.turnover, 0, "%")}</td>
            </tr>
            <tr>
              <td>Dividend yield</td>
              <td className="mono">{fmt(data.dividend_yield, 2, "%")}</td>
            </tr>
          </tbody>
        </table>
      </div>

      {/* ── Tamaño y liquidez ─────────────────────────────────── */}
      <div className="card">
        <div className="card-title">🏦 Tamaño y Liquidez</div>
        <table className="ratio-table">
          <tbody>
            <tr>
              <td>AUM</td>
              <td className="mono" style={{ color: "var(--accent)" }}>{fmtAum(data.aum)}</td>
            </tr>
            <tr>
              <td>Volumen prom.</td>
              <td className="mono">{fmtVol(data.volume_avg)}</td>
            </tr>
            <tr>
              <td>P/E ponderado</td>
              <td className="mono">{fmt(data.valuation.pe)}</td>
            </tr>
            <tr>
              <td>P/B ponderado</td>
              <td className="mono">{fmt(data.valuation.pb)}</td>
            </tr>
          </tbody>
        </table>
      </div>

      {/* ── Retornos ──────────────────────────────────────────── */}
      <div className="card">
        <div className="card-title">📈 Retornos Anualizados</div>
        <table className="ratio-table">
          <tbody>
            {[
              ["YTD",        data.performance.ytd,    "%"],
              ["3 años",     data.performance["3y"],  "%/año"],
              ["5 años",     data.performance["5y"],  "%/año"],
              ["Beta (3Y)",  data.performance.beta,   ""],
            ].map(([label, val, suf]) => {
              const n = val as number | null;
              const color = n == null ? undefined
                : label === "Beta (3Y)" ? undefined
                : n >= 15 ? "var(--green)" : n >= 0 ? "var(--accent)" : "var(--red)";
              return (
                <tr key={String(label)}>
                  <td>{label}</td>
                  <td className="mono" style={{ color }}>
                    {n != null ? `${n > 0 && label !== "Beta (3Y)" ? "+" : ""}${n.toFixed(2)}${suf}` : "—"}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* ── Asset Allocation ──────────────────────────────────── */}
      <div className="card">
        <div className="card-title">🗂 Asset Allocation</div>
        <div className="etf-alloc-list">
          {([
            ["Acciones", data.asset_classes.stocks, "var(--accent)"],
            ["Bonos",    data.asset_classes.bonds,  "var(--purple)"],
            ["Cash",     data.asset_classes.cash,   "var(--yellow)"],
            ["Otros",    data.asset_classes.other,  "var(--text-muted)"],
          ] as [string, number, string][])
            .filter(([, v]) => v > 0)
            .map(([label, val, color]) => (
              <div key={label} className="etf-alloc-row">
                <span className="etf-alloc-label">{label}</span>
                <Bar pct={val} color={color} />
                <span className="etf-alloc-pct mono">{val.toFixed(1)}%</span>
              </div>
            ))}
        </div>
      </div>

      {/* ── Top Holdings ──────────────────────────────────────── */}
      <div className="card span2">
        <div className="card-title">🏢 Top Holdings</div>
        <div className="etf-holdings-list">
          {data.holdings.map(h => (
            <div key={h.symbol} className="etf-holding-row">
              <span className="etf-holding-symbol mono">{h.symbol}</span>
              <span className="etf-holding-name">{h.name}</span>
              <Bar pct={h.weight * 3} color="var(--purple-dim)" />
              <span className="etf-holding-pct mono">{h.weight.toFixed(2)}%</span>
            </div>
          ))}
        </div>
      </div>

      {/* ── Sectores ──────────────────────────────────────────── */}
      {data.sectors.length > 0 && (
        <div className="card span2">
          <div className="card-title">🌐 Exposición Sectorial</div>
          <div className="etf-sectors-list">
            {data.sectors.map(s => (
              <div key={s.key} className="etf-sector-row">
                <span className="etf-sector-name">{s.name}</span>
                <Bar pct={s.weight} color={SECTOR_COLORS[s.key] ?? "var(--accent)"} />
                <span className="etf-sector-pct mono">{s.weight.toFixed(1)}%</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Veredicto ─────────────────────────────────────────── */}
      <div className="card span2" style={{ borderColor: vc + "55" }}>
        <div className="card-title">⭐ Veredicto — {data.ticker}</div>
        <div className="etf-verdict-header">
          <span className="etf-verdict-badge mono" style={{ color: vc, borderColor: vc }}>
            {data.verdict.verdict.toUpperCase()}
          </span>
          <span className="etf-verdict-score text-muted">
            Score: <span className="mono" style={{ color: vc }}>{data.verdict.score}</span>
          </span>
        </div>
        <div className="etf-verdict-notes">
          {data.verdict.notes.map((n, i) => (
            <span key={i} className="etf-verdict-note">· {n}</span>
          ))}
        </div>
      </div>

    </div>
  );
}
