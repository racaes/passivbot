#!/bin/bash

# Activate the virtual environment
source /home/tdb/git/passivbot/venv/bin/activate

# Change to the directory containing the Python script
cd /home/tdb/git/passivbot/

# Run the Python script
python passivbot_forever.py bitget_01 GALUSDT \
/home/tdb/config_to_live/GALUSDT__adg_per_exposure_short__absolute__v0b.json \
-cd \
-lev 30 \
-m futures \
-lw 2.5 \
-sw 2.5

# Run the Python script in the background
# nohup python myscript.py > /dev/null 2>&1 &