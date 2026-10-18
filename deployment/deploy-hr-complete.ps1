param([switch]$Rollback, [ValidateSet('Backend','All')][string]$Phase='All')
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$override = Join-Path $PSScriptRoot "compose.hr-complete-v1.override.yaml"
$docker = Get-Command docker -ErrorAction Stop
# Same compose files from the CURRENT running Lotus instance, preserving the entire stack.
$rawLabels = & docker inspect lotus-frontend-1 --format '{{json .Config.Labels}}'
$labels = $rawLabels | ConvertFrom-Json
$label = $labels.'com.docker.compose.project.config_files'
if ($LASTEXITCODE -ne 0 -or -not $label) { throw "Cannot read live Compose file list" }
$files = @($label -split ',' | Where-Object { $_ -and (Test-Path $_) })
if ($files.Count -lt 3) { throw "Current Compose file list incomplete; no live change" }
$argsList = @("compose","-p","lotus")
foreach ($file in $files) {
  # On redeploy, ignore prior HR override if already present.
  if ($file -eq $override) { continue }
  $argsList += @("-f", $file)
}
if (-not $Rollback) { $argsList += @("-f",$override) }
$argsList += @('up','-d','--no-deps')
if ($Phase -eq 'Backend') { $argsList += 'backend' }
else { $argsList += @('backend','frontend','queue-short','queue-long','scheduler') }
Write-Host "Compose files: $($files.Count); mode: $(if ($Rollback) {'ROLLBACK IMAGE'} else {'HR COMPLETE LIVE'})"
& docker @argsList
if ($LASTEXITCODE -ne 0) { throw "Compose deployment failed" }
& docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}'
if ($LASTEXITCODE -ne 0) { throw "Docker status failed" }