#!/usr/bin/env python

# https://github.com/PiSugar/pisugar-server-py
# reference: https://svs.gsfc.nasa.gov/5048/

import csv
import logging
import math
import random
import types
import typing as t
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from unittest.mock import MagicMock

import arrow
import ephem
import pisugar
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

        @property
        def epdconfig(self):
            return MagicMock()

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
    "quote": ("Luminari-Regular.ttf", 20),
    "credit": ("SourceSans3-Semibold.ttf", 18),
    "date_and_phase": ("SourceSans3-Semibold.ttf", 28),
}
"""Font mapping, where key is the font purpose, and value is a tuple of
(font_filename, default_size).
Font files are assumed to be in the "fonts" directory.
"""

WHITE = 0xFFFFFF

IMAGE_DIR = BASE_DIR / "images"
BACKGROUND_IMAGE = IMAGE_DIR / "screen-template-7in3.png"
BATTERY_INDICATOR_IMAGE = IMAGE_DIR / "battery.png"  # from OpenMoji

WAVESHARE_DISPLAY = "epd7in3f"
"""The display to use. To get a list of possibilities, use:

    >>> import epaper
    >>> epaper.modules()
"""

FONT_ANTIALIASING = False
"""Whether or not to enable antialiasing for fonts. Generally this should be
False for displays with limited color palettes.
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

BATTERY_LOW_THRESHOLD = 20
"""Battery low indicator will be drawn if charge becomes lower than this threshold."""

MOON_QUARTERS = ["New Moon", "First Quarter", "Full Moon", "Third Quarter"]
MOON_PHASES = ["Waxing Crescent", "Waxing Gibbous", "Waning Gibbous", "Waning Crescent"]


logger = logging.getLogger("moonpi")


# --------------- LUNAR PHASE ------------------


@dataclass
class MoonInfo:
    normalized_age: float
    """Normalized age of the moon for the current lunation.
    0 = new moon, ~1 = close to next new moon
    """
    phase_percent: float
    text: str


def _arrow_to_ephem(dt: arrow.Arrow) -> ephem.Date:
    """Convert Arrow date object to ephem.Date."""
    return ephem.Date(dt.datetime)


def _get_moon_cycle_range(date: ephem.Date) -> tuple[ephem.Date, ephem.Date]:
    cycle_start = ephem.previous_new_moon(date)
    cycle_end = ephem.next_new_moon(cycle_start)
    if round(cycle_end, 5) <= round(date, 5):
        cycle_start = ephem.next_new_moon(cycle_start)
        cycle_end = ephem.next_new_moon(cycle_start)
    return (cycle_start, cycle_end)


def _within_a_day(first: ephem.Date, second: ephem.Date):
    return abs(second - first) <= 0.5


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


def _get_normalized_age(date: ephem.Date):
    """Get normalized age of the moon for the current lunation.
    0 = new moon, ~1 = close to next new moon
    """
    cycle_start, cycle_end = _get_moon_cycle_range(date)
    days_since_new = date - cycle_start
    logger.debug(f"Moon is {days_since_new:.2f} day(s) since new")
    return (days_since_new / (cycle_end - cycle_start)) % 1.0


def get_moon_phase(dt: arrow.Arrow) -> MoonInfo:
    """Get the moon info for the 24-hour period, centered around the midpoint of the
    given day.
    """
    middle_of_day = dt.replace(hour=12)
    text = _get_moon_phase_text(_arrow_to_ephem(middle_of_day))

    earth = ephem.Observer()
    earth.lat = math.radians(LOCATION["latitude"])
    earth.long = math.radians(LOCATION["longitude"])
    earth.date = _arrow_to_ephem(middle_of_day)

    moon = ephem.Moon(earth)
    breakpoint()
    phase_percent = moon.phase

    normalized_age = _get_normalized_age(earth.date)

    return MoonInfo(normalized_age, phase_percent, text)


# --------------- IMAGES -----------------


def get_moon_img_path(normalized_age: float, moon_phase_text: str) -> Path:
    moon_dir = IMAGE_DIR / "moon"
    if moon_phase_text in MOON_QUARTERS:
        postfix = moon_phase_text.lower().replace(" ", "-")
        return next(moon_dir.glob(f"*-{postfix}.png"))

    moon_files = sorted(moon_dir.glob("*.png"))
    total_files = len(moon_files)

    idx = round(normalized_age * total_files) % total_files

    return moon_files[idx]


def load_image(img_path: Path) -> Image.Image:
    img = Image.open(img_path)
    if img.has_transparency_data:
        if not img.mode == "RGBA":
            img = img.convert("RGBA")
    elif img.mode != "RGB":
        img = img.convert("RGB")
    return img


# --------------- EPAPER DISPLAY ------------------


def patch_epd7in3f(epd):
    """Version 1.0 of the epaper lib on PyPI has a bug in epd7in3f displays
    where the display comes out dim.  This patches the class to fix the bug.

    See https://github.com/waveshareteam/e-Paper/commit/8be47b27f1a6808fd82ea9ceeac04c172e4ee9a8
    """
    epdconfig = epaper.epaper("epd7in3f").epdconfig

    def init(self):
        if epdconfig.module_init() != 0:
            return -1
        # EPD hardware init start
        self.reset()
        self.ReadBusyH()
        epdconfig.delay_ms(30)

        self.send_command(0xAA)  # CMDH
        self.send_data(0x49)
        self.send_data(0x55)
        self.send_data(0x20)
        self.send_data(0x08)
        self.send_data(0x09)
        self.send_data(0x18)

        self.send_command(0x01)
        self.send_data(0x3F)
        self.send_data(0x00)
        self.send_data(0x32)
        self.send_data(0x2A)
        self.send_data(0x0E)
        self.send_data(0x2A)

        self.send_command(0x00)
        self.send_data(0x5F)
        self.send_data(0x69)

        self.send_command(0x03)
        self.send_data(0x00)
        self.send_data(0x54)
        self.send_data(0x00)
        self.send_data(0x44)

        self.send_command(0x05)
        self.send_data(0x40)
        self.send_data(0x1F)
        self.send_data(0x1F)
        self.send_data(0x2C)

        self.send_command(0x06)
        self.send_data(0x6F)
        self.send_data(0x1F)
        self.send_data(0x1F)
        self.send_data(0x22)

        self.send_command(0x08)
        self.send_data(0x6F)
        self.send_data(0x1F)
        self.send_data(0x1F)
        self.send_data(0x22)

        self.send_command(0x13)  # IPC
        self.send_data(0x00)
        self.send_data(0x04)

        self.send_command(0x30)
        self.send_data(0x3C)

        self.send_command(0x41)  # TSE
        self.send_data(0x00)

        self.send_command(0x50)
        self.send_data(0x3F)

        self.send_command(0x60)
        self.send_data(0x02)
        self.send_data(0x00)

        self.send_command(0x61)
        self.send_data(0x03)
        self.send_data(0x20)
        self.send_data(0x01)
        self.send_data(0xE0)

        self.send_command(0x82)
        self.send_data(0x1E)

        self.send_command(0x84)
        self.send_data(0x00)

        self.send_command(0x86)  # AGID
        self.send_data(0x00)

        self.send_command(0xE3)
        self.send_data(0x2F)

        self.send_command(0xE0)  # CCSET
        self.send_data(0x00)

        self.send_command(0xE6)  # TSSET
        self.send_data(0x00)
        return 0

    epd.init = types.MethodType(init, epd)


@lru_cache
def get_epd():
    epd = epaper.epaper(WAVESHARE_DISPLAY).EPD()
    if WAVESHARE_DISPLAY == "epd7in3f":
        patch_epd7in3f(epd)
    logger.info(f"Created display: {epd}")
    logger.info(f"Display {WAVESHARE_DISPLAY} width: {epd.width}, height: {epd.height}")
    logger.info("Initializing display")
    epd.init()
    logger.info("Initialized display")
    return epd


def epd_clear(epd) -> None:
    """Clear the display."""
    logger.info("Clearing display...")
    epd.Clear()
    logger.info("Cleared")


def epd_sleep(epd) -> None:
    # It's super important to sleep the display when you're done updating, otherwise you could damage it
    logger.info("Putting display to sleep...")
    epd.sleep()  # sends sleep command and calls epdconfig.module_exit()
    logger.info("Display is asleep")


def epd_update_image(epd, image: Image.Image) -> None:
    """Display the image on the e-Paper display, including
    clearing the screen beforehand and putting the display to sleep afterwards.

    Note that if you don't pre-convert the image to the display's color palette,
    it will be done automatically. For more control over the conversion, you may
    want to do the conversion yourself using Pillow prior to calling this function.
    See `paletize_image()`.
    """
    palette = epd_get_palette(epd)
    image = paletize_image(image, palette, dither=False)

    epd_clear(epd)
    epd_buf = epd.getbuffer(image)
    logger.info("Displaying image...")
    epd.display(epd_buf)
    logger.info("Display updated")
    epd_sleep(epd)


def epd_get_palette(epd) -> list[int]:
    """Get the RGB color palette for the e-Paper display based on its capabilities.
    The resulting palette will be padded to 256 colors, for a total length of
    3 * 256.
    """
    colors = ("BLACK", "WHITE", "GREEN", "BLUE", "RED", "YELLOW", "ORANGE")
    bgr_palette = [
        _packed_bgr_to_rgb(getattr(epd, color))
        for color in colors
        if hasattr(epd, color)
    ]
    default_color = bgr_palette[0]
    values_per_swatch = len(default_color)
    palette_256 = list(default_color) * 256
    for swatch_num, color in enumerate(bgr_palette):
        idx = values_per_swatch * swatch_num
        palette_256[idx : idx + values_per_swatch] = color
    return palette_256


def _packed_bgr_to_rgb(val: int) -> tuple[int, ...]:
    """Convert packed BGR color value to 3-tuple,
    e.g. 0x0080FF -> (0xff, 0x80, 0x00)
    """
    return tuple(val.to_bytes(3, "little"))


def paletize_image(
    img: Image.Image, palette: t.Iterable[int], dither=False
) -> Image.Image:
    """Convert an image's color palette to the colors supported by the given
    e-Paper display.
    """

    # Create a palette with the colors supported by the panel
    pal_image = Image.new("P", (1, 1))
    pal_image.putpalette(palette)

    # Convert the soruce image to the display colors with no dither
    image_paletized = img.convert("RGB").quantize(
        palette=pal_image,
        dither=Image.Dither.FLOYDSTEINBERG if dither else Image.Dither.NONE,
    )
    return image_paletized


def get_font(name: str, size=None) -> ImageFont.FreeTypeFont:
    font_file, default_size = FONTS[name]
    font_path = FONT_DIR / font_file

    if not font_path.exists():
        msg = f"could not find the font {font_path}. Make sure you have it downloaded into the right directory"
        raise FileNotFoundError(msg)

    return ImageFont.truetype(str(FONT_DIR / font_file), size if size else default_size)


@dataclass
class ImageSettings:
    now: arrow.Arrow
    quotation_text: str
    credit_text: str
    font_size: int
    moon: MoonInfo
    battery_charge_percent: t.Optional[float]
    output_palette: t.Iterable[int]


class ImageBuilder:
    def __init__(self, settings: ImageSettings):
        self.settings = settings

        # Note that you will need to create your own images and possibly change the image directory below
        logger.info("Opening background image file")
        self.bg_image = load_image(BACKGROUND_IMAGE)

    def build(self):
        image = self.generate_base_image()

        self.add_image_text(image)

        # Draw battery low indicator (if applicable)
        battery_charge_percent = self.settings.battery_charge_percent
        if battery_charge_percent is not None:
            if int(battery_charge_percent) > BATTERY_LOW_THRESHOLD:
                logger.info(f"Battery level is {battery_charge_percent}%.")
            else:
                logger.warning(f"Battery low ({battery_charge_percent}%).")
                self.add_image_battery_indicator(image)

        image = paletize_image(
            image,
            self.settings.output_palette,
            dither=False,  # don't dither fonts or battery indicator
        )
        return image

    @property
    def x_center(self):
        return int((self.right + self.left) / 2)

    @property
    def y_center(self):
        return int((self.bottom + self.top) / 2)

    @property
    def x_margin(self):
        return DISPLAY_MARGINS[0]

    @property
    def y_margin(self):
        return DISPLAY_MARGINS[1]

    @property
    def left(self):
        return self.x_margin

    @property
    def right(self):
        return self.bg_image.width - self.x_margin

    @property
    def top(self):
        return self.y_margin

    @property
    def bottom(self):
        return self.bg_image.height - self.y_margin

    def generate_base_image(self):
        """Generate image containing background and moon (no text)

        The result will be reduced to the given output palette and dithered, but it
        will be in "RGB" mode(i.e., not "P" mode) for further processing.
        """
        # Draw moon
        normalized_age = self.settings.moon.normalized_age
        text = self.settings.moon.text
        moon_img_size = (MOON_SIZE_PX, MOON_SIZE_PX)
        moon_img = load_image(get_moon_img_path(normalized_age, text))
        moon_img = moon_img.resize(moon_img_size)
        moon_coords = (
            self.x_center - int(moon_img.width / 2),
            self.y_center - int(moon_img.height / 2) + 20,
        )

        image = self.bg_image.copy()
        image.paste(moon_img, moon_coords, moon_img)

        image = paletize_image(image, self.settings.output_palette, dither=True)
        return image.convert("RGB")

    def add_image_text(self, image: Image.Image):
        quotation_font = get_font("quote", self.settings.font_size)
        credit_font = get_font("credit")
        date_and_phase_font = get_font("date_and_phase")

        # Grabs today's date and formats it for display
        date_to_show = self.settings.now.strftime("%A, %B %-d")

        draw = ImageDraw.Draw(image)
        draw.fontmode = "L" if FONT_ANTIALIASING else "1"
        # Draw quote and credit
        draw.text(
            (self.x_center, self.top + 5),
            self.settings.quotation_text,
            font=quotation_font,
            fill=0,
            anchor="mt",
        )
        if self.settings.credit_text:
            draw.text(
                (self.right - 5, self.top + 40),
                f"\N{HORIZONTAL BAR} {self.settings.credit_text}",
                font=credit_font,
                fill=0,
                anchor="rm",
            )

        # Draw date
        draw.text(
            (self.left + 10, self.bottom - 38),
            date_to_show,
            font=date_and_phase_font,
            fill=WHITE,
            anchor="lt",
        )
        # Draw moon phase
        draw.text(
            (self.right - 10, self.bottom - 38),
            self.settings.moon.text,
            font=date_and_phase_font,
            fill=WHITE,
            anchor="rt",
        )

    def add_image_battery_indicator(self, image: Image.Image):
        battery_img = load_image(BATTERY_INDICATOR_IMAGE)
        coords = (self.left + 10, self.top + 64)
        image.paste(battery_img, coords, battery_img)


def generate_image(
    now: arrow.Arrow,
    quotation_text: str,
    credit_text: str,
    font_size: int,
    moon_info: MoonInfo,
    battery_charge_percent: t.Optional[float],
    output_palette: t.Iterable[int],
) -> Image.Image:
    settings = ImageSettings(
        now,
        quotation_text,
        credit_text,
        font_size,
        moon_info,
        battery_charge_percent,
        output_palette,
    )
    builder = ImageBuilder(settings)
    image = builder.build()
    return image


def load_quotations() -> list[list[str]]:
    """Load a list of quotations from quotations.csv.

    Example:

        >>> load_quotations()
        [
            ["You are my sun, my moon, and all my stars.", "E.E. Cummings"],
            ["The moon is my mother.", "Sylvia Plath"],
            ...
        ]
    """
    with QUOTATION_FILE.open() as fp:
        reader = csv.reader(fp, skipinitialspace=True)
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
    logger.info(f"Quote: {quotation_text} -- {credit_text}")
    logger.info(f"Font size: {font_size}")
    return (quotation_text, credit_text, font_size)


def get_font_size_for_quote(quotation_text) -> int:
    """Return an appropriate font size for the given quote, based on quote
    length.
    """
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


def get_pisugar_server() -> t.Union[pisugar.PiSugarServer, None]:
    try:
        conn, event_conn = pisugar.connect_tcp()
    except OSError:
        logger.exception("Unable to connect to PiSugar server.")
        return None

    if event_conn is None:
        logger.error("Unable to connect to PiSugar server. event_conn is None")
        return None

    return pisugar.PiSugarServer(conn, event_conn)  # pyright: ignore


def sync_rtc_to_system_clock():
    ps = get_pisugar_server()
    if not ps:
        logger.warning("PiSugar server not found. Could not sync RTC to system clock.")
        return
    logger.debug(f"System time previous to RTC sync: {arrow.now()}")
    logger.info("Syncing system clock to PiSugar RTC")
    ps.rtc_rtc2pi()
    logger.info("Syncing system clock to PiSugar RTC... done")
    logger.debug(f"System time after RTC sync: {arrow.now()}")


def get_battery_charge_percent() -> t.Union[float, None]:
    ps = get_pisugar_server()
    if not ps:
        logger.warning("PiSugar server not found. Skipping battery check.")
        return None
    charge_pct = ps.get_battery_level()
    charging = ps.get_battery_charging()

    logger.info("Battery info:")
    logger.info(f"    charge_level={charge_pct}%")
    logger.info(f"    charging={charging}")
    if charging:
        logger.info(f"      (time until full {ps.get_battery_full_charge_duration()})")
    logger.info(f"    current={1000 * ps.get_battery_current():.3f} mA")
    logger.info(f"    voltage={ps.get_battery_voltage():.3f} V")
    return charge_pct


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    sync_rtc_to_system_clock()
    charge_pct = get_battery_charge_percent()

    now = arrow.now()
    moon_info = get_moon_phase(now)
    logger.info(f"Date: {now}")
    logger.info(f"{moon_info}")

    quotation_text, credit_text, font_size = get_banner_text(now)

    epd = get_epd()
    output_palette = epd_get_palette(epd)
    image = generate_image(
        now,
        quotation_text,
        credit_text,
        font_size,
        moon_info,
        charge_pct,
        output_palette,
    )
    epd_update_image(epd, image)
