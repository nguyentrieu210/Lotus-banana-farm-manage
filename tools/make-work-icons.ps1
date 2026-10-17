Add-Type -AssemblyName System.Drawing
$destination = 'C:\code\Lotus-banana-farm-manage\lotus_farm\public\images'
New-Item -ItemType Directory -Path $destination -Force | Out-Null
foreach ($size in @(192,512)) {
    $bmp = New-Object System.Drawing.Bitmap($size,$size)
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    $g.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
    $g.Clear([System.Drawing.Color]::FromArgb(239,248,242))
    $brush = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(22,100,60))
    $g.FillEllipse($brush,$size*0.13,$size*0.13,$size*0.74,$size*0.74)
    $pen = New-Object System.Drawing.Pen([System.Drawing.Color]::White,[float]($size*0.067))
    $pen.StartCap = [System.Drawing.Drawing2D.LineCap]::Round
    $pen.EndCap = [System.Drawing.Drawing2D.LineCap]::Round
    $pen.LineJoin = [System.Drawing.Drawing2D.LineJoin]::Round
    $points = [System.Drawing.PointF[]]@(
      (New-Object System.Drawing.PointF([float]($size*0.30),[float]($size*0.51))),
      (New-Object System.Drawing.PointF([float]($size*0.44),[float]($size*0.65))),
      (New-Object System.Drawing.PointF([float]($size*0.71),[float]($size*0.37)))
    )
    $g.DrawLines($pen,$points)
    $file = Join-Path $destination ("work-icon-" + $size + ".png")
    $bmp.Save($file,[System.Drawing.Imaging.ImageFormat]::Png)
    $pen.Dispose();$brush.Dispose();$g.Dispose();$bmp.Dispose()
    Write-Output $file
}