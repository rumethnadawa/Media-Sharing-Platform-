#!/bin/bash
# =============================================================================
# MediaShare — EC2 Bootstrap Script (User Data)
# =============================================================================
# Paste this entire script into EC2 → Advanced Details → User Data when
# launching your instance. It runs once as root on first boot.
#
# Prerequisites:
#   - AMI:          Ubuntu 22.04 LTS (ami-0c02fb55956c7d316 in us-east-1)
#   - Instance type: t3.small or larger (1 vCPU, 2 GB RAM)
#   - Security group inbound rules:
#       Port 22   (SSH)   — your IP
#       Port 80   (HTTP)  — 0.0.0.0/0
#       Port 8080 (App)   — 0.0.0.0/0
#   - IAM Role: attach a role with DynamoDB access (or put creds in .env)
# =============================================================================

set -e
LOG_FILE="/var/log/mediashare-bootstrap.log"
exec >> "$LOG_FILE" 2>&1
echo "=== Bootstrap started: $(date) ==="

# ── 1. System packages ───────────────────────────────────────────────────────
apt-get update -y
apt-get install -y git curl unzip ca-certificates gnupg lsb-release

# ── 2. Install Docker Engine ─────────────────────────────────────────────────
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \
    gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" > /etc/apt/sources.list.d/docker.list

apt-get update -y
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

systemctl enable docker
systemctl start docker

# Allow ubuntu user to run docker without sudo
usermod -aG docker ubuntu

echo "Docker installed: $(docker --version)"
echo "Docker Compose installed: $(docker compose version)"

# ── 3. Clone the repository ──────────────────────────────────────────────────
# TODO: Replace with your actual GitHub repo URL
REPO_URL="https://github.com/rumethnadawa/Media-Sharing-Platform-.git"
APP_DIR="/opt/mediashare"

if [ -d "$APP_DIR" ]; then
    echo "App directory exists, pulling latest..."
    cd "$APP_DIR"
    git pull
else
    git clone "$REPO_URL" "$APP_DIR"
fi

cd "$APP_DIR/Media-Sharing-Platform-"   # adjust if your repo root differs

# ── 4. Create .env file with AWS credentials ─────────────────────────────────
# OPTION A (Recommended): Use IAM Role attached to the EC2 instance — no keys needed
#   Just comment out AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY below.
#
# OPTION B: Hardcode credentials (less secure — rotate keys regularly)
cat > .env << 'ENV'
DB_TYPE=dynamodb
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=KIA3CHPOL3E5AV7PZQ4
AWS_SECRET_ACCESS_KEY=+e+rsvi0oU2zHAkEwWers2ISlJnRGGW8BMRAshZu
DYNAMODB_TABLE_NAME=MediaMetadata
S3_BUCKET=group-a-media-bucket-kdu
SQS_QUEUE_NAME=media-processing-queue
ENV

echo ".env written"

# ── 5. Build and start with Docker Compose ───────────────────────────────────
docker compose up --build -d

echo "=== Bootstrap complete: $(date) ==="
echo "App is running at: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4):8080"
