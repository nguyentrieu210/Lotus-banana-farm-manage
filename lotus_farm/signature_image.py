"""Paper background removal for signature / initials photos (Pillow only, unit-tested in tests/).

A phone photo of a signature has grey, tinted and unevenly lit paper, so a fixed "near white"
threshold leaves the background behind. The paper level is estimated locally instead: a max filter
removes the pen strokes, a min filter follows broad shadows, a blur smooths them, and each pixel's opacity follows how much darker it
is than the paper around it. The same constants are used by frontend/src/signature-background.js
so the preview matches the stored image.
"""
from PIL import Image, ImageChops, ImageFilter, ImageMath

DEFAULT_STRENGTH = 50
TRANSPARENT_SHARE = 0.25  # drawn signatures are mostly transparent; the old editor left only a few percent
PAD = 0.04


def thresholds(strength=DEFAULT_STRENGTH):
    """Darkness relative to the local paper, in per mille: below `low` transparent, above `high` opaque."""
    strength = max(0, min(100, int(strength)))
    low = 140 - strength
    return low, low + 180


def paper_level(gray):
    """Local paper brightness for every pixel (mode L, same size as `gray`)."""
    width, height = gray.size
    step = max(1, min(width, height) // 200)
    small = gray.resize((max(1, width // step), max(1, height // step)), Image.BILINEAR)
    size = max(3, min(31, (min(small.size) // 10) | 1))
    # Closing (max then min): the max removes thin pen strokes, the min brings broad shadows and dark
    # photo edges back to their own level, so they are paper rather than ink.
    level = small.filter(ImageFilter.MaxFilter(size)).filter(ImageFilter.MinFilter(size)).filter(ImageFilter.GaussianBlur(size / 3))
    return level.resize((width, height), Image.BILINEAR)


def trim(image):
    alpha = image.getchannel('A')
    box = alpha.point(lambda value: 255 if value > 40 else 0).getbbox()
    if not box:
        raise ValueError('Không thấy nét chữ ký trong ảnh. Chụp gần hơn, đủ sáng và rõ nét.')
    pad = max(2, int(max(box[2] - box[0], box[3] - box[1]) * PAD))
    return image.crop((max(0, box[0] - pad), max(0, box[1] - pad),
                       min(image.width, box[2] + pad), min(image.height, box[3] + pad)))


def already_transparent(image):
    alpha = image.getchannel('A')
    return sum(alpha.histogram()[:250]) > TRANSPARENT_SHARE * image.width * image.height


def remove_background(image, strength=DEFAULT_STRENGTH):
    """RGBA signature with transparent paper, trimmed to the strokes."""
    image = image.convert('RGBA')
    if already_transparent(image):
        return trim(image)
    gray = image.convert('L')
    level = paper_level(gray)
    low, high = thresholds(strength)
    darkness = ImageMath.lambda_eval(lambda a: (a['level'] - a['gray']) * 1000 / (a['level'] + 1), level=level, gray=gray)
    alpha = darkness.point(lambda value: (value - low) * 255 / (high - low)).convert('L')
    image.putalpha(ImageChops.darker(alpha, image.getchannel('A')))
    return trim(image)
