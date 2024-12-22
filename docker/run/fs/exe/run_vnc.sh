#!/bin/bash

echo "Cleaning up any existing VNC server instances..."
pkill x11vnc || true

# Directory to store VNC password
VNC_DIR="/root/.vnc"

# Check if VNC password is set via environment variable
if [ -n "$VNC_PASSWORD" ]; then
    echo "Setting up VNC password..."
    mkdir -p "$VNC_DIR"
    echo "$VNC_PASSWORD" | x11vnc -storepasswd -f "$VNC_DIR/passwd"
    chmod 600 "$VNC_DIR/passwd"
    VNC_AUTH="-rfbauth $VNC_DIR/passwd"
    echo "VNC password has been set."
else
    echo "No VNC password provided. Running VNC server without password (insecure)."
    VNC_AUTH="-nopw"
fi

# Start x11vnc server
echo "Starting x11vnc server on DISPLAY :99 and port 6666..."
x11vnc -display :99 $VNC_AUTH -forever -shared -bg -rfbport 6666 -o /var/log/x11vnc.log

# Verify that x11vnc started successfully
sleep 2
if pgrep x11vnc > /dev/null; then
    echo "x11vnc server started successfully on port 6666."
else
    echo "Failed to start x11vnc server. Check /var/log/x11vnc.log for details."
    exit 1
fi

echo "=== VNC Server Initialization Completed ==="

# Keep the script running to prevent the Docker container from exiting
# The script will terminate when it receives a SIGINT or SIGTERM signal
echo "VNC server is running. Press Ctrl+C to stop."
while true; do
    sleep 60
done
