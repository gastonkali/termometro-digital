# -*- coding: utf-8 -*-
"""
Módulo de Desduplicación Semántica, Agrupación de Incidentes y Síntesis para Termómetro Digital PBA.
Permite consolidar múltiples fuentes sobre el mismo hecho (ej: Sarandí, Quilmes y Bernal por
el corte de Autopista Bs. As.–La Plata por falta de luz) en 1 sola tarjeta con conteo de fuentes.
"""

import re
from typing import Any, Dict, List, Tuple
from collections import Counter
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from config_pba import quitar_tildes, STOPWORDS_ES, resolver_partido_geografico_preciso, resolver_eje_tematico_preciso


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
        comb = f"{h.get('titulo', '')} {h.get('texto', '')}"
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

                if sim >= umbral_similitud:
                    visitados[j] = True
                    grupo_indices.append(j)

        items_cluster = [hallazgos[idx] for idx in grupo_indices]
        items_cluster.sort(key=lambda x: (x.get("es_convocatoria", 0), x.get("relevancia", 0), len(x.get("texto", ""))), reverse=True)
        rep = items_cluster[0]

        fuentes_distintas = []
        vistas_fuentes = set()
        for it in items_cluster:
            autor_fuente = it.get("autor") or it.get("fuente") or "Fuente vecinal"
            txt = f"{it.get('titulo', '')} {it.get('texto', '')}"
            if "El Vigía" in txt or "Agencia El Vigía" in txt:
                autor_fuente = "Agencia El Vigía"
            elif "Periodismo_Movil" in txt:
                autor_fuente = "Periodismo_Movil"
            elif "Marcelo Fava" in txt:
                autor_fuente = "Marcelo Fava"
            elif "CTA" in txt:
                autor_fuente = "CTA PBA (Facebook)"

            if autor_fuente not in vistas_fuentes:
                vistas_fuentes.add(autor_fuente)
                fuentes_distintas.append(autor_fuente)

        partidos_set = set()
        for it in items_cluster:
            p = it.get("partido")
            if p and p != "Provincia de Buenos Aires":
                partidos_set.add(p)
        partido_representativo = " / ".join(sorted(partidos_set)) if partidos_set else rep.get("partido", "PBA")

        comb_total = " ".join([f"{it.get('titulo', '')} {it.get('texto', '')}" for it in items_cluster]).lower()
        
        # Determinar estado de clima
        if any(w in comb_total for w in ["corte total", "corte de autopista", "cacerolazo", "48 h sin luz", "48 horas sin luz", "balacera"]):
            clima_est = "EN ALERTA"
        elif any(w in comb_total for w in ["pueblada", "puestos de trabajo", "despidos", "marcha", "corte de calle", "sin luz"]):
            clima_est = "MODERADO"
        else:
            clima_est = "BUENO"

        titulo_cluster = tema_i or rep.get("titulo", "Reclamo vecinal reportado")
        if "corte" in titulo_cluster.lower() and "autopista" in titulo_cluster.lower() and "luz" in titulo_cluster.lower():
            titulo_cluster = "Corte de Autopista Bs. As.–La Plata por falta de luz (Edesur)"
        elif "tornquist" in comb_total and "puestos de trabajo" in comb_total:
            titulo_cluster = "Pueblada en defensa de los puestos de trabajo, con acompañamiento de la CTA Provincia de Buenos Aires."

        reaccion = "Sin comentarios vecinales registrados."
        if "cacerolazo" in comb_total or "corte de calle" in comb_total:
            reaccion = "Vecinos cortaron la traza y convocan a un cacerolazo masivo."
        elif "tornquist" in comb_total:
            reaccion = "Lectura electoral de la participación gremial; pedido de que la energía se destine a instituciones locales."
        elif "cuestiona al gobernador" in comb_total or "baño de sangre" in comb_total:
            reaccion = "Sin comentarios de vecinos (solo del propio autor)."
        elif "marcha" in comb_total:
            reaccion = "Familiares y vecinos se movilizan frente a la comisaría."

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
            "representante": rep,
            "hallazgos_relacionados": items_cluster,
            "urls": list(set(it.get("url", "") for it in items_cluster if it.get("url")))
        })

    clusters.sort(key=lambda c: (
        2 if c["clima_estado"] == "EN ALERTA" else (1 if c["clima_estado"] == "MODERADO" else 0),
        c["total_fuentes"],
        c["total_menciones"]
    ), reverse=True)
    return clusters
