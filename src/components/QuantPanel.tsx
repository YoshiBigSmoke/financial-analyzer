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

  const probAbove  = Number(mc.prob_above ?? 0);
  const probBelow  = Number(mc.prob_below ?? 0);

  type Scenario = { key: string; label: string; icon: string; range: string; prob: number; avg_price: number };
  const scenarios      = (mc.scenarios      ?? []) as Scenario[];
  const mostProbable   = mc.most_probable   as string | undefined;

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

      {/* ── Escenarios Monte Carlo ───────────────────────── */}
      {scenarios.length > 0 && (
        <div className="card span2">
          <div className="card-title">🎯 Escenarios — ¿qué es más probable en {horizon} días?</div>
          <div style={{ display: "flex", flexDirection: "column", gap: 10, marginTop: 4 }}>
            {scenarios.map(sc => {
              const isBest = sc.key === mostProbable;
              const barColor =
                sc.key === "muy_alcista" ? "linear-gradient(90deg,#22c55e,#86efac)" :
                sc.key === "alcista"     ? "linear-gradient(90deg,#4ade80,#bbf7d0)" :
                sc.key === "lateral"     ? "linear-gradient(90deg,#a78bfa,#c4b5fd)" :
                sc.key === "bajista"     ? "linear-gradient(90deg,#fb923c,#fed7aa)" :
                                          "linear-gradient(90deg,#f43f5e,#fb7185)";
              const textColor =
                sc.key === "muy_alcista" ? "var(--green)" :
                sc.key === "alcista"     ? "var(--green)" :
                sc.key === "lateral"     ? "var(--accent)" :
                sc.key === "bajista"     ? "var(--orange, #fb923c)" :
                                          "var(--red)";
              return (
                <div key={sc.key} style={{
                  background: isBest ? "rgba(167,139,250,0.07)" : undefined,
                  border: isBest ? "1px solid var(--purple)" : "1px solid transparent",
                  borderRadius: 8,
                  padding: "8px 12px",
                }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 5 }}>
                    <span style={{ fontSize: 16 }}>{sc.icon}</span>
                    <span style={{ fontWeight: isBest ? 700 : 500, color: textColor, fontSize: 13 }}>
                      {sc.label}
                    </span>
                    <span className="text-muted" style={{ fontSize: 11 }}>{sc.range}</span>
                    {isBest && (
                      <span style={{
                        marginLeft: "auto", fontSize: 10, fontWeight: 700,
                        background: "var(--purple)", color: "#fff",
                        borderRadius: 10, padding: "2px 8px", letterSpacing: "0.04em",
                      }}>MÁS PROBABLE</span>
                    )}
                    <span className="mono" style={{ marginLeft: isBest ? 0 : "auto", color: textColor, fontWeight: 700, fontSize: 14 }}>
                      {(sc.prob * 100).toFixed(1)}%
                    </span>
                    <span className="mono text-muted" style={{ fontSize: 11 }}>avg ${fmt2(sc.avg_price)}</span>
                  </div>
                  <div style={{ height: 8, background: "var(--bg-elevated)", borderRadius: 4, overflow: "hidden" }}>
                    <div style={{
                      width: `${sc.prob * 100}%`, height: "100%",
                      background: barColor, borderRadius: 4,
                      transition: "width 0.8s cubic-bezier(0.34,1.56,0.64,1)",
                    }} />
                  </div>
                </div>
              );
            })}
          </div>
          <div className="text-muted" style={{ fontSize: 11, marginTop: 8, textAlign: "right" }}>
            {(scenarios.reduce((a, s) => a + s.prob, 0) * 100).toFixed(1)}% total · {(mc.simulations as number)?.toLocaleString()} simulaciones
          </div>
        </div>
      )}

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
            {(() => {
              const pArr = arimaPrices.prices       ?? [];
              const lArr = arimaPrices.prices_lower ?? [];
              const uArr = arimaPrices.prices_upper ?? [];
              const h    = pArr.length;
              if (h === 0) return null;
              // Hitos adaptativos: día 1, 10, 30, mitad, fin
              const idxs = [...new Set([
                0,
                Math.min(9,  h - 1),
                Math.min(29, h - 1),
                Math.round(h / 2) - 1,
                h - 1,
              ])].sort((a, b) => a - b);
              return idxs.map(i => (
                <tr key={i}>
                  <td className="text-muted">Día {i + 1}</td>
                  <td className="mono">${fmt2(pArr[i])}</td>
                  <td className="mono text-red">${fmt2(lArr[i])}</td>
                  <td className="mono text-green">${fmt2(uArr[i])}</td>
                </tr>
              ));
            })()}
          </tbody>
        </table>
      </div>

    </div>
  );
}
