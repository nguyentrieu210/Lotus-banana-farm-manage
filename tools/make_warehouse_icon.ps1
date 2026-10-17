Add-Type -AssemblyName System.Drawing
$ErrorActionPreference = 'Stop'
$base = Resolve-Path '.'
$sourcePath = Join-Path $base 'lotus_farm/public/images/lotus-agritech.jpg'
$outputDir = Join-Path $base 'lotus_farm/public/images'
$source = [System.Drawing.Image]::FromFile($sourcePath)
try {
    $src = New-Object System.Drawing.Rectangle(64, 76, 280, 199)
    $formats = @(
        @{ Name='warehouse-icon-192-v2.png'; Size=192; Ratio=0.88 },
        @{ Name='warehouse-icon-512-v2.png'; Size=512; Ratio=0.88 },
        @{ Name='warehouse-apple-180-v2.png'; Size=180; Ratio=0.88 },
        @{ Name='warehouse-icon-maskable-512-v2.png'; Size=512; Ratio=0.73 }
    )
    foreach ($spec in $formats) {
        $n=[int]$spec.Size
        $bitmap = New-Object System.Drawing.Bitmap($n, $n)
        $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
        try {
            $graphics.Clear([System.Drawing.Color]::White)
            $graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::HighQuality
            $graphics.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
            $graphics.PixelOffsetMode = [System.Drawing.Drawing2D.PixelOffsetMode]::HighQuality
            $width = [int][Math]::Round($n * [double]$spec.Ratio)
            $height = [int][Math]::Round($width * $src.Height / $src.Width)
            $rect = New-Object System.Drawing.Rectangle([int][Math]::Floor(($n-$width)/2),[int][Math]::Floor(($n-$height)/2),$width,$height)
            $graphics.DrawImage($source,$rect,$src,[System.Drawing.GraphicsUnit]::Pixel)
            $target=Join-Path $outputDir $spec.Name
            $bitmap.Save($target,[System.Drawing.Imaging.ImageFormat]::Png)
            Write-Output ($spec.Name+' '+$n+'x'+$n+' logo='+$width+'x'+$height)
        } finally { $graphics.Dispose(); $bitmap.Dispose() }
    }
} finally { $source.Dispose() }
