$ErrorActionPreference='Stop'
$ProgressPreference='SilentlyContinue'
$base='http://localhost:8080'
$items=@(
 @{Label='Kho Lotus';Route='warehouse';Worker='warehouse_service_worker';Manifest='warehouse_manifest'},
 @{Label='Cong viec ngoai Vuon';Route='work';Worker='work_service_worker';Manifest='work_manifest'}
)
$ids=@()
$icons=@()
foreach($app in $items){
 $manifestUrl="$base/api/method/lotus_farm.web.$($app.Manifest)"
 $resp=Invoke-WebRequest -UseBasicParsing -Uri $manifestUrl -TimeoutSec 15
 if($resp.StatusCode -ne 200){throw "Manifest HTTP failed $($app.Route)"}
 $manifestText=if($resp.Content -is [byte[]]){[System.Text.Encoding]::UTF8.GetString($resp.Content)}else{[string]$resp.Content}
 $m=$manifestText | ConvertFrom-Json
 $expect="/" + $app.Route
 Write-Output ("CHECK VALUES: id=["+$m.id+"] start=["+$m.start_url+"] scope=["+$m.scope+"] expected=["+$expect+"]")
 if($m.id -ne $expect -or $m.start_url -ne $expect -or $m.scope -ne $expect){throw "Manifest identity invalid $($app.Route)"}
 if($m.display -ne 'standalone'){throw "Not standalone $($app.Route)"}
 $ids+= $m.id
 if($m.icons.Count -lt 2){throw "Icons missing $($app.Route)"}
 foreach($icon in $m.icons){
  $i=Invoke-WebRequest -UseBasicParsing -Uri "$base$($icon.src)" -TimeoutSec 15
  if($i.StatusCode -ne 200){throw "Icon HTTP failed $($icon.src)"}
  $icons+=$icon.src
 }
 Write-Output "MANIFEST OK: $($m.name) | id=$($m.id), scope=$($m.scope), icons=$($m.icons.Count)"
 $workerUrl="$base/api/method/lotus_farm.web.$($app.Worker)"
 $response=Invoke-WebRequest -UseBasicParsing -Uri $workerUrl -TimeoutSec 15
 if($response.StatusCode -ne 200){throw "Worker failed $($app.Route)"}
 if($response.Headers['Service-Worker-Allowed'] -ne "/$($app.Route)"){throw "Scope header mismatch for $($app.Route)"}
 $workerText=if($response.Content -is [byte[]]){[System.Text.Encoding]::UTF8.GetString($response.Content)}else{[string]$response.Content}
 if($workerText -match '__WORK_ASSETS__|__WAREHOUSE_ASSETS__|__WORK_VERSION__|__WAREHOUSE_VERSION__'){throw "Worker placeholders not compiled $($app.Route)"}
 if($workerText -notmatch 'lotus-'){throw "Worker cache namespace absent"}
 Write-Output "SERVICE WORKER OK: $($app.Route) | scope=$($response.Headers['Service-Worker-Allowed']), MIME=$($response.Headers['Content-Type'])"
 $status=(& curl.exe -sSI -o NUL -w '%{http_code}' --max-time 15 "$base/$($app.Route)")
 if($status -ne '301'){throw "Expected guest login redirect: $($app.Route), got $status"}
 Write-Output "AUTH PAGE OK: /$($app.Route) redirects unauthenticated users"
}
if(($ids | Select-Object -Unique).Count -ne 2){throw 'Same manifest ID'}
if(($icons | Select-Object -Unique).Count -ne 4){throw 'Repeated icons'}
Write-Output 'TWO_SEPARATE_PWAS_OK'
