import sys
from pathlib import Path

import arrow

libdir = Path(__file__).parent.parent
if libdir.exists():
    sys.path.append(str(libdir))

import moon_pi

BASE_DIR = Path(__file__).parent
OUT_DIR = BASE_DIR / "output"


def test_paletize(epd):
    bg_img = moon_pi.load_image(moon_pi.IMAGE_DIR / "screen-template-7in3.png")
    bg_img.save(str(OUT_DIR / "test-palette-before.png"))

    moon_img = moon_pi.load_image(moon_pi.IMAGE_DIR / "moon" / "8125-third-quarter.png")
    moon_img.save(str(OUT_DIR / "test-palette-moon-only.png"))

    bg_img.paste(moon_img, (10, 10), moon_img)
    bg_img.save(str(OUT_DIR / "test-palette-bg-and-moon.png"))


def test_antialiasing(now, epd):
    quote, credit, font_size = moon_pi.get_banner_text(now)
    moon_info = moon_pi.get_moon_phase(now)

    output_palette = moon_pi.epd_get_palette(epd)
    img = moon_pi.generate_image(
        now, quote, credit, font_size, moon_info, 19, output_palette
    )
    img.save(str(OUT_DIR / "test-img-prepalette.png"))
    img = moon_pi.paletize_image(img, output_palette)
    img.save(str(OUT_DIR / "test-img-antialiasing.png"))


if __name__ == "__main__":
    OUT_DIR.mkdir(exist_ok=True)
    now = arrow.Arrow(2023, 11, 5, 0)
    epd = moon_pi.get_epd()

    test_antialiasing(now, epd)
    test_paletize(epd)
