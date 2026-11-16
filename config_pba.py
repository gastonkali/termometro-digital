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

import re
import unicodedata
from typing import Dict, List, Set, Tuple

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
}

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
            "motochorros", "robo a mano armada", "tiraron a matar", "alarma vecinal"
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
    "San Juan", "San Luis", "La Pampa", "Córdoba", "Cordoba"
]

EXCLUSIONES_INTERNACIONALES: List[str] = [
    "españa", "espana", "madrid", "barcelona", "valencia", "sevilla",
    "colombia", "bogota", "bogotá", "medellin", "medellín", "cali",
    "mexico", "méxico", "chile", "santiago de chile", "peru", "perú", "lima",
    "estados unidos", "eeuu", "usa", "texas", "florida", "miami", "new york", "california",
    "venezuela", "caracas", "uruguay", "montevideo", "paraguay", "asunción"
]

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
    "iap",
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
    "obras de iluminacion led terminadas"
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


def es_ruido_o_no_conflictividad(texto: str) -> Tuple[bool, str]:
    """
    Detecta si una publicación es autopromoción municipal, gacetilla institucional
    o un hecho de CABA/rutina que no representa conflictividad ni reclamo vecinal.
    """
    t_norm = quitar_tildes(texto.lower())

    if "bertulazzi" in t_norm:
        return True, "Descartado: Caso de fuga ocurrido en CABA (Comuna porteña)"
    if "parque chacabuco" in t_norm or "comisaria de la ciudad" in t_norm or "policia de la ciudad" in t_norm:
        return True, "Descartado: Hecho en jurisdicción CABA"

    for patron in PATRONES_RUIDO_NO_CONFLICTIVIDAD:
        p_norm = quitar_tildes(patron)
        if p_norm in t_norm:
            return True, f"Descartado: Noticia institucional / autopromoción municipal ('{patron}')"

    return False, ""


def es_exclusion_geografica(texto: str, partido_objetivo: str = "") -> bool:
    """
    Evalúa si un texto corresponde a CABA, otra provincia o país, o no pertenece a PBA.
    Retorna True si debe ser DESCARTADO.
    """
    if not es_texto_espanol(texto):
        return True

    t_lower = texto.lower()

    # Descartar países y ciudades extranjeras
    for inter in EXCLUSIONES_INTERNACIONALES:
        if f" {inter} " in f" {t_lower} " or f"/{inter}" in t_lower or f"#{inter}" in t_lower:
            return True

    # Verificar si menciona exclusiones de CABA o provincias
    menciona_otra_provincia_o_caba = False
    for exc in EXCLUSIONES_CABA + EXCLUSIONES_PROVINCIAS:
        if exc.lower() in t_lower:
            menciona_otra_provincia_o_caba = True
            break

    # Verificar anclajes positivos explícitos de PBA
    tiene_anclaje_pba = False
    if partido_objetivo and partido_objetivo.lower() != "provincia de buenos aires" and partido_objetivo.lower() in t_lower:
        tiene_anclaje_pba = True
    else:
        for loc, part in LOCALIDADES_A_PARTIDO.items():
            if loc in t_lower:
                tiene_anclaje_pba = True
                break

        if not tiene_anclaje_pba:
            for anclaje in ANCLAJES_GENERALES_PBA + ["pba", "zona sur", "zona oeste", "zona norte", "amba"]:
                if anclaje.lower() in t_lower:
                    tiene_anclaje_pba = True
                    break

        if not tiene_anclaje_pba:
            for p in PARTIDOS_PBA:
                if len(p) > 4 and p.lower() in t_lower:
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
    t_norm = quitar_tildes(texto.lower())

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

    # Buscar localidades específicas
    for loc, partido_real in LOCALIDADES_A_PARTIDO.items():
        loc_norm = quitar_tildes(loc)
        if re.search(r"\b" + re.escape(loc_norm) + r"\b", t_norm):
            return partido_real

    # Buscar partidos oficiales
    for partido in PARTIDOS_PBA:
        p_norm = quitar_tildes(partido.lower())
        if re.search(r"\b" + re.escape(p_norm) + r"\b", t_norm):
            return partido

    return partido_sugerido or "Provincia de Buenos Aires"


def resolver_eje_tematico_preciso(texto: str, categoria_sugerida: str = "") -> str:
    """
    Evita clasificar como 'seguridad' reclamos laborales, puestos de trabajo o servicios públicos.
    Por ejemplo: 'Tornquist defensa de puestos de trabajo' -> sociales_servicios.
    """
    t_norm = quitar_tildes(texto.lower())

    if any(k in t_norm for k in [
        "puestos de trabajo", "conflicto laboral", "despidos", "fabrica",
        "cierre de planta", "sin luz", "falta de luz", "corte de luz",
        "edesur", "edenor", "sin agua", "baja presion", "colectivos", "uta"
    ]):
        return "sociales_servicios"

    if any(k in t_norm for k in ["justicia por", "#justiciapor", "femicidio", "crimen de", "asesinato"]):
        return "justicia"

    if any(k in t_norm for k in ["picadas", "juntada de motos", "fiesta clandestina"]):
        return "eventos_no_autorizados"

    if any(k in t_norm for k in ["violencia policial", "gatillo facil", "policia golpeo", "asuntos internos"]):
        return "imagen_institucional"

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

    # Twitter / X: debe ser un tweet específico
    if "x.com" in u or "twitter.com" in u:
        return "/status/" in u

    # Instagram: debe ser post o reel
    if "instagram.com" in u:
        return "/p/" in u or "/reel/" in u

    # Facebook: debe ser permalink de post, foto, reel o video
    if "facebook.com" in u or "fb.com" in u:
        if "/groups/" in u:
            return "/permalink/" in u or "/posts/" in u
        if any(k in u for k in ["/posts/", "/photo/", "fbid=", "/reel/", "/watch/?v=", "/videos/", "story_fbid=", "permalink.php"]):
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
        "enviar mensaje", "precio:", "alquilo dpto", "vendo ropero"
    ]
    if any(p in a for p in patrones):
        return True
    if any(p in t for p in patrones):
        return True
    if a in ["activo", "facebook", "desconocido", "usuario", "participante"]:
        if len(t) < 30 or any(p in t for p in patrones):
            return True
    return False

