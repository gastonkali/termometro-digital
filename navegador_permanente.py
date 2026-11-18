# -*- coding: utf-8 -*-
"""
Navegador permanente para Termómetro Digital PBA.
Mantiene una ventana de Chrome / Brave abierta en el escritorio con pestañas
activas en X (Twitter), Facebook e Instagram.
Permite que el scraper se conecte vía CDP (puerto 9222) sin abrir ni cerrar
ventanas a cada rato, evitando que X dispare chequeos anti-bot.
"""

import os
import signal
import sys
import time
from playwright.sync_api import sync_playwright

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SESSION_DIR = os.path.join(BASE_DIR, "user_session_browser")
CDP_PORT = 9222

_running = True


def handle_signal(sig, frame):
    global _running
    print(f"\nSeñal recibida ({sig}). Cerrando navegador permanente...")
    _running = False


signal.signal(signal.SIGINT, handle_signal)
signal.signal(signal.SIGTERM, handle_signal)


def main():
    print("=======================================================")
    print("🌐 INICIANDO NAVEGADOR PERMANENTE — Termómetro Digital")
    print(f"Puerto de depuración remota: {CDP_PORT}")
    print("Pestaña activa permanente: https://x.com/home")
    print("=======================================================\n")

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=SESSION_DIR,
            headless=False,
            viewport={"width": 1280, "height": 850},
            permissions=["clipboard-read", "clipboard-write"],
            args=[
                f"--remote-debugging-port={CDP_PORT}",
                "--disable-blink-features=AutomationControlled",
                "--start-maximized"
            ]
        )

        # Pestaña 1: X (Twitter)
        page_x = context.pages[0] if context.pages else context.new_page()
        page_x.goto("https://x.com/home", wait_until="domcontentloaded")
        print("✓ Pestaña de X cargada.")

        # Pestaña 2: Facebook
        page_fb = context.new_page()
        page_fb.goto("https://www.facebook.com", wait_until="domcontentloaded")
        print("✓ Pestaña de Facebook cargada.")

        # Pestaña 3: Instagram
        page_ig = context.new_page()
        page_ig.goto("https://www.instagram.com", wait_until="domcontentloaded")
        print("✓ Pestaña de Instagram cargada.")

        print("\n🚀 Navegador permanente activo. Podés minimizar esta ventana si querés.")
        print("El scraper se conectará automáticamente a estas pestañas en cada corrida.")

        while _running:
            if len(context.pages) == 0:
                print("Todas las pestañas fueron cerradas por el usuario.")
                break
            time.sleep(5)

        context.close()
        print("Navegador permanente cerrado.")


if __name__ == "__main__":
    main()
