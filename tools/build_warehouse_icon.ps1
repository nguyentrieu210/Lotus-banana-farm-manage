Add-Type -AssemblyName System.Drawing
$root = Resolve-Path '.'
$srcFile = Join-Path $root 'lotus_farm/public/images/lotus-agritech.jpg'
$source = [Drawing.Image]::FromFile($srcFile)
try {
 foreach ($size in @(192,512)) {
  $target = Join-Path $root ('lotus_farm/public/images/warehouse-icon-v3-' + $size + '.png')
  $bitmap = New-Object Drawing.Bitmap -ArgumentList $size,$size
  try {
   $g = [Drawing.Graphics]::FromImage($bitmap)
   try {
    $g.Clear([Drawing.Color]::White)
    $g.InterpolationMode=[Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
    $g.SmoothingMode=[Drawing.Drawing2D.SmoothingMode]::AntiAlias
    $g.PixelOffsetMode=[Drawing.Drawing2D.PixelOffsetMode]::HighQuality
    # Crop just the actual lotus emblem and the existing word LOTUS from brand art.
    $flower = New-Object Drawing.Rectangle 60,97,291,185
    $word = New-Object Drawing.Rectangle 361,109,235,65
    $flowerDest = New-Object Drawing.Rectangle ([int]($size*0.12)),([int]($size*0.12)),([int]($size*0.76)),([int]($size*0.51))
    $wordDest = New-Object Drawing.Rectangle ([int]($size*0.23)),([int]($size*0.67)),([int]($size*0.54)),([int]($size*0.19))
    $g.DrawImage($source,$flowerDest,$flower,[Drawing.GraphicsUnit]::Pixel)
    $g.DrawImage($source,$wordDest,$word,[Drawing.GraphicsUnit]::Pixel)
   } finally {$g.Dispose()}
   $bitmap.Save($target,[Drawing.Imaging.ImageFormat]::Png)
   Write-Output ("Created icon " + $target + " " + $size + "px")
  } finally {$bitmap.Dispose()}
 }
} finally {$source.Dispose()}
