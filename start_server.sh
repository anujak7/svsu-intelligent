#!/bin/bash
cd /home/svsuuser/svsu-intelligent
echo "Starting SVSU Server..."
./venv/bin/python3 api_server.py > api.log 2>&1
echo "Finished."
