# -*- coding: utf-8 -*-
"""
Detector de Picos Abruptos (Spike Detection) y Alerta Temprana en Tiempo Real.
Monitorea la velocidad de menciones por municipio y categoría.
Si un partido o reclamo experimenta un incremento repentino inusual
(ej: 8 o más menciones en menos de 30 minutos), dispara una Alerta Roja Urgente
inmediatamente a WhatsApp sin esperar al cron de la hora.
"""

import os
import sqlite3
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from database import get_conn
from whatsapp_service import enviar_alerta_whatsapp


UMBRAL_SPIKE_DEFECTO = 4  # Cantidad de menciones en ventana corta para considerar pico


def evaluar_spikes_municipales(ventana_minutos: int = 45, umbral_alerta: int = UMBRAL_SPIKE_DEFECTO) -> List[Dict[str, Any]]:
    """
    Evalúa si algún partido bonaerense superó el umbral normal en la última ventana temporal.
    """
    conn = get_conn()
    cur = conn.cursor()

    limite_tiempo = (datetime.now() - timedelta(minutes=ventana_minutos)).isoformat(timespec="seconds")

    rows = cur.execute(
        """
        SELECT partido, categoria, COUNT(*) AS total_menciones,
               SUM(CASE WHEN es_convocatoria = 1 THEN 1 ELSE 0 END) AS convocatorias
        FROM hallazgos
        WHERE fecha_deteccion >= ? AND descartado = 0
        GROUP BY partido, categoria
        HAVING total_menciones >= ?
        ORDER BY total_menciones DESC
        """,
        (limite_tiempo, umbral_alerta)
    ).fetchall()

    spikes_detectados = []
    for r in rows:
        partido = r["partido"]
        cat = r["categoria"]
        total = r["total_menciones"]
        convs = r["convocatorias"]

        # Obtener los 3 títulos más recientes de ese pico
        ejemplos = cur.execute(
            """
            SELECT titulo, texto, url FROM hallazgos
            WHERE partido = ? AND categoria = ? AND fecha_deteccion >= ?
            ORDER BY id DESC LIMIT 3
            """,
            (partido, cat, limite_tiempo)
        ).fetchall()

        spikes_detectados.append({
            "partido": partido,
            "categoria": cat,
            "total_menciones": total,
            "convocatorias": convs,
            "ventana_minutos": ventana_minutos,
            "ejemplos": [dict(e) for e in ejemplos]
        })

    conn.close()
    return spikes_detectados


def procesar_y_notificar_spikes(numero_whatsapp: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Revisa si hay picos activos y si hay destinatario configurado,
    genera el mensaje de urgencia y lo envía.
    """
    spikes = evaluar_spikes_municipales()
    if not spikes:
        return []

    numero = numero_whatsapp or os.getenv("WHATSAPP_NUMERO", "")
    for sp in spikes:
        msg = [
            f"🔥 *¡ALERTA ROJA: PICO DE ACTIVIDAD DETECTADO!*",
            f"📍 *Municipio:* {sp['partido']}",
            f"🏷️ *Categoría:* {sp['categoria']}",
            f"📈 *Volumen:* {sp['total_menciones']} menciones en los últimos {sp['ventana_minutos']} minutos.",
        ]
        if sp["convocatorias"] > 0:
            msg.append(f"⚠️ *Atención:* Se detectaron {sp['convocatorias']} convocatorias/cortes en marcha.")

        msg.append("\n*Publicaciones recientes del foco:*")
        for ej in sp["ejemplos"][:2]:
            msg.append(f"• _{ej['titulo']}_\n  Enlace: {ej['url']}")

        msg.append("\n👉 Ver Panel en vivo: http://127.0.0.1:5055")
        
        texto_alerta = "\n".join(msg)
        datos_edicion = {
            "edicion_id": "URGENTE",
            "total_hallazgos": sp["total_menciones"],
            "nuevos_hallazgos": sp["total_menciones"],
            "convocatorias": [{"partido": sp["partido"], "titulo": f"PICO URGENTE EN {sp['partido']}"}],
            "nombres_propios": []
        }
        
        # Enviar WhatsApp si hay número
        if numero:
            enviar_alerta_whatsapp(numero, datos_edicion)

    return spikes
