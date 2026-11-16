# -*- coding: utf-8 -*-
"""
Servicio de Alertas por Telegram para Termómetro Digital PBA.
Envía resúmenes ejecutivos y adjunta el archivo PDF directamente al chat de Telegram.
"""

import os
import re
from typing import Any, Dict, Optional
import requests
from dotenv import load_dotenv
from config_pba import es_url_publicacion_valida

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()


def recortar_telegram(texto: str, max_chars: int = 120) -> str:
    if not texto:
        return ""
    t = " ".join(texto.replace("\n", " ").split()).strip()
    if len(t) <= max_chars:
        return t
    recorte = t[:max_chars].rsplit(" ", 1)[0]
    recorte = re.sub(r'[,;:\-–—\s]+$', '', recorte)
    return recorte + "..."


def formatear_mensaje_telegram(datos_edicion: Dict[str, Any]) -> str:
    edicion_id = datos_edicion.get("edicion_id", 1)
    edicion_label = f"Edición #{edicion_id}" if isinstance(edicion_id, int) or str(edicion_id).isdigit() else str(edicion_id)
    hallazgos = datos_edicion.get("total_hallazgos", 0)
    nuevos = datos_edicion.get("nuevos_hallazgos", 0)
    convocatorias = datos_edicion.get("convocatorias", [])
    propuestas = datos_edicion.get("nuevas_propuestas", [])
    nombres = datos_edicion.get("nombres_propios", [])

    msg = [
        f"🚨 *ALERTA TERMÓMETRO DIGITAL PBA — {edicion_label}*",
        "📍 *Cobertura:* 135 Municipios Bonaerenses",
        f"📊 *Hallazgos:* {hallazgos} ({nuevos} nuevos)",
        ""
    ]

    relevamiento = datos_edicion.get("relevamiento_grupos", [])
    if relevamiento:
        msg.append(f"👥 *RELEVAMIENTO DE TUS GRUPOS Y CONTACTOS ({len(relevamiento)}):*")
        for g in relevamiento[:4]:
            f_nom = g.get("fuente", "Grupo").replace("Facebook (", "").replace(")", "").replace("Grupo: ", "")
            p = g.get("partido", "PBA")
            autor = g.get("autor", "Miembro")
            txt_corto = recortar_telegram(g.get("texto") or g.get("titulo") or "", 95)
            url = g.get("url") or ""
            link_str = f" [ver ↗]({url})" if (url and es_url_publicacion_valida(url)) else ""
            msg.append(f"• *[{f_nom} · {p}]* {autor}: _{txt_corto}_{link_str}")
        msg.append("")

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
            txt_corto = recortar_telegram(h.get("texto") or h.get("titulo") or "")
            autor = h.get("autor", "Vecinos")
            msg.append(f"• *[{p}]* {autor}: _{txt_corto}_")
        msg.append("")

    if nombres:
        msg.append(f"👤 *FIGURAS PÚBLICAS / PERSONAS MENCIONADAS POR LOS VECINOS ({len(nombres)}):*")
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
        if resp.status_code != 200:
            # Fallback limpio sin formato si algún caracter de los posteos rompió Markdown
            texto_plano = texto.replace("*", "").replace("_", "").replace("`", "")
            resp = requests.post(url_msg, data={
                "chat_id": cid,
                "text": texto_plano
            }, timeout=15)
        resultado["texto_enviado"] = (resp.status_code == 200)
    except Exception as e:
        resultado["error_texto"] = str(e)

    # 2. Enviar Foto de la publicación si está disponible
    foto_url = datos_edicion.get("foto_destacada")
    if not foto_url and datos_edicion.get("relevamiento_grupos"):
        for g in datos_edicion["relevamiento_grupos"]:
            if g.get("imagen_url") and str(g["imagen_url"]).startswith("http"):
                foto_url = g["imagen_url"]
                break
    if foto_url:
        try:
            r_img = requests.get(foto_url, timeout=8, headers={"User-Agent": "Mozilla/5.0"})
            if r_img.status_code == 200 and len(r_img.content) > 1000:
                url_photo = f"https://api.telegram.org/bot{token}/sendPhoto"
                requests.post(
                    url_photo,
                    data={
                        "chat_id": cid,
                        "caption": f"📸 Imagen de publicación relevada — Edición #{datos_edicion.get('edicion_id', 1)}"
                    },
                    files={"photo": ("publicacion.jpg", r_img.content, "image/jpeg")},
                    timeout=15
                )
                resultado["foto_enviada"] = True
        except Exception:
            pass

    # 3. Enviar Documento PDF adjunto directamente al celular
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
