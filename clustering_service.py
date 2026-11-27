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
    es_ataque_a_autoridad,
    fecha_publicacion_iso,
    limpiar_texto_basura_redes,
    es_convocatoria_futura,
    quitar_prefijo_medio,
    quitar_tildes,
    resolver_eje_tematico_preciso,
    resolver_partido_geografico_preciso,
    resolver_todos_partidos_en_texto,
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


def _palabras_de_lugares() -> set:
    """Palabras de los nombres de partidos y localidades. Se sacan al comparar textos:
    si no, "Ecos Diarios Necochea: Detuvieron en Necochea..." y "Noticias de Necochea:
    vuelven los colectivos" se parecían solo por repetir el nombre del lugar."""
    from config_pba import LOCALIDADES_A_PARTIDO, PARTIDOS_PBA
    palabras = set()
    for nombre in list(PARTIDOS_PBA) + list(LOCALIDADES_A_PARTIDO.keys()) + list(LOCALIDADES_A_PARTIDO.values()):
        for w in re.sub(r"[^\w\s]", " ", quitar_tildes(str(nombre).lower())).split():
            if len(w) > 2 and w not in STOPWORDS_ES:
                palabras.add(w)
    return palabras


_PALABRAS_LUGARES = _palabras_de_lugares()


def limpiar_texto_para_clustering(texto: str, autor: str = "") -> str:
    t = quitar_tildes(texto.lower())
    t = re.sub(r"https?://\S+", " ", t)
    t = re.sub(r"[^\w\s]", " ", t)
    # Tampoco cuenta el nombre del medio o de la cuenta, que encabeza los títulos
    # ("Noticias de Necochea: ...")
    quitar = set(re.sub(r"[^\w\s]", " ", quitar_tildes((autor or "").lower())).split()) | _PALABRAS_LUGARES
    palabras = [w for w in t.split() if w not in STOPWORDS_ES and len(w) > 2 and w not in quitar]
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
        comb = quitar_prefijo_medio(texto_sin_comentarios(h.get('texto', '') or h.get('titulo', '')), h.get("autor", ""))
        h["partido"] = resolver_partido_geografico_preciso(comb, h.get("partido", ""))
        h["categoria"] = resolver_eje_tematico_preciso(comb, h.get("categoria", ""))

    textos_limpios = [limpiar_texto_para_clustering(f"{h.get('titulo', '')} {h.get('texto', '')}", h.get("autor", "")) for h in hallazgos]
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

    combs = [f"{h.get('titulo', '')} {h.get('texto', '')}".lower() for h in hallazgos]
    temas = [detectar_tema_clave_unificado(c) for c in combs]
    genericos = ("", "Provincia de Buenos Aires", "PBA")

    def mismo_partido(a: str, b: str) -> bool:
        # "San Nicolás / Trenque Lauquen" y "Trenque Lauquen" cuentan como el mismo
        return a == b or (a not in genericos and b not in genericos and (a in b or b in a))

    def mismo_hecho(i: int, j: int) -> bool:
        comb_i, comb_j = combs[i], combs[j]
        part_i = hallazgos[i].get("partido", "")
        part_j = hallazgos[j].get("partido", "")
        # Un tema genérico ("pedido de justicia") solo une publicaciones del mismo partido:
        # si no, se mezclaban casos distintos de lugares distintos.
        if temas[i] and temas[i] == temas[j] and mismo_partido(part_i, part_j):
            return True
        if sim_matrix is None:
            return False
        sim = sim_matrix[i, j]
        if hallazgos[i].get("categoria", "") == hallazgos[j].get("categoria", ""):
            sim += 0.10
        if mismo_partido(part_i, part_j):
            sim += 0.15
        if ("luz" in comb_i or "edesur" in comb_i) and ("luz" in comb_j or "edesur" in comb_j) and ("autopista" in comb_i and "autopista" in comb_j):
            sim += 0.40

        # Casos conocidos que cambian el titular entre medios (ej. robo a joyería de Bahía
        # con detenido en Tres Arroyos; delincuente de 16 años / justiciero en Morón;
        # ataque en moto en Castelar).
        comb_i_n = quitar_tildes(comb_i)
        comb_j_n = quitar_tildes(comb_j)
        if (
            ("joyeria" in comb_i_n and "joyeria" in comb_j_n and ("bahia" in comb_i_n or "tres arroyos" in comb_i_n) and ("bahia" in comb_j_n or "tres arroyos" in comb_j_n))
            or (part_i == "Morón" and part_j == "Morón" and ("16 anos" in comb_i_n or "justiciero" in comb_i_n) and ("16 anos" in comb_j_n or "justiciero" in comb_j_n))
            or ("castelar" in comb_i_n and "castelar" in comb_j_n and ("moto" in comb_i_n or "asalto" in comb_i_n or "leguizamon" in comb_i_n) and ("moto" in comb_j_n or "asalto" in comb_j_n or "leguizamon" in comb_j_n))
        ):
            return True

        # Dos partidos distintos solo se agrupan si el texto es casi el mismo hecho
        # (antes el temporal de Cañuelas se mezclaba con un post de Berisso).
        if part_i not in genericos and part_j not in genericos and not mismo_partido(part_i, part_j):
            if sim_matrix[i, j] < 0.6:
                return False

        # Mínimo de similitud léxica real (sin nombres de lugares ni de medios, que ya se
        # sacaron del texto) para no fusionar dos hechos distintos del mismo partido.
        if sim_matrix[i, j] < 0.15:
            return False
        return sim >= umbral_similitud

    for i in range(n):
        if visitados[i]:
            continue

        grupo_indices = [i]
        visitados[i] = True

        # Una publicación entra al grupo si es el mismo hecho que CUALQUIERA de las que ya
        # están (antes solo se comparaba con la primera y un mismo hecho quedaba partido
        # cuando cada medio lo titulaba distinto). Se repite hasta que no entre ninguna más.
        agrego = True
        while agrego:
            agrego = False
            for j in range(i + 1, n):
                if not visitados[j] and any(mismo_hecho(m, j) for m in grupo_indices):
                    visitados[j] = True
                    grupo_indices.append(j)
                    agrego = True

        items_cluster = [hallazgos[idx] for idx in grupo_indices]
        # Representante: la publicación con más conversación (su link es el que se muestra).
        # A igual conversación se prefiere un link directo al medio antes que uno de
        # Google Noticias, que a veces no abre.
        items_cluster.sort(key=lambda x: (
            x.get("es_convocatoria", 0),
            _entero(x.get("num_comentarios")),
            0 if "news.google.com/" in (x.get("url") or "") else 1,
            x.get("relevancia", 0),
            len(x.get("texto", "")),
        ), reverse=True)
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
            cuerpo_it = quitar_prefijo_medio(texto_sin_comentarios(it.get("texto", "") or it.get("titulo", "")), it.get("autor", ""))
            todos_p = resolver_todos_partidos_en_texto(cuerpo_it, it.get("partido", ""))
            # Si una sola nota nombra hasta 3 partidos (ej. corte de AySA en Lomas, Echeverría y Ezeiza),
            # conservar todos; si nombra más (listados provinciales), tomar solo el principal del ítem.
            if 1 <= len(todos_p) <= 3:
                for p in todos_p:
                    partidos_set.add(p)
            else:
                p = it.get("partido")
                if p and p != "Provincia de Buenos Aires":
                    partidos_set.add(p)
        partido_representativo = " / ".join(sorted(partidos_set)) if partidos_set else rep.get("partido", "PBA")

        comb_total = " ".join([f"{it.get('titulo', '')} {it.get('texto', '')}" for it in items_cluster]).lower()
        
        # Determinar estado de clima
        comb_norm = quitar_tildes(comb_total)
        if es_ataque_a_autoridad(comb_norm) or any(w in comb_norm for w in [
            "corte total", "corte de autopista", "cacerolazo", "48 h sin luz", "48 horas sin luz",
            "balacera", "pueblada", "saqueo", "saqueos", "intento de saqueo", "intentos de saqueo",
            "saquear", "saquearon", "saquean", "incendiaron la comisaria", "toma de rehenes", "tiroteo",
        ]):
            clima_est = "EN ALERTA"
        elif any(w in comb_norm for w in [
            "puestos de trabajo", "despidos", "marcha", "corte de calle", "corte de ruta", "sin luz",
            "cortaron la calle", "cortan la calle", "cortaron la ruta", "cortan la ruta", "piquete",
            "protesta", "movilizacion", "autoconvocados", "asamblea vecinal", "ruidazo",
            "homicidio", "asesinato", "asesinaron", "mataron", "murio", "muerte", "femicidio",
            "crimen", "sicario", "secuestro", "complot", "atentado", "disparos", "balazos",
            "tiros", "baleado", "baleada", "herido de bala", "heridos de bala", "arma de fuego",
            "enfrentamiento armado", "narcomenudeo", "banda narco", "bandas narco", "bunker narco",
            "asalto", "asaltaron", "entradera", "entraderas", "robo a mano armada", "robos",
        ]):
            clima_est = "MODERADO"
        else:
            clima_est = "BUENO"

        repercusion = calcular_repercusion(items_cluster, fuentes_distintas)
        clima_base = clima_est
        clima_est = escalar_clima(clima_base, repercusion["nivel"])

        # Antigüedad del hecho: tomar la PRIMERA publicación conocida del cluster (no la más reciente)
        fechas_validas = []
        for it in items_cluster:
            dt = it.get("fecha_publicacion_dt") or fecha_publicacion_iso(
                it.get("fecha_publicacion", ""), it.get("url", "")
            )
            if dt:
                fechas_validas.append(dt)
        fecha_primera_dt = min(fechas_validas) if fechas_validas else None
        if fecha_primera_dt:
            rep["fecha_publicacion_dt"] = fecha_primera_dt

        # Siempre el titular real de la publicación, limpio y sin cortes a mitad de palabra.
        titulo_cluster = limpiar_texto_basura_redes(rep.get("titulo") or "Reclamo vecinal reportado")
        if ":" in titulo_cluster and not titulo_cluster.startswith("http"):
            partes_t = titulo_cluster.split(":", 1)
            if len(partes_t[0]) < 35 and len(partes_t[1].strip()) > 10:
                titulo_cluster = partes_t[1].strip()
        # Si el título guardado quedó cortado a mitad de palabra (ej. los antiguos [:75]), reconstruirlo del texto
        cuerpo_rep = limpiar_texto_basura_redes(texto_sin_comentarios(rep.get("texto") or ""))
        if cuerpo_rep and len(titulo_cluster) <= 78 and len(cuerpo_rep) > len(titulo_cluster) + 5:
            primera_linea_cuerpo = cuerpo_rep.split("\n")[0].strip()
            if primera_linea_cuerpo.lower().startswith(titulo_cluster.rstrip(".…").lower()) and len(primera_linea_cuerpo) > len(titulo_cluster):
                titulo_cluster = primera_linea_cuerpo
        if len(titulo_cluster) > 130:
            titulo_cluster = titulo_cluster[:130].rsplit(" ", 1)[0].rstrip(",;:-–— ") + "…"

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
                c_texto = c_texto[:110].rsplit(" ", 1)[0] + "…"
            reaccion = f"Vecinos comentan: “{c_texto}”"
        else:
            reaccion = "Sin comentarios registrados"

        # Revalidar convocatorias con el criterio estricto (evita entregas comerciales o bicis robadas)
        from engine import detectar_modificadores_agenda
        mods_unificados = set()
        es_conv_real = False
        for it in items_cluster:
            cuerpo_it = f"{it.get('titulo', '')} {texto_sin_comentarios(it.get('texto', ''))}"
            mods_it = detectar_modificadores_agenda(cuerpo_it)
            # Solo si la medida es a futuro: "hizo un piquete" es un reclamo reciente
            if mods_it and es_convocatoria_futura(cuerpo_it):
                es_conv_real = True
                for m in mods_it:
                    mods_unificados.add(m)

        clusters.append({
            "id_cluster": len(clusters) + 1,
            "clima_estado": clima_est,
            "titulo_cluster": titulo_cluster,
            "partido": partido_representativo,
            "categoria": rep.get("categoria", "seguridad"),
            "es_convocatoria": es_conv_real,
            "modificadores_agenda": list(mods_unificados),
            "total_menciones": len(items_cluster),
            "fuentes_nombres": fuentes_distintas,
            "total_fuentes": len(fuentes_distintas),
            "reaccion_vecinal": reaccion,
            "comentarios_cluster": todos_comentarios,
            "repercusion": repercusion,
            "clima_base": clima_base,
            "fecha_publicacion_dt": fecha_primera_dt,
            "representante": rep,
            "hallazgos_relacionados": items_cluster,
            # El link del representante primero (antes el orden era aleatorio por set())
            "urls": list(dict.fromkeys(it.get("url", "") for it in items_cluster if it.get("url")))
        })

    # Orden: primero EN ALERTA con repercusión confirmada (MEDIA/ALTA), luego repercusión,
    # luego nivel de clima. Así una nota aislada de 1 sola fuente no desplaza un hecho de 6 fuentes.
    clusters.sort(key=lambda c: (
        1 if (c["clima_estado"] == "EN ALERTA" and c["repercusion"]["nivel"] != "BAJA") else 0,
        c["repercusion"]["puntaje"],
        NIVELES_CLIMA.index(c["clima_estado"]),
        c["repercusion"]["fuentes"],
        c["repercusion"]["comentarios"],
    ), reverse=True)
    return clusters
