# Moon-Pi

An ePaper moon calendar powered by Raspberry Pi

![IMG_9535](https://github.com/barryl93/Moon-Pi/assets/39839859/7b96522b-2f72-4b4d-bb55-57c7d8657edb)

<!-- vim-markdown-toc GFM -->

- [Instructions](#instructions)
  - [Setup Raspberry Pi](#setup-raspberry-pi)
    - [Grab fonts](#grab-fonts)
    - [Setup Software](#setup-software)
    - [About The Moon Images](#about-the-moon-images)
    - [Gather Quotations](#gather-quotations)
    - [Moon Phase Calculation](#moon-phase-calculation)
  - [Wire it Up](#wire-it-up)
    - [PiSugar power supply](#pisugar-power-supply)
    - [e-Paper display](#e-paper-display)
  - [Put Together The Frame](#put-together-the-frame)
  - [The End](#the-end)
- [Todo](#todo)

<!-- vim-markdown-toc -->

OK, so you want to build a moon-a-day calendar! Let's get started. You'll need
the following:

- [Raspberry Pi Zero 2 W](https://www.amazon.com/gp/product/B09LH5SBPS) (or
  Raspberry Pi Zero W)
- SD card (4GB or more)
- [Waveshare 7.3in 7-Color e-Paper Display HAT](https://www.waveshare.com/product/7.3inch-e-paper-hat-f.htm),
  800 x 480 pixels (can also be found on Amazon)
- [Pisugar 2](https://www.amazon.com/gp/product/B08D678XPR) battery power supply
  with RTC
- [5x7 Black Shadow Box](https://www.amazon.com/gp/product/B081J74KN7)
- [5x7 Pre-Cut Mat Boards](https://www.amazon.com/gp/product/B08JTC2FYK) with
  4x6 inner
- [Picture Frame Turn Fasteners](https://www.amazon.com/dp/B07WVWCYJ5)
- micro-USB to USB-A cable
- (optional)
  [Raspberry Pi heatsinks](https://www.amazon.com/gp/product/B07ZLZRDXZ)
- a screwdriver, wires, screws, a drill, etc. Possibly some thin plywood and a
  saw.

## Instructions

### Setup Raspberry Pi

1. Burn an image onto an SD card, such as Raspberry Pi OS Lite 32-bit (no need
   for "full" version or 64-bit). You may want to configure the image with WiFi
   credentials, a hostname, SSH access, etc.
1. Connect the PiSugar power supply to the Raspberry Pi according to the
   [official instructions](https://github.com/PiSugar/PiSugar/wiki/PiSugar2).
1. Plug the SD card into the Pi, fire it up, and run some installs:

   ```bash
   sudo apt update && sudo apt upgrade
   sudo apt install python3-venv git
   sudo apt install libopenjp2-7      # for Python Pillow library
   curl https://pyenv.run | bash      # follow instructions for enabling pyenv in .bashrc

   # PiSugar server (make sure to select the right PiSugar model -- the PiSugar 2
   # (4-LED) if you bought it from the link above).
   # If you mess up and choose the wrong one, you can run:
   #     sudo dpkg-reconfigure pisugar-server
   curl http://cdn.pisugar.com/release/pisugar-power-manager.sh | sudo bash

   # optional development tools
   sudo apt install zsh neovim
   sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)"
   ```

1. Clone the repo

```bash
cd ~
git clone https://github.com/de-mux/Moon-Pi
```

1. Enable the SPI interface (used by the e-Paper display):

   - ```bash
     sudo raspi-config
     ```
   - Choose Interfacing Options -> SPI -> Yes Enable SPI interface
   - Reboot: `sudo shutdown -r now`
   - `cat /boot/config.txt | grep dtparam`, and verify you see `dtparam=spi=on`
     there
   - To make sure SPI is not occupied, it is recommended to close other drivers'
     coverage. You can use `ls /dev/spi\*` to check whether SPI is occupied. If
     the terminal outputs `/dev/spidev0.1` and `/dev/spidev0.1`, SPI is not
     occupied.

1. Setup Python.

   - You may be able to just use system version. Make sure it's a semi-recent
     version of Python 3:

     ```bash
     $ python --version
     Python 3.9.2
     ```

     If not, install a version 3 with:

     ```bash
     pyenv install 3
     ```

   - Create a virtual environment:

     ```bash
     pyenv virtualenv system moonpi  # if your system version is recent enough
     # ... or ...
     pyenv virtualenv 3 moonpi  # if you had to install version 3
     ```

   - Activate that virtual environment!

     ```bash
     $ pyenv activate moonpi
     (moonpi) $
     ```

   - Install requirements

     ```bash
     pip install -r requirements.txt
     ```

#### Grab fonts

Download the Luminari font into the Moon-Pi/fonts directory. If you decide to go
with different fonts, you will need to update the `FONTS` constant in the
`moon_pi.py` script to point to the right ones. The directory tree should look
like:

```plain
├── README.md
├── fonts
│   ├── Luminari-Regular.ttf
│   ├── SourceSans3-Semibold.ttf
│   └── copy-fonts-here.txt
...
```

- [Luminari](https://dafont101.com/luminari-font/)

#### Setup Software

Most of what you need is in the moon-pi.py script in this repository. Read
through it carefully -- it's copiously commented and will walk you through the
modifications you need to make so that, for example, it says "Happy Birthday!"
on the right day. You may also need to make other modifications depending on
choices you make in the first three steps of this guide. If you change text
lengths or images or how the moon data is formatted, you may need to tweak the
script.

You'll need to set up either a cronjob or a system service to run the moon-pi
script on reboot. In my experience, it was easier to use `systemd`, but YMMV.
Also, note that you'll need to build in some delay time between booting the Pi
and running the script. Otherwise, the script encounters errors by running
before it has permissions for everything it needs. I use a 65-second delay and
it works great.

Once you've got it all set up, remember that when the Pi boots, it'll only run
for a few minutes before shutting itself down. So if you realize you need to fix
or tweak something, you'll need to be sure to SSH into the PI and avail yourself
of `pkill` before the script stops. (In my experience, there's plenty of time to
do this. And if you miss your window, you can always reboot the Pi and try
again!)

#### About The Moon Images

The moon images and background image included were obtained from
[NASA Dial-A-Moon](https://svs.gsfc.nasa.gov/gallery/moonphase/), which are
generally free for personal/educational use (see
[NASA Images and Media Guidelines](https://www.nasa.gov/nasa-brand-center/images-and-media/).
There are enough images to provide a different moon image for every day of a
cycle (30 total to cover a complete ~29.5-day moon phase cycle).

If you want to use your own images, it's recommended (though not strictly
required) to convert the images to the color palette used by your display.

To get a color palette, you can find one of the demo images for your given
display from the Waveshare website, and use that as your palette file. Then use
that file to convert your image to that color palette.

Some image manipulation programs like [ImageMagick](https://imagemagick.org/)
allow you to specify an arbitrary image as a "palette file", while others (like
ffmpeg) require you to create a specific image to be used as a palette file.

I found the best results were obtained by running source images through
ImageMagick with the FloydSteinberg dither setting.

```bash
magick input.png -dither FloydSteinberg -remap waveshare-7color-palette.png output.png
```

(I also tried ffmpeg and Gimp with various dither settings including Floyd
Steinberg, but ImageMagick seemed to yield the best results. Pillow, the Python
library used in this project also has a decent conversion algorithm).

To batch convert multiple images, you can use:

```bash
mkdir converted
for f in /path/to/images/*.png; do magick $f -dither FloydSteinberg -remap images/waveshare-7color-palette.png "converted/$(basename "$f")"; done
```

#### Gather Quotations

You'll have to find your own quotations. I've put a few in the sample file for
you. Note that one field measures the character length of the quotation. This is
because you only have one line (no line wrapping!) to print your quotation, so
the font size changes depending on the line length. If you use a different font
than the one I've chosen, you'll need to figure out your own line length/font
ratios with some trial and error. (That's how I did it!) Use Excel or Numbers or
Sheets or whatever to count up the line lengths for you automatically -- makes
life easier! And don't forget to enclose in quotation marks any quotations that
have commas in them!

#### Moon Phase Calculation

This project uses the "[ephem](https://rhodesmill.org/pyephem/)" library to
determine the moon phase based on the date, allowing the project to run
completely offline.

### Wire it Up

There are a total of 14 wired connections (not counting plugging the battery
into the PiSugar). There are eight wires from the Raspberry Pi to the display
and six wires from the Pi to the PiSugar.

[Here](https://pinout.xyz/) is a pinout of the Raspberry Pi for reference.

#### PiSugar power supply

Here's the
[PiSugar install guide](https://github.com/PiSugar/PiSugar/wiki/PiSugar2).
You'll need this to walk you through setting up the PiSugar to wake up the Pi on
a schedule.

| RPi pin | Description | PiSugar pin |
| ------- | ----------- | ----------- |
| 2       | 5v          | 2           |
| 3       | SDA         | 3           |
| 4       | 5v          | 4           |
| 5       | SCL         | 5           |
| 6       | Gnd         | 6           |
| 9       | Gnd         | 9           |

#### e-Paper display

Here's the
[guide](<https://www.waveshare.com/wiki/7.3inch_e-Paper_HAT_(F)_Manual#Working_With_Raspberry_Pi>)
to connect the display to the Pi

| RPi pin | Description | e-Paper pin |
| ------- | ----------- | ----------- |
| 11      | GPIO 17     | RST         |
| 17      | 3.3v        | VCC         |
| 18      | GPIO 24     | BUSY        |
| 19      | MOSI        | DIN         |
| 20      | Gnd         | GND         |
| 22      | GPIO 25     | DC          |
| 23      | SCLK        | SCLK        |
| 24      | CE0         | CS          |

### Put Together The Frame

Any properly sized frame should work. I used a shadow box, linked above. Once
you have the display and the mat in, I suggest screwing everything into place so
that it doesn't jostle around. I tried cutting my own mats, but couldn't keep it
neat -- a local frame shop was kind enough to cut several of them for me for a
few bucks.

My shadow box came with an insert designed to keep the back panel in place. I
drilled some holes in that and mounted the Pi, the PiSugar, and the battery.
Don't screw all the way through -- there isn't enough space between the insert
and the frame itself to accomodate a screw poking out! I used nylon spacers to
keep the Pi and PiSugar from touching the insert.

The back panels of most frames and shadow boxes are too flimsy for my purposes,
so I cut a piece of thin plywood to size, then drilled ventilation holes. (A Pi
Zero shouldn't have any heat issues, but I'm paranoid.) I also cut a slot for a
USB cable, then stapled a Velcro cable wrap to the back panel for cable
management. You can probably come up with something nicer! Don't forget that you
need a way to keep the back panel in place -- I used some frame turn fasteners
from Amazon. Piece of cake.

### The End

OK, that's the process! Enjoy!

## Todo

- Ideas for stats:
  - Phase name: Waning Gibbous
  - Moon age: 17.36 days
  - Moon illumination: 87.95%
  - Moon tilt: -34.731°
  - Moon sign: Cancer
