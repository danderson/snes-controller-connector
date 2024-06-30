#!/usr/bin/env bash

FILE=snes_connector.py

python3 $FILE dev
while inotifywait -r -e modify $FILE ../build123d/src; do
    python3 $FILE dev
done
