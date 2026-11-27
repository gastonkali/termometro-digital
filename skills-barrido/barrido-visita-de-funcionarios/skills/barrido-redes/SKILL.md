---
name: "barrido-visita-de-funcionarios"
description: Barrido de redes sociales (Instagram, Facebook, X) por fuentes abiertas para detectar convocatorias, manifestaciones, cortes y reclamos actuales o latentes ante visitas oficiales o eventos en localidades de la provincia de Buenos Aires, y entregarlo como PDF 9:16 con fichas neutrales y capturas. Usar cuando el usuario pida "barrido de redes", "barrido", "termómetro digital", "monitoreo social", relevar reclamos o protestas ante una visita del gobernador u otra autoridad, o actualizar un barrido anterior.
---

# Barrido de redes

Relevamiento de **convocatorias y reclamos actuales o latentes** publicados en **fuentes abiertas de redes sociales**, vinculados a localidades y a un evento (por lo general, una visita oficial). El resultado es un PDF vertical 9:16 para celular, con fichas neutrales y capturas de las publicaciones.

## Reglas que no se negocian

1. **Las fuentes son las redes.** Instagram, Facebook y X son las fuentes primarias. Los medios sirven solo para dar contexto o para verificar. No armes fichas con notas viejas de medios.
2. **Reclamos actuales, latentes o recientes (último mes).**
   - Una movilización ya realizada, aunque haya terminado antes de la llegada del funcionario, **entra como ficha** si tiene hasta 1 mes de antigüedad. Lleva la etiqueta "Reclamo reciente" e indica fecha, hora, lugar y reclamos.
   - Solo va al anexo, en "Relevados y no incluidos", el conflicto que se cerró formalmente (por ejemplo, el gremio votó levantar las medidas) o lo que tiene más de 1 mes.
   - **Los conflictos nacionales no son de interés:** Presupuesto nacional, paros universitarios nacionales, marchas de la CGT a Congreso o Plaza de Mayo, hospitales nacionales. No entran como ficha ni figuran en la portada. En el anexo B basta una línea que deje constancia del criterio. Si una marcha mezcla consignas nacionales y locales, la ficha muestra solo los reclamos locales y provinciales.
3. **Instagram se revisa SIEMPRE, cuenta por cuenta, además de la búsqueda por palabras clave.** Mirar el feed de inicio no sirve, y la búsqueda por palabra clave sola tampoco alcanza. Muchos gremios locales publican sus convocatorias solo en Instagram.
   - Antecedente: el 24/11/2026 se pasó por alto la convocatoria de @sutebabb a concentrar en el Museo del Puerto de Ingeniero White durante la visita del gobernador, y el informe afirmó "sin convocatorias". No debe repetirse.
4. **Nunca escribas "sin convocatorias" a secas.** Escribí "sin convocatoria publicada en las cuentas revisadas" y en el anexo listá exactamente qué cuentas se cubrieron y cuáles no.
5. **Neutralidad.** Nada de análisis predictivos, niveles de riesgo ni adjetivos valorativos. Mostrá la posición de cada parte y las citas textuales atribuidas.
6. **Privacidad.**
   - En perfiles personales (no institucionales), ocultá nombre y foto: difuminado por CSS antes de capturar, o un rectángulo encima al recortar.
   - Recortá siempre la barra superior de Facebook e Instagram, donde aparecen la foto de perfil y la cuenta del usuario.
   - No pongas datos del usuario en las URL ni en los informes.
7. **Repetí el barrido cerca del evento.** Las convocatorias se publican hasta la noche anterior o la mañana misma. Proponé un nuevo barrido el día del evento.
8. **Dos pilares obligatorios: cuentas Y palabras clave.** Revisar organizaciones cuenta por cuenta (paso 3) no reemplaza a la búsqueda por palabras clave (paso 3b), ni al revés. Las convocatorias y los reclamos también los publican vecinos y usuarios comunes, en grupos vecinales, en comentarios y en respuestas a cuentas oficiales.
   - Cada barrido corre la grilla completa de `scripts/consultas.ps1` en las tres redes.
   - Toda búsqueda que no se haga queda listada como **pendiente** en el anexo. Nada se omite en silencio.
9. **Nunca se excluye de una consulta el nombre de la localidad** por ser ambiguo (ver "Localidades con nombre ambiguo" en el paso 3b).
10. **Avisá siempre al usuario cuando cambie la lista de actores.** El skill se usa desde varios dispositivos y la copia subida a la cuenta no se actualiza sola.
   - Al terminar cada barrido, si se agregaron, cambiaron o dieron de baja cuentas en `actores.md`, decile explícitamente: "Se actualizó la lista de actores (N cuentas nuevas: …). Hay que volver a subir el skill a la cuenta."
   - Generá el .zip actualizado en `%USERPROFILE%\Downloads\barrido-redes.zip`. Usá rutas internas con barra `/` y la carpeta `barrido-redes/` en el primer nivel (ver "Empaquetado").
   - Si el barrido no cambió la lista, decilo también en una línea.
   - Cada cuenta nueva se anota con su fecha de verificación.

## Flujo de trabajo

### 1. Agenda del evento
- **El bloque "Agenda oficial" de la portada solo se incluye si el usuario entrega la actividad del funcionario:** lugares, horarios y paradas. Solo en ese caso cada ficha se asocia a una parada, y las paradas con convocatoria van en rojo.
- **Si el usuario no la entrega, la portada NO lleva ese bloque.** No escribas "Agenda oficial difundida", "s/d" ni "agenda sin detalle público". Tampoco la armes con notas de prensa ni con publicaciones vagas como "tendrá agenda en La Plata".
  - En su lugar va el bloque **"Para tener en cuenta"**, con datos concretos del relevamiento: sesiones o actos previstos con fuente, movilizaciones recientes y la línea "Convocatorias vinculadas a la visita: sin convocatoria publicada en las cuentas y búsquedas revisadas".
  - Las fichas se asocian a la localidad.
  - La portada no lleva notas al pie sobre la agenda ni sobre los anexos: el pie muestra solo el número de página.
- Si no tenés la agenda, podés preguntarle al usuario al empezar si la tiene. Si no responde, seguí sin el bloque.

### 2. Lista de actores por localidad (antes de buscar)
- Partí de `actores.md`, que tiene las cuentas ya verificadas. Por cada localidad que falte, completá estas categorías:
  - gremios docentes (SUTEBA, FEB, UDOCBA, AMET) y sus agrupaciones internas (Multicolor, Marrón, Celeste);
  - estatales (ATE, UPCN), salud (CICOP), judiciales (AJB) y municipales;
  - centrales: CGT regional, CTA de los Trabajadores, CTA Autónoma;
  - movimientos sociales (UTEP, MTE, Polo Obrero, Barrios de Pie);
  - feministas y multisectoriales (Ni Una Menos);
  - jubilados, vecinales y cuentas comunitarias de la localidad;
  - entidades rurales y cámaras empresarias;
  - medios locales, que se usan para verificar.
- **Descubrimiento en Instagram** (requiere la sesión del usuario en el navegador de la app):
  - Usá el panel "Buscar" (`https://www.instagram.com/explore/`): hacé clic en el cuadro, escribí "<organización> <localidad>" y leé los enlaces `a[href^="/handle/"]`.
  - Las búsquedas de varias palabras en `explore/search/keyword/?q=` suelen dar "No hay resultados". Sirven para términos cortos o lugares ("museo del puerto", "ingeniero white").
  - Adivinar nombres de usuario no sirve: la mayoría no existe.
- Agregá a `actores.md` toda cuenta nueva que verifiques.

### 3. Lectura cuenta por cuenta
- **Instagram (sin sesión):** corré `scripts/ig_sweep.ps1` con la lista de cuentas. Usa la vista embebida pública (`/<cuenta>/embed/`) y devuelve las últimas publicaciones con fecha, enlace y texto, sin necesidad de iniciar sesión. Después filtrá por palabras clave: fecha del evento, "mañana", el día de la semana del evento, nombre de la autoridad, "visita", lugar, "concentr", "moviliz", "marcha", "paro", "corte", "reclam", "convoca".
- **Facebook (con sesión):**
  - Búsqueda de publicaciones recientes: `https://www.facebook.com/search/posts?q=<consulta>&filters=eyJyZWNlbnRfcG9zdHM6MCI6IntcIm5hbWVcIjpcInJlY2VudF9wb3N0c1wiLFwiYXJnc1wiOlwiXCJ9In0%3D`
  - Tené en cuenta que Facebook indexa con días de atraso: la búsqueda puede no mostrar lo publicado ayer u hoy, que es justamente lo más relevante antes del evento. **La búsqueda sola no alcanza:** entrá a la página de cada organización de `actores.md` que tenga Facebook y leé `div[data-ad-rendering-role="story_message"]`. Si alguna página queda sin revisar, listala en el anexo.
  - Abrí las publicaciones relevantes para leer el texto completo y los comentarios.
- **X (con sesión):** `https://x.com/search?q=<consulta> since:AAAA-MM-DD&f=live`. Leé `article` y conservá el enlace `/status/`. Para las cuentas de organizaciones, usá `from:<cuenta> since:…`.

### 3b. Búsqueda por palabras clave (usuarios comunes), obligatoria
Busca lo que publican vecinos y usuarios sin cuenta institucional: convocatorias autoconvocadas, cortes, reclamos barriales y quejas en comentarios.

**1. Generá la grilla** con `scripts/consultas.ps1` para cada localidad:
```powershell
.\consultas.ps1 -Localidad 'La Plata' -Alias @('#LaPlata','platense','platenses') `
  -Barrios @('Tolosa','City Bell','Gonnet','Los Hornos','Villa Elisa','Melchor Romero') `
  -Lugares @('<lugares de la agenda>') -Autoridad @('Kicillof','gobernador') `
  -CuentasOficiales @('Kicillofok','<intendente>') -Desde <7 días antes> -FechaEvento <AAAA-MM-DD> `
  -Ambigua -OutFile <carpeta del informe>\consultas.md
```
- Cargá **todos** los barrios y localidades del partido (no solo los de la agenda), los lugares de cada parada y las cuentas oficiales (autoridad, municipio, ministros que acompañan).
- La grilla cruza estos grupos de términos:
  - lugar: localidad, alias, hashtag, gentilicio, barrios, lugares de la agenda;
  - convocatoria: marcha, movilizamos, concentramos, convocamos, "nos vemos", "todos a";
  - medidas: corte, piquete, paro, protesta, ruidazo, cacerolazo, abrazo, "olla popular", asamblea, autoconvocados, escrache;
  - reclamo: reclamo, vecinos, "basta de", denuncia, "sin respuesta", abandono;
  - temas latentes: luz, agua, cloacas, inundación, baches, inseguridad, IOMA, escuela, hospital, colectivos, basura, despidos, salarios;
  - visita y fecha: visita, viene, "lo esperamos", acto, inauguración, día de la semana, "mañana", la fecha en número y en letras.
- Si aparece un tema o un término nuevo durante el barrido (el nombre de un barrio, una obra, una consigna), agregalo y volvé a buscar con él.

**2. Recorré la grilla completa:**
- **X:** las consultas con `OR`, más `to:<cuenta oficial>` (respuestas: ahí los usuarios dejan reclamos y avisos) y `@<cuenta> <localidad>` (menciones). `near:"<localidad>" within:15km` solo es un complemento.
- **Facebook:** una consulta por término, porque no acepta `OR`. Sumá la búsqueda de **grupos vecinales** (`search/groups`): abrí los grupos públicos de la localidad y de cada barrio y leé las publicaciones recientes del grupo (el buscador general no indexa bien los grupos). Sumá también los **comentarios** de las publicaciones de medios locales y del municipio sobre la visita.
- **Instagram:** hashtags de la localidad y de los barrios (`/explore/tags/<tag>/`), las páginas de ubicación de los lugares de la agenda (panel Buscar > Lugares) y los **comentarios** de las publicaciones de la autoridad, del municipio y de los medios locales sobre la visita.
- Abrí las publicaciones relevantes y leé sus respuestas o comentarios: la convocatoria suele aparecer ahí ("¿a qué hora es?", "nos vemos en…").

**Detalles técnicos verificados el 25/11/2026:**
- **Instagram:**
  - Los hashtags (`/explore/tags/…`) solo muestran destacados antiguos, sin pestaña "Recientes". Usá la búsqueda por palabra clave: `https://www.instagram.com/explore/search/keyword/?q=<términos>`.
  - Quedate con las publicaciones cuyo `img alt` tenga una fecha de la última semana ("on November 24, 2026").
  - Leé el texto sin sesión con `scripts/ig_posts.ps1 -Codigos …`. Si el flyer trae la fecha o el lugar, capturalo y leé la imagen: muchas veces el dato está solo ahí.
- **Facebook:** borra el `localStorage` propio entre navegaciones. Para acumular resultados entre búsquedas, guardalos en `window.name`, que se conserva en la pestaña. No guardes enlaces con parámetros: la extensión los bloquea.
- **X:**
  - `[data-testid="tweetText"]` a veces viene vacío; usá el `textContent` del `article` después de quitarle los `<script>`.
  - La fecha se calcula a partir del ID: `(BigInt(id) >> 22n) + 1288834974657`.
  - Guardá los resultados en `localStorage` del dominio x.com, que se conserva entre búsquedas.
- **Salida del navegador:** la herramienta corta cada respuesta en unos 1.000 caracteres. Devolvé solo los recuentos y leé el detalle en páginas.
- **Términos nuevos:** cuando aparece uno (por ejemplo "cloacas", "ABSA", el nombre de un hospital), agregalo como búsqueda en las tres redes.

**3. Registrá cada búsqueda** en `consultas.md`:
- completá la columna Resultado con "sin resultados relevantes", "N relevantes (enlaces)" o "pendiente: motivo";
- ese registro va completo al anexo del informe, en la sección "Registro de búsquedas".

**4. Privacidad de los usuarios comunes:**
- Se usa el contenido de la publicación, no a la persona.
- En capturas y textos, ocultá nombre, usuario y foto.
- No sigas ni recopiles otras publicaciones del mismo perfil más allá de la que es relevante.
- En el anexo, citá "publicación de usuario, red, fecha". El enlace se da solo a pedido.

**5. Localidades con nombre ambiguo (La Plata = ciudad/partido y "la plata" = dinero).** Los buscadores no distinguen mayúsculas, así que la consulta no puede separar los dos sentidos. **No excluyas el término de la búsqueda** ni lo reemplaces solo por búsquedas `from:`: se pierde información, y muchos usuarios escriben la ciudad en minúscula ("marcha en la plata"). Vale para X, Facebook e Instagram.
    - Buscá "la plata" junto con los términos de conflicto (lo hace la grilla) y **filtrá después, publicación por publicación**, sin descartar nada en la consulta.
    - Para X, este extractor marca cada publicación como CIUDAD, DINERO o AMBIGUA. Adaptá las expresiones a la localidad. Es solo una ayuda: las DINERO y AMBIGUA se miran igual antes de descartarlas.
      ```js
      const ciudad = /#laplata|platense|(ciudad|partido) de la plata|\b\d{1,3} y \d{1,3}\b|diagonal|plaza moreno|casa de gobierno|legislatura|unlp|municipalidad|alak|tolosa|ringuelet|gonnet|city bell|villa elisa|los hornos|san carlos|altos de san lorenzo|villa elvira|melchor romero|abasto|olmos|etcheverry|arana|berisso|ensenada|La Plata/i;
      const dinero = /no hay plata|la plata (de|para) |toda la plata|con la plata que|(robaron|afanaron|choreando) la plata|la plata del|plata dulce/i;
      [...document.querySelectorAll('article')].map(a => { const t = a.innerText.replace(/\s+/g,' ');
        const l = [...a.querySelectorAll('a[href*="/status/"]')].map(x => x.getAttribute('href')).find(h => /status\/\d+$/.test(h));
        const c = /\bLa Plata\b/.test(t) || ciudad.test(t) ? 'CIUDAD' : dinero.test(t) ? 'DINERO' : 'AMBIGUA';
        return c + ' ' + l + ' :: ' + t.slice(0, 280); }).join('\n')
      ```
      En X, `innerText` de `[data-testid="tweetText"]` puede venir vacío: leé el `innerText` del `article` completo. Después de navegar, las funciones definidas en `window` se pierden, así que pegá el código entero en cada llamada.
    - **Es la ciudad** si aparece #LaPlata, "platense", "ciudad de/partido de La Plata", "en/desde/hacia la plata" junto a un lugar o una hora, calles con formato "7 y 50", "diagonal", Plaza Moreno, Casa de Gobierno, Legislatura, UNLP, la Municipalidad, Alak, o barrios y localidades del partido (Tolosa, Ringuelet, Gonnet, City Bell, Villa Elisa, Los Hornos, San Carlos, Altos de San Lorenzo, Villa Elvira, Melchor Romero, Abasto, Olmos, Etcheverry, Arana), o Berisso o Ensenada.
    - **Es dinero** si dice "no hay plata", "la plata de los…", "toda la plata", "la plata para…", "con la plata que…", "se robaron la plata". Descartalo solo si **además** no aparece ninguna señal de la ciudad.
    - **Ambiguas:** si en minúscula no hay señales de ninguno de los dos sentidos, no las descartes: abrí la publicación (con sus respuestas y la ubicación del perfil) y decidí.
    - Complementá con búsquedas que no dependen del nombre: `#LaPlata`, `platense OR platenses`, los nombres de los barrios y de los lugares de la agenda, y `near:"La Plata" within:15km` (solo trae publicaciones geolocalizadas, así que sirve como complemento y no reemplaza a las otras).
    - En el anexo, informá cuántas publicaciones se descartaron por referirse a dinero.
    - El mismo criterio vale para otras localidades con nombre de palabra común (por ejemplo, Junín, Mercedes, Pergamino, Las Flores, Dolores, Salto, Bolívar, Suipacha). Corré `consultas.ps1` con `-Ambigua`.

### Ritmo (obligatorio en los pasos 2, 3 y 3b, para que las redes no bloqueen las cuentas del usuario)
- **La grilla completa lleva varias rondas por red** (por ejemplo, para La Plata: X 14, Facebook 36, Instagram 20). Planificá las rondas al empezar y alterná entre redes: mientras una descansa, se trabaja en otra. Si la grilla no se completa antes del cierre, lo que falta queda como **pendiente** en el registro y en el anexo. Nunca se saltea en silencio.
- **Orden dentro de cada red**, para que lo más urgente salga primero:
  1. autoridad, localidad y fecha de la visita;
  2. localidad con convocatoria o medidas;
  3. respuestas y menciones a cuentas oficiales;
  4. lugares de la agenda;
  5. grupos vecinales y barrios;
  6. temas latentes.
- Dejá **al menos 10 segundos** entre búsquedas o cambios de página en una misma red. Usá `computer wait` o el retardo del script.
- Hacé **como máximo 10 búsquedas seguidas por red**. Después pausá 3 minutos o pasá a otra red y volvé más tarde. Alterná entre Instagram, Facebook y X.
- Scrolleá de a poco: no más de 3 o 4 desplazamientos por página, con 2 o 3 segundos entre cada uno.
- Para *leer* cuentas conocidas de Instagram, priorizá `scripts/ig_sweep.ps1`, que no usa la sesión del usuario. La sesión queda para descubrir cuentas nuevas, Facebook y X.
- **Si aparece una verificación de seguridad, un "Continuar", un captcha o un aviso de actividad inusual, detenete de inmediato** en esa red y avisá al usuario. No reintentes ni resuelvas captchas.
- Antecedente: las ráfagas de búsquedas del 24/11/2026 provocaron cierres de sesión de Instagram y Facebook.

### 4. Selección
- **Entra como ficha:**
  - una convocatoria vinculada al evento: va primera, nivel **rojo**;
  - un reclamo vigente o latente vinculado a un lugar o una actividad de la agenda: nivel **naranja**;
  - un reclamo latente a tener en cuenta, o una movilización realizada en el último mes en la localidad ("Reclamo reciente"): nivel **amarillo**;
  - un reclamo de contexto, sin vínculo directo con la agenda: **sin color** (etiqueta "Contexto").
- Las fichas se ordenan de la más relevante a la menos relevante (rojo, naranja, amarillo, sin color).
- **Va al anexo B:** lo relevado y descartado, con el motivo (conflicto cerrado, más de 1 mes, reclamo a un privado, conflicto nacional, sin reclamo identificable).

### 5. Capturas
- Publicación de Instagram: captura de `https://www.instagram.com/p/<código>/embed/captioned/` con Chrome sin interfaz, ventana de 560 px de ancho y `--force-device-scale-factor=2`. Separá el flyer del texto con `scripts/recortar.ps1`.
- Facebook y X: captura del panel del navegador (`computer screenshot` o `zoom`). Las imágenes quedan en `tool-results` dentro de una ruta larga: copialas primero a una carpeta de ruta corta con `[IO.File]::Copy("\\?\<ruta>", ...)` y después recortá.

### 6. Informe PDF 9:16
- Usá como base `plantilla/informe.html`: páginas de 1080×1920 px, `@page { size: 1080px 1920px }`.
- **Diseño (acordado con el usuario el 26/11/2026; no volver al diseño anterior):**
  - Estética **neutra**: fondo blanco y texto gris oscuro. Nada de modo oscuro ni de un color por ficha.
  - **Color solo para menciones importantes**, en etiquetas, puntos del índice y frases puntuales (nunca fondos completos):
    - **rojo**: lo más relevante, sensible o que deba destacarse con mayor énfasis (por ejemplo, una convocatoria vinculada a la visita, y su fecha, hora y lugar dentro del texto);
    - **naranja**: relevante;
    - **amarillo**: a tener en cuenta;
    - el resto va sin color.
  - **Sin cuadros que saturen la vista:** no usar recuadros de cifras, bloques de color de título, columnas de posiciones, mosaicos de índice ni marcos de celular en las capturas. Los datos (cifras, repercusión, seguidores) van como texto en "Datos clave".
  - **Lectura rápida sin perder información:** quien lee no debe tener que completar la lectura para entender cada punto.
    - La portada abre con un **"Panorama"**: un párrafo que resume todo el barrido (convocatorias y reclamos, con lugar y hora cuando los hay).
    - Cada ficha abre con **"En síntesis"**: 2 a 4 oraciones con quién, qué, cuándo, dónde y si hay convocatoria publicada.
    - Después va el detalle completo para quien quiera profundizar: datos clave, qué reclaman, cronología en redes, posiciones de las partes y estado al día del relevamiento. No se omite información.
  - **Texto justificado** en todos los párrafos y oraciones (con corte de palabras para evitar huecos).
  - **No incluir:** la línea explicativa del alcance del relevamiento ("Convocatorias y reclamos locales y provinciales…"), leyendas o referencias de colores, notas al pie sobre la agenda o los anexos, ni aclaraciones como "Captura de publicación abierta" o "Capturas de publicaciones abiertas".
  - **Pies de página:** en la portada y en las páginas de publicaciones, solo el número de página; en las fichas, la fuente.
- Estructura:
  - portada: título, fecha y localidades, Panorama, agenda (las paradas con convocatoria en rojo) o "Para tener en cuenta", y contenido (lista con punto de color según nivel, título, una línea de estado y página);
  - por cada actor, una página de ficha (etiqueta de nivel, En síntesis y detalle) y una página de publicaciones: **capturas una debajo de la otra, centradas**, con el epígrafe (cuenta, red, fecha y hora) y el enlace inmediatamente debajo de cada captura;
  - **El informe NO incluye los anexos.** Se entregan tres PDF separados:
    1. `Barrido_<Localidad>_<fecha>.pdf`: portada y fichas.
    2. `Anexo_A_Registro_de_busquedas_<Localidad>.pdf`: red, consulta y resultado; pendientes con su motivo; resultados descartados por ambigüedad del nombre.
    3. `Anexo_B_Cuentas_y_no_incluidos_<Localidad>.pdf`: cuentas revisadas por resultado, cuentas citadas desde la búsqueda por palabras clave, relevados no incluidos y nota de método.
  - Cada anexo es un HTML aparte, con el mismo `<head>` de la plantilla y el mismo diseño neutro (sin colores salvo los niveles, texto justificado). Si no entra en una página, usá varias.
- **Enlace bajo cada publicación (obligatorio):** debajo de cada captura, al final de su bloque `.cap-blk`, después del epígrafe, va un enlace con texto fijo. Nunca se muestra la URL.
  - Formato: `<a class="lnk" href="URL">Link de la publicación &#8599;</a>`. El estilo `.lnk` está en la plantilla y Chrome conserva el enlace activo en el PDF.
  - Usá la URL limpia, sin parámetros de rastreo:
    - Instagram: `https://www.instagram.com/p/<código>/`;
    - X: `https://x.com/<cuenta>/status/<id>`;
    - Facebook: `https://www.facebook.com/<página>/posts/<id>`, `/reel/<id>/` o `/photo/?fbid=<id>`.
  - Nunca copies la URL de la barra del navegador, que trae `?multi_permalinks=`, `__cft__`, `hoisted_section_header_type`, etc. En Facebook, tomá el `href` del enlace de la fecha o de la foto de la publicación y conservá solo `story_fbid`, `id`, `v` o `fbid`.
  - **Perfiles personales:** no enlaces el perfil, porque la URL revelaría el nombre que se ocultó.
    - Si la publicación comparte una nota de un medio, enlazá la nota con el texto "Link de la publicación (nota original)".
    - Si no la comparte, usá `<span class="lnk off">Enlace reservado: perfil personal (disponible a pedido)</span>`.
  - Anotá las URL al momento de capturar, en `notas.md` o en la grilla, para no tener que volver a buscarlas.
  - Antes de entregar, contá los enlaces del PDF (`/URI (` en el archivo). Deben coincidir con las publicaciones que no son de perfiles personales.
- Generá el PDF con `scripts/generar_pdf.ps1`. Antes de entregar, revisá una hoja de contactos con todas las páginas (sección de verificación del script): nada puede quedar cortado ni superpuesto.
- Entrega: enviá el archivo y copiá el PDF a `%USERPROFILE%\Downloads`.

## Navegador para las redes
- **Preferido: Claude in Chrome** (herramientas `mcp__claude-in-chrome__*`). Es el Chrome del usuario, con sesiones estables en Facebook, Instagram y X.
  - Primero, `list_connected_browsers` y `tabs_context_mcp`.
  - Trabajá en pestañas nuevas del grupo propio, no toques las del usuario y cerralas al terminar.
- **Alternativa:** el navegador de la app (`mcp__Claude_Browser__*`). Meta lo trata como un dispositivo nuevo y puede cerrar la sesión.
- Si ninguno está disponible: Instagram se puede leer igual con `scripts/ig_sweep.ps1` (sin sesión). Avisá que Facebook, X y el descubrimiento de cuentas nuevas quedan pendientes.

## Empaquetado para subir a la cuenta
```powershell
Add-Type -AssemblyName System.IO.Compression, System.IO.Compression.FileSystem
$src = Join-Path $env:USERPROFILE ".claude\skills\barrido-redes"
$zip = Join-Path $env:USERPROFILE "Downloads\barrido-redes.zip"
if (Test-Path $zip) { Remove-Item $zip -Confirm:$false }
$fs = [IO.File]::Open($zip, 'Create'); $za = New-Object IO.Compression.ZipArchive($fs, 'Create')
Get-ChildItem $src -Recurse -File | ForEach-Object {
  $rel = 'barrido-redes/' + $_.FullName.Substring($src.Length + 1).Replace('\','/')
  [IO.Compression.ZipFileExtensions]::CreateEntryFromFile($za, $_.FullName, $rel) | Out-Null }
$za.Dispose(); $fs.Dispose()
```
El usuario lo sube en claude.ai: **Configuración > Plugins > Añadir > Subir plugin**. Con este formato funciona (verificado el 25/11/2026). Si la versión anterior no se reemplaza sola, el usuario debe quitarla desde el menú "…" del plugin y subir la nueva.

## Herramientas del entorno (PC del usuario, Windows)
- No hay Python. Usá PowerShell, Chrome (`C:\Program Files\Google\Chrome\Application\chrome.exe`) en modo `--headless=new` y System.Drawing para recortar.
- Llamá a Chrome con `cmd /c "...chrome.exe ... > archivo 2>nul"` para que la ejecución sea sincrónica (`--dump-dom`, `--screenshot`, `--print-to-pdf`).
- Si Instagram o Facebook muestran "Continuar" o la pantalla de inicio de sesión, pedile al usuario que inicie sesión en el panel. Nunca ingreses contraseñas.
