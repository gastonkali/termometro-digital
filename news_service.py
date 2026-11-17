# -*- coding: utf-8 -*-
"""
Fuente de MEDIOS para Termómetro Digital PBA: Google Noticias (RSS público, sin clave).

Consulta los 135 partidos agrupados de a varios por búsqueda y devuelve las notas
recientes que pasan los mismos filtros que las publicaciones de redes (tema, lugar,
antigüedad y relevancia). Cada nota trae la fecha exacta y el nombre del medio, lo que
permite contar en cuántos medios distintos se replicó un hecho.
"""

import argparse
import html
import os
import re
import time
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import Any, Dict, List, Optional, Tuple

import requests

from config_pba import (
    MAX_HORAS_ANTIGUEDAD,
    PARTIDOS_NOMBRE_COMPARTIDO,
    PARTIDOS_PBA,
    es_exclusion_geografica,
    es_tema_excluido,
)

GOOGLE_NEWS_RSS = "https://news.google.com/rss/search"
# Google devuelve hasta 100 notas por consulta: con grupos chicos los partidos con mucha
# actividad (Quilmes, La Matanza) no tapan a los demas.
PARTIDOS_POR_CONSULTA = int(os.getenv("TERMOMETRO_PARTIDOS_POR_CONSULTA", "5"))
VENTANA_BUSQUEDA = os.getenv("TERMOMETRO_NOTICIAS_VENTANA", "2d")  # sintaxis when: de Google
MAX_NOTICIAS_POR_CORRIDA = int(os.getenv("TERMOMETRO_MAX_NOTICIAS", "60"))
PAUSA_ENTRE_CONSULTAS = 1.5


def _termino(partido: str) -> str:
    return f'"{partido}"' if " " in partido else partido


def armar_consultas(partidos: Optional[List[str]] = None, por_consulta: int = PARTIDOS_POR_CONSULTA) -> List[str]:
    """Agrupa los partidos en consultas "(A OR B OR ...) when:2d". Los partidos cuyo nombre
    existe en otras provincias (Junín, Maipú, Rivadavia...) se consultan exigiendo además
    "Buenos Aires", "bonaerense" o "conurbano"."""
    partidos = partidos or PARTIDOS_PBA
    unicos = [p for p in partidos if p not in PARTIDOS_NOMBRE_COMPARTIDO]
    compartidos = [p for p in partidos if p in PARTIDOS_NOMBRE_COMPARTIDO]
    consultas = []
    for i in range(0, len(unicos), por_consulta):
        grupo = unicos[i:i + por_consulta]
        consultas.append(f"({' OR '.join(_termino(p) for p in grupo)}) when:{VENTANA_BUSQUEDA}")
    for i in range(0, len(compartidos), por_consulta):
        grupo = compartidos[i:i + por_consulta]
        consultas.append(
            f"({' OR '.join(_termino(p) for p in grupo)}) (\"Buenos Aires\" OR bonaerense OR conurbano) when:{VENTANA_BUSQUEDA}"
        )
    return consultas


def _fecha_local(pub_date: str) -> Optional[datetime]:
    try:
        dt = parsedate_to_datetime(pub_date)
        return dt.astimezone().replace(tzinfo=None) if dt.tzinfo else dt
    except (TypeError, ValueError):
        return None


def _limpiar_titulo(titulo: str, medio: str) -> str:
    titulo = html.unescape(titulo or "").strip()
    if medio and titulo.endswith(f" - {medio}"):
        titulo = titulo[: -len(f" - {medio}")].strip()
    return titulo


def buscar_google_news(consulta: str, timeout: int = 20) -> List[Dict[str, Any]]:
    """Devuelve las notas crudas de una consulta (sin filtrar)."""
    url = GOOGLE_NEWS_RSS + "?" + urllib.parse.urlencode(
        {"q": consulta, "hl": "es-419", "gl": "AR", "ceid": "AR:es-419"}
    )
    resp = requests.get(url, timeout=timeout, headers={"User-Agent": "Mozilla/5.0 (TermometroDigital)"})
    resp.raise_for_status()
    root = ET.fromstring(resp.content)
    notas = []
    for item in root.findall(".//item"):
        medio = (item.findtext("source") or "").strip()
        titulo = _limpiar_titulo(item.findtext("title") or "", medio)
        desc = re.sub(r"<[^>]+>", " ", html.unescape(item.findtext("description") or ""))
        desc = " ".join(desc.split())
        notas.append({
            "titulo": titulo,
            "medio": medio or "Medio",
            "url": (item.findtext("link") or "").strip(),
            "fecha": _fecha_local(item.findtext("pubDate") or ""),
            # La descripción del RSS suele repetir el título; solo se usa si agrega algo
            "descripcion": desc if desc and titulo[:40].lower() not in desc.lower() else "",
        })
    return notas


def filtrar_nota(nota: Dict[str, Any]) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """Aplica los filtros del sistema a una nota. Devuelve (aceptada, motivo, clasificación)."""
    from engine import clasificar_hallazgo, detectar_partido_en_texto

    titulo = nota["titulo"]
    texto = f"{titulo}. {nota['descripcion']}".strip(". ") if nota.get("descripcion") else titulo

    if not nota.get("fecha"):
        return False, "sin fecha", None
    if (datetime.now() - nota["fecha"]).total_seconds() > MAX_HORAS_ANTIGUEDAD * 3600:
        return False, f"más vieja que {MAX_HORAS_ANTIGUEDAD} h", None
    excluir, motivo = es_tema_excluido(titulo, texto, nota.get("medio", ""))
    if excluir:
        return False, motivo, None
    if es_exclusion_geografica(texto):
        return False, "sin lugar de PBA en el título / otra provincia", None
    info = clasificar_hallazgo(
        titulo=f"{nota['medio']}: {titulo}", texto=texto,
        partido_objetivo=detectar_partido_en_texto(texto), pasada="medios",
    )
    if not info:
        return False, "sin término del diccionario ni señal de conflicto", None
    return True, "", info


def recolectar_noticias(
    partidos: Optional[List[str]] = None, verbose: bool = False, max_noticias: int = MAX_NOTICIAS_POR_CORRIDA
) -> List[Dict[str, Any]]:
    """Recorre todas las consultas y devuelve las notas aceptadas, listas para ingerir."""
    aceptadas: List[Dict[str, Any]] = []
    vistas = set()
    descartes: Dict[str, int] = {}
    consultas = armar_consultas(partidos)

    for i, consulta in enumerate(consultas, 1):
        try:
            notas = buscar_google_news(consulta)
        except Exception as e:
            print(f"  [Noticias] Error en consulta {i}/{len(consultas)}: {e}")
            continue
        for nota in notas:
            clave = (nota["medio"].lower(), nota["titulo"][:80].lower())
            if clave in vistas or not nota["url"]:
                continue
            vistas.add(clave)
            ok, motivo, info = filtrar_nota(nota)
            if not ok:
                descartes[motivo] = descartes.get(motivo, 0) + 1
                if verbose:
                    print(f"    ✗ {motivo}: {nota['medio']} | {nota['titulo'][:90]}")
                continue
            if verbose:
                print(f"    ✓ [{info['partido']}] {nota['medio']} | {nota['titulo'][:90]}")
            texto = f"{nota['titulo']}. {nota['descripcion']}" if nota.get("descripcion") else nota["titulo"]
            aceptadas.append({
                "fuente": "Medios (Google Noticias)",
                "autor": nota["medio"],
                "url": nota["url"],
                "titulo": f"{nota['medio']}: {nota['titulo']}",
                "texto": texto,
                "comentarios": [],
                "imagen_url": "",
                "partido": info["partido"],
                "categoria": info["categoria"],
                "pasada": "medios",
                "fecha_publicacion": nota["fecha"].isoformat(timespec="seconds"),
                "metricas": {},
            })
        if i < len(consultas):
            time.sleep(PAUSA_ENTRE_CONSULTAS)

    # Más recientes primero, con tope por corrida
    aceptadas.sort(key=lambda n: n["fecha_publicacion"], reverse=True)
    aceptadas = aceptadas[:max_noticias]
    detalle = ", ".join(f"{k}: {v}" for k, v in sorted(descartes.items(), key=lambda x: -x[1])) or "ninguno"
    print(f"  [Noticias] {len(consultas)} consultas → {len(aceptadas)} notas aceptadas. Descartadas: {detalle}")
    return aceptadas


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Probar la fuente de medios (Google Noticias) sin guardar nada")
    parser.add_argument("partidos", nargs="*", help='Partidos a consultar (ej: Berazategui "La Matanza"). Vacío = los 135.')
    args = parser.parse_args()
    recolectar_noticias(args.partidos or None, verbose=True)
