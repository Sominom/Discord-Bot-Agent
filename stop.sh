#!/bin/bash
current_dir=$(pwd)
echo "Stopping bot"
pkill -f $current_dir/bot.py