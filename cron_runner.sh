#!/usr/bin/env bash
# Runner horario automático para Termómetro Digital PBA
DIR="/home/gnet/.gemini/antigravity/scratch/termometro-digital"
cd "$DIR" || exit 1

# Asegurar que el servidor local app.py esté corriendo
if ! pgrep -f "python3 app.py" > /dev/null; then
    nohup "$DIR/.venv/bin/python3" "$DIR/app.py" > "$DIR/app.log" 2>&1 &
    sleep 3
fi

# Ejecutar el ciclo de monitoreo con la sesión abierta en segundo plano
"$DIR/.venv/bin/python3" "$DIR/session_scraper.py" --headless --max-consultas 4 >> "$DIR/cron_scraper.log" 2>&1
