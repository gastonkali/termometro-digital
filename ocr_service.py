# -*- coding: utf-8 -*-
"""
Módulo OCR Ligero para Extracción de Texto en Flyers y Banners de Convocatorias.
Analiza imágenes adjuntas en publicaciones de Facebook, Instagram o X
para extraer horarios, esquinas, direcciones y consignas que vienen impresas en el flyer.

Soporta:
1. Google Gemini API (Multimodal, alta precisión) si hay GEMINI_API_KEY o GOOGLE_API_KEY en .env.
2. Tesseract OCR local si está instalado en el sistema.
3. Extracción de metadatos de imagen básica.
"""

import os
import re
from typing import Dict, Any, Optional
import requests
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))


def extraer_texto_de_imagen(url_imagen: str, ruta_archivo: Optional[str] = None) -> Dict[str, Any]:
    """
    Intenta extraer el texto incrustado en la imagen del flyer.
    """
    gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    
    # 1. Intentar con Gemini Multimodal si hay API Key disponible
    if gemini_key:
        try:
            from google import genai
            from google.genai import types
            
            client = genai.Client(api_key=gemini_key)
            
            # Descargar imagen en memoria si viene por URL
            contenido_bytes = None
            if ruta_archivo and os.path.exists(ruta_archivo):
                with open(ruta_archivo, "rb") as f:
                    contenido_bytes = f.read()
            elif url_imagen and url_imagen.startswith("http"):
                resp = requests.get(url_imagen, timeout=10)
                if resp.status_code == 200:
                    contenido_bytes = resp.content

            if contenido_bytes:
                prompt = (
                    "Actúa como analista de seguridad y alertas vecinales. Lee todo el texto de este volante/flyer de reclamo o convocatoria. "
                    "Extrae exactamente: fecha, hora, lugar/esquina/comisaría, motivo del reclamo y convocantes. Devuelve un texto claro."
                )
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=[
                        types.Part.from_bytes(data=contenido_bytes, mime_type='image/jpeg'),
                        prompt
                    ]
                )
                texto_extraido = response.text.strip() if response.text else ""
                if texto_extraido:
                    return {
                        "ok": True,
                        "metodo": "gemini_multimodal",
                        "texto_flyer": texto_extraido
                    }
        except Exception as e:
            # Fallback silencioso si falla la llamada
            pass

    # 2. Intentar Tesseract OCR si está disponible
    try:
        import pytesseract
        from PIL import Image
        import io

        if ruta_archivo and os.path.exists(ruta_archivo):
            img = Image.open(ruta_archivo)
        elif url_imagen and url_imagen.startswith("http"):
            resp = requests.get(url_imagen, timeout=10)
            if resp.status_code == 200:
                img = Image.open(io.BytesIO(resp.content))
            else:
                return {"ok": False, "error": "No se pudo descargar la imagen"}
        else:
            return {"ok": False, "error": "Sin origen de imagen"}

        texto = pytesseract.image_to_string(img, lang="spa")
        return {
            "ok": True,
            "metodo": "tesseract_local",
            "texto_flyer": texto.strip()
        }
    except Exception:
        return {
            "ok": False,
            "error": "OCR no disponible (configure GEMINI_API_KEY en .env o instale tesseract)"
        }
