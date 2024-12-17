#!/bin/bash

# Temporary: Fix torch error
export LD_LIBRARY_PATH=$(python -c "import site; print(site.getsitepackages()[0] + '/nvidia/nvjitlink/lib')"):$LD_LIBRARY_PATH

# Run the Python script
echo "Starting the UI..."
python3 run_ui.py || { echo "Failed to run the Python script"; exit 1; }
