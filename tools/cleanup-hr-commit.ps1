$root='C:\code\Lotus-hr-full-20261018'
$files=@('frontend\src\HrApp.vue','lotus_farm\hr_setup.py','lotus_farm\push_notifications.py')
$utf8=New-Object System.Text.UTF8Encoding $false
foreach($relative in $files){
  $path=Join-Path $root $relative
  $raw=[System.IO.File]::ReadAllText($path)
  $clean=[regex]::Replace($raw,'[ \t]+(?=\r?\n)','')
  $clean=$clean.TrimEnd([char]13,[char]10)+[Environment]::NewLine
  [System.IO.File]::WriteAllText($path,$clean,$utf8)
  Write-Output ('cleaned '+$relative)
}