#!/usr/bin/env bash
# Runner Matutino Diario 7:00 AM — Termómetro Digital PBA
DIR="/home/gnet/.gemini/antigravity/scratch/termometro-digital"
cd "$DIR" || exit 1

# Asegurar que el servidor local app.py esté corriendo para termometro-digital
if ! pgrep -f "termometro-digital/app.py" > /dev/null; then
    nohup "$DIR/.venv/bin/python3" "$DIR/app.py" > "$DIR/app.log" 2>&1 &
    sleep 3
fi

# 1. Barrido fresco de primera hora (7 AM)
"$DIR/.venv/bin/python3" "$DIR/session_scraper.py" --headless --max-consultas 4 >> "$DIR/cron_scraper.log" 2>&1

# 2. Generar y enviar el reporte consolidado de las últimas 12 horas
"$DIR/.venv/bin/python3" "$DIR/reporte_matutino.py" >> "$DIR/reporte_matutino.log" 2>&1
