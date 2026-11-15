# -*- coding: utf-8 -*-
"""
Servicio de Alertas por WhatsApp para Termómetro Digital PBA.
Permite enviar resúmenes ejecutivos y enlaces a los reportes PDF generados
a tu número de WhatsApp.

Soporta dos canales:
1. Enlace directo 'wa.me' con mensaje codificado (abrible en 1 clic en WhatsApp Web o App).
2. Integración API directa con Twilio WhatsApp o CallMeBot / UltraMsg si se configura el token en .env.
"""

import os
import urllib.parse
from typing import Dict, Any, Optional
import requests
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

NUMERO_DESTINO = os.getenv("WHATSAPP_NUMERO", "").strip()
TWILIO_SID = os.getenv("TWILIO_ACCOUNT_SID", "").strip()
TWILIO_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "").strip()
TWILIO_FROM = os.getenv("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886").strip()

CALLMEBOT_API_KEY = os.getenv("CALLMEBOT_API_KEY", "").strip()


def formatear_mensaje_whatsapp(datos_edicion: Dict[str, Any], ruta_pdf: str = "") -> str:
    """Prepara el texto formateado con emojis para WhatsApp."""
    edicion_id = datos_edicion.get("edicion_id", 1)
    hallazgos = datos_edicion.get("total_hallazgos", 0)
    nuevos = datos_edicion.get("nuevos_hallazgos", 0)
    convocatorias = datos_edicion.get("convocatorias", [])
    propuestas = datos_edicion.get("nuevas_propuestas", [])
    nombres = datos_edicion.get("nombres_propios", [])

    msg = [
        f"🚨 *ALERTA TERMÓMETRO DIGITAL PBA — Edición #{edicion_id}*",
        "📍 Cobertura: 135 Municipios Bonaerenses",
        f"📊 *Hallazgos:* {hallazgos} ({nuevos} nuevos)",
        ""
    ]

    if convocatorias:
        msg.append(f"📅 *CONVOCATORIAS / PROTESTAS ({len(convocatorias)}):*")
        for c in convocatorias[:4]:
            partido = c.get("partido", "PBA")
            tit = c.get("titulo", "Convocatoria")
            msg.append(f"• *[{partido}]* {tit}")
        msg.append("")

    if nombres:
        msg.append(f"📌 *NOMBRES PROPIOS DEL DÍA ({len(nombres)}):*")
        for n in nombres[:3]:
            msg.append(f"• {n}")
        msg.append("")

    if propuestas:
        msg.append(f"✨ *PALABRAS NUEVAS (2 ediciones seguidas):*")
        for p in propuestas[:3]:
            msg.append(f"• `{p}`")
        msg.append("")

    if ruta_pdf:
        msg.append(f"📄 *Reporte PDF generado:*")
        msg.append(f"{ruta_pdf}")
        msg.append("👉 Ver en Panel: http://127.0.0.1:5055")

    return "\n".join(msg)


def generar_link_whatsapp(numero: str, mensaje: str) -> str:
    """Genera un link wa.me para abrir la conversación y enviar el texto con 1 clic."""
    num_limpio = "".join(filter(str.isdigit, numero))
    msg_encoded = urllib.parse.quote(mensaje)
    return f"https://api.whatsapp.com/send?phone={num_limpio}&text={msg_encoded}"


def enviar_alerta_whatsapp(
    numero: str,
    datos_edicion: Dict[str, Any],
    ruta_pdf: str = ""
) -> Dict[str, Any]:
    """
    Envía la alerta por el método disponible (API directa o genera enlace listo).
    """
    mensaje = formatear_mensaje_whatsapp(datos_edicion, ruta_pdf=ruta_pdf)
    num_limpio = "".join(filter(str.isdigit, numero or NUMERO_DESTINO))

    resultado = {
        "ok": True,
        "mensaje": mensaje,
        "wa_link": generar_link_whatsapp(num_limpio, mensaje) if num_limpio else "",
        "canal": "link_directo"
    }

    # Intentar CallMeBot (servicio gratuito muy común para alertas WhatsApp personales)
    if CALLMEBOT_API_KEY and num_limpio:
        try:
            url = f"https://api.callmebot.com/whatsapp.php?phone={num_limpio}&text={urllib.parse.quote(mensaje)}&apikey={CALLMEBOT_API_KEY}"
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                resultado["canal"] = "callmebot_api"
                resultado["status"] = "enviado_api"
                return resultado
        except Exception as e:
            resultado["error_api"] = str(e)

    # Intentar Twilio si está configurado
    if TWILIO_SID and TWILIO_TOKEN and num_limpio:
        try:
            auth = (TWILIO_SID, TWILIO_TOKEN)
            url = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_SID}/Messages.json"
            data = {
                "From": TWILIO_FROM,
                "To": f"whatsapp:+{num_limpio}",
                "Body": mensaje
            }
            resp = requests.post(url, data=data, auth=auth, timeout=10)
            if resp.status_code in (200, 201):
                resultado["canal"] = "twilio_whatsapp"
                resultado["status"] = "enviado_api"
                return resultado
        except Exception as e:
            resultado["error_api"] = str(e)

    return resultado
