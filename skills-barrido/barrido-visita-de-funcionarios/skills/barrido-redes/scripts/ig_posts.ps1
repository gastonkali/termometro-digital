<#
Lee el texto de publicaciones sueltas de Instagram (por código) mediante la vista embebida
pública (/p/<código>/embed/captioned/). No requiere sesión. Sirve para leer los resultados
de la búsqueda por palabra clave (paso 3b) sin abrir cada publicación con la cuenta del usuario.

Uso:
  .\ig_posts.ps1 -Codigos @('DgK7puqxVuW','DgGCXrQMkg1') -OutFile C:\inf\ig_posts.txt

Salida: una línea por publicación: <código> | <cuenta> | <texto (hasta 700 caracteres)>
#>
param(
  [Parameter(Mandatory)][string[]]$Codigos,
  [Parameter(Mandatory)][string]$OutFile,
  [string]$Tmp = (Join-Path $env:TEMP 'barrido_igp'),
  [string]$Chrome = 'C:\Program Files\Google\Chrome\Application\chrome.exe',
  [int]$PausaSeg = 4
)
New-Item -ItemType Directory -Force $Tmp | Out-Null
$res = New-Object System.Collections.Generic.List[string]
foreach ($c in $Codigos) {
  $f = Join-Path $Tmp ("p_" + ($c -replace '[^A-Za-z0-9_-]', '_') + ".html")
  cmd /c "`"$Chrome`" --headless=new --disable-gpu --user-data-dir=`"$Tmp\chrome`" --virtual-time-budget=8000 --dump-dom https://www.instagram.com/p/$c/embed/captioned/ > `"$f`" 2>nul"
  $t = Get-Content $f -Raw -Encoding UTF8
  if (-not $t) { $res.Add("$c | ? | SIN DATOS"); continue }
  $user = [regex]::Match($t, 'class="UsernameText"[^>]*>([^<]+)<').Groups[1].Value
  $cap = [regex]::Match($t, '(?s)class="Caption"[^>]*>(.*?)<div class="CaptionComments').Groups[1].Value
  if (-not $cap) { $cap = [regex]::Match($t, '(?s)class="Caption"[^>]*>(.*?)</div>').Groups[1].Value }
  $cap = [Net.WebUtility]::HtmlDecode(($cap -replace '<br\s*/?>', ' ' -replace '<[^>]+>', ' ')) -replace '\s+', ' '
  if ($user -and $cap.StartsWith($user)) { $cap = $cap.Substring($user.Length).Trim() }
  $res.Add("$c | $user | " + $cap.Substring(0, [Math]::Min(700, $cap.Length)))
  Start-Sleep -Seconds $PausaSeg
}
$res | Out-File -FilePath $OutFile -Encoding utf8
"Listo: $OutFile ($($res.Count))"
