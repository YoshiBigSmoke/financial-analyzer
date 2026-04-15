import "./Panel.css";

interface Props {
  data: {
    company:  Record<string, unknown>;
    ratios:   Record<string, number | string | null>;
    dcf:      Record<string, unknown>;
    scoring:  Record<string, unknown>;
  };
}

function fmt(v: unknown, pct = false, dollar = false): string {
  if (v === null || v === undefined) return "—";
  const n = Number(v);
  if (isNaN(n)) return String(v);
  if (dollar) return `$${n.toFixed(2)}`;
  if (pct)    return `${(n * 100).toFixed(1)}%`;
  return n.toFixed(2);
}

function ScoreBar({ score }: { score: number }) {
  const pct = ((score - 1) / 4) * 100;
  const gradient =
    score >= 4 ? "linear-gradient(90deg, #22c55e, #86efac)" :
    score >= 3 ? "linear-gradient(90deg, #eab308, #fde047)" :
                 "linear-gradient(90deg, #f43f5e, #fb7185)";
  const color =
    score >= 4 ? "var(--green)" : score >= 3 ? "var(--yellow)" : "var(--red)";
  return (
    <div className="score-bar-wrap">
      <div className="score-bar-track">
        <div className="score-bar-fill" style={{ width: `${pct}%`, background: gradient }} />
      </div>
      <span className="score-label" style={{ color }}>{score}/5</span>
    </div>
  );
}

export function FundamentalPanel({ data }: Props) {
  const { company, ratios, dcf, scoring } = data;
  const mos    = dcf?.margin_of_safety as number | null;
  const mosColor = mos != null ? (mos > 0 ? "var(--green)" : "var(--red)") : undefined;

  return (
    <div className="panel-grid">

      {/* ── Empresa ─────────────────────────────────────── */}
      <div className="card span2">
        <div className="card-header">
          <h2 className="ticker">{String(company?.ticker ?? "—")}</h2>
          <span className="company-name">{String(company?.name ?? "")}</span>
        </div>
        <div className="tags">
          {company?.sector   ? <span className="tag">{String(company.sector)}</span>   : null}
          {company?.industry ? <span className="tag">{String(company.industry)}</span> : null}
          {company?.exchange ? <span className="tag">{String(company.exchange)}</span> : null}
        </div>
      </div>

      {/* ── Ratios de Valuación ─────────────────────────── */}
      <div className="card">
        <div className="card-title">💹 Valuación</div>
        <table className="ratio-table">
          <tbody>
            <tr><td>P/E</td>       <td className="mono">{fmt(ratios?.pe_ratio)}</td></tr>
            <tr><td>P/B</td>       <td className="mono">{fmt(ratios?.pb_ratio)}</td></tr>
            <tr><td>P/S</td>       <td className="mono">{fmt(ratios?.ps_ratio)}</td></tr>
            <tr><td>EV/EBITDA</td> <td className="mono">{fmt(ratios?.ev_ebitda)}</td></tr>
          </tbody>
        </table>
      </div>

      {/* ── Rentabilidad ────────────────────────────────── */}
      <div className="card">
        <div className="card-title">📈 Rentabilidad</div>
        <table className="ratio-table">
          <tbody>
            <tr><td>ROE</td>          <td className="mono">{fmt(ratios?.roe,              true)}</td></tr>
            <tr><td>ROA</td>          <td className="mono">{fmt(ratios?.roa,              true)}</td></tr>
            <tr><td>Margen bruto</td> <td className="mono">{fmt(ratios?.gross_margin,     true)}</td></tr>
            <tr><td>Margen op.</td>   <td className="mono">{fmt(ratios?.operating_margin, true)}</td></tr>
            <tr><td>Margen neto</td>  <td className="mono">{fmt(ratios?.net_margin,       true)}</td></tr>
          </tbody>
        </table>
      </div>

      {/* ── Deuda y Liquidez ────────────────────────────── */}
      <div className="card">
        <div className="card-title">🏦 Deuda / Liquidez</div>
        <table className="ratio-table">
          <tbody>
            <tr><td>D/E</td>           <td className="mono">{fmt(ratios?.debt_to_equity)}</td></tr>
            <tr><td>Current ratio</td> <td className="mono">{fmt(ratios?.current_ratio)}</td></tr>
            <tr><td>Quick ratio</td>   <td className="mono">{fmt(ratios?.quick_ratio)}</td></tr>
          </tbody>
        </table>
      </div>

      {/* ── DCF ─────────────────────────────────────────── */}
      <div className="card">
        <div className="card-title">🎯 DCF — Valor Intrínseco</div>
        <div className="dcf-grid">
          <div className="dcf-item">
            <span className="dcf-label">Valor intrínseco</span>
            <span className="dcf-value accent mono">${fmt(dcf?.intrinsic_value)}</span>
          </div>
          <div className="dcf-item">
            <span className="dcf-label">Precio actual</span>
            <span className="dcf-value mono">${fmt(dcf?.current_price)}</span>
          </div>
          <div className="dcf-item mos-item">
            <span className="dcf-label">Margen de seguridad</span>
            <span className="dcf-value mono mos-value" style={{ color: mosColor }}>
              {mos != null ? `${(mos * 100).toFixed(1)}%` : "—"}
            </span>
            {mos != null && (
              <span className="mos-badge" style={{ background: mos > 0 ? "rgba(34,197,94,0.12)" : "rgba(244,63,94,0.12)", color: mosColor, borderColor: mosColor }}>
                {mos > 0.3 ? "🎉 gran descuento" : mos > 0 ? "😊 con descuento" : mos > -0.3 ? "😬 cotiza con prima" : "🚨 muy cara"}
              </span>
            )}
          </div>
        </div>
        {dcf?.assumptions ? (
          <div className="dcf-assumptions">
            <span>Tasa descuento: {fmt((dcf.assumptions as Record<string,unknown>)?.discount_rate, true)}</span>
            <span>Crecimiento: {fmt((dcf.assumptions as Record<string,unknown>)?.growth_rate, true)}</span>
            <span>Terminal: {fmt((dcf.assumptions as Record<string,unknown>)?.terminal_growth, true)}</span>
          </div>
        ) : null}
      </div>

      {/* ── Scoring ─────────────────────────────────────── */}
      {scoring && (
        <div className="card">
          <div className="card-title">
            ⭐ Scoring &mdash; Overall&nbsp;
            <span className="mono" style={{ color: "var(--accent)" }}>
              {fmt(scoring?.overall)}/5
            </span>
          </div>
          {([
            ["valuation",    "💹 Valuación"],
            ["profitability","📈 Rentabilidad"],
            ["growth",       "🚀 Crecimiento"],
            ["health",       "🏥 Salud financiera"],
          ] as [string, string][]).map(([dim, label]) => {
            const d = (scoring as Record<string, Record<string, unknown>>)[dim];
            return (
              <div key={dim} className="score-row">
                <span className="score-dim">{label}</span>
                <ScoreBar score={Number(d?.score ?? 3)} />
                <div className="score-notes">
                  {((d?.notes as string[]) ?? []).map((n: string, i: number) => (
                    <span key={i} className="score-note">· {n}</span>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}

    </div>
  );
}
