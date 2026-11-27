# -*- coding: utf-8 -*-
"""
actores_barrido.py - Base de datos de actores, páginas y cuentas OSINT verificadas
para la Provincia de Buenos Aires, integrada desde skills-barrido:
1. barrido-reclamos-seguridad (medios y páginas vecinales por partido).
2. barrido-organizaciones-sociales (UTEP, MTE, Evita, Polo Obrero, CCC, Barrios de Pie).
3. barrido-visita-de-funcionarios (gremios docentes, estatales, salud, judiciales y medios locales).
"""

from typing import Dict, List, Any

# ==============================================================================
# 1. CUENTAS DE INSTAGRAM VERIFICADAS (por actor / partido)
# ==============================================================================
# Se revisan periódicamente con rotación respetando los tiempos OSINT (10s entre pedidos).

CUENTAS_INSTAGRAM_BARRIDO: List[str] = [
    # --- Medios y Alertas de Seguridad Provinciales / Conurbano ---
    "hechosyderecho",
    "alertapbanoticias",
    "berissoalinsta",
    "conectados.casares",
    "robos.mdp",
    "s.o.smardelplata",

    # --- La Plata / Gran La Plata ---
    "laplatanoticias",
    "noticiasdevillaelvira",
    "diariohornense",
    "sinlimiteslp",
    "noticiasplatenses",
    "notilaplata.ar",
    "elbonanews",
    "radiogonnet",
    "radiolaplata909",
    "diariogranlaplata",
    "lbinoticias",
    "elobservadorlaplata",
    "inundadosbarrionorte",
    "sutebalp",
    "listamulticolorsutebalaplata",
    "tribunadocentelaplata",
    "udocba.lp",
    "ate_laplata",
    "ateverdeyblancalaplata",
    "delegadxsatelaplata",
    "lamarronate.lp",
    "ate_municipales_la_plata",
    "municipalesautoconvocadxslp",
    "cicoplaplata",
    "cicophigasanmartinlp",
    "cicopludovica",
    "marronsalud.laplata",
    "adulp.sindicato",
    "atulp_sindicato",
    "ajb_la_plata",
    "cgtregionallaplata",
    "ctaa_laplata",
    "multisectorial_lpbe",
    "izquierdadiario.lp",
    "upcnok",
    "suteba_provincia",

    # --- Bahía Blanca / Ing. White / Sudoeste ---
    "sutebabb",
    "lamarronbahia",
    "lacelestesutebabahiablanca",
    "casadedocentesbb",
    "ate_bahiabca",
    "ateconicetbbca",
    "cta_bahiablanca",
    "cta.bahiablanca",
    "ajb.bahiablanca",
    "ajbgenerosbahiablanca",
    "cicop.bahiablanca",
    "cgtbahia",
    "juventudsindicalperonistabahia",
    "ingenierowhiteoficial",
    "apepebahia",

    # --- Coronel Rosales (Punta Alta / Pehuen-Có) ---
    "pehuen_co",
    "pehuenco_mcr",

    # --- Tres Arroyos ---
    "feb_tresarroyos",
    "cgttresarroyos",
    "rural3arroyos",
    "ateneonestorkirchnertsas",

    # --- Organizaciones Sociales Nacionales y Provinciales ---
    "utep_oficial",
    "mteargentina",
    "movimientoevita",
    "movimientoevitapba",
    "mujeresevitapba",
    "polo.obrero",
    "barriosdepieok",

    # --- Organizaciones Sociales por Partido ---
    "utep_evita_quilmes_2",
    "mtequilmes",
    "movimientoevitaquilmes",
    "mte.sanmartin",
    "mte.sanmiguel",
    "mte.tresdefebrero",
    "utepevita.laplata",
    "movimientoevitalaplata",
    "movimientoevitaberisso",
    "bdp_la_matanza",
    "mteuteplujan",
    "uteplomasdezamora",
    "mte_utep.pilar",
    "utep_laplata",
    "mtelaplata",
]


# ==============================================================================
# 2. PÁGINAS DE FACEBOOK VERIFICADAS (DIFUSORES Y MEDIOS POR PARTIDO)
# ==============================================================================
# Lista base de páginas activas verificadas en el barrido OSINT de PBA.
# Formato: { "nombre": str, "url": str, "partido": str, "tipo": str, "seguidores": str }

PAGINAS_FACEBOOK_BARRIDO: List[Dict[str, str]] = [
    # Provinciales
    {"nombre": "La Bonaerense Noticias Policiales", "url": "https://www.facebook.com/LABONAERENSENOTICIASPOLICIALES", "partido": "Provincia de Buenos Aires", "tipo": "policial"},
    {"nombre": "La Plata Noticias 24", "url": "https://www.facebook.com/LaPlataNoticias24", "partido": "La Plata", "tipo": "medio_local"},

    # Conurbano Sur
    {"nombre": "Info Quilmes", "url": "https://www.facebook.com/infoquilmes", "partido": "Quilmes", "tipo": "medio_local"},
    {"nombre": "Quilmes Vecinos Denuncian", "url": "https://www.facebook.com/QUILMESVECINOSDENUNCIAN", "partido": "Quilmes", "tipo": "vecinal"},
    {"nombre": "El Noticiero de Berazategui", "url": "https://www.facebook.com/ElNoticierodeBerazategui", "partido": "Berazategui", "tipo": "medio_local"},
    {"nombre": "Florencio Varela Publica", "url": "https://www.facebook.com/FlorencioVarelaPublica", "partido": "Florencio Varela", "tipo": "medio_local"},
    {"nombre": "Almirante Brown y su Gente", "url": "https://www.facebook.com/altebrownysugente", "partido": "Almirante Brown", "tipo": "vecinal"},
    {"nombre": "LANÚS NOTICIAS", "url": "https://www.facebook.com/lanusnoticias", "partido": "Lanús", "tipo": "medio_local"},
    {"nombre": "Avellaneda Real", "url": "https://www.facebook.com/100064695398736", "partido": "Avellaneda", "tipo": "medio_local"},
    {"nombre": "Ciudad Monte Grande", "url": "https://www.facebook.com/RamonBelozo.FotografoUrbano", "partido": "Esteban Echeverría", "tipo": "vecinal"},
    {"nombre": "CANAL 4 Ezeiza", "url": "https://www.facebook.com/CANAL4EZEIZA", "partido": "Ezeiza", "tipo": "medio_local"},
    {"nombre": "AHORA Berisso", "url": "https://www.facebook.com/AhoraBerissoOk", "partido": "Berisso", "tipo": "medio_local"},
    {"nombre": "Noticias Ensenada", "url": "https://www.facebook.com/noticiasensenada2016", "partido": "Ensenada", "tipo": "medio_local"},
    {"nombre": "Vecinos en Alerta Lomas", "url": "https://www.facebook.com/AlertaLomas", "partido": "Lomas de Zamora", "tipo": "vecinal"},

    # Conurbano Oeste
    {"nombre": "Vecinos de La Matanza Queremos Seguridad", "url": "https://www.facebook.com/61557399783418", "partido": "La Matanza", "tipo": "vecinal"},
    {"nombre": "Noticias MERLO", "url": "https://www.facebook.com/NoticiasMerloBsAs", "partido": "Merlo", "tipo": "medio_local"},
    {"nombre": "Merlo Real Noticia", "url": "https://www.facebook.com/MerloRealFace", "partido": "Merlo", "tipo": "medio_local"},
    {"nombre": "Moreno Noticias 1ª Edición", "url": "https://www.facebook.com/MorenoNoticiasprimeraedicion", "partido": "Moreno", "tipo": "medio_local"},
    {"nombre": "Paisanos de Hurlingham Noticias", "url": "https://www.facebook.com/paisanosdehurlinghamnoticias", "partido": "Hurlingham", "tipo": "medio_local"},
    {"nombre": "Tres de Febrero Avanza", "url": "https://www.facebook.com/3favanza", "partido": "Tres de Febrero", "tipo": "vecinal"},
    {"nombre": "NMP Noticias Marcos Paz", "url": "https://www.facebook.com/100063812623178", "partido": "Marcos Paz", "tipo": "medio_local"},

    # Conurbano Norte
    {"nombre": "San Miguel Noticias ValorSMA", "url": "https://www.facebook.com/ValorSMA", "partido": "San Miguel", "tipo": "medio_local"},
    {"nombre": "Malvinas Argentinas Noticias", "url": "https://www.facebook.com/MalvinasArgentinasNoticias", "partido": "Malvinas Argentinas", "tipo": "medio_local"},
    {"nombre": "Tigre Noticias", "url": "https://www.facebook.com/TigreNoticias365", "partido": "Tigre", "tipo": "medio_local"},
    {"nombre": "San Fernando Nuestro", "url": "https://www.facebook.com/SanFernandoNuestro", "partido": "San Fernando", "tipo": "medio_local"},
    {"nombre": "Qué Pasa San Isidro", "url": "https://www.facebook.com/quepasa.sanisidro", "partido": "San Isidro", "tipo": "medio_local"},
    {"nombre": "Qué Pasa Vicente López", "url": "https://www.facebook.com/quepasa.vicentelopez", "partido": "Vicente López", "tipo": "medio_local"},
    {"nombre": "Centro de Noticias de Pilar", "url": "https://www.facebook.com/centrodenoticiaspilar", "partido": "Pilar", "tipo": "medio_local"},
    {"nombre": "El Diario de Escobar", "url": "https://www.facebook.com/ElDiarioDeEscobar", "partido": "Escobar", "tipo": "medio_local"},
    {"nombre": "Anonimus José C Paz Noticias", "url": "https://www.facebook.com/61588327442640", "partido": "José C. Paz", "tipo": "medio_local"},

    # Interior de PBA
    {"nombre": "Luján En Línea", "url": "https://www.facebook.com/lujanenlinea.noticias", "partido": "Luján", "tipo": "medio_local"},
    {"nombre": "Campana Noticias", "url": "https://www.facebook.com/campananoticiasok", "partido": "Campana", "tipo": "medio_local"},
    {"nombre": "Junín Informado", "url": "https://www.facebook.com/61570674845699", "partido": "Junín", "tipo": "medio_local"},
    {"nombre": "Tandil Alerta Reportes", "url": "https://www.facebook.com/alertatandil", "partido": "Tandil", "tipo": "vecinal"},
    {"nombre": "NoticiasMDQ Mar del Plata", "url": "https://www.facebook.com/noticiasmdq", "partido": "General Pueyrredón", "tipo": "medio_local"},

    # Bahía Blanca / Ing. White
    {"nombre": "ATE Bahía Blanca", "url": "https://www.facebook.com/ate.bahiablanca", "partido": "Bahía Blanca", "tipo": "gremial"},
    {"nombre": "Trabajadores Municipales Bahía Blanca", "url": "https://www.facebook.com/SindicatoDeTrabajadoresMunicipalesBahiaBlanca", "partido": "Bahía Blanca", "tipo": "gremial"},

    # Organizaciones Sociales en Facebook
    {"nombre": "CCC Nacional", "url": "https://www.facebook.com/profile.php?id=100067904332891", "partido": "Provincia de Buenos Aires", "tipo": "organizacion_social"},
    {"nombre": "UTEP Evita Quilmes", "url": "https://www.facebook.com/UTEPEvitaQuilmes", "partido": "Quilmes", "tipo": "organizacion_social"},
    {"nombre": "MTE Sudeste / Quilmes", "url": "https://www.facebook.com/mtesudeste", "partido": "Quilmes", "tipo": "organizacion_social"},
    {"nombre": "CCC La Plata", "url": "https://www.facebook.com/profile.php?id=100080969187154", "partido": "La Plata", "tipo": "organizacion_social"},
    {"nombre": "Movimiento Evita José C. Paz", "url": "https://www.facebook.com/profile.php?id=61580754849731", "partido": "José C. Paz", "tipo": "organizacion_social"},
    {"nombre": "Movimiento Evita Vicente López", "url": "https://www.facebook.com/MovEvitaVteLopez", "partido": "Vicente López", "tipo": "organizacion_social"},
    {"nombre": "Patria Grande Vicente López", "url": "https://www.facebook.com/pgvicentelopez", "partido": "Vicente López", "tipo": "organizacion_social"},

    # Asambleas Vecinales La Plata
    {"nombre": "Asamblea Vecinal Tolosa", "url": "https://www.facebook.com/tolosadicebasta", "partido": "La Plata", "tipo": "vecinal"},
    {"nombre": "Asamblea Inundados Tolosa", "url": "https://www.facebook.com/asambleainundadostolosa", "partido": "La Plata", "tipo": "vecinal"},
    {"nombre": "Asamblea Tolosa se plantó", "url": "https://www.facebook.com/asambleatolosaseplanto", "partido": "La Plata", "tipo": "vecinal"},
]


# ==============================================================================
# 3. GRUPOS VECINALES Y COMUNITARIOS DE FACEBOOK (Abiertos para monitoreo)
# ==============================================================================
GRUPOS_FACEBOOK_BARRIDO: List[Dict[str, str]] = [
    {"nombre": "Vecinos de Tolosa", "url": "https://www.facebook.com/groups/1786457162105954/", "categoria": "seguridad"},
    {"nombre": "CITY BELL Vecinos", "url": "https://www.facebook.com/groups/3080130565574216/", "categoria": "seguridad"},
    {"nombre": "Alguien sabe? yo sé LA PLATA!!", "url": "https://www.facebook.com/groups/287382458609412/", "categoria": "sociales_servicios"},
    {"nombre": "GENTE DE WHITE", "url": "https://www.facebook.com/groups/384850432132685/", "categoria": "seguridad"},
    {"nombre": "gente de white (sin censura)", "url": "https://www.facebook.com/groups/951733971026237/", "categoria": "seguridad"},
    {"nombre": "José C. Paz informado", "url": "https://www.facebook.com/groups/140352039937398/", "categoria": "seguridad"},
    {"nombre": "QUE PASA EN JOSE C PAZ", "url": "https://www.facebook.com/groups/1118910192308894/", "categoria": "seguridad"},
]


# ==============================================================================
# 4. CUENTAS DE X / TWITTER VERIFICADAS
# ==============================================================================
CUENTAS_X_BARRIDO: List[str] = [
    # Oficiales y Monitoreo Institucional
    "Kicillofok",
    "BAProvincia",
    "Julio_Alak",
    # Organizaciones y Gremios
    "UTEPoficial",
    "CATToficialok",
    "CARBAP_ARG",
    "Cepba",
    # Medios Locales y Regionales Bonaerenses
    "lanuevaweb",
    "BHInfoMedia",
    "apepe_bahia",
    "urbana939",
    "infocielo",
    "radiolaplata909",
    "infoblancosobre",
    "tribunaslp",
    "ANDigitalOK",
    "LaUneok",
    "elbonanews",
    "InfoCuandoLlega",
]


# ==============================================================================
# 5. MATRICES DE BÚSQUEDA OSINT COMBINADAS (consultas.ps1 & SKILL templates)
# ==============================================================================

# Términos específicos de convocatorias de seguridad y reclamos de justicia
TERMINOS_RECLAMOS_SEGURIDAD: List[str] = [
    "justicia por", "basta de inseguridad", "queremos vivir en paz",
    "ni uno más", "no queremos más muertes", "queremos justicia",
    "estamos cansados", "#JusticiaPor", "#BastaDeInseguridad",
    "vecinos autoconvocados", "marcha por seguridad", "ruidazo",
    "concentración frente a la comisaría", "frente a fiscalía",
    "frente a tribunales", "asamblea de vecinos"
]

# Términos específicos de organizaciones sociales y economía popular
TERMINOS_ORGANIZACIONES_SOCIALES: List[str] = [
    "olla popular", "ollazo", "ollas vacías", "comedores comunitarios",
    "merenderos", "emergencia alimentaria", "salario social",
    "Volver al Trabajo", "cooperativas", "ajuste en comedores",
    "jornada nacional de lucha", "por el pan en la mesa", "navidad sin hambre",
    "UTEP", "MTE", "Movimiento Evita", "Polo Obrero", "Barrios de Pie",
    "Corriente Clasista y Combativa", "CCC", "Libres del Sur", "FOL"
]

# Términos específicos para visitas de autoridades y agenda de reclamo
TERMINOS_VISITA_AUTORIDADES: List[str] = [
    "visita kicillof", "visita del gobernador", "lo esperamos kicillof",
    "acto oficial reclamo", "visita de ministro", "inauguración reclamo",
    "recorrida oficial reclamo", "escrache funcionario", "concentración casa de gobierno",
    "reclamo legislatura bonaerense", "reclamo en el palacio municipal",
    "docentes reclamo kicillof", "estatales reclamo gobernador"
]
