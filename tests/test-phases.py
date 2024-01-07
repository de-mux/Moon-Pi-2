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


def test_phases(palette):
    start = arrow.get(datetime(2023, 11, 5), "US/Pacific")
    end = arrow.get(datetime(2023, 12, 19), "US/Pacific")
    for idx, dt in enumerate(arrow.Arrow.range("day", start.datetime, end.datetime)):
        now = dt

        moon_info = moon_pi.get_moon_info(now)

        quote, credit, font_size = moon_pi.get_banner_text(now)

        print(now.strftime("%Y-%m-%d %H"), moon_info.text, moon_info.normalized_age)
        img = moon_pi.generate_image(
            now,
            quote,
            credit,
            font_size,
            moon_info,
            100,
            palette,
        )
        img.save(str(OUT_DIR / f"phase-{idx}.png"))


def test_supermoon(palette):
    now = arrow.get(2024, 9, 17, 12, tzinfo="US/Pacific")

    moon_info = moon_pi.get_moon_info(now)

    quote, credit, font_size = moon_pi.get_banner_text(now)

    print(now.strftime("%Y-%m-%d %H"), moon_info.text, moon_info.normalized_age)
    img = moon_pi.generate_image(
        now,
        quote,
        credit,
        font_size,
        moon_info,
        100,
        palette,
    )
    img.save(str(OUT_DIR / "test-supermoon.png"))


def test_blue_moon(palette):
    now = arrow.get(2026, 5, 31, 12, tzinfo="US/Pacific")

    moon_info = moon_pi.get_moon_info(now)

    quote, credit, font_size = moon_pi.get_banner_text(now)

    print(now.strftime("%Y-%m-%d %H"), moon_info.text, moon_info.normalized_age)
    img = moon_pi.generate_image(
        now,
        quote,
        credit,
        font_size,
        moon_info,
        100,
        palette,
    )
    img.save(str(OUT_DIR / "test-blue-moon.png"))


def test_next_supermoon():
    start = arrow.get(datetime(2023, 11, 5, 12), "US/Pacific")
    end = arrow.get(datetime(2024, 9, 18, 12), "US/Pacific")
    for dt in arrow.Arrow.range("day", start.datetime, end.datetime):
        now = dt

        moon_info = moon_pi.get_moon_info(now)
        if moon_info.text == "Supermoon":
            assert now == arrow.get(datetime(2024, 9, 17, 12), "US/Pacific")
            print(now)
            return
    msg = "supermoon not found"
    raise AssertionError(msg)


def test_next_blue_moon():
    start = arrow.get(datetime(2023, 11, 5, 12), "US/Pacific")
    end = arrow.get(datetime(2026, 6, 1, 12), "US/Pacific")
    for dt in arrow.Arrow.range("day", start.datetime, end.datetime):
        now = dt

        moon_info = moon_pi.get_moon_info(now)
        if moon_info.text == "Blue Moon":
            assert now == arrow.get(datetime(2026, 5, 31, 12), "US/Pacific")
            print(now)
            return
    msg = "blue moon not found"
    raise AssertionError(msg)


if __name__ == "__main__":
    OUT_DIR.mkdir(exist_ok=True)
    epd = moon_pi.get_epd()

    output_palette = moon_pi.epd_get_palette(epd)

    test_next_supermoon()
    test_next_blue_moon()
    test_blue_moon(output_palette)
    test_supermoon(output_palette)
    test_phases(output_palette)
