# -*- coding: utf-8 -*-
"""
Configuración maestra de Termómetro Digital (Provincia de Buenos Aires).
Incluye:
- Los 135 partidos oficiales de la Provincia de Buenos Aires.
- Diccionario de localidades / barrios clave de PBA y mapeo al partido correspondiente.
- Diccionario base de palabras clave por categoría.
- Modificadores de convocatoria (para detectar eventos de agenda).
- Reglas de variantes sin tilde, abreviaturas y hashtags.
- Filtros de exclusión geográfica (CABA, otras provincias y países).
- Filtros de no-conflictividad / ruido (gacetillas institucionales, autopromoción, operativos policiales de rutina).
"""

import os
import re
import unicodedata
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple

# Los 135 partidos oficiales de la Provincia de Buenos Aires
PARTIDOS_PBA: List[str] = [
    "Adolfo Alsina", "Adolfo Gonzales Chaves", "Alberti", "Almirante Brown",
    "Arrecifes", "Avellaneda", "Ayacucho", "Azul", "Bahía Blanca", "Balcarce",
    "Baradero", "Benito Juárez", "Berazategui", "Berisso", "Bolívar", "Bragado",
    "Brandsen", "Campana", "Cañuelas", "Capitán Sarmiento", "Carlos Casares",
    "Carlos Tejedor", "Carmen de Areco", "Castelli", "Chacabuco", "Chascomús",
    "Chivilcoy", "Colón", "Coronel Dorrego", "Coronel Pringles", "Coronel Rosales",
    "Coronel Suárez", "Daireaux", "Dolores", "Ensenada", "Escobar",
    "Esteban Echeverría", "Exaltación de la Cruz", "Ezeiza", "Florencio Varela",
    "Florentino Ameghino", "General Alvarado", "General Alvear", "General Arenales",
    "General Belgrano", "General Guido", "General Juan Madariaga", "General La Madrid",
    "General Las Heras", "General Lavalle", "General Paz", "General Pinto",
    "General Pueyrredón", "General Rodríguez", "General San Martín", "General Viamonte",
    "General Villegas", "Guaminí", "Hipólito Yrigoyen", "Hurlingham", "Ituzaingó",
    "José C. Paz", "Junín", "La Costa", "La Matanza", "La Plata", "Lanús",
    "Laprida", "Las Flores", "Leandro N. Alem", "Lezama", "Lincoln", "Lobería",
    "Lobos", "Lomas de Zamora", "Luján", "Magdalena", "Maipú", "Malvinas Argentinas",
    "Mar Chiquita", "Marcos Paz", "Mercedes", "Merlo", "Monte", "Monte Hermoso",
    "Moreno", "Morón", "Navarro", "Necochea", "Nueve de Julio", "Olavarría",
    "Patagones", "Pehuajó", "Pellegrini", "Pergamino", "Pila", "Pilar", "Pinamar",
    "Presidente Perón", "Puan", "Punta Indio", "Quilmes", "Ramallo", "Rauch",
    "Rivadavia", "Rojas", "Roque Pérez", "Saavedra", "Saladillo", "Salliqueló",
    "Salto", "San Andrés de Giles", "San Antonio de Areco", "San Cayetano",
    "San Fernando", "San Isidro", "San Miguel", "San Nicolás", "San Pedro",
    "San Vicente", "Suipacha", "Tandil", "Tapalqué", "Tigre", "Tordillo",
    "Tornquist", "Trenque Lauquen", "Tres Arroyos", "Tres de Febrero",
    "Tres Lomas", "Veinticinco de Mayo", "Vicente López", "Villa Gesell",
    "Villarino", "Zárate"
]

# Partidos del Conurbano / AMBA Bonaerense
PARTIDOS_CONURBANO: List[str] = [
    "Almirante Brown", "Avellaneda", "Berazategui", "Berisso", "Cañuelas",
    "Ensenada", "Escobar", "Esteban Echeverría", "Ezeiza", "Florencio Varela",
    "General Rodríguez", "General San Martín", "Hurlingham", "Ituzaingó",
    "José C. Paz", "La Matanza", "La Plata", "Lanús", "Lomas de Zamora",
    "Malvinas Argentinas", "Marcos Paz", "Merlo", "Moreno", "Morón", "Pilar",
    "Presidente Perón", "Quilmes", "San Fernando", "San Isidro", "San Miguel",
    "San Vicente", "Tigre", "Tres de Febrero", "Vicente López", "Zárate"
]

# Mapeo de Localidades / Barrios Bonaerenses específicos a su Partido real
# Evita asignar erróneamente localidades a "La Plata" solo por mención de la "Autopista Bs. As.-La Plata"
LOCALIDADES_A_PARTIDO: Dict[str, str] = {
    # Avellaneda
    "sarandi": "Avellaneda",
    "sarandí": "Avellaneda",
    "dock sud": "Avellaneda",
    "gerli avellaneda": "Avellaneda",
    "wilde": "Avellaneda",
    "piñeyro": "Avellaneda",
    "villa dominico": "Avellaneda",
    # Quilmes
    "bernal": "Quilmes",
    "don bosco": "Quilmes",
    "ezpeleta": "Quilmes",
    "san francisco solano": "Quilmes",
    "villa la florida": "Quilmes",
    # Lanús
    "valentin alsina": "Lanús",
    "valentín alsina": "Lanús",
    "monte chingolo": "Lanús",
    "remedios de escalada": "Lanús",
    "gerli lanus": "Lanús",
    # Lomas de Zamora
    "banfield": "Lomas de Zamora",
    "temperley": "Lomas de Zamora",
    "turdera": "Lomas de Zamora",
    "ing. budge": "Lomas de Zamora",
    "ingeniero budge": "Lomas de Zamora",
    "fiorito": "Lomas de Zamora",
    "villa albertina": "Lomas de Zamora",
    # Berazategui
    "hudson": "Berazategui",
    "ranelagh": "Berazategui",
    "platanos": "Berazategui",
    "plátanos": "Berazategui",
    "gutierrez berazategui": "Berazategui",
    # Almirante Brown
    "adrogue": "Almirante Brown",
    "adrogué": "Almirante Brown",
    "burzaco": "Almirante Brown",
    "glew": "Almirante Brown",
    "longchamps": "Almirante Brown",
    "claypole": "Almirante Brown",
    "rafael calzada": "Almirante Brown",
    "malvinas argentinas brown": "Almirante Brown",
    # La Matanza
    "san justo": "La Matanza",
    "ramos mejia": "La Matanza",
    "ramos mejía": "La Matanza",
    "gonzalez catan": "La Matanza",
    "gonzález catán": "La Matanza",
    "virrey del pino": "La Matanza",
    "isidro casanova": "La Matanza",
    "gregorio de laferrere": "La Matanza",
    "laferrere": "La Matanza",
    "ciudad evita": "La Matanza",
    "tapiales": "La Matanza",
    "villa madero": "La Matanza",
    # San Martín
    "villa ballester": "General San Martín",
    "jose leon suarez": "General San Martín",
    "josé león suárez": "General San Martín",
    "san andres": "General San Martín",
    # San Isidro
    "boulogne": "San Isidro",
    "martinez": "San Isidro",
    "martínez": "San Isidro",
    "beccar": "San Isidro",
    "acassuso": "San Isidro",
    # Vicente López
    "florida vicente lopez": "Vicente López",
    "olivos": "Vicente López",
    "munro": "Vicente López",
    "carapachay": "Vicente López",
    "villa martelli": "Vicente López",
    # Tres de Febrero
    "caseros": "Tres de Febrero",
    "ciudadela": "Tres de Febrero",
    "el palomar": "Morón",
    "saenz peña": "Tres de Febrero",
    "santos lugares": "Tres de Febrero",
    # Morón
    "haedo": "Morón",
    "castelar": "Morón",
    # Merlo
    "san antonio de padua": "Merlo",
    "parque san martin": "Merlo",
    "libertad": "Merlo",
    # Moreno
    "paso del rey": "Moreno",
    "trujui": "Moreno",
    "cuartel v": "Moreno",
    # La Plata localidades
    "city bell": "La Plata",
    "gonnet": "La Plata",
    "villa elisa": "La Plata",
    "los hornos": "La Plata",
    "tolosa": "La Plata",
    "villa elvira": "La Plata",
    "san carlos la plata": "La Plata",
    # General Pueyrredón / Costa / Interior PBA
    "mar del plata": "General Pueyrredón",
    "mardel": "General Pueyrredón",
    "mdp": "General Pueyrredón",
    "carhue": "Adolfo Alsina",
    "carhué": "Adolfo Alsina",
    "rivera": "Adolfo Alsina",
    # Abreviaturas habituales del conurbano ("Lomas, Echeverría y Ezeiza")
    "echeverria": "Esteban Echeverría",
    "echeverría": "Esteban Echeverría",
    "lomas": "Lomas de Zamora",
    "varela": "Florencio Varela",
}

# Localidades cuyo nombre también es apellido o palabra común ("Juancho Martínez",
# "libertad"). Solo cuentan si van precedidas de "en", "de", "barrio", etc.
LOCALIDADES_AMBIGUAS: Set[str] = {
    "martinez", "libertad", "don bosco", "san andres", "wilde", "hudson", "glew",
}

# Partidos de PBA que comparten nombre con departamentos/ciudades de otras provincias
# o de otros países (México, Colombia, Perú, Uruguay, España). Si el texto nombra otra
# provincia o país, no alcanzan como anclaje; en Google Noticias se consultan exigiendo PBA.
PARTIDOS_NOMBRE_COMPARTIDO: Set[str] = {
    "Maipú", "Rivadavia", "General Alvear", "Junín", "Colón", "Lavalle",
    "General Las Heras", "San Pedro", "Mercedes", "Pila", "Monte", "Salto",
    "General Paz", "Rojas", "Lobos", "Azul", "La Costa", "Puan",
    "Avellaneda", "Pilar", "Moreno", "Escobar",  # Avellaneda (Santa Fe), Pilar (Córdoba)...
    "Bolívar", "Ituzaingó",  # Bolívar (apellido y barrios en todo el país), Ituzaingó (Corrientes)
    # Compartidos con otros países y provincias (causaban falsos positivos de MX/CO/PE/UY/MDZ/MIS)
    "Ensenada", "Benito Juárez", "Magdalena", "Dolores", "Campana", "San Cayetano",
    "San Vicente", "Luján", "Castelli", "Las Flores", "San Isidro", "San Martín",
    "San Miguel", "San Fernando", "Morón", "General Belgrano", "Saavedra",
    "Lincoln", "Navarro", "Alberti", "Suipacha",
}

# Personas o lugares de otras provincias/países que contienen el nombre de un partido.
# Se borran del texto antes de ubicar la publicación (editable).
NOMBRES_NO_GEOGRAFICOS: List[str] = [
    "ramon lanus", "miguel lanus", "guillermo moreno", "mariano moreno", "pablo escobar",
    "avellaneda santa fe", "pilar cordoba", "lomas de zamora futbol",
    "lujan de cuyo", "juan jose castelli", "rio magdalena", "magdalena del mar",
    "magdalena contreras", "magdalena de kino", "sector la campana", "la campana",
    "beca benito juarez", "alcaldia benito juarez", "ensenada bc", "ensenada baja california",
    "san vicente del caguan", "san vicente del raspeig", "san vicente misiones",
    "dolores hidalgo", "moron de la frontera", "san miguel de tucuman",
    "san fernando del valle", "carlos escobar",
]


# Partidos que también son nombres o apellidos de personas: "Luján" (María Luján, la
# víctima), "Zárate" (Evangelina Zárate), "Mercedes", "Dolores", "Pilar", "Moreno"...
PARTIDOS_NOMBRE_DE_PERSONA: Set[str] = {
    "Luján", "Mercedes", "Dolores", "Pilar", "Moreno", "Rojas", "Lobos", "Colón", "Alberti",
    "Pellegrini", "Rivadavia", "Saavedra", "Ramallo", "Escobar", "Zárate", "Lincoln",
    "Castelli", "Rauch", "Lezama", "Navarro", "Salto", "Junín", "Bolívar", "Tordillo",
}
_PALABRAS_NO_NOMBRE_PILA = {
    "en", "de", "del", "la", "el", "los", "las", "y", "a", "por", "para", "desde", "hacia",
    "hasta", "entre", "sobre", "partido", "ciudad", "localidad", "municipio", "zona", "provincia",
    "intendente", "intendenta", "concejo", "hoy", "ayer", "urgente", "alerta", "barrio", "villa",
    "basilica", "rio", "ruta", "general", "san", "santa", "estacion", "centro", "noticias",
}
_SUFIJOS_LUGAR = {"centro", "norte", "sur", "este", "oeste", "ciudad", "partido", "hoy", "ya", "y", "en"}
_PREFIJOS_VICTIMA = re.compile(
    r"(?:justicia\s+(?:por|para)|#justiciapor|crimen\s+de|asesinato\s+de|femicidio\s+de|"
    r"homicidio\s+de|muerte\s+de|la\s+joven|el\s+joven|la\s+nena|el\s+nene|la\s+victima|"
    r"la\s+mama\s+de|el\s+papa\s+de|la\s+madre\s+de|el\s+padre\s+de)\s*$"
)


def enmascarar_personas(texto: str) -> str:
    """Saca del texto los nombres de partido que en realidad son una persona, mirando el
    texto ORIGINAL (con mayúsculas): "Justicia por Luján", "María Luján", "Luján Gómez",
    "Evangelina Zarate". Se deja tal cual si el texto está todo en mayúsculas."""
    if not texto:
        return texto
    salida = texto
    for partido in PARTIDOS_NOMBRE_DE_PERSONA:
        variantes = {partido, quitar_tildes(partido)}
        for v in variantes:
            for m in reversed(list(re.finditer(r"(?<![\wÁÉÍÓÚÑáéíóúñ])" + re.escape(v) + r"(?![\wÁÉÍÓÚÑáéíóúñ])", salida))):
                antes = salida[:m.start()]
                despues = salida[m.end():]
                prev = re.search(r"([A-Za-zÁÉÍÓÚÑáéíóúñ]+)[ \t]+$", antes)
                prox = re.match(r"[ \t]+([A-Za-zÁÉÍÓÚÑáéíóúñ]+)", despues)
                es_persona = False
                # "justicia por Luján", "el crimen de Luján"
                if _PREFIJOS_VICTIMA.search(quitar_tildes(antes.lower())[-40:]):
                    es_persona = True
                # "María Luján": nombre de pila con mayúscula antes, que no sea preposición
                # ni comienzo de oración
                elif prev and prev.group(1)[0].isupper() and not prev.group(1).isupper():
                    p = quitar_tildes(prev.group(1).lower())
                    inicio_oracion = re.search(r"(^|[.!?:\n]\s*)" + re.escape(prev.group(1)) + r"[ \t]+$", antes)
                    if p not in _PALABRAS_NO_NOMBRE_PILA and not inicio_oracion:
                        es_persona = True
                # "Luján Gómez": apellido con mayúscula después
                if not es_persona and prox and prox.group(1)[0].isupper() and not prox.group(1).isupper():
                    if quitar_tildes(prox.group(1).lower()) not in _SUFIJOS_LUGAR and not v.isupper():
                        es_persona = True
                if es_persona:
                    salida = antes + "(persona)" + despues
    return salida


_RE_LA_PLATA_DINERO = re.compile(
    r"\b(?:con|sin|por|lavar|robar|robaron|robarse|robo|toda|esa|su|mi|dar|pagar|falta|devolver|"
    r"gastar|pedir|pide|piden|sacar|llevar|llevo|llevaron|quedarse|estafa\w*|cobr\w*|pon\w*)\s+la\s+plata\b"
    r"|\bla\s+plata\s+(?:de\s+(?:su|sus|mi|mis|los|las|un|una|la\s+gente|todos)|para\s+|que\s+)",
    re.IGNORECASE,
)


def enmascarar_falsos_lugares(texto: str) -> str:
    """Evita falsos positivos donde un nombre de partido se usa como sustantivo común.
    Ejemplo: 'lavar la plata', 'con la plata para un viaje' (dinero, NO la ciudad de La Plata)."""
    if not texto:
        return texto
    salida = _RE_LA_PLATA_DINERO.sub(
        lambda m: re.sub(r"\bla\s+plata\b", "(dinero)", m.group(0), flags=re.IGNORECASE),
        texto,
    )
    # Si el texto tiene mayúsculas (es texto normal, no todo minúsculas) y aparece exactamente
    # "la plata" en minúsculas (no "La Plata" ni "LA PLATA" ni "#laplata"), es dinero.
    if any(c.isupper() for c in salida):
        salida = re.sub(r"(?<![#\wÁÉÍÓÚÑáéíóúñ])la plata(?![\wÁÉÍÓÚÑáéíóúñ])", "(dinero)", salida)
    return salida


def quitar_nombres_no_geograficos(texto_norm: str) -> str:
    texto_norm = expandir_hashtags_lugar(texto_norm)
    for n in NOMBRES_NO_GEOGRAFICOS:
        texto_norm = re.sub(r"(?<![\wñ])" + re.escape(n) + r"(?![\wñ])", " ", texto_norm)
    # "barrio Ituzaingó", "barrio Simón Bolívar": es un barrio con ese nombre (muchas veces
    # de otra provincia), no el partido.
    global _RE_BARRIO_CON_NOMBRE_DE_PARTIDO
    if _RE_BARRIO_CON_NOMBRE_DE_PARTIDO is None:
        nombres = sorted((quitar_tildes(p.lower()) for p in PARTIDOS_PBA), key=len, reverse=True)
        alternativas = "|".join(re.escape(n) for n in nombres)
        _RE_BARRIO_CON_NOMBRE_DE_PARTIDO = re.compile(
            # "barrio Ituzaingó", "Parque Saavedra" (CABA), "Plaza Moreno" (La Plata),
            # "avenida Rivadavia", "calle Moreno"
            r"\b(?:barrio|bo\.|b°|parque|plaza|calle|avenida|av\.|pasaje)\s+(?:de\s+)?(?:[a-zñ]+\s+)?(?:" + alternativas + r")(?![\wñ])"
            # "Club Atlético Lanús", "Colegio San Martín", "Hospital Pilar" (sin "de")
            r"|\b(?:club|colegio|escuela|instituto|hospital|sanatorio)\s+(?:[a-zñ]+\s+)?(?:" + alternativas + r")(?![\wñ])"
        )
    return _RE_BARRIO_CON_NOMBRE_DE_PARTIDO.sub(" ", texto_norm)


_RE_BARRIO_CON_NOMBRE_DE_PARTIDO = None


def _lugares_por_hashtag() -> Dict[str, str]:
    lugares = {}
    for nombre in list(PARTIDOS_PBA) + list(LOCALIDADES_A_PARTIDO.keys()):
        clave = re.sub(r"[^a-zñ0-9]", "", quitar_tildes(nombre.lower()))
        lugares[clave] = quitar_tildes(nombre.lower())
    return lugares


_HASHTAGS_LUGAR: Dict[str, str] = {}


def expandir_hashtags_lugar(texto: str) -> str:
    """Convierte hashtags de lugar en el nombre del lugar: "#LaPlata" / "#laplata" →
    "la plata", "#LomasDeZamora" → "lomas de zamora". Las cuentas de noticias de
    Instagram suelen ubicar el hecho solo con el hashtag."""
    global _HASHTAGS_LUGAR
    if "#" not in (texto or ""):
        return texto
    if not _HASHTAGS_LUGAR:
        _HASHTAGS_LUGAR = _lugares_por_hashtag()

    def _reemplazo(m):
        clave = quitar_tildes(m.group(1).lower())
        return f" {_HASHTAGS_LUGAR[clave]} " if clave in _HASHTAGS_LUGAR else m.group(0)

    return re.sub(r"#([A-Za-zÁÉÍÓÚÑáéíóúñ0-9]+)", _reemplazo, texto)

# ---------------------------------------------------------------------------
# FILTROS DE TEMAS QUE NO INTERESAN (editables)
# ---------------------------------------------------------------------------
# Meteorología: se descarta salvo que el texto hable de una protesta/reclamo concreto
# (ej. "vecinos cortan la ruta por falta de luz tras el temporal" SÍ pasa).
PATRONES_CLIMA: List[str] = [
    "el temporal", "un temporal", "feroz temporal", "fuerte temporal", "del temporal",
    "granizo", "granizada", "rafagas", "alerta amarilla", "alerta naranja",
    "alerta meteorologica", "alerta por tormentas", "alerta por lluvias", "smn",
    "servicio meteorologico", "pronostico", "tormenta", "tormentas", "lluvias intensas",
    "ciclogenesis", "ola de calor", "sensacion termica", "vientos fuertes",
    "lluvias", "lluvias aisladas", "chaparrones", "pronostico extendido", "temperaturas",
]

# Deportes y espectáculos: se descartan salvo que hablen de violencia o incidentes
# (ej. "balacera a la salida del partido" SÍ pasa).
# Efemérides y homenajes ("A 41 años de la muerte de..."): no son hechos del día, salvo
# que convoquen a una marcha o reclamo.
PATRONES_EFEMERIDES: List[str] = [
    "aniversario", "homenaje", "homenajearon", "conmemoracion", "conmemoro", "recordo su",
    "recordaron a", "a 10 anos", "a 20 anos", "a 30 anos", "a 40 anos", "a 50 anos",
    "1976", "dictadura militar", "golpe de estado", "memoria verdad y justicia",
]
PATRON_A_N_ANOS = re.compile(r"\ba \d{1,3} anos de\b")

PATRONES_DEPORTES_ESPECTACULOS: List[str] = [
    "basquet", "basquetbol", "liga nacional", "liga femenina", "torneo", "goleada", "golazo",
    "primera nacional", "primera b", "primera c", "hockey", "voley", "rugby", "fixture",
    "handball", "futsal", "campeonato", "medalla", "atletismo", "maraton", "seleccion argentina",
    "recital", "cartelera", "estreno", "espectaculo", "show en vivo", "festival de musica",
    "causa afa", "beligoy", "chiqui tapia", "marixa balli", "showmatch", "gran hermano",
    "intrusos", "farandula",
]
EXCEPCIONES_VIOLENCIA: List[str] = [
    "incidentes", "barra", "barras", "barrabrava", "balacera", "tiros", "heridos", "herido",
    "muerto", "asesinado", "apunalado", "detenidos", "represion", "disturbios",
]

# Avisos clasificados, permutas, búsquedas laborales, ventas: siempre se descartan.
PATRONES_CLASIFICADOS: List[str] = [
    "permuta", "permutas", "vendo ", "se vende", "alquilo", "alquiler de",
    "busco trabajo", "busco empleo", "preparador fisico", "precio:", "sorteo",
    "consulto precio", "envios a todo el pais", "punto de entrega", "cronograma de entregas",
    "entregas entrada", "ayuda para recuperar", "bicicleta robada", "bici robada",
    "empleo a nivel nacional", "sobre el islam",
]

# Cuentas/fuentes que no se quieren nunca en el reporte (se busca en autor y título).
FUENTES_BLOQUEADAS: List[str] = [
    "polymarket", "apuestas", "casino", "bet365", "codere",
]

# Palabras que indican un conflicto/reclamo concreto (habilitan clima y sirven como
# relevancia mínima para publicaciones que no matchean el diccionario).
SENALES_CONFLICTO: List[str] = [
    "reclamo", "reclaman", "reclamamos", "reclamando", "denuncia", "denuncian",
    "protesta", "protestan", "marcha", "movilizacion", "corte de calle", "corte de ruta",
    "cortan", "cortaron", "piquete", "cacerolazo", "ruidazo", "asamblea",
    "autoconvocados", "autoconvocadas", "quema de gomas", "escrache",
    "robo", "robaron", "roban", "asalto", "asaltaron", "entradera", "entraderas",
    "motochorro", "motochorros", "tiros", "balacera", "baleado", "baleada", "disparos",
    "homicidio", "asesinato", "asesinaron", "mataron", "femicidio", "desaparecido",
    "desaparecida", "secuestro", "abuso", "violencia", "inseguridad", "narco",
    "narcotrafico", "bunker", "usurpacion", "toma de tierras", "desalojo",
    "sin luz", "sin agua", "despidos", "paro", "estafa", "zona liberada",
    "justicia por", "piden justicia", "hartos", "abandonados", "basta de",
    "saqueo", "saqueos", "intento de saqueo", "intentos de saqueo", "saquear", "saquearon", "saquean",
    # Reclamos policiales internos
    "sueldo", "sueldos", "salario", "salarial", "acuartelamiento", "acuartelados",
    "sumario", "desafectado", "desafectaron", "traslado compulsivo", "horas cores",
    "polad", "recargo", "francos", "ioma", "policia herido", "efectivo herido",
    "murio un policia", "policia muerto",
    # Hechos policiales / violencia (con conjugaciones: los títulos dicen "denunció", "asesinar")
    "denuncio", "denunciaron", "matar", "mato", "asesinar", "asesinado", "asesinada",
    "complot", "atentado", "atentaron", "amenaza", "amenazas", "amenazo", "amenazaron",
    "amenazado", "sicario", "sicarios", "tiroteo", "balearon", "baleo", "apunalado",
    "apuñalado", "acuchillado", "intento de homicidio", "crimen", "homicida", "arma",
    "armas", "allanamiento", "allanamientos", "allanaron", "detenido", "detenidos",
    "detenida", "detuvieron", "secuestraron", "extorsion", "extorsionaban", "toma de rehenes",
    "balazos", "narcomenudeo", "narcos", "banda narco", "enfrentamiento", "arma de fuego",
]

# Ataques o amenazas contra autoridades: siempre se consideran EN ALERTA.
# Ej: "plan para matar al intendente", "atentado contra el comisario", "amenazas al concejal".
# El verbo tiene que ir seguido de "al / a la / contra el..." + el cargo, para no confundir
# con "el intendente amenazó con..." o "el plan de obras del intendente".
PATRON_ATAQUE_AUTORIDAD = re.compile(
    r"\b(matar|asesinar|asesinato|atentado|atentar|balear|balearon|disparar|dispararon|amenaz\w*)\b"
    r"\s+(?:\w+\s+){0,2}?(al|a la|contra el|contra la|a un|a una|a los|a las|contra)\s+"
    r"(intendent[ea]s?|concejal\w*|comisari[oa]s?|diputad[oa]s?|senador\w*|gobernador\w*|ministr[oa]s?|"
    r"juez|jueza|jueces|fiscal\w*|funcionari[oa]s?|jefe de policia|jefa de policia)\b"
)


def es_ataque_a_autoridad(texto: str) -> bool:
    return bool(PATRON_ATAQUE_AUTORIDAD.search(quitar_tildes((texto or "").lower())))

# Cuentas de Instagram que se revisan en CADA corrida (sus últimas publicaciones y
# comentarios). Agregá acá las cuentas de noticias locales que seguís, sin "@".
# También se pueden sumar desde el .env: TERMOMETRO_CUENTAS_IG=cuenta1,cuenta2
CUENTAS_INSTAGRAM: List[str] = [
    "hechosyderecho",
]
CUENTAS_INSTAGRAM += [
    c.strip().lstrip("@") for c in os.getenv("TERMOMETRO_CUENTAS_IG", "").split(",")
    if c.strip() and c.strip().lstrip("@") not in CUENTAS_INSTAGRAM
]
MAX_POSTS_POR_CUENTA_IG: int = int(os.getenv("TERMOMETRO_POSTS_POR_CUENTA_IG", "3"))

# Antigüedad máxima (en horas) de una publicación para considerarla vigente.
# 24 h = solo noticias del día (antes 72 h: se colaban notas de 3 días atrás).
MAX_HORAS_ANTIGUEDAD: int = int(os.getenv("TERMOMETRO_MAX_HORAS", "24"))
# Si es 1, una publicación sin fecha legible se descarta (antes quedaba como
# "Fecha no verificada" y así entraban posteos viejos). Poner 0 para conservarlas.
EXIGIR_FECHA_VERIFICADA: bool = os.getenv("TERMOMETRO_EXIGIR_FECHA", "0") == "1"

# ---------------------------------------------------------------------------
# IMPORTANCIA DE UN HECHO (editable)
# ---------------------------------------------------------------------------
# Puntaje de "repercusión" = réplicas en fuentes distintas + comentarios + compartidos.
# Se suman los puntos del escalón más alto alcanzado en cada fila.
PUNTOS_FUENTES_DISTINTAS: List[Tuple[int, int]] = [  # (mínimo de fuentes, puntos)
    (2, 15), (3, 30), (4, 45), (5, 50), (8, 65),
]
PUNTOS_COMENTARIOS: List[Tuple[int, int]] = [  # (mínimo de comentarios, puntos)
    (30, 10), (100, 20), (300, 30), (1000, 45),
]
PUNTOS_COMPARTIDOS: List[Tuple[int, int]] = [  # (mínimo de compartidos/reposts, puntos)
    (50, 10), (300, 20), (1000, 30),
]
# Umbrales de repercusión
REPERCUSION_MEDIA: int = 25   # ej: 3 fuentes distintas, o 1000 comentarios
REPERCUSION_ALTA: int = 50    # ej: 5 medios distintos, 3 fuentes + 100 comentarios, o 4 fuentes + 30 comentarios
# Ventana (horas) para buscar la misma noticia en otras fuentes al armar cada edición
HORAS_VENTANA_REPLICAS: int = int(os.getenv("TERMOMETRO_HORAS_REPLICAS", "24"))


def parsear_numero_red(texto: str) -> int:
    """Convierte contadores de redes a número: "245", "1.234", "1,2 mil", "3,4 k", "2 M"."""
    if not texto:
        return 0
    t = quitar_tildes(str(texto).lower()).replace("\xa0", " ").strip()
    m = re.search(r"(\d[\d.,]*)\s*(mil|k|mill|millones|m)?\b", t)
    if not m:
        return 0
    num, suf = m.group(1), m.group(2) or ""
    mult = 1
    if suf in ("mil", "k"):
        mult = 1000
    elif suf in ("m", "mill", "millones"):
        mult = 1_000_000
    if mult > 1:
        valor = float(num.replace(".", "").replace(",", ".")) if "," in num else float(num)
    else:
        valor = float(num.replace(".", "").replace(",", ""))
    return int(round(valor * mult))

# Anclajes geográficos generales de 1ra pasada
ANCLAJES_GENERALES_PBA: List[str] = [
    "provincia de Buenos Aires",
    "bonaerense",
    "conurbano"
]

# Categorías iniciales de palabras clave
CATEGORIAS_BASE: Dict[str, Dict[str, object]] = {
    "seguridad": {
        "nombre": "Reclamos de seguridad",
        "color": "#ef4444",
        "icono": "shield-alert",
        "terminos": [
            "inseguridad", "insegurida", "marcha por seguridad", "reclamo de seguridad",
            "pedimos seguridad", "queremos seguridad", "basta de inseguridad",
            "nos están matando", "vecinos autoconvocados por seguridad",
            "corte por seguridad", "ruidazo por seguridad", "asamblea vecinal seguridad",
            "vecinos en alerta por robos", "frente a la comisaría reclamo",
            "zona liberada", "más patrullajes", "garita", "gendarmería pedido",
            "búnker narco", "balacera", "escrache comisaria", "lo agarraron los vecinos",
            "justicia por mano propia", "linchamiento", "lo lincharon",
            "le quemaron la casa al ladron", "pueblada por seguridad", "entraderas",
            "motochorros", "robo a mano armada", "tiraron a matar", "alarma vecinal",
            "saqueo", "saqueos", "intento de saqueo", "intentos de saqueo", "saquear", "saquearon"
        ]
    },
    "justicia": {
        "nombre": "Reclamos de justicia",
        "color": "#a855f7",
        "icono": "scale",
        "terminos": [
            "justicia por", "justicia x", "#JusticiaPor", "pedido de justicia",
            "piden justicia", "marcha de silencio", "marcha de antorchas",
            "marcha de velas", "caravana por justicia", "suelta de globos",
            "que no quede impune", "cárcel común", "familiares piden justicia",
            "fiscalía reclamo", "liberaron al asesino", "femicidio",
            "atropellado reclamo", "picada mortal justicia", "asesinato de"
        ]
    },
    "sociales_servicios": {
        "nombre": "Reclamos sociales y servicios",
        "color": "#f59e0b",
        "icono": "zap-off",
        "terminos": [
            "sin luz", "corte de luz", "sin agua", "baja presión",
            "Edenor", "Edesur", "Edelap", "EDEA", "Edes", "AySA", "ABSA",
            "cooperativa eléctrica", "corte de ruta", "corte de autopista",
            "piquete", "acampe", "despidos", "cierre de fábrica", "paro",
            "defensa de puestos de trabajo", "puestos de trabajo", "conflicto laboral",
            "asamblea de trabajadores", "toma de tierras", "usurpación", "desalojo",
            "sin colectivos", "paro de colectivos", "UTA", "olla popular",
            "jubilados autoconvocados", "sin recolección", "inundación",
            "calles intransitables", "reclamo de vecinos por luz", "reclamo por agua",
            "falta de luz", "cuadrillas de edesur", "transformador quemado"
        ]
    },
    "eventos_no_autorizados": {
        "nombre": "Eventos masivos no autorizados",
        "color": "#ec4899",
        "icono": "flame",
        "terminos": [
            "picada ilegal", "picadas ilegales", "juntada de motos", "motoqueada",
            "caravana de motos", "rodada clandestina", "haciendo willy", "wheelie",
            "fiesta clandestina", "fiesta sin habilitación", "previa clandestina",
            "se viene la juntada clandestina"
        ]
    },
    "imagen_institucional": {
        "nombre": "Imagen institucional y denuncias policiales",
        "color": "#3b82f6",
        "icono": "siren",
        "terminos": [
            "violencia policial", "abuso policial", "gatillo fácil",
            "policía golpeó", "video policía golpeando", "comisaría denuncia coimas",
            "detención arbitraria", "Asuntos Internos desafectado",
            "policía involucrado en robo", "patrullero atropelló"
        ]
    }
}

# Modificadores de convocatoria
MODIFICADORES_CONVOCATORIA: List[str] = [
    "nos juntamos", "nos vemos", "convocamos", "te esperamos", "sumate",
    "vamos todos", "punto de encuentro", "difundir", "compartan",
    "mañana a las", "este sábado", "hs", "flyer", "este viernes",
    "este domingo", "hoy a las", "concentramos", "corte total", "cacerolazo",
    "corte de autopista", "quema de gomas"
]

# Hashtags base
HASHTAGS_BASE: List[str] = [
    "#JusticiaPor",
    "#InseguridadEn",
    "#VecinosEnAlerta",
    "#BastaDeInseguridad",
    "#CorteDeLuz"
]

ABREVIATURAS_MAP: Dict[str, List[str]] = {
    "por": ["x"],
    "que": ["q", "k"],
    "porque": ["xq", "xk"],
    "inseguridad": ["insegurida"],
    "justicia por": ["justicia x", "#JusticiaPor"],
    "que no quede impune": ["q no quede impune"]
}

# Exclusiones geográficas estrictas (CABA, otras provincias y barrios porteños)
EXCLUSIONES_CABA: List[str] = [
    "CABA", "Ciudad Autónoma de Buenos Aires", "Capital Federal",
    "Policía de la Ciudad", "Gobierno de la Ciudad", "GCBA", "Jorge Macri",
    "Palermo", "Recoleta", "Belgrano", "Caballito", "Villa Urquiza",
    "Villa Crespo", "Almagro", "Balvanera", "San Telmo", "Puerto Madero",
    "Colegiales", "Chacarita", "Boedo", "Parque Patricios", "Lugano",
    "Mataderos", "Devoto", "Saavedra CABA", "Núñez", "Nunez", "Barracas",
    "Constitución CABA", "Retiro CABA", "Comuna 1", "Comuna 2", "Comuna 3",
    "Comuna 4", "Comuna 5", "Comuna 6", "Comuna 7", "Comuna 8", "Comuna 9",
    "Comuna 10", "Comuna 11", "Comuna 12", "Comuna 13", "Comuna 14", "Comuna 15"
]

EXCLUSIONES_PROVINCIAS: List[str] = [
    "Córdoba Capital", "Provincia de Córdoba", "Rosario", "Santa Fe Capital",
    "Provincia de Santa Fe", "Mendoza", "Tucumán", "Salta", "Jujuy",
    "Neuquén", "Río Negro", "Chubut", "Santa Cruz", "Tierra del Fuego",
    "Entre Ríos", "Paraná", "Corrientes", "Misiones", "Posadas", "Chaco",
    "Resistencia", "Formosa", "Santiago del Estero", "Catamarca", "La Rioja",
    "San Juan", "San Luis", "La Pampa", "Córdoba", "Cordoba",
    "Luján de Cuyo", "Juan José Castelli", "MisionesOnline", "Mendoza Today",
    "Radio Sudamericana", "Diario UNO", "Los Andes", "Trelew", "Bariloche",
    "Ushuaia", "Comodoro Rivadavia", "Río Cuarto", "Villa María", "San Rafael",
    "Godoy Cruz", "Guaymallén", "Las Heras Mendoza", "Maipú Mendoza",
]

EXCLUSIONES_INTERNACIONALES: List[str] = [
    # Países y gentilicios
    "españa", "espana", "español", "española",
    "colombia", "colombiano", "colombiana",
    "mexico", "méxico", "mexicano", "mexicana",
    "chile", "chileno", "chilena",
    "peru", "perú", "peruano", "peruana",
    "estados unidos", "eeuu", "usa", "estadounidense",
    "venezuela", "venezolano", "venezolana",
    "uruguay", "uruguayo", "uruguaya",
    "paraguay", "paraguayo", "paraguaya",
    "ecuador", "ecuatoriano", "ecuatoriana",
    "bolivia", "boliviano", "boliviana",
    "brasil", "brasileño", "brasileña",
    "honduras", "guatemala", "el salvador", "nicaragua", "costa rica",
    "panama", "panamá", "republica dominicana", "república dominicana",
    "puerto rico", "cuba",
    # España
    "madrid", "barcelona", "sevilla", "andalucia", "cataluña", "cataluna",
    "galicia", "asturias", "bilbao", "malaga", "málaga", "zaragoza", "murcia",
    "alicante", "cadiz", "cádiz", "guardia civil", "mossos", "ertzaintza",
    "moron de la frontera", "san vicente del raspeig",
    # México (estados, ciudades, instituciones, medios y léxico policial)
    "cdmx", "ciudad de mexico", "sinaloa", "baja california", "quintana roo", "nayarit",
    "tepic", "cancun", "cancún", "guadalajara", "monterrey", "tijuana", "jalisco",
    "veracruz", "hermosillo", "chihuahua", "oaxaca", "puebla", "guanajuato", "michoacan",
    "michoacán", "tamaulipas", "yucatan", "yucatán", "chiapas", "coahuila",
    "durango", "morelos", "queretaro", "querétaro", "san luis potosi",
    "tabasco", "tlaxcala", "zacatecas", "aguascalientes", "campeche", "colima",
    "mexicali", "mazatlan", "mazatlán", "culiacan", "culiacán", "acapulco",
    "valle de la trinidad", "ensenada bc", "ensenada, bc", "dolores hidalgo",
    "infonavit", "supermanzana", "beca benito juarez", "alcaldia benito juarez",
    "catean", "cateo", "catearon", "aseguramiento de arma", "aseguran fusiles",
    "guardia nacional", "azteca quintana roo", "el mexicano", "semanario zeta",
    "golpe politico", "nayarit noticias", "colosio",
    # Colombia
    "bogota", "bogotá", "medellin", "medellín", "cali", "bucaramanga", "barrancabermeja",
    "barranquilla", "cartagena", "cucuta", "cúcuta", "pereira", "manizales", "santa marta",
    "ibague", "ibagué", "villavicencio", "monteria", "montería", "neiva",
    "popayan", "popayán", "valledupar", "sincelejo", "tunja", "antioquia", "cundinamarca",
    "tolima", "huila", "caldas", "risaralda", "quindio", "quindío", "narino", "nariño",
    "cauca", "rio magdalena", "río magdalena", "caracol radio", "q'hubo", "qhubo",
    "el tiempo colombia", "el espectador", "sector la campana", "san vicente del caguan",
    # Perú
    "lima peru", "lima, peru", "arequipa", "trujillo", "chiclayo", "piura", "cusco", "cuzco",
    "iquitos", "huancayo", "tacna", "callao", "magdalena del mar", "pueblo libre",
    "miraflores", "san borja", "surco", "rpp noticias", "serenazgo",
    # Uruguay
    "montevideo", "paysandu", "paysandú", "punta del este", "canelones",
    "tacuarembo", "tacuarembó", "soriano", "agesor", "avaluado", "avaluada",
    # Chile, Venezuela, EEUU, otros
    "santiago de chile", "valparaiso", "valparaíso", "concepcion", "concepción",
    "antofagasta", "temuco", "vina del mar", "viña del mar", "carabineros",
    "caracas", "maracaibo", "barquisimeto", "asuncion", "asunción",
    "quito", "guayaquil", "cuenca", "cochabamba", "santa cruz de la sierra",
    "tegucigalpa", "san salvador", "managua", "santo domingo", "la habana",
    "sao paulo", "rio de janeiro",
    "texas", "miami", "new york", "california",
]

# Dominios de países extranjeros: si la URL pertenece a alguno de estos TLDs o medios
# extranjeros conocidos, se descarta automáticamente.
DOMINIOS_EXTRANJEROS_TLD: Tuple[str, ...] = (
    ".mx", ".co", ".pe", ".uy", ".cl", ".es", ".ve", ".ec", ".bo", ".py",
    ".cr", ".gt", ".hn", ".sv", ".ni", ".do", ".pa", ".br", ".cu", ".pr",
    ".us", ".uk", ".fr", ".it", ".de", ".pt",
)

DOMINIOS_EXTRANJEROS_CONOCIDOS: Tuple[str, ...] = (
    "lineadirectaportal.com", "golpepolitico.com", "zetatijuana.com", "elimparcial.com",
    "eluniversal.com.mx", "milenio.com", "excelsior.com.mx", "nmas.com.mx",
    "eltiempo.com", "elespectador.com", "qhubobucaramanga.com", "caracol.com.co",
    "rpp.pe", "elcomercio.pe", "agesor.com.uy", "elobservador.com.uy",
    "montevideo.com.uy", "elpais.com.uy", "subrayado.com.uy", "emol.com",
    "biobiochile.cl", "latercera.com", "elmundo.es", "elpais.com",
)


def es_url_extranjera(url: str) -> bool:
    """Devuelve True si la URL apunta a un dominio de otro país (no .ar ni redes globales)."""
    if not url:
        return False
    import urllib.parse
    try:
        host = (urllib.parse.urlparse(url).netloc or "").lower().split(":")[0]
    except Exception:
        return False
    if not host or host.endswith(".ar"):
        return False
    # Redes sociales y Google Noticias son globales: se filtran por contenido, no por TLD
    if any(g in host for g in ("facebook.com", "x.com", "twitter.com", "instagram.com", "news.google.com", "youtube.com", "tiktok.com")):
        return False
    if any(host == d or host.endswith("." + d) for d in DOMINIOS_EXTRANJEROS_CONOCIDOS):
        return True
    if any(host.endswith(tld) for tld in DOMINIOS_EXTRANJEROS_TLD):
        return True
    return False

PALABRAS_INGLES_FLAG: List[str] = [
    "translated from", "show original", "the ", "of the", "with the",
    "was ", "were ", "they ", "that ", "this ", "have been",
    "road safety", "hazard", "hospitalized", "crash", "police said", "killed in"
]

# Filtros de no-conflictividad / ruido institucional / autopromoción municipal
PATRONES_RUIDO_NO_CONFLICTIVIDAD: List[str] = [
    "el distrito mas seguro",
    "el distrito más seguro",
    "municipio mas seguro",
    "municipio más seguro",
    "reconocimiento a la gestion",
    "reconocimiento a la gestión",
    "incorporacion de patrulleros",
    "incorporación de patrulleros",
    "inauguracion de destacamento",
    "inauguración de destacamento",
    "reunion de fiscales",
    "reunión de fiscales",
    "flf-iap",
    "operativo sol",
    "drones en la ruta",
    "drones de seguridad vial",
    "control vehicular de rutina",
    "gestion municipal modelo",
    "gestión municipal modelo",
    "jornada de capacitacion policial",
    "capacitación policial",
    "balance de gestion positivo",
    "balance de gestión",
    "obras de iluminacion led terminadas",
    "asamblea anual", "asamblea ordinaria", "asamblea extraordinaria",
    "convocatoria a asamblea", "convocatorias a asamblea", "asamblea general ordinaria",
]

# Stopwords en español
STOPWORDS_ES: Set[str] = {
    "el", "la", "los", "las", "un", "una", "unos", "unas", "de", "del", "al",
    "a", "en", "con", "por", "para", "sin", "sobre", "entre", "hacia", "hasta",
    "desde", "que", "q", "xq", "como", "cuando", "donde", "quien", "cual",
    "y", "e", "o", "u", "ni", "pero", "mas", "sino", "porque", "pues", "si",
    "no", "ya", "muy", "más", "menos", "tan", "tanto", "todo", "toda",
    "todos", "todas", "otro", "otra", "otros", "otras", "mismo", "misma",
    "este", "esta", "estos", "estas", "ese", "esa", "esos", "esas", "aquel",
    "aquella", "mi", "mis", "tu", "tus", "su", "sus", "nuestro", "nuestra",
    "fue", "fueron", "era", "eran", "son", "es", "está", "están",
    "hay", "habia", "había", "hacer", "hizo", "hace", "hacen",
    "tiene", "tienen", "tuvo", "puede", "pueden", "hoy", "ayer", "mañana",
    "dia", "día", "dias", "días", "hora", "horas", "año", "años",
    "vecino", "vecinos", "vecina", "vecinas", "barrio", "partido", "municipio",
    "calle", "calles", "provincia", "buenos", "aires", "bonaerense", "conurbano",
    "facebook", "post", "video", "foto", "fotos", "compartir", "ver", "nota",
    "noticias", "diario", "info", "hola", "gente", "alguien", "sabe", "favor"
}

# Palabras que suelen filtrarse como falsos nombres de personas (figuras)
DESCARTE_FIGURAS_NOMBRES: Set[str] = {
    "núñez", "nunez", "palermo", "belgrano", "quilmes", "sarandí", "sarandi",
    "bernal", "la plata", "avellaneda", "lanús", "lanus", "buenos aires",
    "conurbano", "policía", "policia", "comisaría", "comisaria", "edesur",
    "edenor", "aysa", "autopista", "ruta", "fiscalía", "fiscalia", "intendente",
    "vicente lopez", "vicente lópez", "operativo sol", "tribunales", "gobierno",
    "bertulazzi", "policia de la ciudad", "iap"
}


def es_texto_espanol(texto: str) -> bool:
    t_low = texto.lower()
    for flag in PALABRAS_INGLES_FLAG:
        if flag in t_low:
            return False
    palabras = t_low.split()
    es_count = sum(1 for p in palabras if p in {
        "de", "la", "el", "en", "y", "a", "los", "se", "del", "las", "por", "un", "para",
        "con", "no", "una", "su", "al", "lo", "mas", "más", "pero", "sus", "fue", "este",
        "esta", "está", "son", "vecinos", "policía", "policia", "barrio", "robo", "seguridad"
    })
    if len(palabras) >= 6 and es_count == 0:
        return False
    return True


def quitar_tildes(texto: str) -> str:
    """Devuelve la versión sin tildes (conservando la ñ)."""
    protegido = texto.replace("ñ", "\x01").replace("Ñ", "\x02")
    normalizado = unicodedata.normalize("NFD", protegido)
    sin_acento = "".join(c for c in normalizado if unicodedata.category(c) != "Mn")
    return sin_acento.replace("\x01", "ñ").replace("\x02", "Ñ")


def generar_variantes_termino(termino: str) -> List[str]:
    variantes: List[str] = [termino]
    sin_tilde = quitar_tildes(termino)
    if sin_tilde != termino and sin_tilde not in variantes:
        variantes.append(sin_tilde)

    t_lower = termino.lower()
    if t_lower in ABREVIATURAS_MAP:
        for v in ABREVIATURAS_MAP[t_lower]:
            if v not in variantes:
                variantes.append(v)

    if " por " in t_lower:
        var_x = t_lower.replace(" por ", " x ")
        if var_x not in variantes:
            variantes.append(var_x)

    if "que " in t_lower:
        var_q = t_lower.replace("que ", "q ")
        if var_q not in variantes:
            variantes.append(var_q)

    return variantes


_SENALES_GREMIALES = (
    "suteba", "ate", "cgt", "cta", "catt", "gremio", "gremial", "sindicato", "sindical",
    "docentes", "trabajadores", "paro", "salario", "salarios", "paritaria", "paritarias",
    "despidos", "reclamo", "conflicto laboral", "puestos de trabajo", "movilizacion",
)


def es_ruido_o_no_conflictividad(texto: str) -> Tuple[bool, str]:
    """
    Detecta si una publicación es autopromoción municipal, gacetilla institucional
    o un hecho de CABA/rutina que no representa conflictividad ni reclamo vecinal.
    """
    t_norm = quitar_tildes(texto.lower())

    if "bertulazzi" in t_norm:
        return True, "Descartado: Caso de fuga ocurrido en CABA (Comuna porteña)"

    # Solo descartar por "policía de la ciudad" si el hecho NO ocurrió en un partido/localidad de PBA
    # (ej. un policía de la Ciudad baleado en Virrey del Pino, La Matanza SÍ es jurisdicción PBA).
    if "parque chacabuco" in t_norm or "comisaria de la ciudad" in t_norm or "policia de la ciudad" in t_norm:
        t_geo = quitar_nombres_no_geograficos(t_norm)
        tiene_lugar_pba = bool(_buscar_localidad(t_geo)) or any(
            len(p) > 3 and contiene_frase(t_geo, p) for p in PARTIDOS_PBA
        )
        if not tiene_lugar_pba:
            return True, "Descartado: Hecho en jurisdicción CABA"

    es_actividad_gremial = any(contiene_frase(t_norm, g) for g in _SENALES_GREMIALES)
    for patron in PATRONES_RUIDO_NO_CONFLICTIVIDAD:
        p_norm = quitar_tildes(patron.lower())
        if "asamblea" in p_norm and es_actividad_gremial:
            continue
        if contiene_frase(t_norm, p_norm):
            return True, f"Descartado: Noticia institucional / autopromoción municipal ('{patron}')"

    return False, ""


def es_exclusion_geografica(texto: str, partido_objetivo: str = "", url: str = "") -> bool:
    """
    Evalúa si un texto corresponde a CABA, otra provincia o país, o no pertenece a PBA.
    Retorna True si debe ser DESCARTADO.
    """
    if url and es_url_extranjera(url):
        return True

    if not es_texto_espanol(texto):
        return True

    texto = enmascarar_falsos_lugares(enmascarar_personas(texto))
    t_lower = texto.lower()
    t_norm_exc = quitar_tildes(t_lower)

    # Descartar países y ciudades extranjeras (palabra completa, inmune a paréntesis/comas/tildes)
    for inter in EXCLUSIONES_INTERNACIONALES:
        inter_norm = quitar_tildes(inter.lower())
        if contiene_frase(t_norm_exc, inter_norm) or f"/{inter_norm}" in t_norm_exc or f"#{inter_norm}" in t_norm_exc:
            return True

    # Verificar si menciona exclusiones de CABA o provincias
    menciona_otra_provincia_o_caba = False
    for exc in EXCLUSIONES_CABA + EXCLUSIONES_PROVINCIAS:
        if contiene_frase(t_norm_exc, exc) or ("@" in t_lower and quitar_tildes(exc.lower()) in t_norm_exc):
            menciona_otra_provincia_o_caba = True
            break

    # Verificar anclajes positivos explícitos de PBA (siempre por palabra completa:
    # antes "Salto" matcheaba dentro de "asalto" y "Pilar" dentro de "pilares").
    t_norm = quitar_nombres_no_geograficos(quitar_tildes(t_lower))
    tiene_anclaje_pba = False

    def _partido_sirve(p: str) -> bool:
        if menciona_otra_provincia_o_caba and p in PARTIDOS_NOMBRE_COMPARTIDO:
            return False
        return contiene_frase(t_norm, p)

    if partido_objetivo and partido_objetivo.lower() != "provincia de buenos aires" and _partido_sirve(partido_objetivo):
        tiene_anclaje_pba = True
    else:
        if _buscar_localidad(t_norm):
            tiene_anclaje_pba = True

        if not tiene_anclaje_pba:
            for anclaje in ANCLAJES_GENERALES_PBA + ["pba", "zona sur", "zona oeste", "zona norte", "amba"]:
                if contiene_frase(t_norm, anclaje):
                    tiene_anclaje_pba = True
                    break

        if not tiene_anclaje_pba:
            for p in PARTIDOS_PBA:
                if len(p) > 3 and _partido_sirve(p):
                    tiene_anclaje_pba = True
                    break

    if menciona_otra_provincia_o_caba and not tiene_anclaje_pba:
        return True

    if not tiene_anclaje_pba:
        return True

    return False


def resolver_partido_geografico_preciso(texto: str, partido_sugerido: str = "") -> str:
    """
    Resuelve el partido bonaerense con máxima precisión geográfica:
    1. Si menciona 'Autopista Bs. As.-La Plata' junto con 'Sarandí' -> Avellaneda (NO La Plata).
    2. Si menciona 'Bernal' o 'Don Bosco' -> Quilmes (NO La Plata).
    3. Mapea localidades específicas (Sarandí, Bernal, Haedo, San Justo, Banfield, etc.) a su Partido real.
    4. Si no hay localidad, busca coincidencia exacta con los 135 partidos.
    """
    texto = enmascarar_falsos_lugares(enmascarar_personas(texto))
    t_norm = quitar_nombres_no_geograficos(quitar_tildes(texto.lower()))

    # Regla específica: Si es corte en Autopista Bs. As.-La Plata pero en Sarandí o Bernal
    if "autopista" in t_norm:
        if "sarandi" in t_norm:
            return "Avellaneda"
        if "bernal" in t_norm or "quilmes" in t_norm:
            return "Quilmes"
        if "wilde" in t_norm or "dock sud" in t_norm:
            return "Avellaneda"
        if "hudson" in t_norm:
            return "Berazategui"

    # Se elige la PRIMERA mención en el texto (antes ganaba el primer partido en orden
    # alfabético de la lista, sin importar dónde apareciera).
    candidatos: List[Tuple[int, str]] = []
    for loc, partido_real in LOCALIDADES_A_PARTIDO.items():
        pos = _posicion_localidad(t_norm, quitar_tildes(loc))
        if pos >= 0:
            candidatos.append((pos, partido_real))
    for partido in PARTIDOS_PBA:
        pos = posicion_frase(t_norm, partido)
        if pos >= 0:
            candidatos.append((pos, partido))
    if candidatos:
        candidatos.sort(key=lambda c: c[0])
        return candidatos[0][1]

    return partido_sugerido or "Provincia de Buenos Aires"


# ---------------------------------------------------------------------------
# Utilidades de texto
# ---------------------------------------------------------------------------

def posicion_frase(texto_norm: str, frase: str) -> int:
    """Posición de `frase` como palabra completa dentro de un texto ya normalizado
    (minúsculas, sin tildes). Devuelve -1 si no aparece."""
    f = quitar_tildes(frase.lower()).strip()
    if not f:
        return -1
    m = re.search(r"(?<![\wñ])" + re.escape(f) + r"(?![\wñ])", texto_norm)
    return m.start() if m else -1


def contiene_frase(texto_norm: str, frase: str) -> bool:
    return posicion_frase(texto_norm, frase) >= 0


def _posicion_localidad(t_norm: str, loc_norm: str) -> int:
    if loc_norm in LOCALIDADES_AMBIGUAS:
        m = re.search(
            r"(?:\ben|\bde|\bbarrio|\blocalidad de|\bzona de)\s+" + re.escape(loc_norm) + r"(?![\wñ])",
            t_norm,
        )
        return m.start() if m else -1
    return posicion_frase(t_norm, loc_norm)


def _buscar_localidad(t_norm: str) -> str:
    for loc, partido in LOCALIDADES_A_PARTIDO.items():
        if _posicion_localidad(t_norm, quitar_tildes(loc)) >= 0:
            return partido
    return ""


def texto_sin_comentarios(texto: str) -> str:
    """Devuelve solo el cuerpo de la publicación, sin los comentarios que el scraper
    concatena al final. Así el nombre de un comentarista ("Juancho Martínez") no
    termina ubicando la publicación en San Isidro."""
    if not texto:
        return ""
    for marca in ("\n\n💬", " [Comentarios:", "\n💬"):
        if marca in texto:
            texto = texto.split(marca, 1)[0]
    return texto


def es_tema_excluido(titulo: str, texto: str, autor: str = "") -> Tuple[bool, str]:
    """Descarta clima, clasificados y fuentes bloqueadas. Devuelve (excluir, motivo)."""
    cuerpo = quitar_tildes(f"{titulo} {texto_sin_comentarios(texto)}".lower())
    autor_norm = quitar_tildes((autor or "").lower())

    for f in FUENTES_BLOQUEADAS:
        if f in autor_norm or f in cuerpo:
            return True, f"Fuente bloqueada ({f})"

    for p in PATRONES_CLASIFICADOS:
        if contiene_frase(cuerpo, p.strip()) or (p.endswith(" ") and p in cuerpo):
            return True, f"Aviso / clasificado ('{p.strip()}')"

    if any(contiene_frase(cuerpo, p) for p in PATRONES_CLIMA):
        if not any(contiene_frase(cuerpo, s) for s in (
            "reclamo", "reclaman", "protesta", "corte de calle", "corte de ruta", "cortan",
            "cortaron", "piquete", "cacerolazo", "marcha", "asamblea", "autoconvocados",
        )):
            return True, "Meteorología / clima sin reclamo asociado"

    if PATRON_A_N_ANOS.search(cuerpo) or any(contiene_frase(cuerpo, p) for p in PATRONES_EFEMERIDES):
        if not any(contiene_frase(cuerpo, s) for s in ("marcha", "reclamo", "reclaman", "piden justicia", "convocan", "corte de", "protesta")):
            return True, "Efeméride / homenaje sin reclamo del día"

    if any(contiene_frase(cuerpo, p) for p in PATRONES_DEPORTES_ESPECTACULOS):
        if not any(contiene_frase(cuerpo, s) for s in EXCEPCIONES_VIOLENCIA):
            return True, "Deportes / espectáculos sin hechos de violencia"

    return False, ""


def tiene_senal_conflicto(texto: str) -> bool:
    t = quitar_tildes(texto_sin_comentarios(texto).lower())
    return any(contiene_frase(t, s) for s in SENALES_CONFLICTO)


# ---------------------------------------------------------------------------
# Fechas de publicación
# ---------------------------------------------------------------------------

_MESES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10,
    "noviembre": 11, "diciembre": 12,
    "ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6, "jul": 7,
    "ago": 8, "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dic": 12,
}

_UNIDADES_RELATIVAS = [
    (r"(?:min|mins|minuto|minutos|m)", "minutes"),
    (r"(?:h|hs|hora|horas)", "hours"),
    (r"(?:d|dia|dias)", "days"),
    (r"(?:sem|semana|semanas|w)", "weeks"),
    (r"(?:a|ano|anos|y)", "years"),
]


def parsear_fecha_publicacion(texto: str, ahora: Optional[datetime] = None) -> Optional[datetime]:
    """Interpreta las fechas que muestran Facebook / Instagram:
    "Justo ahora", "5 min", "3 h", "2 d", "1 sem", "337w", "hace 3 horas", "Ayer a las 20:15",
    "15 de octubre", "15 de octubre de 2024", "15 oct 2024".
    Devuelve None si no la puede interpretar (nunca asume "ahora")."""
    if not texto:
        return None
    ahora = ahora or datetime.now()
    t = quitar_tildes(texto.lower()).strip()
    t = re.sub(r"\s+", " ", t).replace("·", " ").strip()
    t = re.sub(r"^hace\s+", "", t)

    if t in ("justo ahora", "ahora", "just now", "un momento"):
        return ahora
    if t.startswith("ayer") or t.startswith("yesterday"):
        m_hora = re.search(r"(\d{1,2})[:.](\d{2})", t)
        ayer = ahora - timedelta(days=1)
        if m_hora:
            try:
                return ayer.replace(hour=int(m_hora.group(1)), minute=int(m_hora.group(2)), second=0, microsecond=0)
            except ValueError:
                pass
        # Sin hora explícita, "ayer" no debe descartarse por calendario a las 7 AM (< 24 h)
        return ahora - timedelta(hours=18)

    m = re.fullmatch(r"(\d{1,4})\s*([a-z]+)", t)
    if m:
        n = int(m.group(1))
        unidad = m.group(2)
        for patron, nombre in _UNIDADES_RELATIVAS:
            if re.fullmatch(patron, unidad):
                if nombre == "years":
                    return ahora - timedelta(days=365 * n)
                return ahora - timedelta(**{nombre: n})

    m = re.search(r"(\d{1,2})\s+(?:de\s+)?([a-z]+)\.?(?:\s+(?:de\s+)?(\d{4}))?(?:\s+a\s+las\s+(\d{1,2})[:.](\d{2}))?", t)
    if m and m.group(2) in _MESES:
        dia = int(m.group(1))
        mes = _MESES[m.group(2)]
        anio = int(m.group(3)) if m.group(3) else ahora.year
        try:
            if m.group(4) and m.group(5):
                fecha = datetime(anio, mes, dia, int(m.group(4)), int(m.group(5)))
            else:
                # Fecha sin hora: usar fin del día (tope ahora) para no descartar por fecha
                # calendario notas de ayer que tienen menos de 24 h reales.
                fecha = datetime(anio, mes, dia, 23, 59)
                if fecha > ahora and fecha.date() == ahora.date():
                    fecha = ahora
        except ValueError:
            return None
        if not m.group(3) and fecha > ahora + timedelta(days=1):
            fecha = fecha.replace(year=anio - 1)
        return fecha

    return None


_RE_FECHA_EN_TEXTO = re.compile(
    r"(?<![\w])(hace\s+(?:un|una|\d{1,3})\s*(?:min|mins|minutos?|h|hs|horas?|d|d[ií]as?|sem|semanas?)"
    r"|justo ahora"
    r"|ayer(?:\s+a\s+las\s+\d{1,2}[:.]\d{2})?"
    r"|\d{1,2}\s+de\s+(?:enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|setiembre|octubre|noviembre|diciembre)"
    r"(?:\s+de\s+\d{4})?(?:\s+a\s+las\s+\d{1,2}[:.]\d{2})?)(?![\w])",
    re.IGNORECASE,
)


def fecha_en_texto(texto: str, max_chars: int = 250) -> str:
    """Busca la fecha relativa que Facebook deja escrita al principio del texto de la
    tarjeta ("InfoBerisso Hace 21 horas EMERGENCIA..."). Devuelve el fragmento o ""."""
    if not texto:
        return ""
    inicio = texto[:max_chars]
    for m in _RE_FECHA_EN_TEXTO.finditer(inicio):
        frag = m.group(1)
        # "un"/"una" → 1
        frag_num = re.sub(r"(?i)\bhace\s+una?\b", "hace 1", frag)
        if parsear_fecha_publicacion(frag_num):
            return frag_num
    return ""


def quitar_fecha_del_texto(texto: str, fragmento: str) -> str:
    if not fragmento or not texto:
        return texto
    return re.sub(re.escape(fragmento), " ", texto, count=1, flags=re.IGNORECASE).replace("  ", " ").strip()


def fecha_desde_id_tweet(url: str) -> Optional[datetime]:
    """Las publicaciones de X llevan la fecha codificada en el ID (Snowflake)."""
    m = re.search(r"/status/(\d{15,20})", url or "")
    if not m:
        return None
    try:
        ms = (int(m.group(1)) >> 22) + 1288834974657
        return datetime.fromtimestamp(ms / 1000)
    except (ValueError, OSError, OverflowError):
        return None


def fecha_publicacion_iso(valor: str, url: str = "") -> Optional[datetime]:
    """Recupera la fecha real de un hallazgo: primero la guardada en ISO, si no la del
    ID de X. Devuelve None si no hay fecha confiable."""
    if valor:
        try:
            return datetime.fromisoformat(str(valor).strip()[:19])
        except ValueError:
            pass
    return fecha_desde_id_tweet(url)


def describir_fecha(fecha: Optional[datetime], ahora: Optional[datetime] = None) -> str:
    if not fecha:
        return "Fecha no verificada"
    ahora = ahora or datetime.now()
    horas = (ahora - fecha).total_seconds() / 3600
    if horas < 1:
        return "Hace menos de 1 h"
    if horas < 24:
        return f"Hace {int(horas)} h"
    return fecha.strftime("%d/%m/%Y %H:%M")


def resolver_todos_partidos_en_texto(texto: str, partido_sugerido: str = "") -> List[str]:
    """Devuelve todos los partidos de PBA mencionados en el texto (en orden de aparición,
    sin duplicados). Permite detectar hechos multiprovinciales/multidistrito como
    'cortes de AySA en Lomas, Echeverría y Ezeiza'."""
    texto_clean = enmascarar_falsos_lugares(enmascarar_personas(texto or ""))
    t_norm = quitar_nombres_no_geograficos(quitar_tildes(texto_clean.lower()))
    candidatos: List[Tuple[int, str]] = []
    for loc, partido_real in LOCALIDADES_A_PARTIDO.items():
        pos = _posicion_localidad(t_norm, quitar_tildes(loc))
        if pos >= 0:
            candidatos.append((pos, partido_real))
    for partido in PARTIDOS_PBA:
        pos = posicion_frase(t_norm, partido)
        if pos >= 0:
            candidatos.append((pos, partido))
    candidatos.sort(key=lambda c: c[0])
    vistos = []
    for _, p in candidatos:
        if p not in vistos:
            vistos.append(p)
    if not vistos and partido_sugerido and partido_sugerido != "Provincia de Buenos Aires":
        vistos.append(partido_sugerido)
    return vistos


_RE_IG_AUDIO_BASURA = re.compile(
    r"(?:Audio\s+original(?:\s+\d+){0,4}(?:\s+[a-zA-Z0-9_.]+)?)",
    re.IGNORECASE,
)
_RE_IG_HANDLE_TIEMPO = re.compile(
    r"^[a-zA-Z0-9_.]+\s*[•·]\s*\d+\s*(?:min|h|hs|d|sem|m|w)(?:\s+\d+\s+[a-zA-Z0-9_.]+)?\s*",
    re.IGNORECASE,
)
_RE_IG_TIEMPO_SUELTO = re.compile(
    r"\s*[•·]\s*\d+\s*(?:min|h|hs|d|sem|m|w)\b",
    re.IGNORECASE,
)


def limpiar_texto_basura_redes(texto: str) -> str:
    """Quita ruido típico del scrapeo de Instagram/redes ('Audio original 369 17 9 todonoticias',
    'inforbano • 7 min 3 inforbano', marcas '• 1 h' congeladas al momento del scrapeo)."""
    if not texto:
        return ""
    t = _RE_IG_AUDIO_BASURA.sub(" ", texto)
    t = _RE_IG_HANDLE_TIEMPO.sub("", t.strip())
    t = _RE_IG_TIEMPO_SUELTO.sub("", t)
    return re.sub(r"[ \t]{2,}", " ", t).strip()


def resolver_eje_tematico_preciso(texto: str, categoria_sugerida: str = "") -> str:
    """
    Resuelve el eje temático con prioridad clara:
    1. Hechos delictivos / homicidios / robos / detenciones -> seguridad (nunca sociales/laboral)
    2. Reclamos laborales o servicios públicos -> sociales_servicios
    3. Pedidos de justicia / femicidios -> justicia
    4. Picadas / clandestinas -> eventos_no_autorizados
    5. Violencia institucional -> imagen_institucional
    """
    t_norm = quitar_tildes(texto.lower())

    if any(contiene_frase(t_norm, k) for k in [
        "violencia policial", "gatillo facil", "policia golpeo", "asuntos internos", "abuso policial"
    ]):
        return "imagen_institucional"

    if any(contiene_frase(t_norm, k) for k in ["picadas", "juntada de motos", "fiesta clandestina"]):
        return "eventos_no_autorizados"

    if any(contiene_frase(t_norm, k) for k in [
        "justicia por", "#justiciapor", "femicidio", "piden justicia", "pedido de justicia",
        "marcha por justicia", "juicio por", "condena"
    ]):
        return "justicia"

    if any(contiene_frase(t_norm, k) for k in [
        "robo", "robaron", "asalto", "asaltaron", "entradera", "entraderas", "motochorro",
        "motochorros", "homicidio", "asesinaron", "mataron", "balacera", "tiroteo", "baleado",
        "baleada", "disparos", "tiros", "detuvieron", "delincuente", "delincuentes", "ladron",
        "ladrones", "saqueo", "saqueos", "narco", "narcotrafico", "cocaina", "arma de fuego",
        "inseguridad", "secuestro", "comerciante asesinado", "crimen de", "asesinato"
    ]):
        return "seguridad"

    if any(contiene_frase(t_norm, k) for k in [
        "puestos de trabajo", "conflicto laboral", "despidos", "fabrica", "gremio", "sindicato",
        "suteba", "paritaria", "cierre de planta", "sin luz", "falta de luz", "corte de luz",
        "edesur", "edenor", "edelap", "aysa", "absa", "sin agua", "baja presion",
        "colectivos", "uta", "cortes de agua"
    ]):
        return "sociales_servicios"

    return categoria_sugerida or "seguridad"


def es_url_publicacion_valida(url: str) -> bool:
    """
    Verifica que la URL lleve de manera inequívoca a una publicación, tweet, post
    o noticia directa, y NO a una página principal, feed, grupo, búsqueda o perfil.
    """
    if not url or not isinstance(url, str) or not url.startswith("http"):
        return False
    u = url.lower().strip()

    # Exclusiones de navegación o cuentas
    if u in [
        "https://www.facebook.com", "https://www.facebook.com/",
        "https://facebook.com", "https://facebook.com/",
        "https://www.instagram.com", "https://www.instagram.com/",
        "https://instagram.com", "https://instagram.com/",
        "https://x.com", "https://x.com/",
        "https://twitter.com", "https://twitter.com/"
    ]:
        return False

    if any(k in u for k in ["/search/", "/home.php", "/login", "/messages", "/notifications", "/hashtag/", "/stories/"]):
        return False

    # Excluir enlaces para compartir grupos completos
    if "/share/g/" in u:
        return False

    # Twitter / X: debe ser un tweet específico
    if "x.com" in u or "twitter.com" in u:
        return "/status/" in u

    # Instagram: debe ser post o reel
    if "instagram.com" in u:
        return "/p/" in u or "/reel/" in u

    # Facebook: debe ser publicación individual, foto, reel, video o share oficial de post
    if "facebook.com" in u or "fb.com" in u:
        if "/share/p/" in u or "/share/v/" in u or "/share/r/" in u:
            return True
        if "/photo/" in u or "/photo.php" in u or "fbid=" in u:
            return True
        if "/groups/" in u:
            return "/permalink/" in u or "/posts/" in u
        if any(k in u for k in ["/posts/", "/reel/", "/watch/?v=", "/videos/", "story_fbid=", "permalink.php"]):
            return True
        return False

    # Noticias o portales web externos (válidos)
    return True


def es_texto_basura_ui(autor: str, texto: str) -> bool:
    """
    Detecta si el texto o autor corresponde a elementos de la interfaz de usuario de Facebook
    (cajas de publicación, indicadores de chat en línea, carruseles de historias, etc.)
    en lugar de una publicación real de conflicto vecinal.
    """
    a = (autor or "").lower().strip()
    t = (texto or "").lower().strip()

    patrones = [
        "¿qué estás pensando", "que estas pensando", "estás pensando, gaston", "estas pensando",
        "crear una publicación", "crear publicacion", "indicador de estado", "estado online",
        "publicaciones del feed", "reels y videos cortos", "ordenar feed", "escribe un comentario",
        "detalles del grupo", "añadir a tu publicación", "compartir en tu perfil",
        "cambió su foto de portada", "actualizó su foto del perfil", "activo hace",
        "enviar mensaje", "precio:", "alquilo dpto", "vendo ropero",
        "giphy", "tenor", "sticker", "emoji", "en tu casa", "tenía la heladera vacía", "no alcanza ni para los remedios"
    ]
    if any(p in a for p in patrones):
        return True
    if any(p in t for p in patrones):
        return True
    if a in ["activo", "facebook", "desconocido", "usuario", "participante", "giphy", "tenor"]:
        if len(t) < 30 or any(p in t for p in patrones):
            return True
    return False

