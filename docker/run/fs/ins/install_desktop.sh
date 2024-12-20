#!/bin/bash

# Install system dependencies for GUI
apt-get update && apt-get install -y \
    xvfb \
    x11-apps \
    x11-utils \
    x11-xserver-utils \
    xclip \
    xsel \
    openbox \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxrender1 \
    libxext6 \
    python3-tk \
    xauth \
    xcursor-themes \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*
