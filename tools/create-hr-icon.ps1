Add-Type -AssemblyName System.Drawing
$dest="C:\code\Lotus-hr-full-20261018\lotus_farm\public\images"
New-Item -Path $dest -ItemType Directory -Force | Out-Null
foreach ($size in @(192,512)) {
 foreach ($maskable in @($false,$true)){
  if ($maskable -and $size -ne 512){continue}
  $bmp=New-Object System.Drawing.Bitmap($size,$size)
  $g=[System.Drawing.Graphics]::FromImage($bmp)
  $g.SmoothingMode=[System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
  $color=[System.Drawing.ColorTranslator]::FromHtml("#e65338")
  $white=[System.Drawing.Brushes]::White
  $g.Clear($color)
  $scale=$size/512.0
  $g.TranslateTransform(0,0);$g.ScaleTransform($scale,$scale)
  $g.FillEllipse($white,192,104,128,128)
  $g.FillEllipse($white,114,228,284,194)
  $g.FillRectangle((New-Object System.Drawing.SolidBrush([System.Drawing.ColorTranslator]::FromHtml("#e65338"))),110,375,290,145)
  $font=New-Object System.Drawing.Font("Arial",119,[System.Drawing.FontStyle]::Bold,[System.Drawing.GraphicsUnit]::Pixel)
  $format=New-Object System.Drawing.StringFormat
  $format.Alignment=[System.Drawing.StringAlignment]::Center
  $g.DrawString("HR",$font,$white,(New-Object System.Drawing.RectangleF(0,315,512,145)),$format)
  $filename=if($maskable){"hr-icon-maskable-512.png"}else{"hr-icon-$size.png"}
  $bmp.Save((Join-Path $dest $filename),[System.Drawing.Imaging.ImageFormat]::Png)
  $font.Dispose();$format.Dispose();$g.Dispose();$bmp.Dispose()
 }
}
