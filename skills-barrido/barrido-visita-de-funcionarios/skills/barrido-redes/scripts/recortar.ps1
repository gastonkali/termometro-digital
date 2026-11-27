<#
Recorta una captura y opcionalmente tapa zonas (nombres/fotos de perfiles personales).

Uso:
  .\recortar.ps1 -Origen C:\cap\post.jpg -Destino C:\inf\img\c1.png -X 105 -Y 80 -Ancho 578 -Alto 588 -Tapar @(,@(6,4,140,36))

-Tapar: lista de rectángulos @(x, y, ancho, alto) en coordenadas del recorte.
Si la captura está en una ruta larga (tool-results), primero copiala:
  [IO.File]::Copy("\\?\<ruta larga>", "C:\cap\post.jpg", $true)
#>
param(
  [Parameter(Mandatory)][string]$Origen,
  [Parameter(Mandatory)][string]$Destino,
  [int]$X = 0, [int]$Y = 0,
  [Parameter(Mandatory)][int]$Ancho,
  [Parameter(Mandatory)][int]$Alto,
  [object[]]$Tapar
)
Add-Type -AssemblyName System.Drawing
$img = [System.Drawing.Image]::FromFile($Origen)
$bmp = New-Object System.Drawing.Bitmap $Ancho, $Alto
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.DrawImage($img, (New-Object System.Drawing.Rectangle 0, 0, $Ancho, $Alto), (New-Object System.Drawing.Rectangle $X, $Y, $Ancho, $Alto), [System.Drawing.GraphicsUnit]::Pixel)
if ($Tapar) {
  $br = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(255, 58, 59, 60))
  foreach ($r in $Tapar) { $g.FillRectangle($br, $r[0], $r[1], $r[2], $r[3]) }
}
$g.Dispose(); $img.Dispose()
$bmp.Save($Destino, [System.Drawing.Imaging.ImageFormat]::Png); $bmp.Dispose()
"OK $Destino"
