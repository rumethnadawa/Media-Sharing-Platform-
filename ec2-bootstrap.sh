#!/bin/bash
# =============================================================================
# MediaShare — EC2 Bootstrap Script (User Data)
# =============================================================================
# This script is executed automatically when the EC2 instance boots for the first time.
# It provisions the server, installs dependencies, pulls your app, and runs it.

set -e
# Exit immediately if any command fails (prevents half-configured systems)

LOG_FILE="/var/log/mediashare-bootstrap.log"
# Define a log file to capture all output (stdout + stderr)

exec >> "$LOG_FILE" 2>&1
# Redirect all script output into the log file for debugging/troubleshooting

echo "=== Bootstrap started: $(date) ==="
# Log start time


# ── 1. System packages ───────────────────────────────────────────────────────
apt-get update -y
# Update package lists from Ubuntu repositories

apt-get install -y git curl unzip ca-certificates gnupg lsb-release
# Install essential tools:
# - git: clone your repo
# - curl: fetch external resources (e.g., Docker GPG key)
# - unzip: extract archives if needed
# - ca-certificates: SSL certificates
# - gnupg: handle GPG keys (for Docker repo)
# - lsb-release: detect Ubuntu version


# ── 2. Install Docker Engine ─────────────────────────────────────────────────
install -m 0755 -d /etc/apt/keyrings
# Create directory to store trusted GPG keys

curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \
    gpg --dearmor -o /etc/apt/keyrings/docker.gpg
# Download Docker’s official GPG key and convert it to binary format

chmod a+r /etc/apt/keyrings/docker.gpg
# Make the key readable by all users

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" > /etc/apt/sources.list.d/docker.list
# Add Docker’s official repository to APT sources

apt-get update -y
# Refresh package list to include Docker repo

apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
# Install Docker engine and related components:
# - docker-ce: Docker engine
# - docker-ce-cli: CLI tools
# - containerd: container runtime
# - buildx: advanced build features
# - compose-plugin: Docker Compose support

systemctl enable docker
# Ensure Docker starts automatically on boot

systemctl start docker
# Start Docker service immediately

# Allow ubuntu user to run docker without sudo
usermod -aG docker ubuntu
# Add default "ubuntu" user to docker group (avoids needing sudo)

echo "Docker installed: $(docker --version)"
echo "Docker Compose installed: $(docker compose version)"
# Log installed versions


# ── 3. Clone the repository ──────────────────────────────────────────────────
# TODO: Replace with your actual GitHub repo URL
REPO_URL="https://github.com/rumethnadawa/Media-Sharing-Platform-.git"
# GitHub repository URL

APP_DIR="/opt/mediashare"
# Directory where the application will live

if [ -d "$APP_DIR" ]; then
    echo "App directory exists, pulling latest..."
    cd "$APP_DIR"
    git pull
    # If directory already exists, update it with latest changes
else
    git clone "$REPO_URL" "$APP_DIR"
    # Otherwise, clone fresh copy from GitHub
fi

cd "$APP_DIR/Media-Sharing-Platform-"
# Move into the project directory (adjust if repo structure changes)


# ── 4. Create .env file with AWS credentials ─────────────────────────────────
# This file provides configuration values for your application

# OPTION A (Recommended): Use IAM Role attached to the EC2 instance
# → No need to store credentials in code (more secure)

# OPTION B: Hardcode credentials (less secure)
# → Replace placeholders below with real AWS keys if not using IAM role

cat > .env << 'ENV'
DB_TYPE=dynamodb
# Database type used by application

AWS_REGION=us-east-1
# AWS region where resources exist

AWS_ACCESS_KEY_ID=REPLACE_WITH_YOUR_KEY
# AWS access key (leave blank if using IAM role)

AWS_SECRET_ACCESS_KEY=REPLACE_WITH_YOUR_SECRET
# AWS secret key (leave blank if using IAM role)

DYNAMODB_TABLE_NAME=MediaMetadata
# DynamoDB table storing metadata

S3_BUCKET=group-a-media-bucket-kdu
# S3 bucket for storing media files

SQS_QUEUE_NAME=media-processing-queue
# SQS queue for async processing (e.g., thumbnails)
ENV

echo ".env written"
# Confirm environment file creation


# ── 5. Build and start with Docker Compose ───────────────────────────────────
docker compose up --build -d
# Build Docker images and start containers in detached mode


echo "=== Bootstrap complete: $(date) ==="
# Log completion time

echo "App is running at: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4):8080"
# Fetch instance public IP from EC2 metadata service and display access URL
