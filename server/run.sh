#!/bin/bash
cd "$(dirname "$0")"
while true; do
    echo "[$(date)] Starting api_server..."
    python3 api_server.py 2>&1
    echo "[$(date)] Server exited, restarting in 3s..."
    sleep 3
done
