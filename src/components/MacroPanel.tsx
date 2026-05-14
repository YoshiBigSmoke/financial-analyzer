import "./Panel.css";
import "./MacroPanel.css";

type SignalStatus = "green" | "yellow" | "orange" | "red";

interface MacroSignal {
  label:  string;
  status: SignalStatus;
  value:  string;
  note:   string;
  date:   string | null;
}

interface MacroEtf {
  ticker: string;
  reason: string;
}

interface MacroData {
  phase:        string;
  label:        string;
  color:        SignalStatus;
  icon:         string;
  description:  string;
  score:        number;
  etfs:         MacroEtf[];
  signals:      Record<string, MacroSignal>;
  last_updated: string | null;
  fetch_errors: Record<string, string>;
}

interface Props {
  data:      MacroData;
  onRefresh: () => void;
  loading:   boolean;
}

const STATUS_COLOR: Record<SignalStatus, string> = {
  green:  "var(--green)",
  yellow: "var(--yellow)",
  orange: "#f97316",
  red:    "var(--red)",
};

const PHASE_STYLE: Record<SignalStatus, { bg: string; border: string }> = {
  green:  { bg: "rgba(34,197,94,0.08)",  border: "rgba(34,197,94,0.25)"  },
  yellow: { bg: "rgba(234,179,8,0.08)",  border: "rgba(234,179,8,0.25)"  },
  orange: { bg: "rgba(249,115,22,0.08)", border: "rgba(249,115,22,0.25)" },
  red:    { bg: "rgba(244,63,94,0.08)",  border: "rgba(244,63,94,0.25)"  },
};

// Orden fijo de señales
const SIGNAL_ORDER = ["T10Y2Y", "NAPM", "SAHMREALTIME", "CPIAUCSL", "UNRATE"];

function Dot({ status }: { status: SignalStatus }) {
  return (
    <span
      className="macro-dot"
      style={{ background: STATUS_COLOR[status], boxShadow: `0 0 6px ${STATUS_COLOR[status]}` }}
    />
  );
}

function SignalCard({ sig }: { sig: MacroSignal }) {
  return (
    <div className="card macro-signal-card">
      <div className="macro-signal-header">
        <Dot status={sig.status} />
        <span className="macro-signal-label">{sig.label}</span>
      </div>
      <div className="macro-signal-value mono" style={{ color: STATUS_COLOR[sig.status] }}>
        {sig.value}
      </div>
      <div className="macro-signal-note">{sig.note}</div>
      {sig.date && (
        <div className="macro-signal-date">{sig.date}</div>
      )}
    </div>
  );
}

export function MacroPanel({ data, onRefresh, loading }: Props) {
  const phase   = PHASE_STYLE[data.color];
  const signals = SIGNAL_ORDER
    .filter(id => data.signals[id])
    .map(id => ({ id, sig: data.signals[id] }));

  const hasErrors = Object.keys(data.fetch_errors ?? {}).length > 0;

  return (
    <div className="macro-wrap">

      {/* ── Banner de fase ──────────────────────────────────── */}
      <div
        className="macro-banner"
        style={{ background: phase.bg, borderColor: phase.border }}
      >
        <div className="macro-banner-left">
          <span className="macro-phase-icon">{data.icon}</span>
          <div>
            <div className="macro-phase-label" style={{ color: STATUS_COLOR[data.color] }}>
              {data.label}
            </div>
            <div className="macro-phase-desc">{data.description}</div>
          </div>
        </div>
        <div className="macro-banner-right">
          <div className="macro-score-wrap">
            <span className="macro-score-label">Score</span>
            <span
              className="macro-score-val mono"
              style={{ color: STATUS_COLOR[data.color] }}
            >
              {data.score > 0 ? `+${data.score}` : data.score}
            </span>
          </div>
          <button
            className={`btn-ghost small macro-refresh ${loading ? "refreshing" : ""}`}
            onClick={onRefresh}
            disabled={loading}
          >
            {loading ? "↻ Actualizando..." : "↻ Refresh"}
          </button>
        </div>
      </div>

      {/* ── Indicadores ─────────────────────────────────────── */}
      <div className="macro-signals-grid">
        {signals.map(({ id, sig }) => (
          <SignalCard key={id} sig={sig} />
        ))}
      </div>

      {/* ── ETFs recomendados ────────────────────────────────── */}
      <div className="card macro-etf-card">
        <div className="card-title">
          📦 ETFs recomendados &mdash; {data.label}
        </div>
        <div className="macro-etf-list">
          {data.etfs.map(etf => (
            <div key={etf.ticker} className="macro-etf-row">
              <span
                className="macro-etf-ticker mono"
                style={{ color: STATUS_COLOR[data.color] }}
              >
                {etf.ticker}
              </span>
              <span className="macro-etf-reason">{etf.reason}</span>
            </div>
          ))}
        </div>
      </div>

      {/* ── Footer ──────────────────────────────────────────── */}
      <div className="macro-footer">
        <span className="text-muted" style={{ fontSize: 11 }}>
          {data.last_updated
            ? `Datos: ${data.last_updated.slice(0, 16).replace("T", " ")} — FRED (Federal Reserve)`
            : "Fuente: FRED — Federal Reserve Economic Data"}
        </span>
        {hasErrors && (
          <span style={{ fontSize: 11, color: "var(--yellow)" }}>
            ⚠ Algunas series no cargaron: {Object.keys(data.fetch_errors).join(", ")}
          </span>
        )}
      </div>

    </div>
  );
}
