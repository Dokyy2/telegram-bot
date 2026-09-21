#!/bin/bash
termux-wake-lock
while true; do
    if ! pgrep -f "python run_monitor.py" > /dev/null
    then
        cd ~/telegram-bot
        python run_monitor.py &
    fi
    sleep 10
done