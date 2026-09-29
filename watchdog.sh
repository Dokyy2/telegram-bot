#!/bin/bash
cd /data/data/com.termux/files/home

while true; do
    echo "Starting interactive_bot.py..."
    python interactive_bot.py
    
    echo "Bot stopped! Restarting in 5 seconds..."
    sleep 5
done