# -*- coding: utf-8 -*-
"""
Módulo de recolección automatizada con sesión de usuario vía Playwright.
Utiliza un perfil persistente ('user_session_browser') o clona las cookies de sesión
para navegar en Facebook, X (Twitter) e Instagram en vivo con tu cuenta abierta,
leyendo el feed de búsqueda, textos completos y comentarios de vecinos.
"""

import argparse
import json
import os
import sys
import time
from typing import Any, Dict, List, Optional
import requests
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

BASE_DIR = os.path.dirname(__file__)
SESSION_DIR = os.path.join(BASE_DIR, "user_session_browser")
os.makedirs(SESSION_DIR, exist_ok=True)

API_INGEST_URL = "http://127.0.0.1:5055/api/ingest"


def lanzar_navegador_sesion(headless: bool = False):
    """
    Inicia un contexto de navegador persistente donde tus sesiones
    de Facebook, X e Instagram quedan guardadas.
    """
    p = sync_playwright().start()
    context = p.chromium.launch_persistent_context(
        user_data_dir=SESSION_DIR,
        headless=headless,
        channel="chrome",  # Usa el Chrome nativo instalado en Windows
        viewport={"width": 1280, "height": 850},
        args=[
            "--disable-blink-features=AutomationControlled",
            "--start-maximized"
        ]
    )
    return p, context


def extraer_posteos_facebook(page, url_busqueda: str, max_items: int = 8) -> List[Dict[str, Any]]:
    """
    Navega a la URL de búsqueda de Facebook, hace scroll y extrae
    texto de publicaciones y comentarios.
    """
    posteos = []
    try:
        page.goto(url_busqueda, timeout=35000, wait_until="domcontentloaded")
        time.sleep(3.5)

        # Hacer 2-3 scrolls hacia abajo para cargar resultados recientes
        for _ in range(3):
            page.mouse.wheel(0, 1500)
            time.sleep(1.5)

        # Buscar contenedores de publicaciones de Facebook
        # En Facebook web las publicaciones suelen estar en roles feed/article o bloques con texto
        elementos = page.locator('div[role="feed"] > div, div[role="article"]').all()
        if not elementos:
            elementos = page.locator('div[data-ad-preview="message"], div[dir="auto"]').all()

        for el in elementos[:max_items]:
            try:
                texto_completo = el.inner_text().strip()
                if len(texto_completo) < 30:
                    continue

                lineas = [l.strip() for l in texto_completo.split("\n") if l.strip()]
                autor = lineas[0] if lineas else "Usuario Facebook"
                
                # Intentar buscar enlace directo a la publicación
                enlace = page.url
                a_tags = el.locator('a[href*="/posts/"], a[href*="/permalink/"], a[href*="facebook.com"]').all()
                if a_tags:
                    href = a_tags[0].get_attribute("href")
                    if href:
                        enlace = href if href.startswith("http") else f"https://www.facebook.com{href}"

                posteos.append({
                    "fuente": "Facebook (Sesión Abierta)",
                    "autor": autor,
                    "url": enlace,
                    "titulo": f"Alerta en Facebook: {lineas[0][:60]}",
                    "texto": texto_completo,
                    "fecha_publicacion": "Detectado en vivo con mi sesión"
                })
            except Exception:
                continue

    except Exception as e:
        print(f"[Facebook Session] Error navegando: {e}")

    return posteos


def extraer_posteos_twitter(page, url_busqueda: str, max_items: int = 8) -> List[Dict[str, Any]]:
    """
    Navega a la búsqueda de X/Twitter en vivo y extrae tweets recientes.
    """
    tweets = []
    try:
        page.goto(url_busqueda, timeout=35000, wait_until="domcontentloaded")
        time.sleep(3)

        for _ in range(2):
            page.mouse.wheel(0, 1200)
            time.sleep(1.5)

        articulos = page.locator('article[data-testid="tweet"]').all()
        for art in articulos[:max_items]:
            try:
                texto = art.inner_text().strip()
                if len(texto) < 25:
                    continue
                
                enlace = page.url
                links = art.locator('a[href*="/status/"]').all()
                if links:
                    href = links[0].get_attribute("href")
                    if href:
                        enlace = f"https://x.com{href}" if not href.startswith("http") else href

                tweets.append({
                    "fuente": "X / Twitter (Sesión Abierta)",
                    "autor": texto.split("\n")[0] if "\n" in texto else "Usuario X",
                    "url": enlace,
                    "titulo": f"Tweet detectado: {texto[:60]}",
                    "texto": texto,
                    "fecha_publicacion": "En vivo"
                })
            except Exception:
                continue
    except Exception as e:
        print(f"[X Session] Error navegando: {e}")

    return tweets


def ejecutar_ciclo_recoleccion(headless: bool = False, max_consultas: int = 6):
    """
    Ejecuta el ciclo de búsquedas en Facebook y X con tu sesión abierta.
    """
    from engine import generar_matriz_consultas_multired

    print(f"🚀 Iniciando navegador con sesión guardada en: {SESSION_DIR}")
    print(f"Modo Headless: {headless}")

    p, context = lanzar_navegador_sesion(headless=headless)
    page = context.new_page()

    matriz = generar_matriz_consultas_multired()[:max_consultas]
    total_recolectados = []

    try:
        for idx, item in enumerate(matriz, 1):
            print(f"\n[{idx}/{len(matriz)}] Buscando en Facebook: {item['fb_search_query']}...")
            fb_posts = extraer_posteos_facebook(page, item["fb_url"], max_items=4)
            for p_item in fb_posts:
                p_item["partido"] = item["partido"]
                p_item["pasada"] = item["pasada"]
                p_item["categoria"] = item["categoria"]
            total_recolectados.extend(fb_posts)

            if item.get("tw_url"):
                print(f"[{idx}/{len(matriz)}] Buscando en X: {item['partido']}...")
                tw_posts = extraer_posteos_twitter(page, item["tw_url"], max_items=3)
                for t_item in tw_posts:
                    t_item["partido"] = item["partido"]
                    t_item["pasada"] = item["pasada"]
                    t_item["categoria"] = item["categoria"]
                total_recolectados.extend(tw_posts)

            time.sleep(1.5)

    finally:
        context.close()
        p.stop()

    print(f"\n✓ Recolección finalizada. Total de publicaciones capturadas: {len(total_recolectados)}")

    if total_recolectados:
        try:
            resp = requests.post(API_INGEST_URL, json={
                "modo": "sesion_abierta_playwright",
                "posteos": total_recolectados
            }, timeout=15)
            print("Resultado de ingesta en base local:", resp.json())
        except Exception as e:
            print("Error enviando al backend:", e)


def modo_login():
    """
    Abre el navegador en modo visible para que inicies sesión
    en Facebook, X e Instagram una única vez si no lo hiciste todavía.
    """
    print("\n=======================================================")
    print("🔑 MODO INICIO DE SESIÓN — Termómetro Digital PBA")
    print("Se abrirá una ventana de Chrome.")
    print("Iniciá sesión en Facebook, X (Twitter) e Instagram.")
    print("Tus sesiones quedarán guardadas permanentemente en este perfil.")
    print("Cuando termines de loguearte, cerrá la ventana del navegador.")
    print("=======================================================\n")

    p, context = lanzar_navegador_sesion(headless=False)
    page = context.new_page()
    page.goto("https://www.facebook.com")
    
    # Abrir pestañas para X e Instagram
    page_x = context.new_page()
    page_x.goto("https://x.com/login")

    page_ig = context.new_page()
    page_ig.goto("https://www.instagram.com")

    print("Esperando a que cierres el navegador para guardar las cookies...")
    try:
        # Espera hasta que todas las páginas se hayan cerrado manualmente
        while len(context.pages) > 0:
            time.sleep(1)
    except Exception:
        pass
    finally:
        context.close()
        p.stop()
        print("✓ Sesiones guardadas correctamente en user_session_browser.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scraper con sesión abierta para Termómetro Digital")
    parser.add_argument("--login", action="store_true", help="Abrir navegador para iniciar sesión una única vez")
    parser.add_argument("--headless", action="store_true", help="Correr en segundo plano sin ventana visible")
    parser.add_argument("--max-consultas", type=int, default=5, help="Cantidad de consultas a ejecutar")
    args = parser.parse_args()

    if args.login:
        modo_login()
    else:
        ejecutar_ciclo_recoleccion(headless=args.headless, max_consultas=args.max_consultas)
