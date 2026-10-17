# Persist the two-PWA backend/frontend image in the primary Lotus Compose file.
# All other services, ports and credentials remain untouched.
$ErrorActionPreference='Stop'
$path='C:\Users\ADMIN\Documents\ChatGPT\a\lotus-runtime\compose.yaml'
$target='lotus-two-pwa:v6-20261016'
$backup=$path+'.before-two-pwa-20261016.bak'
$lines=[System.IO.File]::ReadAllLines($path,[System.Text.Encoding]::UTF8)
$service=''
$found=@()
for($i=0;$i -lt $lines.Length;$i++){
  if($lines[$i] -match '^  ([a-zA-Z0-9_-]+):\s*$'){
    $service=$Matches[1]
    continue
  }
  if(($service -eq 'backend' -or $service -eq 'frontend') -and $lines[$i] -match '^(    image:\s*)(\S+)(\s*)$'){
    $found+=$service
    $lines[$i]=$Matches[1]+$target+$Matches[3]
    $service=''
  }
}
if($found.Count -ne 2 -or -not $found.Contains('backend') -or -not $found.Contains('frontend')){
  throw 'Cannot isolate both images in the existing compose; no changes written.'
}
if(-not(Test-Path $backup)){Copy-Item -LiteralPath $path -Destination $backup -ErrorAction Stop}
[System.IO.File]::WriteAllLines($path,$lines,[System.Text.UTF8Encoding]::new($false))
Write-Output ('Updated only backend/frontend image to '+$target)
Write-Output ('Compose backup: '+$backup)
