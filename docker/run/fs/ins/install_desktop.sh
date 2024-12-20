#!/bin/bash

apt-get update && apt-get install -y \
    xvfb \
    xauth \
    x11-utils \
    x11-xserver-utils \
    libgl1-mesa-glx \
    openbox \
    python3 \
    python3-pip \
    python3-venv \
    python3-tk \
    python3-dev \
    gnome-screenshot \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*
