import unittest

try:
    from PIL import Image, ImageDraw
except ImportError:  # Pillow ships with the bench; skip elsewhere.
    Image = None

if Image:
    from lotus_farm import signature_image as si


def phone_photo(width=600, height=300):
    """Tinted paper, darker on one side (shadow), with a blue signature stroke."""
    image = Image.new('RGB', (width, height))
    pixels = image.load()
    for x in range(width):
        shade = int(150 + 80 * x / width)  # 150 (shadow) .. 230 (lit)
        for y in range(height):
            pixels[x, y] = (shade + 12, shade + 6, shade - 10)  # warm light: not neutral grey
    draw = ImageDraw.Draw(image)
    draw.line([(80, 200), (200, 90), (320, 210), (460, 100)], fill=(30, 40, 120), width=9)
    return image


@unittest.skipUnless(Image, 'Pillow not installed')
class SignatureBackground(unittest.TestCase):
    def test_shadowed_tinted_paper_becomes_transparent_and_strokes_stay(self):
        result = si.remove_background(phone_photo())
        alpha = result.getchannel('A')
        self.assertLess(result.width, 600, 'trimmed to the strokes')
        corners = [alpha.getpixel((2, 2)), alpha.getpixel((result.width - 3, result.height - 3))]
        self.assertEqual(max(corners), 0, 'paper is transparent, including the shadowed side')
        histogram = alpha.histogram()
        strokes = sum(histogram[201:])
        self.assertGreater(strokes, 1500, 'the pen stroke stays opaque')
        transparent = histogram[0]
        self.assertGreater(transparent / (result.width * result.height), 0.7)

    def test_old_fixed_threshold_case_light_grey_paper(self):
        image = Image.new('RGB', (400, 200), (205, 205, 205))
        ImageDraw.Draw(image).line([(40, 150), (360, 50)], fill=(20, 20, 20), width=7)
        alpha = si.remove_background(image).getchannel('A')
        self.assertEqual(alpha.getpixel((1, 1)), 0, 'grey paper at 205 used to stay fully opaque')

    def test_already_transparent_drawing_is_only_trimmed(self):
        drawing = Image.new('RGBA', (500, 300), (0, 0, 0, 0))
        ImageDraw.Draw(drawing).line([(100, 150), (400, 150)], fill=(10, 10, 10, 255), width=6)
        result = si.remove_background(drawing)
        self.assertLess(result.height, 60)
        self.assertEqual(result.getchannel('A').getpixel((result.width // 2, result.height // 2)), 255)

    def test_blank_photo_is_rejected(self):
        with self.assertRaises(ValueError):
            si.remove_background(Image.new('RGB', (300, 200), (220, 218, 210)))

    def test_strength_moves_the_thresholds(self):
        self.assertEqual(si.thresholds(50), (90, 270))
        self.assertLess(si.thresholds(100)[0], si.thresholds(0)[0])


if __name__ == '__main__':
    unittest.main()
