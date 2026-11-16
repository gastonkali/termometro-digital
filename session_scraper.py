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
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
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
    launch_kwargs = {
        "user_data_dir": SESSION_DIR,
        "headless": headless,
        "viewport": {"width": 1280, "height": 850},
        "args": [
            "--disable-blink-features=AutomationControlled",
            "--start-maximized"
        ]
    }
    try:
        context = p.chromium.launch_persistent_context(
            **launch_kwargs,
            channel="chrome"
        )
    except Exception:
        context = p.chromium.launch_persistent_context(
            **launch_kwargs
        )
    return p, context


import re
import urllib.parse


def limpiar_url_fb(href: str) -> str:
    """
    Limpia y normaliza URLs de Facebook para que lleven directamente
    al posteo, foto, video o perfil del autor sin parámetros de búsqueda generales.
    """
    if not href or "/search/" in href:
        return ""
    # Si es enlace a foto con fbid
    if "/photo/" in href and "fbid=" in href:
        m = re.search(r"fbid=([0-9]+)", href)
        if m:
            return f"https://www.facebook.com/photo/?fbid={m.group(1)}"
    # Si es perfil por id
    if "profile.php" in href and "id=" in href:
        m = re.search(r"id=([0-9]+)", href)
        if m:
            return f"https://www.facebook.com/profile.php?id={m.group(1)}"
    # Si es permalink de post o grupo
    if "/posts/" in href or "/permalink/" in href or "/stories/" in href:
        return href.split("?")[0]
    if "/groups/" in href:
        return href.split("?")[0]
    # Si es perfil de página o usuario
    if href.startswith("https://www.facebook.com/"):
        slug = href.replace("https://www.facebook.com/", "").split("?")[0].strip("/")
        if slug and slug not in ["search", "home.php", "login", "watch", "messages"]:
            return f"https://www.facebook.com/{slug}"
    return href.split("?")[0] if href else ""


def extraer_comentarios_twitter(context, tweet_url: str, max_replies: int = 3) -> Tuple[List[str], str]:
    """
    Abre el tweet directo en una pestaña en segundo plano, extrae el texto completo
    sin truncar y las respuestas/comentarios reales de los vecinos.
    """
    if not tweet_url or "/status/" not in tweet_url:
        return [], ""
    replies = []
    main_text = ""
    p_tab = None
    try:
        p_tab = context.new_page()
        p_tab.goto(tweet_url, timeout=18000, wait_until="domcontentloaded")
        time.sleep(2.5)
        p_tab.mouse.wheel(0, 400)
        time.sleep(1)

        res = p_tab.evaluate(r"""() => {
            const out = [];
            const arts = document.querySelectorAll('article[data-testid="tweet"]');
            let mainTxt = '';
            if (arts.length > 0) {
                const mainEl = arts[0].querySelector('[data-testid="tweetText"]');
                if (mainEl) mainTxt = (mainEl.innerText || '').trim();
            }
            for (let i = 1; i < arts.length && out.length < 3; i++) {
                const userEl = arts[i].querySelector('[data-testid="User-Name"]');
                const user = userEl ? userEl.innerText.split('\n')[0] : 'Vecino';
                const textEl = arts[i].querySelector('[data-testid="tweetText"]');
                if (textEl) {
                    const txt = (textEl.innerText || '').trim().replace(/\n+/g, ' ');
                    if (txt.length > 5) {
                        out.push(`${user}: "${txt}"`);
                    }
                }
            }
            return { replies: out, mainText: mainTxt };
        }""")
        replies = res.get("replies", [])
        main_text = res.get("mainText", "")
    except Exception:
        pass
    finally:
        if p_tab:
            try:
                p_tab.close()
            except Exception:
                pass
    return replies, main_text


def extraer_comentarios_facebook(context, post_url: str, max_comentarios: int = 4) -> List[str]:
    """
    Abre la URL directa del posteo en una pestaña en segundo plano y extrae
    los comentarios reales de los vecinos.
    """
    if not post_url or "facebook.com/search/" in post_url:
        return []
    if not any(k in post_url for k in ["/photo/", "/posts/", "/permalink/", "fbid=", "/groups/"]):
        return []

    comentarios = []
    p_tab = None
    try:
        p_tab = context.new_page()
        p_tab.goto(post_url, timeout=20000, wait_until="domcontentloaded")
        time.sleep(3)
        p_tab.mouse.wheel(0, 500)
        time.sleep(1)

        comentarios = p_tab.evaluate(r"""() => {
            const out = [];
            const commentNodes = document.querySelectorAll('div[aria-label*="Comentario"], div[aria-label*="Comment"]');
            const nodes = commentNodes.length > 0 ? commentNodes : document.querySelectorAll('div[role="article"], ul > li div[dir="auto"]');
            for (const n of nodes) {
                const txt = (n.innerText || '').trim();
                if (!txt || txt.length < 8 || txt.length > 400) continue;
                const lines = txt.split('\n').map(l => l.trim()).filter(l => l && !['Responder', 'Me gusta', 'Compartir', 'Ver más', 'Ver traducción'].includes(l));
                if (lines.length > 0) {
                    const clean = lines.join(' - ');
                    if (clean.length > 8 && !out.includes(clean)) {
                        out.push(clean);
                    }
                }
            }
            return out.slice(0, 4);
        }""")
    except Exception as e:
        print(f"  [Aviso FB Comentarios]: {e}")
    finally:
        if p_tab:
            try:
                p_tab.close()
            except Exception:
                pass
    return comentarios


def extraer_posteos_facebook(page, url_busqueda: str, max_items: int = 8) -> List[Dict[str, Any]]:
    """
    Navega a la URL de búsqueda de Facebook, hace scroll y extrae
    texto real de publicaciones, imágenes adjuntas y comentarios de vecinos.
    """
    from config_pba import es_exclusion_geografica, es_texto_espanol

    posteos = []
    try:
        page.goto(url_busqueda, timeout=35000, wait_until="domcontentloaded")
        time.sleep(3.5)

        for _ in range(3):
            page.mouse.wheel(0, 1500)
            time.sleep(1.5)

        # Expandir botones "Ver más" para no perder texto cortado
        try:
            page.evaluate(r"""() => {
                const buttons = document.querySelectorAll('div[role="button"], span[role="button"], a[role="button"]');
                for (const b of buttons) {
                    const txt = (b.innerText || '').trim();
                    if (txt === 'Ver más' || txt === 'See more') {
                        try { b.click(); } catch(e) {}
                    }
                }
            }""")
            time.sleep(0.8)
        except Exception:
            pass

        raw_items = page.evaluate(r"""() => {
            const results = [];
            const seen = new Set();
            const main = document.querySelector('div[role="main"]') || document.body;

            // 1. Recorrer tarjetas directas del feed
            const feed = main.querySelector('div[role="feed"]');
            const cards = feed ? Array.from(feed.children) : Array.from(main.querySelectorAll('div[role="article"]'));

            for (const card of cards) {
                const rawLines = (card.innerText || '').split('\n').map(l => {
                    return l.replace(/Ver más/gi, '').replace(/See more/gi, '').replace(/\.\.\.$/, '').trim();
                }).filter(l => {
                    if (!l || l.length < 3 || l === 'Facebook' || l === '·' || l === 'Seguir' || l === 'Unirte') return false;
                    if (l.includes('Publicación compartida') || l.includes('Contenido sensible') || l.includes('Puede ser una imagen')) return false;
                    if (/^\d+$/.test(l)) return false;
                    if (l.length < 15 && l.includes('\u034f')) return false;
                    return true;
                });

                if (rawLines.length === 0) continue;
                const autor = rawLines[0];
                const bodyLines = rawLines.slice(1).filter(l => l.length > 5 && !l.includes('de 202'));
                const texto = bodyLines.join('\n');
                if (texto.length < 30 || seen.has(texto)) continue;
                seen.add(texto);

                let imgUrl = '';
                const imgs = Array.from(card.querySelectorAll('img'));
                for (const im of imgs) {
                    const s = im.src || '';
                    if (s && (s.includes('scontent') || s.includes('external.') || s.includes('fbcdn.net')) && !s.includes('emoji') && !s.includes('rsrc') && !s.includes('static')) {
                        const w = im.naturalWidth || im.width || 0;
                        const h = im.naturalHeight || im.height || 0;
                        if (w > 120 || h > 90 || (!w && !s.includes('p32x32') && !s.includes('p40x40') && !s.includes('p50x50'))) {
                            imgUrl = s;
                            break;
                        }
                    }
                }

                let directUrl = '';
                const links = Array.from(card.querySelectorAll('a[href]'));
                for (const a of links) {
                    const h = a.href || '';
                    if (!h || h.includes('/search/')) continue;
                    if (h.includes('/photo/') || h.includes('/posts/') || h.includes('/permalink/') || h.includes('fbid=') || h.includes('/videos/')) {
                        directUrl = h;
                        break;
                    }
                }
                if (!directUrl) {
                    for (const a of links) {
                        const h = a.href || '';
                        if (h && !h.includes('/search/') && !h.includes('/hashtag/') && !h.includes('/login') && !h.includes('/home.php')) {
                            directUrl = h;
                            break;
                        }
                    }
                }

                results.push({
                    autor: autor,
                    texto: texto,
                    url: directUrl,
                    imgUrl: imgUrl
                });
            }

            // 2. Fallback con divs de texto si el feed arrojó pocos
            if (results.length < 3) {
                const textElements = main.querySelectorAll('div[dir="auto"]');
                for (const el of textElements) {
                    const text = (el.innerText || '').trim();
                    if (text.length < 40 || seen.has(text)) continue;
                    if (text.includes('Resultados de') || text.includes('Filtros') || text.includes('Facebook')) continue;
                    if (text.startsWith('Amigos') || text.startsWith('Grupos')) continue;
                    seen.add(text);

                    let directUrl = '';
                    let autor = "Vecinos en Facebook";
                    let imgUrl = '';

                    let cur = el;
                    for (let i = 0; i < 8 && cur; i++) {
                        const links = Array.from(cur.querySelectorAll('a[href]'));
                        for (const a of links) {
                            const h = a.href;
                            if (!h || h.includes('/search/')) continue;
                            if (h.includes('/photo/') || h.includes('/posts/') || h.includes('/permalink/') || h.includes('/stories/') || h.includes('fbid=')) {
                                if (!directUrl) directUrl = h;
                            }
                            if (h.includes('/groups/') && !directUrl) {
                                directUrl = h;
                            }
                            const authorText = (a.innerText || '').trim();
                            if (authorText && authorText.length < 50 && !authorText.includes('Facebook') && !authorText.includes('foto') && !authorText.startsWith('Puede ser') && !authorText.includes('Indicador') && !authorText.includes('Activo') && !authorText.includes('+')) {
                                if (autor === "Vecinos en Facebook") autor = authorText;
                                if (!directUrl && !h.includes('/search/')) directUrl = h;
                            }
                        }

                        if (!imgUrl) {
                            const imgs = Array.from(cur.querySelectorAll('img'));
                            for (const im of imgs) {
                                const s = im.src || '';
                                if (!s || s.includes('emoji') || s.includes('rsrc') || s.includes('static')) continue;
                                if (s.includes('p32x32') || s.includes('p40x40') || s.includes('p50x50') || s.includes('p60x60')) continue;
                                if (s.includes('scontent') || s.includes('external.') || s.includes('fbcdn.net')) {
                                    const w = im.naturalWidth || im.width || 0;
                                    const h = im.naturalHeight || im.height || 0;
                                    if (w > 120 || h > 90 || (!w && !s.includes('emoji'))) {
                                        imgUrl = s;
                                        break;
                                    }
                                }
                            }
                        }
                        cur = cur.parentElement;
                    }

                    results.push({
                        autor: autor,
                        texto: text,
                        url: directUrl,
                        imgUrl: imgUrl
                    });
                }
            }

            return results;
        }""")

        for item in raw_items:
            txt = item.get("texto", "").strip()
            if not txt or len(txt) < 35:
                continue
            if not es_texto_espanol(txt):
                continue
            if es_exclusion_geografica(txt):
                continue

            autor = item.get("autor") or "Vecinos en Facebook"
            primer_renglon = txt.split("\n")[0][:75].strip()
            url_final = limpiar_url_fb(item.get("url"))

            # Extraer comentarios reales si hay URL directa de post/foto
            comentarios = []
            if url_final and any(k in url_final for k in ["/photo/", "/posts/", "/permalink/", "fbid="]):
                print(f"  💬 Extrayendo comentarios de vecinos para: {autor}...")
                comentarios = extraer_comentarios_facebook(page.context, url_final, max_comentarios=4)

            texto_con_comentarios = txt
            if comentarios:
                texto_con_comentarios += "\n\n💬 Comentarios destacados de vecinos:\n" + "\n".join(f"• {c}" for c in comentarios)

            # Si no hay URL directa, usar perfil del autor o grupo directo
            if not url_final:
                url_final = f"https://www.facebook.com/search/posts?q={urllib.parse.quote(autor)}"

            posteos.append({
                "fuente": "Facebook (Sesión Abierta)",
                "autor": autor,
                "url": url_final,
                "titulo": f"{autor}: {primer_renglon}",
                "texto": texto_con_comentarios,
                "comentarios": comentarios,
                "imagen_url": item.get("imgUrl", ""),
                "fecha_publicacion": "Detectado en vivo con mi sesión"
            })
            if len(posteos) >= max_items:
                break

    except Exception as e:
        print(f"[Facebook Session] Error navegando: {e}")

    return posteos


def extraer_posteos_twitter(page, url_busqueda: str, max_items: int = 8) -> List[Dict[str, Any]]:
    """
    Navega a la búsqueda de X/Twitter en vivo y extrae tweets recientes en español de PBA.
    """
    from config_pba import es_exclusion_geografica, es_texto_espanol

    tweets = []
    try:
        # Asegurar parámetros de idioma español y excluir CABA / Córdoba / Madrid
        if "lang%3Aes" not in url_busqueda and "lang:es" not in url_busqueda:
            url_busqueda += "+lang%3Aes+-filter%3Areplies+-CABA+-Cordoba+-Madrid"

        page.goto(url_busqueda, timeout=35000, wait_until="domcontentloaded")
        time.sleep(3)

        for _ in range(2):
            page.mouse.wheel(0, 1200)
            time.sleep(1.5)

        articulos = page.locator('article[data-testid="tweet"]').all()
        for art in articulos:
            try:
                # Expandir si está cortado con "Mostrar más"
                show_more = art.locator('[data-testid="tweet-text-show-more-link"]').first
                if show_more.count():
                    try:
                        show_more.click()
                        time.sleep(0.3)
                    except Exception:
                        pass

                # Extraer texto del tweet
                text_el = art.locator('[data-testid="tweetText"]').first
                if not text_el.count():
                    continue
                texto = text_el.inner_text().strip()
                if len(texto) < 25:
                    continue

                # Filtrar idioma estrictamente español
                if not es_texto_espanol(texto):
                    continue

                # Filtrar exclusión geográfica de PBA
                if es_exclusion_geografica(texto):
                    continue

                # Extraer autor real
                author_el = art.locator('[data-testid="User-Name"]').first
                autor = author_el.inner_text().split("\n")[0].strip() if author_el.count() else "Usuario X"

                # Enlace directo al tweet
                enlace = page.url
                links = art.locator('a[href*="/status/"]').all()
                if links:
                    href = links[0].get_attribute("href")
                    if href:
                        enlace = f"https://x.com{href}" if not href.startswith("http") else href

                img_el = art.locator('div[data-testid="tweetPhoto"] img').first
                img_url = img_el.get_attribute("src") if img_el.count() else ""

                comentarios_tw = []
                if enlace and "/status/" in enlace and len(tweets) < 3:
                    print(f"  💬 Extrayendo respuestas de vecinos y texto completo en X para: {autor}...")
                    comentarios_tw, texto_full = extraer_comentarios_twitter(page.context, enlace, max_replies=3)
                    if texto_full and len(texto_full) > len(texto):
                        texto = texto_full

                texto_con_comentarios = texto
                if comentarios_tw:
                    texto_con_comentarios += "\n\n💬 Comentarios destacados de vecinos:\n" + "\n".join(f"• {c}" for c in comentarios_tw)

                primer_renglon = texto.split("\n")[0][:75].strip()
                tweets.append({
                    "fuente": "X / Twitter (Sesión Abierta)",
                    "autor": autor,
                    "url": enlace,
                    "titulo": f"{autor}: {primer_renglon}",
                    "texto": texto_con_comentarios,
                    "comentarios": comentarios_tw,
                    "imagen_url": img_url,
                    "fecha_publicacion": "En vivo"
                })
                if len(tweets) >= max_items:
                    break
            except Exception:
                continue
    except Exception as e:
        print(f"[X Session] Error navegando: {e}")

    return tweets


def extraer_posteos_facebook_grupos(page, max_grupos: int = 4, max_items_por_grupo: int = 2) -> List[Dict[str, Any]]:
    """
    Navega a los grupos de los que es miembro el usuario (policiales y vecinales)
    y al feed consolidado de grupos, extrayendo reclamos, alertas e interacciones.
    """
    from config_pba import es_exclusion_geografica, es_texto_espanol
    from engine import detectar_partido_en_texto

    GRUPOS_USUARIO = [
        # Policiales Bonaerenses
        {"nombre": "Policiales Bahia", "url": "https://www.facebook.com/groups/policialesbahiaok/", "categoria": "seguridad"},
        {"nombre": "RUMORES POLICIALES", "url": "https://www.facebook.com/groups/990924476974016/", "categoria": "seguridad"},
        {"nombre": "RUMORES POLICÍA BS. AS.", "url": "https://www.facebook.com/groups/922738057507400/", "categoria": "seguridad"},
        {"nombre": "Permutas Policía Bonaerense y Local", "url": "https://www.facebook.com/groups/205011000866057/", "categoria": "seguridad"},
        # Vecinales Conectados de PBA
        {"nombre": "Lomas Conectado", "url": "https://www.facebook.com/groups/lomasconectado/", "categoria": "seguridad"},
        {"nombre": "Vecinos de Avellaneda", "url": "https://www.facebook.com/groups/331221260013652/", "categoria": "seguridad"},
        {"nombre": "San Vicente Conectado", "url": "https://www.facebook.com/groups/sanvicenteconectado/", "categoria": "seguridad"},
        {"nombre": "Banfield Conectado", "url": "https://www.facebook.com/groups/banfieldconectado/", "categoria": "seguridad"},
        {"nombre": "Bella Vista Conectado", "url": "https://www.facebook.com/groups/515289091959193/", "categoria": "seguridad"},
        {"nombre": "Moreno Conectado", "url": "https://www.facebook.com/groups/846636522073940/", "categoria": "seguridad"},
        {"nombre": "Vecinos de Villa Adelina", "url": "https://www.facebook.com/groups/vecinosadelina/", "categoria": "seguridad"},
        {"nombre": "José C. Paz Conectado", "url": "https://www.facebook.com/groups/1958608358362843/", "categoria": "seguridad"},
        {"nombre": "Del Viso / Alberti Conectados", "url": "https://www.facebook.com/groups/708319824599208/", "categoria": "seguridad"},
        {"nombre": "Grand Bourg Conectado", "url": "https://www.facebook.com/groups/260758975428433/", "categoria": "seguridad"},
        {"nombre": "Budge Conectado", "url": "https://www.facebook.com/groups/budgeconectado/", "categoria": "seguridad"},
        {"nombre": "Feed General de Grupos", "url": "https://www.facebook.com/groups/feed/", "categoria": "seguridad"},
    ]

    state_file = os.path.join(BASE_DIR, "scraper_state.json")
    idx_g = 0
    if os.path.exists(state_file):
        try:
            with open(state_file, "r", encoding="utf-8") as sf:
                sdata = json.load(sf)
                idx_g = sdata.get("proximo_grupo_idx", 0) % len(GRUPOS_USUARIO)
        except Exception:
            idx_g = 0

    grupos_a_visitar = [GRUPOS_USUARIO[(idx_g + i) % len(GRUPOS_USUARIO)] for i in range(max_grupos)]
    try:
        sdata = {}
        if os.path.exists(state_file):
            with open(state_file, "r", encoding="utf-8") as sf:
                sdata = json.load(sf)
        sdata["proximo_grupo_idx"] = (idx_g + max_grupos) % len(GRUPOS_USUARIO)
        with open(state_file, "w", encoding="utf-8") as sf:
            json.dump(sdata, sf, indent=2)
    except Exception:
        pass

    posteos = []

    for g_info in grupos_a_visitar:
        g_nombre = g_info["nombre"]
        g_url = g_info["url"]
        try:
            print(f"  👥 Explorando grupo: {g_nombre} ({g_url})...")
            page.goto(g_url, timeout=30000, wait_until="domcontentloaded")
            time.sleep(3.5)
            for _ in range(3):
                page.mouse.wheel(0, 1500)
                time.sleep(1)

            try:
                page.evaluate(r"""() => {
                    document.querySelectorAll('div[role="button"], span[role="button"]').forEach(b => {
                        if ((b.innerText || '').includes('Ver más')) { try { b.click(); } catch(e){} }
                    });
                }""")
            except Exception:
                pass

            items = page.evaluate(r"""() => {
                const out = [];
                const articles = Array.from(document.querySelectorAll('div[role="feed"] > div, div[role="article"]'));
                for (const art of articles) {
                    const msgEl = art.querySelector('div[dir="auto"][style*="text-align"], div[data-ad-preview="message"], div[dir="auto"]');
                    const txt = msgEl ? (msgEl.innerText || '').trim() : '';
                    if (txt && txt.length > 25 && !txt.includes('ordenar feed') && !txt.startsWith('Facebook')) {
                        const authorEl = art.querySelector('h2 a, h3 a, strong a, a[role="link"] strong');
                        const autor = authorEl ? authorEl.innerText.trim() : '';
                        let directUrl = '';
                        for (const a of Array.from(art.querySelectorAll('a[href]'))) {
                            const h = a.href || '';
                            if (h.includes('/posts/') || h.includes('/permalink/') || h.includes('/photo/') || h.includes('fbid=')) {
                                directUrl = h;
                                break;
                            }
                        }
                        let imgUrl = '';
                        for (const im of Array.from(art.querySelectorAll('img'))) {
                            const s = im.src || '';
                            if (s && (s.includes('scontent') || s.includes('fbcdn.net')) && !s.includes('emoji')) {
                                imgUrl = s;
                                break;
                            }
                        }
                        out.push({ autor, texto: txt, directUrl, imgUrl });
                    }
                }
                return out;
            }""")

            items_grupo = 0
            for it in items:
                txt = it.get("texto", "").strip()
                if not txt or len(txt) < 25 or not es_texto_espanol(txt) or es_exclusion_geografica(txt):
                    continue

                autor = it.get("autor") or f"Vecino / Camarada en {g_nombre}"
                url_fin = limpiar_url_fb(it.get("directUrl")) or g_url
                partido_det = detectar_partido_en_texto(f"{g_nombre} {autor} {txt}", partido_por_defecto="Provincia de Buenos Aires")

                comentarios = []
                if url_fin and any(k in url_fin for k in ["/photo/", "/posts/", "/permalink/", "fbid="]):
                    comentarios = extraer_comentarios_facebook(page.context, url_fin, max_comentarios=3)

                texto_full = txt
                if comentarios:
                    texto_full += "\n\n💬 Comentarios destacados de vecinos:\n" + "\n".join(f"• {c}" for c in comentarios)

                primer_renglon = txt.split("\n")[0][:75].strip()
                posteos.append({
                    "fuente": f"Facebook (Grupo: {g_nombre})",
                    "autor": autor,
                    "url": url_fin,
                    "titulo": f"{autor}: {primer_renglon}",
                    "texto": texto_full,
                    "comentarios": comentarios,
                    "imagen_url": it.get("imgUrl", ""),
                    "partido": partido_det,
                    "categoria": g_info.get("categoria", "seguridad"),
                    "pasada": "grupos_vecinales",
                    "fecha_publicacion": "En vivo desde mis grupos"
                })
                items_grupo += 1
                if items_grupo >= max_items_por_grupo:
                    break

        except Exception as e:
            print(f"  [Aviso Grupo {g_nombre}]: {e}")

    return posteos


def extraer_posteos_referentes_policiales(page, max_items: int = 5) -> List[Dict[str, Any]]:
    """
    Monitorea de forma dedicada a Virginia Luján Sosa y referentes policiales bonaerenses.
    Extrae sus publicaciones, reclamos institucionales, movilizaciones y comentarios de camaradas.
    """
    from engine import detectar_partido_en_texto
    from config_pba import es_exclusion_geografica, es_texto_espanol

    posteos = []
    fuentes_policiales = [
        {
            "nombre": "Virginia Luján Sosa (Perfil)",
            "url": "https://www.facebook.com/russita.sosa",
            "autor_default": "Virginia Luján Sosa"
        },
        {
            "nombre": "Búsqueda Virginia Luján Sosa en FB",
            "url": "https://www.facebook.com/search/posts?q=Virginia%20Lujan%20Sosa&filters=eyJyZWNlbnRfcG9zdHM6MCI6IntcIm5hbWVcIjpcInJlY2VudF9wb3N0c1wiLFwiYXJnc1wiOlwiXCJ9In0%3D",
            "autor_default": "Reclamos Policiales PBA"
        }
    ]

    for f_item in fuentes_policiales:
        try:
            print(f"  👮 Explorando referente policial: {f_item['nombre']}...")
            page.goto(f_item["url"], timeout=30000, wait_until="domcontentloaded")
            time.sleep(3.5)
            for _ in range(3):
                page.mouse.wheel(0, 1500)
                time.sleep(1.2)

            try:
                page.evaluate(r"""() => {
                    document.querySelectorAll('div[role="button"], span[role="button"]').forEach(b => {
                        if ((b.innerText || '').includes('Ver más')) { try { b.click(); } catch(e){} }
                    });
                }""")
            except Exception:
                pass

            items = page.evaluate(r"""() => {
                const out = [];
                const articles = Array.from(document.querySelectorAll('div[role="feed"] > div, div[role="article"]'));
                for (const art of articles) {
                    const msgEl = art.querySelector('div[dir="auto"][style*="text-align"], div[data-ad-preview="message"], div[dir="auto"]');
                    const txt = msgEl ? (msgEl.innerText || '').trim() : '';
                    if (txt && txt.length > 25 && !txt.includes('ordenar feed') && !txt.startsWith('Facebook')) {
                        const authorEl = art.querySelector('h2 a, h3 a, strong a, a[role="link"] strong');
                        const autor = authorEl ? authorEl.innerText.trim() : '';
                        let directUrl = '';
                        for (const a of Array.from(art.querySelectorAll('a[href]'))) {
                            const h = a.href || '';
                            if (h.includes('/posts/') || h.includes('/permalink/') || h.includes('/photo/') || h.includes('fbid=')) {
                                directUrl = h;
                                break;
                            }
                        }
                        let imgUrl = '';
                        for (const im of Array.from(art.querySelectorAll('img'))) {
                            const s = im.src || '';
                            if (s && (s.includes('scontent') || s.includes('fbcdn.net')) && !s.includes('emoji')) {
                                imgUrl = s;
                                break;
                            }
                        }
                        out.push({ autor, texto: txt, directUrl, imgUrl });
                    }
                }
                return out;
            }""")

            for it in items:
                txt = it.get("texto", "").strip()
                if not txt or len(txt) < 25 or not es_texto_espanol(txt) or es_exclusion_geografica(txt):
                    continue
                autor = it.get("autor") or f_item["autor_default"]
                url_fin = limpiar_url_fb(it.get("directUrl")) or f_item["url"]
                partido_det = detectar_partido_en_texto(f"{autor} {txt}", partido_por_defecto="Provincia de Buenos Aires")

                comentarios = []
                if url_fin and any(k in url_fin for k in ["/photo/", "/posts/", "/permalink/", "fbid="]):
                    comentarios = extraer_comentarios_facebook(page.context, url_fin, max_comentarios=3)

                texto_full = txt
                if comentarios:
                    texto_full += "\n\n💬 Comentarios destacados de camaradas / vecinos:\n" + "\n".join(f"• {c}" for c in comentarios)

                primer_renglon = txt.split("\n")[0][:75].strip()
                posteos.append({
                    "fuente": f"Facebook ({f_item['nombre']})",
                    "autor": autor,
                    "url": url_fin,
                    "titulo": f"{autor}: {primer_renglon}",
                    "texto": texto_full,
                    "comentarios": comentarios,
                    "imagen_url": it.get("imgUrl", ""),
                    "partido": partido_det,
                    "categoria": "seguridad",
                    "pasada": "referentes_policiales",
                    "fecha_publicacion": "En vivo desde referente policial"
                })
                if len(posteos) >= max_items:
                    break

        except Exception as e:
            print(f"  [Aviso Referentes Policiales]: {e}")

    return posteos

def extraer_posteos_facebook_amigos(page, max_items: int = 5) -> List[Dict[str, Any]]:
    """
    Navega al feed de inicio (publicaciones de amigos y seguidos del usuario)
    y extrae posteos locales de PBA.
    """
    from config_pba import es_exclusion_geografica, es_texto_espanol
    from engine import detectar_partido_en_texto

    posteos = []
    try:
        print("  👤 Explorando feed de inicio y publicaciones de amigos en Facebook...")
        page.goto("https://www.facebook.com/", timeout=30000, wait_until="domcontentloaded")
        time.sleep(3.5)
        for _ in range(3):
            page.mouse.wheel(0, 1500)
            time.sleep(1.2)

        items = page.evaluate(r"""() => {
            const feed = document.querySelector('div[role="feed"]') || document.querySelector('div[role="main"]');
            const cards = feed ? Array.from(feed.children) : [];
            const out = [];
            for (const card of cards) {
                const rawLines = (card.innerText || '').split('\n').map(l => l.replace(/Ver más/gi, '').trim()).filter(l => {
                    if (!l || l.length < 3 || l === 'Facebook' || l === '·' || l === 'Seguir' || l === 'Unirte') return false;
                    if (l.includes('Publicación compartida') || l.includes('Contenido sensible') || l.includes('Puede ser una imagen')) return false;
                    if (/^\d+$/.test(l)) return false;
                    if (l.length < 15 && l.includes('\u034f')) return false;
                    return true;
                });
                if (rawLines.length === 0) continue;
                const autor = rawLines[0];
                const bodyLines = rawLines.slice(1).filter(l => l.length > 5 && !l.includes('de 202'));
                const texto = bodyLines.join('\n');
                if (texto.length < 25) continue;

                let imgUrl = '';
                for (const im of Array.from(card.querySelectorAll('img'))) {
                    const s = im.src || '';
                    if (s && (s.includes('scontent') || s.includes('external.') || s.includes('fbcdn.net')) && !s.includes('emoji')) {
                        const w = im.naturalWidth || im.width || 0;
                        if (w > 120 || !w) { imgUrl = s; break; }
                    }
                }

                let directUrl = '';
                for (const a of Array.from(card.querySelectorAll('a[href]'))) {
                    const h = a.href || '';
                    if (h.includes('/posts/') || h.includes('/permalink/') || h.includes('/photo/') || h.includes('fbid=')) {
                        directUrl = h;
                        break;
                    }
                }
                out.push({ autor, texto, imgUrl, directUrl });
            }
            return out;
        }""")

        for it in items:
            txt = it.get("texto", "").strip()
            if not txt or len(txt) < 30 or not es_texto_espanol(txt) or es_exclusion_geografica(txt):
                continue

            autor = it.get("autor") or "Contacto en Facebook"
            url_fin = limpiar_url_fb(it.get("directUrl")) or "https://www.facebook.com"
            partido_det = detectar_partido_en_texto(f"{autor} {txt}", partido_por_defecto="Provincia de Buenos Aires")

            comentarios = []
            if url_fin and any(k in url_fin for k in ["/photo/", "/posts/", "/permalink/", "fbid="]):
                comentarios = extraer_comentarios_facebook(page.context, url_fin, max_comentarios=3)

            texto_full = txt
            if comentarios:
                texto_full += "\n\n💬 Comentarios destacados de vecinos:\n" + "\n".join(f"• {c}" for c in comentarios)

            primer_renglon = txt.split("\n")[0][:75].strip()
            posteos.append({
                "fuente": "Facebook (Amigos / Contactos)",
                "autor": autor,
                "url": url_fin,
                "titulo": f"{autor}: {primer_renglon}",
                "texto": texto_full,
                "comentarios": comentarios,
                "imagen_url": it.get("imgUrl", ""),
                "partido": partido_det,
                "categoria": "sociales_servicios",
                "pasada": "feed_amigos",
                "fecha_publicacion": "Feed de amigos en vivo"
            })
            if len(posteos) >= max_items:
                break

    except Exception as e:
        print(f"  [Aviso Feed Amigos FB]: {e}")

    return posteos


def extraer_posteos_instagram(page, max_items: int = 6) -> List[Dict[str, Any]]:
    """
    Navega a Instagram con tu sesión abierta:
    1. Revisa el feed de seguidos/amigos (https://www.instagram.com/).
    2. Revisa hashtags locales de PBA (policiabonaerense, vecinosbuenosaires, inseguridadbuenosaires).
    """
    from config_pba import es_exclusion_geografica, es_texto_espanol
    from engine import detectar_partido_en_texto

    posteos = []
    urls_ig = [
        ("https://www.instagram.com/", "feed_amigos"),
        ("https://www.instagram.com/explore/tags/policiabonaerense/", "hashtag_seguridad"),
        ("https://www.instagram.com/explore/tags/inseguridadbuenosaires/", "hashtag_seguridad"),
        ("https://www.instagram.com/explore/tags/vecinosbuenosaires/", "hashtag_vecinal"),
    ]

    for ig_url, tipo_origen in urls_ig:
        if len(posteos) >= max_items:
            break
        try:
            print(f"  📸 Explorando Instagram ({tipo_origen}): {ig_url}...")
            page.goto(ig_url, timeout=30000, wait_until="domcontentloaded")
            time.sleep(3.5)
            for _ in range(2):
                page.mouse.wheel(0, 1000)
                time.sleep(1)

            if tipo_origen == "feed_amigos":
                items_feed = page.evaluate(r"""() => {
                    const arts = document.querySelectorAll('article');
                    const out = [];
                    for (const a of arts) {
                        let autor = '';
                        const authorLinks = a.querySelectorAll('header a, div[role="button"] a');
                        for (const l of authorLinks) {
                            const txt = (l.innerText || '').trim();
                            if (txt && !txt.includes('Follow') && !txt.includes('Seguir') && !txt.includes('•')) {
                                autor = txt;
                                break;
                            }
                        }
                        let imgUrl = '';
                        const imgs = Array.from(a.querySelectorAll('img'));
                        for (const im of imgs) {
                            const s = im.src || '';
                            if (s && (s.includes('cdninstagram.com') || s.includes('fbcdn.net')) && !s.includes('emoji')) {
                                const w = im.naturalWidth || im.width || 0;
                                if (w > 120 || !w) { imgUrl = s; break; }
                            }
                        }
                        let postUrl = '';
                        const links = Array.from(a.querySelectorAll('a[href]'));
                        for (const l of links) {
                            const h = l.href || '';
                            if (h.includes('/p/') || h.includes('/reel/')) {
                                postUrl = h.split('?')[0];
                                break;
                            }
                        }
                        const text = (a.innerText || '').trim();
                        if (text.length > 25) {
                            out.push({ autor: autor || 'Instagram', url: postUrl, imgUrl: imgUrl, texto: text });
                        }
                        if (out.length >= 3) break;
                    }
                    return out;
                }""")
                for it in items_feed:
                    txt = it.get("texto", "").strip()
                    if not txt or len(txt) < 25 or not es_texto_espanol(txt) or es_exclusion_geografica(txt):
                        continue
                    autor = it.get("autor", "Contacto en Instagram")
                    partido_det = detectar_partido_en_texto(f"{autor} {txt}", partido_por_defecto="Provincia de Buenos Aires")
                    primer_renglon = txt.split("\n")[0][:75].strip()
                    posteos.append({
                        "fuente": "Instagram (Seguidos / Amigos)",
                        "autor": autor,
                        "url": it.get("url") or "https://www.instagram.com/",
                        "titulo": f"{autor}: {primer_renglon}",
                        "texto": txt,
                        "comentarios": [],
                        "imagen_url": it.get("imgUrl", ""),
                        "partido": partido_det,
                        "categoria": "seguridad",
                        "pasada": "instagram_amigos",
                        "fecha_publicacion": "Feed de Instagram en vivo"
                    })
                    if len(posteos) >= max_items:
                        break

            else:
                post_links = page.evaluate(r"""() => {
                    return Array.from(document.querySelectorAll('a[href*="/p/"], a[href*="/reel/"]'))
                        .map(a => a.href.split('?')[0])
                        .slice(0, 3);
                }""")
                for plink in post_links:
                    if len(posteos) >= max_items:
                        break
                    try:
                        p_tab = page.context.new_page()
                        p_tab.goto(plink, timeout=20000, wait_until="domcontentloaded")
                        time.sleep(2.5)
                        det = p_tab.evaluate(r"""() => {
                            let autor = '';
                            const a_el = document.querySelector('header a, h2 a');
                            if (a_el) autor = (a_el.innerText || '').trim();
                            let texto = '';
                            const h1 = document.querySelector('h1, div[role="button"] span');
                            if (h1) texto = (h1.innerText || '').trim();
                            if (!texto) {
                                const spans = Array.from(document.querySelectorAll('article span'));
                                for (const sp of spans) {
                                    const t = (sp.innerText || '').trim();
                                    if (t.length > 30) { texto = t; break; }
                                }
                            }
                            if (!texto) texto = document.body.innerText.slice(0, 400).replace(/\n/g, ' ');
                            let imgUrl = '';
                            const imgs = Array.from(document.querySelectorAll('article img, div[role="dialog"] img'));
                            for (const im of imgs) {
                                const s = im.src || '';
                                if (s && (s.includes('cdninstagram.com') || s.includes('fbcdn.net')) && !s.includes('emoji')) {
                                    const w = im.naturalWidth || im.width || 0;
                                    if (w > 120 || !w) { imgUrl = s; break; }
                                }
                            }
                            return { autor, texto, imgUrl };
                        }""")
                        p_tab.close()

                        txt_ig = det.get("texto", "").strip()
                        if not txt_ig or len(txt_ig) < 25 or not es_texto_espanol(txt_ig) or es_exclusion_geografica(txt_ig):
                            continue
                        autor_ig = det.get("autor") or "Instagram PBA"
                        partido_det = detectar_partido_en_texto(f"{autor_ig} {txt_ig}", partido_por_defecto="Provincia de Buenos Aires")
                        primer_renglon = txt_ig.split("\n")[0][:75].strip()
                        posteos.append({
                            "fuente": "Instagram (Hashtags PBA)",
                            "autor": autor_ig,
                            "url": plink,
                            "titulo": f"{autor_ig}: {primer_renglon}",
                            "texto": txt_ig,
                            "comentarios": [],
                            "imagen_url": det.get("imgUrl", ""),
                            "partido": partido_det,
                            "categoria": "seguridad",
                            "pasada": "instagram_hashtags",
                            "fecha_publicacion": "Hashtags Instagram en vivo"
                        })
                    except Exception:
                        pass

        except Exception as e:
            print(f"  [Aviso Instagram]: {e}")

    return posteos


def ejecutar_ciclo_recoleccion(headless: bool = False, max_consultas: int = 6):
    """
    Ejecuta el ciclo de búsquedas en Facebook, X e Instagram con tu sesión abierta:
    1. Búsquedas públicas PBA en Facebook y X.
    2. Feed y grupos de los que sos miembro en Facebook.
    3. Publicaciones de tus amigos en Facebook.
    4. Feed de seguidos y hashtags de PBA en Instagram.
    """
    from engine import generar_matriz_consultas_multired

    print(f"🚀 Iniciando navegador con sesión guardada en: {SESSION_DIR}")
    print(f"Modo Headless: {headless}")

    p, context = lanzar_navegador_sesion(headless=headless)
    page = context.new_page()

    # Rotación dinámica de consultas entre pasadas para cubrir los 135 partidos
    matriz_completa = generar_matriz_consultas_multired()
    state_file = os.path.join(BASE_DIR, "scraper_state.json")
    idx_inicio = 0
    if os.path.exists(state_file):
        try:
            with open(state_file, "r", encoding="utf-8") as sf:
                sdata = json.load(sf)
                idx_inicio = sdata.get("proximo_indice", 0) % len(matriz_completa)
        except Exception:
            idx_inicio = 0

    matriz = [matriz_completa[(idx_inicio + i) % len(matriz_completa)] for i in range(max_consultas)]
    proximo_idx = (idx_inicio + max_consultas) % len(matriz_completa)
    try:
        with open(state_file, "w", encoding="utf-8") as sf:
            json.dump({
                "proximo_indice": proximo_idx,
                "ultima_ejecucion": datetime.now().isoformat(),
                "consultas_ejecutadas": [m.get("fb_search_query") for m in matriz]
            }, sf, indent=2)
    except Exception:
        pass

    total_recolectados = []

    try:
        # Fase 1: Búsquedas públicas en Facebook y X
        for idx, item in enumerate(matriz, 1):
            print(f"\n[{idx}/{len(matriz)}] Buscando en Facebook: {item['fb_search_query']}...")
            fb_posts = extraer_posteos_facebook(page, item["fb_url"], max_items=3)
            for p_item in fb_posts:
                p_item["partido"] = item["partido"]
                p_item["pasada"] = item["pasada"]
                p_item["categoria"] = item["categoria"]
            total_recolectados.extend(fb_posts)

            if item.get("tw_url"):
                print(f"[{idx}/{len(matriz)}] Buscando en X: {item['partido']}...")
                tw_posts = extraer_posteos_twitter(page, item["tw_url"], max_items=2)
                for t_item in tw_posts:
                    t_item["partido"] = item["partido"]
                    t_item["pasada"] = item["pasada"]
                    t_item["categoria"] = item["categoria"]
                total_recolectados.extend(tw_posts)

            time.sleep(1.2)

        # Fase 2: Grupos de los que es miembro / sigue en Facebook
        print("\n👥 Explorando grupos y comunidades de miembros en Facebook...")
        fb_grupos = extraer_posteos_facebook_grupos(page, max_items=6)
        total_recolectados.extend(fb_grupos)

        # Fase 3: Feed de amigos y contactos en Facebook
        print("\n👤 Explorando feed de amigos y contactos en Facebook...")
        fb_amigos = extraer_posteos_facebook_amigos(page, max_items=4)
        total_recolectados.extend(fb_amigos)

        # Fase 4: Feed de seguidos y hashtags bonaerenses en Instagram
        print("\n📸 Explorando feed de seguidos y hashtags en Instagram...")
        ig_posts = extraer_posteos_instagram(page, max_items=5)
        total_recolectados.extend(ig_posts)

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
            data_resp = resp.json()
            print("Resultado de ingesta en base local:", data_resp)

            edicion_id = data_resp.get("resultado", {}).get("edicion_id")
            if edicion_id:
                print(f"\n📄 Compilando reporte PDF para Edición #{edicion_id} con imágenes y comentarios...")
                from pdf_service import crear_reporte_pdf_edicion
                ruta_pdf = crear_reporte_pdf_edicion(edicion_id)
                print(f"✓ PDF generado en: {ruta_pdf}")

                try:
                    from telegram_service import enviar_alerta_telegram
                    from database import get_conn
                    conn = get_conn()
                    convocatorias = conn.execute(
                        "SELECT titulo, partido, categoria FROM hallazgos WHERE edicion_id = ? AND es_convocatoria = 1",
                        (edicion_id,),
                    ).fetchall()
                    nombres = conn.execute(
                        "SELECT nombre FROM nombres_propios WHERE ultima_edicion_id = ? OR vigente = 1 ORDER BY (ultima_edicion_id = ?) DESC, id DESC LIMIT 5",
                        (edicion_id, edicion_id),
                    ).fetchall()
                    hallazgos_dest = conn.execute(
                        "SELECT partido, autor, texto FROM hallazgos WHERE edicion_id = ? AND descartado = 0 ORDER BY id DESC LIMIT 3",
                        (edicion_id,),
                    ).fetchall()
                    conn.close()

                    datos_edicion = {
                        "edicion_id": edicion_id,
                        "total_hallazgos": data_resp.get("resultado", {}).get("procesados", len(total_recolectados)),
                        "nuevos_hallazgos": data_resp.get("resultado", {}).get("nuevos", 0),
                        "convocatorias": [dict(c) for c in convocatorias],
                        "nombres_propios": [n["nombre"] for n in nombres],
                        "hallazgos_destacados": [dict(h) for h in hallazgos_dest],
                    }
                    print("📲 Enviando reporte y PDF a Telegram...")
                    res_tg = enviar_alerta_telegram(datos_edicion, ruta_pdf=ruta_pdf or "")
                    if res_tg.get("ok"):
                        print("✓ ¡Alerta y PDF enviados exitosamente por Telegram!")
                    else:
                        print("Aviso Telegram:", res_tg)
                except Exception as e_tg:
                    print("Error enviando por Telegram:", e_tg)
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
