#!/usr/bin/env bash
# Runner horario automático para Termómetro Digital PBA
DIR="/home/gnet/.gemini/antigravity/scratch/termometro-digital"
cd "$DIR" || exit 1

# Entorno gráfico para cron
export XDG_RUNTIME_DIR="/run/user/$(id -u)"
if [ -z "$XAUTHORITY" ]; then
    export XAUTHORITY=$(ls -t /run/user/$(id -u)/.mutter-Xwaylandauth.* /home/gnet/.Xauthority 2>/dev/null | head -n 1)
fi
export DISPLAY="${DISPLAY:-:0}"
export WAYLAND_DISPLAY="${WAYLAND_DISPLAY:-wayland-0}"

# 1. Asegurar que el servidor local app.py esté corriendo para termometro-digital
if ! curl -s http://127.0.0.1:5055/ > /dev/null; then
    nohup "$DIR/.venv/bin/python3" "$DIR/app.py" > "$DIR/app.log" 2>&1 &
    sleep 3
fi

# 2. Asegurar que el navegador permanente con X esté abierto
if ! curl -s http://127.0.0.1:9222/json/version > /dev/null; then
    "$DIR/iniciar_navegador_permanente.sh"
    sleep 3
fi

# 3. Ejecutar el ciclo de monitoreo con bloqueo exclusivo (evita corridas duplicadas simultáneas)
flock -n /tmp/termometro_scraper.lock "$DIR/.venv/bin/python3" "$DIR/session_scraper.py" --max-consultas 4 >> "$DIR/cron_scraper.log" 2>&1
