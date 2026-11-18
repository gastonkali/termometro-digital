#!/usr/bin/env bash
# Inicia el navegador permanente en segundo plano con DISPLAY=:0
DIR="/home/gnet/.gemini/antigravity/scratch/termometro-digital"
cd "$DIR" || exit 1

if curl -s http://127.0.0.1:9222/json/version > /dev/null; then
    echo "El navegador permanente ya está corriendo en el puerto 9222."
    exit 0
fi

DISPLAY="${DISPLAY:-:0}" nohup "$DIR/.venv/bin/python3" "$DIR/navegador_permanente.py" > "$DIR/navegador.log" 2>&1 &
echo "Iniciando navegador permanente con ventana de X abierta..."
sleep 3
