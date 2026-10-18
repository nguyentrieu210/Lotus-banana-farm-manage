param([switch]$Rollback)
$ErrorActionPreference='Stop'
$root=Split-Path -Parent $PSScriptRoot
$override=Join-Path $PSScriptRoot 'compose.cccd-qr-v1.override.yaml'
$raw=& docker inspect lotus-frontend-1 --format '{{json .Config.Labels}}'
if($LASTEXITCODE -ne 0){throw 'Cannot find running Lotus frontend'}
$label=($raw | ConvertFrom-Json).'com.docker.compose.project.config_files'
if(-not $label){throw 'Missing original compose config'}
$files=@($label -split ',' | Where-Object {$_ -and (Test-Path $_) -and $_ -ne $override})
if($files.Count -lt 3){throw 'Incomplete original compose list; aborting'}
$cmd=@('compose','-p','lotus')
foreach($file in $files){$cmd+=@('-f',$file)}
if(-not $Rollback){$cmd+=@('-f',$override)}
$cmd+=@('up','-d','--no-deps','backend','frontend')
& docker @cmd
if($LASTEXITCODE -ne 0){throw 'Compose deployment failed'}
& docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}'
if($LASTEXITCODE -ne 0){throw 'Status check failed'}
