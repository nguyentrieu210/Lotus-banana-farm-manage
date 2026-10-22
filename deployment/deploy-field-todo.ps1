$ErrorActionPreference = 'Stop'
$siteContainer = docker inspect lotus-create-site-1 | ConvertFrom-Json | Select-Object -First 1
if (-not $siteContainer) { throw "No existing Lotus create-site container" }
$vars = @{}
foreach ($value in $siteContainer.Config.Env) {
  $pos = $value.IndexOf('=')
  if ($pos -gt 0) { $vars[$value.Substring(0,$pos)] = $value.Substring($pos+1) }
}
foreach ($key in @('DB_ROOT_PASSWORD','LOTUS_ADMIN_PASSWORD')) {
  if (-not $vars.ContainsKey($key)) { throw "Existing Lotus runtime is missing $key" }
  Set-Item "Env:$key" $vars[$key]
}
$env:LOTUS_IMAGE = 'lotus-field-todo:v1-20261021'
$compose = 'C:\code\lotus-release-land\deployment\compose.release.yaml'
docker compose -p lotus -f $compose config --quiet
if ($LASTEXITCODE -ne 0) { throw "Compose validation failed" }
docker compose -p lotus -f $compose up -d --no-deps backend frontend queue-short queue-long scheduler websocket
if ($LASTEXITCODE -ne 0) { throw "Compose deploy failed" }
Write-Host 'DEPLOYED field-todo release'
