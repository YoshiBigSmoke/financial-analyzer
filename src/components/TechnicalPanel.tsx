import "./Panel.css";

interface Signal {
  indicator: string;
  signal:    "buy" | "sell" | "neutral";
  value:     number;
  note:      string;
}
interface Consensus {
  consensus: "buy" | "sell" | "neutral";
  score:     number;
  buy:       number;
  sell:      number;
  neutral:   number;
}
interface Props {
  data: { signals: Signal[]; consensus: Consensus };
}

const SIG_COLOR = { buy: "var(--green)", sell: "var(--red)", neutral: "var(--yellow)" };
const SIG_ICON  = { buy: "🚀", sell: "🛑", neutral: "😐" };

export function TechnicalPanel({ data }: Props) {
  const { signals, consensus } = data;
  const cc = SIG_COLOR[consensus.consensus];

  return (
    <div className="panel-grid">

      {/* ── Consenso ────────────────────────────────────── */}
      <div className="card span2">
        <div className="card-title">📡 Consenso técnico</div>
        <div className="consensus-row">
          <span className="consensus-badge" style={{ color: cc, borderColor: cc }}>
            {SIG_ICON[consensus.consensus]} {consensus.consensus.toUpperCase()}
          </span>
          <span className="consensus-score mono" style={{ color: cc }}>
            score {consensus.score > 0 ? "+" : ""}{consensus.score}
          </span>
          <span className="text-muted">
            🚀 {consensus.buy} &nbsp;🛑 {consensus.sell} &nbsp;😐 {consensus.neutral}
          </span>
        </div>
      </div>

      {/* ── Señales individuales ─────────────────────────── */}
      <div className="card span2">
        <div className="card-title">📊 Señales</div>
        <div className="signals-list">
          {signals.map(s => (
            <div key={s.indicator} className="signal-row">
              <span className="signal-icon" style={{ color: SIG_COLOR[s.signal] }}>
                {SIG_ICON[s.signal]}
              </span>
              <span className="signal-name mono">{s.indicator}</span>
              <span className="signal-note text-muted">{s.note}</span>
              <span className="signal-value mono">{s.value}</span>
            </div>
          ))}
        </div>
      </div>

    </div>
  );
}
