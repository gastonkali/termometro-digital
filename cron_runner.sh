#!/usr/bin/env bash
# Runner horario automático para Termómetro Digital PBA
DIR="/home/gnet/.gemini/antigravity/scratch/termometro-digital"
cd "$DIR" || exit 1

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

# 3. Ejecutar el ciclo de monitoreo (se conecta vía CDP a la ventana abierta sin cerrarla)
"$DIR/.venv/bin/python3" "$DIR/session_scraper.py" --max-consultas 4 >> "$DIR/cron_scraper.log" 2>&1
