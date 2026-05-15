#!/bin/bash
# ── Financial Analyzer — lanzador ─────────────────────────────────────────
#
# Uso:
#   ./launch.sh           → app desktop Tauri (datos reales, requiere build)
#   ./launch.sh --browser → modo navegador en http://localhost:1420
#                           (datos de prueba, hot-reload, sin compilar Tauri)

cd "$(dirname "$0")"

if [ "$1" = "--browser" ]; then
  echo "🌐 Abriendo en modo navegador → http://localhost:1420"
  echo "   Los cambios en src/ se reflejan al instante (hot-reload)."
  echo "   Datos: modo preview (VOO de muestra). Para datos reales usa Tauri."
  echo ""
  # Arranca Vite y abre el navegador cuando esté listo
  npx vite &
  VITE_PID=$!
  until curl -s http://localhost:1420 >/dev/null 2>&1; do
    sleep 0.3
  done
  xdg-open http://localhost:1420 2>/dev/null || open http://localhost:1420 2>/dev/null || true
  wait $VITE_PID
else
  echo "🖥  Abriendo app desktop (Tauri)..."
  # Arranca Vite preview y el binario Tauri compilado
  npx vite preview &
  VITE_PID=$!
  until curl -s http://localhost:1420 >/dev/null 2>&1; do
    sleep 0.3
  done
  WEBKIT_DISABLE_DMABUF_RENDERER=1 ./src-tauri/target/debug/financial-analyzer
  kill $VITE_PID 2>/dev/null
fi
