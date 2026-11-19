# -*- coding: utf-8 -*-
"""
Reporte Matutino Diario 7:00 AM — Termómetro Digital PBA.
Consolida todas las publicaciones recolectadas en las últimas 12 horas,
genera un PDF especial matutino y lo despacha automáticamente por Telegram.
"""

import os
import sys
from datetime import datetime, timedelta

from database import get_conn
from pdf_service import crear_reporte_pdf_ultimas_horas
from telegram_service import enviar_alerta_telegram


def _hechos_importantes(horas_atras: int):
    try:
        from pdf_service import obtener_hechos_importantes
        return obtener_hechos_importantes(horas_atras=horas_atras, max_hechos=3)
    except Exception as e:
        print("Aviso: no se pudieron calcular los hechos importantes:", e)
        return []


def ejecutar_reporte_matutino(horas_atras: int = 12):
    print(f"\n=======================================================")
    print(f"🌅 INICIANDO REPORTE MATUTINO (Últimas {horas_atras} horas)")
    print(f"Hora local: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"=======================================================\n")

    # 1. Compilar PDF de las últimas 12 horas
    print("📄 Compilando reporte PDF matutino consolidado...")
    ruta_pdf = crear_reporte_pdf_ultimas_horas(horas_atras=horas_atras)
    print(f"✓ PDF matutino generado: {ruta_pdf}")

    # 2. Consultar métricas de las últimas 12 horas
    conn = get_conn()
    corte_iso = (datetime.now() - timedelta(hours=horas_atras)).isoformat(timespec="seconds")

    hallazgos_12hs = conn.execute(
        """
        SELECT * FROM hallazgos 
        WHERE (fecha_deteccion >= ? OR ultima_deteccion >= ?) AND descartado = 0
        ORDER BY es_convocatoria DESC, relevancia DESC, id DESC
        """,
        (corte_iso, corte_iso),
    ).fetchall()

    convocatorias = [h for h in hallazgos_12hs if h["es_convocatoria"] == 1]
    nombres = conn.execute(
        "SELECT DISTINCT nombre FROM nombres_propios WHERE creado_en >= ? OR vigente = 1 ORDER BY (creado_en >= ?) DESC, id DESC LIMIT 5",
        (corte_iso, corte_iso),
    ).fetchall()
    conn.close()

    total_hallazgos = len(hallazgos_12hs)

    # 3. Formatear datos para Telegram
    datos_matutinos = {
        "edicion_id": f"Matutino 7 AM (Últimas {horas_atras}hs)",
        "total_hallazgos": total_hallazgos,
        "nuevos_hallazgos": total_hallazgos,
        "convocatorias": [dict(c) for c in convocatorias],
        "nombres_propios": [n["nombre"] for n in nombres if len(n["nombre"]) <= 25],
        "hallazgos_destacados": [dict(h) for h in hallazgos_12hs[:3]],
        "hechos_importantes": _hechos_importantes(horas_atras),
    }

    # 4. Enviar a Telegram
    print("📲 Enviando reporte matutino consolidado a Telegram...")
    res_tg = enviar_alerta_telegram(datos_matutinos, ruta_pdf=ruta_pdf)
    if res_tg.get("ok"):
        print("✓ ¡Reporte matutino y PDF de 12 horas enviados exitosamente a Telegram!")
    else:
        print("Aviso Telegram:", res_tg)

    return res_tg


if __name__ == "__main__":
    ejecutar_reporte_matutino(horas_atras=12)
