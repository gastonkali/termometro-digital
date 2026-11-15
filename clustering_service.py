# -*- coding: utf-8 -*-
"""
Módulo de Desduplicación Semántica y Clustering de Hallazgos para Termómetro Digital PBA.
Agrupa publicaciones similares que relatan el mismo incidente
(ej: 40 publicaciones sobre el mismo corte de tren o reclamo en comisaría)
en un único 'Evento Detectado', evitando reportes inflados y repetitivos.
"""

import re
from typing import Any, Dict, List, Tuple
from collections import Counter
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from config_pba import quitar_tildes, STOPWORDS_ES


def limpiar_texto_para_clustering(texto: str) -> str:
    t = quitar_tildes(texto.lower())
    t = re.sub(r"https?://\S+", " ", t)
    t = re.sub(r"[^\w\s]", " ", t)
    palabras = [w for w in t.split() if w not in STOPWORDS_ES and len(w) > 2]
    return " ".join(palabras)


def agrupar_en_clusters(hallazgos: List[Dict[str, Any]], umbral_similitud: float = 0.45) -> List[Dict[str, Any]]:
    """
    Agrupa hallazgos en clusters semánticos basados en contenido TF-IDF y cercanía geográfica.
    Devuelve lista de clusters consolidados con su representante principal,
    volumen de menciones y enlaces asociados.
    """
    if not hallazgos:
        return []

    if len(hallazgos) == 1:
        h = hallazgos[0]
        return [{
            "id_cluster": 1,
            "titulo_cluster": h.get("titulo", "Incidente único"),
            "partido": h.get("partido", "Provincia de Buenos Aires"),
            "categoria": h.get("categoria", "seguridad"),
            "es_convocatoria": bool(h.get("es_convocatoria")),
            "modificadores_agenda": h.get("modificadores_agenda", []),
            "total_menciones": 1,
            "representante": h,
            "hallazgos_relacionados": [h],
            "urls": [h.get("url", "")]
        }]

    textos_limpios = [limpiar_texto_para_clustering(f"{h.get('titulo', '')} {h.get('texto', '')}") for h in hallazgos]
    
    # Manejar caso de textos vacíos
    textos_validos = [t if t.strip() else "reclamo vecinal" for t in textos_limpios]

    try:
        vectorizer = TfidfVectorizer(max_features=500, min_df=1)
        tfidf_matrix = vectorizer.fit_transform(textos_validos)
        sim_matrix = cosine_similarity(tfidf_matrix)
    except Exception:
        # Fallback a lista simple si no se puede vectorizar
        return [{
            "id_cluster": idx + 1,
            "titulo_cluster": h.get("titulo", "Publicación"),
            "partido": h.get("partido", "PBA"),
            "categoria": h.get("categoria", "seguridad"),
            "es_convocatoria": bool(h.get("es_convocatoria")),
            "total_menciones": 1,
            "representante": h,
            "hallazgos_relacionados": [h],
            "urls": [h.get("url", "")]
        } for idx, h in enumerate(hallazgos)]

    n = len(hallazgos)
    visitados = [False] * n
    clusters = []

    for i in range(n):
        if visitados[i]:
            continue

        grupo_indices = [i]
        visitados[i] = True
        partido_i = hallazgos[i].get("partido", "")

        for j in range(i + 1, n):
            if visitados[j]:
                continue
            
            partido_j = hallazgos[j].get("partido", "")
            sim = sim_matrix[i, j]

            # Bono de similitud si coinciden en el mismo partido bonaerense
            if partido_i and partido_j and partido_i == partido_j:
                sim += 0.15

            if sim >= umbral_similitud:
                visitados[j] = True
                grupo_indices.append(j)

        # Seleccionar representante (el que tenga mayor relevancia o más texto)
        items_cluster = [hallazgos[idx] for idx in grupo_indices]
        items_cluster.sort(key=lambda x: (x.get("es_convocatoria", 0), x.get("relevancia", 0), len(x.get("texto", ""))), reverse=True)
        rep = items_cluster[0]

        # Consolidar modificadores de agenda
        mods_unificados = set()
        for it in items_cluster:
            for m in it.get("modificadores_agenda", []):
                mods_unificados.add(m)

        clusters.append({
            "id_cluster": len(clusters) + 1,
            "titulo_cluster": rep.get("titulo", "Incidente reportado"),
            "partido": rep.get("partido", "Provincia de Buenos Aires"),
            "categoria": rep.get("categoria", "seguridad"),
            "es_convocatoria": any(it.get("es_convocatoria") for it in items_cluster),
            "modificadores_agenda": list(mods_unificados),
            "total_menciones": len(items_cluster),
            "representante": rep,
            "hallazgos_relacionados": items_cluster,
            "urls": list(set(it.get("url", "") for it in items_cluster if it.get("url")))
        })

    # Ordenar clusters: primero convocatorias de agenda, luego mayor volumen de menciones
    clusters.sort(key=lambda c: (1 if c["es_convocatoria"] else 0, c["total_menciones"]), reverse=True)
    return clusters
