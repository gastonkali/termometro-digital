# -*- coding: utf-8 -*-
"""
Servidor Web y API REST de Termómetro Digital (Monitoreo Facebook PBA).
"""

import json
import os
from datetime import datetime
from flask import Flask, jsonify, render_template, request

from config_pba import (
    ANCLAJES_GENERALES_PBA,
    MODIFICADORES_CONVOCATORIA,
    PARTIDOS_CONURBANO,
    PARTIDOS_PBA,
    generar_variantes_termino,
)
from database import (
    aprobar_palabra_candidata,
    cambiar_vigencia_nombre_propio,
    descartar_palabra_candidata,
    get_conn,
    init_db,
    obtener_diccionario_completo,
    registrar_nombre_propio,
)
from engine import (
    construir_url_facebook_search,
    ejecutar_barrido,
    generar_matriz_consultas_multired,
    ingerir_posteos_directos_facebook,
)
from pdf_service import crear_reporte_pdf_edicion
from whatsapp_service import enviar_alerta_whatsapp
from clustering_service import agrupar_en_clusters
from spike_detector import evaluar_spikes_municipales, procesar_y_notificar_spikes
from ocr_service import extraer_texto_de_imagen

app = Flask(__name__)
init_db()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/state", methods=["GET"])
def api_state():
    categoria = request.args.get("categoria", "").strip()
    partido = request.args.get("partido", "").strip()
    pasada = request.args.get("pasada", "").strip()
    solo_agenda = request.args.get("solo_agenda", "0") == "1"
    q_texto = request.args.get("q", "").strip()

    conn = get_conn()

    where_clauses = ["descartado = 0"]
    params = []

    if categoria:
        where_clauses.append("categoria = ?")
        params.append(categoria)
    if partido:
        where_clauses.append("partido = ?")
        params.append(partido)
    if pasada:
        where_clauses.append("pasada = ?")
        params.append(pasada)
    if solo_agenda:
        where_clauses.append("es_convocatoria = 1")
    if q_texto:
        where_clauses.append(
            "(lower(titulo) LIKE ? OR lower(texto) LIKE ? OR lower(termino_detectado) LIKE ? OR lower(partido) LIKE ?)"
        )
        like_q = f"%{q_texto.lower()}%"
        params.extend([like_q, like_q, like_q, like_q])

    where_sql = " AND ".join(where_clauses)
    rows = conn.execute(
        f"""
        SELECT * FROM hallazgos
        WHERE {where_sql}
        ORDER BY fijado DESC, id DESC
        LIMIT 200
        """,
        params,
    ).fetchall()

    hallazgos = []
    for r in rows:
        d = dict(r)
        try:
            d["modificadores_agenda"] = json.loads(d.get("modificadores_agenda") or "[]")
        except Exception:
            d["modificadores_agenda"] = []
        try:
            d["nombres_propios"] = json.loads(d.get("nombres_propios") or "[]")
        except Exception:
            d["nombres_propios"] = []
        hallazgos.append(d)

    # Estadísticas globales
    total_hallazgos = conn.execute(
        "SELECT COUNT(*) AS c FROM hallazgos WHERE descartado = 0"
    ).fetchone()["c"]
    total_convocatorias = conn.execute(
        "SELECT COUNT(*) AS c FROM hallazgos WHERE descartado = 0 AND es_convocatoria = 1"
    ).fetchone()["c"]
    por_categoria_rows = conn.execute(
        "SELECT categoria, COUNT(*) AS c FROM hallazgos WHERE descartado = 0 GROUP BY categoria"
    ).fetchall()
    conteo_categorias = {r["categoria"]: r["c"] for r in por_categoria_rows}

    por_partido_rows = conn.execute(
        """
        SELECT partido, COUNT(*) AS c
        FROM hallazgos
        WHERE descartado = 0
        GROUP BY partido
        ORDER BY c DESC
        LIMIT 20
        """
    ).fetchall()
    top_partidos = [{"partido": r["partido"], "cantidad": r["c"]} for r in por_partido_rows]

    # Nombres propios del día
    nombres_rows = conn.execute(
        "SELECT * FROM nombres_propios ORDER BY vigente DESC, ultima_edicion_id DESC, apariciones DESC"
    ).fetchall()
    nombres_propios = [dict(r) for r in nombres_rows]

    # Palabras candidatas de la Pasada Abierta (propuestas con >= 2 ediciones seguidas primero)
    candidatas_rows = conn.execute(
        """
        SELECT * FROM palabras_candidatas
        WHERE estado IN ('propuesta', 'observando', 'incorporada')
        ORDER BY
            CASE estado WHEN 'propuesta' THEN 0 WHEN 'observando' THEN 1 ELSE 2 END,
            ediciones_consecutivas DESC,
            total_apariciones DESC
        LIMIT 50
        """
    ).fetchall()
    palabras_candidatas = [dict(r) for r in candidatas_rows]

    # Últimas ediciones
    ediciones_rows = conn.execute(
        "SELECT * FROM ediciones ORDER BY id DESC LIMIT 10"
    ).fetchall()
    ediciones = [dict(r) for r in ediciones_rows]

    conn.close()

    # Desduplicación semántica y clusters de incidentes
    clusters = agrupar_en_clusters(hallazgos)

    # Detección de picos en tiempo real (spikes)
    spikes_activos = evaluar_spikes_municipales(ventana_minutos=60, umbral_alerta=3)

    diccionario = obtener_diccionario_completo()
    partidos_q = [partido] if partido and partido in PARTIDOS_PBA else None
    cola_fb = generar_matriz_consultas_multired(partidos_seleccionados=partidos_q)[:45]

    return jsonify(
        {
            "kpis": {
                "total_hallazgos": total_hallazgos,
                "total_convocatorias": total_convocatorias,
                "total_clusters": len(clusters),
                "spikes_activos": len(spikes_activos),
                "nombres_vigentes": sum(1 for n in nombres_propios if n["vigente"] == 1),
                "propuestas_pendientes": sum(
                    1 for p in palabras_candidatas if p["estado"] == "propuesta"
                ),
                "ultima_edicion": ediciones[0] if ediciones else None,
            },
            "conteo_categorias": conteo_categorias,
            "top_partidos": top_partidos,
            "hallazgos": hallazgos,
            "clusters": clusters,
            "spikes": spikes_activos,
            "nombres_propios": nombres_propios,
            "palabras_candidatas": palabras_candidatas,
            "ediciones": ediciones,
            "diccionario": diccionario,
            "modificadores_convocatoria": MODIFICADORES_CONVOCATORIA,
            "anclajes_generales": ANCLAJES_GENERALES_PBA,
            "partidos_pba": PARTIDOS_PBA,
            "partidos_conurbano": PARTIDOS_CONURBANO,
            "cola_facebook": cola_fb,
        }
    )


@app.route("/api/scan", methods=["POST"])
def api_scan():
    payload = request.get_json(silent=True) or {}
    partidos = payload.get("partidos") or None
    max_consultas = int(payload.get("max_consultas", 20))
    freshness = payload.get("freshness", "pw")

    resultado = ejecutar_barrido(
        modo="manual_panel",
        partidos_filtro=partidos,
        max_consultas=max_consultas,
        freshness=freshness,
    )
    return jsonify({"ok": True, "resultado": resultado})


@app.route("/api/ingest", methods=["POST"])
def api_ingest():
    payload = request.get_json(silent=True) or {}
    posteos = payload.get("posteos", [])
    modo = payload.get("modo", "facebook_directo")
    if not isinstance(posteos, list) or not posteos:
        return jsonify({"ok": False, "error": "Lista de posteos vacía"}), 400

    res = ingerir_posteos_directos_facebook(posteos, modo=modo)
    return jsonify({"ok": True, "resultado": res})


@app.route("/api/nombres-propios", methods=["POST"])
def api_agregar_nombre_propio():
    payload = request.get_json(silent=True) or {}
    nombre = (payload.get("nombre") or "").strip()
    tipo = (payload.get("tipo") or "Caso / Empresa / Barrio").strip()
    partido = (payload.get("partido") or "Provincia de Buenos Aires").strip()
    categoria = (payload.get("categoria") or "seguridad").strip()
    contexto = (payload.get("contexto") or "Agregado para seguimiento diario").strip()

    if not nombre:
        return jsonify({"ok": False, "error": "Nombre requerido"}), 400

    conn = get_conn()
    ult = conn.execute("SELECT MAX(id) AS m FROM ediciones").fetchone()["m"] or 1
    conn.close()

    registrar_nombre_propio(
        nombre=nombre,
        tipo=tipo,
        partido=partido,
        categoria_origen=categoria,
        contexto=contexto,
        edicion_id=ult,
    )
    return jsonify(
        {
            "ok": True,
            "fb_url": construir_url_facebook_search(f'"{nombre}" {partido}'),
        }
    )


@app.route("/api/nombres-propios/<int:nombre_id>/vigencia", methods=["POST"])
def api_toggle_nombre_propio(nombre_id: int):
    payload = request.get_json(silent=True) or {}
    vigente = 1 if payload.get("vigente", True) else 0
    cambiar_vigencia_nombre_propio(nombre_id, vigente)
    return jsonify({"ok": True})


@app.route("/api/palabras-candidatas/<int:palabra_id>/aprobar", methods=["POST"])
def api_aprobar_candidata(palabra_id: int):
    payload = request.get_json(silent=True) or {}
    categoria = payload.get("categoria")
    ok = aprobar_palabra_candidata(palabra_id, categoria=categoria)
    return jsonify({"ok": ok})


@app.route("/api/palabras-candidatas/<int:palabra_id>/descartar", methods=["POST"])
def api_descartar_candidata(palabra_id: int):
    ok = descartar_palabra_candidata(palabra_id)
    return jsonify({"ok": ok})


@app.route("/api/keywords", methods=["POST"])
def api_agregar_keyword():
    payload = request.get_json(silent=True) or {}
    termino = (payload.get("termino") or "").strip()
    categoria = (payload.get("categoria") or "seguridad").strip()
    if not termino:
        return jsonify({"ok": False, "error": "Término vacío"}), 400

    conn = get_conn()
    ahora = datetime.now().isoformat(timespec="seconds")
    conn.execute(
        "INSERT OR IGNORE INTO palabras_clave_extra (termino, categoria, origen, creado_en) VALUES (?, ?, 'manual', ?)",
        (termino, categoria, ahora),
    )
    conn.commit()
    conn.close()
    return jsonify(
        {"ok": True, "variantes_generadas": generar_variantes_termino(termino)}
    )


@app.route("/api/ocr/flyer", methods=["POST"])
def api_ocr_flyer():
    payload = request.get_json(silent=True) or {}
    url_img = payload.get("url_imagen") or ""
    res = extraer_texto_de_imagen(url_img)
    return jsonify(res)


@app.route("/api/spikes/notificar", methods=["POST"])
def api_spikes_notificar():
    payload = request.get_json(silent=True) or {}
    numero = payload.get("numero")
    spikes = procesar_y_notificar_spikes(numero)
    return jsonify({"ok": True, "spikes_enviados": len(spikes), "spikes": spikes})


@app.route("/api/pdf/generar", methods=["POST"])
def api_generar_pdf():
    payload = request.get_json(silent=True) or {}
    conn = get_conn()
    ult_id = payload.get("edicion_id") or conn.execute("SELECT MAX(id) AS m FROM ediciones").fetchone()["m"] or 1
    conn.close()

    pdf_path = crear_reporte_pdf_edicion(int(ult_id))
    return jsonify({
        "ok": bool(pdf_path),
        "edicion_id": ult_id,
        "pdf_path": pdf_path,
        "filename": os.path.basename(pdf_path) if pdf_path else ""
    })


@app.route("/api/whatsapp/alerta", methods=["POST"])
def api_whatsapp_alerta():
    payload = request.get_json(silent=True) or {}
    numero = payload.get("numero") or ""
    conn = get_conn()
    ult_id = payload.get("edicion_id") or conn.execute("SELECT MAX(id) AS m FROM ediciones").fetchone()["m"] or 1
    edicion = conn.execute("SELECT * FROM ediciones WHERE id = ?", (ult_id,)).fetchone()
    convocatorias = conn.execute(
        "SELECT titulo, partido, categoria FROM hallazgos WHERE edicion_id = ? AND es_convocatoria = 1", (ult_id,)
    ).fetchall()
    nombres = conn.execute("SELECT nombre FROM nombres_propios WHERE vigente = 1 LIMIT 5").fetchall()
    conn.close()

    pdf_path = crear_reporte_pdf_edicion(int(ult_id))

    datos_edicion = {
        "edicion_id": ult_id,
        "total_hallazgos": edicion["total_hallazgos"] if edicion else 0,
        "nuevos_hallazgos": edicion["nuevos_hallazgos"] if edicion else 0,
        "convocatorias": [dict(c) for c in convocatorias],
        "nombres_propios": [n["nombre"] for n in nombres],
    }

    res = enviar_alerta_whatsapp(numero, datos_edicion, ruta_pdf=pdf_path or "")
    return jsonify(res)


if __name__ == "__main__":
    port = int(os.getenv("TERMOMETRO_PORT", "5055"))
    app.run(host="127.0.0.1", port=port, debug=False)
