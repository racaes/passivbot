#!/bin/bash

# Activate the virtual environment
source /home/tdb/git/passivbot/venv.bak/bin/activate

# Change to the directory containing the Python script
cd /home/tdb/git/passivbot/

# Run the Python script
python forager.py /home/tdb/config_to_live/myconfig_v03.hjson

# Run the Python script in the background
# nohup python myscript.py > /dev/null 2>&1 &