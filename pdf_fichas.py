# -*- coding: utf-8 -*-
"""
Reporte en formato "fichas 9:16" (1080 x 1920 px), el mismo diseño que el skill de
barrido de redes:

- Portada: título, fecha y partidos, PANORAMA (síntesis de todo el corte),
  convocatorias publicadas y contenido (índice de fichas).
- Una ficha por hecho: En síntesis, datos (cuándo, dónde, difusión, repercusión,
  enlace), reacción vecinal (comentarios anonimizados), cronología en redes y estado.
- Si el hecho tiene imágenes, una página de publicaciones con las imágenes
  centradas, epígrafe y enlace.

Estética neutra: fondo blanco y texto gris oscuro. El color solo marca el nivel:
rojo = convocatoria publicada o en alerta, naranja = reclamo vigente,
amarillo = a tener en cuenta.

Se elige con TERMOMETRO_FORMATO_PDF=fichas (predeterminado) o a4 (formato anterior).
"""

import html as html_lib
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from database import get_conn
from config_pba import texto_sin_comentarios, es_url_publicacion_valida
from pdf_service import (
    agrupar_con_contexto,
    clasificar_descartes_y_vigentes,
    imagen_de_hecho,
    imagen_embebida,
    recortar_texto_limpio,
    resumen_repercusion,
    seleccionar_hechos_tabla,
)

MAX_FICHAS = int(os.getenv("TERMOMETRO_MAX_FICHAS", "8"))

EJE_LABELS = {
    "seguridad": "Seguridad",
    "justicia": "Justicia",
    "sociales_servicios": "Sociales / laboral",
    "eventos_no_autorizados": "Eventos masivos",
    "imagen_institucional": "Imagen institucional",
}

CSS = """
@page { size: 1080px 1920px; margin: 0; }
* { box-sizing: border-box; margin: 0; padding: 0; }
:root {
  --tx: #1F2328; --tx2: #565E68; --tx3: #8A919A; --rule: #DADDE1; --soft: #F2F3F5; --bg: #FFFFFF;
  --rojo: #C62828; --naranja: #E06A00; --amarillo: #E3B000;
}
html, body { background: var(--bg); }
body { font-family: "Segoe UI", Inter, "Noto Sans", "DejaVu Sans", Arial, sans-serif; color: var(--tx); -webkit-print-color-adjust: exact; print-color-adjust: exact; }
.page { width: 1080px; height: 1920px; overflow: hidden; position: relative; page-break-after: always; break-after: page; background: var(--bg); padding: 70px 72px 0; }
.page:last-child { page-break-after: auto; break-after: auto; }
.foot { position: absolute; left: 72px; right: 72px; bottom: 46px; display: flex; justify-content: space-between; gap: 30px; font-size: 21px; color: var(--tx3); border-top: 1px solid var(--rule); padding-top: 16px; background: var(--bg); }
.foot span:first-child { overflow: hidden; white-space: nowrap; text-overflow: ellipsis; }

.lv { display: inline-block; font-size: 20px; font-weight: 700; letter-spacing: 2px; text-transform: uppercase; padding: 5px 14px; border-radius: 6px; }
.lv.rojo { background: var(--rojo); color: #fff; }
.lv.naranja { background: var(--naranja); color: #fff; }
.lv.amarillo { background: var(--amarillo); color: #2B2100; }
.lv.neutro { background: var(--soft); color: var(--tx2); border: 1px solid var(--rule); }
.dot { display: inline-block; width: 18px; height: 18px; border-radius: 50%; flex: none; }
.dot.rojo { background: var(--rojo); } .dot.naranja { background: var(--naranja); } .dot.amarillo { background: var(--amarillo); } .dot.neutro { background: #fff; border: 2px solid #B5BAC1; }
.hl-rojo { color: var(--rojo); font-weight: 700; }

.kicker { font-size: 22px; letter-spacing: 5px; text-transform: uppercase; color: var(--tx3); font-weight: 600; }
.cover h1 { font-size: 62px; line-height: 1.02; font-weight: 700; margin: 22px 0 16px; letter-spacing: -1px; }
.cover .date { font-size: 30px; font-weight: 600; color: var(--tx2); line-height: 1.3; }
.panorama { margin-top: 30px; background: var(--soft); border-left: 8px solid var(--tx); border-radius: 0 12px 12px 0; padding: 26px 30px; }
.panorama h2, .blk h2 { font-size: 21px; letter-spacing: 4px; text-transform: uppercase; color: var(--tx3); font-weight: 700; margin-bottom: 12px; }
.panorama p { font-size: 26px; line-height: 1.4; }
.blk { margin-top: 28px; }
.agenda .row { display: flex; gap: 26px; padding: 10px 0; border-bottom: 1px solid var(--rule); align-items: baseline; }
.agenda .t { width: 110px; flex: none; font-size: 30px; font-weight: 700; }
.agenda .p { font-size: 27px; font-weight: 600; }
.agenda .w { font-size: 23px; color: var(--tx2); margin-top: 3px; line-height: 1.3; }
.agenda .row.hot .t, .agenda .row.hot .p { color: var(--rojo); }
.agenda .flag { font-size: 21px; font-weight: 700; color: var(--rojo); margin-top: 5px; }
.idx .row { display: flex; gap: 20px; align-items: center; padding: 10px 0; border-bottom: 1px solid var(--rule); }
.idx .n { width: 56px; font-size: 30px; font-weight: 700; color: var(--tx3); flex: none; }
.idx .l { font-size: 27px; font-weight: 700; }
.idx .s { font-size: 22px; color: var(--tx2); margin-top: 3px; line-height: 1.3; }
.idx .pg { margin-left: auto; font-size: 21px; color: var(--tx3); flex: none; }
.vacio { font-size: 26px; color: var(--tx2); font-style: italic; padding: 12px 0; }

.fhead { display: flex; align-items: center; gap: 18px; }
.fhead .n { font-size: 30px; font-weight: 700; color: var(--tx3); }
.fhead .type { font-size: 21px; color: var(--tx3); letter-spacing: 2px; text-transform: uppercase; font-weight: 600; }
.ficha h2 { font-size: 54px; line-height: 1.08; font-weight: 700; margin-top: 18px; letter-spacing: -0.5px; }
.ficha h2.largo { font-size: 44px; }
.ficha .loc { font-size: 26px; color: var(--tx2); margin-top: 10px; }
.sint { margin-top: 28px; background: var(--soft); border-left: 8px solid var(--c, #8A919A); border-radius: 0 12px 12px 0; padding: 24px 30px; }
.sint .k { font-size: 20px; letter-spacing: 4px; text-transform: uppercase; color: var(--tx3); font-weight: 700; margin-bottom: 10px; }
.sint p { font-size: 30px; line-height: 1.4; }
.datos { margin-top: 26px; display: grid; grid-template-columns: 190px 1fr; row-gap: 10px; font-size: 25px; line-height: 1.35; }
.datos dt { color: var(--tx3); font-weight: 600; }
.sec { margin-top: 30px; }
.sec h3 { font-size: 21px; letter-spacing: 4px; text-transform: uppercase; color: var(--tx3); font-weight: 700; margin-bottom: 12px; padding-bottom: 8px; border-bottom: 1px solid var(--rule); }
.sec ul { list-style: none; }
.sec li { font-size: 26px; line-height: 1.38; padding-left: 26px; position: relative; margin-bottom: 8px; }
.sec li::before { content: ""; position: absolute; left: 2px; top: 14px; width: 9px; height: 9px; border-radius: 50%; background: #9AA1AA; }
.crono .r { display: flex; gap: 22px; font-size: 25px; line-height: 1.36; margin-bottom: 9px; }
.crono .d { width: 190px; flex: none; font-weight: 700; color: var(--tx2); }
.estado { margin-top: 30px; font-size: 26px; line-height: 1.4; padding: 18px 24px; border: 1px solid var(--rule); border-radius: 10px; }
.estado b { color: var(--tx2); }
.estado.rojo { border: 2px solid var(--rojo); }

.pubs h2 { font-size: 44px; font-weight: 700; margin-top: 14px; line-height: 1.1; }
.cap-blk { margin-top: 34px; text-align: center; }
.cap-blk img { display: block; margin: 0 auto; max-width: 880px; max-height: var(--alto, 1250px); border: 1px solid var(--rule); border-radius: 10px; object-fit: contain; }
.epi { margin-top: 14px; font-size: 25px; color: var(--tx2); line-height: 1.35; }
.epi b { color: var(--tx); }
.lnk { display: inline-block; margin-top: 8px; font-size: 22px; font-weight: 700; color: #1F5FBF; text-decoration: underline; text-underline-offset: 4px; }
.quote { margin: 26px auto 0; max-width: 820px; font-size: 25px; line-height: 1.35; color: var(--tx2); font-style: italic; text-align: center; }
.quote small { display: block; font-style: normal; font-size: 19px; color: var(--tx3); margin-top: 4px; }

.panorama p, .sint p, .sec li, .crono .r > div:last-child, .estado, .datos dd, .agenda .w, .idx .s, .ficha .loc { text-align: justify; hyphens: auto; -webkit-hyphens: auto; }
"""


def _e(texto: Any) -> str:
    return html_lib.escape(str(texto or ""))


def _nivel(c: Dict[str, Any]) -> tuple:
    """(color, etiqueta) según convocatoria y clima del hecho."""
    if c.get("es_convocatoria"):
        return "rojo", "Convocatoria publicada"
    return {
        "EN ALERTA": ("rojo", "En alerta"),
        "MODERADO": ("naranja", "Reclamo vigente"),
        "BUENO": ("amarillo", "A tener en cuenta"),
    }.get(c.get("clima_estado"), ("neutro", "Contexto"))


def _red(fuente: str) -> str:
    """'Facebook (Grupo: X)' -> 'Facebook'; un medio queda con su nombre."""
    f = (fuente or "").strip()
    for red in ("Facebook", "Instagram", "X / Twitter", "TikTok", "YouTube"):
        if f.startswith(red):
            return "X" if red == "X / Twitter" else red
    return f.split(" (")[0] or "Web"


def _fecha(dt: Optional[datetime], con_hora: bool = True) -> str:
    if not dt:
        return "s/f"
    return dt.strftime("%d/%m · %H:%M") if con_hora else dt.strftime("%d/%m")


def _comentarios(c: Dict[str, Any], maximo: int, max_chars: int) -> List[str]:
    """Comentarios reales del hecho, sin el nombre del autor (anonimizados)."""
    salida = []
    for com in c.get("comentarios_cluster") or []:
        t = str(com).replace("\xa0", " ").strip()
        if " - · - " in t:
            t = t.split(" - · - ")[-1]
        elif ":" in t[:60]:
            t = t.split(":", 1)[1]
        t = t.strip().strip('"“”').strip()
        if len(t) >= 8:
            salida.append(recortar_texto_limpio(t, max_chars))
        if len(salida) >= maximo:
            break
    return salida


def _publicaciones(c: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Publicaciones del hecho sin repetir URL, ordenadas por fecha."""
    vistas, salida = set(), []
    for it in c.get("hallazgos_relacionados") or []:
        clave = (it.get("url") or "").strip() or id(it)
        if clave in vistas:
            continue
        vistas.add(clave)
        salida.append(it)
    salida.sort(key=lambda it: it.get("fecha_publicacion_dt") or datetime.min)
    return salida


def _imagenes(c: Dict[str, Any], maximo: int = 2) -> List[tuple]:
    """[(publicación, imagen embebida como data URI)]. Las imágenes se descargan y se
    meten dentro del PDF porque los links de Instagram/Facebook vencen; si no hay
    ninguna en redes se usa la imagen principal de la nota del medio."""
    if not any((it.get("imagen_url") or "").startswith("http") for it in c.get("hallazgos_relacionados") or []):
        imagen_de_hecho(c, max_descargas=1)
    salida, vistas = [], set()
    rep = c.get("representante") or {}
    for it in [rep] + list(reversed(_publicaciones(c))):
        img = (it.get("imagen_url") or "").strip()
        if img.startswith("http") and img not in vistas:
            vistas.add(img)
            src = imagen_embebida(img)
            if src:
                salida.append((it, src))
        if len(salida) >= maximo:
            break
    return salida


def _enlace(url: str, texto: str = "Link de la publicación ↗") -> str:
    url = (url or "").strip()
    if url and es_url_publicacion_valida(url):
        return f'<a class="lnk" href="{_e(url)}">{_e(texto)}</a>'
    return '<span style="color:var(--tx3)">Sin enlace directo</span>'


def _plural(n: int, singular: str, plural: str) -> str:
    return f"{n} {singular if n == 1 else plural}"


# ---------------------------------------------------------------- páginas

def _portada(clusters, fichas, paginas_ficha, total_pags, total_rel, n_desc, titulo, edicion_str, ahora) -> str:
    convs = [c for c in fichas if c.get("es_convocatoria")]
    reclamos = [c for c in fichas if not c.get("es_convocatoria") and c.get("clima_estado") in ("EN ALERTA", "MODERADO")]
    resto = [c for c in fichas if c not in convs and c not in reclamos]

    partidos = list(dict.fromkeys(c.get("partido") or "PBA" for c in clusters))
    if len(partidos) > 4:
        partidos_txt = ", ".join(partidos[:4]) + f" y {len(partidos) - 4} más"
    else:
        partidos_txt = " y ".join([", ".join(partidos[:-1]), partidos[-1]]) if len(partidos) > 1 else (partidos[0] if partidos else "Provincia de Buenos Aires")

    if not clusters:
        panorama = "Sin hechos vigentes en las publicaciones relevadas en este corte."
    else:
        partes = []
        if convs:
            detalle = "; ".join(f"{_e(c['partido'])} ({_e(recortar_texto_limpio(c['titulo_cluster'], 70).replace('...', '…').rstrip('.'))})" for c in convs[:3])
            verbo = "Se relevó" if len(convs) == 1 else "Se relevaron"
            partes.append(f'{verbo} <span class="hl-rojo">{_plural(len(convs), "convocatoria publicada", "convocatorias publicadas")}</span>: {detalle}.')
        if reclamos:
            p_rec = ", ".join(dict.fromkeys(_e(c["partido"]) for c in reclamos[:4]))
            verbo = "se registra" if len(reclamos) == 1 else "se registran"
            pre = f"Además {verbo}" if convs else verbo.capitalize()
            partes.append(f"{pre} {_plural(len(reclamos), 'reclamo vigente', 'reclamos vigentes')} sin convocatoria publicada, en {p_rec}.")
        if resto:
            partes.append(f"Otros {len(resto)} hechos quedan a tener en cuenta." if len(resto) > 1 else "Otro hecho queda a tener en cuenta.")
        if len(clusters) > len(fichas):
            partes.append(f"Se muestran los {len(fichas)} más importantes de {len(clusters)} hechos vigentes.")
        if n_desc:
            partes.append(f"De {total_rel} publicaciones relevadas se descartaron {n_desc} por desactualizadas o fuera de alcance.")
        panorama = " ".join(partes)

    agenda = ""
    if convs:
        filas = ""
        for c in convs[:3]:
            n = fichas.index(c) + 1
            dt = (c.get("representante") or {}).get("fecha_publicacion_dt")
            filas += (
                f'<div class="row hot"><span class="dot rojo"></span><div>'
                f'<div class="p">{_e(c["partido"])}</div>'
                f'<div class="w">{_e(recortar_texto_limpio(c["titulo_cluster"], 120))}</div>'
                f'<div class="flag">● Convocatoria publicada {_e(_fecha(dt))} (ficha {n:02d})</div></div></div>'
            )
        agenda = f'<div class="blk agenda"><h2>Convocatorias</h2>{filas}</div>'

    if fichas:
        filas = ""
        for i, c in enumerate(fichas):
            color, etiqueta = _nivel(c)
            eje = EJE_LABELS.get(c.get("categoria"), c.get("categoria") or "")
            filas += (
                f'<div class="row"><span class="dot {color}"></span><div class="n">{i + 1:02d}</div><div>'
                f'<div class="l">{_e(c["partido"])}</div>'
                f'<div class="s">{_e(recortar_texto_limpio(c["titulo_cluster"], 80))} · {_e(eje.lower())}</div></div>'
                f'<div class="pg">pág. {paginas_ficha[i]}</div></div>'
            )
        indice = f'<div class="blk idx"><h2>Contenido</h2>{filas}</div>'
    else:
        indice = '<div class="blk idx"><h2>Contenido</h2><div class="vacio">Sin fichas en este corte.</div></div>'

    return f"""
<section class="page cover">
  <div class="kicker">Relevamiento en redes sociales · {ahora.strftime('%d/%m/%Y')}</div>
  <h1>{_e(titulo)}</h1>
  <div class="date">{_e(edicion_str)} · corte {ahora.strftime('%H:%M')} · {_e(partidos_txt)}</div>
  <div class="panorama"><h2>Panorama</h2><p>{panorama}</p></div>
  {agenda}
  {indice}
  <div class="foot"><span></span><span>1 / {total_pags}</span></div>
</section>"""


def _ficha(c: Dict[str, Any], n: int, pag: int, total_pags: int, ahora: datetime) -> str:
    color, etiqueta = _nivel(c)
    rep = c.get("representante") or {}
    eje = EJE_LABELS.get(c.get("categoria"), c.get("categoria") or "")
    titulo = recortar_texto_limpio(c.get("titulo_cluster") or "", 110)
    clase_h2 = ' class="largo"' if len(titulo) > 55 else ""

    texto = texto_sin_comentarios(rep.get("texto") or "") or rep.get("titulo") or titulo
    sintesis = recortar_texto_limpio(texto, 340)

    fuentes = c.get("fuentes_nombres") or [rep.get("autor") or rep.get("fuente") or "Redes"]
    rep_data = c.get("repercusion") or {}
    cifras = []
    for clave, nombre in (("comentarios", "comentarios"), ("compartidos", "compartidos"), ("reacciones", "reacciones")):
        if rep_data.get(clave):
            cifras.append(f"{rep_data[clave]} {nombre}")
    difusion = f"{_plural(len(fuentes), 'fuente', 'fuentes')}: {', '.join(fuentes[:4])}"
    if len(fuentes) > 4:
        difusion += f" y {len(fuentes) - 4} más"
    if cifras:
        difusion += " · " + " · ".join(cifras)

    url = (c.get("urls") or [""])[0]
    datos = f"""
    <dt>Cuándo</dt><dd>{_e(rep.get('fecha_publicacion_dt').strftime('%d/%m/%Y · %H:%M') if rep.get('fecha_publicacion_dt') else 'Fecha no verificada')} (publicación)</dd>
    <dt>Dónde</dt><dd>{_e(c.get('partido') or 'PBA')} · {_e(_red(rep.get('fuente')))}</dd>
    <dt>Difusión</dt><dd>{_e(difusion)}</dd>
    <dt>Repercusión</dt><dd>{_e(rep_data.get('nivel') or '—')} · {_e(resumen_repercusion(c))}</dd>
    <dt>Enlace</dt><dd>{_enlace(url)}</dd>"""

    coms = _comentarios(c, maximo=2, max_chars=110)
    bloque_coms = ""
    if coms:
        items = "".join(f"<li>“{_e(t)}”</li>" for t in coms)
        bloque_coms = f'<div class="sec"><h3>Reacción vecinal</h3><ul>{items}</ul></div>'

    pubs = _publicaciones(c)[-5:]
    filas_crono = ""
    for it in pubs:
        quien = it.get("autor") or _red(it.get("fuente"))
        que = texto_sin_comentarios(it.get("titulo") or it.get("texto") or "")
        filas_crono += (
            f'<div class="r"><div class="d">{_e(_fecha(it.get("fecha_publicacion_dt")))}</div>'
            f'<div><b>{_e(quien)}</b> ({_e(_red(it.get("fuente")))}): {_e(recortar_texto_limpio(que, 115))}</div></div>'
        )

    if c.get("es_convocatoria"):
        estado_txt = "convocatoria publicada"
    elif c.get("clima_estado") in ("EN ALERTA", "MODERADO"):
        estado_txt = "reclamo vigente, sin convocatoria publicada"
    else:
        estado_txt = "hecho a tener en cuenta, sin convocatoria publicada"
    estado_txt += f". Repercusión {(rep_data.get('nivel') or '—').lower()}"
    if not coms:
        estado_txt += "; sin comentarios registrados"
    clase_estado = "estado rojo" if color == "rojo" else "estado"

    return f"""
<section class="page ficha" style="--c:var(--{color if color != 'neutro' else 'tx3'})">
  <div class="fhead"><span class="n">{n:02d}</span><span class="lv {color}">{_e(etiqueta)}</span><span class="type">{_e(eje)}</span></div>
  <h2{clase_h2}>{_e(titulo)}</h2>
  <div class="loc">{_e(c.get('partido') or 'PBA')} · {_e(_plural(len(pubs), 'publicación', 'publicaciones'))} sobre el hecho</div>
  <div class="sint"><div class="k">En síntesis</div><p>{_e(sintesis)}</p></div>
  <dl class="datos">{datos}</dl>
  {bloque_coms}
  <div class="sec crono"><h3>Cronología en redes</h3>{filas_crono}</div>
  <div class="{clase_estado}"><b>Estado al {ahora.strftime('%d/%m')}:</b> {_e(estado_txt)}.</div>
  <div class="foot"><span>Fuente: {_e(', '.join(fuentes[:3]))}</span><span>{pag} / {total_pags}</span></div>
</section>"""


def _pagina_publicaciones(c: Dict[str, Any], imgs: List[tuple], n: int, pag: int, total_pags: int) -> str:
    color, etiqueta = _nivel(c)
    alto = "1250px" if len(imgs) == 1 else "620px"
    bloques = ""
    for it, src in imgs:
        quien = it.get("autor") or _red(it.get("fuente"))
        dt = it.get("fecha_publicacion_dt")
        fecha = dt.strftime("%d/%m/%Y, %H:%M") if dt else "fecha no verificada"
        resumen = recortar_texto_limpio(texto_sin_comentarios(it.get("titulo") or it.get("texto") or ""), 110)
        bloques += f"""
  <div class="cap-blk" style="--alto:{alto}">
    <img src="{_e(src)}" alt="">
    <div class="epi"><b>{_e(quien)} · {_e(_red(it.get('fuente')))} · {_e(fecha)}.</b> {_e(resumen)}</div>
    {_enlace(it.get('url'))}
  </div>"""
    coms = _comentarios(c, maximo=1, max_chars=140)
    cita = f'<div class="quote">“{_e(coms[0])}”<small>Comentario de usuario · anonimizado</small></div>' if coms else ""
    return f"""
<section class="page pubs">
  <div class="fhead"><span class="n">{n:02d}</span><span class="lv {color}">{_e(etiqueta)}</span></div>
  <h2>Publicación · {_e(recortar_texto_limpio(c.get('titulo_cluster') or '', 70))}</h2>
  {bloques}
  {cita}
  <div class="foot"><span></span><span>{pag} / {total_pags}</span></div>
</section>"""


# ---------------------------------------------------------------- armado

def renderizar_fichas(
    clusters: List[Dict[str, Any]],
    total_relevadas: int,
    total_descartadas: int,
    edicion_str: str,
    titulo: Optional[str] = None,
    ahora: Optional[datetime] = None,
) -> str:
    """HTML completo del reporte 9:16 a partir de los hechos ya agrupados."""
    ahora = ahora or datetime.now()
    titulo = titulo or "Termómetro Digital PBA"
    # Los más importantes, con lugar garantizado para lo que circula en redes
    fichas = seleccionar_hechos_tabla(clusters, cantidad=MAX_FICHAS, minimo_redes=2)

    # Numeración: portada = 1; cada ficha ocupa 1 página, o 2 si tiene imágenes
    imagenes = [_imagenes(c) for c in fichas]
    con_pubs = [bool(imgs) for imgs in imagenes]
    paginas_ficha, pag = [], 2
    for tiene in con_pubs:
        paginas_ficha.append(pag)
        pag += 2 if tiene else 1
    total_pags = pag - 1

    secciones = [_portada(clusters, fichas, paginas_ficha, total_pags, total_relevadas,
                          total_descartadas, titulo, edicion_str, ahora)]
    for i, c in enumerate(fichas):
        secciones.append(_ficha(c, i + 1, paginas_ficha[i], total_pags, ahora))
        if con_pubs[i]:
            secciones.append(_pagina_publicaciones(c, imagenes[i], i + 1, paginas_ficha[i] + 1, total_pags))

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>{_e(titulo)} · {_e(edicion_str)}</title>
<style>{CSS}</style>
</head>
<body>
{''.join(secciones)}
</body>
</html>
"""


def generar_html_fichas(
    edicion_id: Optional[int] = None,
    horas_atras: Optional[int] = None,
    titulo_custom: Optional[str] = None,
) -> str:
    """Mismos datos y filtros que el reporte A4, en formato de fichas 9:16."""
    conn = get_conn()
    if horas_atras:
        ahora_dt = datetime.now()
        inicio_dt = ahora_dt - timedelta(hours=horas_atras)
        corte_iso = inicio_dt.isoformat(timespec="seconds")
        filas = conn.execute(
            "SELECT * FROM hallazgos WHERE fecha_deteccion >= ? OR ultima_deteccion >= ? ORDER BY es_convocatoria DESC, id DESC",
            (corte_iso, corte_iso),
        ).fetchall()
        edicion_str = f"Consolidado {horas_atras} h ({inicio_dt.strftime('%d/%m %H:%M')} a {ahora_dt.strftime('%d/%m %H:%M')})"
    else:
        filas = conn.execute(
            "SELECT * FROM hallazgos WHERE edicion_id = ? OR ultima_edicion_id = ? ORDER BY es_convocatoria DESC, id DESC",
            (edicion_id, edicion_id),
        ).fetchall()
        edicion_str = f"Edición #{edicion_id or 1}"
    conn.close()

    vigentes, descartados = clasificar_descartes_y_vigentes([dict(f) for f in filas])
    clusters = agrupar_con_contexto(vigentes, edicion_id if not horas_atras else None)
    return renderizar_fichas(
        clusters,
        total_relevadas=len(vigentes) + len(descartados),
        total_descartadas=len(descartados),
        edicion_str=edicion_str,
        titulo=titulo_custom,
    )
