param([switch]$Rollback)
$ErrorActionPreference='Stop'
$override=Join-Path $PSScriptRoot 'compose.hr-mobile-v1.override.yaml'
$label=((& docker inspect lotus-frontend-1 --format '{{json .Config.Labels}}') | ConvertFrom-Json).'com.docker.compose.project.config_files'
if($LASTEXITCODE -ne 0 -or -not $label){throw 'Cannot inspect current Lotus stack'}
$files=@($label -split ',' | Where-Object {$_ -and $_ -ne $override -and (Test-Path $_)})
if($files.Count -lt 3){throw 'Incomplete Compose stack. No deployment.'}
$argsList=@('compose','-p','lotus')
foreach($file in $files){$argsList+=@('-f',$file)}
if(-not $Rollback){$argsList+=@('-f',$override)}
$argsList+=@('up','-d','--no-deps','backend','frontend')
& docker @argsList
if($LASTEXITCODE -ne 0){throw 'Cannot deploy Lotus HR mobile'}
& docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}'
