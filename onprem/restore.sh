#!/bin/bash
set -e

# Policy Miner Restore Script
# This script restores all data, configuration, and SSL certificates from a backup

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

if [ -z "$1" ]; then
    echo "Usage: $0 <backup-directory>"
    echo ""
    echo "Example: $0 /var/backups/policy-miner/2024-01-09_14-30-00"
    echo ""
    echo "Available backups:"
    ls -d /var/backups/policy-miner/*/ 2>/dev/null || echo "  (none found)"
    exit 1
fi

BACKUP_DIR="$1"

if [ ! -d "$BACKUP_DIR" ]; then
    echo "❌ Backup directory not found: $BACKUP_DIR"
    exit 1
fi

echo "============================================="
echo "Policy Miner Restore"
echo "============================================="
echo ""
echo "Backup directory: $BACKUP_DIR"
echo ""

# Show backup manifest if exists
if [ -f "$BACKUP_DIR/MANIFEST.txt" ]; then
    echo "Backup information:"
    cat "$BACKUP_DIR/MANIFEST.txt"
    echo ""
fi

# Confirmation
echo "⚠️  WARNING: This will replace all current data!"
echo ""
read -p "Are you sure you want to continue? (yes/no) " -r
echo
if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
    echo "Restore cancelled."
    exit 0
fi

echo ""
echo "Starting restore..."
echo ""

# Stop services
echo "Stopping services..."
cd "$PROJECT_DIR"
docker compose -f docker-compose.onprem.yml down
echo "✅ Services stopped"

# Restore configuration
echo "Restoring configuration..."
if [ -f "$BACKUP_DIR/.env" ]; then
    cp "$BACKUP_DIR/.env" "$SCRIPT_DIR/.env"
    echo "✅ Environment file restored"
fi

if [ -d "$BACKUP_DIR/onprem" ]; then
    cp -r "$BACKUP_DIR/onprem"/* "$SCRIPT_DIR/"
    echo "✅ Configuration files restored"
fi
echo ""

# Restore SSL certificates
echo "Restoring SSL certificates..."
if [ -d "$BACKUP_DIR/ssl" ]; then
    rm -rf "$PROJECT_DIR/ssl"
    cp -r "$BACKUP_DIR/ssl" "$PROJECT_DIR/"
    echo "✅ SSL certificates restored"
fi
echo ""

# Remove old volumes
echo "Removing old Docker volumes..."
docker volume rm poalo_policy_miner_postgres_data 2>/dev/null || true
docker volume rm poalo_policy_miner_redis_data 2>/dev/null || true
docker volume rm poalo_policy_miner_minio_data 2>/dev/null || true
docker volume rm poalo_policy_miner_grafana_data 2>/dev/null || true
docker volume rm poalo_policy_miner_prometheus_data 2>/dev/null || true
echo "✅ Old volumes removed"
echo ""

# Create new volumes
echo "Creating new Docker volumes..."
docker volume create poalo_policy_miner_postgres_data
docker volume create poalo_policy_miner_redis_data
docker volume create poalo_policy_miner_minio_data
docker volume create poalo_policy_miner_grafana_data
docker volume create poalo_policy_miner_prometheus_data
echo "✅ New volumes created"
echo ""

# Restore Docker volumes
echo "Restoring Docker volumes..."

if [ -f "$BACKUP_DIR/postgres_data.tar.gz" ]; then
    echo "  - postgres_data"
    docker run --rm \
      -v poalo_policy_miner_postgres_data:/data \
      -v "$BACKUP_DIR":/backup \
      alpine tar xzf /backup/postgres_data.tar.gz -C /data
fi

if [ -f "$BACKUP_DIR/redis_data.tar.gz" ]; then
    echo "  - redis_data"
    docker run --rm \
      -v poalo_policy_miner_redis_data:/data \
      -v "$BACKUP_DIR":/backup \
      alpine tar xzf /backup/redis_data.tar.gz -C /data
fi

if [ -f "$BACKUP_DIR/minio_data.tar.gz" ]; then
    echo "  - minio_data"
    docker run --rm \
      -v poalo_policy_miner_minio_data:/data \
      -v "$BACKUP_DIR":/backup \
      alpine tar xzf /backup/minio_data.tar.gz -C /data
fi

if [ -f "$BACKUP_DIR/grafana_data.tar.gz" ]; then
    echo "  - grafana_data"
    docker run --rm \
      -v poalo_policy_miner_grafana_data:/data \
      -v "$BACKUP_DIR":/backup \
      alpine tar xzf /backup/grafana_data.tar.gz -C /data
fi

if [ -f "$BACKUP_DIR/prometheus_data.tar.gz" ]; then
    echo "  - prometheus_data"
    docker run --rm \
      -v poalo_policy_miner_prometheus_data:/data \
      -v "$BACKUP_DIR":/backup \
      alpine tar xzf /backup/prometheus_data.tar.gz -C /data
fi

echo "✅ Docker volumes restored"
echo ""

# Start PostgreSQL for database restore
echo "Starting PostgreSQL..."
docker compose -f docker-compose.onprem.yml up -d postgres
sleep 10
echo "✅ PostgreSQL started"
echo ""

# Restore PostgreSQL database
if [ -f "$BACKUP_DIR/postgres.sql.gz" ]; then
    echo "Restoring PostgreSQL database..."
    gunzip -c "$BACKUP_DIR/postgres.sql.gz" | docker compose -f docker-compose.onprem.yml exec -T postgres psql -U policy_miner
    echo "✅ PostgreSQL database restored"
elif [ -f "$BACKUP_DIR/postgres.sql" ]; then
    echo "Restoring PostgreSQL database..."
    cat "$BACKUP_DIR/postgres.sql" | docker compose -f docker-compose.onprem.yml exec -T postgres psql -U policy_miner
    echo "✅ PostgreSQL database restored"
fi
echo ""

# Start all services
echo "Starting all services..."
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
echo "============================================="
echo "Restore Complete!"
echo "============================================="
echo ""
echo "Services:"
docker compose -f docker-compose.onprem.yml ps
echo ""
echo "Application is now restored and running."
echo ""
