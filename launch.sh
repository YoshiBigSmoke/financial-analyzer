#!/bin/bash
cd "$(dirname "$0")"

# Arranca Vite preview (puerto y no-cache definidos en vite.config.ts)
npx vite preview &
VITE_PID=$!

# Espera a que el servidor esté listo
until curl -s http://localhost:1420 > /dev/null 2>&1; do
    sleep 0.3
done

# Lanza la app
WEBKIT_DISABLE_DMABUF_RENDERER=1 ./src-tauri/target/debug/financial-analyzer

# Cierra el servidor al salir
kill $VITE_PID 2>/dev/null
