# -*- coding: utf-8 -*-
"""
Capa de persistencia SQLite para Termómetro Digital.
Gestiona:
- Ediciones de barrido (runs horarios o manuales)
- Hallazgos de Facebook (clasificados por categoría, partido y modificadores de agenda)
- Nombres propios del día (víctimas, barrios, empresas/fábricas vigentes)
- Palabras candidatas de la Pasada Abierta (detección de 2 ediciones consecutivas)
- Palabras clave personalizadas sumadas al diccionario
"""

import hashlib
import json
import os
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional

from config_pba import CATEGORIAS_BASE, generar_variantes_termino

DB_PATH = os.path.join(os.path.dirname(__file__), "termometro_digital.db")


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_conn()
    cur = conn.cursor()

    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS ediciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha_inicio TEXT NOT NULL,
            fecha_fin TEXT,
            modo TEXT DEFAULT 'automatico',
            partidos_barridos INTEGER DEFAULT 0,
            consultas_ejecutadas INTEGER DEFAULT 0,
            total_hallazgos INTEGER DEFAULT 0,
            nuevos_hallazgos INTEGER DEFAULT 0,
            notas TEXT
        );

        CREATE TABLE IF NOT EXISTS hallazgos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            edicion_id INTEGER,
            fecha_deteccion TEXT NOT NULL,
            fecha_publicacion TEXT,
            fuente TEXT DEFAULT 'Facebook',
            url TEXT NOT NULL,
            url_hash TEXT UNIQUE NOT NULL,
            titulo TEXT,
            texto TEXT NOT NULL,
            autor TEXT,
            categoria TEXT NOT NULL,
            termino_detectado TEXT,
            variante_usada TEXT,
            partido TEXT,
            anclaje_usado TEXT,
            pasada TEXT DEFAULT 'anclaje_general',
            es_convocatoria INTEGER DEFAULT 0,
            modificadores_agenda TEXT DEFAULT '[]',
            nombres_propios TEXT DEFAULT '[]',
            relevancia INTEGER DEFAULT 50,
            fijado INTEGER DEFAULT 0,
            descartado INTEGER DEFAULT 0,
            imagen_url TEXT,
            comentarios_json TEXT DEFAULT '[]',
            FOREIGN KEY(edicion_id) REFERENCES ediciones(id)
        );

        CREATE TABLE IF NOT EXISTS nombres_propios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT UNIQUE NOT NULL,
            tipo TEXT DEFAULT 'Caso / Entidad',
            partido TEXT DEFAULT '',
            categoria_origen TEXT DEFAULT 'seguridad',
            contexto TEXT DEFAULT '',
            primera_edicion_id INTEGER,
            ultima_edicion_id INTEGER,
            apariciones INTEGER DEFAULT 1,
            vigente INTEGER DEFAULT 1,
            creado_en TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS palabras_candidatas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            palabra TEXT UNIQUE NOT NULL,
            categoria_sugerida TEXT DEFAULT 'seguridad',
            partido_origen TEXT DEFAULT '',
            ejemplo_texto TEXT DEFAULT '',
            primera_edicion_id INTEGER NOT NULL,
            ultima_edicion_id INTEGER NOT NULL,
            ediciones_consecutivas INTEGER DEFAULT 1,
            total_apariciones INTEGER DEFAULT 1,
            estado TEXT DEFAULT 'observando',
            actualizado_en TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS palabras_clave_extra (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            termino TEXT UNIQUE NOT NULL,
            categoria TEXT NOT NULL,
            origen TEXT DEFAULT 'propuesta_pasada_abierta',
            creado_en TEXT NOT NULL
        );
        """
    )
    conn.commit()
    conn.close()


def compute_url_hash(url: str, titulo: str = "", texto: str = "") -> str:
    clean = (url or "").strip().split("?")[0].lower()
    if not clean or clean in ("https://www.facebook.com", "https://facebook.com"):
        clean = f"{titulo[:80]}|{texto[:140]}".lower()
    return hashlib.sha256(clean.encode("utf-8")).hexdigest()[:32]


def crear_edicion(modo: str = "automatico", notas: str = "") -> int:
    conn = get_conn()
    cur = conn.cursor()
    ahora = datetime.now().isoformat(timespec="seconds")
    cur.execute(
        "INSERT INTO ediciones (fecha_inicio, modo, notas) VALUES (?, ?, ?)",
        (ahora, modo, notas),
    )
    edicion_id = cur.lastrowid
    conn.commit()
    conn.close()
    return int(edicion_id)


def cerrar_edicion(
    edicion_id: int,
    partidos_barridos: int,
    consultas_ejecutadas: int,
    total_hallazgos: int,
    nuevos_hallazgos: int,
) -> None:
    conn = get_conn()
    cur = conn.cursor()
    ahora = datetime.now().isoformat(timespec="seconds")
    cur.execute(
        """
        UPDATE ediciones
        SET fecha_fin = ?,
            partidos_barridos = ?,
            consultas_ejecutadas = ?,
            total_hallazgos = ?,
            nuevos_hallazgos = ?
        WHERE id = ?
        """,
        (
            ahora,
            partidos_barridos,
            consultas_ejecutadas,
            total_hallazgos,
            nuevos_hallazgos,
            edicion_id,
        ),
    )
    conn.commit()
    conn.close()


def obtener_diccionario_completo() -> Dict[str, Dict[str, Any]]:
    """Devuelve las categorías base más las palabras sumadas por el usuario/sistema."""
    import copy

    categorias = copy.deepcopy(CATEGORIAS_BASE)
    conn = get_conn()
    rows = conn.execute("SELECT termino, categoria FROM palabras_clave_extra").fetchall()
    conn.close()

    for r in rows:
        cat = r["categoria"]
        term = r["termino"]
        if cat in categorias and term not in categorias[cat]["terminos"]:
            categorias[cat]["terminos"].append(term)
    return categorias


def obtener_todos_los_terminos_conocidos() -> set:
    dic = obtener_diccionario_completo()
    conocidos = set()
    for cat_data in dic.values():
        for t in cat_data["terminos"]:
            conocidos.add(t.lower())
            for v in generar_variantes_termino(t):
                conocidos.add(v.lower())
    return conocidos


def insertar_hallazgo(datos: Dict[str, Any]) -> bool:
    """
    Inserta un hallazgo si no existe previamente por url_hash.
    Devuelve True si es un hallazgo nuevo, False si ya existía.
    """
    conn = get_conn()
    cur = conn.cursor()
    ahora = datetime.now().isoformat(timespec="seconds")
    url = datos.get("url", "")
    titulo = datos.get("titulo", "")
    texto = datos.get("texto", "")
    u_hash = compute_url_hash(url, titulo, texto)

    try:
        cur.execute(
            """
            INSERT INTO hallazgos (
                edicion_id, fecha_deteccion, fecha_publicacion, fuente, url, url_hash,
                titulo, texto, autor, categoria, termino_detectado, variante_usada,
                partido, anclaje_usado, pasada, es_convocatoria, modificadores_agenda,
                nombres_propios, relevancia, imagen_url, comentarios_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                datos.get("edicion_id", 1),
                datos.get("fecha_deteccion", ahora),
                datos.get("fecha_publicacion", "Reciente"),
                datos.get("fuente", "Facebook"),
                url,
                u_hash,
                titulo,
                texto,
                datos.get("autor", "Publicación pública FB"),
                datos.get("categoria", "seguridad"),
                datos.get("termino_detectado", ""),
                datos.get("variante_usada", ""),
                datos.get("partido", "Provincia de Buenos Aires"),
                datos.get("anclaje_usado", ""),
                datos.get("pasada", "anclaje_general"),
                1 if datos.get("es_convocatoria") else 0,
                json.dumps(datos.get("modificadores_agenda", []), ensure_ascii=False),
                json.dumps(datos.get("nombres_propios", []), ensure_ascii=False),
                datos.get("relevancia", 70),
                datos.get("imagen_url", ""),
                json.dumps(datos.get("comentarios", []), ensure_ascii=False),
            ),
        )
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        try:
            updates = []
            params = []
            if datos.get("imagen_url"):
                updates.append("imagen_url = ?")
                params.append(datos.get("imagen_url"))
            if datos.get("comentarios"):
                updates.append("comentarios_json = ?")
                params.append(json.dumps(datos.get("comentarios", []), ensure_ascii=False))
            if datos.get("edicion_id"):
                updates.append("edicion_id = ?")
                params.append(datos.get("edicion_id"))
            if updates:
                params.append(u_hash)
                cur.execute(f"UPDATE hallazgos SET {', '.join(updates)} WHERE url_hash = ?", params)
                conn.commit()
        except Exception:
            pass
        finally:
            conn.close()
        return False


def registrar_nombre_propio(
    nombre: str,
    tipo: str,
    partido: str,
    categoria_origen: str,
    contexto: str,
    edicion_id: int,
) -> None:
    nombre_limpio = nombre.strip()
    if len(nombre_limpio) < 3:
        return
    conn = get_conn()
    cur = conn.cursor()
    ahora = datetime.now().isoformat(timespec="seconds")
    row = cur.execute(
        "SELECT id, apariciones FROM nombres_propios WHERE lower(nombre) = lower(?)",
        (nombre_limpio,),
    ).fetchone()
    if row:
        cur.execute(
            """
            UPDATE nombres_propios
            SET ultima_edicion_id = ?,
                apariciones = apariciones + 1,
                contexto = CASE WHEN ? != '' THEN ? ELSE contexto END
            WHERE id = ?
            """,
            (edicion_id, contexto, contexto, row["id"]),
        )
    else:
        cur.execute(
            """
            INSERT INTO nombres_propios (
                nombre, tipo, partido, categoria_origen, contexto,
                primera_edicion_id, ultima_edicion_id, apariciones, vigente, creado_en
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 1, 1, ?)
            """,
            (
                nombre_limpio,
                tipo,
                partido,
                categoria_origen,
                contexto,
                edicion_id,
                edicion_id,
                ahora,
            ),
        )
    conn.commit()
    conn.close()


def registrar_palabra_candidata(
    palabra: str,
    categoria_sugerida: str,
    partido_origen: str,
    ejemplo_texto: str,
    edicion_id: int,
) -> Dict[str, Any]:
    """
    Registra una palabra/frase emergente detectada en la Pasada Abierta ("vecinos" + partido).
    Si aparece en dos ediciones seguidas (ultima_edicion_id == edicion_id - 1),
    incrementa ediciones_consecutivas y pasa a estado 'propuesta'.
    """
    p_clean = palabra.strip().lower()
    conocidos = obtener_todos_los_terminos_conocidos()
    if p_clean in conocidos or len(p_clean) < 4:
        return {"status": "ignored"}

    conn = get_conn()
    cur = conn.cursor()
    ahora = datetime.now().isoformat(timespec="seconds")
    row = cur.execute(
        "SELECT * FROM palabras_candidatas WHERE lower(palabra) = ?", (p_clean,)
    ).fetchone()

    if not row:
        cur.execute(
            """
            INSERT INTO palabras_candidatas (
                palabra, categoria_sugerida, partido_origen, ejemplo_texto,
                primera_edicion_id, ultima_edicion_id, ediciones_consecutivas,
                total_apariciones, estado, actualizado_en
            ) VALUES (?, ?, ?, ?, ?, ?, 1, 1, 'observando', ?)
            """,
            (
                p_clean,
                categoria_sugerida,
                partido_origen,
                ejemplo_texto[:240],
                edicion_id,
                edicion_id,
                ahora,
            ),
        )
        conn.commit()
        conn.close()
        return {"status": "created", "ediciones_consecutivas": 1}

    if row["estado"] in ("incorporada", "descartada"):
        conn.close()
        return {"status": row["estado"]}

    ult_ed = row["ultima_edicion_id"]
    consec = row["ediciones_consecutivas"]

    if edicion_id == ult_ed:
        # Misma edición: solo sumar apariciones totales
        nuevo_consec = consec
    elif edicion_id == ult_ed + 1:
        # Apareció en dos ediciones seguidas
        nuevo_consec = consec + 1
    else:
        # Se cortó la racha de ediciones seguidas, reinicia a 1
        nuevo_consec = 1

    nuevo_estado = "propuesta" if nuevo_consec >= 2 else row["estado"]

    cur.execute(
        """
        UPDATE palabras_candidatas
        SET ultima_edicion_id = ?,
            ediciones_consecutivas = ?,
            total_apariciones = total_apariciones + 1,
            partido_origen = ?,
            ejemplo_texto = ?,
            estado = ?,
            actualizado_en = ?
        WHERE id = ?
        """,
        (
            edicion_id,
            nuevo_consec,
            partido_origen or row["partido_origen"],
            ejemplo_texto[:240] or row["ejemplo_texto"],
            nuevo_estado,
            ahora,
            row["id"],
        ),
    )
    conn.commit()
    conn.close()
    return {"status": nuevo_estado, "ediciones_consecutivas": nuevo_consec}


def aprobar_palabra_candidata(palabra_id: int, categoria: Optional[str] = None) -> bool:
    conn = get_conn()
    cur = conn.cursor()
    row = cur.execute(
        "SELECT * FROM palabras_candidatas WHERE id = ?", (palabra_id,)
    ).fetchone()
    if not row:
        conn.close()
        return False

    cat_final = categoria or row["categoria_sugerida"] or "seguridad"
    ahora = datetime.now().isoformat(timespec="seconds")
    cur.execute(
        "UPDATE palabras_candidatas SET estado = 'incorporada', categoria_sugerida = ?, actualizado_en = ? WHERE id = ?",
        (cat_final, ahora, palabra_id),
    )
    cur.execute(
        "INSERT OR IGNORE INTO palabras_clave_extra (termino, categoria, origen, creado_en) VALUES (?, ?, 'propuesta_2_ediciones', ?)",
        (row["palabra"], cat_final, ahora),
    )
    conn.commit()
    conn.close()
    return True


def descartar_palabra_candidata(palabra_id: int) -> bool:
    conn = get_conn()
    cur = conn.cursor()
    ahora = datetime.now().isoformat(timespec="seconds")
    cur.execute(
        "UPDATE palabras_candidatas SET estado = 'descartada', actualizado_en = ? WHERE id = ?",
        (ahora, palabra_id),
    )
    conn.commit()
    conn.close()
    return True


def cambiar_vigencia_nombre_propio(nombre_id: int, vigente: int) -> bool:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "UPDATE nombres_propios SET vigente = ? WHERE id = ?", (vigente, nombre_id)
    )
    conn.commit()
    conn.close()
    return True
