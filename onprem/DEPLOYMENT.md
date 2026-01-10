# On-Premises Deployment Guide

This guide walks you through deploying Policy Miner on your on-premises infrastructure.

## Prerequisites

### Hardware Requirements

**Minimum:**
- CPU: 4 cores
- RAM: 8 GB
- Storage: 100 GB SSD
- Network: 1 Gbps

**Recommended (Production):**
- CPU: 8 cores
- RAM: 16 GB
- Storage: 500 GB SSD (RAID 10)
- Network: 10 Gbps
- Backup storage: Additional 500 GB for backups

### Software Requirements

- Docker Engine 24.x or later
- Docker Compose 2.x or later
- OpenSSL (for certificate generation)
- Linux OS (Ubuntu 22.04 LTS or RHEL 8/9 recommended)

## Installation Steps

### 1. Set Up Docker Host

#### For Ubuntu 22.04

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo apt install docker-compose-plugin -y

# Add your user to docker group
sudo usermod -aG docker $USER
newgrp docker

# Enable Docker to start on boot
sudo systemctl enable docker
sudo systemctl start docker
```

#### For RHEL 8/9

```bash
# Update system
sudo dnf update -y

# Install Docker
sudo dnf config-manager --add-repo https://download.docker.com/linux/rhel/docker-ce.repo
sudo dnf install docker-ce docker-ce-cli containerd.io docker-compose-plugin -y

# Start Docker
sudo systemctl enable docker
sudo systemctl start docker

# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker
```

### 2. Clone Repository

```bash
# Clone the repository
git clone https://github.com/doogie-bigmack/application-security-policy-miner.git
cd application-security-policy-miner
```

### 3. Generate SSL Certificates

#### Option A: Self-Signed Certificates (Development/Internal Use)

```bash
# Create SSL directories
mkdir -p ssl/{nginx,postgres,redis,minio}

# Generate self-signed certificate for NGINX
openssl req -x509 -nodes -days 365 -newkey rsa:4096 \
  -keyout ssl/nginx/key.pem \
  -out ssl/nginx/cert.pem \
  -subj "/C=US/ST=State/L=City/O=Organization/CN=policy-miner.local"

# Generate certificate for PostgreSQL
openssl req -x509 -nodes -days 365 -newkey rsa:4096 \
  -keyout ssl/postgres/server.key \
  -out ssl/postgres/server.crt \
  -subj "/C=US/ST=State/L=City/O=Organization/CN=postgres"

chmod 600 ssl/postgres/server.key
chmod 644 ssl/postgres/server.crt

# Generate certificate for Redis
openssl req -x509 -nodes -days 365 -newkey rsa:4096 \
  -keyout ssl/redis/redis.key \
  -out ssl/redis/redis.crt \
  -subj "/C=US/ST=State/L=City/O=Organization/CN=redis"

# Generate CA certificate for Redis
cp ssl/redis/redis.crt ssl/redis/ca.crt

# Generate certificate for MinIO
openssl req -x509 -nodes -days 365 -newkey rsa:4096 \
  -keyout ssl/minio/private.key \
  -out ssl/minio/public.crt \
  -subj "/C=US/ST=State/L=City/O=Organization/CN=minio"
```

#### Option B: Let's Encrypt (Public-Facing)

```bash
# Install certbot
sudo apt install certbot -y  # Ubuntu
# sudo dnf install certbot -y  # RHEL

# Generate certificate (requires DNS pointing to your server)
sudo certbot certonly --standalone -d policy-miner.yourcompany.com

# Copy certificates to project
sudo cp /etc/letsencrypt/live/policy-miner.yourcompany.com/fullchain.pem ssl/nginx/cert.pem
sudo cp /etc/letsencrypt/live/policy-miner.yourcompany.com/privkey.pem ssl/nginx/key.pem
sudo chown $USER:$USER ssl/nginx/*.pem
```

### 4. Configure Environment Variables

```bash
# Copy environment template
cp onprem/.env.example onprem/.env

# Generate secret keys
export SECRET_KEY=$(openssl rand -hex 32)
export ENCRYPTION_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")

# Edit the configuration file
nano onprem/.env
```

**Important:** Update all `CHANGE_ME_*` values with strong, unique passwords.

Required configurations:
- `POSTGRES_PASSWORD`: Strong password for PostgreSQL
- `REDIS_PASSWORD`: Strong password for Redis
- `MINIO_ROOT_USER` and `MINIO_ROOT_PASSWORD`: MinIO credentials
- `SECRET_KEY`: Generate with `openssl rand -hex 32`
- `ENCRYPTION_KEY`: Generate with Python Fernet
- `GRAFANA_ADMIN_PASSWORD`: Strong password for Grafana admin

### 5. Configure Domain Name

#### Option A: Update /etc/hosts (Development)

```bash
# Add to /etc/hosts
sudo bash -c 'echo "127.0.0.1 policy-miner.local" >> /etc/hosts'
```

#### Option B: Configure DNS (Production)

Add A record in your DNS server:
```
policy-miner.yourcompany.com  A  <server-ip>
```

Update `APP_DOMAIN` in `onprem/.env`:
```bash
APP_DOMAIN=policy-miner.yourcompany.com
```

### 6. Deploy Services

```bash
# Load environment variables
export $(cat onprem/.env | grep -v '^#' | xargs)

# Deploy using docker-compose
docker-compose -f docker-compose.onprem.yml up -d

# Wait for services to start (2-3 minutes)
docker-compose -f docker-compose.onprem.yml ps

# Check logs
docker-compose -f docker-compose.onprem.yml logs -f
```

### 7. Verify Deployment

```bash
# Check all services are healthy
docker-compose -f docker-compose.onprem.yml ps

# Test backend health
curl -k https://policy-miner.local/api/health

# Test frontend
curl -k https://policy-miner.local/

# Access the application
# Open browser: https://policy-miner.local
```

### 8. Configure Firewall

```bash
# Allow HTTP and HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Enable firewall
sudo ufw enable
```

## Integration with On-Prem Git Server

### GitLab Self-Hosted

1. Navigate to Repositories page in Policy Miner
2. Click "Add Repository" → "Import from GitLab"
3. Enter your GitLab server URL: `https://gitlab.yourcompany.com`
4. Generate Personal Access Token in GitLab with `read_repository` scope
5. Paste token and browse repositories

### GitHub Enterprise

1. Navigate to Repositories page
2. Click "Add Repository" → "Import from GitHub"
3. Your GitHub Enterprise base URL is auto-detected
4. Generate Personal Access Token with `repo` scope
5. Authenticate and import repositories

### Bitbucket Server

1. Navigate to Repositories page
2. Click "Add Repository" → "Import from Bitbucket"
3. Enter Bitbucket Server URL
4. Generate App Password in Bitbucket
5. Import repositories

### Self-Signed Certificate Support

If your Git server uses self-signed certificates:

```bash
# Add CA certificate to backend container
docker cp /path/to/git-server-ca.crt poalo_policy_miner-backend-1:/usr/local/share/ca-certificates/
docker exec poalo_policy_miner-backend-1 update-ca-certificates
docker-compose -f docker-compose.onprem.yml restart backend
```

## Backup and Restore

### Backup

```bash
#!/bin/bash
# backup.sh

BACKUP_DIR="/backups/policy-miner/$(date +%Y-%m-%d)"
mkdir -p $BACKUP_DIR

# Backup PostgreSQL
docker exec poalo_policy_miner-postgres-1 pg_dump -U policy_miner policy_miner > $BACKUP_DIR/postgres.sql

# Backup Docker volumes
docker run --rm -v poalo_policy_miner_postgres_data:/data -v $BACKUP_DIR:/backup alpine tar czf /backup/postgres_data.tar.gz -C /data .
docker run --rm -v poalo_policy_miner_minio_data:/data -v $BACKUP_DIR:/backup alpine tar czf /backup/minio_data.tar.gz -C /data .
docker run --rm -v poalo_policy_miner_redis_data:/data -v $BACKUP_DIR:/backup alpine tar czf /backup/redis_data.tar.gz -C /data .

# Backup configuration
cp -r onprem/.env $BACKUP_DIR/
cp -r ssl $BACKUP_DIR/

echo "Backup completed: $BACKUP_DIR"
```

### Restore

```bash
#!/bin/bash
# restore.sh

BACKUP_DIR="/backups/policy-miner/2024-01-09"

# Stop services
docker-compose -f docker-compose.onprem.yml down

# Restore PostgreSQL
docker-compose -f docker-compose.onprem.yml up -d postgres
sleep 10
cat $BACKUP_DIR/postgres.sql | docker exec -i poalo_policy_miner-postgres-1 psql -U policy_miner

# Restore volumes
docker run --rm -v poalo_policy_miner_postgres_data:/data -v $BACKUP_DIR:/backup alpine tar xzf /backup/postgres_data.tar.gz -C /data
docker run --rm -v poalo_policy_miner_minio_data:/data -v $BACKUP_DIR:/backup alpine tar xzf /backup/minio_data.tar.gz -C /data
docker run --rm -v poalo_policy_miner_redis_data:/data -v $BACKUP_DIR:/backup alpine tar xzf /backup/redis_data.tar.gz -C /data

# Restore configuration
cp $BACKUP_DIR/.env onprem/.env

# Start all services
docker-compose -f docker-compose.onprem.yml up -d

echo "Restore completed"
```

### Automated Backup (Cron)

```bash
# Add to crontab
crontab -e

# Daily backup at 2 AM
0 2 * * * /path/to/backup.sh

# Weekly backup cleanup (keep last 30 days)
0 3 * * 0 find /backups/policy-miner -type d -mtime +30 -exec rm -rf {} \;
```

## Monitoring and Maintenance

### Access Grafana

1. Open: `https://policy-miner.local/grafana`
2. Login with credentials from `.env` file
3. Default dashboards are pre-configured

### View Logs

```bash
# All services
docker-compose -f docker-compose.onprem.yml logs -f

# Specific service
docker-compose -f docker-compose.onprem.yml logs -f backend

# NGINX access logs
docker-compose -f docker-compose.onprem.yml exec nginx tail -f /var/log/nginx/access.log
```

### Update Application

```bash
# Pull latest changes
git pull origin main

# Rebuild and restart
docker-compose -f docker-compose.onprem.yml build
docker-compose -f docker-compose.onprem.yml up -d

# Clean up old images
docker image prune -f
```

### Health Checks

```bash
# Check service health
docker-compose -f docker-compose.onprem.yml ps

# Check disk usage
df -h

# Check Docker volume usage
docker system df
```

## Troubleshooting

### Services Won't Start

```bash
# Check logs
docker-compose -f docker-compose.onprem.yml logs

# Check environment variables
docker-compose -f docker-compose.onprem.yml config

# Verify SSL certificates exist
ls -la ssl/nginx/
```

### SSL Certificate Errors

```bash
# Verify certificate validity
openssl x509 -in ssl/nginx/cert.pem -text -noout

# Check certificate permissions
ls -la ssl/*/
```

### Database Connection Issues

```bash
# Test PostgreSQL connection
docker-compose -f docker-compose.onprem.yml exec postgres psql -U policy_miner -d policy_miner

# Check PostgreSQL logs
docker-compose -f docker-compose.onprem.yml logs postgres
```

### Can't Access Application

```bash
# Check NGINX is running
docker-compose -f docker-compose.onprem.yml ps nginx

# Check NGINX configuration
docker-compose -f docker-compose.onprem.yml exec nginx nginx -t

# Check firewall
sudo ufw status
```

### Out of Disk Space

```bash
# Clean Docker system
docker system prune -a --volumes

# Check volume sizes
docker system df -v

# Move Docker data directory (if needed)
# Stop Docker, move /var/lib/docker to larger disk, update daemon.json
```

## Security Hardening

### 1. Enable OS-Level Encryption

```bash
# Ubuntu with LUKS encryption
sudo cryptsetup luksFormat /dev/sdb
sudo cryptsetup luksOpen /dev/sdb encrypted-disk
sudo mkfs.ext4 /dev/mapper/encrypted-disk
```

### 2. Configure Log Rotation

```bash
# Create logrotate configuration
sudo tee /etc/logrotate.d/policy-miner <<EOF
/var/lib/docker/volumes/poalo_policy_miner_nginx_logs/_data/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    create 0640 root root
    sharedscripts
    postrotate
        docker-compose -f /path/to/docker-compose.onprem.yml exec nginx nginx -s reload
    endscript
}
EOF
```

### 3. Enable SELinux (RHEL/CentOS)

```bash
# Enable SELinux
sudo setenforce 1

# Make persistent
sudo sed -i 's/SELINUX=permissive/SELINUX=enforcing/' /etc/selinux/config
```

### 4. Regular Security Updates

```bash
# Ubuntu
sudo apt update && sudo apt upgrade -y

# RHEL
sudo dnf update -y

# Docker images
docker-compose -f docker-compose.onprem.yml pull
docker-compose -f docker-compose.onprem.yml up -d
```

## Performance Tuning

### PostgreSQL

Edit `docker-compose.onprem.yml`:
```yaml
command: >
  postgres
  -c shared_buffers=512MB
  -c effective_cache_size=2GB
  -c maintenance_work_mem=128MB
  -c work_mem=16MB
```

### Redis

```yaml
command: >
  redis-server
  --maxmemory 1gb
  --maxmemory-policy allkeys-lru
```

### NGINX

Edit `onprem/nginx.conf`:
```nginx
worker_processes auto;
worker_connections 2048;
```

## Scaling Considerations

For high-availability deployments:

1. **Database Replication**: Set up PostgreSQL streaming replication
2. **Load Balancing**: Add multiple backend/frontend containers
3. **External Storage**: Use NFS/GlusterFS for shared volumes
4. **Redis Cluster**: Configure Redis Sentinel for HA
5. **Backup Redundancy**: Replicate backups to secondary site

## Support

For issues or questions:
- GitHub Issues: https://github.com/doogie-bigmack/application-security-policy-miner/issues
- Documentation: See `README.md`
