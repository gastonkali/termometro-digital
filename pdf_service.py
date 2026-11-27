# -*- coding: utf-8 -*-
"""
Generador automático de reportes PDF para Termómetro Digital PBA.
Utiliza el diseño ejecutivo exacto del modelo aprobado (2 páginas estructuradas):

Página 1:
- Header: Termómetro Digital PBA — Reporte de Alertas, corte y edición.
- Bloque Clima General (Semáforo con cuadro coloreado a la izquierda + texto analítico síntesis a la derecha).
- Barra de métricas (5 casilleros: Relevadas, Vigentes en PBA, Desactualizadas, Fuera de alcance, Convocatorias).
- Tabla "Hechos vigentes" (Clima, Partido, Hecho con eje, Reacción vecinal, Fuente con link).
- Nota aclaratoria de enlaces si aplica.
- Sección "Destacado" (Tarjeta con imagen/miniatura de 3-4 cm, metadatos, síntesis, comentarios relevantes citados).
- Sección "Agenda de convocatorias y protestas" (o leyenda si no se detectaron).

Página 2:
- Anexo — Publicaciones descartadas (Tabla: Publicación, Contenido, Motivo del descarte [desactualizada, fuera de alcance CABA, etc.], Link).
- Aclaración de obtención de fechas.
- Anexo — Figuras y palabras nuevas (Tabla: Elemento, Detalle, Estado [se mantiene / descartado / pendiente]).
- Footer institucional.
"""

import html as html_lib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from database import get_conn
from clustering_service import agrupar_en_clusters
from config_pba import (
    EXIGIR_FECHA_VERIFICADA,
    HORAS_VENTANA_REPLICAS,
    MAX_HORAS_ANTIGUEDAD,
    describir_fecha,
    es_convocatoria_futura,
    es_reclamo_reciente,
    es_tema_excluido,
    quitar_prefijo_medio,
    tiene_reclamo_explicito,
    fecha_publicacion_iso,
    limpiar_texto_basura_redes,
    texto_sin_comentarios,
    es_ruido_o_no_conflictividad,
    es_exclusion_geografica,
    es_texto_basura_ui,
    es_url_publicacion_valida,
    resolver_partido_geografico_preciso,
    resolver_eje_tematico_preciso
)

BASE_DIR = os.path.dirname(__file__)
PDF_OUTPUT_DIR = os.path.join(BASE_DIR, "reportes_pdf")
os.makedirs(PDF_OUTPUT_DIR, exist_ok=True)


def encontrar_ejecutable_navegador() -> Optional[str]:
    import glob, shutil
    for cmd in ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "brave-browser", "microsoft-edge"]:
        path = shutil.which(cmd)
        if path:
            return path

    pw_paths = glob.glob(os.path.expanduser("~/.cache/ms-playwright/chromium-*/chrome-linux64/chrome"))
    if pw_paths and os.path.exists(pw_paths[0]):
        return pw_paths[0]

    pw_headless = glob.glob(os.path.expanduser("~/.cache/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-linux64/chrome-headless-shell"))
    if pw_headless and os.path.exists(pw_headless[0]):
        return pw_headless[0]

    candidatos = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
    ]
    for ruta in candidatos:
        if os.path.exists(ruta):
            return ruta
    return None



def recortar_texto_limpio(texto: str, max_chars: int = 140) -> str:
    if not texto:
        return ""
    t = " ".join(texto.split()).strip()
    if len(t) <= max_chars:
        if t.count("“") > t.count("”"):
            t += "”"
        if t.count('"') % 2 != 0:
            t += '"'
        return t
    
    recorte = t[:max_chars].rsplit(" ", 1)[0]
    recorte = re.sub(r'[,;:\-–—\s]+$', '', recorte)
    if recorte.count("“") > recorte.count("”"):
        recorte += "”"
    if recorte.count('"') % 2 != 0:
        recorte += '"'
    if not recorte.endswith((".", "!", "?", "”", '"', "...")):
        recorte += "..."
    return recorte


def limpiar_contexto_nombre(texto: str, max_chars: int = 140) -> str:
    return recortar_texto_limpio(texto, max_chars=max_chars)


def agrupar_con_contexto(vigentes: List[Dict[str, Any]], edicion_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """Agrupa los hechos sumando como contexto las publicaciones de las últimas
    HORAS_VENTANA_REPLICAS horas que no estén ya en `vigentes`. Así tanto una edición
    horaria como el Consolidado 12 h cuentan todas las réplicas del período completo."""
    ids_vigentes = {v.get("id") for v in vigentes if v.get("id") is not None}
    corte_iso = (datetime.now() - timedelta(hours=HORAS_VENTANA_REPLICAS)).isoformat(timespec="seconds")
    conn = get_conn()
    if edicion_id:
        filas = conn.execute(
            "SELECT * FROM hallazgos WHERE (fecha_deteccion >= ? OR ultima_deteccion >= ?) "
            "AND edicion_id != ? AND COALESCE(ultima_edicion_id, 0) != ? AND descartado = 0",
            (corte_iso, corte_iso, edicion_id, edicion_id),
        ).fetchall()
    else:
        filas = conn.execute(
            "SELECT * FROM hallazgos WHERE (fecha_deteccion >= ? OR ultima_deteccion >= ?) "
            "AND descartado = 0",
            (corte_iso, corte_iso),
        ).fetchall()
    conn.close()
    filas_extra = [dict(f) for f in filas if f["id"] not in ids_vigentes]
    contexto, _ = clasificar_descartes_y_vigentes(filas_extra)
    for c in contexto:
        c["_contexto"] = True

    clusters = agrupar_en_clusters(vigentes + contexto)
    return [c for c in clusters if any(not it.get("_contexto") for it in c["hallazgos_relacionados"])]


def obtener_hechos_importantes(
    edicion_id: Optional[int] = None, horas_atras: Optional[int] = None, max_hechos: int = 3
) -> List[Dict[str, Any]]:
    """Los hechos más importantes (mismo criterio que el PDF), resumidos para Telegram."""
    conn = get_conn()
    if horas_atras:
        corte_iso = (datetime.now() - timedelta(hours=horas_atras)).isoformat(timespec="seconds")
        filas = conn.execute("SELECT * FROM hallazgos WHERE fecha_deteccion >= ? OR ultima_deteccion >= ?", (corte_iso, corte_iso)).fetchall()
    else:
        filas = conn.execute("SELECT * FROM hallazgos WHERE edicion_id = ? OR ultima_edicion_id = ?", (edicion_id, edicion_id)).fetchall()
    conn.close()
    vigentes, _ = clasificar_descartes_y_vigentes([dict(f) for f in filas])
    clusters = agrupar_con_contexto(vigentes, edicion_id if not horas_atras else None)
    salida = []
    for c in seleccionar_hechos_tabla(clusters, cantidad=max_hechos, minimo_redes=1):
        salida.append({
            "clima": c["clima_estado"],
            "partido": c["partido"],
            "titulo": c["titulo_cluster"],
            "repercusion": c["repercusion"]["nivel"],
            "motivos": resumen_repercusion(c),
            "redes": " · ".join(redes_del_hecho(c)),
            "url": c["urls"][0] if c.get("urls") else "",
            "comentario": (c.get("comentarios_cluster") or [""])[0],
            "imagen": imagen_de_hecho(c, max_descargas=1),
        })
    return salida


def es_item_de_redes(item: Dict[str, Any]) -> bool:
    """True si la publicación viene de Facebook, X o Instagram (no de un medio)."""
    fuente = (item.get("fuente") or "").lower()
    return item.get("pasada") != "medios" and not fuente.startswith("medios")


def redes_del_hecho(cluster: Dict[str, Any]) -> List[str]:
    """Etiquetas de las plataformas donde apareció el hecho: Medios, X, Instagram, Facebook."""
    etiquetas = []
    for it in cluster.get("hallazgos_relacionados") or []:
        f = (it.get("fuente") or "").lower()
        u = (it.get("url") or "").lower()
        if not es_item_de_redes(it):
            et = "Medios"
        elif "x.com" in u or "twitter" in f:
            et = "X"
        elif "instagram" in u or "instagram" in f:
            et = "Instagram"
        else:
            et = "Facebook"
        if et not in etiquetas:
            etiquetas.append(et)
    return etiquetas


def seleccionar_hechos_tabla(clusters: List[Dict[str, Any]], cantidad: int = 5, minimo_redes: int = 2) -> List[Dict[str, Any]]:
    """Los hechos más importantes, pero garantizando lugar para lo que circula en redes
    (X, Instagram, Facebook): si no, las notas replicadas en muchos medios ocupan siempre
    toda la tabla y los posteos de redes, que suelen tener una sola fuente, nunca aparecen."""
    elegidos = list(clusters[:cantidad])
    con_redes = [c for c in elegidos if any(es_item_de_redes(it) for it in c["hallazgos_relacionados"])]
    faltan = minimo_redes - len(con_redes)
    if faltan > 0:
        candidatos = [c for c in clusters[cantidad:] if any(es_item_de_redes(it) for it in c["hallazgos_relacionados"])]
        for nuevo in candidatos[:faltan]:
            # Reemplaza al hecho de solo-medios peor ubicado
            for i in range(len(elegidos) - 1, -1, -1):
                if elegidos[i] not in con_redes:
                    elegidos[i] = nuevo
                    con_redes.append(nuevo)
                    break
            else:
                break
    orden = {id(c): i for i, c in enumerate(clusters)}
    return sorted(elegidos, key=lambda c: orden[id(c)])


_RE_OG_IMAGE = [
    re.compile(r'<meta[^>]+property=["\']og:image(?::secure_url)?["\'][^>]*content=["\']([^"\']+)', re.I),
    re.compile(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]*property=["\']og:image["\']', re.I),
    re.compile(r'<meta[^>]+name=["\']twitter:image["\'][^>]*content=["\']([^"\']+)', re.I),
]


def _og_image(url: str, timeout: int = 6) -> str:
    """Imagen principal de una nota (etiqueta og:image del medio)."""
    try:
        import requests
        resp = requests.get(url, timeout=timeout, headers={"User-Agent": "Mozilla/5.0 (TermometroDigital)"})
        if resp.status_code != 200:
            return ""
        cabecera = resp.text[:300000]
        for rx in _RE_OG_IMAGE:
            m = rx.search(cabecera)
            if m and m.group(1).startswith("http"):
                return html_lib.unescape(m.group(1))
    except Exception:
        pass
    return ""


_CACHE_IMAGENES: Dict[str, str] = {}


def imagen_embebida(url: str, max_bytes: int = 1_500_000) -> str:
    """Descarga la imagen y la devuelve como data URI para meterla dentro del PDF.
    Las fotos de Instagram/Facebook son links firmados que vencen o se bloquean al abrirse
    fuera de la red (por eso salían rotas, con el texto "Foto"). Devuelve "" si no se pudo:
    en ese caso el PDF muestra un ícono en lugar de una imagen rota."""
    if not url:
        return ""
    if url.startswith("data:image/"):
        return url
    if not url.startswith("http"):
        return ""
    if url in _CACHE_IMAGENES:
        return _CACHE_IMAGENES[url]
    resultado = ""
    try:
        import base64
        import requests
        from urllib.parse import urlparse
        dominio = urlparse(url).netloc
        referer = ("https://www.instagram.com/" if ("cdninstagram" in dominio or "instagram" in dominio)
                   else "https://www.facebook.com/" if "fbcdn" in dominio else "")
        cabeceras = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125.0 Safari/537.36"}
        if referer:
            cabeceras["Referer"] = referer
        resp = requests.get(url, timeout=8, headers=cabeceras)
        tipo = (resp.headers.get("Content-Type") or "").split(";")[0].strip()
        if resp.status_code == 200 and tipo.startswith("image/") and 500 < len(resp.content) <= max_bytes:
            resultado = f"data:{tipo};base64," + base64.b64encode(resp.content).decode("ascii")
    except Exception:
        resultado = ""
    _CACHE_IMAGENES[url] = resultado
    return resultado


def imagen_de_hecho(cluster: Dict[str, Any], max_descargas: int = 2) -> str:
    """Una imagen para identificar el hecho: la de alguna publicación de redes, o la
    og:image de la nota del medio (se guarda en la base para no volver a pedirla)."""
    items = list(cluster.get("hallazgos_relacionados") or [])
    rep = cluster.get("representante")
    if rep in items:
        items.remove(rep)
        items.insert(0, rep)
    for it in items:
        img = (it.get("imagen_url") or "").strip()
        if img.startswith("http"):
            return img
    intentos = 0
    for it in items:
        url = (it.get("url") or "").strip()
        if not url.startswith("http") or "news.google.com/" in url or es_item_de_redes(it):
            continue
        if intentos >= max_descargas:
            break
        intentos += 1
        img = _og_image(url)
        if img:
            it["imagen_url"] = img
            if it.get("id"):
                try:
                    conn = get_conn()
                    conn.execute("UPDATE hallazgos SET imagen_url = ? WHERE id = ?", (img, it["id"]))
                    conn.commit()
                    conn.close()
                except Exception:
                    pass
            return img
    return ""


def resumen_repercusion(cluster: Dict[str, Any]) -> str:
    """Texto corto con los motivos de importancia: '3 fuentes distintas · 240 comentarios'."""
    rep = cluster.get("repercusion") or {}
    motivos = rep.get("motivos") or []
    if not motivos:
        return "Una sola fuente, sin repercusión registrada"
    return " · ".join(motivos)


def html_comentarios(comentarios: List[Any], max_items: int = 2, max_chars: int = 90) -> str:
    """Lista de comentarios reales ("Autor: texto") escapada para el PDF.
    Si no hay comentarios lo dice, sin inventar ninguna reacción."""
    items = [str(c).strip().replace('"', "") for c in (comentarios or []) if str(c).strip()]
    if not items:
        return "<span style='color:#94a3b8; font-style:italic;'>Sin comentarios registrados</span>"
    partes = []
    for c in items[:max_items]:
        if ":" in c:
            autor, cuerpo = c.split(":", 1)
            partes.append(
                f"<div style='margin-bottom:3px;'><strong>{html_lib.escape(autor.strip())}:</strong> "
                f"“{html_lib.escape(recortar_texto_limpio(cuerpo.strip(), max_chars))}”</div>"
            )
        else:
            partes.append(f"<div style='margin-bottom:3px;'>“{html_lib.escape(recortar_texto_limpio(c, max_chars))}”</div>")
    if len(items) > max_items:
        partes.append(f"<span style='color:#64748b; font-size:6.5pt;'>+{len(items) - max_items} comentarios más</span>")
    return "".join(partes)

def clasificar_descartes_y_vigentes(hallazgos_raw: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Separa las publicaciones entre Vigentes en PBA y Descartadas (desactualizadas, fuera de alcance CABA, autopromoción).
    """
    vigentes = []
    descartados = []

    for h in hallazgos_raw:
        comb = f"{h.get('titulo', '')} {h.get('texto', '')}"
        comb_low = comb.lower()

        # 1. Chequeo de exclusión por ruido o institucional / CABA
        es_ruido, razon_ruido = es_ruido_o_no_conflictividad(comb)
        if es_ruido:
            descartados.append({
                "publicacion": f"{h.get('autor') or h.get('fuente', 'Redes')} ({h.get('fuente', 'Web')})",
                "contenido": recortar_texto_limpio(h.get("texto", h.get("titulo", "")), 130),
                "motivo": razon_ruido,
                "url": h.get("url", "#")
            })
            continue

        # 1b. Temas que no interesan (clima, clasificados, fuentes bloqueadas)
        excluir, motivo_tema = es_tema_excluido(h.get("titulo", ""), h.get("texto", ""), h.get("autor", ""))
        if excluir:
            descartados.append({
                "publicacion": f"{h.get('autor') or h.get('fuente', 'Redes')} ({h.get('fuente', 'Web')})",
                "contenido": recortar_texto_limpio(texto_sin_comentarios(h.get("texto", h.get("titulo", ""))), 130),
                "motivo": f"Fuera de tema: {motivo_tema}.",
                "url": h.get("url", "#")
            })
            continue

        # 2. Chequeo geográfico estricto (antes que la fecha, para que un post de
        #    otro país o provincia figure como "fuera de alcance" y no como "desactualizado")
        comb_geo = f"{comb} — {h.get('autor', '')}".strip()
        if es_exclusion_geografica(comb_geo, h.get("partido", ""), url=h.get("url", "")):
            descartados.append({
                "publicacion": f"{h.get('autor') or h.get('fuente', 'Redes')}",
                "contenido": recortar_texto_limpio(h.get("texto", h.get("titulo", "")), 130),
                "motivo": "Fuera de alcance: Ocurrió en otro país, CABA u otra provincia.",
                "url": h.get("url", "#")
            })
            continue

        # 3. Fecha real de publicación (guardada por el scraper o decodificada del ID de X)
        fecha_pub = fecha_publicacion_iso(h.get("fecha_publicacion", ""), h.get("url", ""))
        h["fecha_publicacion_dt"] = fecha_pub
        vieja = False
        fecha_str = ""
        # Para convocatorias ("convocan para mañana..."), dar 12 h extra para no descartarlas el día del evento
        limite_horas = MAX_HORAS_ANTIGUEDAD + (12 if h.get("es_convocatoria") else 0)
        if fecha_pub:
            if (datetime.now() - fecha_pub).total_seconds() > limite_horas * 3600:
                vieja = True
                fecha_str = fecha_pub.strftime("%d/%m/%Y %H:%M")
        else:
            anio_actual = datetime.now().year
            m_fecha = re.search(r"\b(20[12]\d)\b", comb)
            if m_fecha and int(m_fecha.group(1)) < anio_actual - 1:
                vieja = True
                fecha_str = f"menciona {m_fecha.group(1)}"
            elif "hace 2 años" in comb_low or "hace un año" in comb_low:
                vieja = True
                fecha_str = "años anteriores"
            elif EXIGIR_FECHA_VERIFICADA:
                # Sin fecha confiable no se puede asegurar que sea del día: se descarta.
                vieja = True
                fecha_str = "sin fecha verificable"
        if vieja:
            descartados.append({
                "publicacion": f"{h.get('autor') or h.get('fuente', 'Redes')} ({h.get('fuente', 'Web')})",
                "contenido": recortar_texto_limpio(h.get("texto", h.get("titulo", "")), 130),
                "motivo": f"Desactualizada: {fecha_str}.",
                "url": h.get("url", "#")
            })
            continue

        # Asignar precisión geográfica y de eje
        h["partido"] = resolver_partido_geografico_preciso(quitar_prefijo_medio(texto_sin_comentarios(h.get("texto", "") or h.get("titulo", "")), h.get("autor", "")), h.get("partido", ""))
        h["categoria"] = resolver_eje_tematico_preciso(comb, h.get("categoria", ""))
        # Convocatoria solo si la medida es a futuro (también corrige lo ya guardado);
        # una movilización en pasado es un reclamo reciente.
        cuerpo = f"{h.get('titulo', '')} {texto_sin_comentarios(h.get('texto', ''))}"
        h["es_convocatoria"] = 1 if (h.get("es_convocatoria") and es_convocatoria_futura(cuerpo)) else 0
        h["reclamo_reciente"] = es_reclamo_reciente(cuerpo)
        h["reclamo_explicito"] = tiene_reclamo_explicito(cuerpo)
        vigentes.append(h)

    # Deduplicar descartados por URL o contenido (evita filas duplicadas en el Anexo del Consolidado)
    descartados_unicos = []
    vistos_desc = set()
    for d in descartados:
        clave_d = (d.get("url", "").strip(), d.get("contenido", "")[:60].lower())
        if clave_d not in vistos_desc:
            vistos_desc.add(clave_d)
            descartados_unicos.append(d)

    return vigentes, descartados_unicos


def generar_html_reporte(
    edicion_id: Optional[int] = None,
    horas_atras: Optional[int] = None,
    titulo_custom: Optional[str] = None
) -> str:
    conn = get_conn()
    if horas_atras:
        ahora_dt = datetime.now()
        inicio_dt = ahora_dt - timedelta(hours=horas_atras)
        corte_iso = inicio_dt.isoformat(timespec="seconds")
        hallazgos_rows = conn.execute(
            "SELECT * FROM hallazgos WHERE fecha_deteccion >= ? OR ultima_deteccion >= ? ORDER BY es_convocatoria DESC, id DESC",
            (corte_iso, corte_iso),
        ).fetchall()
        edicion_str = f"Consolidado {horas_atras} h ({inicio_dt.strftime('%d/%m %H:%M')} a {ahora_dt.strftime('%d/%m %H:%M')})"
        # Solo lo del período (antes se sumaban nombres y palabras de días anteriores)
        nombres_rows_raw = conn.execute(
            "SELECT * FROM nombres_propios WHERE creado_en >= ? ORDER BY id DESC LIMIT 10",
            (corte_iso,),
        ).fetchall()
        propuestas_rows_raw = conn.execute(
            "SELECT * FROM palabras_candidatas WHERE actualizado_en >= ? ORDER BY id DESC LIMIT 10",
            (corte_iso,),
        ).fetchall()
    else:
        hallazgos_rows = conn.execute(
            "SELECT * FROM hallazgos WHERE edicion_id = ? OR ultima_edicion_id = ? ORDER BY es_convocatoria DESC, id DESC",
            (edicion_id, edicion_id),
        ).fetchall()
        edicion_str = f"Edición #{edicion_id or 1}"
        # Solo lo visto en esta edición (antes se sumaban nombres y palabras viejos)
        nombres_rows_raw = conn.execute(
            "SELECT * FROM nombres_propios WHERE ultima_edicion_id = ? ORDER BY id DESC LIMIT 10",
            (edicion_id,),
        ).fetchall()
        propuestas_rows_raw = conn.execute(
            "SELECT * FROM palabras_candidatas WHERE ultima_edicion_id = ? ORDER BY id DESC LIMIT 10",
            (edicion_id,),
        ).fetchall()
    conn.close()
    nombres_rows = [dict(r) for r in nombres_rows_raw]
    propuestas_rows = [dict(r) for r in propuestas_rows_raw]

    raw_items = [dict(r) for r in hallazgos_rows]
    vigentes_items, descartados_items = clasificar_descartes_y_vigentes(raw_items)

    # Agrupar vigentes en clusters (en una edición se suman las publicaciones de las
    # últimas horas para detectar si la misma noticia ya se replicó en otras fuentes)
    clusters_vigentes = agrupar_con_contexto(vigentes_items, edicion_id if not horas_atras else None)

    # Conteo de métricas para la barra de 5 casilleros
    total_relevadas = len(vigentes_items) + len(descartados_items)
    total_vigentes_pba = len(vigentes_items)
    desactualizadas_cnt = sum(1 for d in descartados_items if "Desactualizada" in d["motivo"])
    fuera_alcance_cnt = len(descartados_items) - desactualizadas_cnt
    convocatorias_cnt = sum(1 for c in clusters_vigentes if c["es_convocatoria"])

    # Clima General: una nota aislada de 1 sola fuente (repercusión BAJA) no dispara
    # el clima general a EN ALERTA por sí sola.
    alertas_confirmadas = [
        c for c in clusters_vigentes
        if c["clima_estado"] == "EN ALERTA" and c["repercusion"]["nivel"] != "BAJA"
    ]
    alertas_totales = [c for c in clusters_vigentes if c["clima_estado"] == "EN ALERTA"]
    hay_alerta = len(alertas_confirmadas) >= 1 or len(alertas_totales) >= 2
    if hay_alerta:
        clima_txt = "EN ALERTA"
        clima_color = "#dc2626"
        clima_bg = "#dc2626"
    elif any(c["clima_estado"] in ("MODERADO", "EN ALERTA") for c in clusters_vigentes):
        clima_txt = "MODERADO"
        clima_color = "#d97706"
        clima_bg = "#d97706"
    else:
        clima_txt = "BUENO"
        clima_color = "#16a34a"
        clima_bg = "#16a34a"

    # Redacción analítica del Semáforo (orden por importancia, respetando mayúsculas y sin doble puntuación)
    focos_activos = [c for c in clusters_vigentes if c["clima_estado"] in ("MODERADO", "EN ALERTA")]
    foco_principal = clusters_vigentes[0] if clusters_vigentes else None
    if foco_principal and clima_txt in ("MODERADO", "EN ALERTA"):
        reaccion_limpia = foco_principal["reaccion_vecinal"].strip().rstrip(".")
        titulo_foco = foco_principal["titulo_cluster"].strip().rstrip(".")
        if len(focos_activos) > 1:
            partidos_ordenados = list(dict.fromkeys(c["partido"] for c in focos_activos))[:3]
            partidos_foco = ", ".join(partidos_ordenados)
            lead_foco = f"<strong>Focos de conflictividad vigentes en: {html_lib.escape(partidos_foco)}</strong>, principalmente por {html_lib.escape(titulo_foco)} ({html_lib.escape(reaccion_limpia.lower())})."
        else:
            lead_foco = f"<strong>Foco de conflictividad vigente: {html_lib.escape(foco_principal['partido'])}</strong>, por {html_lib.escape(titulo_foco)} ({html_lib.escape(reaccion_limpia.lower())})."
        
        if convocatorias_cnt > 0:
            conv_txt = f"Se registran {convocatorias_cnt} convocatoria{'s' if convocatorias_cnt != 1 else ''} en la Agenda."
        else:
            conv_txt = "Sin convocatorias masivas con fecha u horario en este corte."

        desc_descartes = (
            f" De las {total_relevadas} publicaciones relevadas, {len(descartados_items)} se descartaron por desactualizadas o fuera de alcance (ver Anexo)."
            if descartados_items else " Todas las publicaciones relevadas corresponden al ámbito bonaerense vigente."
        )
        texto_analisis_clima = f"{lead_foco}<br/>{conv_txt}{desc_descartes}"
    else:
        texto_analisis_clima = (
            "Sin focos de conflictividad detectados en las publicaciones relevadas en este corte."
        )

    fecha_hora = datetime.now().strftime("%d/%m/%Y %H:%M")

    # Mapeo de Ejes para la tabla
    EJE_LABELS = {
        "seguridad": "seguridad",
        "justicia": "justicia",
        "sociales_servicios": "sociales / laboral",
        "organizaciones_sociales": "organizaciones sociales",
        "visita_autoridades": "visita oficial",
        "eventos_no_autorizados": "eventos masivos",
        "imagen_institucional": "imagen institucional"
    }

    # Relevamiento exclusivo de Grupos, Red Personal y Contactos seguidos
    items_red_propia = []
    ids_vistos = set()
    for r in vigentes_items:
        p_val = (r.get("pasada") or "").lower()
        f_val = (r.get("fuente") or "").lower()
        if (
            p_val in ("grupos_vecinales", "feed_amigos", "referentes_policiales", "instagram_amigos", "instagram_cuentas", "x_seguidos")
            or "grupo:" in f_val
            or "amigos" in f_val
            or "contactos" in f_val
            or "virginia" in f_val
            or "policiales" in f_val
            or "permutas" in f_val
            or "rumores" in f_val
        ):
            if r["id"] not in ids_vistos:
                if es_url_publicacion_valida(r.get("url")) and not es_texto_basura_ui(r.get("autor", ""), r.get("texto", "")):
                    ids_vistos.add(r["id"])
                    items_red_propia.append(r)

    # Si en la edición actual hay menos de 4, completar con publicaciones válidas de grupos
    # y contactos detectadas en las últimas 24 horas (MAX_HORAS_ANTIGUEDAD), pasando los
    # mismos filtros (para no mostrar ítems descartados ni perder la fecha de X/FB).
    urls_descartadas_set = {(d.get("url") or "").strip() for d in descartados_items}
    if len(items_red_propia) < 4:
        conn = get_conn()
        corte_24h = (datetime.now() - timedelta(hours=MAX_HORAS_ANTIGUEDAD)).isoformat(timespec="seconds")
        recientes_grupos = conn.execute(
            """
            SELECT * FROM hallazgos
            WHERE (pasada IN ('grupos_vecinales', 'feed_amigos', 'referentes_policiales', 'instagram_amigos', 'instagram_cuentas', 'x_seguidos')
               OR fuente LIKE '%Grupo%'
               OR fuente LIKE '%Amigos%'
               OR fuente LIKE '%Virginia%'
               OR fuente LIKE '%Instagram%'
               OR fuente LIKE '%Twitter%')
              AND descartado = 0
              AND (fecha_deteccion >= ? OR ultima_deteccion >= ?)
              AND url NOT LIKE '%facebook.com'
              AND url NOT LIKE '%facebook.com/'
              AND (url LIKE '%/posts/%' OR url LIKE '%/permalink/%' OR url LIKE '%/status/%' OR url LIKE '%/p/%' OR url LIKE '%/reel/%' OR url LIKE '%fbid=%' OR url LIKE '%/share/%' OR url NOT LIKE '%facebook.com%')
            ORDER BY (imagen_url IS NOT NULL AND imagen_url != '') DESC, id DESC LIMIT 20
            """,
            (corte_24h, corte_24h),
        ).fetchall()
        conn.close()
        recientes_validos, _ = clasificar_descartes_y_vigentes([dict(rg) for rg in recientes_grupos])
        for rg_d in recientes_validos:
            u_rg = (rg_d.get("url") or "").strip()
            if rg_d["id"] not in ids_vistos and u_rg not in urls_descartadas_set:
                if es_url_publicacion_valida(u_rg) and not es_texto_basura_ui(rg_d.get("autor", ""), rg_d.get("texto", "")):
                    ids_vistos.add(rg_d["id"])
                    items_red_propia.append(rg_d)
                    if len(items_red_propia) >= 4:
                        break

    # Priorizar publicaciones que contengan imagen real para que el relevamiento sea visual
    items_red_propia.sort(
        key=lambda x: (
            1 if x.get("imagen_url") and str(x.get("imagen_url")).startswith("http") else 0,
            x.get("id", 0)
        ),
        reverse=True
    )

    filas_red_propia = ""
    for item in items_red_propia[:int(os.getenv("TERMOMETRO_FILAS_RED_PROPIA", "6"))]:
        f_nom = item.get("fuente", "Facebook")
        # "Facebook (Grupo: X)" → "X"; "X / Twitter (Cuentas que sigo)" → "X · Cuentas que sigo"
        m_lbl = re.match(r"^(Facebook|Instagram|X / Twitter)\s*\((.*)\)$", f_nom)
        if m_lbl:
            red = {"Facebook": "", "Instagram": "Instagram · ", "X / Twitter": "X · "}[m_lbl.group(1)]
            comunidad_lbl = red + m_lbl.group(2).replace("Grupo: ", "")
        else:
            comunidad_lbl = f_nom
        if "Permutas" in comunidad_lbl:
            comunidad_lbl = "Permutas Policía PBA"
        elif "RUMORES POLICIALES" in comunidad_lbl:
            comunidad_lbl = "Rumores Policiales PBA"
        elif "Policiales Bahia" in comunidad_lbl:
            comunidad_lbl = "Policiales Bahía Blanca"
        elif "Virginia" in comunidad_lbl:
            comunidad_lbl = "Virginia Luján Sosa"
        elif comunidad_lbl.startswith(("Amigos", "Contactos")):
            comunidad_lbl = "Feed Amigos / Contactos"

        autor_raw = (item.get("autor") or "Miembro").strip()
        txt_raw = item.get("texto") or item.get("titulo") or ""
        if autor_raw.lower() == "instagram":
            m_ig_handle = re.match(r"^\s*@?([a-zA-Z0-9_.]{3,30})\s*[•·]", txt_raw)
            if m_ig_handle:
                autor_raw = "@" + m_ig_handle.group(1)
        autor = html_lib.escape(autor_raw)
        partido = html_lib.escape(item.get("partido") or "PBA")
        
        txt_limpio = html_lib.escape(recortar_texto_limpio(limpiar_texto_basura_redes(texto_sin_comentarios(txt_raw)), 110))
        
        img_url = imagen_embebida((item.get("imagen_url") or "").strip())
        url_directa = (item.get("url") or "").strip()
        link_valido = es_url_publicacion_valida(url_directa)

        if img_url:
            if link_valido:
                thumb_item = (
                    f'<a href="{url_directa}" target="_blank" style="text-decoration:none; display:inline-block;">'
                    f'<img src="{html_lib.escape(img_url)}" alt="Foto" '
                    f'style="width: 44px; height: 44px; object-fit: cover; border-radius: 4px; border: 1px solid #cbd5e1; display: block;" />'
                    f'</a>'
                )
            else:
                thumb_item = (
                    f'<img src="{html_lib.escape(img_url)}" alt="Foto" '
                    f'style="width: 44px; height: 44px; object-fit: cover; border-radius: 4px; border: 1px solid #cbd5e1; display: block; margin: 0 auto;" />'
                )
        else:
            icono = "👮" if any(k in comunidad_lbl.lower() for k in ["polic", "rumores", "sosa", "permutas"]) else "📢"
            thumb_item = (
                f'<div style="width: 44px; height: 44px; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 4px; display: flex; align-items: center; justify-content: center; font-size: 13pt; color: #64748b; margin: 0 auto;">'
                f'{icono}'
                f'</div>'
            )

        comms_raw = item.get("comentarios") or item.get("comentarios_json") or []
        dt_item = item.get("fecha_publicacion_dt") or fecha_publicacion_iso(
            item.get("fecha_publicacion", ""), item.get("url", "")
        )
        fecha_item = describir_fecha(dt_item)
        if isinstance(comms_raw, str):
            try:
                comms_raw = json.loads(comms_raw)
            except Exception:
                comms_raw = []
        
        reaccion_txt = ""
        if comms_raw and isinstance(comms_raw, list):
            c_primero = str(comms_raw[0]).strip().replace("\xa0", " ").replace('"', '')
            if ":" in c_primero:
                c_autor, c_cuerpo = c_primero.split(":", 1)
                reaccion_txt = f"<strong>{html_lib.escape(c_autor.strip())}:</strong> “{html_lib.escape(recortar_texto_limpio(c_cuerpo.strip(), 70))}”"
            else:
                reaccion_txt = f"“{html_lib.escape(recortar_texto_limpio(c_primero, 75))}”"
            if len(comms_raw) > 1:
                reaccion_txt += f" <span style='color:#64748b; font-size:6.5pt;'>+{len(comms_raw)-1} más</span>"
        else:
            reaccion_txt = "<span style='color:#94a3b8; font-style:italic;'>Sin comentarios adicionales</span>"

        link_td = f'<a class="link-inline" href="{url_directa}" target="_blank">ver ↗</a>' if link_valido else '<span style="color:#94a3b8;">—</span>'

        filas_red_propia += f"""
        <tr>
          <td>
            <strong style="color:#1e3a8a;">{html_lib.escape(comunidad_lbl)}</strong><br/>
            <span style="font-size: 6.8pt; color: #475569;">Por: {autor}</span><br/>
            <span style="font-size: 6.5pt; color: #94a3b8;">{html_lib.escape(fecha_item)}</span>
          </td>
          <td><strong>{partido}</strong></td>
          <td style="text-align: center; vertical-align: middle;">{thumb_item}</td>
          <td style="font-size: 7.9pt; line-height: 1.25;">{txt_limpio}</td>
          <td>{html_comentarios(comms_raw if isinstance(comms_raw, list) else [], max_items=2, max_chars=70)}</td>
          <td style="text-align: center;">{link_td}</td>
        </tr>
        """

    if not filas_red_propia:
        filas_red_propia = """
        <tr>
          <td colspan="6" style="text-align: center; color: #64748b; font-style: italic; padding: 8px;">
            Sin publicaciones recientes detectadas en grupos o contactos durante este corte.
          </td>
        </tr>
        """

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8" />
  <title>Termómetro Digital PBA — Reporte de Alertas</title>
  <style>
    @page {{
      size: A4;
      margin: 10mm 12mm;
    }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      color: #1e293b;
      margin: 0;
      padding: 0;
      font-size: 8.8pt;
      line-height: 1.38;
      background: #ffffff;
    }}
    .page {{
      page-break-after: always;
    }}
    .page:last-child {{
      page-break-after: avoid;
    }}
    /* ENCABEZADO */
    .top-header {{
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 12px;
    }}
    .main-title {{
      font-size: 16pt;
      font-weight: 800;
      color: #0f172a;
      letter-spacing: -0.4px;
      margin: 0;
    }}
    .main-subtitle {{
      font-size: 8pt;
      color: #64748b;
      margin-top: 3px;
    }}
    .top-meta {{
      text-align: right;
      font-size: 8pt;
      color: #0f172a;
    }}
    .top-meta strong {{
      font-weight: 700;
    }}
    .top-meta .corte-date {{
      color: #64748b;
      margin-top: 2px;
    }}

    /* CAJA CLIMA GENERAL */
    .clima-banner {{
      display: flex;
      background: #f8fafc;
      border: 1px solid #e2e8f0;
      border-radius: 6px;
      margin-bottom: 8px;
      overflow: hidden;
    }}
    .clima-box-color {{
      width: 140px;
      min-width: 140px;
      background: {clima_bg};
      color: #ffffff;
      padding: 12px 8px;
      display: flex;
      flex-direction: column;
      justify-content: center;
      align-items: center;
      text-align: center;
    }}
    .clima-tag-label {{
      font-size: 7pt;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.6px;
      opacity: 0.9;
    }}
    .clima-tag-state {{
      font-size: 13pt;
      font-weight: 900;
      letter-spacing: -0.2px;
      margin-top: 2px;
    }}
    .clima-content {{
      padding: 10px 14px;
      font-size: 8.4pt;
      color: #334155;
      line-height: 1.45;
      display: flex;
      align-items: center;
    }}

    /* METRICAS 5 CASILLEROS */
    .metricas-bar {{
      display: flex;
      gap: 8px;
      margin-bottom: 14px;
    }}
    .met-card {{
      flex: 1;
      background: #ffffff;
      border: 1px solid #e2e8f0;
      border-radius: 5px;
      padding: 6px 4px;
      text-align: center;
    }}
    .met-num {{
      font-size: 15pt;
      font-weight: 800;
      color: #0f172a;
      line-height: 1.1;
    }}
    .met-lbl {{
      font-size: 6.8pt;
      font-weight: 700;
      color: #64748b;
      text-transform: uppercase;
      letter-spacing: 0.4px;
      margin-top: 2px;
    }}

    /* SECCION Y TABLA HECHOS VIGENTES */
    .section-title {{
      font-size: 9.5pt;
      font-weight: 800;
      color: #0f172a;
      margin-top: 10px;
      margin-bottom: 6px;
    }}
    table.data-table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 8pt;
      margin-bottom: 6px;
    }}
    table.data-table th {{
      background: #0f172a;
      color: #ffffff;
      font-weight: 700;
      text-align: left;
      padding: 5px 8px;
      font-size: 7.5pt;
    }}
    table.data-table td {{
      padding: 4px 6px;
      border-bottom: 1px solid #e2e8f0;
      vertical-align: top;
      color: #334155;
    }}
    table.data-table tr:nth-child(even) td {{
      background: #f8fafc;
    }}
    .pill-clima {{
      display: inline-block;
      font-size: 6.8pt;
      font-weight: 800;
      color: #ffffff;
      padding: 2px 6px;
      border-radius: 3px;
      text-transform: uppercase;
    }}
    .pill-clima-moderado {{ background: #d97706; }}
    .pill-clima-bueno {{ background: #16a34a; }}
    .pill-clima-alerta {{ background: #dc2626; }}
    .sub-eje {{
      font-size: 7.2pt;
      color: #64748b;
      margin-top: 3px;
    }}
    .link-inline {{
      color: #2563eb;
      text-decoration: none;
      font-weight: 600;
    }}
    .clarification-note {{
      font-size: 7.3pt;
      color: #64748b;
      font-style: italic;
      margin-bottom: 8px;
    }}

    /* DESTACADO */
    .destacado-card {{
      border: 1px solid #e2e8f0;
      border-left: 4px solid #d97706;
      border-radius: 6px;
      padding: 6px 10px;
      margin-bottom: 8px;
      background: #ffffff;
    }}
    .destacado-flex {{
      display: flex;
      gap: 12px;
      align-items: flex-start;
    }}
    .destacado-thumb {{
      width: 105px;
      height: 70px;
      border-radius: 4px;
      object-fit: cover;
      border: 1px solid #e2e8f0;
      flex-shrink: 0;
      background: #f1f5f9;
    }}
    .destacado-body {{
      flex: 1;
    }}
    .destacado-header {{
      font-size: 9.2pt;
      font-weight: 800;
      color: #0f172a;
      margin-bottom: 3px;
    }}
    .destacado-meta {{
      font-size: 7.2pt;
      color: #64748b;
      margin-bottom: 4px;
    }}
    .destacado-desc {{
      font-size: 8.2pt;
      color: #1e293b;
      margin-bottom: 5px;
    }}
    .destacado-comentarios {{
      font-size: 7.8pt;
      color: #334155;
    }}
    .destacado-comentarios strong {{
      color: #0f172a;
    }}
    .destacado-comentarios ul {{
      margin: 2px 0 0 0;
      padding-left: 14px;
    }}
    .destacado-comentarios li {{
      margin-bottom: 2px;
    }}

    /* AGENDA */
    .agenda-empty {{
      font-size: 8pt;
      color: #64748b;
      margin: 4px 0 10px 0;
    }}

    /* ANEXOS (PÁGINA 2) */
    .anexo-table th {{
      background: #0f172a;
      color: #ffffff;
      padding: 5px 8px;
      font-size: 7.5pt;
    }}
    .anexo-table td {{
      padding: 5px 8px;
      font-size: 7.8pt;
      border-bottom: 1px solid #e2e8f0;
      vertical-align: top;
    }}
    .anexo-table tr:nth-child(even) td {{
      background: #f8fafc;
    }}
    .motivo-descarte {{
      color: #b91c1c;
      font-weight: 500;
    }}
    .estado-col {{
      font-weight: 600;
      font-size: 7.5pt;
    }}
    .estado-descartado {{ color: #b91c1c; }}
    .estado-mantenido {{ color: #15803d; }}
    .estado-pendiente {{ color: #b45309; }}

    .doc-footer {{
      margin-top: 16px;
      border-top: 1px solid #e2e8f0;
      padding-top: 6px;
      font-size: 7pt;
      color: #94a3b8;
      text-align: center;
    }}
  </style>
</head>
<body>

  <!-- PÁGINA 1 -->
  <div class="page">
    <div class="top-header">
      <div>
        <div class="main-title">Termómetro Digital PBA — Reporte de Alertas</div>
        <div class="main-subtitle">Monitoreo de redes sociales (Facebook, X, Instagram, Google) · 135 partidos de la Provincia de Buenos Aires</div>
      </div>
      <div class="top-meta">
        <div><strong>{edicion_str}</strong></div>
        <div class="corte-date">Corte: {fecha_hora}</div>
      </div>
    </div>

    <!-- BANNER CLIMA GENERAL -->
    <div class="clima-banner">
      <div class="clima-box-color">
        <div class="clima-tag-label">CLIMA GENERAL</div>
        <div class="clima-tag-state">{clima_txt}</div>
      </div>
      <div class="clima-content">
        <div>{texto_analisis_clima}</div>
      </div>
    </div>

    <!-- BARRA 5 CASILLEROS -->
    <div class="metricas-bar">
      <div class="met-card">
        <div class="met-num">{total_relevadas}</div>
        <div class="met-lbl">RELEVADAS</div>
      </div>
      <div class="met-card">
        <div class="met-num">{total_vigentes_pba}</div>
        <div class="met-lbl">VIGENTES EN PBA</div>
      </div>
      <div class="met-card">
        <div class="met-num">{desactualizadas_cnt}</div>
        <div class="met-lbl">DESACTUALIZADAS</div>
      </div>
      <div class="met-card">
        <div class="met-num">{fuera_alcance_cnt}</div>
        <div class="met-lbl">FUERA DE ALCANCE</div>
      </div>
      <div class="met-card">
        <div class="met-num">{convocatorias_cnt}</div>
        <div class="met-lbl">CONVOCATORIAS</div>
      </div>
    </div>

    <!-- TABLA HECHOS VIGENTES -->
    <div class="section-title">Hechos vigentes y alertas públicas PBA</div>
    <table class="data-table">
      <thead>
        <tr>
          <th style="width: 10%;">Clima</th>
          <th style="width: 12%;">Partido</th>
          <th style="width: 9%;">Imagen</th>
          <th style="width: 35%;">Hecho</th>
          <th style="width: 20%;">Reacción vecinal</th>
          <th style="width: 14%;">Fuente</th>
        </tr>
      </thead>
      <tbody>
"""

    if not clusters_vigentes:
        # Fila de respaldo si no hay hechos vigentes
        html += """
        <tr>
          <td><span class="pill-clima pill-clima-bueno">BUENO</span></td>
          <td>Provincia de Buenos Aires</td>
          <td>—</td>
          <td>Sin hechos vigentes detectados en las publicaciones relevadas.</td>
          <td>—</td>
          <td>—</td>
        </tr>
        """
    else:
        cantidad_filas = 6 if horas_atras else 4
        for c in seleccionar_hechos_tabla(clusters_vigentes, cantidad=cantidad_filas):
            img_hecho = imagen_embebida(imagen_de_hecho(c))
            if img_hecho:
                thumb_hecho = (
                    f'<img src="{html_lib.escape(img_hecho)}" alt="" '
                    f'style="width:58px; height:44px; object-fit:cover; border-radius:4px; border:1px solid #cbd5e1; display:block;" />'
                )
            else:
                thumb_hecho = (
                    '<div style="width:58px; height:44px; background:#f1f5f9; border:1px solid #e2e8f0; border-radius:4px; '
                    'display:flex; align-items:center; justify-content:center; font-size:13pt;">📰</div>'
                )
            redes_txt = " · ".join(redes_del_hecho(c))
            pill_class = (
                "pill-clima-alerta" if c["clima_estado"] == "EN ALERTA"
                else ("pill-clima-moderado" if c["clima_estado"] == "MODERADO" else "pill-clima-bueno")
            )
            eje_str = EJE_LABELS.get(c["categoria"], c["categoria"])
            primera_fuente = c.get("fuentes_nombres", ["Fuente"])[0] if c.get("fuentes_nombres") else "Redes"
            primera_url = c["urls"][0] if c.get("urls") else ""
            otras = len(c.get("fuentes_nombres") or []) - 1
            otras_txt = f'<div class="sub-eje">y {otras} fuente{"s" if otras > 1 else ""} más</div>' if otras > 0 else ""
            if primera_url and es_url_publicacion_valida(primera_url):
                fuente_td = f'{html_lib.escape(primera_fuente)} · <a class="link-inline" href="{primera_url}" target="_blank">ver ↗</a>{otras_txt}'
            else:
                fuente_td = f'{html_lib.escape(primera_fuente)}{otras_txt}'

            reaccion_html = html_comentarios(c.get("comentarios_cluster") or [], max_items=2, max_chars=80)
            fecha_hecho = describir_fecha(c.get("fecha_publicacion_dt") or c["representante"].get("fecha_publicacion_dt"))
            html += f"""
        <tr>
          <td><span class="pill-clima {pill_class}">{c['clima_estado']}</span></td>
          <td><strong>{html_lib.escape(c['partido'])}</strong></td>
          <td style="vertical-align: top;">{thumb_hecho}</td>
          <td>
            {html_lib.escape(c['titulo_cluster'])}
            <div class="sub-eje">Visto en: {html_lib.escape(redes_txt)}</div>
            <div class="sub-eje">Eje: {eje_str} · {html_lib.escape(fecha_hecho)}</div>
            <div class="sub-eje"><strong>Repercusión {html_lib.escape(c['repercusion']['nivel'])}:</strong> {html_lib.escape(resumen_repercusion(c))}</div>
          </td>
          <td>{reaccion_html}</td>
          <td>{fuente_td}</td>
        </tr>
            """

    html += f"""
      </tbody>
    </table>
    <div class="clarification-note">Fechas: tomadas de la propia publicación (Facebook / Instagram), del ID de X o de la fecha del medio. Se descartan publicaciones de más de {MAX_HORAS_ANTIGUEDAD} h{" y las que no muestran fecha legible" if EXIGIR_FECHA_VERIFICADA else ' ("Fecha no verificada" = la red no la mostró legible)'}.<br/>Orden por importancia: gravedad del hecho y repercusión (cuántas fuentes distintas lo publicaron en las últimas {HORAS_VENTANA_REPLICAS} h, comentarios y compartidos). Una repercusión MEDIA lleva un hecho a MODERADO como mínimo; una ALTA lo sube un nivel.</div>

    <!-- DESTACADO -->
    <div class="section-title">Destacado</div>
"""

    # Bloque de tarjeta destacada
    destacado_item = clusters_vigentes[0] if clusters_vigentes else None
    if destacado_item:
        rep = destacado_item["representante"]
        url_destacada = destacado_item["urls"][0] if destacado_item["urls"] else "#"
        fuente_destacada = (
            destacado_item.get("fuentes_nombres", [rep.get("autor") or "Vecinos"])[0]
            if destacado_item.get("fuentes_nombres")
            else (rep.get("autor") or "Vecinos")
        )
        plataforma_dest = rep.get("fuente", "Redes Sociales")
        fecha_pub_dest = describir_fecha(destacado_item.get("fecha_publicacion_dt") or rep.get("fecha_publicacion_dt"))
        clima_dest = destacado_item["clima_estado"]
        pill_dest_class = (
            "pill-clima-alerta" if clima_dest == "EN ALERTA"
            else ("pill-clima-moderado" if clima_dest == "MODERADO" else "pill-clima-bueno")
        )

        img_dest = imagen_embebida(imagen_de_hecho(destacado_item))
        if img_dest:
            thumb_html = f'<img class="destacado-thumb" src="{html_lib.escape(img_dest)}" alt="Foto Hecho" />'
        else:
            thumb_html = (
                f'<div class="destacado-thumb" style="display:flex;flex-direction:column;align-items:center;justify-content:center;background:#f1f5f9;color:#334155;font-weight:700;font-size:7.5pt;text-align:center;padding:4px;border:1px solid #cbd5e1;">'
                f'<span style="font-size:12pt;margin-bottom:2px;">📍</span>'
                f'{html_lib.escape(destacado_item["partido"])}'
                f'</div>'
            )

        desc_cruda = limpiar_texto_basura_redes(texto_sin_comentarios(rep.get("texto") or "")) or rep.get("titulo") or destacado_item["titulo_cluster"]
        desc_limpia = recortar_texto_limpio(desc_cruda, max_chars=260)
        # Evitar repetir el titular palabra por palabra en el cuerpo del Destacado
        tit_norm_d = re.sub(r"\W+", "", destacado_item["titulo_cluster"].lower())
        desc_norm_d = re.sub(r"\W+", "", desc_limpia.lower())
        es_duplicado_titulo = bool(tit_norm_d) and (desc_norm_d == tit_norm_d or desc_norm_d.startswith(tit_norm_d) and len(desc_norm_d) <= len(tit_norm_d) + 8)
        desc_html_destacado = "" if es_duplicado_titulo else f'<div class="destacado-desc">{html_lib.escape(desc_limpia)}</div>'

        # Comentarios de todas las publicaciones del mismo hecho, no solo de una
        comentarios_raw = destacado_item.get("comentarios_cluster") or rep.get("comentarios") or rep.get("comentarios_json") or []
        if isinstance(comentarios_raw, str):
            try:
                comentarios_raw = json.loads(comentarios_raw)
            except Exception:
                comentarios_raw = []

        if comentarios_raw and isinstance(comentarios_raw, list):
            comms_items_html = ""
            for comm in comentarios_raw[:2]:
                comm_str = str(comm).strip()
                if " - · - " in comm_str:
                    c_parts = comm_str.split(" - · - ")
                    c_autor = c_parts[0].strip()
                    c_txt = c_parts[-1].strip()
                    comms_items_html += f"<li><strong>{html_lib.escape(c_autor)}:</strong> “{html_lib.escape(recortar_texto_limpio(c_txt, 110))}”</li>"
                elif ":" in comm_str:
                    c_parts = comm_str.split(":", 1)
                    c_autor = c_parts[0].strip()
                    c_txt = c_parts[1].strip()
                    comms_items_html += f"<li><strong>{html_lib.escape(c_autor)}:</strong> “{html_lib.escape(recortar_texto_limpio(c_txt, 110))}”</li>"
                else:
                    comms_items_html += f"<li>“{html_lib.escape(recortar_texto_limpio(comm_str, 120))}”</li>"
            bloque_comentarios = f"""
            <div class="destacado-comentarios">
              <strong>Comentarios relevantes:</strong>
              <ul>
                {comms_items_html}
              </ul>
            </div>
            """
        else:
            bloque_comentarios = """
            <div class="destacado-comentarios" style="color:#64748b; font-style:italic; margin-top:4px;">
              Sin comentarios adicionales registrados en la publicación original.
            </div>
            """

        html += f"""
    <div class="destacado-card">
      <div class="destacado-flex">
        {thumb_html}
        <div class="destacado-body">
          <div class="destacado-header">{html_lib.escape(destacado_item['partido'])} — {html_lib.escape(destacado_item['titulo_cluster'])}</div>
          <div class="destacado-meta">
            <span class="pill-clima {pill_dest_class}" style="font-size: 6.5pt; padding: 1px 4px;">{clima_dest}</span>
            {html_lib.escape(fuente_destacada)} · {html_lib.escape(plataforma_dest)} · {html_lib.escape(fecha_pub_dest)} · <a class="link-inline" href="{url_destacada}">Abrir publicación original ↗</a>
            <br/><strong>Repercusión {html_lib.escape(destacado_item['repercusion']['nivel'])}:</strong> {html_lib.escape(resumen_repercusion(destacado_item))}
          </div>
          {desc_html_destacado}
          {bloque_comentarios}
        </div>
      </div>
    </div>
        """
    else:
        html += """
    <div class="destacado-card">
      <div class="destacado-desc" style="color: #64748b; font-style: italic;">
        Sin hechos destacados en las publicaciones relevadas en este corte.
      </div>
    </div>
        """

    convocatorias_items = [c for c in clusters_vigentes if c["es_convocatoria"]]
    if convocatorias_items:
        agenda_html = """<table class="data-table" style="margin-bottom:8px;">
      <thead>
        <tr>
          <th style="width: 18%;">Partido</th>
          <th style="width: 48%;">Convocatoria / Reclamo</th>
          <th style="width: 20%;">Reacción vecinal</th>
          <th style="width: 14%;">Fuente</th>
        </tr>
      </thead>
      <tbody>"""
        for cv in convocatorias_items[:3]:
            cv_fuente = cv.get("fuentes_nombres", ["Vecinos"])[0] if cv.get("fuentes_nombres") else "Vecinos"
            cv_url = cv["urls"][0] if cv["urls"] else "#"
            agenda_html += f"""
        <tr>
          <td><strong>{html_lib.escape(cv['partido'])}</strong></td>
          <td>{html_lib.escape(cv['titulo_cluster'])}</td>
          <td>{html_lib.escape(cv['reaccion_vecinal'])}</td>
          <td>{html_lib.escape(cv_fuente)} · <a class="link-inline" href="{cv_url}">ver ↗</a></td>
        </tr>"""
        agenda_html += """
      </tbody>
    </table>"""
    else:
        agenda_html = '<div class="agenda-empty">No se detectaron convocatorias con fecha u horario en este corte.</div>'

    html += f"""
  </div>

  <!-- PÁGINA 2: GRUPOS, CONTACTOS Y AGENDA -->
  <div class="page">
    <!-- SECCIÓN RELEVAMIENTO DE GRUPOS Y CONTACTOS PROPIOS -->
    <div class="section-title" style="margin-top: 0; font-size: 11pt;">Relevamiento exclusivo — Grupos y contactos que sigo</div>
    <table class="data-table">
      <thead>
        <tr>
          <th style="width: 20%;">Comunidad / Contacto</th>
          <th style="width: 13%;">Partido</th>
          <th style="width: 10%; text-align: center;">Imagen</th>
          <th style="width: 27%;">Publicación y reclamo</th>
          <th style="width: 22%;">Comentarios de miembros</th>
          <th style="width: 8%; text-align: center;">Link</th>
        </tr>
      </thead>
      <tbody>
        {filas_red_propia}
      </tbody>
    </table>

    <!-- AGENDA DE CONVOCATORIAS -->
    <div class="section-title" style="margin-top: 8px; font-size: 11pt;">Agenda de convocatorias y protestas</div>
    {agenda_html}

    <div class="section-title" style="margin-top: 10px; font-size: 11pt;">Anexo — Publicaciones descartadas</div>
    <table class="data-table anexo-table">
      <thead>
        <tr>
          <th style="width: 20%;">Publicación</th>
          <th style="width: 42%;">Contenido</th>
          <th style="width: 32%;">Motivo del descarte</th>
          <th style="width: 6%; text-align: center;">Link</th>
        </tr>
      </thead>
      <tbody>
"""

    if descartados_items:
        for d in descartados_items[:8]:
            d_pub = html_lib.escape(d.get("publicacion", "Fuente"))
            d_cont = html_lib.escape(recortar_texto_limpio(d.get("contenido", ""), 120))
            d_mot = html_lib.escape(d.get("motivo", "Descarte"))
            d_url = d.get("url", "#")
            html += f"""
        <tr>
          <td><strong>{d_pub}</strong></td>
          <td>{d_cont}</td>
          <td class="motivo-descarte">{d_mot}</td>
          <td style="text-align: center;"><a class="link-inline" href="{d_url}">↗</a></td>
        </tr>
            """
        if len(descartados_items) > 8:
            restantes_desc = len(descartados_items) - 8
            html += f"""
        <tr>
          <td colspan="4" style="text-align: center; color: #64748b; font-style: italic; font-size: 7.4pt; padding: 4px;">
            … y {restantes_desc} publicación{"es" if restantes_desc != 1 else ""} descartada{"s" if restantes_desc != 1 else ""} más (total: {len(descartados_items)}).
          </td>
        </tr>
            """
    else:
        html += """
        <tr>
          <td colspan="4" style="text-align: center; color: #64748b; font-style: italic; padding: 10px;">
            No se registraron publicaciones fuera de alcance o desactualizadas en este corte.
          </td>
        </tr>
        """

    html += f"""
      </tbody>
    </table>
    <div class="clarification-note">Las fechas de las publicaciones de X se obtienen del identificador de cada publicación.</div>

    <div class="section-title" style="margin-top: 14px; font-size: 11pt;">Anexo — Figuras públicas / personas mencionadas por los vecinos y palabras nuevas</div>
    <table class="data-table anexo-table">
      <thead>
        <tr>
          <th style="width: 22%;">Elemento</th>
          <th style="width: 44%;">Detalle y contexto citado</th>
          <th style="width: 24%;">Estado</th>
          <th style="width: 10%; text-align: center;">Link</th>
        </tr>
      </thead>
      <tbody>
"""

    filas_anexo_figuras = 0

    # Excluir solo publicaciones descartadas; las figuras mencionadas en hechos vigentes
    # del reporte SÍ deben listarse aquí, sin duplicar el mismo nombre.
    urls_excluidas_anexo = {(d.get("url") or "").strip() for d in descartados_items}
    urls_excluidas_anexo.discard("")
    urls_excluidas_anexo.discard("#")
    nombres_en_anexo = set()

    def _repetida_en_anexo(url_fila: str, nombre_fila: str = "") -> bool:
        u = (url_fila or "").strip()
        if u and u in urls_excluidas_anexo:
            return True
        clave_n = (nombre_fila or u).strip().lower()
        if clave_n in nombres_en_anexo:
            return True
        nombres_en_anexo.add(clave_n)
        return False

    for nr in nombres_rows:
        if filas_anexo_figuras >= 4:
            break
        n_nombre = nr["nombre"]
        n_ctx = limpiar_contexto_nombre(nr.get("contexto", ""), 100)
        if es_texto_basura_ui(n_nombre, n_ctx):
            continue
        if _repetida_en_anexo(nr.get("fuente_url"), n_nombre):
            continue

        n_tipo = nr.get("tipo", "Figura / Persona")
        n_partido = nr.get("partido", "Provincia de Buenos Aires")
        n_apariciones = nr.get("apariciones", 1)
        menciones_str = f"{n_apariciones} mención" if n_apariciones == 1 else f"{n_apariciones} menciones"
        estado_badge = (
            '<span class="estado-col estado-mantenido">Mencionado por vecinos</span>'
            if nr.get("vigente", 1)
            else '<span class="estado-col estado-descartado">Descartado</span>'
        )
        n_url = (nr.get("fuente_url") or "").strip()
        link_col = f'<a class="link-inline" href="{n_url}" target="_blank">ver ↗</a>' if es_url_publicacion_valida(n_url) else '<span style="color:#94a3b8;">—</span>'

        html += f"""
        <tr>
          <td><strong>“{html_lib.escape(n_nombre)}”</strong><br/><span style="font-size: 6.8pt; color: #64748b;">({html_lib.escape(n_tipo)})</span></td>
          <td><strong>{html_lib.escape(n_partido)}:</strong> {html_lib.escape(n_ctx)} ({menciones_str})</td>
          <td class="estado-col">{estado_badge}</td>
          <td style="text-align: center;">{link_col}</td>
        </tr>
        """
        filas_anexo_figuras += 1

    for pr in propuestas_rows:
        if filas_anexo_figuras >= 7:
            break
        p_palabra = pr["palabra"]
        p_ej = limpiar_contexto_nombre(pr.get("ejemplo_texto", ""), 95)
        if es_texto_basura_ui(p_palabra, p_ej):
            continue
        if _repetida_en_anexo(pr.get("fuente_url")):
            continue

        p_cat = pr.get("categoria_sugerida", "general")
        p_partido = pr.get("partido_origen", "PBA")
        p_estado = pr.get("estado", "observando")
        estado_badge = (
            '<span class="estado-col estado-pendiente">En observación</span>'
            if p_estado == "observando"
            else f'<span class="estado-col estado-descartado">{html_lib.escape(p_estado)}</span>'
        )
        p_url = (pr.get("fuente_url") or "").strip()
        link_col = f'<a class="link-inline" href="{p_url}" target="_blank">ver ↗</a>' if es_url_publicacion_valida(p_url) else '<span style="color:#94a3b8;">—</span>'

        html += f"""
        <tr>
          <td><strong>{html_lib.escape(p_palabra)}</strong><br/><span style="font-size: 6.8pt; color: #64748b;">Eje: {html_lib.escape(p_cat)}</span></td>
          <td><strong>{html_lib.escape(p_partido)}:</strong> {html_lib.escape(p_ej)}</td>
          <td class="estado-col">{estado_badge}</td>
          <td style="text-align: center;">{link_col}</td>
        </tr>
        """
        filas_anexo_figuras += 1

    if filas_anexo_figuras == 0:
        html += """
        <tr>
          <td colspan="4" style="text-align: center; color: #64748b; font-style: italic; padding: 10px;">
            Sin figuras públicas ni términos atípicos nuevos detectados en este corte.
          </td>
        </tr>
        """

    html += f"""
      </tbody>
    </table>
    <div class="doc-footer">
      Reporte generado por Termómetro Digital · Cobertura: 135 municipios bonaerenses · Excluye CABA y otras provincias · Versión modelo de Alertas
    </div>
  </div>

</body>
</html>
"""
    return html


def compilar_pdf_desde_html(html_content: str, ruta_salida_pdf: str) -> bool:
    nav_exe = encontrar_ejecutable_navegador()
    if not nav_exe:
        print("[PDF] Error: No se encontró navegador basado en Chromium.")
        return False

    temp_html = os.path.join(PDF_OUTPUT_DIR, "temp_reporte.html")
    with open(temp_html, "w", encoding="utf-8") as f:
        f.write(html_content)

    cmd = [
        nav_exe,
        "--headless=new",
        "--disable-gpu",
        "--no-pdf-header-footer",
        # Da tiempo a que carguen las imágenes remotas de las publicaciones
        "--virtual-time-budget=8000",
        f"--print-to-pdf={ruta_salida_pdf}",
        temp_html,
    ]

    try:
        if os.path.exists(ruta_salida_pdf):
            os.remove(ruta_salida_pdf)
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        # En Windows, msedge.exe/chrome.exe vuelve enseguida y el PDF se escribe unos
        # segundos después: se espera hasta que exista y su tamaño deje de cambiar.
        import time
        tam_anterior, limite = -1, time.time() + 45
        while time.time() < limite:
            tam = os.path.getsize(ruta_salida_pdf) if os.path.exists(ruta_salida_pdf) else -1
            if tam > 1000 and tam == tam_anterior:
                return True
            tam_anterior = tam
            time.sleep(1)
        print(f"[PDF] Error: {res.stderr}")
        return False
    except Exception as e:
        print(f"[PDF] Excepción: {e}")
        return False


def formato_pdf() -> str:
    """'fichas' (9:16, mismo diseño que el skill de barrido) o 'a4' (tablas)."""
    return "a4" if os.getenv("TERMOMETRO_FORMATO_PDF", "fichas").strip().lower() == "a4" else "fichas"


def generar_html_segun_formato(edicion_id: Optional[int] = None, horas_atras: Optional[int] = None) -> str:
    if formato_pdf() == "a4":
        return generar_html_reporte(edicion_id=edicion_id, horas_atras=horas_atras)
    from pdf_fichas import generar_html_fichas
    return generar_html_fichas(edicion_id=edicion_id, horas_atras=horas_atras)


def crear_reporte_pdf_edicion(edicion_id: int) -> Optional[str]:
    html = generar_html_segun_formato(edicion_id=edicion_id)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    pdf_path = os.path.join(PDF_OUTPUT_DIR, f"Alerta_Termometro_PBA_Edicion_{edicion_id}_{timestamp}.pdf")
    pdf_path_latest = os.path.join(PDF_OUTPUT_DIR, "Alerta_Termometro_PBA_Ultima.pdf")

    if compilar_pdf_desde_html(html, pdf_path):
        try:
            import shutil
            shutil.copyfile(pdf_path, pdf_path_latest)
        except Exception:
            pass
        return pdf_path
    return None


def crear_reporte_pdf_ultimas_horas(horas_atras: int = 12) -> Optional[str]:
    html = generar_html_segun_formato(horas_atras=horas_atras)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    pdf_path = os.path.join(PDF_OUTPUT_DIR, f"Reporte_Matutino_PBA_{horas_atras}h_{timestamp}.pdf")
    pdf_path_latest = os.path.join(PDF_OUTPUT_DIR, "Alerta_Termometro_PBA_Ultima.pdf")

    if compilar_pdf_desde_html(html, pdf_path):
        try:
            import shutil
            shutil.copyfile(pdf_path, pdf_path_latest)
        except Exception:
            pass
        return pdf_path
    return None


if __name__ == "__main__":
    conn = get_conn()
    ult = conn.execute("SELECT MAX(id) AS m FROM ediciones").fetchone()["m"] or 1
    conn.close()
    pdf = crear_reporte_pdf_edicion(ult)
    print(f"PDF generado: {pdf}")
