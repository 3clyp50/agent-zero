#!/bin/bash

echo "Cleaning up any existing Xvfb and Xauthority instances..."
pkill Xvfb || true
pkill openbox || true

if [ -f /root/.Xauthority ]; then
    rm /root/.Xauthority
    echo "Removed existing /root/.Xauthority file."
fi

rm -f /tmp/.X*lock
touch /root/.Xauthority

echo "Starting Xvfb..."
Xvfb :99 -screen 0 1024x768x24 &
sleep 2

echo "Generating xauth..."
xauth generate :99 . trusted
xauth list

echo "Starting openbox..."
openbox &
sleep 2

echo "Xvfb and openbox are up and running."