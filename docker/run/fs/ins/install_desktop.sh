#!/bin/bash

# Install system dependencies for GUI and desktop sharing
apt-get update && apt-get install -y \
    xvfb \
    openbox \
    x11-apps \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxrender1 \
    libxext6 \
    python3-tk \
    x11vnc \
    fluxbox \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*