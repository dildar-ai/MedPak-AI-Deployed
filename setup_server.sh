#!/bin/bash

# MedPak AI - Automated Ubuntu Server Setup Script
# Designed for Oracle Cloud ARM A1 Instances + DuckDNS

set -e # Exit on any error

echo "========================================="
echo "   MedPak AI Backend Setup Script        "
echo "========================================="

# 1. Collect Variables
read -p "Enter your DuckDNS domain (e.g. medpak.duckdns.org): " DOMAIN_NAME
read -p "Enter your Email (for Let's Encrypt SSL): " EMAIL
read -p "Enter your GROQ_API_KEY: " GROQ_API_KEY
read -p "Enter a SECRET_KEY for JWT (or press enter to auto-generate): " SECRET_KEY

if [ -z "$SECRET_KEY" ]; then
    SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
fi

REPO_URL="https://github.com/dildar-ai/MedPak-AI.git"
APP_DIR="/opt/medpak-ai"

# 2. Update System & Install Dependencies
echo ">>> Updating system and installing dependencies..."
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3-pip python3-venv nginx certbot python3-certbot-nginx git libgl1 libglib2.0-0

# 3. Clone Repository
echo ">>> Cloning repository..."
if [ -d "$APP_DIR" ]; then
    sudo rm -rf "$APP_DIR"
fi
sudo git clone $REPO_URL $APP_DIR
sudo chown -R $USER:$USER $APP_DIR

# 4. Setup Python Virtual Environment
echo ">>> Setting up Python environment..."
cd $APP_DIR/backend
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 5. Configure Environment Variables
echo ">>> Configuring .env..."
cat <<EOF > .env
GROQ_API_KEY=$GROQ_API_KEY
SECRET_KEY=$SECRET_KEY
CORS_ORIGINS=["*"]
DEBUG=false
EOF

# 6. Configure Nginx Reverse Proxy
echo ">>> Configuring Nginx..."
sudo bash -c "cat <<EOF > /etc/nginx/sites-available/medpak
server {
    listen 80;
    server_name $DOMAIN_NAME;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \\\$host;
        proxy_set_header X-Real-IP \\\$remote_addr;
        proxy_set_header X-Forwarded-For \\\$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \\\$scheme;
    }
}
EOF"

sudo ln -sf /etc/nginx/sites-available/medpak /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo systemctl restart nginx

# 7. Generate SSL Certificate
echo ">>> Generating SSL Certificate via Let's Encrypt..."
sudo certbot --nginx -d $DOMAIN_NAME --non-interactive --agree-tos -m $EMAIL

# 8. Setup Systemd Service
echo ">>> Creating Systemd Service..."
sudo bash -c "cat <<EOF > /etc/systemd/system/medpak.service
[Unit]
Description=MedPak AI FastAPI Backend
After=network.target

[Service]
User=$USER
WorkingDirectory=$APP_DIR/backend
Environment=\"PATH=$APP_DIR/backend/venv/bin\"
ExecStart=$APP_DIR/backend/venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
EOF"

sudo systemctl daemon-reload
sudo systemctl enable medpak
sudo systemctl start medpak

echo "========================================="
echo "   Setup Complete!                       "
echo "========================================="
echo "Your backend is now running at: https://$DOMAIN_NAME/api/health"
echo "You can check the logs anytime with: sudo journalctl -u medpak -f"
