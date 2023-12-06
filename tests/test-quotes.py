import sys
from pathlib import Path

import arrow

libdir = Path(__file__).parent.parent
if libdir.exists():
    sys.path.append(str(libdir))

import moon_pi

BASE_DIR = Path(__file__).parent
OUT_DIR = BASE_DIR / "output"


def test_quotes(now, epd):
    rows = moon_pi.load_quotations()

    lunation, phase_percent, moon_phase_text = moon_pi.get_moon_phase(now)

    for idx, row in enumerate(rows):
        quote, credit = row
        font_size = moon_pi.get_font_size_for_quote(quote)

        img = moon_pi.generate_image(
            now,
            quote,
            credit,
            font_size,
            moon_pi.BACKGROUND_IMAGE,
            moon_phase_text,
            lunation,
            100,
            epd,
        )
        img.save(str(OUT_DIR / f"test-img-{idx}.png"))


def test_bday(epd):
    now = arrow.Arrow(2020, 6, 16)

    lunation, phase_percent, moon_phase_text = moon_pi.get_moon_phase(now)

    quote, credit, font_size = moon_pi.get_banner_text(now)
    img = moon_pi.generate_image(
        now,
        quote,
        credit,
        font_size,
        moon_pi.BACKGROUND_IMAGE,
        moon_phase_text,
        lunation,
        100,
        epd,
    )
    img.save(str(OUT_DIR / "test-img-bday.png"))


def test_low_battery(now, epd):
    quote, credit, font_size = moon_pi.get_banner_text(now)
    lunation, phase_percent, moon_phase_text = moon_pi.get_moon_phase(now)

    img = moon_pi.generate_image(
        now,
        quote,
        credit,
        font_size,
        moon_pi.BACKGROUND_IMAGE,
        moon_phase_text,
        lunation,
        19,
        epd,
    )
    img.save(str(OUT_DIR / "test-img-low-battery.png"))


if __name__ == "__main__":
    OUT_DIR.mkdir(exist_ok=True)
    now = arrow.now()
    epd = moon_pi.get_epd()

    test_quotes(now, epd)

    test_bday(epd)
    test_low_battery(now, epd)
