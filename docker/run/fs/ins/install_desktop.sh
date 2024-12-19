#!/bin/bash

# Install system dependencies for GUI and desktop sharing
apt-get update && apt-get install -y \
    xvfb \
    x11-apps \
    x11-utils \
    x11-xserver-utils \
    x11vnc \
    xclip \
    xsel \
    openbox \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxrender1 \
    libxext6 \
    python3-tk \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*