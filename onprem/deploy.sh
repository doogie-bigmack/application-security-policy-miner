#!/bin/bash
set -e

# Policy Miner On-Premises Deployment Script
# This script automates the deployment of Policy Miner on-premises

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "============================================="
echo "Policy Miner On-Premises Deployment"
echo "============================================="
echo ""

# Check prerequisites
echo "Checking prerequisites..."

if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

if ! command -v docker compose &> /dev/null && ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

echo "✅ Docker is installed"
echo "✅ Docker Compose is installed"
echo ""

# Check if .env exists
if [ ! -f "$SCRIPT_DIR/.env" ]; then
    echo "❌ Environment file not found: $SCRIPT_DIR/.env"
    echo ""
    echo "Please copy and configure the environment file:"
    echo "  cp $SCRIPT_DIR/.env.example $SCRIPT_DIR/.env"
    echo "  nano $SCRIPT_DIR/.env"
    echo ""
    exit 1
fi

echo "✅ Environment file found"
echo ""

# Check SSL certificates
echo "Checking SSL certificates..."

if [ ! -f "$PROJECT_DIR/ssl/nginx/cert.pem" ] || [ ! -f "$PROJECT_DIR/ssl/nginx/key.pem" ]; then
    echo "⚠️  SSL certificates not found. Generating self-signed certificates..."
    mkdir -p "$PROJECT_DIR/ssl"/{nginx,postgres,redis,minio}

    # NGINX certificate
    openssl req -x509 -nodes -days 365 -newkey rsa:4096 \
      -keyout "$PROJECT_DIR/ssl/nginx/key.pem" \
      -out "$PROJECT_DIR/ssl/nginx/cert.pem" \
      -subj "/C=US/ST=State/L=City/O=Organization/CN=policy-miner.local" 2>/dev/null

    # PostgreSQL certificate
    openssl req -x509 -nodes -days 365 -newkey rsa:4096 \
      -keyout "$PROJECT_DIR/ssl/postgres/server.key" \
      -out "$PROJECT_DIR/ssl/postgres/server.crt" \
      -subj "/C=US/ST=State/L=City/O=Organization/CN=postgres" 2>/dev/null
    chmod 600 "$PROJECT_DIR/ssl/postgres/server.key"
    chmod 644 "$PROJECT_DIR/ssl/postgres/server.crt"

    # Redis certificate
    openssl req -x509 -nodes -days 365 -newkey rsa:4096 \
      -keyout "$PROJECT_DIR/ssl/redis/redis.key" \
      -out "$PROJECT_DIR/ssl/redis/redis.crt" \
      -subj "/C=US/ST=State/L=City/O=Organization/CN=redis" 2>/dev/null
    cp "$PROJECT_DIR/ssl/redis/redis.crt" "$PROJECT_DIR/ssl/redis/ca.crt"

    # MinIO certificate
    openssl req -x509 -nodes -days 365 -newkey rsa:4096 \
      -keyout "$PROJECT_DIR/ssl/minio/private.key" \
      -out "$PROJECT_DIR/ssl/minio/public.crt" \
      -subj "/C=US/ST=State/L=City/O=Organization/CN=minio" 2>/dev/null

    echo "✅ Self-signed certificates generated"
else
    echo "✅ SSL certificates found"
fi
echo ""

# Load environment variables
echo "Loading environment variables..."
set -a
source "$SCRIPT_DIR/.env"
set +a
echo "✅ Environment variables loaded"
echo ""

# Validate required environment variables
echo "Validating configuration..."
REQUIRED_VARS=(
    "POSTGRES_PASSWORD"
    "REDIS_PASSWORD"
    "MINIO_ROOT_USER"
    "MINIO_ROOT_PASSWORD"
    "SECRET_KEY"
    "ENCRYPTION_KEY"
    "GRAFANA_ADMIN_PASSWORD"
)

MISSING_VARS=()
for VAR in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!VAR}" ] || [[ "${!VAR}" == CHANGE_ME* ]]; then
        MISSING_VARS+=("$VAR")
    fi
done

if [ ${#MISSING_VARS[@]} -ne 0 ]; then
    echo "❌ Missing or unconfigured environment variables:"
    for VAR in "${MISSING_VARS[@]}"; do
        echo "  - $VAR"
    done
    echo ""
    echo "Please update $SCRIPT_DIR/.env with proper values."
    exit 1
fi

echo "✅ Configuration validated"
echo ""

# Confirmation
echo "Ready to deploy with the following configuration:"
echo "  Domain: ${APP_DOMAIN:-policy-miner.local}"
echo "  PostgreSQL User: ${POSTGRES_USER:-policy_miner}"
echo "  Grafana User: ${GRAFANA_ADMIN_USER:-admin}"
echo ""

read -p "Continue with deployment? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Deployment cancelled."
    exit 0
fi

echo ""
echo "Starting deployment..."
echo ""

# Build images
echo "Building Docker images..."
cd "$PROJECT_DIR"
docker compose -f docker-compose.onprem.yml build --no-cache
echo "✅ Images built successfully"
echo ""

# Start services
echo "Starting services..."
docker compose -f docker-compose.onprem.yml up -d
echo "✅ Services started"
echo ""

# Wait for services to be healthy
echo "Waiting for services to be healthy..."
TIMEOUT=180
ELAPSED=0
while [ $ELAPSED -lt $TIMEOUT ]; do
    HEALTHY=$(docker compose -f docker-compose.onprem.yml ps --format json | jq -r 'select(.Health=="healthy") | .Service' | wc -l)
    TOTAL=$(docker compose -f docker-compose.onprem.yml ps --format json | jq -r '.Service' | wc -l)

    if [ "$HEALTHY" -eq "$TOTAL" ]; then
        echo "✅ All services are healthy"
        break
    fi

    echo "  Healthy: $HEALTHY/$TOTAL services (${ELAPSED}s elapsed)"
    sleep 5
    ELAPSED=$((ELAPSED + 5))
done

if [ $ELAPSED -ge $TIMEOUT ]; then
    echo "⚠️  Timeout waiting for services to be healthy. Check logs:"
    echo "  docker compose -f docker-compose.onprem.yml logs"
    exit 1
fi

echo ""

# Display status
echo "============================================="
echo "Deployment Complete!"
echo "============================================="
echo ""
echo "Services:"
docker compose -f docker-compose.onprem.yml ps
echo ""
echo "Access URLs:"
echo "  Application: https://${APP_DOMAIN:-policy-miner.local}"
echo "  Monitoring:  https://${APP_DOMAIN:-policy-miner.local}/grafana"
echo ""
echo "Credentials:"
echo "  Grafana User: ${GRAFANA_ADMIN_USER:-admin}"
echo "  Grafana Password: (from .env file)"
echo ""
echo "Next steps:"
echo "  1. Add '${APP_DOMAIN:-policy-miner.local}' to /etc/hosts or configure DNS"
echo "  2. Open https://${APP_DOMAIN:-policy-miner.local} in your browser"
echo "  3. Configure firewall: sudo ufw allow 80/tcp && sudo ufw allow 443/tcp"
echo "  4. Set up backups: See onprem/DEPLOYMENT.md for backup scripts"
echo ""
echo "For troubleshooting, see: onprem/DEPLOYMENT.md"
echo ""
