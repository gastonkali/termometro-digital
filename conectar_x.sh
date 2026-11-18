#!/usr/bin/env bash
# Script para conectar o cambiar cuenta de X (Twitter) en Termómetro Digital PBA
DIR="/home/gnet/.gemini/antigravity/scratch/termometro-digital"
cd "$DIR" || exit 1
DISPLAY="${DISPLAY:-:0}" "$DIR/.venv/bin/python3" "$DIR/session_scraper.py" --login-x
