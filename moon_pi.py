#!/usr/bin/env python

# https://github.com/PiSugar/pisugar-server-py

import csv
import logging
import os
import random
from pathlib import Path
from subprocess import call

import arrow
import epaper
from PIL import Image, ImageDraw, ImageFont
from functools import lru_cache

# from waveshare_epd import epd5in65f

# Replace BIRTHDAY_MONTH w/ recipient's month of birth and BIRTHDAY_DAY w/ day of birth
BIRTHDAY_MONTH = 6
BIRTHDAY_DAY = 16

BASE_DIR = Path(__file__).parent.parent
QUOTATION_FILE = BASE_DIR / "quotations.csv"

FONT_DIR = BASE_DIR / "fonts"
FONTS = {
    "luminari": FONT_DIR / "Luminari.ttf",
    "futura": FONT_DIR / "Futura.ttc",
    "unicode": FONT_DIR / "AppleColorEmoji.ttc",
}

IMAGE_DIR = BASE_DIR / "images"

WAVESHARE_DISPLAY = "epd7in3f"
"""The display to use. To get a list of possibilities, use:

    >>> import epaper
    >>> epaper.modules()
"""


logger = logging.getLogger("moonpi")


@lru_cache
def get_epd():
    epd = epaper.epaper(WAVESHARE_DISPLAY).EPD()
    logger.info(f"Created display: {epd}")
    logger.info(f"Display {WAVESHARE_DISPLAY} width: {epd.width}, height: {epd.height}")
    logger.info(f"Initializing display")
    epd.init()
    logger.info(f"Initialized display")
    return epd


def epd_clear(epd):
    """Clear the display."""
    logger.info("Clearing display")
    epd.Clear()
    logger.info("Cleared")


def get_banner_text(now: arrow.Arrow):
    day = now.date().day
    month = now.date().month

    # Compare the month and day of the recipient's birthday with today's month and day
    # This will replace the random moon quotation with HAPPY BIRTHDAY on the recipient's birthday
    if BIRTHDAY_MONTH == month and BIRTHDAY_DAY == day:
        quotation_text = "HAPPY BIRTHDAY!"
        credit_text = ""
        font_size = 44
    # If it's not the birthday, then the script grabs a random quotation from the file.
    else:
        with QUOTATION_FILE.open() as fp:
            reader = csv.reader(fp)
            # Skip the header row
            next(reader)
            # Convert the remaining rows to a list
            rows = list(reader)
            # Choose a random row
            random_row = random.choice(rows)
            # set the variables to print the text later
            quotation_text, credit_text = random_row
            quote_length = len(quotation_text)
            if quote_length <= 54:
                font_size = 24
            elif quote_length < 60:
                font_size = 22
            elif quote_length <= 65:
                font_size = 20
            else:
                font_size = 18
    return (quotation_text, credit_text, font_size)


def get_battery_charge_percent():
    # get battery charge info from the PiJuice and set charge_pct to that value
    pj = pijuice.PiJuice(1, 0x14)  # create an instance of the PiJuice class
    battery_info = pj.status.GetChargeLevel()  # get the battery charge level
    charge_pct = format(battery_info["data"])
    return charge_pct


def generate_image():
    # defining variables for the text to be printed
    # I used Luminari, Futura, and AppleColorEmoji (for the low battery indicator)
    # You'll want to choose your own and you'll need to put them in proper directory
    quotation = ImageFont.truetype(FONTS["luminari"], font_size)
    credit = ImageFont.truetype(FONTS["futura"], 18)
    date_and_phase = ImageFont.truetype(FONTS["futura"], 26)
    battery_warning = "\U0001FAAB"
    unicode_font = ImageFont.truetype(FONTS["unicode"], 26)

    # Grabs today's date and formats it for display
    date_to_show = now.strftime("%A, %B %-d")

    # Note that you will need to create your own images and possibly change the image directory below
    logger.info("getting image file")
    h_image = Image.open(IMAGE_DIR / filename)
    draw = ImageDraw.Draw(h_image)
    draw.text((300, 5), quotation_text, font=quotation, fill=0, anchor="mt")
    draw.text((600, 40), credit_text, font=credit, fill=0, anchor="rm")
    draw.text((10, 410), date_to_show, font=date_and_phase, fill=epd.WHITE, anchor="lt")
    draw.text(
        (590, 410),
        caption_text,
        font=date_and_phase,
        fill=epd.WHITE,
        anchor="rt",
    )
    if int(charge_pct) > 20:
        print("Battery level is fine.")
    else:
        draw.rectangle((10, 55, 35, 90), fill="white")
        draw.text((10, 60), battery_warning, font=unicode_font, embedded_color=True)


def epd_sleep(epd):
    # It's super important to sleep the display when you're done updating, otherwise you could damage it
    logger.info("Putting display to sleep...")
    epd.sleep()  # sends sleep command and calls epdconfig.module_exit()
    logger.info("Display is asleep")


def epd_update_image(epd, image):
    epd_clear(epd)
    epd.display(epd.getbuffer(image))
    epd_sleep(epd)


def draw_test():
    h_image = generate_image()
    epd = get_epd()
    epd_update_image(epd, h_image)


# def draw_test2():
#    h_image = Image.open(IMAGE_DIR / "7in3f1.bmp")
#    epd = get_epd()
#    epd_clear(epd)
#    # epd_update_image(epd, h_image)
#    epd_sleep(epd)


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    charge_pct = get_battery_charge_percent()

    # get today's date and break it into day and month variables
    now = arrow.now()

    quotation_text, credit_text, font_size = get_banner_text(now)

    # open the .csv file containing the moonphase data and grabs the needed info
    with open("/home/pi/moon_data.csv") as csvfile:
        # read the file as a dictionary
        reader = csv.DictReader(csvfile)
        today = now.strftime("%Y-%m-%d")
        # iterate over the rows in the file
        for row in reader:
            # if the date in the current row matches today's date
            if row["datetime"] == today:
                # set the caption
                caption_text = row["caption"]
                # set the file
                filename = row["file"]

    h_image = generate_image(quotation_text, credit_text, font_size)
    epd = get_epd()
    epd_update_image(epd, h_image)

    # TODO: uncomment this before deploying
    # call("sudo shutdown -h now", shell=True)
