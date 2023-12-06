#!/usr/bin/env python

# https://github.com/PiSugar/pisugar-server-py
# reference: https://svs.gsfc.nasa.gov/5048/

import csv
import logging
import math
import random
from functools import lru_cache
from pathlib import Path
from unittest.mock import MagicMock

import arrow
import ephem
from PIL import Image, ImageDraw, ImageFont

try:
    import epaper
except ImportError:

    class MockEpaperDisplay:
        width = 800
        height = 480

        BLACK = 0x000000  #   0000  BGR
        WHITE = 0xFFFFFF  #   0001
        GREEN = 0x00FF00  #   0010
        BLUE = 0xFF0000  #   0011
        RED = 0x0000FF  #   0100
        YELLOW = 0x00FFFF  #   0101
        ORANGE = 0x0080FF  #   0110

        def __init__(self, display_id: str):
            self.name = display_id

        def __getattr__(self, _):
            return MagicMock()

        def getbuffer(self, img: Image.Image):
            return img

        def display(self, img: Image.Image):
            img_fpath = Path(__file__).parent / "test-img.png"
            img.save(img_fpath)

    class MockEPaper:
        def __init__(self, display_id):
            self.name = display_id

        def EPD(self):
            return MockEpaperDisplay(self.name)

    class epaper:
        """Mock epaper class, for debugging on a non-RPi environment"""

        @classmethod
        def epaper(cls, display_id):
            return MockEPaper(display_id)


# Replace BIRTHDAY_MONTH w/ recipient's month of birth and BIRTHDAY_DAY w/ day of birth
BIRTHDAY_MONTH = 6
BIRTHDAY_DAY = 16

BASE_DIR = Path(__file__).parent
QUOTATION_FILE = BASE_DIR / "quotations.csv"

FONT_DIR = BASE_DIR / "fonts"
FONTS = {
    "quote": ("Luminari.ttf", 20),
    "credit": ("SourceSans3-Semibold.ttf", 20),
    "date_and_phase": ("SourceSans3-Semibold.ttf", 28),
}
"""Font mapping, where key is the font purpose, and value is a tuple of
(font_filename, default_size).
Font files are assumed to be in the "fonts" directory.
"""

IMAGE_DIR = BASE_DIR / "images"
BACKGROUND_IMAGE = IMAGE_DIR / "screen-template-7in3.png"
BATTERY_INDICATOR_IMAGE = IMAGE_DIR / "battery.png"  # from OpenMoji

WAVESHARE_DISPLAY = "epd7in3f"
"""The display to use. To get a list of possibilities, use:

    >>> import epaper
    >>> epaper.modules()
"""

DISPLAY_MARGINS = (51, 18)
"""Margins for the display, in the form x, y, where x is the left and right
margins, and y is the top and bottom margins.
This is for cases where the outer edges of the display will not be seen, such
as when covered by a picture matte.
"""

MOON_SIZE_PX = 400
"""Size of the moon image, in pixels."""


LOCATION = {"city": "san francisco", "latitude": 37.773972, "longitude": -122.431297}
"""The location information, with latitude and longitude. Customize this to your
own location.
"""

MOON_QUARTERS = ["New Moon", "First Quarter", "Full Moon", "Third Quarter"]
MOON_PHASES = ["Waxing Crescent", "Waxing Gibbous", "Waning Gibbous", "Waning Crescent"]


logger = logging.getLogger("moonpi")


# --------------- LUNAR PHASE ------------------


def _get_moon_cycle_range(date: ephem.Date) -> tuple[ephem.Date, ephem.Date]:
    cycle_start = ephem.previous_new_moon(date)
    cycle_end = ephem.next_new_moon(cycle_start)
    if round(cycle_end, 5) <= round(date, 5):
        cycle_start = ephem.next_new_moon(cycle_start)
        cycle_end = ephem.next_new_moon(cycle_start)
    return (cycle_start, cycle_end)


def _within_a_day(first: ephem.Date, second: ephem.Date):
    return abs(int(second) - int(first)) < 1


def _get_moon_phase_text(date: ephem.Date):
    cycle_start, cycle_end = _get_moon_cycle_range(date)

    quarter_dates = [
        cycle_start,
        ephem.next_first_quarter_moon(cycle_start),
        ephem.next_full_moon(cycle_start),
        ephem.next_last_quarter_moon(cycle_start),
        cycle_end,
    ]

    for idx, quarter_date in enumerate(quarter_dates):
        if _within_a_day(date, quarter_date):
            return MOON_QUARTERS[idx % 4]

    for idx, quarter_date in enumerate(quarter_dates[1:]):
        if date < quarter_date:
            return MOON_PHASES[idx]

    return MOON_PHASES[-1]


def _get_lunation(date: ephem.Date):
    """Normalization of time between the date and the last new moon.
    0 = new moon, ~1 = close to next new moon
    """
    cycle_start, cycle_end = _get_moon_cycle_range(date)
    days_since_new = date - cycle_start
    return (days_since_new / (cycle_end - cycle_start)) % 1.0


def get_moon_phase(dt: arrow.Arrow) -> tuple[float, float, str]:
    earth = ephem.Observer()
    earth.lat = math.radians(LOCATION["latitude"])
    earth.long = math.radians(LOCATION["longitude"])
    earth.date = ephem.Date(dt.datetime)

    moon = ephem.Moon(earth)
    phase_percent = moon.phase

    text = _get_moon_phase_text(earth.date)
    lunation = _get_lunation(earth.date)

    return lunation, phase_percent, text


# --------------- IMAGES -----------------


def get_moon_img_path(lunation: float, moon_phase_text: str) -> Path:
    moon_dir = IMAGE_DIR / "moon"
    if moon_phase_text in MOON_QUARTERS:
        postfix = moon_phase_text.lower().replace(" ", "-")
        return next(moon_dir.glob(f"*-{postfix}.png"))

    moon_files = sorted(moon_dir.glob("*.png"))
    total_files = len(moon_files)

    idx = round(lunation * total_files) % total_files

    return moon_files[idx]


# --------------- EPAPER DISPLAY ------------------


@lru_cache
def get_epd():
    epd = epaper.epaper(WAVESHARE_DISPLAY).EPD()
    logger.info(f"Created display: {epd}")
    logger.info(f"Display {WAVESHARE_DISPLAY} width: {epd.width}, height: {epd.height}")
    logger.info("Initializing display")
    epd.init()
    logger.info("Initialized display")
    return epd


def epd_clear(epd):
    """Clear the display."""
    logger.info("Clearing display")
    epd.Clear()
    logger.info("Cleared")


def epd_sleep(epd):
    # It's super important to sleep the display when you're done updating, otherwise you could damage it
    logger.info("Putting display to sleep...")
    epd.sleep()  # sends sleep command and calls epdconfig.module_exit()
    logger.info("Display is asleep")


def epd_update_image(epd, image):
    epd_clear(epd)
    epd.display(epd.getbuffer(image))
    epd_sleep(epd)


def get_font(name: str, size=None) -> ImageFont.FreeTypeFont:
    font_file, default_size = FONTS[name]
    return ImageFont.truetype(str(FONT_DIR / font_file), size if size else default_size)


def generate_image(
    now: arrow.Arrow,
    quotation_text: str,
    credit_text: str,
    font_size: int,
    background_img: Path,
    moon_phase_text: str,
    moon_phase_lunation: float,
    battery_charge_percent: float,
    epd,
):
    quotation_font = get_font("quote", font_size)
    credit_font = get_font("credit")
    date_and_phase_font = get_font("date_and_phase")

    # Grabs today's date and formats it for display
    date_to_show = now.strftime("%A, %B %-d")

    # Note that you will need to create your own images and possibly change the image directory below
    logger.info("Opening background image file")
    h_image = Image.open(background_img)
    draw = ImageDraw.Draw(h_image)

    # set margins
    x_margin, y_margin = DISPLAY_MARGINS
    x_center = int(h_image.width / 2)
    y_center = int(h_image.height / 2)
    left = x_margin
    right = h_image.width - x_margin
    top = y_margin
    bottom = h_image.height - y_margin

    moon_img_size = (MOON_SIZE_PX, MOON_SIZE_PX)
    moon_img = Image.open(get_moon_img_path(moon_phase_lunation, moon_phase_text))
    moon_img = moon_img.resize(moon_img_size)
    moon_coords = (
        x_center - int(moon_img.width / 2),
        y_center - int(moon_img.height / 2) + 20,
    )

    h_image.paste(moon_img, moon_coords, moon_img)

    draw.text(
        (x_center, top + 5), quotation_text, font=quotation_font, fill=0, anchor="mt"
    )
    if credit_text:
        draw.text(
            (right - 5, top + 40),
            f"\N{HORIZONTAL BAR} {credit_text}",
            font=credit_font,
            fill=0,
            anchor="rm",
        )
    draw.text(
        (left + 10, bottom - 38),
        date_to_show,
        font=date_and_phase_font,
        fill=epd.WHITE,
        anchor="lt",
    )
    draw.text(
        (right - 10, bottom - 38),
        moon_phase_text,
        font=date_and_phase_font,
        fill=epd.WHITE,
        anchor="rt",
    )

    if int(battery_charge_percent) > 20:
        logger.info(f"Battery level is {battery_charge_percent}%.")
    else:
        logger.warning(f"Battery low ({battery_charge_percent}%).")
        battery_img = Image.open(BATTERY_INDICATOR_IMAGE)
        x = left + 10
        y = top + 64
        h_image.paste(battery_img, (x, y), battery_img)
    return h_image


def load_quotations():
    with QUOTATION_FILE.open() as fp:
        reader = csv.reader(fp)
        # Skip the header row
        next(reader)
        # Convert the remaining rows to a list
        rows = list(reader)
    return rows


def get_banner_text(now: arrow.Arrow):
    day = now.date().day
    month = now.date().month

    # Compare the month and day of the recipient's birthday with today's month and day
    # This will replace the random moon quotation with HAPPY BIRTHDAY on the recipient's birthday
    if BIRTHDAY_MONTH == month and BIRTHDAY_DAY == day:
        quotation_text = "Happy Birthday!"
        credit_text = ""
        font_size = 42
    # If it's not the birthday, then the script grabs a random quotation from the file.
    else:
        rows = load_quotations()
        # Choose a random row
        random_row = random.choice(rows)
        # set the variables to print the text later
        quotation_text, credit_text = random_row
        font_size = get_font_size_for_quote(quotation_text)
    return (quotation_text, credit_text, font_size)


def get_font_size_for_quote(quotation_text) -> int:
    quote_length = len(quotation_text)
    if quote_length <= 54:
        return 24
    elif quote_length < 60:
        return 22
    elif quote_length <= 65:
        return 20
    elif quote_length <= 80:
        return 18
    return 16


def get_battery_charge_percent():
    # get battery charge info from the PiJuice and set charge_pct to that value
    pj = pijuice.PiJuice(1, 0x14)  # create an instance of the PiJuice class
    battery_info = pj.status.GetChargeLevel()  # get the battery charge level
    charge_pct = format(battery_info["data"])
    return charge_pct


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    # charge_pct = get_battery_charge_percent()
    charge_pct = 100  # FIXME: debug only

    now = arrow.now()
    moon_phase_lunation, moon_phase_percent, moon_phase_text = get_moon_phase(now)

    epd = get_epd()

    quotation_text, credit_text, font_size = get_banner_text(now)
    h_image = generate_image(
        now,
        quotation_text,
        credit_text,
        font_size,
        BACKGROUND_IMAGE,
        moon_phase_text,
        moon_phase_lunation,
        charge_pct,
        epd,
    )

    epd_update_image(epd, h_image)

    # TODO: uncomment this before deploying
    # call("sudo shutdown -h now", shell=True)
