$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing
$images = Join-Path (Split-Path $PSScriptRoot -Parent) 'lotus_farm\public\images'
$set = @(
  @('warehouse-icon-v3-512.png','warehouse-icon-maskable-512.png'),
  @('buying-icon-512.png','buying-icon-maskable-512.png'),
  @('work-icon-v3-512.png','work-icon-maskable-512.png')
)
foreach ($pair in $set) {
  $sourcePath = Join-Path $images $pair[0]
  $destination = Join-Path $images $pair[1]
  if (-not (Test-Path $sourcePath)) { throw "Missing $sourcePath" }
  $img = [System.Drawing.Image]::FromFile($sourcePath)
  $bitmap = New-Object System.Drawing.Bitmap(512, 512)
  $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
  try {
    $graphics.Clear([System.Drawing.Color]::White)
    $graphics.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
    $graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::HighQuality
    $graphics.DrawImage($img, 112, 112, 288, 288)
    $bitmap.Save($destination, [System.Drawing.Imaging.ImageFormat]::Png)
    Write-Output "$($pair[1]) 512x512"
  } finally {
    $graphics.Dispose()
    $bitmap.Dispose()
    $img.Dispose()
  }
}
