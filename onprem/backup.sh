#!/bin/bash
set -e

# Policy Miner Backup Script
# This script backs up all data, configuration, and SSL certificates

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKUP_BASE_DIR="${BACKUP_DIR:-/var/backups/policy-miner}"
TIMESTAMP=$(date +%Y-%m-%d_%H-%M-%S)
BACKUP_DIR="$BACKUP_BASE_DIR/$TIMESTAMP"

echo "============================================="
echo "Policy Miner Backup"
echo "============================================="
echo ""
echo "Backup directory: $BACKUP_DIR"
echo ""

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Check if services are running
cd "$PROJECT_DIR"
if ! docker compose -f docker-compose.onprem.yml ps | grep -q "Up"; then
    echo "⚠️  Warning: Services may not be running"
    read -p "Continue with backup? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Backup cancelled."
        exit 0
    fi
fi

# Backup PostgreSQL database
echo "Backing up PostgreSQL database..."
docker compose -f docker-compose.onprem.yml exec -T postgres pg_dump -U policy_miner policy_miner > "$BACKUP_DIR/postgres.sql"
gzip "$BACKUP_DIR/postgres.sql"
echo "✅ PostgreSQL backup complete"

# Backup Docker volumes
echo "Backing up Docker volumes..."

echo "  - postgres_data"
docker run --rm \
  -v poalo_policy_miner_postgres_data:/data \
  -v "$BACKUP_DIR":/backup \
  alpine tar czf /backup/postgres_data.tar.gz -C /data .

echo "  - redis_data"
docker run --rm \
  -v poalo_policy_miner_redis_data:/data \
  -v "$BACKUP_DIR":/backup \
  alpine tar czf /backup/redis_data.tar.gz -C /data .

echo "  - minio_data"
docker run --rm \
  -v poalo_policy_miner_minio_data:/data \
  -v "$BACKUP_DIR":/backup \
  alpine tar czf /backup/minio_data.tar.gz -C /data .

echo "  - grafana_data"
docker run --rm \
  -v poalo_policy_miner_grafana_data:/data \
  -v "$BACKUP_DIR":/backup \
  alpine tar czf /backup/grafana_data.tar.gz -C /data .

echo "  - prometheus_data"
docker run --rm \
  -v poalo_policy_miner_prometheus_data:/data \
  -v "$BACKUP_DIR":/backup \
  alpine tar czf /backup/prometheus_data.tar.gz -C /data .

echo "✅ Docker volumes backup complete"

# Backup configuration files
echo "Backing up configuration..."
if [ -f "$SCRIPT_DIR/.env" ]; then
    cp "$SCRIPT_DIR/.env" "$BACKUP_DIR/.env"
fi
cp -r "$SCRIPT_DIR" "$BACKUP_DIR/onprem"
echo "✅ Configuration backup complete"

# Backup SSL certificates
echo "Backing up SSL certificates..."
if [ -d "$PROJECT_DIR/ssl" ]; then
    cp -r "$PROJECT_DIR/ssl" "$BACKUP_DIR/"
fi
echo "✅ SSL certificates backup complete"

# Create backup manifest
echo "Creating backup manifest..."
cat > "$BACKUP_DIR/MANIFEST.txt" <<EOF
Policy Miner Backup
==================
Timestamp: $TIMESTAMP
Date: $(date)
Hostname: $(hostname)
Docker Compose Version: $(docker compose version)

Contents:
- postgres.sql.gz: PostgreSQL database dump
- postgres_data.tar.gz: PostgreSQL data volume
- redis_data.tar.gz: Redis data volume
- minio_data.tar.gz: MinIO data volume
- grafana_data.tar.gz: Grafana data volume
- prometheus_data.tar.gz: Prometheus data volume
- .env: Environment configuration
- onprem/: Deployment configuration
- ssl/: SSL certificates

To restore, use: onprem/restore.sh $BACKUP_DIR
EOF
echo "✅ Manifest created"

# Calculate backup size
BACKUP_SIZE=$(du -sh "$BACKUP_DIR" | cut -f1)
echo ""
echo "============================================="
echo "Backup Complete!"
echo "============================================="
echo ""
echo "Location: $BACKUP_DIR"
echo "Size: $BACKUP_SIZE"
echo ""
echo "Files:"
ls -lh "$BACKUP_DIR"
echo ""

# Cleanup old backups (keep last 30 days)
if [ -d "$BACKUP_BASE_DIR" ]; then
    echo "Cleaning up old backups (>30 days)..."
    find "$BACKUP_BASE_DIR" -type d -mtime +30 -exec rm -rf {} \; 2>/dev/null || true
    echo "✅ Cleanup complete"
fi

echo ""
echo "Backup completed successfully!"
