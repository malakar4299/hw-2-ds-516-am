#!/bin/bash

# Update and install required software
apt-get update
apt-get install -yq git python3-pip python3-venv

# Define where to clone your repository and the directory for hw-4
REPO_DIR="/opt/app"
HW4_DIR="$REPO_DIR/hw-4"

# Fetch source code if it doesn't exist
if [ ! -d "$REPO_DIR" ]; then
    git clone https://github.com/malakar4299/hw-ds-561-am.git $REPO_DIR
fi

# Python environment setup for hw-4
if [ ! -d "$HW4_DIR/env" ]; then
    python3 -m venv $HW4_DIR/env
    $HW4_DIR/env/bin/pip install --upgrade pip
    $HW4_DIR/env/bin/pip install -r $HW4_DIR/requirements.txt
fi

# Python start environment for hw-4
if [ -d "$HW4_DIR/env" ]; then
    source $HW4_DIR/env/bin/activate
fi

# Start the country logger app directly
$HW4_DIR/env/bin/python3 $HW4_DIR/logger.py > $HW4_DIR/banned-data-logs.log 2>&1 &
