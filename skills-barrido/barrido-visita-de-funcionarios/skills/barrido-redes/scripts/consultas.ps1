<#
Genera la grilla de búsquedas por palabras clave (usuarios comunes) para una localidad,
en X, Facebook e Instagram, como lista de control para completar durante el barrido.

Uso:
  .\consultas.ps1 -Localidad 'La Plata' -Alias @('#LaPlata','platense','platenses') `
    -Barrios @('Tolosa','City Bell','Gonnet','Los Hornos','Villa Elisa','Melchor Romero') `
    -Lugares @('Plaza Moreno','Casa de Gobierno') -Autoridad @('Kicillof','gobernador') `
    -CuentasOficiales @('Kicillofok','Julio_Alak') -Desde '2026-11-19' -FechaEvento '2026-11-26' `
    -Ambigua -OutFile C:\inf\consultas.md

Salida: un .md con una fila por búsqueda (id, red, tipo, consulta, URL, columna "Resultado"
para completar). El registro completo va al anexo del informe.
-Ambigua: la localidad también es una palabra común (La Plata, Junín, Mercedes, Dolores...).
  No cambia las consultas (nunca se excluye el término): marca que hay que filtrar después.
#>
param(
  [Parameter(Mandatory)][string]$Localidad,
  [string[]]$Alias = @(),
  [string[]]$Barrios = @(),
  [string[]]$Lugares = @(),
  [string[]]$Autoridad = @('Kicillof', 'gobernador'),
  [string[]]$CuentasOficiales = @('Kicillofok'),
  [Parameter(Mandatory)][string]$Desde,
  [Parameter(Mandatory)][string]$FechaEvento,
  [switch]$Ambigua,
  [Parameter(Mandatory)][string]$OutFile
)
$es = [Globalization.CultureInfo]::GetCultureInfo('es-AR')
$f = [datetime]::ParseExact($FechaEvento, 'yyyy-MM-dd', $null)
$dia = $es.DateTimeFormat.GetDayName($f.DayOfWeek)
$fechas = @($dia, 'mañana', 'hoy', $f.ToString('d/M'), $f.ToString('dd/MM'), "$($f.Day) de $($es.DateTimeFormat.GetMonthName($f.Month))") | Select-Object -Unique

# Grupos de términos (en X se combinan con OR; Facebook e Instagram no aceptan OR)
$convoca = @('marcha','marchamos','movilización','movilizamos','concentración','concentramos','convocamos','convocatoria','"nos vemos"','"todos a"')
$medidas = @('corte','cortan','cortamos','piquete','paro','protesta','ruidazo','cacerolazo','abrazo','"olla popular"','asamblea','autoconvocados','escrache')
$reclamo = @('reclamo','reclamamos','reclaman','vecinos','"basta de"','denuncia','denuncian','"sin respuesta"','abandono','"nadie nos"')
$temas   = @('luz','agua','cloacas','inundación','inundados','baches','inseguridad','IOMA','escuela','hospital','colectivos','basura','despidos','salarios')
$visita  = @('visita','viene','"lo esperamos"','acto','inauguración','inaugura','recorrida')
$corto   = @('marcha','corte','protesta','reclamo','paro','concentración','vecinos','autoconvocados')

function OrG($a) { '(' + ($a -join ' OR ') + ')' }
function Q($s) { if ($s -match '^[#@]' -or $s -notmatch '\s') { $s } else { '"' + $s + '"' } }
$loc = Q $Localidad.ToLower()
$since = " since:$Desde"
$rows = New-Object System.Collections.Generic.List[object]
function Add($red, $tipo, $consulta, $url) { $rows.Add([pscustomobject]@{ Red = $red; Tipo = $tipo; Consulta = $consulta; URL = $url }) }
function XUrl($q) { 'https://x.com/search?q=' + [uri]::EscapeDataString($q) + '&f=live' }
$fbRecent = '&filters=eyJyZWNlbnRfcG9zdHM6MCI6IntcIm5hbWVcIjpcInJlY2VudF9wb3N0c1wiLFwiYXJnc1wiOlwiXCJ9In0%3D'
function FbUrl($q) { 'https://www.facebook.com/search/posts?q=' + [uri]::EscapeDataString($q) + $fbRecent }
function FbGrp($q) { 'https://www.facebook.com/search/groups?q=' + [uri]::EscapeDataString($q) }

# ---------- X ----------
foreach ($g in @(@('convocatoria', $convoca), @('medidas', $medidas), @('reclamos', $reclamo))) {
  $q = "$loc $(OrG $g[1])$since"; Add 'X' "Localidad + $($g[0])" $q (XUrl $q)
}
$q = "$loc $(OrG $temas) $(OrG @('reclamo','vecinos','sin','basta','denuncia'))$since"; Add 'X' 'Localidad + temas latentes' $q (XUrl $q)
$q = "$(OrG $Autoridad) $loc $(OrG ($visita + ($fechas | ForEach-Object { Q $_ })))$since"; Add 'X' 'Autoridad + localidad + visita/fecha' $q (XUrl $q)
if ($Alias.Count) { $q = "$(OrG ($Alias | ForEach-Object { Q $_ })) $(OrG ($convoca[0..5] + $medidas[0..5] + $reclamo[0..2]))$since"; Add 'X' 'Alias/hashtag/gentilicio + conflicto' $q (XUrl $q) }
for ($i = 0; $i -lt $Barrios.Count; $i += 6) {
  $b = $Barrios[$i..([Math]::Min($i + 5, $Barrios.Count - 1))] | ForEach-Object { Q $_ }
  $q = "$(OrG $b) $(OrG $corto)$since"; Add 'X' 'Barrios + conflicto' $q (XUrl $q)
}
if ($Lugares.Count) { $q = "$(OrG ($Lugares | ForEach-Object { Q $_ })) $(OrG ($corto + $fechas[0..1]))$since"; Add 'X' 'Lugares de la agenda' $q (XUrl $q) }
foreach ($c in $CuentasOficiales) {
  $q = "to:$c$since"; Add 'X' "Respuestas a @$c" $q (XUrl $q)
  $q = "@$c $loc$since"; Add 'X' "Menciones a @$c + localidad" $q (XUrl $q)
}
$q = "near:`"$Localidad`" within:15km $(OrG $corto)$since"; Add 'X' 'Geolocalizadas (complemento)' $q (XUrl $q)

# ---------- Facebook (sin OR: una consulta por término) ----------
foreach ($t in @('marcha','corte','protesta','reclamo vecinos','autoconvocados','concentración','paro')) {
  $q = "$Localidad $t"; Add 'Facebook' 'Publicaciones recientes' $q (FbUrl $q)
}
foreach ($a in $Autoridad) { $q = "$a $Localidad"; Add 'Facebook' 'Autoridad + localidad' $q (FbUrl $q) }
foreach ($b in $Barrios) { $q = "$b reclamo vecinos"; Add 'Facebook' 'Barrio + reclamo' $q (FbUrl $q) }
foreach ($l in $Lugares) { $q = "$l $Localidad"; Add 'Facebook' 'Lugar de la agenda' $q (FbUrl $q) }
$q = "vecinos $Localidad"; Add 'Facebook' 'Grupos vecinales (abrir y leer recientes)' $q (FbGrp $q)
foreach ($b in $Barrios) { $q = "vecinos $b"; Add 'Facebook' 'Grupos vecinales por barrio' $q (FbGrp $q) }

# ---------- Instagram ----------
$tags = @($Localidad) + $Barrios | ForEach-Object { ($_.ToLower() -replace '[^a-z0-9ñáéíóú]', '') } | Select-Object -Unique
foreach ($t in $tags) { Add 'Instagram' 'Hashtag (pestaña Recientes si existe)' "#$t" "https://www.instagram.com/explore/tags/$([uri]::EscapeDataString($t))/" }
foreach ($l in $Lugares) { Add 'Instagram' 'Ubicación (panel Buscar > Lugares)' $l 'https://www.instagram.com/explore/' }
foreach ($t in @('marcha','corte','reclamo','protesta')) { $q = "$t $($Localidad.ToLower())"; Add 'Instagram' 'Palabra clave (panel Buscar)' $q 'https://www.instagram.com/explore/' }
Add 'Instagram' 'Comentarios en publicaciones oficiales y de medios sobre la visita' '(abrir los posteos de la autoridad, el municipio y los medios locales)' ''

# ---------- Salida ----------
$n = 0
$sb = New-Object Text.StringBuilder
[void]$sb.AppendLine("# Registro de búsquedas por palabras clave · $Localidad · evento $FechaEvento")
[void]$sb.AppendLine("")
if ($Ambigua) { [void]$sb.AppendLine("> Localidad con nombre ambiguo: NO excluir el término. Clasificar cada resultado (ciudad / dinero u otro sentido / ambigua) y abrir las ambiguas. Contar las descartadas.`n") }
foreach ($red in 'X', 'Facebook', 'Instagram') {
  $rr = $rows | Where-Object Red -eq $red
  [void]$sb.AppendLine("## $red ($($rr.Count) búsquedas · ritmo: máx. 10 seguidas, 10 s entre cada una)")
  [void]$sb.AppendLine("| # | Tipo | Consulta | Resultado |"); [void]$sb.AppendLine("|---|---|---|---|")
  foreach ($r in $rr) { $n++; $u = if ($r.URL) { " [abrir]($($r.URL))" } else { '' }; [void]$sb.AppendLine("| $n | $($r.Tipo) | ``$($r.Consulta)``$u | pendiente |") }
  [void]$sb.AppendLine("")
}
[IO.File]::WriteAllText($OutFile, $sb.ToString(), (New-Object Text.UTF8Encoding($false)))
"Listo: $OutFile · X: $(($rows | ? Red -eq 'X').Count) · Facebook: $(($rows | ? Red -eq 'Facebook').Count) · Instagram: $(($rows | ? Red -eq 'Instagram').Count)"
