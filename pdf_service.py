# -*- coding: utf-8 -*-
"""
Generador automático de reportes PDF para Termómetro Digital PBA.
Utiliza el motor Chromium/Edge Headless local para renderizar HTML estilizado
con diseño profesional listo para compartir.
"""

import json
import os
import subprocess
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional

from database import get_conn

BASE_DIR = os.path.dirname(__file__)
PDF_OUTPUT_DIR = os.path.join(BASE_DIR, "reportes_pdf")
os.makedirs(PDF_OUTPUT_DIR, exist_ok=True)


def encontrar_ejecutable_navegador() -> Optional[str]:
    import glob, shutil
    # Linux / Mac commands in PATH
    for cmd in ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "brave-browser", "microsoft-edge"]:
        path = shutil.which(cmd)
        if path:
            return path

    # Playwright cached chromium
    pw_paths = glob.glob(os.path.expanduser("~/.cache/ms-playwright/chromium-*/chrome-linux64/chrome"))
    if pw_paths and os.path.exists(pw_paths[0]):
        return pw_paths[0]

    pw_headless = glob.glob(os.path.expanduser("~/.cache/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-linux64/chrome-headless-shell"))
    if pw_headless and os.path.exists(pw_headless[0]):
        return pw_headless[0]

    # Windows paths
    candidatos = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
    ]
    for ruta in candidatos:
        if os.path.exists(ruta):
            return ruta
    return None


def generar_html_reporte(edicion_id: int) -> str:
    conn = get_conn()
    edicion = conn.execute("SELECT * FROM ediciones WHERE id = ?", (edicion_id,)).fetchone()
    hallazgos = conn.execute(
        """
        SELECT * FROM hallazgos
        WHERE edicion_id = ? AND descartado = 0
        ORDER BY es_convocatoria DESC, relevancia DESC, id DESC
        """,
        (edicion_id,),
    ).fetchall()
    if not hallazgos:
        hallazgos = conn.execute(
            "SELECT * FROM hallazgos WHERE descartado = 0 ORDER BY es_convocatoria DESC, id DESC LIMIT 40"
        ).fetchall()

    nombres = conn.execute("SELECT * FROM nombres_propios WHERE vigente = 1 ORDER BY apariciones DESC").fetchall()
    propuestas = conn.execute("SELECT * FROM palabras_candidatas WHERE estado = 'propuesta'").fetchall()
    conn.close()

    fecha_hora = datetime.now().strftime("%d/%m/%Y %H:%M")

    # Contadores
    convocatorias = [h for h in hallazgos if h["es_convocatoria"] == 1]
    seguridad = [h for h in hallazgos if h["categoria"] == "seguridad"]
    justicia = [h for h in hallazgos if h["categoria"] == "justicia"]
    servicios = [h for h in hallazgos if h["categoria"] == "sociales_servicios"]
    eventos = [h for h in hallazgos if h["categoria"] == "eventos_no_autorizados"]
    institucional = [h for h in hallazgos if h["categoria"] == "imagen_institucional"]

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8" />
  <title>Termómetro Digital PBA — Edición #{edicion_id}</title>
  <style>
    @page {{
      size: A4;
      margin: 15mm;
    }}
    body {{
      font-family: Arial, Helvetica, sans-serif;
      color: #1e293b;
      margin: 0;
      padding: 0;
      font-size: 11pt;
      line-height: 1.4;
    }}
    .header {{
      border-bottom: 2px solid #0f172a;
      padding-bottom: 10px;
      margin-bottom: 16px;
    }}
    .title {{
      font-size: 20pt;
      font-weight: bold;
      color: #b91c1c;
      margin: 0;
    }}
    .subtitle {{
      font-size: 10pt;
      color: #64748b;
      margin-top: 4px;
    }}
    .kpi-row {{
      display: flex;
      gap: 10px;
      margin-bottom: 16px;
    }}
    .kpi-card {{
      flex: 1;
      background: #f8fafc;
      border: 1px solid #e2e8f0;
      border-radius: 6px;
      padding: 10px;
      text-align: center;
    }}
    .kpi-val {{
      font-size: 16pt;
      font-weight: bold;
      color: #0f172a;
    }}
    .kpi-lbl {{
      font-size: 8pt;
      color: #64748b;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }}
    .section-title {{
      font-size: 13pt;
      font-weight: bold;
      color: #0f172a;
      border-bottom: 1px solid #cbd5e1;
      padding-bottom: 4px;
      margin-top: 18px;
      margin-bottom: 10px;
    }}
    .agenda-box {{
      background: #fffbeb;
      border-left: 4px solid #f59e0b;
      padding: 10px;
      margin-bottom: 10px;
      border-radius: 4px;
    }}
    .badge {{
      display: inline-block;
      font-size: 8pt;
      font-weight: bold;
      padding: 2px 6px;
      border-radius: 3px;
      margin-right: 4px;
    }}
    .badge-agenda {{ background: #fef3c7; color: #b45309; border: 1px solid #fcd34d; }}
    .badge-partido {{ background: #e0f2fe; color: #0369a1; }}
    .badge-red {{ background: #ede9fe; color: #6d28d9; }}
    .badge-cat {{ background: #fee2e2; color: #b91c1c; }}
    .item-card {{
      background: #ffffff;
      border: 1px solid #e2e8f0;
      border-radius: 8px;
      padding: 12px;
      margin-bottom: 12px;
      page-break-inside: avoid;
    }}
    .preview-box {{
      background: #f8fafc;
      border-left: 4px solid #2563eb;
      padding: 8px 12px;
      margin: 8px 0;
      border-radius: 4px;
    }}
    .preview-title {{
      font-size: 7.5pt;
      font-weight: bold;
      color: #64748b;
      text-transform: uppercase;
      margin-bottom: 4px;
    }}
    .preview-text {{
      color: #1e293b;
      font-size: 9.5pt;
      line-height: 1.45;
      margin: 0;
      white-space: pre-wrap;
    }}
    .item {{
      border-bottom: 1px solid #f1f5f9;
      padding: 8px 0;
      page-break-inside: avoid;
    }}
    .item-title {{
      font-weight: bold;
      color: #0f172a;
      font-size: 10.5pt;
    }}
    .item-text {{
      color: #334155;
      font-size: 9.5pt;
      margin: 4px 0;
    }}
    .item-meta {{
      font-size: 8.5pt;
      color: #64748b;
    }}
    .item-url {{
      color: #2563eb;
      font-size: 8pt;
      text-decoration: none;
      word-break: break-all;
    }}
    .footer {{
      margin-top: 25px;
      border-top: 1px solid #e2e8f0;
      padding-top: 8px;
      font-size: 8pt;
      color: #94a3b8;
      text-align: center;
    }}
  </style>
</head>
<body>
  <div class="header">
    <div class="title">🌡️ Termómetro Digital PBA — Reporte de Alertas</div>
    <div class="subtitle">Monitoreo de Redes Sociales (Facebook, X/Twitter, Instagram, Google) • 135 Partidos PBA</div>
    <div class="subtitle"><strong>Fecha:</strong> {fecha_hora} | <strong>Edición:</strong> #{edicion_id}</div>
  </div>

  <div class="kpi-row">
    <div class="kpi-card">
      <div class="kpi-val">{len(hallazgos)}</div>
      <div class="kpi-lbl">Hallazgos Totales</div>
    </div>
    <div class="kpi-card" style="border-left: 3px solid #f59e0b;">
      <div class="kpi-val" style="color: #d97706;">{len(convocatorias)}</div>
      <div class="kpi-lbl">Agenda Convocatorias</div>
    </div>
    <div class="kpi-card" style="border-left: 3px solid #ef4444;">
      <div class="kpi-val" style="color: #dc2626;">{len(seguridad)}</div>
      <div class="kpi-lbl">Seguridad</div>
    </div>
    <div class="kpi-card" style="border-left: 3px solid #8b5cf6;">
      <div class="kpi-val" style="color: #7c3aed;">{len(justicia)}</div>
      <div class="kpi-lbl">Justicia</div>
    </div>
    <div class="kpi-card" style="border-left: 3px solid #3b82f6;">
      <div class="kpi-val" style="color: #2563eb;">{len(nombres)}</div>
      <div class="kpi-lbl">Nombres Propios</div>
    </div>
  </div>
"""

    # Bloque 1: Convocatorias de Agenda
    html += '<div class="section-title">📅 Agenda Temprana de Convocatorias y Protestas</div>'
    if convocatorias:
        for c in convocatorias:
            mods = ", ".join(json.loads(c["modificadores_agenda"] or "[]"))
            html += f"""
            <div class="agenda-box">
              <div>
                <span class="badge badge-agenda">CONVOCATORIA</span>
                <span class="badge badge-partido">📍 {c['partido']}</span>
                <span class="badge badge-red">🌐 {c['fuente']}</span>
              </div>
              <div class="item-title" style="margin-top: 4px;">{c['titulo']}</div>
              <div class="item-text">{c['texto']}</div>
              <div class="item-meta">Modificadores detectados: <strong>{mods}</strong></div>
              <div class="item-meta">Enlace: <a class="item-url" href="{c['url']}">{c['url']}</a></div>
            </div>
            """
    else:
        html += '<p style="color: #64748b; font-size: 9pt;">No se detectaron nuevas convocatorias con fecha u horario en este corte.</p>'

    # Bloque 2: Nombres Propios del Día vigentes
    if nombres:
        html += '<div class="section-title">📌 Nombres Propios del Día en Seguimiento</div>'
        html += '<ul style="font-size: 9.5pt; color: #334155; padding-left: 18px; margin: 6px 0;">'
        for n in nombres[:10]:
            html += f"<li><strong>{n['nombre']}</strong> ({n['tipo']} — 📍 {n['partido']}): {n['apariciones']} menciones. <em>{n['contexto']}</em></li>"
        html += "</ul>"

    # Bloque 3: Propuestas de Palabras Nuevas
    if propuestas:
        html += '<div class="section-title">✨ Palabras Nuevas Propuestas (2 Ediciones Seguidas)</div>'
        html += '<ul style="font-size: 9.5pt; color: #047857; padding-left: 18px; margin: 6px 0;">'
        for p in propuestas:
            html += f"<li><strong>{p['palabra']}</strong> (Sugerida: {p['categoria_sugerida']}, origen: {p['partido_origen']}, {p['ediciones_consecutivas']} ediciones consecutivas)</li>"
        html += "</ul>"

    # Bloque 4: Hallazgos Destacados
    html += '<div class="section-title">📡 Hallazgos Recientes Destacados en PBA</div>'
    for h in hallazgos[:15]:
        texto_raw = (h['texto'] or "").strip()
        partes = texto_raw.split("💬 Comentarios destacados de vecinos:")
        texto_principal = partes[0].strip()
        if len(texto_principal) > 350:
            texto_principal = texto_principal[:350] + "..."

        bloque_comentarios = ""
        if len(partes) > 1 and partes[1].strip():
            comentarios_html = ""
            for c in partes[1].strip().split("\n"):
                c_limpio = c.lstrip("• ").strip()
                if c_limpio:
                    comentarios_html += f"<li><em>{c_limpio}</em></li>"
            if comentarios_html:
                bloque_comentarios = f"""
                <div style="margin-top: 8px; border-top: 1px dashed #cbd5e1; padding-top: 6px;">
                  <strong style="font-size: 8pt; color: #0284c7;">💬 Comentarios destacados de vecinos:</strong>
                  <ul style="margin: 3px 0; padding-left: 16px; font-size: 8.5pt; color: #334155;">
                    {comentarios_html}
                  </ul>
                </div>
                """

        html += f"""
        <div class="item-card">
          <div style="margin-bottom: 6px;">
            <span class="badge badge-partido">📍 {h['partido']}</span>
            <span class="badge badge-red">{h['fuente']}</span>
            <span class="badge badge-cat">🏷️ {h['categoria'].upper()}</span>
          </div>
          <div class="item-title">{h['titulo']}</div>
          <div class="preview-box">
            <div class="preview-title">Vista previa de la publicación:</div>
            <p class="preview-text">"{texto_principal}"</p>
            {bloque_comentarios}
          </div>
          <div class="item-meta">
            <span>👤 <strong>Autor:</strong> {h['autor']}</span> • 
            <span>🔗 <a class="item-url" href="{h['url']}">Abrir publicación original ↗</a></span>
          </div>
        </div>
        """

    html += f"""
  <div class="footer">
    Reporte generado automáticamente por Termómetro Digital • Cobertura 135 Municipios Bonaerenses • Excluye CABA y otras provincias
  </div>
</body>
</html>
"""
    return html


def compilar_pdf_desde_html(html_content: str, ruta_salida_pdf: str) -> bool:
    nav_exe = encontrar_ejecutable_navegador()
    if not nav_exe:
        print("[PDF] Error: No se encontró ningún navegador basado en Chromium (Edge, Chrome o Brave).")
        return False

    temp_html = os.path.join(PDF_OUTPUT_DIR, "temp_reporte.html")
    with open(temp_html, "w", encoding="utf-8") as f:
        f.write(html_content)

    cmd = [
        nav_exe,
        "--headless=new",
        "--disable-gpu",
        "--no-pdf-header-footer",
        f"--print-to-pdf={ruta_salida_pdf}",
        temp_html,
    ]

    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=25)
        if os.path.exists(ruta_salida_pdf) and os.path.getsize(ruta_salida_pdf) > 1000:
            return True
        print(f"[PDF] Error al compilar: {res.stderr}")
        return False
    except Exception as e:
        print(f"[PDF] Excepción en subprocess: {e}")
        return False


def crear_reporte_pdf_edicion(edicion_id: int) -> Optional[str]:
    """Genera el PDF y devuelve su ruta absoluta."""
    html = generar_html_reporte(edicion_id)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    pdf_path = os.path.join(PDF_OUTPUT_DIR, f"Alerta_Termometro_PBA_Edicion_{edicion_id}_{timestamp}.pdf")
    pdf_path_latest = os.path.join(PDF_OUTPUT_DIR, "Alerta_Termometro_PBA_Ultima.pdf")

    if compilar_pdf_desde_html(html, pdf_path):
        # Copiar también a la ruta Latest
        try:
            import shutil
            shutil.copyfile(pdf_path, pdf_path_latest)
        except Exception:
            pass
        return pdf_path
    return None


if __name__ == "__main__":
    conn = get_conn()
    ult = conn.execute("SELECT MAX(id) AS m FROM ediciones").fetchone()["m"] or 1
    conn.close()
    pdf = crear_reporte_pdf_edicion(ult)
    print(f"PDF generado: {pdf}")
