#!/bin/bash
cd ~/svsu-intelligent
pkill -f api_server.py
sleep 2
nohup ./venv/bin/python3 -u api_server.py > api.log 2>&1 &
echo "Server restart initiated."
