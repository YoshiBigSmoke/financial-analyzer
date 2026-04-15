/**
 * PriceChart — SVG puro, interacción estilo TradingView:
 *   · Rueda → zoom (siempre)
 *   · Click + drag izquierda → ver historial pasado
 *   · Click + drag derecha  → volver al presente
 *   · Hover → crosshair con OHLCV
 */

import { useMemo, useRef, useState, useEffect, useCallback } from "react";

// ── Tipos ─────────────────────────────────────────────────────────────────

interface PriceRow {
  date: string; open: number; high: number; low: number; adj_close: number; volume: number;
}
interface ConeData {
  p5: number[]; p25: number[]; p50: number[]; p75: number[]; p95: number[];
}
interface Props {
  prices: PriceRow[]; cone?: ConeData; horizon?: number; showBands?: boolean;
}

// ── Layout ────────────────────────────────────────────────────────────────

const PAD      = { top: 32, right: 80, bottom: 28, left: 68 };
const GAP      = 10;
const MAX_BARS = 120;
const BAR_W    = 6;   // px por barra — constante, no se ve afectada por el cono

// ── Paleta ────────────────────────────────────────────────────────────────

const C = {
  bg: "#0d0f18", area: "#090b12", border: "#1e2235", muted: "#475569",
  accent: "#00d4aa", green: "#22c55e", red: "#f43f5e",
  yellow: "#eab308", blue: "#60a5fa", purple: "#a78bfa",
};

// ── Helpers ───────────────────────────────────────────────────────────────

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
    const sl = vals.slice(i - period + 1, i + 1);
    const mean = sma[i]!;
    const std = Math.sqrt(sl.reduce((a, b) => a + (b - mean) ** 2, 0) / period);
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
  xOf: (i: number) => number,
  yOf: (v: number) => number,
): string {
  let d = ""; let on = false;
  for (let i = 0; i < values.length; i++) {
    if (values[i] === null) { on = false; continue; }
    const x = xOf(i).toFixed(1), y = yOf(values[i]!).toFixed(1);
    d += on ? `L${x},${y}` : `M${x},${y}`; on = true;
  }
  return d;
}
function fmtP(p: number) { return p >= 1000 ? p.toFixed(0) : p >= 100 ? p.toFixed(1) : p.toFixed(2); }

// ── Componente ────────────────────────────────────────────────────────────

export function PriceChart({ prices, cone, horizon = 30, showBands = true }: Props) {

  // ── Tamaño del contenedor ────────────────────────────────────────────
  const outerRef = useRef<HTMLDivElement>(null);
  const [contH, setContH] = useState(520);
  useEffect(() => {
    const el = outerRef.current; if (!el) return;
    const ro = new ResizeObserver(e => { const h = Math.round(e[0].contentRect.height); if (h > 120) setContH(h); });
    ro.observe(el); return () => ro.disconnect();
  }, []);

  // ── Zoom + paneo ──────────────────────────────────────────────────────
  const [zoomBars, setZoomBars]   = useState(MAX_BARS);
  const [panOffset, setPanOffset] = useState(0); // 0 = vela más reciente visible

  // Reset al cambiar de ticker
  useEffect(() => {
    setZoomBars(Math.min(MAX_BARS, prices.length || MAX_BARS));
    setPanOffset(0);
  }, [prices]);

  // Rueda → zoom (sin restricción de deltaX para que funcione en trackpad)
  useEffect(() => {
    const el = outerRef.current; if (!el) return;
    function onWheel(e: WheelEvent) {
      e.preventDefault();
      const factor = e.deltaY > 0 ? 1.15 : 1 / 1.15;
      setZoomBars(prev => Math.round(Math.min(prices.length || MAX_BARS, Math.max(15, prev * factor))));
    }
    el.addEventListener("wheel", onWheel, { passive: false });
    return () => el.removeEventListener("wheel", onWheel);
  }, [prices]);

  // Drag → paneo  (dirección TradingView: arrastrar derecha = ir al pasado)
  const dragRef = useRef<{ startX: number; startPan: number } | null>(null);
  const [isDragging, setIsDragging] = useState(false);

  const startDrag = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    dragRef.current = { startX: e.clientX, startPan: panOffset };
    setIsDragging(true);
  }, [panOffset]);

  const doDrag = useCallback((e: React.MouseEvent) => {
    if (!dragRef.current || !outerRef.current) return;
    const w = outerRef.current.getBoundingClientRect().width;
    if (w === 0) return;
    const deltaX    = e.clientX - dragRef.current.startX;
    // +deltaX = mouse se mueve a la derecha = ir al pasado (panOffset sube)
    const deltaBars = Math.round(deltaX * zoomBars / w);
    const maxPan    = Math.max(0, prices.length - zoomBars);
    setPanOffset(Math.max(0, Math.min(maxPan, dragRef.current.startPan + deltaBars)));
  }, [zoomBars, prices.length]);

  const stopDrag = useCallback(() => { dragRef.current = null; setIsDragging(false); }, []);

  // ── Crosshair ────────────────────────────────────────────────────────
  // hoverPos: posición raw del cursor en coords SVG (para las líneas, siempre visible)
  // hoverIdx: índice de barra histórica bajo el cursor (null en zona del cono = sin OHLCV)
  const [hoverPos, setHoverPos] = useState<{ svgX: number; svgY: number } | null>(null);
  const [hoverIdx, setHoverIdx] = useState<number | null>(null);

  // ── Cálculo SVG ───────────────────────────────────────────────────────
  const data = useMemo(() => {
    const VH      = Math.max(60, Math.round(contH * 0.14));
    const CH      = Math.max(120, contH - PAD.top - PAD.bottom - VH - GAP);
    const TOTAL_H = PAD.top + CH + GAP + VH + PAD.bottom;

    // Ventana visible
    const endIdx   = Math.max(zoomBars - 1, prices.length - 1 - panOffset);
    const startIdx = Math.max(0, endIdx - zoomBars + 1);
    const hist     = prices.slice(startIdx, endIdx + 1);
    const atEnd    = panOffset === 0;

    if (hist.length === 0) return null;

    const closes = hist.map(p => p.adj_close);
    const dates  = hist.map(p => p.date);

    // Cono solo cuando estamos en la vela más reciente
    const future = cone && horizon > 0 && atEnd ? bizDays(dates[dates.length - 1], horizon) : [];

    // BAR_W es fijo — el cono no comprime las velas históricas
    const barSpan  = BAR_W;
    const barHalf  = barSpan * 0.38;
    const histW    = hist.length * barSpan;
    const futureW  = future.length * barSpan;
    const CW       = Math.max(histW + futureW, 600);
    const TW       = PAD.left + CW + PAD.right;

    const xOf = (i: number) => PAD.left + (i + 0.5) * barSpan;

    // Precios min/max (cone solo cuando atEnd)
    const allP: number[] = hist.flatMap(p => [p.high, p.low]);
    if (cone && atEnd) {
      const hi = Math.min(horizon, cone.p95.length);
      for (let i = 0; i < hi; i++) allP.push(cone.p95[i], cone.p5[i]);
    }
    const pMin   = Math.min(...allP) * 0.988;
    const pMax   = Math.max(...allP) * 1.012;
    const pRange = pMax - pMin || 1;
    const pY     = (p: number) => PAD.top + CH - ((p - pMin) / pRange) * CH;

    const maxVol = Math.max(...hist.map(p => p.volume)) || 1;
    const vBase  = PAD.top + CH + GAP + VH;
    const vY     = (v: number) => vBase - (v / maxVol) * VH;
    const vH2    = (v: number) => (v / maxVol) * VH;

    const sma20  = calcSMA(closes, 20);
    const sma50  = calcSMA(closes, 50);
    const sma200 = calcSMA(closes, 200);
    const bb     = calcBB(closes);

    const yTicks = Array.from({ length: 6 }, (_, i) => ({
      p: pMin + pRange * (i / 5), y: pY(pMin + pRange * (i / 5)),
    }));
    const step   = Math.max(1, Math.round(hist.length / 5));
    const xTicks = Array.from({ length: Math.floor(hist.length / step) }, (_, i) => ({
      label: dates[(i + 1) * step - 1]?.slice(0, 7) ?? "",
      x: xOf((i + 1) * step - 1),
    }));

    return {
      hist, closes, future, CW, TW,
      barSpan, barHalf, xOf, pY, pMin, pRange,
      vY, vH2, vBase,
      sma20, sma50, sma200, bb,
      yTicks, xTicks,
      futureOffset: hist.length,
      atEnd,
      CH, VH, TOTAL_H,
    };
  }, [prices, cone, horizon, contH, zoomBars, panOffset]);

  // ── Mouse move unificado (drag + crosshair) ───────────────────────────
  const onMouseMove = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    // Drag — esconde crosshair mientras se arrastra
    if (dragRef.current) { doDrag(e); setHoverPos(null); setHoverIdx(null); return; }

    if (!data || !outerRef.current) return;
    const rect = outerRef.current.getBoundingClientRect();
    const svgX = e.clientX - rect.left;
    const svgY = e.clientY - rect.top;
    const { barSpan, CH, CW, futureOffset } = data;

    // Crosshair visible en TODO el área del gráfico (histórico + cono)
    if (svgX >= PAD.left && svgX < PAD.left + CW && svgY >= PAD.top && svgY < PAD.top + CH) {
      setHoverPos({ svgX, svgY });
      // OHLCV solo sobre barras históricas
      const idx = Math.floor((svgX - PAD.left) / barSpan);
      setHoverIdx(idx >= 0 && idx < futureOffset ? idx : null);
    } else {
      setHoverPos(null);
      setHoverIdx(null);
    }
  }, [data, doDrag]);

  const onMouseLeave = useCallback(() => { stopDrag(); setHoverPos(null); setHoverIdx(null); }, [stopDrag]);

  // ── Render ───────────────────────────────────────────────────────────
  if (!data) return null;

  const {
    hist, future, CW, TW,
    barHalf, xOf, pY, pMin, pRange,
    vY, vH2,
    sma20, sma50, sma200, bb,
    yTicks, xTicks,
    futureOffset, atEnd,
    CH, VH, TOTAL_H,
  } = data;

  const lastClose = hist[hist.length - 1]?.adj_close ?? 0;
  const lastX     = xOf(futureOffset - 1);
  const vBase     = PAD.top + CH + GAP + VH;

  // Crosshair calculado
  // chBar / chX — solo cuando hay barra histórica bajo el cursor (para OHLCV)
  // hoverPos    — posición raw para las líneas (funciona en todo el gráfico incluido el cono)
  const chBar   = hoverIdx !== null ? hist[hoverIdx] : null;
  const chX     = hoverIdx !== null ? xOf(hoverIdx) : (hoverPos?.svgX ?? 0);
  const chPrice = hoverPos
    ? pMin + pRange * (1 - (hoverPos.svgY - PAD.top) / CH)
    : 0;

  return (
    <div
      ref={outerRef}
      style={{
        minWidth: "100%", width: "fit-content", height: "100%",
        background: C.bg, position: "relative",
        cursor: isDragging ? "grabbing" : "crosshair",
        userSelect: "none",
      }}
      onMouseDown={startDrag}
      onMouseMove={onMouseMove}
      onMouseUp={stopDrag}
      onMouseLeave={onMouseLeave}
    >
      {/* Indicador de posición */}
      <div style={{
        position: "absolute", top: 8, right: 12, zIndex: 10,
        fontSize: 10, color: "rgba(255,255,255,0.35)", pointerEvents: "none", fontFamily: "monospace",
      }}>
        {hist.length}d{panOffset > 0 ? ` · ↩ ${panOffset}d atrás` : " · rueda: zoom  drag: mover"}
      </div>

      <svg
        viewBox={`0 0 ${TW} ${TOTAL_H}`}
        width={TW}
        height={TOTAL_H}
        style={{ display: "block", pointerEvents: "none" }}  /* eventos al div, no al SVG */
        xmlns="http://www.w3.org/2000/svg"
      >
        {/* Fondos */}
        <rect width={TW} height={TOTAL_H} fill={C.bg} />
        <rect x={PAD.left} y={PAD.top} width={CW} height={CH} fill={C.area} />
        <rect x={PAD.left} y={PAD.top + CH + GAP} width={CW} height={VH} fill={C.area} />

        {/* Grilla Y */}
        {yTicks.map((t, i) => (
          <g key={i}>
            <line x1={PAD.left} y1={t.y} x2={PAD.left + CW} y2={t.y}
              stroke={C.border} strokeWidth={0.5} strokeDasharray="3,3" />
            <text x={PAD.left - 6} y={t.y + 3.5} textAnchor="end"
              fill={C.muted} fontSize={9} fontFamily="monospace">{fmtP(t.p)}</text>
          </g>
        ))}

        {/* Grilla X */}
        {xTicks.map((t, i) => (
          <g key={i}>
            <line x1={t.x} y1={PAD.top} x2={t.x} y2={PAD.top + CH}
              stroke={C.border} strokeWidth={0.5} strokeDasharray="3,3" />
            <text x={t.x} y={TOTAL_H - 8} textAnchor="middle"
              fill={C.muted} fontSize={9} fontFamily="monospace">{t.label}</text>
          </g>
        ))}

        {/* Bollinger */}
        <path d={makePath(bb.map(v => v?.upper ?? null), i => xOf(i), pY)}
          fill="none" stroke="rgba(0,212,170,0.28)" strokeWidth={1} strokeDasharray="2,3" />
        <path d={makePath(bb.map(v => v?.lower ?? null), i => xOf(i), pY)}
          fill="none" stroke="rgba(0,212,170,0.28)" strokeWidth={1} strokeDasharray="2,3" />

        {/* SMAs */}
        <path d={makePath(sma200, i => xOf(i), pY)} fill="none" stroke={C.purple} strokeWidth={1} strokeDasharray="5,3" />
        <path d={makePath(sma50,  i => xOf(i), pY)} fill="none" stroke={C.blue}   strokeWidth={1} />
        <path d={makePath(sma20,  i => xOf(i), pY)} fill="none" stroke={C.yellow} strokeWidth={1} />

        {/* Velas (4 paths) */}
        {(() => {
          let gWick = "", rWick = "", gBody = "", rBody = "";
          const bw = (barHalf * 2).toFixed(1);
          for (let i = 0; i < hist.length; i++) {
            const p = hist[i];
            const x = xOf(i), xs = x.toFixed(1), xb = (x - barHalf).toFixed(1);
            const isG = p.adj_close >= p.open;
            const yH = pY(p.high).toFixed(1), yL = pY(p.low).toFixed(1);
            const yT = pY(Math.max(p.open, p.adj_close)).toFixed(1);
            const bh = Math.max(1, pY(Math.min(p.open, p.adj_close)) - pY(Math.max(p.open, p.adj_close)));
            const wick = `M${xs},${yH}L${xs},${yL}`;
            const body = `M${xb},${yT}h${bw}v${bh.toFixed(1)}h-${bw}z`;
            if (isG) { gWick += wick; gBody += body; } else { rWick += wick; rBody += body; }
          }
          return (<>
            <path d={gWick} stroke={C.green} strokeWidth={0.8} fill="none" />
            <path d={rWick} stroke={C.red}   strokeWidth={0.8} fill="none" />
            <path d={gBody} fill={C.green} /><path d={rBody} fill={C.red} />
          </>);
        })()}

        {/* Volumen (2 paths) */}
        {(() => {
          let gVol = "", rVol = "";
          const bw = (barHalf * 2).toFixed(1);
          for (let i = 0; i < hist.length; i++) {
            const p = hist[i], x = xOf(i);
            const isG = p.adj_close >= (i > 0 ? hist[i - 1].adj_close : p.adj_close);
            const bar = `M${(x - barHalf).toFixed(1)},${vY(p.volume).toFixed(1)}h${bw}v${vH2(p.volume).toFixed(1)}h-${bw}z`;
            if (isG) gVol += bar; else rVol += bar;
          }
          return (<>
            <path d={gVol} fill="rgba(34,197,94,0.45)" />
            <path d={rVol} fill="rgba(244,63,94,0.45)" />
          </>);
        })()}

        {/* Cono MC (solo cuando estamos en la vela más reciente) */}
        {cone && atEnd && (() => {
          const segs = [
            { data: cone.p95, color: "rgba(34,197,94,0.65)", w: 1 },
            { data: cone.p75, color: "rgba(34,197,94,0.40)", w: 1 },
            { data: cone.p50, color: "rgba(0,212,170,0.90)", w: 2 },
            { data: cone.p25, color: "rgba(244,63,94,0.40)", w: 1 },
            { data: cone.p5,  color: "rgba(244,63,94,0.65)", w: 1 },
          ] as const;
          return segs.map((s, si) => {
            let d = `M${lastX.toFixed(1)},${pY(lastClose).toFixed(1)}`;
            future.forEach((_, fi) => {
              const v = s.data[fi];
              if (v !== undefined) d += `L${xOf(futureOffset + fi).toFixed(1)},${pY(v).toFixed(1)}`;
            });
            return <path key={si} d={d} fill="none" stroke={s.color} strokeWidth={s.w} />;
          });
        })()}

        {/* Bandas d15/d30 */}
        {cone && atEnd && showBands && future.length >= 30 && (() => {
          const x0 = lastX, x15 = xOf(futureOffset + 14), x30 = xOf(futureOffset + 29);
          const defs = [
            { x0, x1: x15, v: cone.p75[14], color: "rgba(34,197,94,0.80)", w: 1, dash: "4,3" },
            { x0, x1: x15, v: cone.p50[14], color: "rgba(0,212,170,1.00)", w: 2, dash: "" },
            { x0, x1: x15, v: cone.p25[14], color: "rgba(244,63,94,0.80)", w: 1, dash: "4,3" },
            { x0: x15, x1: x30, v: cone.p75[29], color: "rgba(34,197,94,0.55)", w: 1, dash: "2,3" },
            { x0: x15, x1: x30, v: cone.p50[29], color: "rgba(0,212,170,0.80)", w: 2, dash: "4,3" },
            { x0: x15, x1: x30, v: cone.p25[29], color: "rgba(244,63,94,0.55)", w: 1, dash: "2,3" },
          ];
          return (<>
            {defs.map((b, bi) => (
              <line key={bi}
                x1={b.x0.toFixed(1)} y1={pY(b.v).toFixed(1)}
                x2={b.x1.toFixed(1)} y2={pY(b.v).toFixed(1)}
                stroke={b.color} strokeWidth={b.w} strokeDasharray={b.dash}
              />
            ))}
            <line x1={x15.toFixed(1)} y1={pY(cone.p25[14]).toFixed(1)}
                  x2={x15.toFixed(1)} y2={pY(cone.p75[14]).toFixed(1)}
              stroke="rgba(255,255,255,0.10)" strokeWidth={1} strokeDasharray="2,3" />
          </>);
        })()}

        {/* ── Crosshair ─────────────────────────────────────────────── */}
        {hoverPos && !isDragging && (() => {
          const { svgX: rawX, svgY: rawY } = hoverPos;
          // Línea vertical: snapped al centro de la barra si hay barra bajo el cursor
          const lineX      = chX;
          const priceLabelW = 60;

          return (<>
            {/* Línea vertical — cubre historial + cono */}
            <line
              x1={lineX.toFixed(1)} y1={PAD.top.toString()}
              x2={lineX.toFixed(1)} y2={(PAD.top + CH + GAP + VH).toString()}
              stroke="rgba(255,255,255,0.45)" strokeWidth={0.8}
            />
            {/* Línea horizontal */}
            <line
              x1={PAD.left.toString()} y1={rawY.toFixed(1)}
              x2={(PAD.left + CW).toFixed(1)} y2={rawY.toFixed(1)}
              stroke="rgba(255,255,255,0.45)" strokeWidth={0.8}
            />

            {/* Label de precio en eje Y */}
            <rect
              x={(PAD.left - 4 - priceLabelW).toFixed(1)} y={(rawY - 9).toFixed(1)}
              width={priceLabelW} height={17} fill={C.accent} rx="3"
            />
            <text
              x={(PAD.left - 4 - priceLabelW / 2).toFixed(1)} y={(rawY + 4.5).toFixed(1)}
              textAnchor="middle" fill="#000" fontSize={9} fontFamily="monospace" fontWeight="bold"
            >
              {fmtP(chPrice)}
            </text>

            {/* Label de fecha en eje X (solo sobre barras históricas) */}
            {chBar && (
              <>
                <rect
                  x={(lineX - 26).toFixed(1)} y={(TOTAL_H - PAD.bottom + 3).toFixed(1)}
                  width="52" height="14" fill={C.accent} rx="3"
                />
                <text
                  x={lineX.toFixed(1)} y={(TOTAL_H - PAD.bottom + 13).toFixed(1)}
                  textAnchor="middle" fill="#000" fontSize={9} fontFamily="monospace" fontWeight="bold"
                >
                  {chBar.date.slice(5)}
                </text>
              </>
            )}

            {/* Caja OHLCV (solo sobre barras históricas) */}
            {chBar && (() => {
              const isGreen = chBar.adj_close >= chBar.open;
              const clr     = isGreen ? C.green : C.red;
              const bx = PAD.left + 10, by = PAD.top + 8;
              const lines = [
                { l: "A", v: `$${fmtP(chBar.open)}`,      c: clr     },
                { l: "H", v: `$${fmtP(chBar.high)}`,      c: C.green },
                { l: "L", v: `$${fmtP(chBar.low)}`,       c: C.red   },
                { l: "C", v: `$${fmtP(chBar.adj_close)}`, c: clr     },
              ];
              return (<>
                <rect x={bx} y={by} width={115} height={72}
                  fill="rgba(9,11,18,0.88)" rx="4" stroke={C.border} strokeWidth={0.8} />
                <text x={bx + 8} y={by + 14} fill={C.muted} fontSize={9} fontFamily="monospace">
                  {chBar.date}
                </text>
                {lines.map((ln, li) => (
                  <g key={li}>
                    <text x={bx + 8}  y={by + 27 + li * 13}
                      fill={C.muted} fontSize={9} fontFamily="monospace">{ln.l}</text>
                    <text x={bx + 22} y={by + 27 + li * 13}
                      fill={ln.c} fontSize={9} fontFamily="monospace" fontWeight="bold">{ln.v}</text>
                  </g>
                ))}
              </>);
            })()}

            {/* Punto de intersección en la zona del cono (sin barra histórica) */}
            {!chBar && (
              <circle cx={rawX.toFixed(1)} cy={rawY.toFixed(1)} r="3"
                fill="none" stroke="rgba(255,255,255,0.6)" strokeWidth={1} />
            )}
          </>);
        })()}

        {/* Bordes */}
        <rect x={PAD.left} y={PAD.top} width={CW} height={CH}
          fill="none" stroke={C.border} strokeWidth={1} />
        <rect x={PAD.left} y={vBase} width={CW} height={VH}
          fill="none" stroke={C.border} strokeWidth={1} />

        {/* Leyenda */}
        <g fontSize={9} fontFamily="monospace">
          {[
            { label: "── SMA20", color: C.yellow, x: PAD.left + 8 },
            { label: "── SMA50", color: C.blue,   x: PAD.left + 68 },
            { label: "╌ SMA200", color: C.purple, x: PAD.left + 130 },
            { label: "·· BB",    color: "rgba(0,212,170,0.55)", x: PAD.left + 198 },
            ...(cone && atEnd ? [{ label: "── Cono MC",  color: C.accent,                     x: PAD.left + 238 }] : []),
            ...(cone && atEnd && showBands ? [{ label: "── d15/d30", color: "rgba(34,197,94,0.85)", x: PAD.left + 308 }] : []),
          ].map((item, i) => (
            <text key={i} x={item.x} y={PAD.top - 8} fill={item.color}>{item.label}</text>
          ))}
        </g>
      </svg>
    </div>
  );
}
