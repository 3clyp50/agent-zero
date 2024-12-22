#!/bin/bash

# Copy all contents from persistent /per to root directory (/) without overwriting
cp -r --no-preserve=ownership,mode /per/* /

# Allow execution of /root/.bashrc and /root/.profile
chmod 444 /root/.bashrc
chmod 444 /root/.profile

# Update package list to save time later (running in background)
apt-get update > /dev/null 2>&1 &

# Start SSH service in background
/usr/sbin/sshd -D &

# Start searxng server in background
su - searxng -c "bash /exe/run_searxng.sh" &

# Run the desktop environment startup script
bash /exe/run_desktop.sh

# Run the vnc server startup script
bash /exe/run_vnc.sh

# Start A0 and handle restart on exit
bash /exe/run_A0.sh 
if [ $? -ne 0 ]; then
    echo "A0 script exited with an error. Restarting container..."
    exit 1
fi
