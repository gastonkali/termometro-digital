---
name: barrido-organizaciones-sociales
description: Barrido OSINT en Instagram, Facebook, X y medios de convocatorias, ollas, cortes y reclamos por alimentos o contra el ajuste de organizaciones sociales (UTEP, MTE, Evita, CCC, etc.) en la provincia de Buenos Aires.
---

# Barrido de organizaciones sociales

Relevamiento en fuentes abiertas de **convocatorias, movilizaciones, cortes, ollas populares, ollazos y reclamos por alimentos o contra el ajuste** de organizaciones sociales y de la economía popular en **toda la provincia de Buenos Aires** (135 partidos), salvo que el usuario recorte el alcance. El resultado es un informe PDF 9:16 neutral, con fichas por convocatoria, tabla de estado por partido y anexos separados.

## Cuándo se usa y cuándo no
- **Se usa** cuando el usuario pide un barrido sobre organizaciones sociales, movimientos sociales, piqueteros, economía popular, UTEP, MTE, Movimiento Evita, CCC, Polo Obrero, Barrios de Pie, FOL, Libres del Sur u otras; sobre ollas populares, ollazos, comedores o merenderos; pedidos de alimentos o "emergencia alimentaria"; jornadas nacionales de lucha y sus réplicas locales; reclamos contra el ajuste de estos actores. Vale cualquier variante de nombre ("barrido UTEP", "barrido ollas", "barrido movimientos sociales", "barrido jornada de lucha", etc.).
- **No se usa** para "barrido gobernador", "barrido visita del gobernador", "barrido visita de funcionario" o similares: eso es el skill **barrido-redes**, que no se modifica ni se mezcla con este.
- Este skill **no lee ni escribe** en `barrido-redes` (ni su `actores.md`). Solo puede tomar su plantilla visual como referencia de lectura (ver paso 7).

## Paso 0. Confirmar antes de empezar (obligatorio)
Antes de cualquier búsqueda, preguntale al usuario (con AskUserQuestion si está disponible) y no empieces hasta tener respuesta:
1. **Tipo y tema del barrido**: qué jornada, consigna, organización o reclamo (por ejemplo, "Jornada Nacional de Lucha UTEP 26/11", "ollas populares en el conurbano").
2. **Alcance territorial**: por defecto, toda la provincia. Confirmalo. Si nombra partidos, son **prioridad de orden**, no límite: el resto de la provincia se barre igual, salvo que diga explícitamente "solo".
3. **Fecha del hecho y ventana de búsqueda** (por defecto, desde 7 días antes hasta la hora del barrido).
4. **Organizaciones** a incluir (por defecto, todas las de la lista base) y si suma alguna nueva.
5. **Material de partida** (flyers, capturas, enlaces) y **hora de cierre** del informe.
Si el usuario no responde y la sesión es desatendida, usá los valores por defecto y escribilos en la portada.

## Reglas que no se negocian
1. **Nada queda en "vista previa".** Toda publicación que aparezca en una grilla, búsqueda o miniatura y pueda ser relevante (fecha dentro de la ventana y tema compatible) **se abre**: se lee el texto completo y se mira la imagen. Lo que no se pudo abrir va como **pendiente con motivo** en el anexo A, nunca como "vista previa" ni "según la miniatura". Antes de entregar, contá: publicaciones listadas = publicaciones abiertas + pendientes con motivo.
2. **Toda la provincia.** Las réplicas locales de una convocatoria nacional **sí** entran (es el objeto de este barrido). Quedan fuera, en el anexo B: CABA, otras provincias, otros países y convocatorias ya realizadas que no son del tema (por ejemplo, el 25N), cada una con su motivo.
3. **Cuentas y palabras clave, las dos.** Leer cuenta por cuenta (paso 3) no reemplaza a la búsqueda por palabras clave (paso 4), ni al revés.
4. **Nunca "sin convocatorias" a secas.** Escribí "sin convocatoria publicada en las cuentas y búsquedas revisadas hasta las HH:MM del DD/MM".
5. **Neutralidad.** Sin niveles de riesgo, sin predicciones, sin adjetivos valorativos. Posiciones atribuidas y citas textuales breves.
6. **Sin recomendaciones ni medidas sugeridas en el informe.** Nada de "se recomienda", "conviene" ni "medidas sugeridas" en el PDF ni en los anexos. Si corresponde repetir el barrido, decilo solo en el chat.
7. **Privacidad.** En perfiles personales, ocultá nombre y foto; no enlaces el perfil; no recopiles más publicaciones de esa persona. Recortá siempre la barra superior de Facebook e Instagram y la de WhatsApp o el teléfono en capturas recibidas. Los datos del usuario no van en URLs ni en el informe.
8. **Ritmo** (para no bloquear las cuentas del usuario): al menos 10 s entre búsquedas o cambios de página en una misma red; como máximo 10 seguidas por red y después alternar de red; 3 o 4 desplazamientos por página como máximo. Si aparece un captcha, una verificación o un aviso de actividad inusual, detenete en esa red y avisá. No resuelvas captchas ni ingreses contraseñas.
9. **Repetir cerca del hecho.** Los puntos locales suelen publicarse la noche previa o la misma mañana, y a veces solo los difunden radios, medios barriales o grupos de WhatsApp. Ofrecé (en el chat) un nuevo barrido entre las 7 y las 9 del día del hecho.

## Paso 1. Planificar
- Armá la lista de trabajo: organizaciones × partidos, partiendo de la **lista base** (al final). Marcá en cada cuenta la fecha de su última publicación cuando la revises.
- Creá una lista de tareas visible: descubrimiento, lectura de cuentas, palabras clave, medios, apertura de todo lo pendiente, informe, verificación.

## Paso 2. Descubrir cuentas por organización y partido
- **Instagram (con sesión, panel Buscar)**: en `https://www.instagram.com/explore/`, hacé clic en el cuadro de búsqueda (no escribas sin foco: un atajo abre el diálogo "Enviar comentarios"), escribí y leé los enlaces de perfil. Consultas: "<org>" sola y "<org> <partido>" para cada partido prioritario (utep, mte, mte utep, movimiento evita, ccc, corriente clasista y combativa, polo obrero, barrios de pie, fol, libres del sur, utd, somos, frente darío santillán, mtd, ctep). La búsqueda de varias palabras en `explore/search/keyword/` sirve para consignas, no para cuentas.
- **Facebook**: `https://www.facebook.com/search/pages?q=<org> <partido>` y `search/top`. Muchas organizaciones (la CCC sobre todo) publican **solo en Facebook**.
- **X**: `from:` para cuentas nacionales; las locales casi no usan X.
- Anotá cada cuenta nueva con fecha de verificación. Al terminar, si hubo cambios en la lista base, avisá al usuario y ofrecé actualizar este skill con una propuesta de edición (tarjeta de skills); no lo cambies por tu cuenta ni uses zips ni copias locales.

## Paso 3. Leer cuenta por cuenta
- **Instagram**: abrí el perfil y leé las miniaturas: el `alt` de `a[href*="/p/"] img` trae la fecha ("on November 25, 2026"). Si la fecha falta ("undefined") o cae dentro de la ventana, **abrí la publicación** y leé el texto con la lectura de texto de página. La vista `/embed/` puede no devolver el texto: no dependas de ella. No uses APIs internas de Instagram.
- **Método rápido para Instagram (probado el 26/11/2026)**: la fecha de cada publicación sale del código de la URL, sin abrirla: se decodifica el código (alfabeto `A-Za-z0-9-_`, primeros 11 caracteres) como número en base 64 y `(n >> 23) + 1314220021721` son los milisegundos de publicación. Para leer el texto completo de las publicaciones de la ventana, pedí la página pública de la publicación (`fetch('/p/<código>/')` con la sesión) y tomá la etiqueta `og:description`, que trae cuenta, fecha y texto completo; con 6 a 10 s de pausa entre pedidos, en segundo plano, y leyendo los resultados por partes. Cuenta como publicación abierta. Las publicaciones sin texto (solo imagen) se abren igual para ver la imagen.
- **Facebook**: abrí la página, desplazá 2 veces y expandí "Ver más" de cada `div[data-ad-rendering-role="story_message"]` antes de leer. Anotá la fecha de la última publicación aunque no sea relevante. No leas ni copies URLs con parámetros de rastreo (la extensión las bloquea): para enlaces usá el patrón limpio.
- **X**: `from:<cuenta> since:AAAA-MM-DD`; fecha por ID: `(BigInt(id) >> 22n) + 1288834974657`; leé el `article` completo quitando los `<script>`.

## Paso 4. Palabras clave (obligatorio, en las tres redes)
- **Consignas del hecho**: textos del flyer y de la convocatoria nacional (por ejemplo, "jornada nacional de lucha", "el hambre no se aguanta más", "por el pan en la mesa", "navidad sin hambre").
- **Medidas**: olla popular, ollazo, "ollas vacías", corte, piquete, "cortes y movilizaciones", acampe, "todos a", concentramos, movilizamos, "nos vemos".
- **Reclamos**: comedores, merenderos, alimentos, "emergencia alimentaria", Capital Humano, "salario social", "Volver al Trabajo", cooperativas, ajuste, hambre.
- **Lugares típicos**: Puente Pueyrredón, Puente La Noria, accesos, rutas, plazas centrales y municipios de cada partido.
- Combiná consigna + partido y consigna + organización. En Instagram usá `explore/search/keyword/?q=` y **desplazá la grilla al menos 3 veces**; filtrá por fecha con el `alt` y abrí todo lo que quede en la ventana (regla 1). En Facebook usá la búsqueda de publicaciones recientes, sabiendo que indexa con atraso; no alcanza sola. En X, búsquedas con `OR` y `since:`.
- Localidades con nombre ambiguo (La Plata, Junín, Mercedes, etc.): no las excluyas de la consulta; filtrá después publicación por publicación.

## Paso 5. Medios, radios y difusores
- Los flyers con lugar y hora suelen circular primero por radios y medios barriales (antecedente: el 25/11/2026 el flyer de la CCC "Por el pan en la mesa", 26/11, 9 h, Plaza Italia, lo publicó la página de Facebook "3T" (106.1 3T Radio) y no la CCC). Buscá el texto del flyer y la consigna en páginas de medios locales y en `search/top` de Facebook.
- Si el usuario manda una captura (por ejemplo, de WhatsApp), ubicá la publicación original para obtener el enlace. Si no aparece, va como pendiente con motivo y la ficha usa la captura con la leyenda "captura aportada por el usuario".
- Para localizar un lugar que el flyer no aclara (por ejemplo, "Plaza Italia"), usá las pistas visibles (banderas, logos de la seccional) y decí explícitamente que es una inferencia hasta confirmarla con una fuente propia.

## Paso 6. Selección
**Criterio del usuario (26/11/2026): cualquier presencia organizada de estas organizaciones es relevante, aunque no haya un reclamo explícito.** Entran entregas de mercadería, ollas y viandas, ranchadas, ferias, encuentros, actos, murales, reuniones con autoridades o instituciones, formaciones, actividades en sedes, participación en marchas o acompañamientos de otros actores, y marchas anunciadas sin fecha. No se descartan por "asistencial" ni por "otro tema": van a la ficha o a la tabla de presencia organizada. En el anexo B quedan solo las actividades fuera de la provincia, fuera de la ventana o de actores que no son organizaciones sociales (ONG, gremios, partidos), con su motivo.
- **Ficha roja "Convocatoria publicada"**: convocatoria con lugar y hora en la provincia.
- **Ficha "Actividad con lugar y hora"** (color turquesa): presencia organizada de hoy o de los días siguientes con lugar y hora, aunque no sea un reclamo (por ejemplo, una entrega de mercadería).
- **Tabla "Presencia organizada en la ventana"** (obligatoria): partido, organización, actividad, fecha, hora y lugar según cada publicación ("lugar no indicado" si falta), primero las próximas y después las realizadas. En la portada, dentro de "Para tener en cuenta", va el total de actividades y de partidos.
- **Ficha ámbar "Convocatoria sin punto local"**: convocatoria nacional o local replicada sin lugar ni hora; una ficha por convocatoria, con todas sus réplicas verificadas.
- **Tabla "Estado por partido"** (obligatoria): por cada partido revisado, cuentas, fecha de última publicación y resultado (convocatoria con punto / actividad hoy / flyer replicado / presencia organizada / sin convocatoria publicada / inactiva / pendiente con motivo).
- **Anexo B**: lo relevado y descartado con su motivo (otra provincia, CABA, ya realizada, otro tema, perfil personal sin convocatoria).

## Paso 7. Informe
- Formato 9:16, 1080×1920 px por página, modo oscuro. Si existe la plantilla `plantilla/informe.html` del skill barrido-redes, se puede **leer** como referencia de estilos (sin modificar ese skill). Si no está, usá el mismo esquema: portada, fichas (datos + publicaciones con capturas en marco de celular), tabla de estado por partido.
- Portada: título del barrido, fecha y hora de cierre, bloque **"Para tener en cuenta"** (convocatorias con punto primero, réplicas, partidos sin convocatoria publicada) e índice. Sin recomendaciones.
- Bajo cada captura, enlace con texto fijo `Link de la publicación ↗` y URL limpia (Instagram `/p/<código>/`, X `/<cuenta>/status/<id>`, Facebook `/<página>/posts/<id>` o `/photo/?fbid=`). Perfil personal o captura sin original: `<span class="lnk off">Enlace no disponible: motivo</span>`.
- Se entregan **tres PDF**: `Barrido_<Tema>_<fecha>.pdf`, `Anexo_A_Registro_de_busquedas_<Tema>.pdf` (red, consulta, resultado; pendientes con motivo) y `Anexo_B_Cuentas_y_no_incluidos_<Tema>.pdf` (cuentas por resultado con fecha de última publicación, descartados con motivo, nota de método sin recomendaciones).
- Generá los PDF con Chrome sin interfaz (`--headless=new --print-to-pdf --no-pdf-header-footer`), donde esté disponible (en la nube o en la PC del usuario).

## Paso 8. Verificación antes de entregar (obligatoria)
- Hoja de contactos con todas las páginas: nada cortado, superpuesto ni tapado por el pie. Si una tabla no entra, partila en dos páginas.
- Cero apariciones de "vista previa", "sin abrir" o "según la miniatura" en los tres PDF.
- Cantidad de enlaces (`/URI (`) = publicaciones con enlace público.
- Cero frases de recomendación ("se recomienda", "conviene", "sugerimos").
- Todas las cuentas de la tabla tienen fecha de última publicación o motivo de pendiente.
- Entregá los archivos y, en el chat, en pocas líneas: convocatorias con lugar y hora, réplicas, partidos sin convocatoria, pendientes. Ahí sí podés ofrecer repetir el barrido.

## Lista base de cuentas (verificadas el 26/11/2026)
Formato: cuenta · partido · estado al verificar (fecha de la última publicación). Orden sugerido para leer: primero las **activas**, después las de baja actividad; las **inactivas** se revisan igual pero rápido (solo fecha de la última publicación). Esta lista se actualiza solo por propuesta de edición aceptada por el usuario.

### Nacionales y provinciales (leer siempre primero)
- IG @utep_oficial · X @UTEPoficial · FB página UTEP · UTEP nacional · activa (26/11/2026)
- IG @mteargentina · MTE nacional · activa (25/11/2026)
- IG @movimientoevita · IG @movimientoevitapba · IG @mujeresevitapba · Evita nacional y provincia · activas (25 y 26/11/2026)
- IG @polo.obrero · Polo Obrero nacional · activa (26/11/2026)
- IG @barriosdepieok · Barrios de Pie nacional · activa (25/11/2026)
- FB CCC Nacional (facebook.com/profile.php?id=100067904332891; cccnacional.com) · activa (20/11/2026)

### Activas por partido
- **Quilmes**: IG @utep_evita_quilmes_2 (26/11) · FB facebook.com/UTEPEvitaQuilmes (26/11) · IG @mtequilmes (26/11) · FB MTE Quilmes facebook.com/mtesudeste (26/11) · IG @movimientoevitaquilmes (25/11)
- **General San Martín**: IG @mte.sanmartin (25/11)
- **San Miguel**: IG @mte.sanmiguel (25/11)
- **Tres de Febrero**: IG @mte.tresdefebrero (25/11)
- **La Plata**: IG @utepevita.laplata (19/11) · IG @movimientoevitalaplata (20/11) · FB Corriente Clasista y Combativa La Plata (profile.php?id=100080969187154) (15/11)
- **Berisso**: IG @movimientoevitaberisso (24/11)
- **La Matanza**: IG @bdp_la_matanza, Barrios de Pie La Matanza (24/11)
- **Luján**: IG @mteuteplujan (16/11)
- **José C. Paz**: FB Movimiento Evita JoseC.Paz (profile.php?id=61580754849731) (26/11; publica convocatorias y entregas de mercadería con lugar y hora en los flyers)
- **Vicente López**: FB Movimiento Evita Vicente López (facebook.com/MovEvitaVteLopez) (25/11) · FB Patria Grande Vicente López (facebook.com/pgvicentelopez) (23/11)

### Baja actividad (última publicación entre agosto y octubre de 2026)
- IG @utep_laplata · La Plata · 25/09
- FB perfil "UTEP La Plata" (profile.php?id=100027194995013) · La Plata · 05/08
- IG @mtelaplata · La Plata, Berisso y Ensenada · 13/10
- IG @uteplomasdezamora · Lomas de Zamora · 30/09
- IG @mte_utep.pilar · Pilar · 30/10
- FB CCC Quilmes, Berazategui y Varela (profile.php?id=100064493930818) · 25/09
- FB UTEP Evita JCP (profile.php?id=61565681900874) · José C. Paz · 19/07
- FB Mov Evita Jcp (profile.php?id=100089490567871) · José C. Paz · 13/07 (recuerdo compartido; publica también en grupos de José C. Paz)

### Inactivas (revisar solo la fecha)
- IG @mte.brown · Almirante Brown · 21/01/2026
- FB CCC Desocupados y Precarizados La Matanza (facebook.com/CCCDesocupadosyPrecarizadosLaMatanza) · 07/06/2026
- IG @utep_fciovarela · Florencio Varela · 25/07/2025
- IG @mteutepmoreno · Moreno · 14/05/2025
- IG @movimientoevitazl · Zárate · 30/11/2024
- IG @utep_chascomus · Chascomús · 09/10/2024
- FB Ccc Almirante Brown (profile.php?id=61551448451710) · 11/04/2024
- IG @mte_utep.vicentelopez · Vicente López · 23/09/2023
- FB Promotoras de Salud CCC La Plata (profile.php?id=100083451128164) · 18/09/2023
- FB FinEs La Plata CCC (profile.php?id=100090326262373) · 16/02/2023
- FB Frente Nacional por la Igualdad Movimiento Evita José C. Paz (profile.php?id=100076516806174) · 17/12/2022
- FB movimiento evita jose c paz (profile.php?id=100087276826984) · 08/12/2022
- FB movimiento evita José C.Paz (profile.php?id=100084805617776) · 30/08/2022
- FB Coop. Movimiento CCC La Plata (facebook.com/corrienteclasistaccclaplata) · 2022 · IG @sembrando.futuro.utep · Quilmes · 2022
- IG @utep_almirante_brown · 24/12/2021 · FB CCC Almirante Brown (profile.php?id=100064459071921) · 2021
- IG @utepherreria · Vicente López · 16/12/2021
- IG @olpvarela (OLP-UTEP) · Florencio Varela · 17/11/2021
- IG @utepevita.lomas · Lomas de Zamora · 15/04/2021
- FB CCC La Plata (facebook.com/CCCLaPlata) · 2020
- IG @utep.laplata · La Plata · 19/12/2019
- Sin publicaciones: IG @uteplaplata · IG @utep.evita.quilmes · FB Movimiento Evita De Jose C.Paz (profile.php?id=100088153652033)
- Instagram: no se hallaron cuentas de la CCC de la provincia.

### Difusores y medios
- FB "3T" (106.1 3T Radio) · difundió el flyer de la CCC del 26/11 · no aparece en el buscador de Facebook con "3T 106.1" ni "3T radio" (pendiente: enlace y localidad).
- Radio Fan 103.9 (programa "Ir a más") · entrevistó a la UTEP por la jornada del 26/11 (difundido por UTEP Evita Quilmes).
- Medios con notas sobre comedores u ollas: Alerta PBA Noticias (IG @alertapbanoticias), Berisso al Instante (IG @berissoalinsta), Conectados Casares (IG @conectados.casares).

### Búsquedas por palabra clave que dieron resultado (26/11/2026)
- Instagram (`explore/search/keyword/`): "olla popular", "emergencia alimentaria", "jornada nacional de lucha", "ollazo", "polo obrero", "barrios de pie", "comedores comunitarios". Frases largas de flyer ("el hambre no se aguanta mas") no devolvieron resultados.
- Facebook: la búsqueda entre comillas en `search/top` devuelve publicaciones viejas; sirve para descubrir páginas, no para la ventana.
- Para separar CABA de la provincia: "La Noche de las Ollas" es una acción de ollas de CABA (Barrios de Pie CABA y otras); no confundir con convocatorias bonaerenses.

### Pendientes de identificar
- FOL, Libres del Sur, UTD, Somos, Frente Darío Santillán y MTD por partido; Polo Obrero y Barrios de Pie por partido (salvo La Matanza).
- Cuentas UTEP/MTE de La Matanza, Lanús, Berazategui y Merlo (no halladas).

## Antecedente de práctica (25 y 26/11/2026)
Barrido de la Jornada Nacional de Lucha de UTEP del 26/11 y de la adhesión de la CCC. Errores que este skill corrige:
- Se trató a tres partidos como límite del barrido cuando el alcance era toda la provincia (regla del paso 0.2).
- Dos publicaciones quedaron como "vista previa, sin abrir" (regla 1).
- La nota de método incluyó "se recomienda repetir el barrido" (regla 6).
- El flyer con lugar y hora no estaba en las cuentas de la organización sino en una radio (paso 5).