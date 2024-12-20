#!/bin/bash

echo "Setting up Xauthority..."
export DISPLAY=:99
export XAUTHORITY=/root/.Xauthority

# Create the Xauthority file and generate a key
touch /root/.Xauthority
xauth generate $DISPLAY . trusted
xauth list

echo "Starting Xvfb..."
Xvfb $DISPLAY -screen 0 1024x768x24 +extension RANDR &
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

# Monitor for failures and restart services if necessary
while true; do
    if ! pgrep -x "Xvfb" > /dev/null; then
        echo "Xvfb stopped. Restarting..."
        Xvfb $DISPLAY -screen 0 1024x768x24 +extension RANDR &
        sleep 2
        xauth generate $DISPLAY . trusted
        xsetroot -cursor_name left_ptr
    fi

    if ! pgrep -x "openbox" > /dev/null; then
        echo "Openbox stopped. Restarting..."
        openbox &
        sleep 1
    fi

    sleep 5  # Check services every 5 seconds
done
