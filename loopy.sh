#!/usr/bin/env bash

FILE=snes_connector.py

while inotifywait -r -e modify $FILE ../build123d/src; do
    python3 $FILE
done
