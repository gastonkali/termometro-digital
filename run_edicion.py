# -*- coding: utf-8 -*-
"""
Ejecutor de Edición Horaria de Termómetro Digital PBA.
Corre las 4 pasadas metodológicas, actualiza la base de datos SQLite y genera
un reporte ejecutivo en Markdown con:
- Hallazgos por categoría (Seguridad, Justicia, Sociales/Servicios, Eventos no autorizados, Imagen institucional)
- Agenda de Convocatorias detectadas (modificadores de convocatoria)
- Nombres Propios del Día vigentes
- Propuestas de palabras nuevas (detectadas en 2 ediciones seguidas en la Pasada Abierta)
"""

import argparse
import json
import os
from datetime import datetime

from database import get_conn, init_db
from engine import ejecutar_barrido, generar_matriz_consultas_multired
from pdf_service import crear_reporte_pdf_edicion

REPORTES_DIR = os.path.join(os.path.dirname(__file__), "reportes")


def generar_reporte_markdown(edicion_id: int) -> str:
    os.makedirs(REPORTES_DIR, exist_ok=True)
    conn = get_conn()

    edicion = conn.execute(
        "SELECT * FROM ediciones WHERE id = ?", (edicion_id,)
    ).fetchone()
    hallazgos = conn.execute(
        "SELECT * FROM hallazgos WHERE edicion_id = ? AND descartado = 0 ORDER BY es_convocatoria DESC, relevancia DESC",
        (edicion_id,),
    ).fetchall()
    if not hallazgos:
        hallazgos = conn.execute(
            "SELECT * FROM hallazgos WHERE descartado = 0 ORDER BY id DESC LIMIT 25"
        ).fetchall()

    nombres = conn.execute(
        "SELECT * FROM nombres_propios WHERE vigente = 1 ORDER BY apariciones DESC"
    ).fetchall()
    propuestas = conn.execute(
        "SELECT * FROM palabras_candidatas WHERE estado = 'propuesta' ORDER BY ediciones_consecutivas DESC"
    ).fetchall()
    conn.close()

    lineas = [
        f"# 🌡️ Termómetro Digital PBA — Edición #{edicion_id}",
        f"**Fecha de ejecución:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (America/Argentina/Buenos_Aires)",
        f"**Cobertura:** Provincia de Buenos Aires (135 partidos — excluye CABA y otras provincias)",
        "",
        "## 📊 Resumen de la Edición",
        f"- **Consultas ejecutadas:** {edicion['consultas_ejecutadas'] if edicion else 0}",
        f"- **Partidos barridos:** {edicion['partidos_barridos'] if edicion else 0}",
        f"- **Hallazgos procesados:** {edicion['total_hallazgos'] if edicion else len(hallazgos)}",
        f"- **Hallazgos nuevos incorporados:** {edicion['nuevos_hallazgos'] if edicion else 0}",
        "",
    ]

    # 1. Agenda de Convocatorias
    convocatorias = [h for h in hallazgos if h["es_convocatoria"] == 1]
    lineas.append(f"## 📅 Agenda de Convocatorias Detectadas ({len(convocatorias)})")
    if convocatorias:
        for c in convocatorias:
            mods = ", ".join(json.loads(c["modificadores_agenda"] or "[]"))
            lineas.append(
                f"- **[{c['partido']}]** ({c['categoria']}) **{c['titulo']}** — Modificadores: `{mods}`\n"
                f"  - Extracto: _{c['texto'][:200]}_\n"
                f"  - Enlace: {c['url']}"
            )
    else:
        lineas.append("- _Sin convocatorias nuevas en este corte._")
    lineas.append("")

    # 2. Nombres Propios del Día vigentes
    lineas.append(f"## 📌 Nombres Propios del Día en Seguimiento ({len(nombres)})")
    if nombres:
        for n in nombres:
            lineas.append(
                f"- **{n['nombre']}** ({n['tipo']} — {n['partido']}): {n['apariciones']} menciones | Contexto: _{n['contexto']}_"
            )
    else:
        lineas.append("- _Sin nombres propios activos._")
    lineas.append("")

    # 3. Propuestas de palabras nuevas (2 ediciones seguidas en Pasada Abierta)
    lineas.append(
        f"## ✨ Palabras Nuevas Propuestas (2+ Ediciones Seguidas en Pasada Abierta) ({len(propuestas)})"
    )
    if propuestas:
        for p in propuestas:
            lineas.append(
                f"- **`{p['palabra']}`** — Detectada en **{p['ediciones_consecutivas']} ediciones seguidas** "
                f"(Partido origen: {p['partido_origen']}, Categoría sugerida: `{p['categoria_sugerida']}`)"
            )
    else:
        lineas.append(
            "- _Ninguna palabra candidata alcanzó 2 ediciones consecutivas en este turno._"
        )
    lineas.append("")

    # 4. Detalle de Hallazgos por Categoría
    lineas.append("## 📡 Últimos Hallazgos en Facebook PBA")
    for h in hallazgos[:25]:
        lineas.append(
            f"### [{h['partido']}] {h['titulo']}\n"
            f"- **Categoría:** `{h['categoria']}` | **Término/Variante:** `{h['termino_detectado']}` (`{h['variante_usada']}`) | **Pasada:** `{h['pasada']}`\n"
            f"- **Texto:** {h['texto']}\n"
            f"- **URL:** {h['url']}\n"
        )

    contenido = "\n".join(lineas)
    ruta_edicion = os.path.join(REPORTES_DIR, f"edicion_{edicion_id}.md")
    ruta_ultima = os.path.join(REPORTES_DIR, "ultima_edicion.md")

    with open(ruta_edicion, "w", encoding="utf-8") as f:
        f.write(contenido)
    with open(ruta_ultima, "w", encoding="utf-8") as f:
        f.write(contenido)

    return ruta_ultima


def main():
    parser = argparse.ArgumentParser(
        description="Ejecuta una edición de monitoreo de Termómetro Digital PBA."
    )
    parser.add_argument("--modo", default="cron_horario", help="Modo de ejecución")
    parser.add_argument(
        "--max-consultas", type=int, default=16, help="Cantidad de consultas a ejecutar"
    )
    parser.add_argument(
        "--partido", default="", help="Filtrar por un partido específico de los 135"
    )
    args = parser.parse_args()

    init_db()
    partidos = [args.partido] if args.partido else None
    res = ejecutar_barrido(
        modo=args.modo,
        partidos_filtro=partidos,
        max_consultas=args.max_consultas,
        freshness="pw",
    )
    ruta_rep = generar_reporte_markdown(res["edicion_id"])
    ruta_pdf = crear_reporte_pdf_edicion(res["edicion_id"])

    # Enviar alerta automática por Telegram si está configurado
    try:
        from telegram_service import enviar_alerta_telegram
        conn = get_conn()
        convocatorias = conn.execute(
            "SELECT titulo, partido, categoria FROM hallazgos WHERE edicion_id = ? AND es_convocatoria = 1",
            (res["edicion_id"],),
        ).fetchall()
        nombres = conn.execute(
            "SELECT nombre FROM nombres_propios WHERE vigente = 1 LIMIT 5"
        ).fetchall()
        conn.close()

        datos_edicion = {
            "edicion_id": res["edicion_id"],
            "total_hallazgos": res.get("total_hallazgos", 0),
            "nuevos_hallazgos": res.get("nuevos_hallazgos", 0),
            "convocatorias": [dict(c) for c in convocatorias],
            "nombres_propios": [n["nombre"] for n in nombres],
        }
        res_tg = enviar_alerta_telegram(datos_edicion, ruta_pdf=ruta_pdf or "")
        if res_tg.get("ok"):
            print("✓ Alerta y PDF enviados automáticamente por Telegram")
    except Exception as e:
        print("Aviso Telegram:", e)

    print(json.dumps({**res, "reporte_markdown": ruta_rep, "reporte_pdf": ruta_pdf}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
