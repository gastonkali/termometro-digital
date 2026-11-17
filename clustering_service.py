# -*- coding: utf-8 -*-
"""
Módulo de Desduplicación Semántica, Agrupación de Incidentes y Síntesis para Termómetro Digital PBA.
Permite consolidar múltiples fuentes sobre el mismo hecho (ej: Sarandí, Quilmes y Bernal por
el corte de Autopista Bs. As.–La Plata por falta de luz) en 1 sola tarjeta con conteo de fuentes.
"""

import json
import re
from typing import Any, Dict, List, Tuple
from collections import Counter
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from config_pba import (
    PUNTOS_COMENTARIOS,
    PUNTOS_COMPARTIDOS,
    PUNTOS_FUENTES_DISTINTAS,
    REPERCUSION_ALTA,
    REPERCUSION_MEDIA,
    STOPWORDS_ES,
    quitar_tildes,
    resolver_eje_tematico_preciso,
    resolver_partido_geografico_preciso,
    texto_sin_comentarios,
)

NIVELES_CLIMA = ["BUENO", "MODERADO", "EN ALERTA"]


def _puntos_escalon(valor: int, escalones) -> int:
    puntos = 0
    for minimo, pts in escalones:
        if valor >= minimo:
            puntos = pts
    return puntos


def _entero(v: Any) -> int:
    try:
        return int(v or 0)
    except (TypeError, ValueError):
        return 0


def calcular_repercusion(items: List[Dict[str, Any]], fuentes: List[str]) -> Dict[str, Any]:
    """Repercusión de un hecho: en cuántas fuentes distintas se replicó y cuánta
    conversación generó (comentarios, compartidos). Devuelve puntaje, nivel y motivos."""
    comentarios = 0
    compartidos = 0
    reacciones = 0
    for it in items:
        leidos = it.get("comentarios") or it.get("comentarios_json") or []
        if isinstance(leidos, str):
            try:
                leidos = json.loads(leidos)
            except Exception:
                leidos = []
        comentarios += max(_entero(it.get("num_comentarios")), len(leidos) if isinstance(leidos, list) else 0)
        compartidos += _entero(it.get("num_compartidos"))
        reacciones += _entero(it.get("num_reacciones"))

    n_fuentes = len(fuentes)
    puntos = (
        _puntos_escalon(n_fuentes, PUNTOS_FUENTES_DISTINTAS)
        + _puntos_escalon(comentarios, PUNTOS_COMENTARIOS)
        + _puntos_escalon(compartidos, PUNTOS_COMPARTIDOS)
    )
    if puntos >= REPERCUSION_ALTA:
        nivel = "ALTA"
    elif puntos >= REPERCUSION_MEDIA:
        nivel = "MEDIA"
    else:
        nivel = "BAJA"

    motivos = []
    if n_fuentes > 1:
        motivos.append(f"{n_fuentes} fuentes distintas")
    if comentarios:
        motivos.append(f"{comentarios} comentario{'s' if comentarios != 1 else ''}")
    if compartidos:
        motivos.append(f"{compartidos} compartidos")
    return {
        "puntaje": puntos,
        "nivel": nivel,
        "fuentes": n_fuentes,
        "comentarios": comentarios,
        "compartidos": compartidos,
        "reacciones": reacciones,
        "motivos": motivos,
    }


def escalar_clima(clima_base: str, nivel_repercusion: str) -> str:
    """La repercusión nunca baja la gravedad, solo la sube:
    MEDIA lleva un hecho BUENO a MODERADO; ALTA sube un nivel (hasta EN ALERTA)."""
    idx = NIVELES_CLIMA.index(clima_base) if clima_base in NIVELES_CLIMA else 0
    if nivel_repercusion == "ALTA":
        idx = min(idx + 1, 2)
    elif nivel_repercusion == "MEDIA" and idx == 0:
        idx = 1
    return NIVELES_CLIMA[idx]


TEMAS_CLAVE_CONOCIDOS = [
    ("Corte de Autopista Bs. As.–La Plata por falta de luz (Edesur)", ["autopista", "luz"]),
    ("Corte de Autopista Bs. As.–La Plata por falta de luz (Edesur)", ["autopista", "edesur"]),
    ("Corte de Autopista Bs. As.–La Plata por falta de luz (Edesur)", ["autopista", "sarandi"]),
    ("Corte de Autopista Bs. As.–La Plata por falta de luz (Edesur)", ["autopista", "bernal"]),
    ("Pueblada en defensa de los puestos de trabajo", ["puestos de trabajo", "tornquist"]),
    ("Pueblada en defensa de los puestos de trabajo", ["pueblada", "tornquist"]),
    ("Asamblea por conflicto laboral y despidos", ["despidos", "fabrica", "trabajadores"]),
    ("Pedido de justicia y marcha", ["femicidio", "justicia por"]),
    ("Marcha por seguridad y cacerolazo vecinal", ["marcha", "seguridad", "comisaria"]),
    ("Juntada masiva de motos y picadas", ["juntada de motos", "picadas"]),
]


def limpiar_texto_para_clustering(texto: str) -> str:
    t = quitar_tildes(texto.lower())
    t = re.sub(r"https?://\S+", " ", t)
    t = re.sub(r"[^\w\s]", " ", t)
    palabras = [w for w in t.split() if w not in STOPWORDS_ES and len(w) > 2]
    return " ".join(palabras)


def detectar_tema_clave_unificado(texto: str) -> str:
    t_norm = quitar_tildes(texto.lower())
    for titulo_unificado, keywords in TEMAS_CLAVE_CONOCIDOS:
        if all(k in t_norm for k in keywords):
            return titulo_unificado
    return ""


def agrupar_en_clusters(hallazgos: List[Dict[str, Any]], umbral_similitud: float = 0.35) -> List[Dict[str, Any]]:
    """
    Agrupa hallazgos en clusters semánticos basados en contenido TF-IDF,
    temas clave y localidad/eje temático.
    Ordena los incidentes por cantidad de fuentes y relevancia.
    """
    if not hallazgos:
        return []

    for h in hallazgos:
        comb = texto_sin_comentarios(h.get('texto', '') or h.get('titulo', ''))
        h["partido"] = resolver_partido_geografico_preciso(comb, h.get("partido", ""))
        h["categoria"] = resolver_eje_tematico_preciso(comb, h.get("categoria", ""))

    textos_limpios = [limpiar_texto_para_clustering(f"{h.get('titulo', '')} {h.get('texto', '')}") for h in hallazgos]
    textos_validos = [t if t.strip() else "reclamo vecinal" for t in textos_limpios]

    try:
        vectorizer = TfidfVectorizer(max_features=400, min_df=1)
        tfidf_matrix = vectorizer.fit_transform(textos_validos)
        sim_matrix = cosine_similarity(tfidf_matrix)
    except Exception:
        sim_matrix = None

    n = len(hallazgos)
    visitados = [False] * n
    clusters = []

    for i in range(n):
        if visitados[i]:
            continue

        grupo_indices = [i]
        visitados[i] = True
        comb_i = f"{hallazgos[i].get('titulo', '')} {hallazgos[i].get('texto', '')}".lower()
        tema_i = detectar_tema_clave_unificado(comb_i)

        for j in range(i + 1, n):
            if visitados[j]:
                continue
            
            comb_j = f"{hallazgos[j].get('titulo', '')} {hallazgos[j].get('texto', '')}".lower()
            tema_j = detectar_tema_clave_unificado(comb_j)

            if tema_i and tema_j and tema_i == tema_j:
                visitados[j] = True
                grupo_indices.append(j)
                continue

            if sim_matrix is not None:
                sim = sim_matrix[i, j]
                part_i = hallazgos[i].get("partido", "")
                part_j = hallazgos[j].get("partido", "")
                cat_i = hallazgos[i].get("categoria", "")
                cat_j = hallazgos[j].get("categoria", "")

                if cat_i == cat_j:
                    sim += 0.10
                if part_i == part_j:
                    sim += 0.15

                if ("luz" in comb_i or "edesur" in comb_i) and ("luz" in comb_j or "edesur" in comb_j) and ("autopista" in comb_i and "autopista" in comb_j):
                    sim += 0.40

                # Dos partidos distintos solo se agrupan si el texto es casi el mismo hecho
                # (antes el temporal de Cañuelas se mezclaba con un post de Berisso).
                genericos = ("", "Provincia de Buenos Aires", "PBA")
                if part_i not in genericos and part_j not in genericos and part_i != part_j:
                    if sim_matrix[i, j] < 0.6:
                        continue

                if sim >= umbral_similitud:
                    visitados[j] = True
                    grupo_indices.append(j)

        items_cluster = [hallazgos[idx] for idx in grupo_indices]
        # Representante: la publicación con más conversación (su link es el que se muestra)
        items_cluster.sort(key=lambda x: (x.get("es_convocatoria", 0), _entero(x.get("num_comentarios")), x.get("relevancia", 0), len(x.get("texto", ""))), reverse=True)
        rep = items_cluster[0]

        # Fuentes distintas = autores/medios distintos. (Antes había nombres fijos por
        # texto: cualquier post con "CTA" en mayúsculas —p. ej. "DIRECTA"— se contaba como
        # la misma fuente, y la réplica en varios medios quedaba subestimada.)
        fuentes_distintas = []
        vistas_fuentes = set()
        for it in items_cluster:
            autor_fuente = (it.get("autor") or it.get("fuente") or "Fuente vecinal").strip()
            clave_fuente = quitar_tildes(autor_fuente.lower())
            if clave_fuente not in vistas_fuentes:
                vistas_fuentes.add(clave_fuente)
                fuentes_distintas.append(autor_fuente)

        partidos_set = set()
        for it in items_cluster:
            p = it.get("partido")
            if p and p != "Provincia de Buenos Aires":
                partidos_set.add(p)
        partido_representativo = " / ".join(sorted(partidos_set)) if partidos_set else rep.get("partido", "PBA")

        comb_total = " ".join([f"{it.get('titulo', '')} {it.get('texto', '')}" for it in items_cluster]).lower()
        
        # Determinar estado de clima
        comb_norm = quitar_tildes(comb_total)
        if any(w in comb_norm for w in ["corte total", "corte de autopista", "cacerolazo", "48 h sin luz", "48 horas sin luz", "balacera", "pueblada", "saqueo", "incendiaron la comisaria"]):
            clima_est = "EN ALERTA"
        elif any(w in comb_norm for w in [
            "puestos de trabajo", "despidos", "marcha", "corte de calle", "corte de ruta", "sin luz",
            "cortaron la calle", "cortan la calle", "cortaron la ruta", "cortan la ruta", "piquete",
            "protesta", "movilizacion", "autoconvocados", "asamblea vecinal", "ruidazo",
        ]):
            clima_est = "MODERADO"
        else:
            clima_est = "BUENO"

        repercusion = calcular_repercusion(items_cluster, fuentes_distintas)
        clima_base = clima_est
        clima_est = escalar_clima(clima_base, repercusion["nivel"])

        titulo_cluster = tema_i or rep.get("titulo", "Reclamo vecinal reportado")
        if "corte" in titulo_cluster.lower() and "autopista" in titulo_cluster.lower() and "luz" in titulo_cluster.lower():
            titulo_cluster = "Corte de Autopista Bs. As.–La Plata por falta de luz (Edesur)"
        else:
            if ":" in titulo_cluster and not titulo_cluster.startswith("http"):
                partes_t = titulo_cluster.split(":", 1)
                if len(partes_t[0]) < 30 and len(partes_t[1].strip()) > 10:
                    titulo_cluster = partes_t[1].strip()
            if len(titulo_cluster) > 130:
                titulo_cluster = titulo_cluster[:130].rsplit(" ", 1)[0] + "..."

        # Reacción dinámica basada en comentarios reales de vecinos
        todos_comentarios = []
        for it in items_cluster:
            c_list = it.get("comentarios") or it.get("comentarios_json") or []
            if isinstance(c_list, str):
                try:
                    c_list = json.loads(c_list)
                except Exception:
                    c_list = []
            if isinstance(c_list, list):
                for c in c_list:
                    c = str(c).strip().replace('"', "")
                    if c and c not in todos_comentarios:
                        todos_comentarios.append(c)

        if todos_comentarios:
            c_primer = str(todos_comentarios[0]).strip()
            if " - · - " in c_primer:
                c_texto = c_primer.split(" - · - ")[-1].strip()
            elif ":" in c_primer:
                c_texto = c_primer.split(":", 1)[-1].strip()
            else:
                c_texto = c_primer
            if len(c_texto) > 110:
                c_texto = c_texto[:110].rsplit(" ", 1)[0] + "..."
            reaccion = f"Vecinos comentan: “{c_texto}”"
        else:
            # Antes se inventaba una frase ("Vecinos y familiares se movilizan en reclamo
            # activo") cuando aparecía la palabra "reclamo". Solo se muestran comentarios reales.
            reaccion = "Sin comentarios registrados."

        mods_unificados = set()
        for it in items_cluster:
            for m in it.get("modificadores_agenda", []):
                mods_unificados.add(m)

        clusters.append({
            "id_cluster": len(clusters) + 1,
            "clima_estado": clima_est,
            "titulo_cluster": titulo_cluster,
            "partido": partido_representativo,
            "categoria": rep.get("categoria", "seguridad"),
            "es_convocatoria": any(it.get("es_convocatoria") for it in items_cluster),
            "modificadores_agenda": list(mods_unificados),
            "total_menciones": len(items_cluster),
            "fuentes_nombres": fuentes_distintas,
            "total_fuentes": len(fuentes_distintas),
            "reaccion_vecinal": reaccion,
            "comentarios_cluster": todos_comentarios,
            "repercusion": repercusion,
            "clima_base": clima_base,
            "representante": rep,
            "hallazgos_relacionados": items_cluster,
            # El link del representante primero (antes el orden era aleatorio por set())
            "urls": list(dict.fromkeys(it.get("url", "") for it in items_cluster if it.get("url")))
        })

    # Orden: gravedad final, luego repercusión (réplicas + comentarios + compartidos)
    clusters.sort(key=lambda c: (
        NIVELES_CLIMA.index(c["clima_estado"]),
        c["repercusion"]["puntaje"],
        c["repercusion"]["fuentes"],
        c["repercusion"]["comentarios"],
    ), reverse=True)
    return clusters
