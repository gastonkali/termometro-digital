<#
Genera el PDF 9:16 a partir del HTML del informe y una hoja de contactos para revisar.

Uso:
  .\generar_pdf.ps1 -Html C:\inf\informe.html -Pdf C:\inf\Informe.pdf
  .\generar_pdf.ps1 -Html C:\inf\informe.html -Hoja C:\temp\hoja.png -Paginas 12

Con -Hoja genera una imagen con todas las páginas reducidas (6 por fila) para verificar
que nada quede cortado ni superpuesto. Leer esa imagen antes de entregar.
#>
param(
  [Parameter(Mandatory)][string]$Html,
  [string]$Pdf,
  [string]$Hoja,
  [int]$Paginas = 12,
  [string]$Tmp = (Join-Path $env:TEMP 'barrido_pdf'),
  [string]$Chrome = 'C:\Program Files\Google\Chrome\Application\chrome.exe'
)
New-Item -ItemType Directory -Force $Tmp | Out-Null
$dir = Split-Path $Html -Parent
$uriBase = 'file:///' + ($dir -replace '\\', '/')
if ($Pdf) {
  cmd /c "`"$Chrome`" --headless=new --disable-gpu --user-data-dir=`"$Tmp\chrome`" --no-pdf-header-footer --virtual-time-budget=5000 --print-to-pdf=`"$Pdf`" $uriBase/$(Split-Path $Html -Leaf) 2>nul"
  $b = [IO.File]::ReadAllText($Pdf, [Text.Encoding]::GetEncoding(28591))
  "PDF: $Pdf · páginas: $(([regex]::Matches($b, '/Type\s*/Page[^s]')).Count)"
}
if ($Hoja) {
  $c = [IO.File]::ReadAllText($Html)
  $s = $c.Replace('</style>', 'body{display:flex;flex-wrap:wrap;width:6480px;zoom:0.29} .page{flex:none}</style>')
  $tmpHtml = Join-Path $dir '_hoja.html'
  [IO.File]::WriteAllText($tmpHtml, $s, (New-Object Text.UTF8Encoding($false)))
  $filas = [Math]::Ceiling($Paginas / 6)
  $alto = [int](1920 * 0.29 * $filas) + 2
  cmd /c "`"$Chrome`" --headless=new --disable-gpu --hide-scrollbars --user-data-dir=`"$Tmp\chrome2`" --window-size=1880,$alto --virtual-time-budget=5000 --screenshot=`"$Hoja`" $uriBase/_hoja.html 2>nul"
  Remove-Item $tmpHtml -Confirm:$false
  "Hoja: $Hoja"
}
