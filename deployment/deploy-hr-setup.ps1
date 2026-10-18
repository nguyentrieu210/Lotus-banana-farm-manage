param([switch]$Rollback)
$ErrorActionPreference='Stop'
$override=Join-Path $PSScriptRoot 'compose.hr-setup-v1.override.yaml'
$labels=((& docker inspect lotus-frontend-1 --format '{{json .Config.Labels}}') | ConvertFrom-Json)
$config=$labels.'com.docker.compose.project.config_files'
if($LASTEXITCODE -ne 0 -or -not $config){throw 'Cannot find live Lotus Compose stack'}
$files=@($config -split ',' | Where-Object {$_ -and (Test-Path $_) -and $_ -ne $override})
if($files.Count -lt 3){throw 'Incomplete live Compose stack'}
$argsList=@('compose','-p','lotus')
foreach($file in $files){$argsList+=@('-f',$file)}
if(-not $Rollback){$argsList+=@('-f',$override)}
$argsList+=@('up','-d','--no-deps','backend','frontend','queue-short')
& docker @argsList
if($LASTEXITCODE -ne 0){throw 'Deploy failed'}
& docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}'
