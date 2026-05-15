#!/bin/bash
# ── Financial Analyzer — lanzador ─────────────────────────────────────────
#
# Uso normal (rofi / file manager / doble clic):
#   ./launch.sh           → arranca el servidor y abre la app desktop
#
# Modo navegador (para ver UI con hot-reload):
#   ./launch.sh --browser → abre http://localhost:1420 con datos de prueba

cd "$(dirname "$0")"

# Si ya hay un servidor corriendo en 1420, no lanzar otro
SERVER_RUNNING=false
if curl -s http://localhost:1420 >/dev/null 2>&1; then
  SERVER_RUNNING=true
fi

if [ "$1" = "--browser" ]; then
  echo "🌐 Modo navegador → http://localhost:1420"
  npx vite &
  VITE_PID=$!
  until curl -s http://localhost:1420 >/dev/null 2>&1; do sleep 0.3; done
  xdg-open http://localhost:1420 2>/dev/null || open http://localhost:1420 2>/dev/null || true
  wait $VITE_PID
else
  # Modo normal: sirve dist/ y abre el binario
  if [ "$SERVER_RUNNING" = "false" ]; then
    npx vite preview --port 1420 &
    VITE_PID=$!
    until curl -s http://localhost:1420 >/dev/null 2>&1; do sleep 0.3; done
  fi

  WEBKIT_DISABLE_DMABUF_RENDERER=1 ./src-tauri/target/debug/financial-analyzer

  # Cierra el servidor solo si lo arrancamos nosotros
  if [ -n "$VITE_PID" ]; then
    kill $VITE_PID 2>/dev/null
  fi
fi
