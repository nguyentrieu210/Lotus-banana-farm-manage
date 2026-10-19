param([string]$BaseUrl = 'http://localhost:8080')
$ErrorActionPreference = 'Stop'
$manifest = '/home/frappe/frappe-bench/apps/lotus_farm/lotus_farm/public/frontend/.vite/manifest.json'
function Get-StockManifest([string]$Container) {
  $raw = (& docker exec $Container cat $manifest) -join "`n"
  if ($LASTEXITCODE -ne 0) { throw "Cannot read manifest inside $Container" }
  return $raw | ConvertFrom-Json
}
$api = Get-StockManifest 'lotus-backend-1'
$ui = Get-StockManifest 'lotus-frontend-1'
$backendEntry = $api.'index.html'
$frontendEntry = $ui.'index.html'
if (!$backendEntry -or !$frontendEntry) { throw 'index.html entry missing (serves every /lotus route, including /lotus/kho)' }
if ($backendEntry.file -ne $frontendEntry.file) {
  throw "Stale build! Backend uses $($backendEntry.file), frontend uses $($frontendEntry.file)"
}
if (($backendEntry.css -join '|') -ne ($frontendEntry.css -join '|')) {
  throw "Stale stylesheet manifest! Backend CSS and frontend CSS differ"
}
$asset = "$BaseUrl/assets/lotus_farm/frontend/$($backendEntry.file)"
$response = Invoke-WebRequest -Uri $asset -Method Head -UseBasicParsing
if ($response.StatusCode -ne 200) {
  throw "App file not available at $asset : $($response.StatusCode)"
}
Write-Host "OK: $($backendEntry.file) is served by both backend and frontend"
Write-Host "OK: $asset returned HTTP $($response.StatusCode)"
