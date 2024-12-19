#!/bin/bash

# Start Xvfb (for virtual display)
echo "Starting Xvfb..."
Xvfb :99 -screen 0 1024x768x24 +extension RANDR &
sleep 2  # Wait for Xvfb to initialize

# Set the DISPLAY environment variable
export DISPLAY=:99

# Ensure a visible cursor
echo "Setting visible cursor..."
xsetroot -cursor_name left_ptr

# Start Openbox window manager
echo "Starting Openbox..."
openbox &
sleep 1  # Ensure Openbox has started

# Start x11vnc server for VNC access
echo "Starting x11vnc server..."
x11vnc -display :99 -forever -nopw &

# Monitor for failures and restart services if necessary
while true; do
    if ! pgrep -x "Xvfb" > /dev/null; then
        echo "Xvfb stopped. Restarting..."
        Xvfb :99 -screen 0 1024x768x24 +extension RANDR &
        sleep 2
        export DISPLAY=:99
        xsetroot -cursor_name left_ptr
    fi

    if ! pgrep -x "openbox" > /dev/null; then
        echo "Openbox stopped. Restarting..."
        openbox &
        sleep 1
    fi

    if ! pgrep -x "x11vnc" > /dev/null; then
        echo "x11vnc stopped. Restarting..."
        x11vnc -display :99 -forever -nopw &
    fi

    sleep 5  # Check services every 5 seconds
done
