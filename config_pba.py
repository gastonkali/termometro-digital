# -*- coding: utf-8 -*-
"""
Configuración maestra de Termómetro Digital (Provincia de Buenos Aires).
Incluye:
- Los 135 partidos oficiales de la Provincia de Buenos Aires.
- Diccionario base de palabras clave por categoría.
- Modificadores de convocatoria (para detectar eventos de agenda).
- Reglas de variantes sin tilde, abreviaturas y hashtags.
- Filtros de exclusión geográfica (CABA y otras provincias).
"""

import unicodedata
from typing import Dict, List, Set

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

# Partidos del Conurbano / AMBA Bonaerense (prioridad alta de volumen)
PARTIDOS_CONURBANO: List[str] = [
    "Almirante Brown", "Avellaneda", "Berazategui", "Berisso", "Cañuelas",
    "Ensenada", "Escobar", "Esteban Echeverría", "Ezeiza", "Florencio Varela",
    "General Rodríguez", "General San Martín", "Hurlingham", "Ituzaingó",
    "José C. Paz", "La Matanza", "La Plata", "Lanús", "Lomas de Zamora",
    "Malvinas Argentinas", "Marcos Paz", "Merlo", "Moreno", "Morón", "Pilar",
    "Presidente Perón", "Quilmes", "San Fernando", "San Isidro", "San Miguel",
    "San Vicente", "Tigre", "Tres de Febrero", "Vicente López", "Zárate"
]

# Anclajes geográficos generales de 1ra pasada
ANCLAJES_GENERALES_PBA: List[str] = [
    "provincia de Buenos Aires",
    "bonaerense",
    "conurbano"
]

# Categorías iniciales de palabras clave definidas por el usuario
CATEGORIAS_BASE: Dict[str, Dict[str, object]] = {
    "seguridad": {
        "nombre": "Reclamos de seguridad",
        "color": "#ef4444",
        "icono": "shield-alert",
        "terminos": [
            "inseguridad", "insegurida", "marcha por seguridad", "reclamo de seguridad",
            "pedimos seguridad", "queremos seguridad", "basta de inseguridad",
            "nos están matando", "vecinos autoconvocados", "vecinos se concentran",
            "vecinos cortaron", "corte de calle", "quema de cubiertas", "ruidazo",
            "cacerolazo", "asamblea vecinal", "vecinos en alerta", "frente a la comisaría",
            "zona liberada", "más patrullajes", "garita", "gendarmería", "búnker",
            "balacera", "escrache", "escracharon", "lo agarraron los vecinos",
            "justicia por mano propia", "linchamiento", "lo lincharon",
            "le quemaron la casa", "pueblada"
        ]
    },
    "justicia": {
        "nombre": "Reclamos de justicia",
        "color": "#a855f7",
        "icono": "scale",
        "terminos": [
            "justicia por", "justicia x", "#JusticiaPor", "pedido de justicia",
            "piden justicia", "marcha de silencio", "marcha de antorchas",
            "marcha de velas", "caravana por", "suelta de globos",
            "que no quede impune", "cárcel común", "familiares piden",
            "Tribunales", "fiscalía", "liberaron al", "femicidio",
            "atropellado", "picada mortal"
        ]
    },
    "sociales_servicios": {
        "nombre": "Reclamos sociales y servicios",
        "color": "#f59e0b",
        "icono": "zap-off",
        "terminos": [
            "sin luz", "corte de luz", "sin agua", "baja presión",
            "Edenor", "Edesur", "Edelap", "EDEA", "Edes", "AySA", "ABSA",
            "cooperativa eléctrica", "corte de ruta", "piquete", "acampe",
            "despidos", "cierre de fábrica", "paro", "asamblea de trabajadores",
            "toma de tierras", "usurpación", "desalojo", "sin colectivos",
            "UTA", "olla popular", "jubilados autoconvocados", "sin recolección",
            "inundación", "calles intransitables"
        ]
    },
    "eventos_no_autorizados": {
        "nombre": "Eventos masivos no autorizados",
        "color": "#ec4899",
        "icono": "flame",
        "terminos": [
            "picada", "picadas", "juntada de motos", "motoqueada",
            "caravana de motos", "rodada", "willy", "wheelie",
            "fiesta clandestina", "fiesta sin habilitación", "previa",
            "se viene la juntada"
        ]
    },
    "imagen_institucional": {
        "nombre": "Imagen institucional",
        "color": "#3b82f6",
        "icono": "siren",
        "terminos": [
            "violencia policial", "abuso policial", "gatillo fácil",
            "policía golpeó", "video policía", "patrullero", "bonaerense",
            "comisaría denuncia", "detención arbitraria", "Asuntos Internos",
            "desafectado"
        ]
    }
}

# Modificadores de convocatoria (para alimentar la Agenda de protestas/eventos)
MODIFICADORES_CONVOCATORIA: List[str] = [
    "nos juntamos", "nos vemos", "convocamos", "te esperamos", "sumate",
    "vamos todos", "punto de encuentro", "difundir", "compartan",
    "mañana a las", "este sábado", "hs", "flyer", "este viernes",
    "este domingo", "hoy a las", "concentramos"
]

# Hashtags y variantes ortográficas/abreviadas frecuentes
HASHTAGS_BASE: List[str] = [
    "#JusticiaPor",
    "#InseguridadEn",
    "#VecinosEnAlerta",
    "#BastaDeInseguridad"
]

ABREVIATURAS_MAP: Dict[str, List[str]] = {
    "por": ["x"],
    "que": ["q", "k"],
    "porque": ["xq", "xk"],
    "inseguridad": ["insegurida"],
    "justicia por": ["justicia x", "#JusticiaPor"],
    "que no quede impune": ["q no quede impune", "q no kede impune"]
}

# Exclusiones geográficas: CABA y otras provincias argentinas
EXCLUSIONES_CABA: List[str] = [
    "CABA", "Ciudad Autónoma de Buenos Aires", "Capital Federal",
    "Policía de la Ciudad", "Gobierno de la Ciudad", "GCBA", "Jorge Macri",
    "Palermo", "Recoleta", "Belgrano", "Caballito", "Villa Urquiza",
    "Villa Crespo", "Almagro", "Balvanera", "San Telmo", "Puerto Madero",
    "Colegiales", "Chacarita", "Boedo", "Parque Patricios", "Lugano",
    "Mataderos", "Devoto", "Saavedra CABA", "Comuna 1", "Comuna 12",
    "Comuna 13", "Comuna 14", "Comuna 15"
]

EXCLUSIONES_PROVINCIAS: List[str] = [
    "Córdoba Capital", "Provincia de Córdoba", "Rosario", "Santa Fe Capital",
    "Provincia de Santa Fe", "Mendoza", "Tucumán", "Salta", "Jujuy",
    "Neuquén", "Río Negro", "Chubut", "Santa Cruz", "Tierra del Fuego",
    "Entre Ríos", "Paraná", "Corrientes", "Misiones", "Posadas", "Chaco",
    "Resistencia", "Formosa", "Santiago del Estero", "Catamarca", "La Rioja",
    "San Juan", "San Luis", "La Pampa"
]

# Stopwords en español para el detector de palabras nuevas en Pasada Abierta
STOPWORDS_ES: Set[str] = {
    "el", "la", "los", "las", "un", "una", "unos", "unas", "de", "del", "al",
    "a", "en", "con", "por", "para", "sin", "sobre", "entre", "hacia", "hasta",
    "desde", "que", "q", "xq", "como", "cuando", "donde", "quien", "cual",
    "y", "e", "o", "u", "ni", "pero", "mas", "sino", "porque", "pues", "si",
    "no", "ya", "muy", "mas", "más", "menos", "tan", "tanto", "todo", "toda",
    "todos", "todas", "otro", "otra", "otros", "otras", "mismo", "misma",
    "este", "esta", "estos", "estas", "ese", "esa", "esos", "esas", "aquel",
    "aquella", "mi", "mis", "tu", "tus", "su", "sus", "nuestro", "nuestra",
    "fue", "fueron", "era", "eran", "son", "es", "esta", "está", "están",
    "estan", "hay", "habia", "había", "hacer", "hizo", "hace", "hacen",
    "tiene", "tienen", "tuvo", "puede", "pueden", "hoy", "ayer", "mañana",
    "manana", "dia", "día", "dias", "días", "hora", "horas", "año", "años",
    "vecino", "vecinos", "vecina", "vecinas", "barrio", "partido", "municipio",
    "calle", "calles", "provincia", "buenos", "aires", "bonaerense", "conurbano",
    "facebook", "post", "video", "foto", "fotos", "compartir", "ver", "nota",
    "noticias", "diario", "info", "hola", "gente", "alguien", "sabe", "favor"
}


def quitar_tildes(texto: str) -> str:
    """Devuelve la versión sin tildes (conservando la ñ)."""
    protegido = texto.replace("ñ", "\x01").replace("Ñ", "\x02")
    normalizado = unicodedata.normalize("NFD", protegido)
    sin_acento = "".join(c for c in normalizado if unicodedata.category(c) != "Mn")
    return sin_acento.replace("\x01", "ñ").replace("\x02", "Ñ")


def generar_variantes_termino(termino: str) -> List[str]:
    """
    Genera variantes ortográficas:
    - Original
    - Sin tilde
    - Errores frecuentes / abreviaturas (insegurida, justicia x, q, xq)
    - Hashtag equivalente si aplica
    """
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


def es_exclusion_geografica(texto: str, partido_objetivo: str = "") -> bool:
    """
    Evalúa si un texto corresponde a CABA o a otra provincia y NO tiene anclaje
    explícito en un partido bonaerense.
    """
    t_lower = texto.lower()

    # Si menciona explícitamente el partido bonaerense buscado o "provincia de buenos aires", se conserva
    if partido_objetivo and partido_objetivo.lower() in t_lower:
        return False
    for anclaje in ANCLAJES_GENERALES_PBA:
        if anclaje.lower() in t_lower:
            return False

    # Verificar si menciona algún partido de PBA
    for p in PARTIDOS_PBA:
        if len(p) > 5 and p.lower() in t_lower:
            return False

    # Si menciona exclusiones de CABA u otras provincias, descartar
    for exc in EXCLUSIONES_CABA + EXCLUSIONES_PROVINCIAS:
        if exc.lower() in t_lower:
            return True

    return False
