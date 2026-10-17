# Separate Home Screen identity for "Công việc ngoài Vườn".
# Rendered locally using the existing Windows System.Drawing installation.
Add-Type -AssemblyName System.Drawing
$ErrorActionPreference='Stop'
$base=Resolve-Path '.'
$folder=Join-Path $base 'lotus_farm/public/images'
foreach($size in @(192,512)){
  $bitmap=[System.Drawing.Bitmap]::new($size,$size)
  $g=[System.Drawing.Graphics]::FromImage($bitmap)
  $g.SmoothingMode=[System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
  $g.InterpolationMode=[System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
  $g.PixelOffsetMode=[System.Drawing.Drawing2D.PixelOffsetMode]::HighQuality
  $g.Clear([System.Drawing.Color]::FromArgb(243,249,244))
  $baseBrush=[System.Drawing.SolidBrush]::new([System.Drawing.Color]::FromArgb(24,105,68))
  $white=[System.Drawing.SolidBrush]::new([System.Drawing.Color]::White)
  $accent=[System.Drawing.SolidBrush]::new([System.Drawing.Color]::FromArgb(245,125,63))
  try{
    $g.FillEllipse($baseBrush,[float]($size*.13),[float]($size*.13),[float]($size*.74),[float]($size*.74))
    # White branch, curved leaves and a small orange badge distinguish Work from Warehouse logo.
    $stem=[System.Drawing.Pen]::new([System.Drawing.Color]::White,[float]($size*.045))
    $stem.StartCap=[System.Drawing.Drawing2D.LineCap]::Round
    $stem.EndCap=[System.Drawing.Drawing2D.LineCap]::Round
    try{
      $g.DrawBezier($stem,[float]($size*.5),[float]($size*.72),[float]($size*.47),[float]($size*.58),[float]($size*.54),[float]($size*.48),[float]($size*.56),[float]($size*.32))
      $leaf1=[System.Drawing.Drawing2D.GraphicsPath]::new()
      $leaf1.StartFigure()
      $leaf1.AddBezier([float]($size*.53),[float]($size*.53),[float]($size*.32),[float]($size*.50),[float]($size*.29),[float]($size*.36),[float]($size*.27),[float]($size*.32))
      $leaf1.AddBezier([float]($size*.27),[float]($size*.32),[float]($size*.47),[float]($size*.31),[float]($size*.53),[float]($size*.42),[float]($size*.53),[float]($size*.53))
      $leaf1.CloseFigure()
      $g.FillPath($white,$leaf1)
      $leaf1.Dispose()
      $leaf2=[System.Drawing.Drawing2D.GraphicsPath]::new()
      $leaf2.StartFigure()
      $leaf2.AddBezier([float]($size*.55),[float]($size*.44),[float]($size*.54),[float]($size*.25),[float]($size*.70),[float]($size*.25),[float]($size*.76),[float]($size*.24))
      $leaf2.AddBezier([float]($size*.76),[float]($size*.24),[float]($size*.75),[float]($size*.44),[float]($size*.67),[float]($size*.48),[float]($size*.55),[float]($size*.44))
      $leaf2.CloseFigure()
      $g.FillPath($white,$leaf2)
      $leaf2.Dispose()
    } finally{$stem.Dispose()}
    $g.FillEllipse($accent,[float]($size*.62),[float]($size*.66),[float]($size*.17),[float]($size*.17))
    $check=[System.Drawing.Pen]::new([System.Drawing.Color]::White,[float]($size*.026))
    $check.StartCap=[System.Drawing.Drawing2D.LineCap]::Round
    $check.EndCap=[System.Drawing.Drawing2D.LineCap]::Round
    try {
      $g.DrawLine($check,[float]($size*.66),[float]($size*.745),[float]($size*.69),[float]($size*.772))
      $g.DrawLine($check,[float]($size*.69),[float]($size*.772),[float]($size*.748),[float]($size*.705))
    } finally {$check.Dispose()}
    $dest=Join-Path $folder ('work-icon-v3-'+$size+'.png')
    $bitmap.Save($dest,[System.Drawing.Imaging.ImageFormat]::Png)
    Write-Output ('Rendered separate Work icon '+$size+'x'+$size)
  }finally{$accent.Dispose();$white.Dispose();$baseBrush.Dispose();$g.Dispose();$bitmap.Dispose()}
}
