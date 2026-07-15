#!/bin/sh

# Start the background sync daemon in the background
echo "Starting synchronization daemon..."
python daemon.py &

# Start the web server in the foreground
echo "Starting web server on port 8080..."
python app.py
