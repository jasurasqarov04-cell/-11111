#!/bin/sh
set -e
cd /app
python fly_health.py &
exec python bot.py
