#!/bin/bash

current_dir=$(pwd)
log_file="$current_dir/bot.log"
echo "Starting bot"
source "$current_dir/venv/bin/activate"
pip install -r "$current_dir/requirements.txt"
nohup python3 "$current_dir/bot.py" > "$log_file" 2>&1 &
deactivate
echo "Bot started"
