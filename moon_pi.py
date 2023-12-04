#!/usr/bin/env python

# https://github.com/PiSugar/pisugar-server-py

import csv
import logging
import os
import random
from pathlib import Path
from subprocess import call

import arrow
import pijuice
from PIL import Image, ImageDraw, ImageFont

# from waveshare_epd import epd5in65f

# Replace BIRTHDAY_MONTH w/ recipient's month of birth and BIRTHDAY_DAY w/ day of birth
BIRTHDAY_MONTH = 6
BIRTHDAY_DAY = 16

BASE_DIR = Path(__file__).parent
QUOTATION_FILE = BASE_DIR / "quotations.csv"

# picdir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'pic')
# libdir = os.path.join(
#    os.path.dirname(os.path.dirname(os.path.realpath(__file__))), "lib"
# )
# if os.path.exists(libdir):
#    sys.path.append(libdir)


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
    # Replace "/home/pi/quotations.csv" with your own file
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


if __name__ == "__main__":
    charge_pct = get_battery_charge_percent()

    # get today's date and break it into day and month variables
    now = arrow.now()
    # today = datetime.today().strftime("%Y-%m-%d")

    quotation_text, credit_text, font_size = get_banner_text(now)

    logging.basicConfig(level=logging.DEBUG)

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

    # defining variables for the text to be printed
    # I used Luminari, Futura, and AppleColorEmoji (for the low battery indicator)
    # You'll want to choose your own and you'll need to put them in proper directory
    quotation = ImageFont.truetype(os.path.join("/home/pi/Luminari.ttf"), font_size)
    credit = ImageFont.truetype(os.path.join("/home/pi/Futura.ttc"), 18)
    date_and_phase = ImageFont.truetype(os.path.join("/home/pi/Futura.ttc"), 26)
    battery_warning = "\U0001FAAB"
    unicode_font = ImageFont.truetype("/home/pi/AppleColorEmoji.ttc", 26)

    epd = epd5in65f.EPD()

    epd.init()

    epd.Clear()

    # Grabs today's date and formats it for display
    date_to_show = now.strftime("%A, %B %-d")

    # Note that you will need to create your own images and possibly change the image directory below
    logging.info("getting image file")
    Himage = Image.open("/home/pi/images/%s" % (filename))
    draw = ImageDraw.Draw(Himage)
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
    epd.display(epd.getbuffer(Himage))

    # It's super important to sleep the display when you're done updating, otherwise you could damage it

    epd.sleep()

    call("sudo shutdown -h now", shell=True)
