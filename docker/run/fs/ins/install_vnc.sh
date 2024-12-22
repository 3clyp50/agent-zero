#!/bin/bash

apt-get update && apt-get install -y \
    x11vnc \
    xfonts-base \
    xfonts-100dpi \
    xfonts-75dpi \
    xfonts-scalable \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*
