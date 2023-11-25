#!/bin/bash

# Update and install required software
apt-get update
apt-get install -yq git python3-pip python3-venv nginx
pip3 install --upgrade pip

# Define where to clone your repository and the directory for hw-4
REPO_DIR="/opt/app1"
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

# Change to the hw-4 directory
cd $HW4_DIR

# Nginx Configuration for Flask App
NGINX_CONF="/etc/nginx/sites-available/flask_app"
if [ ! -f "$NGINX_CONF" ]; then
    cat > $NGINX_CONF <<EOL
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    }
}
EOL

    # Enable the configuration by creating a symlink
    ln -s $NGINX_CONF /etc/nginx/sites-enabled/
fi

# Remove the default Nginx configuration if it exists
if [ -e /etc/nginx/sites-enabled/default ]; then
    rm /etc/nginx/sites-enabled/default
fi


# Start Nginx
systemctl restart nginx

# Check if gunicorn is running for hw-4, if not, start it
if ! pgrep -f "gunicorn -b 0.0.0.0:8080 main:app"; then
    $HW4_DIR/env/bin/gunicorn -b 0.0.0.0:8080 main:app --daemon
fi
