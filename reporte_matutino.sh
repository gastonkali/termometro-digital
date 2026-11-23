#!/usr/bin/env bash
# Runner Matutino Diario 7:00 AM — Termómetro Digital PBA
DIR="/home/gnet/.gemini/antigravity/scratch/termometro-digital"
cd "$DIR" || exit 1

# Entorno gráfico para cron
export XDG_RUNTIME_DIR="/run/user/$(id -u)"
if [ -z "$XAUTHORITY" ]; then
    export XAUTHORITY=$(ls -t /run/user/$(id -u)/.mutter-Xwaylandauth.* /home/gnet/.Xauthority 2>/dev/null | head -n 1)
fi
export DISPLAY="${DISPLAY:-:0}"
export WAYLAND_DISPLAY="${WAYLAND_DISPLAY:-wayland-0}"

# Asegurar que el servidor local app.py esté corriendo para termometro-digital
if ! curl -s http://127.0.0.1:5055/ > /dev/null; then
    nohup "$DIR/.venv/bin/python3" "$DIR/app.py" > "$DIR/app.log" 2>&1 &
    sleep 3
fi

# Asegurar que el navegador permanente con X esté abierto
if ! curl -s http://127.0.0.1:9222/json/version > /dev/null; then
    "$DIR/iniciar_navegador_permanente.sh"
    sleep 3
fi

# Esperar a que termine la corrida horaria de las 7:00 AM (si está activa) sin lanzar una duplicada
flock /tmp/termometro_scraper.lock true

# Generar y enviar el reporte consolidado de las últimas 12 horas
"$DIR/.venv/bin/python3" "$DIR/reporte_matutino.py" >> "$DIR/reporte_matutino.log" 2>&1
