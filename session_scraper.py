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
    Inicia o se conecta a un contexto de navegador persistente.
    Si el navegador permanente está abierto (puerto 9222), se conecta
    directamente vía CDP sin abrir ni cerrar ventanas, manteniendo la ventana
    de X activa para evitar que se disparen chequeos anti-bot.
    """
    p = sync_playwright().start()

    # 1. Intentar conectar al navegador permanente ya abierto (CDP 9222)
    try:
        browser_cdp = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        context = browser_cdp.contexts[0] if browser_cdp.contexts else browser_cdp
        setattr(context, "_es_cdp", True)
        setattr(context, "_browser_cdp", browser_cdp)
        print("  🌐 Conectado al navegador permanente ya abierto (CDP 9222) — ventana de X activa.")
        return p, context
    except Exception:
        pass

    # 2. Si no hay navegador en 9222, lanzar contexto persistente tradicional
    launch_kwargs = {
        "user_data_dir": SESSION_DIR,
        "headless": headless,
        "viewport": {"width": 1280, "height": 850},
        "permissions": ["clipboard-read", "clipboard-write"],
        "args": [
            "--remote-debugging-port=9222",
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
    setattr(context, "_es_cdp", False)
    return p, context


import re
import urllib.parse


JS_HELPERS_TARJETA = r"""() => {
    if (window.__td) return;
    const RE_FECHA = /^(justo ahora|ahora|ayer.*|hace .+|\d{1,3}\s*(min|h|d|sem|a|m|w|y)|\d{1,2}\s+(de\s+)?(ene|feb|mar|abr|may|jun|jul|ago|sep|set|oct|nov|dic)[a-z]*\.?(\s+(de\s+)?\d{4})?(\s+a las .*)?)$/i;
    const esPost = h => /\/posts\/|\/permalink\/|story_fbid=|\/photo\/|\/photo\.php|fbid=|\/reel\/|\/videos\/|\/watch\/\?v=|\/share\/[pvr]\//.test(h);
    const enComentario = el => !!el.closest('[aria-label^="Comentario de"], [aria-label*="Respuesta de"], [aria-label^="Comment by"], [aria-label*="Reply by"]');
    const textoFecha = a => {
        const cands = [a.getAttribute('aria-label') || '', (a.innerText || '').trim()];
        const sub = a.querySelector('[aria-label]');
        if (sub) cands.push(sub.getAttribute('aria-label') || '');
        for (const c of cands) {
            const t = (c || '').replace(/\s+/g, ' ').trim();
            if (t && t.length < 45 && RE_FECHA.test(t)) return t;
        }
        return '';
    };
    function urlYFecha(card) {
        // Nunca tomar enlaces que están dentro de los comentarios (fotos o perfiles de
        // comentaristas): eso llevaba a "otra publicación".
        const links = Array.from(card.querySelectorAll('a[href]')).filter(a => !enComentario(a));
        // 1. El enlace de la fecha ("3 h", "15 de octubre") es el enlace propio del post.
        for (const a of links) {
            const h = a.href || '';
            if (!esPost(h)) continue;
            const f = textoFecha(a);
            if (f) return { url: h, fecha: f };
        }
        let fecha = '';
        for (const a of links) { const f = textoFecha(a); if (f) { fecha = f; break; } }
        if (!fecha) {
            // Facebook a veces muestra la fecha como texto suelto ("Hace 21 horas"), no como enlace
            const clon = card.cloneNode(true);
            clon.querySelectorAll('[aria-label^="Comentario de"], [aria-label^="Respuesta de"], [aria-label^="Comment by"], [aria-label^="Reply by"]').forEach(e => e.remove());
            for (const l of (clon.innerText || '').split('\n')) {
                const t = l.replace(/\s+/g, ' ').replace(/^·\s*|\s*·$/g, '').trim();
                if (t && t.length < 45 && RE_FECHA.test(t)) { fecha = t; break; }
            }
        }
        const prioridades = [
            h => h.includes('/photo/') || h.includes('fbid='),
            h => h.includes('/posts/'),
            h => /\/share\/[pvr]\//.test(h),
            h => h.includes('l.facebook.com/l.php') && h.includes('u='),
            h => h.includes('/reel/') || h.includes('/watch/?v=') || h.includes('/videos/') || h.includes('story_fbid='),
            h => h.includes('/permalink/') && !h.includes('/search/') && !h.includes('/hashtag/'),
        ];
        for (const p of prioridades) {
            for (const a of links) { const h = a.href || ''; if (p(h)) return { url: h, fecha }; }
        }
        return { url: '', fecha };
    }
    function numero(txt) {
        let t = (txt || '').toLowerCase().replace(/ /g, ' ').trim();
        const m = t.match(/(\d[\d.,]*)\s*(mil|k|m)?\b/);
        if (!m) return 0;
        let n = m[1], mult = 1;
        if (m[2] === 'mil' || m[2] === 'k') mult = 1000;
        else if (m[2] === 'm') mult = 1000000;
        const v = mult > 1 ? parseFloat(n.includes(',') ? n.replace(/\./g, '').replace(',', '.') : n)
                           : parseFloat(n.replace(/[.,]/g, ''));
        return Math.round((v || 0) * mult);
    }
    function metricas(card) {
        // Solo el texto de la tarjeta fuera de los comentarios
        const out = { comentarios: 0, compartidos: 0, reacciones: 0 };
        const clon = card.cloneNode(true);
        clon.querySelectorAll('[aria-label^="Comentario de"], [aria-label^="Respuesta de"], [aria-label^="Comment by"], [aria-label^="Reply by"]').forEach(e => e.remove());
        const lineas = (clon.innerText || card.innerText || '').split('\n').map(l => l.trim());
        for (const l of lineas) {
            let m = l.match(/^(\d[\d.,]*\s*(?:mil|k|m)?)\s+comentarios?$/i) || l.match(/^(\d[\d.,]*\s*(?:mil|k|m)?)\s+comments?$/i);
            if (m) out.comentarios = Math.max(out.comentarios, numero(m[1]));
            m = l.match(/^(\d[\d.,]*\s*(?:mil|k|m)?)\s+(?:veces compartid[oa]|compartid[oa]s?|shares?)$/i);
            if (m) out.compartidos = Math.max(out.compartidos, numero(m[1]));
        }
        for (const el of card.querySelectorAll('[aria-label]')) {
            const a = el.getAttribute('aria-label') || '';
            let m = a.match(/^(?:Todas las reacciones|All reactions):?\s*(.+)$/i);
            if (m) { out.reacciones = Math.max(out.reacciones, numero(m[1])); continue; }
            m = a.match(/^(\d[\d.,]*\s*(?:mil|k|m)?)\s+comentarios?$/i);
            if (m) out.comentarios = Math.max(out.comentarios, numero(m[1]));
        }
        return out;
    }
    window.__td = { urlYFecha, metricas };
}"""


def _inyectar_helpers_js(page) -> None:
    try:
        page.evaluate(JS_HELPERS_TARJETA)
    except Exception:
        pass


def _resolver_fecha(fecha_txt: str, url: str = "", texto: str = "") -> Tuple[str, bool]:
    """Devuelve (fecha ISO o "", es_vieja). Si la red no dio la fecha en el enlace, se
    busca escrita en el texto de la tarjeta ("Hace 21 horas"). Sin fecha legible devuelve ""."""
    from config_pba import MAX_HORAS_ANTIGUEDAD, fecha_desde_id_tweet, fecha_en_texto, parsear_fecha_publicacion

    dt = (parsear_fecha_publicacion(fecha_txt or "")
          or parsear_fecha_publicacion(fecha_en_texto(texto or ""))
          or fecha_desde_id_tweet(url))
    if not dt:
        return "", False
    vieja = (datetime.now() - dt).total_seconds() > MAX_HORAS_ANTIGUEDAD * 3600
    return dt.isoformat(timespec="seconds"), vieja


def _fecha_iso_externa(valor: str) -> Tuple[str, bool]:
    """Convierte un datetime ISO con zona (Instagram / X) a hora local."""
    from config_pba import MAX_HORAS_ANTIGUEDAD

    if not valor:
        return "", False
    try:
        dt = datetime.fromisoformat(valor.replace("Z", "+00:00"))
        if dt.tzinfo:
            dt = dt.astimezone().replace(tzinfo=None)
    except ValueError:
        return "", False
    vieja = (datetime.now() - dt).total_seconds() > MAX_HORAS_ANTIGUEDAD * 3600
    return dt.isoformat(timespec="seconds"), vieja


def _metricas_tweet(art) -> Dict[str, int]:
    """Respuestas, reposts y me gusta de un tweet (desde el aria-label de cada botón)."""
    from config_pba import parsear_numero_red

    out = {"comentarios": 0, "compartidos": 0, "reacciones": 0}
    for testid, clave in (("reply", "comentarios"), ("retweet", "compartidos"), ("unretweet", "compartidos"),
                          ("like", "reacciones"), ("unlike", "reacciones")):
        try:
            el = art.locator(f'[data-testid="{testid}"]').first
            if el.count():
                out[clave] = max(out[clave], parsear_numero_red(el.get_attribute("aria-label") or ""))
        except Exception:
            pass

    # Fallback para nueva interfaz de X (sin data-testid)
    if out["reacciones"] == 0 and out["compartidos"] == 0 and out["comentarios"] == 0:
        try:
            for btn in art.locator('button, [role="button"]').all():
                lbl = (btn.get_attribute("aria-label") or "").lower()
                if "me gusta" in lbl or "likes" in lbl:
                    out["reacciones"] = max(out["reacciones"], parsear_numero_red(lbl))
                elif "repost" in lbl or "retweet" in lbl:
                    out["compartidos"] = max(out["compartidos"], parsear_numero_red(lbl))
                elif "respuesta" in lbl or "reply" in lbl or "replies" in lbl:
                    out["comentarios"] = max(out["comentarios"], parsear_numero_red(lbl))
        except Exception:
            pass
    return out


def _url_grupo_cronologica(url: str) -> str:
    # Por defecto los grupos muestran "Más relevantes" (posteos de hace semanas).
    if "/groups/feed" in url or "sorting_setting" in url:
        return url
    return url.rstrip("/") + "/?sorting_setting=CHRONOLOGICAL"


def copiar_enlace_compartir_facebook(page, card_locator) -> str:
    """
    Hace clic en 'Compartir' -> 'Copiar enlace' en la tarjeta de publicación
    para obtener el enlace canónico directo según el método oficial de Facebook.
    """
    try:
        # Vaciar el portapapeles antes: si "Copiar enlace" falla en silencio, antes se
        # leía el enlace de la publicación ANTERIOR y quedaba asignado a esta.
        try:
            page.evaluate("() => navigator.clipboard.writeText('')")
        except Exception:
            pass
        share_btn = card_locator.locator(
            'div[role="button"]:has-text("Compartir"), div[aria-label="Compartir"], div[aria-label*="Compartir esta publicación"]'
        ).last
        if share_btn.count() == 0:
            return ""
        share_btn.scroll_into_view_if_needed()
        time.sleep(0.3)
        share_btn.click()
        time.sleep(0.6)

        copy_btn = page.locator(
            'div[role="menuitem"]:has-text("Copiar enlace"), div[role="button"]:has-text("Copiar enlace"), span:has-text("Copiar enlace")'
        ).first
        res_url = ""
        if copy_btn.count() > 0:
            copy_btn.click()
            time.sleep(0.4)
            clip = page.evaluate('() => navigator.clipboard.readText()')
            if clip and clip.startswith("http"):
                res_url = clip.strip()
        page.keyboard.press("Escape")
        time.sleep(0.3)
        return res_url
    except Exception:
        try:
            page.keyboard.press("Escape")
        except Exception:
            pass
        return ""


def limpiar_url_fb(href: str) -> str:
    """
    Limpia y normaliza URLs de Facebook para que lleven DIRECTAMENTE
    al posteo, foto, video, reel o artículo externo compartido.
    Rechaza terminantemente perfiles, páginas, grupos generales, búsquedas o home.
    """
    if not href:
        return ""
    href = href.strip()

    # 1. Enlace externo compartido a través del redireccionador l.facebook.com
    if "l.facebook.com/l.php" in href and "u=" in href:
        m = re.search(r"u=([^&]+)", href)
        if m:
            ext_url = urllib.parse.unquote(m.group(1))
            if ext_url.startswith("http") and not any(d in ext_url for d in ["facebook.com", "fb.com"]):
                return ext_url.split("?fbclid")[0].split("&fbclid")[0]

    # Exclusiones terminantes de Facebook que no son publicaciones
    if any(k in href for k in ["/search/", "/home.php", "/login", "/messages", "/notifications", "/hashtag/", "/stories/"]):
        return ""
    if href in ["https://www.facebook.com", "https://www.facebook.com/", "https://facebook.com", "https://facebook.com/"]:
        return ""
    # Enlaces de compartir grupo NO son publicaciones
    if "/share/g/" in href:
        return ""

    # 2. Enlaces oficiales de compartir publicación / video / reel
    if "/share/p/" in href or "/share/v/" in href or "/share/r/" in href:
        return href.split("?")[0].rstrip("/") + "/"

    # 3. Foto con fbid (prioridad máxima sobre permalinks genéricos de grupo)
    if ("/photo/" in href or "/photo.php" in href or "fbid=" in href):
        m = re.search(r"fbid=([0-9]+)", href)
        if m:
            return f"https://www.facebook.com/photo/?fbid={m.group(1)}"

    # 4. Post directo de página o perfil
    if "/posts/" in href:
        return href.split("?")[0].rstrip("/") + "/"

    # 5. Reel
    if "/reel/" in href:
        m = re.search(r"/reel/([0-9]+)", href)
        if m:
            return f"https://www.facebook.com/reel/{m.group(1)}/"

    # 6. Videos / Watch
    if "/watch/" in href and "v=" in href:
        m = re.search(r"v=([0-9]+)", href)
        if m:
            return f"https://www.facebook.com/watch/?v={m.group(1)}"
    if "/videos/" in href:
        m = re.search(r"/videos/([0-9]+)", href)
        if m:
            return f"https://www.facebook.com/watch/?v={m.group(1)}"

    # 7. Post o permalink en grupo
    if "/groups/" in href:
        if "/posts/" in href or "/permalink/" in href:
            return href.split("?")[0].rstrip("/") + "/"
        # El grupo general NO es una publicación: descartar
        return ""

    # 8. permalink.php o story.php con story_fbid
    if ("permalink.php" in href or "story.php" in href) and "story_fbid=" in href:
        m = re.search(r"story_fbid=([a-zA-Z0-9]+)", href)
        id_m = re.search(r"id=([0-9]+)", href)
        if m and id_m:
            return f"https://www.facebook.com/permalink.php?story_fbid={m.group(1)}&id={id_m.group(1)}"
        elif m:
            return f"https://www.facebook.com/permalink.php?story_fbid={m.group(1)}"

    # Si es perfil de usuario o página sin permalink de post, DESCARTAR
    return ""


def es_url_publicacion_valida(url: str) -> bool:
    """
    Verifica que la URL lleve de manera inequívoca a una publicación, tweet, post
    o noticia directa, y NO a una página principal, feed, grupo o perfil.
    """
    if not url or not url.startswith("http"):
        return False
    u = url.lower().strip()

    if u in ["https://www.facebook.com", "https://www.facebook.com/", "https://facebook.com", "https://facebook.com/", "https://www.instagram.com/", "https://instagram.com/"]:
        return False
    if any(k in u for k in ["/search/", "/home.php", "/login", "/messages", "/hashtag/", "/stories/"]):
        return False

    # Excluir explícitamente compartir grupos completos
    if "/share/g/" in u:
        return False

    # Twitter / X
    if "x.com" in u or "twitter.com" in u:
        return "/status/" in u

    # Instagram
    if "instagram.com" in u:
        return "/p/" in u or "/reel/" in u

    # Facebook
    if "facebook.com" in u or "fb.com" in u:
        if "/share/p/" in u or "/share/v/" in u or "/share/r/" in u:
            return True
        if "/photo/" in u or "/photo.php" in u or "fbid=" in u:
            return True
        if "/groups/" in u:
            return "/permalink/" in u or "/posts/" in u
        if any(k in u for k in ["/posts/", "/reel/", "/watch/?v=", "/videos/", "story_fbid=", "permalink.php"]):
            return True
        return False

    # Noticias o artículos periodísticos externos (válidos)
    return True


def es_texto_basura_ui(autor: str, texto: str) -> bool:
    """
    Detecta si el texto o autor corresponde a elementos de la interfaz de usuario de Facebook
    (cajas de publicación, indicadores de chat en línea, carruseles de historias, etc.)
    """
    a = (autor or "").lower().strip()
    t = (texto or "").lower().strip()

    patrones = [
        "¿qué estás pensando", "que estas pensando", "estás pensando, gaston", "estas pensando",
        "crear una publicación", "crear publicacion", "indicador de estado", "estado online",
        "publicaciones del feed", "reels y videos cortos", "ordenar feed", "escribe un comentario",
        "detalles del grupo", "añadir a tu publicación", "compartir en tu perfil",
        "cambió su foto de portada", "actualizó su foto del perfil", "activo hace",
        "enviar mensaje", "precio:", "alquilo dpto", "vendo ropero"
    ]
    if any(p in a for p in patrones):
        return True
    if any(p in t for p in patrones):
        return True
    if a in ["activo", "facebook", "desconocido", "usuario", "participante"]:
        if len(t) < 30 or any(p in t for p in patrones):
            return True
    return False


def _comentario_util(cuerpo: str, texto_post: str = "") -> bool:
    """Descarta comentarios vacíos, solo etiquetas de personas, solo emojis/risas o que
    repiten el texto de la publicación."""
    c = re.sub(r"@\w+", "", cuerpo or "").strip()
    if len(c) < 8:
        return False
    palabras = re.findall(r"[a-záéíóúñü]+", c.lower())
    if len(palabras) < 2:
        return False
    if re.fullmatch(r"(?:[jJaAhHkK]{4,}\s*)+", c):
        return False
    # Solo nombres propios (alguien etiquetando a otra persona)
    tokens = c.split()
    if len(tokens) <= 4 and all(t[:1].isupper() for t in tokens if t[:1].isalpha()):
        return False
    if texto_post and c[:40].lower() in texto_post.lower():
        return False
    return True


def extraer_comentarios_twitter(context, tweet_url: str, max_replies: int = 4) -> Tuple[List[str], str]:
    """
    Abre el tweet directo en una pestaña en segundo plano, extrae el texto completo
    sin truncar y las respuestas reales (descarta las del propio autor y las vacías).
    """
    if not tweet_url or "/status/" not in tweet_url:
        return [], ""
    replies: List[str] = []
    main_text = ""
    p_tab = None
    try:
        p_tab = context.new_page()
        p_tab.goto(tweet_url, timeout=20000, wait_until="domcontentloaded")
        try:
            p_tab.wait_for_selector('article[data-testid="tweet"]', timeout=12000)
        except Exception:
            return [], ""
        for _ in range(2):
            p_tab.mouse.wheel(0, 900)
            time.sleep(1.2)

        res = p_tab.evaluate(r"""() => {
            const arts = Array.from(document.querySelectorAll('article[data-testid="tweet"]'));
            const handle = el => {
                const u = el.querySelector('[data-testid="User-Name"]');
                if (!u) return ['', ''];
                const partes = u.innerText.split('\n');
                const h = partes.find(p => p.startsWith('@')) || '';
                return [partes[0] || '', h];
            };
            let mainTxt = '', mainHandle = '';
            if (arts.length) {
                const el = arts[0].querySelector('[data-testid="tweetText"]');
                if (el) mainTxt = (el.innerText || '').trim();
                mainHandle = handle(arts[0])[1];
            }
            const out = [];
            for (let i = 1; i < arts.length; i++) {
                const [nombre, h] = handle(arts[i]);
                if (h && h === mainHandle) continue;   // hilo del mismo autor, no es reacción
                const t = arts[i].querySelector('[data-testid="tweetText"]');
                if (!t) continue;
                out.push({ autor: nombre || h || 'Usuario', texto: (t.innerText || '').trim().replace(/\n+/g, ' ') });
            }
            return { replies: out, mainText: mainTxt };
        }""")
        main_text = res.get("mainText", "")
        for r in res.get("replies", []):
            if _comentario_util(r.get("texto", ""), main_text):
                replies.append(f"{r['autor']}: {r['texto']}")
            if len(replies) >= max_replies:
                break
    except Exception as e:
        print(f"  [Aviso X Respuestas]: {e}")
    finally:
        if p_tab:
            try:
                p_tab.close()
            except Exception:
                pass
    return replies, main_text


def extraer_comentarios_facebook(context, post_url: str, max_comentarios: int = 4, texto_post: str = "") -> List[str]:
    """
    Abre la URL directa del posteo en una pestaña en segundo plano, despliega
    los comentarios y extrae las intervenciones reales de vecinos/camaradas.
    """
    if not post_url or "facebook.com/search/" in post_url:
        return []
    if not any(k in post_url for k in ["/photo/", "/posts/", "/permalink/", "fbid=", "/groups/", "/reel/", "/share/", "story_fbid=", "/videos/", "/watch"]):
        return []

    comentarios: List[str] = []
    p_tab = None
    try:
        p_tab = context.new_page()
        p_tab.goto(post_url, timeout=25000, wait_until="domcontentloaded")
        time.sleep(3)
        p_tab.mouse.wheel(0, 600)
        time.sleep(1)

        # Desplegar comentarios si están plegados (solo botones de comentarios)
        try:
            p_tab.evaluate(r"""() => {
                document.querySelectorAll('div[role="button"], span[role="button"]').forEach(b => {
                    const txt = (b.innerText || '').trim();
                    if (/^Ver (más|los \d+|\d+) comentarios?/i.test(txt) || /^Ver más respuestas/i.test(txt) || /^View (more|all) comments/i.test(txt)) {
                        try { b.click(); } catch(e){}
                    }
                });
            }""")
            time.sleep(1.5)
        except Exception:
            pass

        crudos = p_tab.evaluate(r"""() => {
            const out = [];
            const UI = /^(\d+\s*(min|h|d|sem|a|s|m|w|y)|justo ahora|ahora|editado|autor|autora|seguir|unirte|responder|me gusta|compartir|ver traducción|ocultar|ver más|fan destacado|top fan|·)$/i;
            const nodes = document.querySelectorAll('div[aria-label^="Comentario de"], div[aria-label^="Respuesta de"], div[aria-label^="Comment by"], div[aria-label^="Reply by"]');
            for (const n of nodes) {
                const aria = n.getAttribute('aria-label') || '';
                let autor = aria.replace(/^(Comentario|Respuesta) de\s+/i, '').replace(/^(Comment|Reply) by\s+/i, '')
                                .replace(/\s+(hace|ago)\b.*$/i, '').replace(/\s+\d+\s*\w*$/, '').trim();
                const lines = (n.innerText || '').split('\n').map(l => l.trim()).filter(l => l && !UI.test(l));
                if (!lines.length) continue;
                if (!autor) autor = lines[0];
                const cuerpo = lines.filter(l => l !== autor).join(' ').trim();
                out.push({ autor, texto: cuerpo });
            }
            return out;
        }""")
        vistos = set()
        for c in crudos:
            cuerpo = c.get("texto", "")
            clave = cuerpo[:60].lower()
            if clave in vistos or not _comentario_util(cuerpo, texto_post):
                continue
            vistos.add(clave)
            comentarios.append(f"{c.get('autor') or 'Vecino'}: {cuerpo}")
            if len(comentarios) >= max_comentarios:
                break
    except Exception as e:
        print(f"  [Aviso FB Comentarios]: {e}")
    finally:
        if p_tab:
            try:
                p_tab.close()
            except Exception:
                pass
    return comentarios


def completar_comentarios(context, posteos: List[Dict[str, Any]], max_posts: int = 8) -> None:
    """
    Lee los comentarios SOLO de las publicaciones que van a llegar al reporte (las que
    pasan el clasificador), empezando por las más relevantes. Antes se abrían todas
    (incluidas avisos y posts descartados) y nunca las de búsquedas públicas ni las de X.
    """
    from engine import clasificar_hallazgo

    candidatos = []
    for p in posteos:
        try:
            info = clasificar_hallazgo(
                titulo=p.get("titulo", ""), texto=p.get("texto", ""),
                categoria_forzada=p.get("categoria", ""), partido_objetivo=p.get("partido", ""),
                pasada=p.get("pasada", "anclaje_general"),
            )
        except Exception:
            info = None
        if info:
            candidatos.append((info.get("relevancia", 0), p))

    candidatos.sort(key=lambda c: c[0], reverse=True)
    leidos = 0
    for _, p in candidatos:
        if leidos >= max_posts:
            break
        url = p.get("url", "")
        texto = p.get("texto", "")
        if "/status/" in url:
            replies, texto_completo = extraer_comentarios_twitter(context, url, max_replies=4)
            if texto_completo and len(texto_completo) > len(texto):
                p["texto"] = texto_completo
            nuevos = replies
        elif "facebook.com" in url or "fb.com" in url:
            nuevos = extraer_comentarios_facebook(context, url, max_comentarios=4, texto_post=texto)
        elif "instagram.com" in url:
            if p.get("comentarios"):
                continue  # ya se leyeron al abrir el post
            nuevos, metricas_ig = extraer_comentarios_instagram(context, url, max_comentarios=4)
            if metricas_ig:
                p["metricas"] = {**(p.get("metricas") or {}), **metricas_ig}
        else:
            continue
        leidos += 1
        previos = p.get("comentarios") or []
        p["comentarios"] = (nuevos + [c for c in previos if c not in nuevos])[:4] if nuevos else previos
        print(f"  💬 {len(p['comentarios'])} comentarios — {p.get('autor', '')[:30]}: {texto[:50]!r}")
    print(f"  Comentarios leídos en {leidos} publicaciones relevantes (de {len(candidatos)} que pasan el filtro).")


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

        _inyectar_helpers_js(page)
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

                const _uf = window.__td.urlYFecha(card);
                const directUrl = _uf.url;
                const fechaTxt = _uf.fecha;
                if (!directUrl) continue;

                results.push({
                    autor: autor,
                    texto: texto,
                    url: directUrl,
                    imgUrl: imgUrl,
                    fechaTxt: fechaTxt,
                    metricas: window.__td.metricas(card)
                });
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
            if es_texto_basura_ui(autor, txt):
                continue

            url_final = limpiar_url_fb(item.get("url"))
            if not url_final or not es_url_publicacion_valida(url_final):
                continue
            fecha_iso, es_vieja = _resolver_fecha(item.get("fechaTxt"), url_final, txt)
            if es_vieja:
                continue

            primer_renglon = txt.split("\n")[0][:75].strip()
            comentarios = []

            texto_con_comentarios = txt
            if comentarios:
                texto_con_comentarios += "\n\n💬 Comentarios destacados de vecinos:\n" + "\n".join(f"• {c}" for c in comentarios)

            posteos.append({
                "fuente": "Facebook (Sesión Abierta)",
                "autor": autor,
                "url": url_final,
                "titulo": f"{autor}: {primer_renglon}",
                "texto": texto_con_comentarios,
                "comentarios": comentarios,
                "imagen_url": item.get("imgUrl", ""),
                "fecha_publicacion": fecha_iso,
                "metricas": item.get("metricas") or {}
            })
            if len(posteos) >= max_items:
                break

    except Exception as e:
        print(f"[Facebook Session] Error navegando: {e}")

    return posteos


def normalizar_url_busqueda_x(url_busqueda: str) -> str:
    """Garantiza que lang:es y las exclusiones estén dentro de q y que f=live
    ("Más recientes") quede intacto, aunque la URL venga armada a mano."""
    partes = urllib.parse.urlsplit(url_busqueda)
    qs = urllib.parse.parse_qs(partes.query)
    q = (qs.get("q") or [""])[0]
    f = (qs.get("f") or ["live"])[0]
    # Reparar URLs viejas donde los filtros quedaron pegados al parámetro f
    if f != "live":
        q = f"{q} {f.replace('live', '', 1)}".strip()
        f = "live"
    for extra in ("lang:es", "-filter:replies", "-CABA", "-Cordoba", "-Madrid"):
        if extra.lower() not in q.lower():
            q += f" {extra}"
    query = urllib.parse.urlencode({"q": " ".join(q.split()), "src": "typed_query", "f": f})
    return urllib.parse.urlunsplit(("https", "x.com", "/search", query, ""))


def diagnosticar_pagina_x(page) -> str:
    """Explica por qué una búsqueda de X no mostró tweets (sin sesión, bloqueo, sin resultados)."""
    url = page.url or ""
    if "/login" in url or "i/flow/login" in url or "/i/flow/" in url:
        return "SIN SESIÓN: X redirigió al login. Corré `python session_scraper.py --login` e iniciá sesión en X."
    try:
        if page.locator('iframe[src*="arkose"], iframe[id*="arkose"]').count() > 0:
            return "BLOQUEO: X pide verificación humana (captcha). Abrí X a mano en ese perfil y resolvelo."
        cuerpo = (page.inner_text("body") or "").lower()
    except Exception:
        cuerpo = ""
    if any(t in cuerpo for t in ["confirma que eres humano", "verify you are human", "comprueba que eres humano"]):
        return "BLOQUEO: X pide verificación humana (captcha). Abrí X a mano en ese perfil y resolvelo."
    if any(t in cuerpo for t in ["iniciar sesión", "inicia sesión", "sign in", "log in"]) and "buscar" not in cuerpo:
        return "SIN SESIÓN: la página pide iniciar sesión. Corré `python session_scraper.py --login`."
    if any(t in cuerpo for t in ["no hay resultados", "no results for", "sin resultados"]):
        return "SIN RESULTADOS: X no encontró tweets recientes para esta búsqueda."
    if any(t in cuerpo for t in ["algo salió mal", "something went wrong", "rate limit", "límite"]):
        return "ERROR DE X: 'Algo salió mal' o límite de uso. Suele pasar en modo headless o por demasiadas búsquedas."
    if not cuerpo.strip():
        return "PÁGINA VACÍA: X no cargó (posible detección del modo headless)."
    return "X cargó pero no mostró tweets (motivo desconocido)."


def extraer_posteos_twitter(page, url_busqueda: str, max_items: int = 8, verbose: bool = False, partido_objetivo: str = "") -> List[Dict[str, Any]]:
    """
    Navega a la búsqueda de X/Twitter en vivo y extrae tweets recientes en español de PBA.
    Imprime un resumen con cuántos tweets vio y por qué descartó cada uno.
    """
    from config_pba import es_exclusion_geografica, es_tema_excluido, es_texto_espanol

    tweets = []
    descartes: Dict[str, int] = {}

    def _descartar(motivo: str, texto: str = "") -> None:
        descartes[motivo] = descartes.get(motivo, 0) + 1
        if verbose:
            print(f"    ✗ {motivo}: {texto[:90]!r}")

    try:
        url_busqueda = normalizar_url_busqueda_x(url_busqueda)
        page.goto(url_busqueda, timeout=35000, wait_until="domcontentloaded")

        # X es una SPA: esperar a que aparezcan los tweets en lugar de 3 s fijos
        try:
            page.wait_for_selector('article[data-testid="tweet"], article:has(a[href*="/status/"])', timeout=15000)
        except Exception:
            print(f"  ⚠️ [X] 0 tweets — {diagnosticar_pagina_x(page)}")
            return []

        for _ in range(2):
            page.mouse.wheel(0, 1200)
            time.sleep(1.5)

        tweets = _parsear_tweets_en_pagina(page, max_items, _descartar, verbose, partido_objetivo)
    except Exception as e:
        print(f"[X Session] Error navegando: {e}")
    detalle = ", ".join(f"{k}: {v}" for k, v in descartes.items()) or "ninguno"
    print(f"  [X] {len(tweets)} tweets aceptados. Descartados: {detalle}")
    return tweets


def _parsear_tweets_en_pagina(page, max_items: int, _descartar, verbose: bool = False,
                              partido_objetivo: str = "",
                              fuente: str = "X / Twitter (Sesión Abierta)") -> List[Dict[str, Any]]:
    """Lee los tweets visibles en la página (búsqueda o timeline) y aplica los filtros."""
    from config_pba import es_exclusion_geografica, es_tema_excluido, es_texto_espanol

    tweets: List[Dict[str, Any]] = []
    articulos = page.locator('article[data-testid="tweet"], article:has(a[href*="/status/"])').all()
    for art in articulos:
        try:
            # Expandir si está cortado con "Mostrar más"
            show_more = art.locator('[data-testid="tweet-text-show-more-link"], button:has-text("Mostrar más"), button:has-text("Show more")').first
            if show_more.count():
                try:
                    show_more.click()
                    time.sleep(0.3)
                except Exception:
                    pass

            # Extraer texto del tweet
            text_el = art.locator('[data-testid="tweetText"], div[dir="auto"][lang], div[class*="wrap-anywhere"][dir="auto"]').first
            if not text_el.count():
                _descartar("sin texto (solo imagen/video)")
                continue
            texto = text_el.inner_text().strip()
            if len(texto) < 25:
                _descartar("texto muy corto", texto)
                continue

            # Filtrar idioma estrictamente español
            if not es_texto_espanol(texto):
                _descartar("no está en español", texto)
                continue

            excluir, motivo = es_tema_excluido("", texto)
            if excluir:
                _descartar(motivo, texto)
                continue

            # Filtrar exclusión geográfica de PBA
            if es_exclusion_geografica(texto, partido_objetivo):
                _descartar("sin lugar de PBA en el texto / otra provincia", texto)
                continue

            # Extraer autor real
            author_el = art.locator('[data-testid="User-Name"], div[class*="x-middot-group"], a[href*="/status/"]').first
            autor = author_el.inner_text().split("\n")[0].strip() if author_el.count() else "Usuario X"

            # Enlace directo al tweet: el <a> que contiene la hora es el del tweet
            # principal (no el de un tweet citado ni el de /photo/ o /analytics).
            href = None
            time_link = art.locator('a[href*="/status/"]:has(time)').first
            if time_link.count():
                href = time_link.get_attribute("href")
            if not href:
                links = art.locator('a[href*="/status/"]').all()
                href = links[0].get_attribute("href") if links else None
            if not href:
                _descartar("sin enlace al tweet", texto)
                continue
            m_status = re.search(r"^(.*?/status/\d+)", href)
            if m_status:
                href = m_status.group(1)
            enlace = f"https://x.com{href}" if not href.startswith("http") else href
            if not es_url_publicacion_valida(enlace):
                continue

            fecha_iso = ""
            time_el = art.locator("time").first
            dt_attr = time_el.get_attribute("datetime") if time_el.count() else None
            if dt_attr:
                try:
                    fecha_iso = datetime.fromisoformat(dt_attr.replace("Z", "+00:00")).astimezone().replace(tzinfo=None).isoformat(timespec="seconds")
                except ValueError:
                    fecha_iso = ""
            if not fecha_iso:
                fecha_iso, _ = _resolver_fecha("", enlace)
            if fecha_iso:
                from config_pba import MAX_HORAS_ANTIGUEDAD
                if (datetime.now() - datetime.fromisoformat(fecha_iso)).total_seconds() > MAX_HORAS_ANTIGUEDAD * 3600:
                    _descartar(f"más viejo que {MAX_HORAS_ANTIGUEDAD} h", texto)
                    continue

            metricas = _metricas_tweet(art)

            img_el = art.locator('div[data-testid="tweetPhoto"] img, img[src*="pbs.twimg.com/media/"], img[src*="thumb/"]').first
            img_url = img_el.get_attribute("src") if img_el.count() else ""

            comentarios_tw = []

            texto_con_comentarios = texto
            if comentarios_tw:
                texto_con_comentarios += "\n\n💬 Comentarios destacados de vecinos:\n" + "\n".join(f"• {c}" for c in comentarios_tw)

            primer_renglon = texto.split("\n")[0][:75].strip()
            tweets.append({
                "fuente": fuente,
                "autor": autor,
                "url": enlace,
                "titulo": f"{autor}: {primer_renglon}",
                "texto": texto_con_comentarios,
                "comentarios": comentarios_tw,
                "imagen_url": img_url,
                "fecha_publicacion": fecha_iso,
                "metricas": metricas
            })
            if verbose:
                print(f"    ✓ {autor}: {texto[:90]!r}")
            if len(tweets) >= max_items:
                break
        except Exception as e_art:
            _descartar(f"error leyendo tweet ({type(e_art).__name__})")
            continue
    return tweets


def extraer_posteos_x_seguidos(page, max_items: int = 8, verbose: bool = False) -> List[Dict[str, Any]]:
    """Lee la pestaña "Siguiendo" del inicio de X: los tweets de las cuentas que seguís, en
    orden cronológico (la pestaña "Para vos" la ordena X a su criterio y mezcla desconocidos)."""
    descartes: Dict[str, int] = {}
    ya_descartados = set()

    def _descartar(motivo: str, texto: str = "") -> None:
        # El timeline se relee tras cada scroll: contar cada tweet una sola vez
        if texto and texto in ya_descartados:
            return
        ya_descartados.add(texto)
        descartes[motivo] = descartes.get(motivo, 0) + 1
        if verbose:
            print(f"    ✗ {motivo}: {texto[:90]!r}")

    tweets: List[Dict[str, Any]] = []
    try:
        print("  🐦 Revisando la pestaña Siguiendo de X...")
        page.goto("https://x.com/home", timeout=35000, wait_until="domcontentloaded")
        try:
            page.wait_for_selector('[role="tab"]', timeout=15000)
        except Exception:
            print(f"  ⚠️ [X Siguiendo] {diagnosticar_pagina_x(page)}")
            return []
        tab = page.get_by_role("tab", name=re.compile(r"^(Siguiendo|Following)$", re.I)).first
        if tab.count():
            if tab.get_attribute("aria-selected") != "true":
                tab.click()
                time.sleep(2.5)
        else:
            print("  ⚠️ [X Siguiendo] no se encontró la pestaña 'Siguiendo'; se lee el inicio tal como está.")
        try:
            page.wait_for_selector('article[data-testid="tweet"], article:has(a[href*="/status/"])', timeout=15000)
        except Exception:
            print(f"  ⚠️ [X Siguiendo] 0 tweets — {diagnosticar_pagina_x(page)}")
            return []

        # El timeline va reciclando los tweets al bajar: leer después de cada scroll
        vistos = set()
        for _ in range(int(os.getenv("TERMOMETRO_X_SCROLLS", "4")) + 1):
            for t in _parsear_tweets_en_pagina(page, max_items * 3, _descartar, verbose,
                                               fuente="X / Twitter (Cuentas que sigo)"):
                if t["url"] not in vistos:
                    vistos.add(t["url"])
                    t["pasada"] = "x_seguidos"
                    t["categoria"] = ""
                    tweets.append(t)
            if len(tweets) >= max_items:
                break
            page.mouse.wheel(0, 1500)
            time.sleep(1.5)
    except Exception as e:
        print(f"  [Aviso X Siguiendo]: {e}")

    detalle = ", ".join(f"{k}: {v}" for k, v in descartes.items()) or "ninguno"
    print(f"  [X Siguiendo] {len(tweets[:max_items])} tweets aceptados. Descartados: {detalle}")
    return tweets[:max_items]


_RUTAS_GRUPOS_NO_GRUPO = {"feed", "joins", "discover", "create", "notifications", "search", "your_groups", "categories", "membership"}


def _clave_grupo(url: str) -> str:
    m = re.search(r"facebook\.com/groups/([^/?#]+)", url or "")
    return m.group(1).lower() if m else (url or "").lower()


def descubrir_grupos_facebook(page, horas_cache: int = 24) -> List[Dict[str, Any]]:
    """Lista los grupos de Facebook de los que sos miembro (facebook.com/groups/joins/).
    Se guarda en scraper_state.json y se vuelve a leer como mucho una vez por día."""
    state_file = os.path.join(BASE_DIR, "scraper_state.json")
    sdata: Dict[str, Any] = {}
    try:
        if os.path.exists(state_file):
            with open(state_file, "r", encoding="utf-8") as sf:
                sdata = json.load(sf)
        cache = sdata.get("grupos_descubiertos") or {}
        if cache.get("grupos") and cache.get("fecha"):
            if (datetime.now() - datetime.fromisoformat(cache["fecha"])).total_seconds() < horas_cache * 3600:
                return cache["grupos"]
    except Exception:
        sdata = {}

    grupos: List[Dict[str, Any]] = []
    try:
        print("  👥 Actualizando la lista de grupos de los que sos miembro...")
        page.goto("https://www.facebook.com/groups/joins/?nav_source=tab", timeout=30000, wait_until="domcontentloaded")
        time.sleep(3.5)
        for _ in range(int(os.getenv("TERMOMETRO_SCROLLS_LISTA_GRUPOS", "6"))):
            page.mouse.wheel(0, 2000)
            time.sleep(1.2)
        crudos = page.evaluate(r"""() => {
            const out = [];
            for (const a of document.querySelectorAll('div[role="main"] a[href*="/groups/"]')) {
                const nombre = (a.innerText || a.getAttribute('aria-label') || '').split('\n')[0].trim();
                if (nombre.length >= 3) out.push({ nombre, url: a.href.split('?')[0] });
            }
            return out;
        }""")
        vistos = set()
        for g in crudos:
            clave = _clave_grupo(g["url"])
            if not clave or clave in _RUTAS_GRUPOS_NO_GRUPO or clave in vistos:
                continue
            if g["nombre"].lower() in ("ver grupo", "view group", "ver todo", "see all"):
                continue
            vistos.add(clave)
            grupos.append({"nombre": g["nombre"][:60], "url": f"https://www.facebook.com/groups/{clave}/", "categoria": "seguridad"})
        print(f"  👥 Grupos encontrados en tu cuenta: {len(grupos)}")
    except Exception as e:
        print(f"  [Aviso lista de grupos]: {e}")

    if grupos:
        try:
            sdata["grupos_descubiertos"] = {"fecha": datetime.now().isoformat(timespec="seconds"), "grupos": grupos}
            with open(state_file, "w", encoding="utf-8") as sf:
                json.dump(sdata, sf, indent=2, ensure_ascii=False)
        except Exception:
            pass
    return grupos


def extraer_posteos_facebook_grupos(page, max_grupos: int = 4, max_items_por_grupo: int = 2, max_items: int = 8) -> List[Dict[str, Any]]:
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
    ]
    # Sumar todos los grupos de los que sos miembro (lista actualizada una vez por día)
    ya = {_clave_grupo(g["url"]) for g in GRUPOS_USUARIO}
    for g in descubrir_grupos_facebook(page):
        if _clave_grupo(g["url"]) not in ya:
            ya.add(_clave_grupo(g["url"]))
            GRUPOS_USUARIO.append(g)

    state_file = os.path.join(BASE_DIR, "scraper_state.json")
    idx_g = 0
    if os.path.exists(state_file):
        try:
            with open(state_file, "r", encoding="utf-8") as sf:
                sdata = json.load(sf)
                idx_g = sdata.get("proximo_grupo_idx", 0) % len(GRUPOS_USUARIO)
        except Exception:
            idx_g = 0

    # El feed general de grupos (lo último de TODOS tus grupos) se mira en cada corrida;
    # además se rota por los grupos de a max_grupos.
    max_grupos = min(max_grupos, len(GRUPOS_USUARIO))
    grupos_a_visitar = [{"nombre": "Feed General de Grupos", "url": "https://www.facebook.com/groups/feed/", "categoria": "seguridad"}]
    grupos_a_visitar += [GRUPOS_USUARIO[(idx_g + i) % len(GRUPOS_USUARIO)] for i in range(max_grupos)]
    try:
        sdata = {}
        if os.path.exists(state_file):
            with open(state_file, "r", encoding="utf-8") as sf:
                sdata = json.load(sf)
        sdata["proximo_grupo_idx"] = (idx_g + max_grupos) % len(GRUPOS_USUARIO)
        with open(state_file, "w", encoding="utf-8") as sf:
            json.dump(sdata, sf, indent=2, ensure_ascii=False)
    except Exception:
        pass

    posteos = []

    for g_info in grupos_a_visitar:
        g_nombre = g_info["nombre"]
        g_url = g_info["url"]
        try:
            print(f"  👥 Explorando grupo: {g_nombre} ({g_url})...")
            page.goto(_url_grupo_cronologica(g_url), timeout=30000, wait_until="domcontentloaded")
            time.sleep(3.5)
            for _ in range(3):
                page.mouse.wheel(0, 1500)
                time.sleep(1)

            # Desplegar "Ver más" de textos y botones de comentarios
            try:
                page.evaluate(r"""() => {
                    document.querySelectorAll('div[role="button"], span[role="button"], a[role="button"]').forEach(b => {
                        const txt = (b.innerText || '').trim();
                        if (txt.includes('Ver más')) { try { b.click(); } catch(e){} }
                    });
                }""")
                time.sleep(2)
            except Exception:
                pass

            _inyectar_helpers_js(page)
            items = page.evaluate(r"""() => {
                const out = [];
                const feed = document.querySelector('div[role="feed"]');
                const cards = feed ? Array.from(feed.children) : Array.from(document.querySelectorAll('div[role="article"]'));
                for (const card of cards) {
                    let msg = '';
                    for (const d of Array.from(card.querySelectorAll('div[dir="auto"]'))) {
                        const t = (d.innerText || '').trim();
                        if (t.length > 25 && !t.includes('ordenar feed') && !t.startsWith('Facebook') && !t.includes('Escribe un comentario') && !t.includes('Detalles')) {
                            if (t.length > msg.length) msg = t;
                        }
                    }
                    if (!msg || msg.length < 25) continue;

                    let autor = '';
                    const actionBtn = card.querySelector('div[aria-label*="Acciones para esta publicación"]');
                    if (actionBtn) {
                        const aria = actionBtn.getAttribute('aria-label') || '';
                        autor = aria.replace('Acciones para esta publicación de ', '').replace('Acciones para esta publicación', '').trim();
                    }
                    if (!autor) {
                        const aLink = card.querySelector('h2 a, h3 a, h4 a, strong a, a[role="link"]');
                        if (aLink) autor = (aLink.innerText || '').trim();
                    }

                    const _uf = window.__td.urlYFecha(card);
                const directUrl = _uf.url;
                const fechaTxt = _uf.fecha;
                if (!directUrl) continue;

                    let imgUrl = '';
                    for (const im of Array.from(card.querySelectorAll('img'))) {
                        const s = im.src || '';
                        if (s && (s.includes('scontent') || s.includes('fbcdn.net')) && !s.includes('emoji') && !s.includes('rsrc')) {
                            imgUrl = s;
                            break;
                        }
                    }

                    const comments = [];
                    for (const c of Array.from(card.querySelectorAll('div[aria-label^="Comentario de"], div[aria-label*="Respuesta de"]'))) {
                        const ctxt = (c.innerText || '').trim();
                        const lines = ctxt.split('\n').map(l => l.trim()).filter(l => l && !['Responder', 'Me gusta', 'Compartir', 'Ver traducción', '·', 'Editado'].includes(l));
                        if (lines.length >= 2) {
                            const cAuthor = lines[0];
                            const cBody = lines.slice(1).filter(l => !/^(\d+\s*(min|h|d|sem|a|s|m|w|y)|justo ahora|ahora|editado|autor|seguir|unirte|responder|me gusta|compartir|ver traducción|ocultar|ver más|·)$/i.test(l)).join(' ');
                            if (cBody.length > 2 && cBody !== msg) {
                                comments.push(`${cAuthor}: ${cBody}`);
                            }
                        }
                    }

                    out.push({ autor, texto: msg, directUrl, imgUrl, fechaTxt, metricas: window.__td.metricas(card), comments: comments.slice(0, 4) });
                }
                return out;
            }""")

            items_grupo = 0
            candidate_cards_loc = None
            for it in items:
                txt = it.get("texto", "").strip()
                autor = it.get("autor") or f"Vecino / Camarada en {g_nombre}"
                if not txt or len(txt) < 25 or not es_texto_espanol(txt) or es_exclusion_geografica(txt) or es_texto_basura_ui(autor, txt):
                    continue

                url_fin = limpiar_url_fb(it.get("directUrl"))
                # Si la URL es un permalink de grupo (que puede redireccionar al feed general)
                # o si no se obtuvo URL directa, se obtiene el enlace oficial con Compartir -> Copiar enlace
                if not url_fin or "/permalink/" in url_fin:
                    try:
                        if candidate_cards_loc is None:
                            candidate_cards_loc = page.locator('div[role="feed"] > div, div[role="article"]').all()
                        for c_loc in candidate_cards_loc:
                            c_text = c_loc.inner_text().strip()
                            if txt[:35] in c_text:
                                share_copied = copiar_enlace_compartir_facebook(page, c_loc)
                                if share_copied:
                                    clean_share = limpiar_url_fb(share_copied)
                                    if clean_share and es_url_publicacion_valida(clean_share):
                                        url_fin = clean_share
                                        break
                    except Exception:
                        pass

                if not url_fin or not es_url_publicacion_valida(url_fin):
                    continue
                fecha_iso, es_vieja = _resolver_fecha(it.get("fechaTxt"), url_fin, txt)
                if es_vieja:
                    continue
                if not fecha_iso:
                    fecha_iso = datetime.now().isoformat(timespec="seconds")
                partido_det = detectar_partido_en_texto(f"{g_nombre} {autor} {txt}", partido_por_defecto="Provincia de Buenos Aires")

                comentarios = [c for c in (it.get("comments") or []) if _comentario_util(c.split(":", 1)[-1], txt)]

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
                    "fecha_publicacion": fecha_iso,
                    "metricas": it.get("metricas") or {}
                })
                items_grupo += 1
                # El feed general junta todos los grupos: se le permiten más publicaciones
                tope = max_items_por_grupo * 3 if "/groups/feed" in g_url else max_items_por_grupo
                if items_grupo >= tope:
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

            # Desplegar "Ver más" de textos y botones de comentarios
            try:
                page.evaluate(r"""() => {
                    document.querySelectorAll('div[role="button"], span[role="button"], a[role="button"]').forEach(b => {
                        const txt = (b.innerText || '').trim();
                        if (txt.includes('Ver más')) { try { b.click(); } catch(e){} }
                    });
                }""")
                time.sleep(2)
            except Exception:
                pass

            _inyectar_helpers_js(page)
            items = page.evaluate(r"""() => {
                const out = [];
                const feed = document.querySelector('div[role="feed"]');
                const cards = feed ? Array.from(feed.children) : Array.from(document.querySelectorAll('div[role="article"]'));
                for (const card of cards) {
                    let msg = '';
                    for (const d of Array.from(card.querySelectorAll('div[dir="auto"]'))) {
                        const t = (d.innerText || '').trim();
                        if (t.length > 25 && !t.includes('ordenar feed') && !t.startsWith('Facebook') && !t.includes('Escribe un comentario') && !t.includes('Detalles')) {
                            if (t.length > msg.length) msg = t;
                        }
                    }
                    if (!msg || msg.length < 25) continue;

                    let autor = '';
                    const actionBtn = card.querySelector('div[aria-label*="Acciones para esta publicación"]');
                    if (actionBtn) {
                        const aria = actionBtn.getAttribute('aria-label') || '';
                        autor = aria.replace('Acciones para esta publicación de ', '').replace('Acciones para esta publicación', '').trim();
                    }
                    if (!autor) {
                        const aLink = card.querySelector('h2 a, h3 a, h4 a, strong a, a[role="link"]');
                        if (aLink) autor = (aLink.innerText || '').trim();
                    }

                    const _uf = window.__td.urlYFecha(card);
                const directUrl = _uf.url;
                const fechaTxt = _uf.fecha;
                if (!directUrl) continue;

                    let imgUrl = '';
                    for (const im of Array.from(card.querySelectorAll('img'))) {
                        const s = im.src || '';
                        if (s && (s.includes('scontent') || s.includes('fbcdn.net')) && !s.includes('emoji') && !s.includes('rsrc')) {
                            imgUrl = s;
                            break;
                        }
                    }

                    const comments = [];
                    for (const c of Array.from(card.querySelectorAll('div[aria-label^="Comentario de"], div[aria-label*="Respuesta de"]'))) {
                        const ctxt = (c.innerText || '').trim();
                        const lines = ctxt.split('\n').map(l => l.trim()).filter(l => l && !['Responder', 'Me gusta', 'Compartir', 'Ver traducción', '·', 'Editado'].includes(l));
                        if (lines.length >= 2) {
                            const cAuthor = lines[0];
                            const cBody = lines.slice(1).filter(l => !/^(\d+\s*(min|h|d|sem|a|s|m|w|y)|justo ahora|ahora|editado|autor|seguir|unirte|responder|me gusta|compartir|ver traducción|ocultar|ver más|·)$/i.test(l)).join(' ');
                            if (cBody.length > 2 && cBody !== msg) {
                                comments.push(`${cAuthor}: ${cBody}`);
                            }
                        }
                    }

                    out.push({ autor, texto: msg, directUrl, imgUrl, fechaTxt, metricas: window.__td.metricas(card), comments: comments.slice(0, 4) });
                }
                return out;
            }""")

            candidate_cards_loc = None
            for it in items:
                txt = it.get("texto", "").strip()
                autor = it.get("autor") or f_item["autor_default"]
                if not txt or len(txt) < 25 or not es_texto_espanol(txt) or es_exclusion_geografica(txt) or es_texto_basura_ui(autor, txt):
                    continue

                url_fin = limpiar_url_fb(it.get("directUrl"))
                if not url_fin or "/permalink/" in url_fin:
                    try:
                        if candidate_cards_loc is None:
                            candidate_cards_loc = page.locator('div[role="feed"] > div, div[role="article"]').all()
                        for c_loc in candidate_cards_loc:
                            c_text = c_loc.inner_text().strip()
                            if txt[:35] in c_text:
                                share_copied = copiar_enlace_compartir_facebook(page, c_loc)
                                if share_copied:
                                    clean_share = limpiar_url_fb(share_copied)
                                    if clean_share and es_url_publicacion_valida(clean_share):
                                        url_fin = clean_share
                                        break
                    except Exception:
                        pass

                if not url_fin or not es_url_publicacion_valida(url_fin):
                    continue
                fecha_iso, es_vieja = _resolver_fecha(it.get("fechaTxt"), url_fin, txt)
                if es_vieja:
                    continue
                if not fecha_iso:
                    fecha_iso = datetime.now().isoformat(timespec="seconds")
                partido_det = detectar_partido_en_texto(f"{autor} {txt}", partido_por_defecto="Provincia de Buenos Aires")

                comentarios = [c for c in (it.get("comments") or []) if _comentario_util(c.split(":", 1)[-1], txt)]

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
                    "fecha_publicacion": fecha_iso,
                    "metricas": it.get("metricas") or {}
                })
                if len(posteos) >= max_items:
                    break

        except Exception as e:
            print(f"  [Aviso Referentes Policiales]: {e}")

    return posteos

FEEDS_FACEBOOK_SEGUIDOS = [
    # (url, etiqueta de la fuente)
    ("https://www.facebook.com/", "Facebook (Feed de Contactos y Grupos)"),
    ("https://www.facebook.com/groups/feed/", "Facebook (Feed General de Grupos)"),
]


def extraer_posteos_facebook_amigos(page, max_items: int = 5) -> List[Dict[str, Any]]:
    """Publicaciones de amigos, páginas y perfiles que seguís en Facebook, en orden
    cronológico ("Más recientes"). Antes se leía el inicio, que Facebook ordena a su
    criterio y mezcla con sugerencias y publicidad."""
    posteos: List[Dict[str, Any]] = []
    vistas = set()
    for url_feed, etiqueta in FEEDS_FACEBOOK_SEGUIDOS:
        if len(posteos) >= max_items:
            break
        for p_item in _extraer_feed_facebook(page, url_feed, etiqueta, max_items - len(posteos)):
            if p_item["url"] not in vistas:
                vistas.add(p_item["url"])
                posteos.append(p_item)
    return posteos


def _extraer_feed_facebook(page, url_feed: str, etiqueta_fuente: str, max_items: int = 5) -> List[Dict[str, Any]]:
    from config_pba import es_exclusion_geografica, es_texto_espanol
    from engine import detectar_partido_en_texto

    posteos = []
    try:
        print(f"  👤 Explorando {etiqueta_fuente}...")
        page.goto(url_feed, timeout=30000, wait_until="domcontentloaded")
        time.sleep(3.5)
        for _ in range(int(os.getenv("TERMOMETRO_SCROLLS_FEED_FB", "5"))):
            page.mouse.wheel(0, 1500)
            time.sleep(1.2)

        _inyectar_helpers_js(page)
        items = page.evaluate(r"""() => {
            let cards = Array.from(document.querySelectorAll('div[role="feed"] > div, div[role="article"], div[data-pagelet*="FeedUnit"]'));
            if (cards.length <= 2) {
                const feed = document.querySelector('div[role="feed"]') || document.querySelector('div[role="main"]');
                if (feed) cards = Array.from(feed.children);
            }
            const out = [];
            for (const card of cards) {
                const cardText = (card.innerText || '').toLowerCase();
                if (cardText.includes('¿qué estás pensando') || cardText.includes('que estas pensando') || cardText.includes('crear una publicación') || cardText.includes('publicaciones del feed') || cardText.includes('reels y videos') || cardText.includes('historias')) {
                    continue;
                }

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

                const _uf = window.__td.urlYFecha(card);
                const directUrl = _uf.url;
                const fechaTxt = _uf.fecha;
                if (!directUrl) continue;

                let imgUrl = '';
                for (const im of Array.from(card.querySelectorAll('img'))) {
                    const s = im.src || '';
                    if (s && (s.includes('scontent') || s.includes('external.') || s.includes('fbcdn.net')) && !s.includes('emoji')) {
                        const w = im.naturalWidth || im.width || 0;
                        if (w > 120 || !w) { imgUrl = s; break; }
                    }
                }

                out.push({ autor, texto, imgUrl, directUrl, fechaTxt, metricas: window.__td.metricas(card) });
            }
            return out;
        }""")

        candidate_cards_loc = None
        for it in items:
            txt = it.get("texto", "").strip()
            autor = it.get("autor") or "Contacto en Facebook"
            if not txt or len(txt) < 30 or not es_texto_espanol(txt) or es_exclusion_geografica(txt) or es_texto_basura_ui(autor, txt):
                continue

            url_fin = limpiar_url_fb(it.get("directUrl"))
            if not url_fin or "/permalink/" in url_fin:
                try:
                    if candidate_cards_loc is None:
                        feed_el = page.locator('div[role="feed"] > div, div[role="article"]').all()
                        candidate_cards_loc = feed_el
                    for c_loc in candidate_cards_loc:
                        c_text = c_loc.inner_text().strip()
                        if txt[:35] in c_text:
                            share_copied = copiar_enlace_compartir_facebook(page, c_loc)
                            if share_copied:
                                clean_share = limpiar_url_fb(share_copied)
                                if clean_share and es_url_publicacion_valida(clean_share):
                                    url_fin = clean_share
                                    break
                except Exception:
                    pass

            if not url_fin or not es_url_publicacion_valida(url_fin):
                continue
            fecha_iso, es_vieja = _resolver_fecha(it.get("fechaTxt"), url_fin, txt)
            if es_vieja:
                continue
            partido_det = detectar_partido_en_texto(f"{autor} {txt}", partido_por_defecto="Provincia de Buenos Aires")

            comentarios = []

            texto_full = txt
            if comentarios:
                texto_full += "\n\n💬 Comentarios destacados de vecinos:\n" + "\n".join(f"• {c}" for c in comentarios)

            primer_renglon = txt.split("\n")[0][:75].strip()
            posteos.append({
                "fuente": etiqueta_fuente,
                "autor": autor,
                "url": url_fin,
                "titulo": f"{autor}: {primer_renglon}",
                "texto": texto_full,
                "comentarios": comentarios,
                "imagen_url": it.get("imgUrl", ""),
                "partido": partido_det,
                "categoria": "sociales_servicios",
                "pasada": "feed_amigos",
                "fecha_publicacion": fecha_iso,
                "metricas": it.get("metricas") or {}
            })
            if len(posteos) >= max_items:
                break

    except Exception as e:
        print(f"  [Aviso {etiqueta_fuente}]: {e}")

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
        # "Siguiendo": solo cuentas que seguís, en orden cronológico (el inicio común
        # lo ordena Instagram y mezcla sugerencias)
        ("https://www.instagram.com/?variant=following", "feed_amigos"),
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
            scrolls = int(os.getenv("TERMOMETRO_SCROLLS_FEED_IG", "5")) if tipo_origen == "feed_amigos" else 2
            for _ in range(scrolls):
                page.mouse.wheel(0, 1000)
                time.sleep(1)

            if tipo_origen == "feed_amigos":
                items_feed = page.evaluate(r"""(maxPosts) => {
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
                        const tEl = a.querySelector('time[datetime]');
                        const fechaIso = tEl ? tEl.getAttribute('datetime') : '';
                        if (text.length > 25) {
                            out.push({ autor: autor || 'Instagram', url: postUrl, imgUrl: imgUrl, texto: text, fechaIso });
                        }
                        if (out.length >= maxPosts) break;
                    }
                    return out;
                }""", int(os.getenv("TERMOMETRO_POSTS_FEED_IG", "12")))
                for it in items_feed:
                    txt = it.get("texto", "").strip()
                    post_url = (it.get("url") or "").strip()
                    if not post_url or not es_url_publicacion_valida(post_url):
                        continue
                    autor = it.get("autor", "Contacto en Instagram")
                    fecha_iso, es_vieja = _fecha_iso_externa(it.get("fechaIso"))
                    if es_vieja:
                        continue
                    # El texto de la tarjeta del feed trae todo mezclado ("lbinoticias • 9 min
                    # Tolosa (La Plata) 16 lbinoticias 🚨 ..."). Se abre el post para tomar
                    # el texto limpio, el autor real, los comentarios y las métricas.
                    datos_post = None
                    if os.getenv("TERMOMETRO_ABRIR_POSTS_IG", "1") == "1":
                        p_tab = None
                        try:
                            p_tab = page.context.new_page()
                            datos_post = leer_post_instagram(p_tab, post_url)
                        except Exception:
                            datos_post = None
                        finally:
                            if p_tab:
                                try:
                                    p_tab.close()
                                except Exception:
                                    pass
                    if datos_post and datos_post.get("caption"):
                        txt = datos_post["caption"]
                        autor = datos_post.get("autor") or autor
                        if not fecha_iso:
                            fecha_iso, es_vieja = _fecha_iso_externa(datos_post.get("fecha_iso_raw"))
                            if es_vieja:
                                continue
                    if not txt or len(txt) < 25 or not es_texto_espanol(txt) or es_exclusion_geografica(txt):
                        continue
                    partido_det = detectar_partido_en_texto(txt, partido_por_defecto="Provincia de Buenos Aires")
                    primer_renglon = next((l for l in txt.split("\n") if len(l.strip()) > 15), txt)[:75].strip()
                    posteos.append({
                        "fuente": "Instagram (Seguidos / Amigos)",
                        "autor": autor,
                        "url": post_url,
                        "titulo": f"{autor}: {primer_renglon}",
                        "texto": txt,
                        "comentarios": (datos_post or {}).get("comentarios", [])[:4],
                        "imagen_url": (datos_post or {}).get("imagen_url") or it.get("imgUrl", ""),
                        "partido": partido_det,
                        "categoria": "seguridad",
                        "pasada": "instagram_amigos",
                        "fecha_publicacion": fecha_iso,
                        "metricas": (datos_post or {}).get("metricas", {}),
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
                        page.goto(plink, timeout=20000, wait_until="domcontentloaded")
                        time.sleep(2)
                        det = page.evaluate(r"""() => {
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
                            const tEl = document.querySelector('time[datetime]');
                            const fechaIso = tEl ? tEl.getAttribute('datetime') : '';
                            return { autor, texto, imgUrl, fechaIso };
                        }""")

                        txt_ig = det.get("texto", "").strip()
                        if not txt_ig or len(txt_ig) < 25 or not es_texto_espanol(txt_ig) or es_exclusion_geografica(txt_ig):
                            continue
                        autor_ig = det.get("autor") or "Instagram PBA"
                        fecha_iso, es_vieja = _fecha_iso_externa(det.get("fechaIso"))
                        if es_vieja:
                            continue
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
                            "fecha_publicacion": fecha_iso
                        })
                    except Exception:
                        pass

        except Exception as e:
            print(f"  [Aviso Instagram]: {e}")

    return posteos


JS_POST_INSTAGRAM = r"""() => {
    const main = document.querySelector('main') || document.body;
    const UI = /^(responder|reply|ver traducción|see translation|me gusta|like|\d+\s*(sem|min|h|d|s|w|a)|ver respuestas.*|ocultar respuestas|editado|seguir|following|seguidos|follow|·|autor|creator)$/i;
    const tEl = main.querySelector('time[datetime]');
    const fechaIso = tEl ? tEl.getAttribute('datetime') : '';
    const h1 = main.querySelector('h1');
    const caption = h1 ? (h1.innerText || '').trim() : '';
    let autor = '';
    const header = main.querySelector('header');
    if (header) {
        const a = header.querySelector('a[href^="/"]');
        if (a) autor = (a.innerText || a.getAttribute('href') || '').replace(/\//g, '').trim();
    }
    let imgUrl = '';
    for (const im of main.querySelectorAll('img')) {
        const s = im.src || '';
        if ((s.includes('cdninstagram') || s.includes('fbcdn')) && (im.naturalWidth || im.width || 0) > 200) { imgUrl = s; break; }
    }
    // Comentarios: cada <li> (o contenedor de lista) con un enlace a un perfil y texto
    const comentarios = [];
    const vistos = new Set();
    for (const li of main.querySelectorAll('ul li, div[role="listitem"]')) {
        const link = li.querySelector('a[href^="/"]:not([href*="/p/"]):not([href*="/explore/"])');
        if (!link) continue;
        const usuario = (link.innerText || '').trim() || (link.getAttribute('href') || '').replace(/\//g, '');
        if (!usuario || usuario.includes(' ')) continue;
        const lineas = (li.innerText || '').split('\n').map(l => l.trim())
            .filter(l => l && l !== usuario && !UI.test(l) && !/^\d+ (me gusta|likes?)$/i.test(l));
        const texto = lineas.join(' ').trim();
        if (!texto || texto === caption || vistos.has(texto)) continue;
        vistos.add(texto);
        comentarios.push({ autor: usuario, texto });
    }
    // Métricas visibles: "217 Me gusta", "Les gusta a X y 216 personas más", "Ver los 12 comentarios"
    const todo = main.innerText || '';
    let reacciones = 0, numComentarios = 0;
    let m = todo.match(/([\d.,]+\s*(?:mil|k)?)\s+me gusta/i) || todo.match(/([\d.,]+\s*(?:mil|k)?)\s+likes?/i);
    if (m) reacciones = m[1];
    m = todo.match(/y\s+([\d.,]+\s*(?:mil|k)?)\s+personas? más/i) || todo.match(/and\s+([\d.,]+\s*(?:k)?)\s+others/i);
    if (m && !reacciones) reacciones = 'MAS1:' + m[1];
    m = todo.match(/ver (?:los |todos los )?([\d.,]+\s*(?:mil|k)?)\s+comentarios/i) || todo.match(/view all ([\d.,]+) comments/i);
    if (m) numComentarios = m[1];
    return { fechaIso, caption, autor, imgUrl, comentarios, reacciones: String(reacciones), numComentarios: String(numComentarios) };
}"""


def leer_post_instagram(page, url: str) -> Optional[Dict[str, Any]]:
    """Abre un post / reel de Instagram y devuelve texto, fecha, comentarios y métricas."""
    from config_pba import parsear_numero_red

    try:
        page.goto(url, timeout=25000, wait_until="domcontentloaded")
        try:
            page.wait_for_selector("main time[datetime], main h1", timeout=12000)
        except Exception:
            return None
        time.sleep(1.5)
        # Desplegar más comentarios si está el botón
        try:
            page.evaluate(r"""() => {
                for (const b of document.querySelectorAll('main [role="button"], main button')) {
                    const t = (b.getAttribute('aria-label') || b.innerText || '').trim();
                    if (/cargar más comentarios|load more comments/i.test(t)) { try { b.click(); } catch(e){} }
                }
            }""")
            time.sleep(1.2)
        except Exception:
            pass
        d = page.evaluate(JS_POST_INSTAGRAM)
    except Exception as e:
        print(f"  [Aviso Instagram post]: {e}")
        return None

    reac_txt = d.get("reacciones") or "0"
    reacciones = parsear_numero_red(reac_txt.replace("MAS1:", "")) + (1 if reac_txt.startswith("MAS1:") else 0)
    comentarios = []
    for c in d.get("comentarios") or []:
        if c.get("autor") and c["autor"] == d.get("autor"):
            continue  # respuestas del propio autor
        if _comentario_util(c.get("texto", ""), d.get("caption", "")):
            comentarios.append(f"{c['autor']}: {c['texto']}")
    return {
        "caption": d.get("caption", ""),
        "autor": d.get("autor", ""),
        "fecha_iso_raw": d.get("fechaIso", ""),
        "imagen_url": d.get("imgUrl", ""),
        "comentarios": comentarios,
        "metricas": {
            "comentarios": max(parsear_numero_red(d.get("numComentarios") or "0"), len(d.get("comentarios") or [])),
            "compartidos": 0,
            "reacciones": reacciones,
        },
    }


def extraer_comentarios_instagram(context, post_url: str, max_comentarios: int = 4) -> Tuple[List[str], Dict[str, int]]:
    """Abre un post de Instagram en otra pestaña y devuelve (comentarios, métricas)."""
    p_tab = None
    try:
        p_tab = context.new_page()
        datos = leer_post_instagram(p_tab, post_url)
        if not datos:
            return [], {}
        return datos["comentarios"][:max_comentarios], datos["metricas"]
    finally:
        if p_tab:
            try:
                p_tab.close()
            except Exception:
                pass


def extraer_posteos_instagram_cuentas(page, cuentas: Optional[List[str]] = None, max_por_cuenta: Optional[int] = None,
                                      verbose: bool = False) -> List[Dict[str, Any]]:
    """
    Revisa en cada corrida las últimas publicaciones de las cuentas de Instagram configuradas
    (CUENTAS_INSTAGRAM), con su fecha, comentarios y métricas. A diferencia del feed, que
    Instagram ordena a su criterio, acá no se pierde ningún post reciente de esas cuentas.
    """
    from config_pba import (CUENTAS_INSTAGRAM, MAX_HORAS_ANTIGUEDAD, MAX_POSTS_POR_CUENTA_IG,
                            es_exclusion_geografica, es_tema_excluido, es_texto_espanol)
    from engine import detectar_partido_en_texto

    cuentas = cuentas or CUENTAS_INSTAGRAM
    max_por_cuenta = max_por_cuenta or MAX_POSTS_POR_CUENTA_IG
    posteos: List[Dict[str, Any]] = []

    for cuenta in cuentas:
        try:
            print(f"  📸 Revisando cuenta de Instagram @{cuenta}...")
            page.goto(f"https://www.instagram.com/{cuenta}/", timeout=30000, wait_until="domcontentloaded")
            try:
                page.wait_for_selector('a[href*="/p/"], a[href*="/reel/"]', timeout=15000)
            except Exception:
                url_actual = page.url or ""
                motivo = "SIN SESIÓN (pide iniciar sesión)" if "/accounts/login" in url_actual else "no cargó la grilla de publicaciones"
                print(f"  ⚠️ [Instagram @{cuenta}] {motivo}")
                continue
            links = page.evaluate(r"""() => {
                const out = [];
                for (const a of document.querySelectorAll('main a[href*="/p/"], main a[href*="/reel/"]')) {
                    const h = a.href.split('?')[0];
                    if (!out.includes(h)) out.push(h);
                }
                return out.slice(0, 9);
            }""")
        except Exception as e:
            print(f"  [Aviso Instagram @{cuenta}]: {e}")
            continue

        aceptados = 0
        viejos_seguidos = 0
        for url in links:
            if aceptados >= max_por_cuenta or viejos_seguidos >= 3:
                break
            datos = leer_post_instagram(page, url)
            if not datos or not datos["caption"]:
                continue
            fecha_iso, es_vieja = _fecha_iso_externa(datos["fecha_iso_raw"])
            if es_vieja:
                # Los primeros pueden ser posts fijados (viejos): seguir mirando un poco más
                viejos_seguidos += 1
                if verbose:
                    print(f"    ✗ más viejo que {MAX_HORAS_ANTIGUEDAD} h: {datos['caption'][:80]!r}")
                continue
            viejos_seguidos = 0
            txt = datos["caption"]
            excluir, motivo = es_tema_excluido("", txt, cuenta)
            if excluir or not es_texto_espanol(txt) or es_exclusion_geografica(txt):
                if verbose:
                    print(f"    ✗ {motivo or 'sin lugar de PBA / idioma'}: {txt[:80]!r}")
                continue
            partido = detectar_partido_en_texto(txt, partido_por_defecto="Provincia de Buenos Aires")
            primer_renglon = next((l for l in txt.split("\n") if len(l.strip()) > 15), txt)[:75].strip()
            if verbose:
                print(f"    ✓ [{partido}] {txt[:80]!r} — {len(datos['comentarios'])} comentarios leídos, métricas {datos['metricas']}")
            posteos.append({
                "fuente": f"Instagram (@{cuenta})",
                "autor": datos["autor"] or cuenta,
                "url": url,
                "titulo": f"{datos['autor'] or cuenta}: {primer_renglon}",
                "texto": txt,
                "comentarios": datos["comentarios"][:4],
                "imagen_url": datos["imagen_url"],
                "partido": partido,
                "categoria": "",
                "pasada": "instagram_cuentas",
                "fecha_publicacion": fecha_iso,
                "metricas": datos["metricas"],
            })
            aceptados += 1
    return posteos


def _hechos_importantes_edicion(edicion_id) -> List[Dict[str, Any]]:
    try:
        from pdf_service import obtener_hechos_importantes
        return obtener_hechos_importantes(edicion_id=edicion_id, max_hechos=3)
    except Exception as e:
        print("Aviso: no se pudieron calcular los hechos importantes:", e)
        return []


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

    es_cdp = getattr(context, "_es_cdp", False)
    if es_cdp:
        page_x = next((pg for pg in context.pages if "x.com" in pg.url or "twitter.com" in pg.url), None)
        page_fb = next((pg for pg in context.pages if "facebook.com" in pg.url), None)
        page_ig = next((pg for pg in context.pages if "instagram.com" in pg.url), None)
        if not page_x:
            page_x = context.new_page()
            page_x.goto("https://x.com/home", wait_until="domcontentloaded")
        if not page_fb:
            page_fb = context.new_page()
            page_fb.goto("https://www.facebook.com", wait_until="domcontentloaded")
        if not page_ig:
            page_ig = context.new_page()
            page_ig.goto("https://www.instagram.com/?variant=following", wait_until="domcontentloaded")
        page = page_fb
    else:
        page = context.pages[0] if context.pages else context.new_page()
        page_x = page
        page_fb = page
        page_ig = page

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
        # Conservar el resto del estado (rotación de grupos y lista de grupos): antes se
        # pisaba el archivo entero y la rotación de grupos volvía siempre al principio.
        sdata = {}
        if os.path.exists(state_file):
            with open(state_file, "r", encoding="utf-8") as sf:
                sdata = json.load(sf)
        sdata.update({
            "proximo_indice": proximo_idx,
            "ultima_ejecucion": datetime.now().isoformat(),
            "consultas_ejecutadas": [m.get("fb_search_query") for m in matriz],
        })
        with open(state_file, "w", encoding="utf-8") as sf:
            json.dump(sdata, sf, indent=2, ensure_ascii=False)
    except Exception:
        pass

    total_recolectados = []

    try:
        # Fase 0: Medios (Google Noticias) — cubre los 135 partidos en cada corrida y trae
        # el nombre del medio y la fecha exacta, para detectar réplicas en varios medios.
        if os.getenv("TERMOMETRO_NOTICIAS", "1") != "0":
            print("\n📰 Buscando en medios (Google Noticias)...")
            try:
                from news_service import recolectar_noticias
                total_recolectados.extend(recolectar_noticias())
            except Exception as e_news:
                print(f"  [Noticias] No se pudo consultar Google Noticias: {e_news}")

        # Fase 1: Búsquedas públicas en Facebook y X
        for idx, item in enumerate(matriz, 1):
            print(f"\n[{idx}/{len(matriz)}] Buscando en Facebook: {item['fb_search_query']}...")
            fb_posts = extraer_posteos_facebook(page_fb, item["fb_url"], max_items=3)
            for p_item in fb_posts:
                p_item["partido"] = item["partido"]
                p_item["pasada"] = item["pasada"]
                p_item["categoria"] = item["categoria"]
            total_recolectados.extend(fb_posts)

            if item.get("tw_url"):
                print(f"[{idx}/{len(matriz)}] Buscando en X: {item['partido']}...")
                tw_posts = extraer_posteos_twitter(page_x, item["tw_url"], max_items=2, partido_objetivo=item.get("partido", ""))
                for t_item in tw_posts:
                    t_item["partido"] = item["partido"]
                    t_item["pasada"] = item["pasada"]
                    t_item["categoria"] = item["categoria"]
                total_recolectados.extend(tw_posts)

            time.sleep(1.2)

        # Fase 2: Grupos policiales y vecinales de PBA
        print("\n👥 Explorando grupos policiales y vecinales en Facebook...")
        page_fb = next((pg for pg in context.pages if "facebook.com" in pg.url), page)
        fb_grupos = extraer_posteos_facebook_grupos(
            page_fb, max_grupos=int(os.getenv("TERMOMETRO_GRUPOS_POR_CORRIDA", "6")), max_items_por_grupo=2
        )
        total_recolectados.extend(fb_grupos)

        # Fase 2.5: Referentes Policiales y Virginia Luján Sosa
        print("\n👮 Monitoreando referentes policiales y Virginia Luján Sosa...")
        fb_sosa = extraer_posteos_referentes_policiales(page_fb, max_items=4)
        total_recolectados.extend(fb_sosa)

        # Fase 3: Feed de amigos y contactos en Facebook
        print("\n👤 Explorando feed de amigos y contactos en Facebook...")
        fb_amigos = extraer_posteos_facebook_amigos(page_fb, max_items=int(os.getenv("TERMOMETRO_MAX_FEED_FB", "8")))
        total_recolectados.extend(fb_amigos)

        # Fase 3b: cuentas que seguís en X (pestaña "Siguiendo")
        if os.getenv("TERMOMETRO_X_SEGUIDOS", "1") != "0":
            print("\n🐦 Revisando las cuentas que seguís en X...")
            page_x = next((pg for pg in context.pages if "x.com" in pg.url or "twitter.com" in pg.url), page)
            total_recolectados.extend(extraer_posteos_x_seguidos(page_x, max_items=int(os.getenv("TERMOMETRO_MAX_X_SEGUIDOS", "8"))))

        # Fase 4: Feed de seguidos y hashtags bonaerenses en Instagram
        print("\n📸 Explorando feed de seguidos y hashtags en Instagram...")
        page_ig = next((pg for pg in context.pages if "instagram.com" in pg.url), page)
        ig_posts = extraer_posteos_instagram(page_ig, max_items=int(os.getenv("TERMOMETRO_MAX_FEED_IG", "8")))
        total_recolectados.extend(ig_posts)

        # Fase 4b: cuentas de Instagram configuradas (noticias locales que seguís)
        print("\n📸 Revisando cuentas de Instagram configuradas...")
        total_recolectados.extend(extraer_posteos_instagram_cuentas(page_ig))

        # Fase 5: reacción vecinal — comentarios de las publicaciones relevantes
        print("\n💬 Leyendo comentarios de las publicaciones que van al reporte...")
        completar_comentarios(context, total_recolectados, max_posts=int(os.getenv("TERMOMETRO_MAX_POSTS_COMENTARIOS", "8")))

    finally:
        if getattr(context, "_es_cdp", False):
            try:
                for pg in context.pages:
                    if not pg.is_closed():
                        if "x.com" in pg.url and "/search" in pg.url:
                            pg.goto("https://x.com/home", wait_until="domcontentloaded")
                        elif "facebook.com" in pg.url and "/search" in pg.url:
                            pg.goto("https://www.facebook.com", wait_until="domcontentloaded")
                        elif "instagram.com" in pg.url and ("/p/" in pg.url or "/reel/" in pg.url):
                            pg.goto("https://www.instagram.com/?variant=following", wait_until="domcontentloaded")
            except Exception:
                pass
            b_cdp = getattr(context, "_browser_cdp", None)
            if b_cdp:
                try:
                    b_cdp.close()
                except Exception:
                    pass
            p.stop()
            print("  🌐 Desconectado de navegador permanente. La ventana de X permanece abierta.")
        else:
            context.close()
            p.stop()

    print(f"\n✓ Recolección finalizada. Total de publicaciones capturadas: {len(total_recolectados)}")
    # Cuántas vino de cada red: si alguna da 0 en todas las corridas, ahí está el problema
    por_red: Dict[str, int] = {}
    for p_item in total_recolectados:
        f_red = (p_item.get("fuente") or "").split(" (")[0] or "Otro"
        por_red[f_red] = por_red.get(f_red, 0) + 1
    print("  Por red: " + (", ".join(f"{k}: {v}" for k, v in sorted(por_red.items())) or "ninguna"))
    con_coment = sum(1 for p_item in total_recolectados if p_item.get("comentarios"))
    print(f"  Publicaciones con comentarios leídos: {con_coment}")

    if total_recolectados:
        data_resp = {}
        edicion_id = None
        try:
            # Por defecto se guarda DIRECTO con el código de este proceso. Antes se mandaba al
            # panel web (app.py), que es un proceso que queda corriendo días: después de un
            # git pull seguía clasificando con el código viejo (sin métricas, sin los filtros
            # nuevos) hasta que alguien lo reiniciara.
            if os.getenv("TERMOMETRO_INGESTA_API", "0") != "1":
                raise RuntimeError("ingesta directa (TERMOMETRO_INGESTA_API=0)")
            resp = requests.post(API_INGEST_URL, json={
                "modo": "sesion_abierta_playwright",
                "posteos": total_recolectados
            }, timeout=60)
            data_resp = resp.json()
            print("Resultado de ingesta en base local (vía API):", data_resp)
            edicion_id = data_resp.get("resultado", {}).get("edicion_id")
        except Exception as e:
            print(f"  Guardando en la base con el motor local ({e})...")
            try:
                from engine import ingerir_posteos_directos_facebook
                res_ing = ingerir_posteos_directos_facebook(total_recolectados, modo="sesion_abierta_playwright")
                data_resp = {"ok": True, "resultado": res_ing}
                edicion_id = res_ing.get("edicion_id")
                print("Resultado de ingesta directa local:", data_resp)
            except Exception as e_direct:
                print("Error crítico en ingesta directa:", e_direct)

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
                    "SELECT titulo, partido, categoria FROM hallazgos WHERE (edicion_id = ? OR ultima_edicion_id = ?) AND es_convocatoria = 1",
                    (edicion_id, edicion_id),
                ).fetchall()
                nombres = conn.execute(
                    "SELECT nombre FROM nombres_propios WHERE ultima_edicion_id = ? OR vigente = 1 ORDER BY (ultima_edicion_id = ?) DESC, id DESC LIMIT 5",
                    (edicion_id, edicion_id),
                ).fetchall()
                hallazgos_dest = conn.execute(
                    "SELECT partido, autor, texto FROM hallazgos WHERE (edicion_id = ? OR ultima_edicion_id = ?) AND descartado = 0 ORDER BY id DESC LIMIT 3",
                    (edicion_id, edicion_id),
                ).fetchall()
                grupos_dest = list(conn.execute(
                    """
                    SELECT id, fuente, autor, partido, titulo, texto, url, imagen_url FROM hallazgos
                    WHERE (edicion_id = ? OR ultima_edicion_id = ?)
                      AND (pasada IN ('grupos_vecinales', 'feed_amigos', 'referentes_policiales', 'instagram_amigos', 'instagram_cuentas', 'x_seguidos')
                           OR fuente LIKE '%Grupo%' OR fuente LIKE '%Amigos%' OR fuente LIKE '%Virginia%' OR fuente LIKE '%Instagram%')
                      AND descartado = 0
                      AND url NOT LIKE '%facebook.com'
                      AND url NOT LIKE '%facebook.com/'
                      AND (url LIKE '%/posts/%' OR url LIKE '%/permalink/%' OR url LIKE '%/status/%' OR url LIKE '%/p/%' OR url LIKE '%/reel/%' OR url LIKE '%fbid=%' OR url LIKE '%/share/%' OR url NOT LIKE '%facebook.com%')
                    ORDER BY (imagen_url IS NOT NULL AND imagen_url != '') DESC, id DESC LIMIT 4
                    """,
                    (edicion_id, edicion_id),
                ).fetchall())

                if len(grupos_dest) < 4:
                    corte_24h = (datetime.now() - timedelta(hours=24)).isoformat(timespec="seconds")
                    ids_existentes = {g["id"] for g in grupos_dest}
                    extra_grupos = conn.execute(
                        """
                        SELECT id, fuente, autor, partido, titulo, texto, url, imagen_url FROM hallazgos
                        WHERE (fecha_deteccion >= ? OR ultima_deteccion >= ?)
                          AND (pasada IN ('grupos_vecinales', 'feed_amigos', 'referentes_policiales', 'instagram_amigos', 'instagram_cuentas', 'x_seguidos')
                               OR fuente LIKE '%Grupo%' OR fuente LIKE '%Amigos%' OR fuente LIKE '%Virginia%' OR fuente LIKE '%Instagram%')
                          AND descartado = 0
                          AND url NOT LIKE '%facebook.com'
                          AND url NOT LIKE '%facebook.com/'
                          AND (url LIKE '%/posts/%' OR url LIKE '%/permalink/%' OR url LIKE '%/status/%' OR url LIKE '%/p/%' OR url LIKE '%/reel/%' OR url LIKE '%fbid=%' OR url LIKE '%/share/%' OR url NOT LIKE '%facebook.com%')
                        ORDER BY (imagen_url IS NOT NULL AND imagen_url != '') DESC, id DESC LIMIT 10
                        """,
                        (corte_24h, corte_24h),
                    ).fetchall()
                    for eg in extra_grupos:
                        if eg["id"] not in ids_existentes:
                            ids_existentes.add(eg["id"])
                            grupos_dest.append(eg)
                            if len(grupos_dest) >= 4:
                                break
                conn.close()

                datos_edicion = {
                    "edicion_id": edicion_id,
                    "total_hallazgos": data_resp.get("resultado", {}).get("procesados", len(total_recolectados)),
                    "nuevos_hallazgos": data_resp.get("resultado", {}).get("nuevos", 0),
                    "convocatorias": [dict(c) for c in convocatorias],
                    "nombres_propios": [n["nombre"] for n in nombres],
                    "hallazgos_destacados": [dict(h) for h in hallazgos_dest],
                    "relevamiento_grupos": [dict(g) for g in grupos_dest],
                    "hechos_importantes": _hechos_importantes_edicion(edicion_id),
                }
                print("📲 Enviando reporte y PDF a Telegram...")
                res_tg = enviar_alerta_telegram(datos_edicion, ruta_pdf=ruta_pdf or "")
                if res_tg.get("ok"):
                    print("✓ ¡Alerta y PDF enviados exitosamente por Telegram!")
                else:
                    print("Aviso Telegram:", res_tg)
            except Exception as e_tg:
                print("Error enviando por Telegram:", e_tg)


def conectar_cuenta_x():
    """
    Abre una ventana visible de navegador directo en X (Twitter)
    para conectar o cambiar a tu otra cuenta de X.
    Tus sesiones quedan guardadas permanentemente en user_session_browser.
    """
    print("\n=======================================================")
    print("🐦 CONECTAR CUENTA DE X (TWITTER) — Termómetro Digital")
    print("Se abrirá la ventana del navegador en tu pantalla.")
    print("Podés:")
    print(" 1. Si querés mantener ambas cuentas: hacé clic abajo a la izquierda")
    print("    en tu perfil y elegí 'Agregar una cuenta existente'.")
    print(" 2. O cerrá la sesión actual e iniciá con la nueva cuenta.")
    print("Cuando termines de iniciar sesión, simplemente cerrá la ventana.")
    print("=======================================================\n")

    p, context = lanzar_navegador_sesion(headless=False)
    page = context.new_page()
    page.goto("https://x.com/home")

    print("Esperando a que cierres la ventana del navegador...")
    try:
        while len(context.pages) > 0:
            time.sleep(1)
    except Exception:
        pass
    finally:
        context.close()
        p.stop()
        print("\n✓ Sesión de X guardada correctamente en user_session_browser.")


def conectar_cuenta_ig():
    """
    Abre o enfoca la pestaña de Instagram en el navegador permanente
    para iniciar sesión o actualizar la cuenta con los nuevos seguidos.
    """
    print("\n=======================================================")
    print("📸 CONECTAR CUENTA DE INSTAGRAM — Termómetro Digital")
    print("Se abrió la pestaña de Instagram en tu navegador.")
    print("Iniciá sesión con tu cuenta actualizada.")
    print("Tus seguidos y sesiones quedan guardados permanentemente.")
    print("=======================================================\n")

    p = sync_playwright().start()
    try:
        browser_cdp = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        ctx = browser_cdp.contexts[0]
        page_ig = next((pg for pg in ctx.pages if "instagram.com" in pg.url), None)
        if not page_ig:
            page_ig = ctx.new_page()
        page_ig.goto("https://www.instagram.com/accounts/login/")
        page_ig.bring_to_front()
        print("✓ Pestaña de Instagram activa en el navegador.")
        print("Iniciá sesión en la ventana y dejala abierta.")
        browser_cdp.close()
    except Exception:
        p_c, context = lanzar_navegador_sesion(headless=False)
        page = context.new_page()
        page.goto("https://www.instagram.com/accounts/login/")
        print("Esperando a que cierres la ventana...")
        try:
            while len(context.pages) > 0:
                time.sleep(1)
        except Exception:
            pass
        finally:
            context.close()
            p_c.stop()
    finally:
        p.stop()


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


def probar_x(consulta: str, headless: bool = False) -> None:
    """Corre UNA búsqueda en X, muestra cada tweet aceptado/descartado y no guarda nada."""
    from engine import construir_url_twitter_search

    url = construir_url_twitter_search(consulta)
    print(f"🔎 Probando X con: {consulta}\n   URL: {normalizar_url_busqueda_x(url)}\n")
    p, context = lanzar_navegador_sesion(headless=headless)
    try:
        page = context.pages[0] if context.pages else context.new_page()
        tweets = extraer_posteos_twitter(page, url, max_items=20, verbose=True)
        print(f"\nResultado: {len(tweets)} tweets pasarían al reporte.")
    finally:
        context.close()
        p.stop()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scraper con sesión abierta para Termómetro Digital")
    parser.add_argument("--login", action="store_true", help="Abrir navegador para iniciar sesión una única vez")
    parser.add_argument("--login-x", action="store_true", help="Abrir ventana visible de X para conectar o cambiar cuenta de Twitter")
    parser.add_argument("--login-ig", action="store_true", help="Abrir o enfocar pestaña de Instagram para conectar o actualizar cuenta")
    parser.add_argument("--headless", action="store_true", help="Correr en segundo plano sin ventana visible")
    parser.add_argument("--max-consultas", type=int, default=5, help="Cantidad de consultas a ejecutar")
    parser.add_argument("--probar-ig", metavar="CUENTA", help="Probar la lectura de una cuenta de Instagram sin guardar nada (ej: hechosyderecho)")
    parser.add_argument("--probar-x", metavar="CONSULTA", help='Probar una búsqueda en X sin guardar nada (ej: "La Matanza inseguridad")')
    args = parser.parse_args()

    if args.probar_ig:
        p_ig, ctx_ig = lanzar_navegador_sesion(headless=args.headless)
        try:
            pag = ctx_ig.pages[0] if ctx_ig.pages else ctx_ig.new_page()
            res_ig = extraer_posteos_instagram_cuentas(pag, [args.probar_ig.lstrip("@")], verbose=True)
            print(f"\nResultado: {len(res_ig)} publicaciones pasarían al reporte.")
            for r_ig in res_ig:
                for c_ig in r_ig["comentarios"]:
                    print(f"    💬 {c_ig[:120]}")
        finally:
            ctx_ig.close()
            p_ig.stop()
    elif args.probar_x:
        probar_x(args.probar_x, headless=args.headless)
    elif args.login_x:
        conectar_cuenta_x()
    elif args.login:
        modo_login()
    else:
        ejecutar_ciclo_recoleccion(headless=args.headless, max_consultas=args.max_consultas)
