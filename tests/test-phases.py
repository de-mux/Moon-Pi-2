import sys
from datetime import datetime
from pathlib import Path

import arrow

libdir = Path(__file__).parent.parent
if libdir.exists():
    sys.path.append(str(libdir))

import moon_pi

BASE_DIR = Path(__file__).parent
OUT_DIR = BASE_DIR / "output"


def test_phases(epd):
    start = arrow.get(datetime(2023, 11, 5), "US/Pacific")
    end = arrow.get(datetime(2023, 12, 19), "US/Pacific")
    for idx, dt in enumerate(arrow.Arrow.range("day", start.datetime, end.datetime)):
        now = dt

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
        img.save(str(OUT_DIR / f"phase-{idx}.png"))


if __name__ == "__main__":
    OUT_DIR.mkdir(exist_ok=True)
    epd = moon_pi.get_epd()

    test_phases(epd)
