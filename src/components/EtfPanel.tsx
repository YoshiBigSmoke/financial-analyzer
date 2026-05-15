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
  inception_date:      string | null;
  index_tracked:       string | null;
  aum:                 number | null;
  volume_avg:          number | null;
  price:               number | null;
  nav:                 number | null;
  premium_discount:    number | null;
  week52_high:         number | null;
  week52_low:          number | null;
  dividend_yield:      number | null;
  expense_ratio:       number | null;
  cat_expense_ratio:   number | null;
  annual_cost_10k:     number | null;
  turnover:            number | null;
  valuation:           { pe: number | null; pb: number | null };
  performance:         { ytd: number | null; "1y": number | null; "3y": number | null; "5y": number | null; beta: number | null };
  holdings:            Array<{ symbol: string; name: string; weight: number }>;
  sectors:             Array<{ key: string; name: string; weight: number }>;
  asset_classes:       { stocks: number; bonds: number; cash: number; other: number };
  alternatives:        string[] | null;
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

function fmtPrice(v: number | null): string {
  if (v == null) return "—";
  return `$${v.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
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

function fmtReturn(v: number | null, label?: string): React.ReactNode {
  if (v == null) return <span style={{ color: "var(--text-muted)" }}>—</span>;
  const isBeta = label === "Beta";
  const color = isBeta ? undefined : v >= 15 ? "var(--green)" : v >= 0 ? "var(--accent)" : "var(--red)";
  const sign  = !isBeta && v > 0 ? "+" : "";
  const suffix = isBeta ? "" : "%";
  return <span className="mono" style={{ color }}>{sign}{v.toFixed(2)}{suffix}</span>;
}

// ── Sub-components ─────────────────────────────────────────────────────────

function Bar({ pct, color = "var(--accent)", max = 100 }: { pct: number; color?: string; max?: number }) {
  return (
    <div className="etf-bar-track">
      <div className="etf-bar-fill" style={{ width: `${Math.min((pct / max) * 100, 100)}%`, background: color }} />
    </div>
  );
}

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

  // 52-week position (0-100%)
  const w52pos = (data.price && data.week52_low && data.week52_high && data.week52_high > data.week52_low)
    ? ((data.price - data.week52_low) / (data.week52_high - data.week52_low)) * 100
    : null;

  return (
    <div className="panel-grid">

      {/* ── Header ────────────────────────────────────────────── */}
      <div className="card span2">
        <div className="etf-header-row">
          <div>
            <div className="card-header">
              <h2 className="ticker">{data.ticker}</h2>
              <span className="company-name">{data.name}</span>
            </div>
            <div className="tags" style={{ marginTop: 6 }}>
              {data.fund_family  && <span className="tag">{data.fund_family}</span>}
              {data.category     && <span className="tag">{data.category}</span>}
              {data.legal_type   && <span className="tag">{data.legal_type}</span>}
              {data.inception_date && <span className="tag">Desde {data.inception_date.slice(0, 4)}</span>}
            </div>
            {data.index_tracked && (
              <p className="etf-index-label">Sigue: <span className="mono">{data.index_tracked}</span></p>
            )}
          </div>

          {/* Precio grande */}
          <div className="etf-price-block">
            <div className="etf-price-main">{fmtPrice(data.price)}</div>
            {data.nav && (
              <div className="etf-nav-row">
                <span className="text-muted">NAV {fmtPrice(data.nav)}</span>
                {data.premium_discount != null && (
                  <span className="mono" style={{
                    color: Math.abs(data.premium_discount) < 0.1 ? "var(--green)"
                         : data.premium_discount > 0 ? "var(--yellow)" : "var(--accent)",
                    fontSize: 12, marginLeft: 8,
                  }}>
                    {data.premium_discount > 0 ? "+" : ""}{data.premium_discount.toFixed(3)}%
                    {Math.abs(data.premium_discount) < 0.1 ? " par" : data.premium_discount > 0 ? " prima" : " descuento"}
                  </span>
                )}
              </div>
            )}
          </div>
        </div>

        {/* 52-week range */}
        {data.week52_low != null && data.week52_high != null && (
          <div className="etf-52w-wrap">
            <span className="text-muted" style={{ fontSize: 12 }}>52s: {fmtPrice(data.week52_low)}</span>
            <div className="etf-52w-track">
              {w52pos != null && (
                <div className="etf-52w-thumb" style={{ left: `calc(${w52pos.toFixed(1)}% - 6px)` }} />
              )}
              <div className="etf-52w-fill" style={{ width: `${w52pos?.toFixed(1) ?? 50}%` }} />
            </div>
            <span className="text-muted" style={{ fontSize: 12 }}>{fmtPrice(data.week52_high)}</span>
            {w52pos != null && (
              <span className="mono" style={{ fontSize: 11, color: "var(--text-muted)", marginLeft: 8 }}>
                {w52pos.toFixed(0)}% del rango
              </span>
            )}
          </div>
        )}
      </div>

      {/* ── Costo ─────────────────────────────────────────────── */}
      <div className="card">
        <div className="card-title">💰 Costo</div>
        <div className="etf-cost-main">
          <span className="etf-cost-er mono"
            style={{ color: data.expense_ratio != null && data.expense_ratio < 0.15
              ? "var(--green)" : data.expense_ratio != null && data.expense_ratio > 0.60
              ? "var(--red)" : "var(--yellow)" }}>
            {fmt(data.expense_ratio, 2, "% / año")}
          </span>
        </div>
        <table className="ratio-table" style={{ marginTop: 8 }}>
          <tbody>
            <tr>
              <td>Promedio categoría</td>
              <td className="mono">{fmt(data.cat_expense_ratio, 2, "%")}</td>
            </tr>
            <tr>
              <td>Con $10,000 invertidos</td>
              <td className="mono" style={{ color: "var(--accent)" }}>
                {data.annual_cost_10k != null ? `$${data.annual_cost_10k}/año` : "—"}
              </td>
            </tr>
            <tr>
              <td>Rotación cartera</td>
              <td className="mono">{data.turnover != null ? `${data.turnover.toFixed(0)}%` : "—"}</td>
            </tr>
            <tr>
              <td>Dividend yield</td>
              <td className="mono">{fmt(data.dividend_yield, 2, "%")}</td>
            </tr>
          </tbody>
        </table>

        {data.alternatives && data.alternatives.length > 0 && (
          <div className="etf-alts-block">
            <span className="etf-alts-label">Alternativas similares</span>
            <div className="etf-alts-list">
              {data.alternatives.map(a => (
                <span key={a} className="etf-alt-chip mono">{a}</span>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* ── Retornos ──────────────────────────────────────────── */}
      <div className="card">
        <div className="card-title">📈 Retornos</div>
        <table className="ratio-table">
          <tbody>
            {([
              ["YTD",       data.performance.ytd],
              ["1 año",     data.performance["1y"]],
              ["3 años",    data.performance["3y"]],
              ["5 años",    data.performance["5y"]],
              ["Beta (3Y)", data.performance.beta],
            ] as [string, number | null][]).map(([label, val]) => (
              <tr key={label}>
                <td>{label}</td>
                <td>{fmtReturn(val, label)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* ── Análisis de Valor ─────────────────────────────────── */}
      {(() => {
        const netYield =
          data.dividend_yield != null && data.expense_ratio != null
            ? parseFloat((data.dividend_yield - data.expense_ratio).toFixed(2))
            : null;

        const pe = data.valuation.pe;
        const peLabel =
          pe == null ? null
          : pe < 20  ? "barato vs mercado"
          : pe < 28  ? "en línea con mercado"
          :             "caro vs mercado";
        const peColor =
          pe == null ? undefined
          : pe < 20  ? "var(--green)"
          : pe < 28  ? "var(--accent)"
          :             "var(--red)";

        const pd = data.premium_discount;
        const pdColor =
          pd == null           ? undefined
          : Math.abs(pd) < 0.1 ? "var(--green)"
          : pd > 0             ? "var(--yellow)"
          :                      "var(--accent)";

        let valueLabel = "";
        let valueNote  = "";
        if (pe != null && pd != null) {
          if (pe < 22 && Math.abs(pd) < 0.15) {
            valueLabel = "Precio atractivo";
            valueNote  = "P/E bajo y cotiza cerca del NAV";
          } else if (pe > 30 && pd > 0.3) {
            valueLabel = "Cotiza con prima elevada";
            valueNote  = "Portafolio caro y precio sobre el NAV";
          } else {
            valueLabel = "Precio razonable";
            valueNote  = "Sin señales de sobre o subvaloración marcadas";
          }
        }

        return (
          <div className="card">
            <div className="card-title">🎯 Análisis de Valor</div>
            <table className="ratio-table">
              <tbody>
                {data.nav != null && (
                  <tr>
                    <td>NAV (valor real)</td>
                    <td className="mono">{fmtPrice(data.nav)}</td>
                  </tr>
                )}
                {pd != null && (
                  <tr>
                    <td>Prima / Descuento vs NAV</td>
                    <td className="mono" style={{ color: pdColor }}>
                      {pd > 0 ? "+" : ""}{pd.toFixed(3)}%
                    </td>
                  </tr>
                )}
                {pe != null && (
                  <tr>
                    <td>P/E portafolio</td>
                    <td className="mono" style={{ color: peColor }}>
                      {pe.toFixed(1)}x
                      {peLabel && (
                        <span style={{ fontSize: 11, marginLeft: 6, color: peColor }}>
                          ({peLabel})
                        </span>
                      )}
                    </td>
                  </tr>
                )}
                {data.valuation.pb != null && (
                  <tr>
                    <td>P/B portafolio</td>
                    <td className="mono">{data.valuation.pb.toFixed(2)}x</td>
                  </tr>
                )}
                {netYield != null && (
                  <tr>
                    <td>Rendimiento neto anual</td>
                    <td className="mono" style={{ color: netYield > 0 ? "var(--green)" : "var(--red)" }}>
                      {netYield > 0 ? "+" : ""}{netYield.toFixed(2)}%
                      <span style={{ fontSize: 11, color: "var(--text-muted)", marginLeft: 6 }}>
                        (dividendo − comisión)
                      </span>
                    </td>
                  </tr>
                )}
              </tbody>
            </table>

            {valueLabel && (
              <div style={{ marginTop: 12, padding: "8px 10px",
                background: "rgba(255,255,255,0.04)", borderRadius: 6 }}>
                <span style={{ fontWeight: 600, color: "var(--accent)" }}>
                  {valueLabel}
                </span>
                <span style={{ fontSize: 12, color: "var(--text-muted)", marginLeft: 8 }}>
                  — {valueNote}
                </span>
              </div>
            )}
          </div>
        );
      })()}

      {/* ── Tamaño y liquidez ─────────────────────────────────── */}
      <div className="card">
        <div className="card-title">🏦 Tamaño y Liquidez</div>
        <table className="ratio-table">
          <tbody>
            <tr>
              <td>AUM (patrimonio)</td>
              <td className="mono" style={{ color: "var(--accent)" }}>{fmtAum(data.aum)}</td>
            </tr>
            <tr>
              <td>Volumen diario prom.</td>
              <td className="mono">{fmtVol(data.volume_avg)}</td>
            </tr>
            <tr>
              <td>Inicio del fondo</td>
              <td className="mono">{data.inception_date ?? "—"}</td>
            </tr>
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
            .filter(([, v]) => Math.abs(v) > 0.01)
            .map(([label, val, color]) => (
              <div key={label} className="etf-alloc-row">
                <span className="etf-alloc-label">{label}</span>
                <Bar pct={Math.abs(val)} color={color} />
                <span className="etf-alloc-pct mono" style={{ color: val < 0 ? "var(--red)" : undefined }}>
                  {val > 0 ? "" : "−"}{Math.abs(val).toFixed(1)}%
                </span>
              </div>
            ))}
        </div>
      </div>

      {/* ── Top Holdings ──────────────────────────────────────── */}
      {data.holdings.length > 0 && (
        <div className="card span2">
          <div className="card-title">🏢 Top 10 Holdings</div>
          <div className="etf-holdings-list">
            {data.holdings.map((h, i) => (
              <div key={h.symbol} className="etf-holding-row">
                <span className="etf-holding-rank text-muted">{i + 1}</span>
                <span className="etf-holding-symbol mono">{h.symbol}</span>
                <span className="etf-holding-name">{h.name}</span>
                <Bar pct={h.weight} color="var(--purple-dim)" max={data.holdings[0]?.weight ?? 20} />
                <span className="etf-holding-pct mono">{h.weight.toFixed(2)}%</span>
              </div>
            ))}
          </div>
          {data.holdings.length > 0 && (
            <p className="etf-holdings-note text-muted">
              Concentración top 10: {data.holdings.reduce((s, h) => s + h.weight, 0).toFixed(1)}% del fondo
            </p>
          )}
        </div>
      )}

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
            Score: <span className="mono" style={{ color: vc }}>{data.verdict.score}/10</span>
          </span>
          {data.alternatives && data.alternatives.length > 0 && (
            <span className="etf-verdict-alts text-muted">
              Compara con: <span className="mono">{data.alternatives.slice(0, 2).join(", ")}</span>
            </span>
          )}
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
