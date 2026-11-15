# -*- coding: utf-8 -*-
"""
Motor de búsqueda y recolección multi-red para Termómetro Digital PBA.
Cubre:
- Facebook (site:facebook.com)
- X / Twitter (site:x.com OR site:twitter.com)
- Instagram (site:instagram.com)
- Google Search directo + Brave API + DuckDuckGo
- Extracción de comentarios vecinales si se aportan URLs o publicaciones completas
"""

import base64
import os
import re
import time
import urllib.parse
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

from config_pba import (
    ANCLAJES_GENERALES_PBA,
    HASHTAGS_BASE,
    MODIFICADORES_CONVOCATORIA,
    PARTIDOS_CONURBANO,
    PARTIDOS_PBA,
    STOPWORDS_ES,
    es_exclusion_geografica,
    generar_variantes_termino,
    quitar_tildes,
)
from database import (
    cerrar_edicion,
    crear_edicion,
    get_conn,
    insertar_hallazgo,
    obtener_diccionario_completo,
    obtener_todos_los_terminos_conocidos,
    registrar_nombre_propio,
    registrar_palabra_candidata,
)

# Cargar variables de entorno
LOCAL_ENV = os.path.join(os.path.dirname(__file__), ".env")
OSINT_ENV = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "osint-brave-search", ".env")
)
load_dotenv(LOCAL_ENV)
if not os.getenv("BRAVE_API_KEY") and os.path.exists(OSINT_ENV):
    load_dotenv(OSINT_ENV)


PATRONES_NOMBRES_PROPIOS = [
    (
        "Víctima / Caso",
        re.compile(
            r"(?:justicia\s+(?:por|x)|#JusticiaPor\s*|pedido\s+de\s+justicia\s+por|mataron\s+a|asesinaron\s+a|atropellaron\s+a|femicidio\s+de)\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+){0,2})"
        ),
    ),
    (
        "Barrio / Lugar",
        re.compile(
            r"(?:[Bb]arrio|[Vv]illa|[Cc]ountry|[Aa]sentamiento|[Pp]laza|[Cc]omisaría)\s+([A-ZÁÉÍÓÚÑ0-9][a-záéíóúñ0-9]+(?:\s+[A-ZÁÉÍÓÚÑ0-9][a-záéíóúñ0-9]+){0,2})"
        ),
    ),
    (
        "Empresa / Institución",
        re.compile(
            r"(?:[Ff]ábrica|[Ee]mpresa|[Pp]apelera|[Ff]rigorífico|[Cc]ooperativa|[Ee]scuela|[Jj]ardín|[Cc]olegio|[Hh]ospital|[Cc]línica|[Tt]extil|[Mm]etalúrgica)\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+(?:del|de\s+la|de|los|las|[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)){0,3})"
        ),
    ),
    (
        "Entidad entrecomillada",
        re.compile(
            r'["“«]([A-ZÁÉÍÓÚÑ][A-Za-záéíóúñÁÉÍÓÚÑ0-9\s]{3,35})["”»]'
        ),
    ),
]

CONTEXTO_RECLAMO_SEEDS = {
    "reclamo", "reclaman", "denuncia", "denuncian", "peligro", "urgente",
    "vergüenza", "verguenza", "abandono", "abandonados", "hartos", "cansados",
    "alerta", "cuidado", "robo", "robaron", "asaltaron", "entraron", "tiros",
    "basural", "cloacas", "pozo", "bache", "luminaria", "oscuras", "oscuridad",
    "semaforo", "semáforo", "puente", "zanja", "contaminacion", "contaminación",
    "humo", "olor", "quema", "tala", "ambulancia", "salita", "guardia",
    "transporte", "ramal", "frecuencia", "tarifa", "estafa", "entraderas",
    "motochorros", "inhibidores", "cables", "transformador", "medidor"
}


def construir_url_facebook_search(query: str, solo_recientes: bool = True) -> str:
    q_encoded = urllib.parse.quote(query)
    base = f"https://www.facebook.com/search/posts?q={q_encoded}"
    if solo_recientes:
        filtro_recientes = '{"recent_posts:0":"{\\"name\\":\\"recent_posts\\",\\"args\\":\\"\\"}"}'
        b64 = base64.b64encode(filtro_recientes.encode("utf-8")).decode("utf-8")
        base += f"&filters={urllib.parse.quote(b64)}"
    return base


def construir_url_twitter_search(query: str) -> str:
    q_encoded = urllib.parse.quote(f"{query} -filter:replies")
    return f"https://x.com/search?q={q_encoded}&f=live"


def construir_url_instagram_search(query: str) -> str:
    # Si empieza con hashtag, ir a la etiqueta, si no a búsqueda general
    q_clean = query.replace("#", "").strip()
    return f"https://www.instagram.com/explore/tags/{urllib.parse.quote(q_clean)}/"


def construir_url_google_search(query: str) -> str:
    q_encoded = urllib.parse.quote(query)
    return f"https://www.google.com/search?q={q_encoded}&tbs=qdr:w"


def detectar_partido_en_texto(texto: str, partido_por_defecto: str = "") -> str:
    t_lower = quitar_tildes(texto.lower())
    for partido in PARTIDOS_PBA:
        p_norm = quitar_tildes(partido.lower())
        if re.search(r"\b" + re.escape(p_norm) + r"\b", t_lower):
            return partido
    return partido_por_defecto or "Provincia de Buenos Aires"


def detectar_modificadores_agenda(texto: str) -> List[str]:
    t_lower = quitar_tildes(texto.lower())
    encontrados = []
    for mod in MODIFICADORES_CONVOCATORIA:
        m_norm = quitar_tildes(mod.lower())
        if m_norm == "hs":
            if re.search(r"\b\d{1,2}(?::\d{2})?\s*hs\b", t_lower):
                encontrados.append("hs (horario)")
        elif m_norm in t_lower:
            encontrados.append(mod)
    return encontrados


def extraer_nombres_propios(texto: str) -> List[Tuple[str, str]]:
    descartar = {
        "Buenos Aires", "Provincia De", "Capital Federal", "Facebook", "Twitter", "Instagram",
        "Policía Bonaerense", "Conurbano Bonaerense", "Gran Buenos",
        "Todos Los", "Muchas Gracias", "Por Favor"
    }
    partidos_set = {p.lower() for p in PARTIDOS_PBA}
    hallados: List[Tuple[str, str]] = []
    vistos = set()

    for tipo, regex in PATRONES_NOMBRES_PROPIOS:
        for match in regex.finditer(texto):
            candidato = match.group(1).strip(" .,;:!¡?¿-—")
            if len(candidato) < 4 or len(candidato) > 40:
                continue
            if candidato in descartar or candidato.lower() in partidos_set:
                continue
            if candidato.lower() not in vistos:
                vistos.add(candidato.lower())
                hallados.append((candidato, tipo))
    return hallados


def extraer_candidatos_pasada_abierta(texto: str) -> List[Tuple[str, str]]:
    conocidos = obtener_todos_los_terminos_conocidos()
    t_clean = re.sub(r"https?://\S+", " ", texto.lower())
    palabras = re.findall(r"[a-záéíóúñ#]{4,22}", t_clean)

    filtradas = [
        p for p in palabras
        if p not in STOPWORDS_ES
        and quitar_tildes(p) not in STOPWORDS_ES
        and p not in conocidos
        and quitar_tildes(p) not in conocidos
    ]

    candidatos: List[Tuple[str, str]] = []

    for p in filtradas:
        if p.startswith("#") and len(p) > 5:
            candidatos.append((p, inferir_categoria_por_contexto(t_clean)))

    for i in range(len(palabras) - 1):
        w1, w2 = palabras[i], palabras[i + 1]
        if w1 in STOPWORDS_ES or w2 in STOPWORDS_ES:
            continue
        bigrama = f"{w1} {w2}"
        if bigrama in conocidos or quitar_tildes(bigrama) in conocidos:
            continue
        if w1 in CONTEXTO_RECLAMO_SEEDS or w2 in CONTEXTO_RECLAMO_SEEDS:
            candidatos.append((bigrama, inferir_categoria_por_contexto(t_clean)))

    for p in filtradas:
        if p in CONTEXTO_RECLAMO_SEEDS and p not in conocidos:
            candidatos.append((p, inferir_categoria_por_contexto(t_clean)))

    unicos = []
    vistos = set()
    for term, cat in candidatos:
        if term not in vistos:
            vistos.add(term)
            unicos.append((term, cat))
    return unicos[:4]


def inferir_categoria_por_contexto(texto_lower: str) -> str:
    if any(w in texto_lower for w in ("robo", "robaron", "asalto", "tiros", "motochorro", "entraderas", "patrullero", "comisaría", "comisaria")):
        return "seguridad"
    if any(w in texto_lower for w in ("juez", "fiscal", "juicio", "condena", "impune", "asesino")):
        return "justicia"
    if any(w in texto_lower for w in ("motos", "escape", "ruido", "clandestina", "after")):
        return "eventos_no_autorizados"
    if any(w in texto_lower for w in ("policía", "policia", "efectivo", "uniformado", "comisario")):
        return "imagen_institucional"
    return "sociales_servicios"


def clasificar_hallazgo(
    titulo: str,
    texto: str,
    categoria_forzada: str = "",
    termino_forzado: str = "",
    partido_objetivo: str = "",
    anclaje_usado: str = "",
    pasada: str = "anclaje_general",
) -> Optional[Dict[str, Any]]:
    combinado = f"{titulo} {texto}".strip()

    if es_exclusion_geografica(combinado, partido_objetivo):
        return None

    diccionario = obtener_diccionario_completo()
    comb_lower = combinado.lower()
    comb_sin_tilde = quitar_tildes(comb_lower)

    categoria_detectada = categoria_forzada or "seguridad"
    termino_detectado = termino_forzado or ""
    variante_usada = termino_forzado or ""

    if not termino_detectado:
        for cat_key, cat_info in diccionario.items():
            for term in cat_info["terminos"]:
                for var in generar_variantes_termino(term):
                    v_low = var.lower()
                    if v_low in comb_lower or quitar_tildes(v_low) in comb_sin_tilde:
                        categoria_detectada = cat_key
                        termino_detectado = term
                        variante_usada = var
                        break
                if termino_detectado:
                    break
            if termino_detectado:
                break

    if pasada == "pasada_abierta" and not termino_detectado:
        categoria_detectada = inferir_categoria_por_contexto(comb_lower)
        termino_detectado = "vecinos (pasada abierta)"
        variante_usada = "vecinos"

    partido = detectar_partido_en_texto(combinado, partido_objetivo)
    modificadores = detectar_modificadores_agenda(combinado)
    es_convocatoria = len(modificadores) > 0
    nombres_propios = extraer_nombres_propios(combinado)

    relevancia = 65
    if es_convocatoria:
        relevancia += 20
    if nombres_propios:
        relevancia += 10
    if partido in PARTIDOS_PBA:
        relevancia += 5
    relevancia = min(relevancia, 100)

    return {
        "categoria": categoria_detectada,
        "termino_detectado": termino_detectado or "monitoreo general",
        "variante_usada": variante_usada or termino_detectado,
        "partido": partido,
        "anclaje_usado": anclaje_usado or partido,
        "pasada": pasada,
        "es_convocatoria": es_convocatoria,
        "modificadores_agenda": modificadores,
        "nombres_propios": [n[0] for n in nombres_propios],
        "nombres_propios_tuplas": nombres_propios,
        "relevancia": relevancia,
    }


class BuscadorMultiRedPBA:
    """
    Ejecuta búsquedas cruzadas sobre Facebook, X / Twitter, Instagram y Google
    usando Brave Search API, Google Search y respaldo DuckDuckGo.
    """

    BRAVE_URL = "https://api.search.brave.com/res/v1/web/search"

    def __init__(self) -> None:
        self.brave_key = os.getenv("BRAVE_API_KEY", "").strip()
        self.google_key = os.getenv("GOOGLE_API_KEY", "").strip()
        self.google_cx = os.getenv("GOOGLE_CSE_ID", "").strip()

        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/125.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "es-AR,es;q=0.9",
            }
        )

    def buscar_multi_red(
        self, query: str, count: int = 12, freshness: str = "pw"
    ) -> List[Dict[str, str]]:
        # 1. Probar Brave API (rápido y con frescura configurable)
        if self.brave_key and len(self.brave_key) > 5:
            res = self._buscar_brave(query, count=count, freshness=freshness)
            if res:
                return res

        # 2. Probar Google Custom Search si está configurado
        if self.google_key and self.google_cx:
            res = self._buscar_google_api(query, count=count)
            if res:
                return res

        # 3. Respaldo DuckDuckGo HTML
        return self._buscar_ddg_html(query, max_results=count)

    def _buscar_brave(
        self, query: str, count: int = 12, freshness: str = "pw"
    ) -> List[Dict[str, str]]:
        headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": self.brave_key,
        }
        params: Dict[str, Any] = {
            "q": query,
            "count": min(count, 20),
            "search_lang": "es",
            "country": "ar",
            "text_decorations": 0,
        }
        if freshness:
            params["freshness"] = freshness

        try:
            resp = requests.get(self.BRAVE_URL, headers=headers, params=params, timeout=12)
            if resp.status_code != 200:
                return []
            data = resp.json()
            raw = data.get("web", {}).get("results", [])
            items = []
            for r in raw:
                url = r.get("url", "")
                fuente = self._detectar_plataforma(url)
                items.append(
                    {
                        "titulo": r.get("title", f"Publicación en {fuente}"),
                        "texto": r.get("description", ""),
                        "url": url,
                        "fecha_publicacion": r.get("page_age") or r.get("age") or "Reciente",
                        "fuente": fuente,
                    }
                )
            return items
        except Exception:
            return []

    def _buscar_google_api(self, query: str, count: int = 10) -> List[Dict[str, str]]:
        try:
            url = "https://www.googleapis.com/customsearch/v1"
            params = {
                "key": self.google_key,
                "cx": self.google_cx,
                "q": query,
                "num": min(count, 10),
                "gl": "ar",
                "hl": "es"
            }
            resp = requests.get(url, params=params, timeout=12)
            if resp.status_code != 200:
                return []
            data = resp.json()
            items = []
            for item in data.get("items", []):
                link = item.get("link", "")
                fuente = self._detectar_plataforma(link)
                items.append({
                    "titulo": item.get("title", f"Publicación {fuente}"),
                    "texto": item.get("snippet", ""),
                    "url": link,
                    "fecha_publicacion": "Google Web Reciente",
                    "fuente": fuente
                })
            return items
        except Exception:
            return []

    def _buscar_ddg_html(self, query: str, max_results: int = 10) -> List[Dict[str, str]]:
        try:
            resp = self.session.post(
                "https://html.duckduckgo.com/html/",
                data={"q": query, "kl": "ar-es", "df": "w"},
                timeout=12,
            )
            if resp.status_code != 200:
                return []
            soup = BeautifulSoup(resp.text, "html.parser")
            items = []
            for div in soup.select(".result")[:max_results]:
                a_tag = div.select_one(".result__a")
                snip = div.select_one(".result__snippet")
                if not a_tag:
                    continue
                url = a_tag.get("href", "")
                fuente = self._detectar_plataforma(url)
                titulo = a_tag.get_text(" ", strip=True)
                texto = snip.get_text(" ", strip=True) if snip else ""
                items.append(
                    {
                        "titulo": titulo,
                        "texto": texto,
                        "url": url,
                        "fecha_publicacion": "Reciente",
                        "fuente": fuente,
                    }
                )
            return items
        except Exception:
            return []

    @staticmethod
    def _detectar_plataforma(url: str) -> str:
        u = url.lower()
        if "facebook.com" in u:
            return "Facebook"
        if "x.com" in u or "twitter.com" in u:
            return "X (Twitter)"
        if "instagram.com" in u:
            return "Instagram"
        if "youtube.com" in u:
            return "YouTube"
        if "tiktok.com" in u:
            return "TikTok"
        return "Web Regional PBA"


def generar_matriz_consultas_multired(
    partidos_seleccionados: Optional[List[str]] = None,
    incluir_135_completos: bool = False,
) -> List[Dict[str, str]]:
    """
    Genera consultas combinadas para Facebook, X/Twitter e Instagram.
    """
    diccionario = obtener_diccionario_completo()
    consultas: List[Dict[str, str]] = []

    exclusiones_dork = '-"CABA" -"Capital Federal" -"Policía de la Ciudad" -Córdoba -Rosario'
    anclaje_or = '("provincia de Buenos Aires" OR "bonaerense" OR "conurbano")'
    redes_or = '(site:facebook.com OR site:x.com OR site:twitter.com OR site:instagram.com)'

    # 1. Pasada 1: Categorías generales en todas las redes
    for cat_key, cat_info in diccionario.items():
        terminos = cat_info["terminos"]
        for i in range(0, len(terminos), 5):
            lote = terminos[i : i + 5]
            expansiones = []
            for t in lote:
                for v in generar_variantes_termino(t)[:2]:
                    expansiones.append(f'"{v}"')
            or_terms = "(" + " OR ".join(expansiones) + ")"
            dork_web = f"{redes_or} {or_terms} {anclaje_or} {exclusiones_dork}"
            fb_q = f"{lote[0]} provincia de Buenos Aires"
            tw_q = f"{lote[0]} Buenos Aires"
            consultas.append(
                {
                    "pasada": "anclaje_general",
                    "categoria": cat_key,
                    "termino_base": ", ".join(lote[:3]),
                    "partido": "Provincia de Buenos Aires",
                    "anclaje": "provincia de Buenos Aires / bonaerense / conurbano",
                    "dork_web": dork_web,
                    "fb_search_query": fb_q,
                    "fb_url": construir_url_facebook_search(fb_q),
                    "tw_url": construir_url_twitter_search(tw_q),
                    "ig_url": construir_url_instagram_search(lote[0]),
                    "google_url": construir_url_google_search(f'"{lote[0]}" {anclaje_or}')
                }
            )

    # 2. Pasada de Agenda Temprana y Convocatorias
    mods_sample = '("nos juntamos" OR "convocamos" OR "vecinos autoconvocados" OR "punto de encuentro" OR "marcha por seguridad" OR "corte de calle")'
    consultas.append(
        {
            "pasada": "agenda_convocatorias",
            "categoria": "seguridad",
            "termino_base": "Convocatorias y Agenda Vecinal",
            "partido": "Provincia de Buenos Aires",
            "anclaje": "conurbano / bonaerense",
            "dork_web": f"{redes_or} {mods_sample} {anclaje_or} {exclusiones_dork}",
            "fb_search_query": "vecinos autoconvocados nos juntamos provincia de Buenos Aires",
            "fb_url": construir_url_facebook_search("vecinos autoconvocados nos juntamos Buenos Aires"),
            "tw_url": construir_url_twitter_search("vecinos autoconvocados Buenos Aires"),
            "ig_url": construir_url_instagram_search("VecinosEnAlerta"),
            "google_url": construir_url_google_search(f'{mods_sample} {anclaje_or}')
        }
    )

    # 3. Pasada por Partidos
    lista_partidos = (
        partidos_seleccionados
        if partidos_seleccionados
        else (PARTIDOS_PBA if incluir_135_completos else PARTIDOS_CONURBANO[:12])
    )

    for partido in lista_partidos:
        fb_q = f'"{partido}" inseguridad reclamo vecinos'
        consultas.append(
            {
                "pasada": "partido_135",
                "categoria": "seguridad",
                "termino_base": f"Núcleo Seguridad {partido}",
                "partido": partido,
                "anclaje": partido,
                "dork_web": f'{redes_or} "{partido}" ("inseguridad" OR "corte de calle" OR "sin luz" OR "reclamo") {exclusiones_dork}',
                "fb_search_query": fb_q,
                "fb_url": construir_url_facebook_search(fb_q),
                "tw_url": construir_url_twitter_search(f'"{partido}" (inseguridad OR "sin luz" OR reclamo)'),
                "ig_url": construir_url_instagram_search(f"Reclamo{partido.replace(' ', '')}"),
                "google_url": construir_url_google_search(f'"{partido}" reclamo vecinos')
            }
        )

    # 4. Pasada Abierta ("vecinos" + partido)
    for partido in lista_partidos:
        fb_q = f'"vecinos" "{partido}"'
        consultas.append(
            {
                "pasada": "pasada_abierta",
                "categoria": "seguridad",
                "termino_base": "vecinos (pasada abierta)",
                "partido": partido,
                "anclaje": f"vecinos + {partido}",
                "dork_web": f'{redes_or} "vecinos" "{partido}" {exclusiones_dork}',
                "fb_search_query": fb_q,
                "fb_url": construir_url_facebook_search(fb_q),
                "tw_url": construir_url_twitter_search(f'"vecinos" "{partido}"'),
                "ig_url": construir_url_instagram_search(f"Vecinos{partido.replace(' ', '')}"),
                "google_url": construir_url_google_search(f'"vecinos" "{partido}"')
            }
        )

    return consultas


def ejecutar_barrido(
    modo: str = "automatico",
    partidos_filtro: Optional[List[str]] = None,
    max_consultas: int = 24,
    freshness: str = "pw",
) -> Dict[str, Any]:
    edicion_id = crear_edicion(modo=modo, notas=f"Barrido Multi-Red ({freshness})")
    buscador = BuscadorMultiRedPBA()

    matriz = generar_matriz_consultas_multired(partidos_seleccionados=partidos_filtro)

    p1 = [c for c in matriz if c["pasada"] in ("anclaje_general", "agenda_convocatorias")]
    p2 = [c for c in matriz if c["pasada"] == "partido_135"]
    p4 = [c for c in matriz if c["pasada"] == "pasada_abierta"]

    seleccion: List[Dict[str, str]] = []
    seleccion.extend(p1[: max(6, max_consultas // 3)])
    seleccion.extend(p2[: max(8, max_consultas // 3)])
    seleccion.extend(p4[: max(5, max_consultas // 4)])
    seleccion = seleccion[:max_consultas]

    total_hallazgos = 0
    nuevos_hallazgos = 0
    partidos_tocados = set()
    nuevas_propuestas = []
    convocatorias_detectadas = []

    for item_q in seleccion:
        partidos_tocados.add(item_q["partido"])
        resultados = buscador.buscar_multi_red(
            item_q["dork_web"], count=10, freshness=freshness
        )

        for r in resultados:
            info = clasificar_hallazgo(
                titulo=r.get("titulo", ""),
                texto=r.get("texto", ""),
                categoria_forzada=item_q["categoria"],
                termino_forzado=(
                    item_q["termino_base"]
                    if item_q["pasada"] == "nombre_propio"
                    else ""
                ),
                partido_objetivo=item_q["partido"],
                anclaje_usado=item_q["anclaje"],
                pasada=item_q["pasada"],
            )
            if not info:
                continue

            total_hallazgos += 1
            registro = {
                "edicion_id": edicion_id,
                "fecha_publicacion": r.get("fecha_publicacion", "Reciente"),
                "fuente": r.get("fuente", "Facebook"),
                "url": r.get("url", item_q["fb_url"]),
                "titulo": r.get("titulo", ""),
                "texto": r.get("texto", ""),
                "autor": f"Alerta {r.get('fuente', 'Redes')} PBA",
                **info,
            }
            es_nuevo = insertar_hallazgo(registro)
            if es_nuevo:
                nuevos_hallazgos += 1
                if info.get("es_convocatoria"):
                    convocatorias_detectadas.append({
                        "titulo": r.get("titulo", ""),
                        "partido": info["partido"],
                        "categoria": info["categoria"]
                    })

            for nom_propio, tipo_np in info.get("nombres_propios_tuplas", []):
                registrar_nombre_propio(
                    nombre=nom_propio,
                    tipo=tipo_np,
                    partido=info["partido"],
                    categoria_origen=info["categoria"],
                    contexto=r.get("titulo", "")[:140],
                    edicion_id=edicion_id,
                )

            if item_q["pasada"] == "pasada_abierta":
                comb_texto = f"{r.get('titulo', '')} {r.get('texto', '')}"
                candidatos = extraer_candidatos_pasada_abierta(comb_texto)
                for palabra_cand, cat_sug in candidatos:
                    res_cand = registrar_palabra_candidata(
                        palabra=palabra_cand,
                        categoria_sugerida=cat_sug,
                        partido_origen=info["partido"],
                        ejemplo_texto=comb_texto,
                        edicion_id=edicion_id,
                    )
                    if res_cand.get("status") == "propuesta":
                        nuevas_propuestas.append(palabra_cand)

        time.sleep(0.3)

    cerrar_edicion(
        edicion_id=edicion_id,
        partidos_barridos=len(partidos_tocados),
        consultas_ejecutadas=len(seleccion),
        total_hallazgos=total_hallazgos,
        nuevos_hallazgos=nuevos_hallazgos,
    )

    return {
        "edicion_id": edicion_id,
        "consultas_ejecutadas": len(seleccion),
        "partidos_barridos": len(partidos_tocados),
        "total_hallazgos": total_hallazgos,
        "nuevos_hallazgos": nuevos_hallazgos,
        "nuevas_propuestas": list(set(nuevas_propuestas)),
        "convocatorias": convocatorias_detectadas
    }


def ingerir_posteos_directos_facebook(
    posteos: List[Dict[str, Any]], modo: str = "facebook_directo_navegador"
) -> Dict[str, Any]:
    edicion_id = crear_edicion(modo=modo, notas="Ingesta directa desde Redes / Navegador")
    total_procesados = 0
    nuevos = 0
    partidos = set()

    for p in posteos:
        titulo = p.get("titulo") or p.get("autor") or "Publicación Vecinal"
        texto = p.get("texto", "")
        # Si incluye comentarios, concatenarlos para análisis de agenda
        comentarios = p.get("comentarios", [])
        if comentarios and isinstance(comentarios, list):
            texto += " [Comentarios: " + " | ".join(str(c) for c in comentarios) + "]"

        partido_obj = p.get("partido", "")
        pasada = p.get("pasada", "anclaje_general")

        info = clasificar_hallazgo(
            titulo=titulo,
            texto=texto,
            categoria_forzada=p.get("categoria", ""),
            termino_forzado=p.get("termino_detectado", ""),
            partido_objetivo=partido_obj,
            anclaje_usado=p.get("anclaje", partido_obj or "Ingesta Directa"),
            pasada=pasada,
        )
        if not info:
            continue

        total_procesados += 1
        partidos.add(info["partido"])
        url = p.get("url") or construir_url_facebook_search(
            f"{info['termino_detectado']} {info['partido']}"
        )

        es_nuevo = insertar_hallazgo(
            {
                "edicion_id": edicion_id,
                "fecha_publicacion": p.get("fecha_publicacion", "Hace instantes"),
                "fuente": p.get("fuente", "Redes Directo (Mi Sesión)"),
                "url": url,
                "titulo": titulo,
                "texto": texto,
                "autor": p.get("autor", "Publicación Vecinal"),
                **info,
            }
        )
        if es_nuevo:
            nuevos += 1

        for nom_propio, tipo_np in info.get("nombres_propios_tuplas", []):
            registrar_nombre_propio(
                nombre=nom_propio,
                tipo=tipo_np,
                partido=info["partido"],
                categoria_origen=info["categoria"],
                contexto=texto[:140],
                edicion_id=edicion_id,
            )

        if pasada == "pasada_abierta" or "vecinos" in texto.lower():
            for palabra_cand, cat_sug in extraer_candidatos_pasada_abierta(
                f"{titulo} {texto}"
            ):
                registrar_palabra_candidata(
                    palabra=palabra_cand,
                    categoria_sugerida=cat_sug,
                    partido_origen=info["partido"],
                    ejemplo_texto=texto,
                    edicion_id=edicion_id,
                )

    cerrar_edicion(
        edicion_id=edicion_id,
        partidos_barridos=len(partidos),
        consultas_ejecutadas=len(posteos),
        total_hallazgos=total_procesados,
        nuevos_hallazgos=nuevos,
    )
    return {
        "edicion_id": edicion_id,
        "procesados": total_procesados,
        "nuevos": nuevos,
    }
