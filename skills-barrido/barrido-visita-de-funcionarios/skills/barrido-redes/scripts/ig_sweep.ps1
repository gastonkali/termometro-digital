<#
Lee las últimas publicaciones (hasta 12) de cuentas públicas de Instagram mediante la
vista embebida pública (/<cuenta>/embed/). No requiere sesión.

Uso:
  .\ig_sweep.ps1 -Handles @('sutebabb','cgtbahia') -Desde '2026-11-14' -OutFile C:\temp\ig.txt

Salida: una línea por publicación posterior a -Desde:
  [cuenta] dd/MM HH:mm https://www.instagram.com/p/<código>/ :: <texto>
y un resumen por cuenta: "## cuenta : seguidores N, posts en embed N, desde <fecha>: N"
"SIN DATOS" = la cuenta no existe, es privada o Instagram no devolvió la vista.
#>
param(
  [Parameter(Mandatory)][string[]]$Handles,
  [Parameter(Mandatory)][string]$OutFile,
  [string]$Desde = (Get-Date).AddDays(-10).ToString('yyyy-MM-dd'),
  [string]$Tmp = (Join-Path $env:TEMP 'barrido_ig'),
  [string]$Chrome = 'C:\Program Files\Google\Chrome\Application\chrome.exe',
  [int]$PausaSeg = 4
)
New-Item -ItemType Directory -Force $Tmp | Out-Null
$d = [datetime]::ParseExact($Desde, 'yyyy-MM-dd', $null)
$since = [DateTimeOffset]::new($d.Year, $d.Month, $d.Day, 0, 0, 0, [TimeSpan]::FromHours(-3)).ToUnixTimeSeconds()
$res = New-Object System.Collections.Generic.List[string]
foreach ($h in $Handles) {
  $f = Join-Path $Tmp ("ig_" + ($h -replace '[^a-zA-Z0-9_.]', '_') + ".html")
  cmd /c "`"$Chrome`" --headless=new --disable-gpu --user-data-dir=`"$Tmp\chrome`" --virtual-time-budget=8000 --dump-dom https://www.instagram.com/$h/embed/ > `"$f`" 2>nul"
  $t = Get-Content $f -Raw -Encoding UTF8
  if (-not $t -or $t.IndexOf('shortcode_media') -lt 0) { $res.Add("## $h : SIN DATOS"); continue }
  $fc = [regex]::Match($t, 'followers_count\\":(\d+)').Groups[1].Value
  $blocks = $t -split 'shortcode_media\\":'
  $n = 0; $recent = 0
  foreach ($b in $blocks[1..($blocks.Length - 1)]) {
    $code = [regex]::Match($b, 'shortcode\\":\\"([A-Za-z0-9_-]+)').Groups[1].Value
    $ts = [regex]::Match($b, 'taken_at_timestamp\\":(\d+)').Groups[1].Value
    $cap = [regex]::Match($b, 'edge_media_to_caption.*?text\\":\\"(.*?)\\"\}').Groups[1].Value
    try { $cap = [regex]::Unescape([regex]::Unescape($cap)) } catch {}
    $cap = ($cap -replace '\s+', ' ')
    $fecha = if ($ts) { [DateTimeOffset]::FromUnixTimeSeconds([int64]$ts).ToOffset([TimeSpan]::FromHours(-3)).ToString('dd/MM HH:mm') } else { '?' }
    $n++
    if ($ts -and [int64]$ts -ge $since) {
      $recent++
      $res.Add("[$h] $fecha https://www.instagram.com/p/$code/ :: " + $cap.Substring(0, [Math]::Min(600, $cap.Length)))
    }
  }
  $res.Add("## $h : seguidores $fc, posts en embed $n, desde ${Desde}: $recent")
  Start-Sleep -Seconds $PausaSeg  # ritmo: evitar bloqueos de Instagram
}
$res | Out-File -FilePath $OutFile -Encoding utf8
"Listo: $OutFile"
