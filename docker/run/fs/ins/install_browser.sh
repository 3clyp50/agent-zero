#!/bin/bash

apt-get update && apt-get install -y \
    firefox-esr
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*
