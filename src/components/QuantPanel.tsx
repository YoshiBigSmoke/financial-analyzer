import "./Panel.css";

interface Props {
  data: {
    ticker:        string;
    current_price: number;
    horizon:       number;
    garch:         Record<string, unknown>;
    monte_carlo:   Record<string, unknown>;
    cone:          Record<string, number[]>;
    arima:         Record<string, unknown>;
  };
}

function fmt2(v: unknown): string {
  const n = Number(v);
  return isNaN(n) ? "—" : n.toFixed(2);
}
function fmtPct(v: unknown): string {
  const n = Number(v);
  return isNaN(n) ? "—" : `${n.toFixed(2)}%`;
}

function ProbBar({ prob, color, gradient }: { prob: number; color: string; gradient: string }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
      <div style={{ flex: 1, height: 10, background: "var(--bg-elevated)", borderRadius: 6, overflow: "hidden" }}>
        <div style={{
          width: `${prob * 100}%`, height: "100%",
          background: gradient, borderRadius: 6,
          transition: "width 0.6s cubic-bezier(0.34,1.56,0.64,1)",
        }} />
      </div>
      <span className="mono" style={{ color, minWidth: 44, fontWeight: 700 }}>{(prob * 100).toFixed(1)}%</span>
    </div>
  );
}

export function QuantPanel({ data }: Props) {
  const { current_price, horizon, garch, monte_carlo, cone, arima } = data;
  const mc   = monte_carlo as Record<string, unknown>;
  const pct  = (mc.percentiles ?? {}) as Record<string, number>;
  const gp   = (garch.params  ?? {}) as Record<string, number>;
  const gfc  = (garch.forecast ?? {}) as Record<string, unknown>;
  const adf  = ((arima.adf ?? {}) as Record<string, unknown>);
  const arimaOrder = arima.order as number[] | undefined;
  const arimaPrices = ((arima.prices ?? {}) as Record<string, number[]>);

  const probAbove = Number(mc.prob_above ?? 0);
  const probBelow = Number(mc.prob_below ?? 0);

  return (
    <div className="panel-grid">

      {/* ── GARCH ────────────────────────────────────────── */}
      <div className="card">
        <div className="card-title">🌊 GARCH(1,1) — Volatilidad</div>
        <table className="ratio-table">
          <tbody>
            <tr><td>α (shock pasado)</td>   <td className="mono">{fmt2(gp["alpha[1]"])}</td></tr>
            <tr><td>β (persistencia)</td>   <td className="mono">{fmt2(gp["beta[1]"])}</td></tr>
            <tr><td>α + β</td>              <td className="mono">{fmt2(garch.persistence)}</td></tr>
            <tr><td>Half-life vol</td>      <td className="mono">{garch.half_life ? `${garch.half_life} días` : "—"}</td></tr>
            <tr><td>Vol. diaria ({horizon}d avg)</td>  <td className="mono">{fmtPct(gfc.avg_daily)}</td></tr>
            <tr><td>Vol. anualizada</td>    <td className="mono">{fmtPct(gfc.avg_annual)}</td></tr>
          </tbody>
        </table>
      </div>

      {/* ── Monte Carlo ──────────────────────────────────── */}
      <div className="card">
        <div className="card-title">🎲 Monte Carlo GBM — {horizon} días</div>
        <div className="mc-price-row">
          <div>
            <span className="dcf-label">Precio actual</span>
            <span className="dcf-value mono">${fmt2(current_price)}</span>
          </div>
          <div>
            <span className="dcf-label">Precio esperado (p50)</span>
            <span className="dcf-value accent mono">${fmt2(mc.expected_price)}</span>
          </div>
        </div>

        <div className="card-title" style={{ marginTop: 12 }}>Distribución al día {horizon}</div>
        <table className="ratio-table">
          <tbody>
            {[[99,"var(--green)"],[95,"var(--green)"],[75,"var(--green)"],
               [50,"var(--accent)"],[25,"var(--red)"],[5,"var(--red)"],[1,"var(--red)"]].map(([p, c]) => (
              <tr key={p}>
                <td style={{ color: c as string }}>p{p}</td>
                <td className="mono">${fmt2(pct[p])}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* ── VaR / CVaR ───────────────────────────────────── */}
      <div className="card">
        <div className="card-title">⚡ Riesgo — VaR / CVaR</div>
        <table className="ratio-table">
          <tbody>
            <tr>
              <td>VaR 5%</td>
              <td className="mono text-red">${fmt2(mc.var_5)}</td>
            </tr>
            <tr>
              <td>VaR 1%</td>
              <td className="mono text-red">${fmt2(mc.var_1)}</td>
            </tr>
            <tr>
              <td>CVaR 5%</td>
              <td className="mono text-red">${fmt2(mc.cvar_5)}</td>
            </tr>
          </tbody>
        </table>
        <div style={{ marginTop: 16 }}>
          <div className="dcf-label" style={{ marginBottom: 6 }}>
            P(sube sobre ${fmt2(current_price)})
          </div>
          <ProbBar prob={probAbove} color="var(--green)" gradient="linear-gradient(90deg, #22c55e, #86efac)" />
          <div className="dcf-label" style={{ margin: "8px 0 6px" }}>
            P(baja bajo ${fmt2(current_price)})
          </div>
          <ProbBar prob={probBelow} color="var(--red)" gradient="linear-gradient(90deg, #f43f5e, #fb7185)" />
        </div>
      </div>

      {/* ── Cono de precios ──────────────────────────────── */}
      <div className="card">
        <div className="card-title">🔭 Cono de precios — día {horizon}</div>
        <table className="ratio-table">
          <tbody>
            <tr><td className="text-green">Optimista extremo (p95)</td>  <td className="mono text-green">${fmt2(cone.p95?.slice(-1)[0])}</td></tr>
            <tr><td className="text-green">Optimista (p75)</td>          <td className="mono text-green">${fmt2(cone.p75?.slice(-1)[0])}</td></tr>
            <tr><td className="text-accent">Central (p50)</td>           <td className="mono text-accent">${fmt2(cone.p50?.slice(-1)[0])}</td></tr>
            <tr><td className="text-red">Pesimista (p25)</td>            <td className="mono text-red">${fmt2(cone.p25?.slice(-1)[0])}</td></tr>
            <tr><td className="text-red">Pesimista extremo (p5)</td>     <td className="mono text-red">${fmt2(cone.p5?.slice(-1)[0])}</td></tr>
          </tbody>
        </table>
      </div>

      {/* ── ARIMA ────────────────────────────────────────── */}
      <div className="card span2">
        <div className="card-title">
          📡 ARIMA{arimaOrder ? `(${arimaOrder.join(",")})` : ""} — Proyección de precios
          <span className="text-muted" style={{ marginLeft: 8, fontSize: 12 }}>
            ADF p-value: {fmt2(adf.p_value)} — serie {adf.stationary ? "estacionaria ✓" : "no estacionaria"}
          </span>
        </div>
        <table className="ratio-table">
          <thead>
            <tr>
              <th>Día</th>
              <th>Precio central</th>
              <th>IC 95% inferior</th>
              <th>IC 95% superior</th>
            </tr>
          </thead>
          <tbody>
            {[0, 4, 9, 19, 29].map(i => {
              const prices = arimaPrices.prices ?? [];
              const lower  = arimaPrices.prices_lower ?? [];
              const upper  = arimaPrices.prices_upper ?? [];
              if (i >= prices.length) return null;
              return (
                <tr key={i}>
                  <td className="text-muted">Día {i + 1}</td>
                  <td className="mono">${fmt2(prices[i])}</td>
                  <td className="mono text-red">${fmt2(lower[i])}</td>
                  <td className="mono text-green">${fmt2(upper[i])}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

    </div>
  );
}
