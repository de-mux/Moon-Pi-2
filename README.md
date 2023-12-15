# Moon-Pi 2

An ePaper moon calendar powered by Raspberry Pi

![Final Build](./images/build/final.jpg)

<!-- vim-markdown-toc GFM -->

- [Instructions](#instructions)
  - [Setup Raspberry Pi](#setup-raspberry-pi)
    - [Grab fonts](#grab-fonts)
    - [Disable unneeded services](#disable-unneeded-services)
    - [Setup systemd service](#setup-systemd-service)
    - [Setup Software](#setup-software)
    - [Customization](#customization)
      - [About The Moon Images](#about-the-moon-images)
      - [Background image](#background-image)
      - [Quotations File](#quotations-file)
    - [Moon Phase Calculation](#moon-phase-calculation)
  - [Wire it Up](#wire-it-up)
    - [PiSugar power supply](#pisugar-power-supply)
    - [e-Paper display](#e-paper-display)
  - [Run a quick test](#run-a-quick-test)
    - [Final test](#final-test)
  - [Troubleshooting](#troubleshooting)
  - [Put Together The Frame](#put-together-the-frame)
- [Todo](#todo)

<!-- vim-markdown-toc -->

So you want to build a moon-a-day calendar! You'll need the following:

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
- micro-USB to USB-A cable
- (optional)
  [Raspberry Pi heatsinks](https://www.amazon.com/gp/product/B07ZLZRDXZ)
- soldering iron, screwdriver, screws, standoffs, tape, a drill or Dremel tool,
  etc.

## Instructions

### Setup Raspberry Pi

1. Burn an image onto an SD card, such as Raspberry Pi OS Lite 32-bit (no need
   for "full" version or 64-bit). You should configure the image with "moon" as
   the username, WiFi credentials, a hostname (like moonpi), SSH access enabled,
   etc.
1. Connect the PiSugar power supply to the Raspberry Pi according to the
   [official instructions](https://github.com/PiSugar/PiSugar/wiki/PiSugar2).
1. Plug the SD card into the Pi, fire it up, and run some installs:

   ```bash
   sudo apt update && sudo apt upgrade
   sudo apt install python3-venv git
   sudo apt install libopenjp2-7      # for Python Pillow library
   curl https://pyenv.run | bash      # follow instructions for enabling pyenv in .bashrc

   # PiSugar server (make sure to select the right PiSugar model -- the PiSugar 2
   # (2-LED) if you bought it from the link above). Hint: look at the number of
   #    LEDs next to the PiSugar charging port.
   # If you mess up and choose the wrong one, you can run:
   #     sudo dpkg-reconfigure pisugar-server
   # PiSugar will ask you for a password for the web UI -- be aware that it
   # stores this in plain text on your system.
   curl http://cdn.pisugar.com/release/pisugar-power-manager.sh | sudo bash

   # optional development tools
   sudo apt install zsh neovim
   sudo apt install i2c-tools
   sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)"
   ```

1. Setup PiSugar RTC and auto-boot.

   - Login to the PiSugar power manager server
   - **Sync the RTC/system clock** by going into the sync settings and sync
     "Web > Pi & RTC". This should synchronize both the RPi system clock and the
     PiSugar's RTC with an internet NTP server
   - **Enable autoboot** by changing "Scheduled Wake Up" to "enabled" and choose
     a suitable time, for example 1:00AM
   - Note: you can also manually edit `/etc/pisugar-server/config.json`,
     `/etc/default/pisugar-server`, and `/etc/default/pisugar-poweroff`

1. Enable the SPI interface (used by the e-Paper display) and the I2C interface
   (used by PiSugar):

   - ```bash
     sudo raspi-config
     ```
   - Choose Interfacing Options -> SPI -> Yes Enable SPI interface
   - Choose Interfacing Options -> I2C -> Yes
   - Reboot: `sudo shutdown -r now`
   - `cat /boot/config.txt | grep dtparam`, and verify you see `dtparam=spi=on`
     there
   - To make sure SPI is not occupied, it is recommended to close other drivers'
     coverage. You can use `ls /dev/spi\*` to check whether SPI is occupied. If
     the terminal outputs `/dev/spidev0.1` and `/dev/spidev0.1`, SPI is not
     occupied.

1. Clone the repo

```bash
cd ~
git clone https://github.com/de-mux/Moon-Pi
```

This should put the Moon-Pi directory under your home directory.

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

#### Disable unneeded services

```bash
sudo systemctl disable hciuart
sudo systemctl disable bluealsa
sudo systemctl disable bluetooth

sudo systemctl disable man-db.timer
sudo systemctl disable apt-daily.service
sudo systemctl disable apt-daily.timer
sudo systemctl disable apt-daily-upgrade.timer
sudo systemctl disable apt-daily-upgrade.service
```

Edit `/boot/config.txt` and add the following lines:

```bash
# Disable Bluetooth
dtoverlay=disable-bt
```

#### Setup systemd service

```bash
cd ~/Moon-Pi
sudo cp moonpi.service /etc/systemd/system
sudo systemctl enable moonpi
```

Note that the `sudo` before the `systemctl` command is important, because
although the script is run as the user, it needs sudo to issue the shutdown
command.

Now the Moon Pi script will run once at startup.

Once you've got it all set up, remember that when the Pi boots, it'll only run
for a few minutes before shutting itself down. So if you realize you need to fix
or tweak something, you'll need to be sure to SSH into the PI and run
`touch ~/noshutdown` before the script completes. The script will detect the
presence of `~/noshutdown` and disable auto-shutdown. Don't forget to remove the
file when you're done debugging.

#### Setup Software

Take a look at the `moon-pi.py` script in this repository. Some things you may
want to change:

- `BIRTHDAY_MONTH` AND `BIRTHDAY_DAY` (so it says "Happy Birthday!" on the
  recipient's birthday)
- `FONTS` if you want to use your own fonts
- `WAVESHARE_DISPLAY` if you use a different one than what's used in these
  instructions
  - Note: if you change this, you may need to tweak `DISPLAY_MARGINS`,
    `MOON_SIZE_PX` and some of the values under the methods of the
    `ImageBuilder` class
- `LOCATION` based on where the recipient lives
- `BATTERY_LOW_THRESHOLD` to display the battery low indicator at a different
  threshold

#### Customization

##### About The Moon Images

The moon images and background image included were obtained from
[NASA Dial-A-Moon](https://svs.gsfc.nasa.gov/gallery/moonphase/), which are
generally free for personal/educational use (see
[NASA Images and Media Guidelines](https://www.nasa.gov/nasa-brand-center/images-and-media/).
There are enough images to provide a different moon image for every day of a
cycle (30 total to cover a complete ~29.5-day moon phase cycle).

Note the script will automatically downscale and convert images to the e-Paper
display's color palette using the Floyd-Steinberg dithering method.

##### Background image

The background image used is `./images/screen-template-7in3.png`. If you change
this, you may want to convert it to the e-Paper display's color palette.

Some image manipulation programs like [ImageMagick](https://imagemagick.org/)
allow you to specify an arbitrary image as a "palette file", while others (like
ffmpeg) require you to create a specific image format to be used as a palette
file.

There is a reference palette image `./images/waveshare-7color-palette.png` for
the 7-color waveshare display.

You can also find reference files on the Waveshare website.

I found the best results were obtained by running source images through
ImageMagick with the FloydSteinberg dither setting.

```bash
magick input.png -dither FloydSteinberg -remap images/waveshare-7color-palette.png output.png
```

(I also tried ffmpeg and Gimp with various dither settings including Floyd
Steinberg, but ImageMagick seemed to yield the best results. Pillow, the Python
library used in this project also has a decent conversion algorithm).

To batch convert multiple images, you can use:

```bash
mkdir converted
for f in /path/to/images/*.png; do magick $f -dither FloydSteinberg -remap images/waveshare-7color-palette.png "converted/$(basename "$f")"; done
```

##### Quotations File

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

Before connecting the PiSugar to the Pi, solder the Pi header on so you can
connect the e-Paper display wires in the next step. The PiSugar uses pogo pins
to interface with the RPi, so they should work even when the header is
populated. Alternatively, you can pull the 6 pins of the header corresponding to
the PiSugar's pins prior to soldering so you can get a slightly more comfortable
fit.

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

### Run a quick test

```bash
cd ~/Moon-Pi
pyenv activate moonpi
python moon_pi.py
```

This should update the display with a moon image for the current date.

Note that running the script by itself will not power down the Pi -- this is
done in the run.sh script that is run by the systemd service. This way you can
test the script without worrying about the device rebooting and kicking you out
every time.

#### Final test

Test that the systemd service will run the Moon Pi script at startup by powering
the device off and on. After 30-45 seconds, the script should run, updating the
display. If it didn't work, you can check the logs:

```bash
cat ~/moonpi.log  # for the script log file
journalctl -u moonpi.service  # for the systemd log
```

If you need to, you can disable auto-shutdown in the service by creating a file
in `$HOME` called `noshutdown`. Just remember to remove it again after you're
done debugging so the device doesn't remain on indefinitely.

### Troubleshooting

To check on status of moonpi.service:

```bash
journalctl status moonpi
```

For system boot information, you can use journalctl:

```bash
# Show systemd logs for current boot
journalctl -b
# List all boot timestamps
journalctl --list-boots
# Show previous boot
journalctl -b -1
```

### Put Together The Frame

Align the display with the mat and tape it into place. You may need to modify
the insert that comes with the shadow box a little to accomodate things like the
e-Paper cable. I cut out a slot for the e-Paper cable so the insert wasn't
pressing up against it, and also cut some channels for the tie-wrap fasteners
that I used to mount the Raspberry Pi and PiSugar assembly.

Affix the RPi/PiSugar assembly to the shadow box insert, and check that it fits
inside the shadow box. Make sure there is nothing touching the display that
could damage it. You might want some padding to protect the back of the display
from touching the Pi assembly.

Drill a hole in the back panel for the PiSugar charging port.

Mount the e-Paper HAT somehow (I used screws to mount it to the back of the back
panel).

Connect all cables, power on the device, and you're done!

## Todo

- Ideas for stats:
  - Phase name: Waning Gibbous
  - Moon age: 17.36 days
  - Moon illumination: 87.95%
  - Moon tilt: -34.731°
  - Moon sign: Cancer
