#!/usr/bin/env bash

# Used to brighten moon images. Requires imagemagick

set -o errexit   # exit immediately upon error
set -o pipefail  # exit if any step in a pipeline fails
#set -o xtrace    # print each command before execution
#

SRC_DIR=../images/moon-new
BRIGHTEN_DEST_DIR=../images/moon-brighten
PALETTIZED_DEST_DIR=../images/moon-palettized
PALETTE_FILE=../images/waveshare-7color-palette.png

CURVES="curves=m='0/0 0.1215686275/0.1294117647 0.2470588235/0.4156862745 1/1'"


mkdir -p "$PALETTIZED_DEST_DIR"
mkdir -p "$BRIGHTEN_DEST_DIR"


#for f in $SRC_DIR/*.png; do
#    ffmpeg -i "$f" -vf "$CURVES" $FFMPEG_EFFECT "$BRIGHTEN_DEST_DIR"/$(basename "$f")
#done

for f in $BRIGHTEN_DEST_DIR/*.png; do
    magick $f -dither FloydSteinberg -remap "$PALETTE_FILE" "$PALETTIZED_DEST_DIR"/$(basename "$f" .png).gif
done
