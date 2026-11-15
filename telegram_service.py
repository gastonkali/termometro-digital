# -*- coding: utf-8 -*-
"""
Servicio de Alertas por Telegram para Termómetro Digital PBA.
Envía resúmenes ejecutivos y adjunta el archivo PDF directamente al chat de Telegram.
"""

import os
from typing import Any, Dict, Optional
import requests
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()


def formatear_mensaje_telegram(datos_edicion: Dict[str, Any]) -> str:
    edicion_id = datos_edicion.get("edicion_id", 1)
    hallazgos = datos_edicion.get("total_hallazgos", 0)
    nuevos = datos_edicion.get("nuevos_hallazgos", 0)
    convocatorias = datos_edicion.get("convocatorias", [])
    propuestas = datos_edicion.get("nuevas_propuestas", [])
    nombres = datos_edicion.get("nombres_propios", [])

    msg = [
        f"🚨 *ALERTA TERMÓMETRO DIGITAL PBA — Edición #{edicion_id}*",
        "📍 *Cobertura:* 135 Municipios Bonaerenses",
        f"📊 *Hallazgos:* {hallazgos} ({nuevos} nuevos)",
        ""
    ]

    if convocatorias:
        msg.append(f"📅 *CONVOCATORIAS / PROTESTAS ({len(convocatorias)}):*")
        for c in convocatorias[:5]:
            partido = c.get("partido", "PBA")
            tit = c.get("titulo", "Convocatoria")
            msg.append(f"• *[{partido}]* {tit}")
        msg.append("")

    hallazgos_destacados = datos_edicion.get("hallazgos_destacados", [])
    if hallazgos_destacados:
        msg.append("📡 *VISTA PREVIA DE RECLAMOS VECINALES PBA:*")
        for h in hallazgos_destacados[:3]:
            p = h.get("partido", "PBA")
            txt = (h.get("texto") or "").replace("\n", " ").strip()
            txt_corto = txt[:120] + ("..." if len(txt) > 120 else "")
            autor = h.get("autor", "Vecinos")
            msg.append(f"• *[{p}]* {autor}: _{txt_corto}_")
        msg.append("")

    if nombres:
        msg.append(f"📌 *NOMBRES PROPIOS DEL DÍA ({len(nombres)}):*")
        for n in nombres[:4]:
            msg.append(f"• {n}")
        msg.append("")

    if propuestas:
        msg.append(f"✨ *PALABRAS NUEVAS (Candidatas):*")
        for p in propuestas[:3]:
            msg.append(f"• `{p}`")
        msg.append("")

    return "\n".join(msg)


def enviar_alerta_telegram(
    datos_edicion: Dict[str, Any],
    ruta_pdf: Optional[str] = None,
    chat_id: Optional[str] = None
) -> Dict[str, Any]:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    cid = chat_id or os.getenv("TELEGRAM_CHAT_ID", "").strip()

    if not token or not cid:
        return {
            "ok": False,
            "error": "Faltan configurar TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID en .env"
        }

    texto = formatear_mensaje_telegram(datos_edicion)
    resultado = {"ok": True, "texto_enviado": False, "pdf_enviado": False}

    # 1. Enviar Mensaje de Texto
    try:
        url_msg = f"https://api.telegram.org/bot{token}/sendMessage"
        resp = requests.post(url_msg, data={
            "chat_id": cid,
            "text": texto,
            "parse_mode": "Markdown"
        }, timeout=15)
        resultado["texto_enviado"] = (resp.status_code == 200)
    except Exception as e:
        resultado["error_texto"] = str(e)

    # 2. Enviar Documento PDF adjunto directamente al celular
    if ruta_pdf and os.path.exists(ruta_pdf):
        try:
            url_doc = f"https://api.telegram.org/bot{token}/sendDocument"
            with open(ruta_pdf, "rb") as f:
                resp = requests.post(
                    url_doc,
                    data={
                        "chat_id": cid,
                        "caption": f"📄 Reporte PDF — Edición #{datos_edicion.get('edicion_id', 1)}"
                    },
                    files={"document": f},
                    timeout=30
                )
            resultado["pdf_enviado"] = (resp.status_code == 200)
        except Exception as e:
            resultado["error_pdf"] = str(e)

    return resultado
