/**
 * PriceChart — SVG puro, sin canvas.
 * Responsive en altura via ResizeObserver.
 * Velas y volumen como paths compuestos (~25 nodos vs ~1000 anterior).
 */

import { useMemo, useRef, useState, useEffect } from "react";

// ── Tipos ─────────────────────────────────────────────────────────────────

interface PriceRow {
  date:      string;
  open:      number;
  high:      number;
  low:       number;
  adj_close: number;
  volume:    number;
}

interface ConeData {
  p5:  number[];
  p25: number[];
  p50: number[];
  p75: number[];
  p95: number[];
}

interface Props {
  prices:     PriceRow[];
  cone?:      ConeData;
  horizon?:   number;
  showBands?: boolean;
}

// ── Constantes de layout (las que NO cambian con la altura) ────────────────

const PAD      = { top: 32, right: 72, bottom: 28, left: 64 };
const GAP      = 10;
const MAX_BARS = 120;   // 6 meses — para que el cono MC sea visible sin scroll

// ── Paleta ─────────────────────────────────────────────────────────────────

const C = {
  bg:      "#0d0f18",
  area:    "#090b12",
  border:  "#1e2235",
  muted:   "#475569",
  accent:  "#00d4aa",
  green:   "#22c55e",
  red:     "#f43f5e",
  yellow:  "#eab308",
  blue:    "#60a5fa",
  purple:  "#a78bfa",
};

// ── Helpers ────────────────────────────────────────────────────────────────

function calcSMA(vals: number[], period: number): (number | null)[] {
  return vals.map((_, i) => {
    if (i < period - 1) return null;
    return vals.slice(i - period + 1, i + 1).reduce((a, b) => a + b, 0) / period;
  });
}

function calcBB(vals: number[], period = 20, k = 2) {
  const sma = calcSMA(vals, period);
  return vals.map((_, i) => {
    if (sma[i] === null) return null;
    const sl   = vals.slice(i - period + 1, i + 1);
    const mean = sma[i]!;
    const std  = Math.sqrt(sl.reduce((a, b) => a + (b - mean) ** 2, 0) / period);
    return { upper: mean + k * std, lower: mean - k * std };
  });
}

function bizDays(start: string, n: number): string[] {
  const out: string[] = [];
  const d = new Date(start + "T12:00:00Z");
  let c = 0;
  while (c < n) {
    d.setUTCDate(d.getUTCDate() + 1);
    const dow = d.getUTCDay();
    if (dow !== 0 && dow !== 6) { out.push(d.toISOString().slice(0, 10)); c++; }
  }
  return out;
}

function makePath(
  values: (number | null)[],
  xOf:   (i: number) => number,
  yOf:   (v: number) => number,
): string {
  let d = ""; let on = false;
  for (let i = 0; i < values.length; i++) {
    if (values[i] === null) { on = false; continue; }
    const x = xOf(i).toFixed(1), y = yOf(values[i]!).toFixed(1);
    d += on ? `L${x},${y}` : `M${x},${y}`;
    on = true;
  }
  return d;
}

function fmtPrice(p: number) {
  return p >= 1000 ? p.toFixed(0) : p >= 100 ? p.toFixed(1) : p.toFixed(2);
}

// ── Componente ─────────────────────────────────────────────────────────────

export function PriceChart({ prices, cone, horizon = 30, showBands = true }: Props) {

  // ── Responsive height ────────────────────────────────────────────────────
  const outerRef    = useRef<HTMLDivElement>(null);
  const [contH, setContH] = useState(520);   // default seguro hasta que se mida

  useEffect(() => {
    const el = outerRef.current;
    if (!el) return;
    const ro = new ResizeObserver(entries => {
      const h = Math.round(entries[0].contentRect.height);
      if (h > 120) setContH(h);   // ignorar valores absurdamente pequeños
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  // ── Cálculo de datos + layout ────────────────────────────────────────────
  const data = useMemo(() => {
    // Alturas dinámicas basadas en el contenedor
    const VH      = Math.max(60, Math.round(contH * 0.14));
    const CH      = Math.max(120, contH - PAD.top - PAD.bottom - VH - GAP);
    const TOTAL_H = PAD.top + CH + GAP + VH + PAD.bottom;

    const hist = prices.length > MAX_BARS ? prices.slice(-MAX_BARS) : prices;
    if (hist.length === 0) return null;

    const closes  = hist.map(p => p.adj_close);
    const dates   = hist.map(p => p.date);
    const future  = cone && horizon > 0 ? bizDays(dates[dates.length - 1], horizon) : [];
    const nBars   = hist.length + future.length;

    // 4px por barra — el cono MC cabe dentro del viewport sin scroll horizontal
    const CW = Math.max(800, nBars * 4);
    const TW = PAD.left + CW + PAD.right;

    const barSpan = CW / nBars;
    const barHalf = Math.max(0.6, barSpan * 0.38);
    const xOf     = (i: number) => PAD.left + (i + 0.5) * barSpan;

    // Precio min/max (incluye cono)
    const allP: number[] = hist.flatMap(p => [p.high, p.low]);
    if (cone) {
      const hi = Math.min(horizon, cone.p95.length);
      for (let i = 0; i < hi; i++) { allP.push(cone.p95[i], cone.p5[i]); }
    }
    const pMin = Math.min(...allP) * 0.988;
    const pMax = Math.max(...allP) * 1.012;

    // Protección: si pMin === pMax la división sería 0
    const pRange = pMax - pMin || 1;
    const pY     = (p: number) => PAD.top + CH - ((p - pMin) / pRange) * CH;

    const maxVol  = Math.max(...hist.map(p => p.volume)) || 1;
    const vBase   = PAD.top + CH + GAP + VH;
    const vY      = (v: number) => vBase - (v / maxVol) * VH;
    const vH2     = (v: number) => (v / maxVol) * VH;

    const sma20  = calcSMA(closes, 20);
    const sma50  = calcSMA(closes, 50);
    const sma200 = calcSMA(closes, 200);
    const bb     = calcBB(closes);

    // Y-axis: 6 niveles de precio
    const yTicks = Array.from({ length: 6 }, (_, i) => {
      const p = pMin + pRange * (i / 5);
      return { p, y: pY(p) };
    });

    // X-axis: ~5 etiquetas de fecha
    const step   = Math.max(1, Math.round(hist.length / 5));
    const xTicks = Array.from(
      { length: Math.floor(hist.length / step) },
      (_, i) => ({ label: dates[(i + 1) * step - 1]?.slice(0, 7) ?? "", x: xOf((i + 1) * step - 1) })
    );

    return {
      hist, closes, future, nBars, CW, TW,
      barSpan, barHalf, xOf, pY, vY, vH2, vBase,
      pMin, pMax,
      sma20, sma50, sma200, bb,
      yTicks, xTicks,
      futureOffset: hist.length,
      // layout dinámico para el render
      CH, VH, TOTAL_H,
    };
  }, [prices, cone, horizon, contH]);

  if (!data) return null;

  const {
    hist, closes, future, CW, TW,
    barHalf, xOf, pY, vY, vH2,
    sma20, sma50, sma200, bb,
    yTicks, xTicks,
    futureOffset,
    CH, VH, TOTAL_H,
  } = data;

  const lastClose = closes[closes.length - 1];
  const lastX     = xOf(futureOffset - 1);
  const vBase     = PAD.top + CH + GAP + VH;

  return (
    <div
      ref={outerRef}
      style={{ width: "100%", height: "100%", background: C.bg }}
    >
      <svg
        viewBox={`0 0 ${TW} ${TOTAL_H}`}
        width={TW}
        height={TOTAL_H}
        style={{ display: "block" }}
        xmlns="http://www.w3.org/2000/svg"
      >
        {/* ── Fondos ─────────────────────────────────────────────────── */}
        <rect width={TW} height={TOTAL_H} fill={C.bg} />
        <rect x={PAD.left} y={PAD.top} width={CW} height={CH} fill={C.area} />
        <rect x={PAD.left} y={PAD.top + CH + GAP} width={CW} height={VH} fill={C.area} />

        {/* ── Grilla Y ───────────────────────────────────────────────── */}
        {yTicks.map((t, i) => (
          <g key={i}>
            <line x1={PAD.left} y1={t.y} x2={PAD.left + CW} y2={t.y}
              stroke={C.border} strokeWidth={0.5} strokeDasharray="3,3" />
            <text x={PAD.left - 6} y={t.y + 3.5} textAnchor="end"
              fill={C.muted} fontSize={9} fontFamily="monospace">
              {fmtPrice(t.p)}
            </text>
          </g>
        ))}

        {/* ── Grilla X ───────────────────────────────────────────────── */}
        {xTicks.map((t, i) => (
          <g key={i}>
            <line x1={t.x} y1={PAD.top} x2={t.x} y2={PAD.top + CH}
              stroke={C.border} strokeWidth={0.5} strokeDasharray="3,3" />
            <text x={t.x} y={TOTAL_H - 8} textAnchor="middle"
              fill={C.muted} fontSize={9} fontFamily="monospace">
              {t.label}
            </text>
          </g>
        ))}

        {/* ── Bollinger Bands ─────────────────────────────────────────── */}
        <path d={makePath(bb.map(v => v?.upper ?? null), i => xOf(i), pY)}
          fill="none" stroke="rgba(0,212,170,0.28)" strokeWidth={1} strokeDasharray="2,3" />
        <path d={makePath(bb.map(v => v?.lower ?? null), i => xOf(i), pY)}
          fill="none" stroke="rgba(0,212,170,0.28)" strokeWidth={1} strokeDasharray="2,3" />

        {/* ── SMAs ────────────────────────────────────────────────────── */}
        <path d={makePath(sma200, i => xOf(i), pY)}
          fill="none" stroke={C.purple} strokeWidth={1} strokeDasharray="5,3" />
        <path d={makePath(sma50, i => xOf(i), pY)}
          fill="none" stroke={C.blue} strokeWidth={1} />
        <path d={makePath(sma20, i => xOf(i), pY)}
          fill="none" stroke={C.yellow} strokeWidth={1} />

        {/* ── Velas (4 paths en lugar de ~360 elementos) ─────────────── */}
        {(() => {
          let gWick = "", rWick = "", gBody = "", rBody = "";
          const bw = (barHalf * 2).toFixed(1);
          for (let i = 0; i < hist.length; i++) {
            const p       = hist[i];
            const x       = xOf(i);
            const xs      = x.toFixed(1);
            const xb      = (x - barHalf).toFixed(1);
            const isGreen = p.adj_close >= p.open;
            const yH      = pY(p.high).toFixed(1);
            const yL      = pY(p.low).toFixed(1);
            const yT      = pY(Math.max(p.open, p.adj_close)).toFixed(1);
            const bh      = Math.max(1, pY(Math.min(p.open, p.adj_close)) - pY(Math.max(p.open, p.adj_close)));
            const wick    = `M${xs},${yH}L${xs},${yL}`;
            const body    = `M${xb},${yT}h${bw}v${bh.toFixed(1)}h-${bw}z`;
            if (isGreen) { gWick += wick; gBody += body; }
            else         { rWick += wick; rBody += body; }
          }
          return (
            <>
              <path d={gWick} stroke={C.green} strokeWidth={0.8} fill="none" />
              <path d={rWick} stroke={C.red}   strokeWidth={0.8} fill="none" />
              <path d={gBody} fill={C.green} />
              <path d={rBody} fill={C.red} />
            </>
          );
        })()}

        {/* ── Volumen (2 paths) ────────────────────────────────────────── */}
        {(() => {
          let gVol = "", rVol = "";
          const bw = (barHalf * 2).toFixed(1);
          for (let i = 0; i < hist.length; i++) {
            const p       = hist[i];
            const x       = xOf(i);
            const xb      = (x - barHalf).toFixed(1);
            const isGreen = p.adj_close >= (i > 0 ? hist[i - 1].adj_close : p.adj_close);
            const yv      = vY(p.volume).toFixed(1);
            const vh      = vH2(p.volume).toFixed(1);
            const bar     = `M${xb},${yv}h${bw}v${vh}h-${bw}z`;
            if (isGreen) gVol += bar; else rVol += bar;
          }
          return (
            <>
              <path d={gVol} fill="rgba(34,197,94,0.45)" />
              <path d={rVol} fill="rgba(244,63,94,0.45)" />
            </>
          );
        })()}

        {/* ── Monte Carlo Cone ────────────────────────────────────────── */}
        {cone && (() => {
          const segs = [
            { data: cone.p95, color: "rgba(34,197,94,0.65)",  w: 1 },
            { data: cone.p75, color: "rgba(34,197,94,0.40)",  w: 1 },
            { data: cone.p50, color: "rgba(0,212,170,0.90)",  w: 2 },
            { data: cone.p25, color: "rgba(244,63,94,0.40)",  w: 1 },
            { data: cone.p5,  color: "rgba(244,63,94,0.65)",  w: 1 },
          ] as const;
          return segs.map((s, si) => {
            let d = `M${lastX.toFixed(1)},${pY(lastClose).toFixed(1)}`;
            future.forEach((_, fi) => {
              const v = s.data[fi];
              if (v !== undefined)
                d += `L${xOf(futureOffset + fi).toFixed(1)},${pY(v).toFixed(1)}`;
            });
            return <path key={si} d={d} fill="none" stroke={s.color} strokeWidth={s.w} />;
          });
        })()}

        {/* ── Bandas d15 / d30 ────────────────────────────────────────── */}
        {cone && showBands && future.length >= 30 && (() => {
          const x0  = lastX;
          const x15 = xOf(futureOffset + 14);
          const x30 = xOf(futureOffset + 29);
          const defs = [
            { x0, x1: x15, v: cone.p75[14], color: "rgba(34,197,94,0.80)",  w: 1, dash: "4,3" },
            { x0, x1: x15, v: cone.p50[14], color: "rgba(0,212,170,1.00)",  w: 2, dash: "" },
            { x0, x1: x15, v: cone.p25[14], color: "rgba(244,63,94,0.80)",  w: 1, dash: "4,3" },
            { x0: x15, x1: x30, v: cone.p75[29], color: "rgba(34,197,94,0.55)",  w: 1, dash: "2,3" },
            { x0: x15, x1: x30, v: cone.p50[29], color: "rgba(0,212,170,0.80)",  w: 2, dash: "4,3" },
            { x0: x15, x1: x30, v: cone.p25[29], color: "rgba(244,63,94,0.55)",  w: 1, dash: "2,3" },
          ];
          return (
            <>
              {defs.map((b, bi) => (
                <line key={bi}
                  x1={b.x0.toFixed(1)} y1={pY(b.v).toFixed(1)}
                  x2={b.x1.toFixed(1)} y2={pY(b.v).toFixed(1)}
                  stroke={b.color} strokeWidth={b.w} strokeDasharray={b.dash}
                />
              ))}
              <line
                x1={x15.toFixed(1)} y1={pY(cone.p25[14]).toFixed(1)}
                x2={x15.toFixed(1)} y2={pY(cone.p75[14]).toFixed(1)}
                stroke="rgba(255,255,255,0.10)" strokeWidth={1} strokeDasharray="2,3"
              />
            </>
          );
        })()}

        {/* ── Bordes ─────────────────────────────────────────────────── */}
        <rect x={PAD.left} y={PAD.top} width={CW} height={CH}
          fill="none" stroke={C.border} strokeWidth={1} />
        <rect x={PAD.left} y={vBase} width={CW} height={VH}
          fill="none" stroke={C.border} strokeWidth={1} />

        {/* ── Leyenda ─────────────────────────────────────────────────── */}
        <g fontSize={9} fontFamily="monospace">
          {[
            { label: "── SMA20",       color: C.yellow,                x: PAD.left + 8   },
            { label: "── SMA50",       color: C.blue,                  x: PAD.left + 68  },
            { label: "╌ SMA200",       color: C.purple,                x: PAD.left + 130 },
            { label: "·· BB",          color: "rgba(0,212,170,0.55)",  x: PAD.left + 198 },
            ...(cone ? [{ label: "── Cono MC",      color: C.accent,   x: PAD.left + 236 }] : []),
            ...(cone && showBands ? [{ label: "── d15/d30", color: "rgba(34,197,94,0.85)", x: PAD.left + 306 }] : []),
          ].map((item, i) => (
            <text key={i} x={item.x} y={PAD.top - 8} fill={item.color}>{item.label}</text>
          ))}
        </g>
      </svg>
    </div>
  );
}
