---
name: "barrido-reclamos-seguridad"
description: "Barrido OSINT de convocatorias vecinales por seguridad y reclamos de justicia en la provincia de Buenos Aires (marchas, ruidazos, cortes, concentraciones en comisarías); un Word por convocatoria con el modelo Reclamo de seguridad / Marcha vecinal."
---

# Barrido de reclamos de seguridad y justicia (PBA)

Detecta en fuentes abiertas las convocatorias de vecinos por inseguridad o en reclamo de justicia (marchas, ruidazos, cortes, concentraciones frente a comisarías, municipios, fiscalías o tribunales, asambleas vecinales por seguridad) en **toda la provincia de Buenos Aires**, y entrega **un informe Word por convocatoria** con el modelo "Reclamo de seguridad / Marcha vecinal" (modelo Junín – Villa Belgrano).

## Cuándo se usa y cuándo no
- **Se usa** cuando el usuario pide un barrido de reclamos de seguridad, marchas vecinales, "justicia por…", ruidazos, convocatorias por inseguridad o similares, con cualquier variante de nombre.
- **No se usa** para "barrido gobernador / visita de funcionario" (skill **barrido-redes**, que no se modifica ni se mezcla con este), ni para organizaciones sociales (barrido-organizaciones-sociales) ni UOCRA (barrido-uocra).
- No reemplaza a los modelos de escrache en redes, conflicto entre bandas, hecho puntual relevante ni alerta de escalada: si el material es de ese tipo, avisá y usá ese modelo.

## Paso 0. Preguntar antes de empezar (obligatorio)
Con AskUserQuestion si está disponible, y sin empezar hasta tener respuesta:
1. **Ventana**: por defecto, desde las 00 h del día anterior hasta la hora del barrido, más todas las convocatorias a futuro que aparezcan.
2. **Alcance**: por defecto, toda la provincia. Si nombra partidos, son prioridad de orden, no límite, salvo que diga "solo".
3. **Material de partida**: hecho puntual, nombre de víctima, flyer, captura o enlace.
4. **Hora de cierre** y si quiere un informe por cada convocatoria hallada (por defecto) o solo de alguna.
En una sesión desatendida, usá los valores por defecto y decilo en el chat.

## Reglas que no se negocian
1. **Abrir todo lo relevante.** Nada se informa "según la miniatura" ni "vista previa": se abre, se lee completo y se mira la imagen. Lo que no se pudo abrir se informa en el chat como pendiente con motivo.
2. **Enfoque operativo, sin perfiles políticos.** No se individualiza ni se perfila a convocantes ni participantes de una protesta pacífica, ni por filiación política ni por ninguna otra cosa. Los perfiles personales se ocultan (sin nombre, sin foto, sin enlace). La familia de la víctima puede nombrarse solo como "familiares de <víctima>" si la convocatoria pública la menciona.
3. **PERFIL DIFUSOR** describe la página o el medio que difundió (nombre, tipo, seguidores, ámbito, antigüedad, si difundió convocatorias anteriores), nunca a vecinos particulares.
4. **Sin recomendaciones.** Nada de "medidas sugeridas", "previsiones operativas", "se recomienda" o "conviene". Si hace falta volver a barrer, decilo solo en el chat.
5. **Redacción.** No usar "a fin de prevenir alteraciones al orden público". Usar la fórmula: "A través de una publicación realizada en la red social <Facebook/Instagram/X> <por la página X>, vecinos de <barrio> se concentrarían el <día> a las <hora> en <lugar>, en reclamo de…". Hechos atribuidos con "según", "de acuerdo a lo publicado". Sin adjetivos valorativos ni predicciones.
6. **Ritmo** (para no bloquear las cuentas del usuario): al menos 10 s entre cambios de página en una misma red; como máximo 10 acciones seguidas por red y después alternar; lotes de 3 páginas como máximo por llamada al navegador (lotes largos de Facebook cuelgan la extensión). Ante captcha, verificación o aviso de actividad inusual: detenerse en esa red y avisar. No resolver captchas ni ingresar contraseñas.
7. **Privacidad.** Recortar la barra superior de Facebook/Instagram y la de WhatsApp o del teléfono en capturas. No poner datos personales en URLs.

## Paso 1. Hechos primero
Las convocatorias casi siempre nacen de un hecho grave reciente (homicidio, robo violento, desaparición, siniestro vial con fuga, abuso). Antes de buscar convocatorias:
- Revisá las páginas provinciales y los medios activos de la lista base (paso 2) por hechos graves de las últimas 72 h; anotá víctima, barrio y partido.
- Para cada hecho, buscá "justicia por <nombre>", "#JusticiaPor<Nombre>", "<nombre> marcha" y "<barrio> vecinos" en Facebook (publicaciones recientes), Instagram (`explore/search/keyword/?q=`) y X (`since:`). Las convocatorias suelen aparecer entre 24 y 72 h después del hecho.

## Paso 2. Lista base por partido
Leé primero las páginas **activas** del partido (lista al final): la primera publicación y 2 desplazamientos, expandiendo "Ver más". Las de actividad **baja** se revisan si el partido tiene un hecho reciente. Las **inactivas** no se leen salvo pedido. Anotá la fecha de la última publicación de cada página revisada.
Si aparece una página nueva que difunde convocatorias, al terminar ofrecé (en el chat) sumarla a este skill con una propuesta de edición; no edites el skill por tu cuenta.

## Paso 3. Palabras clave (obligatorio, en las tres redes)
Combiná cada familia con el partido o la localidad:
- **Consignas**: "justicia por", "basta de inseguridad", "queremos vivir en paz", "ni uno más", "no queremos más muertes", "queremos justicia", "estamos cansados".
- **Medidas**: marcha, ruidazo, cacerolazo, corte, "vecinos autoconvocados", "nos movilizamos", "todos a", "nos concentramos", "asamblea de vecinos", "convocatoria".
- **Destinos**: comisaría, municipio, municipalidad, fiscalía, tribunales, "frente a la comisaría", "plaza principal".
- **Hashtags**: #JusticiaPor…, #BastaDeInseguridad.
Localidades con nombre ambiguo (Junín, Mercedes, San Martín, La Plata, Ensenada…): no las excluyas; filtrá después publicación por publicación. Descartá CABA, otras provincias y otros países.

## Paso 4. Datos de cada convocatoria
Para cada convocatoria con lugar o fecha en la provincia, reuní: publicación original (enlace limpio) y réplicas; lugar exacto, fecha y hora; motivo; hecho de origen (fuentes periodísticas con enlace); convocatorias anteriores del mismo barrio o caso (concurrencia, modalidad, incidentes si los hubo según fuentes); coordenadas del punto (formato Google Maps "-34.93604, -57.94640") y distancia a la dependencia policial o municipal más cercana; métricas visibles (reacciones, comentarios, compartidos) con hora de toma; datos de la página difusora.
Fechas: Instagram por shortcode (`(n>>23)+1314220021721` ms); X por ID (`(BigInt(id)>>22n)+1288834974657n`); Facebook leyendo la fecha de la publicación abierta (no la relativa de la grilla si la publicación es vieja).

## Paso 5. Informe Word (uno por convocatoria)
Cargá el skill **docx** antes de armarlo. Formato del modelo Junín – Villa Belgrano, exclusivo de este tipo de informe:
- Arriba a la derecha: "Fecha del informe: dd/mm/aaaa".
- Título en mayúsculas y negrita: "LOCALIDAD – BARRIO – RECLAMO DE SEGURIDAD" (o "RECLAMO DE JUSTICIA" si corresponde).
- Times New Roman 11, texto justificado, mismo interlineado en todo el documento. Sin pie de página, sin encabezado institucional, sin "INFORME OSINT".
- Títulos de sección en mayúsculas, negrita, con línea inferior: **CONTEXTO** / **ANTECEDENTE INMEDIATO** / **GEOLOCALIZACIÓN** / **DIFUSIÓN Y REPERCUSIÓN** / **PERFIL DIFUSOR**.
  - CONTEXTO: la convocatoria con la fórmula de la regla 5, el motivo y el hecho de origen con su fuente periodística enlazada.
  - ANTECEDENTE INMEDIATO: convocatorias o hechos previos del mismo barrio o caso. Si no hay: "No se registraron convocatorias anteriores en las fuentes revisadas".
  - GEOLOCALIZACIÓN: dirección, coordenadas, enlace "Ver en Google Maps", captura del mapa y distancia a la dependencia más cercana.
  - DIFUSIÓN Y REPERCUSIÓN: publicación original y réplicas (páginas y medios, no perfiles personales), métricas con hora de toma.
  - PERFIL DIFUSOR: la página o medio que difundió (regla 3).
- Imágenes alineadas a la izquierda con marco fino, una debajo de la otra; debajo de cada una, el epígrafe y después el enlace. Imagen, epígrafe y enlace en la misma hoja. Sin huecos en blanco evitables (achicar imágenes si hace falta). Hipervínculos sin subrayar.
- Donde falta un dato: "No consta en la fuente disponible".
- Nombre del archivo: `Reclamo_Seguridad_<Localidad>_<Barrio>_<ddmmaaaa>.docx`.

## Paso 6. Verificación antes de entregar
- Convertí cada .docx a PDF y mirá todas las páginas: nada cortado, imagen-epígrafe-enlace juntos, sin huecos grandes.
- Cero apariciones de "orden público", "se recomienda", "conviene", "previsiones", "vista previa".
- Cero nombres o fotos de perfiles personales.
- Todos los enlaces funcionan y son limpios (sin parámetros de rastreo).
- En el chat, en pocas líneas: convocatorias halladas (lugar, fecha, hora), partidos sin convocatoria publicada "en las páginas y búsquedas revisadas hasta las HH:MM", pendientes con motivo. Nunca "sin convocatorias" a secas.

## Lista base de difusores por partido (Facebook, verificada el 26/11/2026)
Formato: página · ruta o id · seguidores · última publicación al verificar. **Activa** = publicó en la última semana; **baja** = último mes o más; **inactiva** = más de un año. Las páginas sin fecha están identificadas pero sin verificar: verificarlas en el primer barrido que toque ese partido.

### Provinciales
- La Bonaerense Noticias Policiales · /LABONAERENSENOTICIASPOLICIALES · 102 mil · activa (26/11)
- La Plata Noticias · /LaPlataNoticias24 · 90 mil · activa (26/11)

### Conurbano sur
- **Quilmes**: Info Quilmes /infoquilmes 162 mil, activa (26/11) · Quilmes Vecinos Denuncian /QUILMESVECINOSDENUNCIAN 6,9 mil, baja (14/07) · sin verificar: Mirada de Quilmes Oeste /miradaenquilmes, La Noticia de Quilmes /noticiasdequilmes, Diario El Sol /elsolquilmes, El Megáfono /ElmegafonodeQuilmes, Quilmes Vecinal id 61587169740987, Vecinos de Quilmes denuncian /vecinosdequilmesdenuncian
- **Florencio Varela**: Florencio Varela Publica /FlorencioVarelaPublica 1,7 mil, sin verificar · Vecinos Autoconvocados en Florencio Varela id 100067634174089, sin verificar · inactivas: Florencio Varela - noticias id 100069771639405 (2019), Vecinos de Varela /vecinosdevarela (2020) · partido con poca cobertura de páginas: reforzar con palabras clave
- **Berazategui**: El Noticiero de Berazategui /ElNoticierodeBerazategui 250 mil, activa (25/11) · sin verificar: Berazategui Noticias /beranoticias, Todo Berazategui Noticias /todoberazateguinoticias, Vecinos Unidos Berazategui id 100066922016922 · descartada: "Los vecinos de Berazategui decimos NO…" (tema único)
- **Lomas de Zamora**: Vecinos en Alerta Lomas /AlertaLomas 23 mil, baja (13/08) · Vecinos de Lomas Pedimos Justicia y Seguridad /VecinosDeLomasDeZamoraPedimosJusticiaYSeguridad 10 mil, baja (23/06) · sin verificar: Fuenteovejuna /FuenteovejunaVecinosDeLomasDeZamora, Vecinos contra la Inseguridad /VecinosContraLaInseguridadLomasDeZamora, Lomas de Zamora Noticias id 100050489739754, Vecinos Parque Barón /vecinosparquebaronLZ
- **Almirante Brown**: almirante brown y su gente /altebrownysugente 13 mil, activa (22/11) · sin verificar: Vecinos - Alte. Brown id 100064342916199, Noticias Almirante Brown id 100063828436450
- **Lanús**: LANÚS NOTICIAS /lanusnoticias 87 mil, activa (26/11) · sin verificar: Lanús Hoy /LanusHoy, Vecinos de Valentín Alsina /vecinosdevalentinalsinalanus, Reclamos de Vecinos de Lanús /Lanushcd
- **Avellaneda**: Avellaneda-Real id 100064695398736 117 mil, activa (26/11) · sin verificar: La Ciudad de Avellaneda /laciudadavellaneda, Avellaneda Hoy /avellanedahoy.com.ar, Foro Vecinos de Avellaneda /foroavellaneda · ojo: "Parque Avellaneda" es barrio de CABA
- **Esteban Echeverría**: Ciudad Monte Grande /RamonBelozo.FotografoUrbano 93 mil, activa (26/11) · sin verificar: Monte Grande id 100083579710102
- **Ezeiza**: CANAL 4 Ezeiza /CANAL4EZEIZA 129 mil, activa (25/11) · sin verificar: Ezeiza Denuncia id 100064429042566, La Palabra de Ezeiza /lapalabraezeiza, Ezeiza Hoy /EzeizaHoy
- **La Plata**: La Plata Noticias /LaPlataNoticias24, activa (26/11) · sin verificar: Vecinos La Plata /vecinosvlp, Parque del Plata Coordinadora /PdPCoordinadora, Asamblea Vecinal Tolosa (antecedente)
- **Berisso**: AHORA Berisso /AhoraBerissoOk 79 mil, activa (26/11) · sin verificar: Berisso Ciudad /berisso.ciudad, El Mundo de Berisso /semanarioelmundo
- **Ensenada**: Noticias Ensenada /noticiasensenada2016 45 mil, activa (25/11) · sin verificar: /EnsenadaWeb

### Conurbano oeste
- **La Matanza**: Vecinos de La Matanza Queremos Seguridad id 61557399783418 68 mil, activa (26/11) · sin verificar: Vecinos de San Justo /VecinosdeSanJusto, Hospital René Favaloro Vecinos Autoconvocados · inactiva: Alerta Vecinos La Matanza /AlertaVecinosLaMatanza (2020) · antecedentes: Vecinos en Alerta (VEA), Vecinos en Alerta Rafael Castillo, Vecinos en Alerta Ramos Mejía
- **Merlo**: Noticias MERLO /NoticiasMerloBsAs 230 mil, activa (26/11) · sin verificar: Merlo Real Noticia /MerloRealFace 234 mil, Merlo Real Noticias /MerloRealSinCensuras, infomerlo /infomerlo, Vecinos de Merlo en Alerta /villademerloenalerta, Vecinos Autoconvocados Merlo Morón id 100063832655371
- **Moreno**: Moreno Noticias 1ª Edición /MorenoNoticiasprimeraedicion 362 mil, activa (26/11) · sin verificar: Moreno Es Lo Que Hay /morenoesloquehay, Morenovisión /morenovision, Moreno Seguro /MorenoSeguro, InfoMoreno /infomoreno.periodismodigital
- **Morón**: sin página activa verificada · sin verificar: Vecinos en alerta MORON id 100071649128571, Vecinos de Morón /VecinosDeMoronOk · inactivas: Vecinos Unidos Morón /Vecinosunidosmoron (2022), MORON Noticias Plus (2014) · reforzar con palabras clave
- **Ituzaingó**: sin verificar: Noticias Ituzaingó id 100063943650275
- **Hurlingham**: Paisanos de Hurlingham Noticias /paisanosdehurlinghamnoticias 12 mil, 03/11 · sin verificar: Hurlingham Noticias /HurNoticias, Hurlingham City /hurlinghamcityok
- **Tres de Febrero**: Tres de Febrero Avanza /3favanza 24 mil, 10/11
- **Marcos Paz**: NMP Noticias Marcos Paz id 100063812623178 33 mil, activa (25/11)

### Conurbano norte
- **San Martín**: Estación Landon (radio) /Radioestacionlandon 4,8 mil, baja (14/10; difundió la convocatoria del 15/09/2026 frente a la Comisaría San Martín 1ª) · sin verificar: Villa Ballester San Martín /vecinosdevillaballestersanmartin, Yo vivo o viví en Villa Ballester /VillaBallesterOK
- **San Miguel**: San Miguel Noticias /ValorSMA 150 mil, activa (26/11; confirmar que es San Miguel, Buenos Aires) · sin verificar: Noticias San Miguel /NoticiasSanMiguel2023 · descartar /SanMiguelsv503 (El Salvador)
- **José C. Paz**: Anonimus José c paz noticias id 61588327442640 5,4 mil, baja (07/09) · sin verificar: José C Paz en Acción id 61577115294051; grupos "José C. Paz informado" /groups/140352039937398 y "QUE PASA EN JOSE C PAZ" /groups/1118910192308894 · inactiva: El Diario de José C. Paz (02/2025) · reforzar con palabras clave
- **Malvinas Argentinas**: Malvinas Argentinas Noticias /MalvinasArgentinasNoticias 191 mil, activa (18/11) · sin verificar: Malvinas x Argentinos /malvinasxargentinos
- **Tigre**: TigreNoticias /TigreNoticias365 61 mil, activa (20/11) · sin verificar: Tigre News id 61578207226061, Tigre al día /tigre.aldia
- **San Fernando**: San Fernando Nuestro /SanFernandoNuestro 37 mil, activa (26/11)
- **San Isidro**: Que Pasa San Isidro /quepasa.sanisidro 39 mil, activa (26/11) · sin verificar: Radio San Isidro FM /radiosanisidroFM105.1
- **Vicente López**: Que Pasa Vicente López /quepasa.vicentelopez 27 mil, activa (26/11)
- **Pilar**: Centro de Noticias de Pilar /centrodenoticiaspilar 54 mil, activa (26/11) · sin verificar: Cordialmente Pilar /surarturoferreira, Pilar Hoy /pilarhoy
- **Escobar**: El Diario de Escobar /ElDiarioDeEscobar 160 mil, activa (26/11) · sin verificar: El Día de Escobar /eldiadeescobar, Escobar Red Comunitaria /Escobar.RedcomunitariaTodosJuntos

### Interior
- **Luján**: Luján En Línea /lujanenlinea.noticias 123 mil, activa (26/11) · sin verificar: Luján Hoy /lujanhoy.com.ar
- **Campana**: Campana Noticias /campananoticiasok 101 mil, activa (26/11) · sin verificar: El Diario de Campana /eldiariodecampana
- **Zárate**: sin verificar: Zárate Online /tulugarrrandom 122 mil, DeltaCom id 100063558251748 · inactiva: Noticias ZA /zarate.alerta (2019)
- **Junín**: Junín Informado id 61570674845699 13 mil, activa (25/11; antecedente Villa Belgrano) · sin verificar: Diario Junín /diariojunin, Junín24 /Junin24oficial
- **Tandil**: Tandil Alerta Reportes /alertatandil 62 mil, activa (26/11) · sin verificar: El Diario de Tandil /diariodetandil
- **Mar del Plata (General Pueyrredon)**: NoticiasMDQ /noticiasmdq 138 mil, activa (26/11) · sin verificar: Mar del Plata 24 /mardelplata24 · Instagram: robos.mdp, S.O.S Mar del Plata (s.o.smardelplata)
- **Bahía Blanca**: sin verificar: Bahía Blanca Che /bahiablanca.che

### Partidos sin difusor identificado
Todos los demás partidos de la provincia (Cañuelas, San Vicente, Presidente Perón, General Rodríguez, Mercedes, Chivilcoy, Olavarría, Azul, Necochea, Tres Arroyos, Pinamar, Villa Gesell, la Costa, Pergamino, San Nicolás, Chascomús, Punta Indio, etc.) se cubren con palabras clave + nombre del partido. Antecedentes recientes de convocatorias: Pinamar (justicia por Aldana, 10/2026), Punta Indio (11/2026), Campana – Barrio Monteverde (10/2026), Padua – Merlo (10/2026).

## Método de verificación de una página (Facebook)
Navegar a la página, esperar 5 s, desplazar hasta el encabezado "Publicaciones" y hacer zoom a la región [700,40,1400,200] para leer el nombre y la fecha de la primera publicación. Lotes de 3 páginas. Si la salida de JavaScript devuelve "[BLOCKED…]", limpiar caracteres "=", "?" y "=>" de la salida.