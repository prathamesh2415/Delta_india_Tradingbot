#!/bin/bash
# Run ONCE on a fresh Ubuntu EC2 instance (as ubuntu user).
set -euo pipefail

APP_DIR="${APP_DIR:-/home/ubuntu/trading-bot}"

echo "=== EC2 setup: trading bot ==="

sudo apt-get update -y
sudo apt-get install -y python3 python3-pip python3-venv git

mkdir -p "$APP_DIR/logs"
cd "$APP_DIR"

if [ ! -d "venv" ]; then
  python3 -m venv venv
fi

source venv/bin/activate
pip install --upgrade pip
pip install -r requirements-prod.txt

if [ ! -f ".env" ]; then
  echo ""
  echo "WARNING: .env not found in $APP_DIR"
  echo "Copy your .env from laptop before starting the service:"
  echo "  scp -i your-key.pem .env ubuntu@YOUR_EC2_IP:$APP_DIR/.env"
  echo ""
fi

sudo cp deploy/trading-bot.service /etc/systemd/system/trading-bot.service
sudo systemctl daemon-reload
sudo systemctl enable trading-bot

echo ""
echo "Setup done. Next steps:"
echo "  1. Place .env in $APP_DIR (with DELTA_API_KEY, DELTA_API_SECRET)"
echo "  2. Whitelist this server's IP on Delta Exchange API settings"
echo "  3. python check_setup.py"
echo "  4. sudo systemctl start trading-bot"
echo "  5. sudo systemctl status trading-bot"
echo "  6. tail -f logs/trading.log"
echo ""
echo "Optional dashboard:"
echo "  sudo cp deploy/trading-dashboard.service /etc/systemd/system/"
echo "  sudo systemctl enable --now trading-dashboard"
echo "  Open http://YOUR_ELASTIC_IP:8000 (whitelist port 8000 to your IP only)"
