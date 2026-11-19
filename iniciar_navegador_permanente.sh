#!/usr/bin/env bash
# Inicia el navegador permanente en segundo plano con entorno gráfico adecuado
DIR="/home/gnet/.gemini/antigravity/scratch/termometro-digital"
cd "$DIR" || exit 1

# Exportar variables gráficas para cron o sesiones no interactivas
export XDG_RUNTIME_DIR="/run/user/$(id -u)"
if [ -z "$XAUTHORITY" ]; then
    export XAUTHORITY=$(ls -t /run/user/$(id -u)/.mutter-Xwaylandauth.* /home/gnet/.Xauthority 2>/dev/null | head -n 1)
fi
export DISPLAY="${DISPLAY:-:0}"
export WAYLAND_DISPLAY="${WAYLAND_DISPLAY:-wayland-0}"

if curl -s http://127.0.0.1:9222/json/version > /dev/null; then
    echo "El navegador permanente ya está corriendo en el puerto 9222."
    exit 0
fi

nohup "$DIR/.venv/bin/python3" -u "$DIR/navegador_permanente.py" >> "$DIR/navegador.log" 2>&1 &
echo "Iniciando navegador permanente con ventana de X abierta..."
sleep 4
