# Build a lossless header asset without cutting off any of the LOTUS / Agritech letters.
# Detect the colored logo pixels from the ORIGINAL image; don't use hard-coded crop coordinates.
Add-Type -AssemblyName System.Drawing
$ErrorActionPreference='Stop'
$base=Resolve-Path '.'
$sourcePath=Join-Path $base 'lotus_farm/public/images/lotus-agritech.jpg'
$target=Join-Path $base 'lotus_farm/public/images/lotus-agritech-header-v2.png'
$image=[Drawing.Bitmap]::FromFile($sourcePath)
try {
  $minX=$image.Width;$minY=$image.Height;$maxX=0;$maxY=0
  for($y=0;$y -lt $image.Height;$y+=2) {
    for($x=0;$x -lt $image.Width;$x+=2) {
      $pixel=$image.GetPixel($x,$y)
      $highest=[Math]::Max($pixel.R,[Math]::Max($pixel.G,$pixel.B))
      $lowest=[Math]::Min($pixel.R,[Math]::Min($pixel.G,$pixel.B))
      if(($highest-$lowest) -gt 45 -and $highest -gt 85 -and $lowest -lt 205) {
        if($x -lt $minX){$minX=$x};if($x -gt $maxX){$maxX=$x}
        if($y -lt $minY){$minY=$y};if($y -gt $maxY){$maxY=$y}
      }
    }
  }
  if($maxX -le $minX -or $maxY -le $minY){throw 'No colored logo pixels found.'}
  $left=[Math]::Max(0,$minX-24)
  $top=[Math]::Max(0,$minY-20)
  $right=[Math]::Min($image.Width,$maxX+25)
  $bottom=[Math]::Min($image.Height,$maxY+21)
  $width=$right-$left;$height=$bottom-$top
  $bitmap=[Drawing.Bitmap]::new($width,$height)
  try {
    $graphics=[Drawing.Graphics]::FromImage($bitmap)
    try {
      $graphics.Clear([Drawing.Color]::White)
      $graphics.DrawImage($image,[Drawing.Rectangle]::new(0,0,$width,$height),
        [Drawing.Rectangle]::new($left,$top,$width,$height),[Drawing.GraphicsUnit]::Pixel)
    } finally {$graphics.Dispose()}
    $bitmap.Save($target,[Drawing.Imaging.ImageFormat]::Png)
  } finally {$bitmap.Dispose()}
  Write-Output ("Complete Lotus Agritech logo: $width x $height; bounds [$minX,$minY]-[$maxX,$maxY]")
} finally {$image.Dispose()}
