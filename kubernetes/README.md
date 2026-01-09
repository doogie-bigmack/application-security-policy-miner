# Kubernetes Deployment Guide

This directory contains Kubernetes manifests for deploying Policy Miner to cloud environments (AWS EKS, Azure AKS, or any Kubernetes cluster).

## Prerequisites

- Kubernetes cluster (1.24+)
- kubectl configured
- Helm 3.x (for optional components)
- Container registry (ECR, ACR, Docker Hub, etc.)

## Quick Start

### 1. Build and Push Docker Images

```bash
# Build backend image
docker build -t your-registry/policy-miner-backend:latest -f backend/Dockerfile backend/

# Build frontend image
docker build -t your-registry/policy-miner-frontend:latest -f frontend/Dockerfile frontend/

# Push images
docker push your-registry/policy-miner-backend:latest
docker push your-registry/policy-miner-frontend:latest
```

### 2. Update Image References

Edit `backend-deployment.yaml` and `frontend-deployment.yaml` to use your registry URLs:

```yaml
image: your-registry/policy-miner-backend:latest
image: your-registry/policy-miner-frontend:latest
```

### 3. Configure Secrets

**CRITICAL**: Update `secrets.yaml` with production values:

```bash
# Generate encryption key
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Generate JWT secret
openssl rand -base64 32

# Update secrets.yaml with real values
```

**Production Note**: Use external secret management:
- AWS: AWS Secrets Manager + External Secrets Operator
- Azure: Azure Key Vault + External Secrets Operator
- HashiCorp Vault
- Sealed Secrets

### 4. Deploy to Kubernetes

```bash
# Create namespace
kubectl apply -f namespace.yaml

# Create secrets (update first!)
kubectl apply -f secrets.yaml

# Create config maps
kubectl apply -f configmap.yaml

# Deploy PostgreSQL
kubectl apply -f postgres-statefulset.yaml

# Deploy Redis
kubectl apply -f redis-deployment.yaml

# Deploy MinIO
kubectl apply -f minio-deployment.yaml

# Wait for databases to be ready
kubectl wait --for=condition=ready pod -l app=postgres -n policy-miner --timeout=300s
kubectl wait --for=condition=ready pod -l app=redis -n policy-miner --timeout=300s
kubectl wait --for=condition=ready pod -l app=minio -n policy-miner --timeout=300s

# Deploy backend
kubectl apply -f backend-deployment.yaml

# Deploy frontend
kubectl apply -f frontend-deployment.yaml

# Deploy ingress
kubectl apply -f ingress.yaml
```

### 5. Verify Deployment

```bash
# Check all pods are running
kubectl get pods -n policy-miner

# Check services
kubectl get svc -n policy-miner

# Check ingress
kubectl get ingress -n policy-miner

# View logs
kubectl logs -n policy-miner -l app=backend --tail=100
kubectl logs -n policy-miner -l app=frontend --tail=100
```

## Cloud Provider Specific Configuration

### AWS EKS

1. **Create EKS Cluster**:
```bash
eksctl create cluster \
  --name policy-miner \
  --region us-east-1 \
  --nodegroup-name standard-workers \
  --node-type t3.large \
  --nodes 3 \
  --nodes-min 3 \
  --nodes-max 10 \
  --managed
```

2. **Install AWS Load Balancer Controller**:
```bash
helm repo add eks https://aws.github.io/eks-charts
helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
  -n kube-system \
  --set clusterName=policy-miner
```

3. **Storage Class** - Update manifests to use `gp3`:
```yaml
storageClassName: gp3
```

4. **Use AWS Bedrock** for LLM:
```yaml
# In configmap.yaml
LLM_PROVIDER: "aws_bedrock"
AWS_BEDROCK_REGION: "us-east-1"
AWS_BEDROCK_MODEL_ID: "anthropic.claude-sonnet-4-20250514-v1:0"
```

5. **IAM Roles** - Use IRSA (IAM Roles for Service Accounts):
```bash
# Create IAM role for backend pods
eksctl create iamserviceaccount \
  --name backend-sa \
  --namespace policy-miner \
  --cluster policy-miner \
  --attach-policy-arn arn:aws:iam::aws:policy/AmazonBedrockFullAccess \
  --approve
```

### Azure AKS

1. **Create AKS Cluster**:
```bash
az aks create \
  --resource-group policy-miner-rg \
  --name policy-miner \
  --node-count 3 \
  --node-vm-size Standard_D4s_v3 \
  --enable-cluster-autoscaler \
  --min-count 3 \
  --max-count 10 \
  --generate-ssh-keys
```

2. **Install Application Gateway Ingress Controller**:
```bash
az aks enable-addons \
  --resource-group policy-miner-rg \
  --name policy-miner \
  --addon ingress-appgw \
  --appgw-name policy-miner-appgw
```

3. **Storage Class** - Update manifests to use `managed-premium`:
```yaml
storageClassName: managed-premium
```

4. **Use Azure OpenAI** for LLM:
```yaml
# In configmap.yaml
LLM_PROVIDER: "azure_openai"
```

5. **Managed Identity** - Use workload identity:
```bash
az aks update \
  --resource-group policy-miner-rg \
  --name policy-miner \
  --enable-workload-identity
```

## Auto-Scaling

The deployment includes Horizontal Pod Autoscalers (HPA):

- **Backend**: Scales 3-10 pods based on CPU (70%) and memory (80%)
- **Frontend**: Scales 2-10 pods based on CPU (70%)

To enable cluster autoscaling:

**AWS**:
```bash
# Already enabled in eksctl command above
```

**Azure**:
```bash
# Already enabled in az aks create command above
```

## High Availability

The deployment is configured for high availability:

- **Backend**: 3 replicas across availability zones
- **Frontend**: 2 replicas across availability zones
- **PostgreSQL**: StatefulSet with persistent storage
- **Redis**: Single replica (consider Redis Sentinel or Redis Cluster for HA)
- **MinIO**: Single replica (consider distributed MinIO for HA)

### Production HA Recommendations

1. **PostgreSQL**: Use managed database service
   - AWS RDS PostgreSQL with Multi-AZ
   - Azure Database for PostgreSQL with HA

2. **Redis**: Use managed Redis service
   - AWS ElastiCache Redis with cluster mode
   - Azure Cache for Redis with HA

3. **Object Storage**: Use managed object storage
   - AWS S3 (replace MinIO)
   - Azure Blob Storage (replace MinIO)

## Monitoring

Install Prometheus and Grafana for monitoring:

```bash
# Add Prometheus Helm repo
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts

# Install Prometheus
helm install prometheus prometheus-community/kube-prometheus-stack \
  --namespace policy-miner \
  --set prometheus.prometheusSpec.serviceMonitorSelectorNilUsesHelmValues=false
```

## Backup and Disaster Recovery

### Database Backups

**PostgreSQL**:
```bash
# Manual backup
kubectl exec -n policy-miner postgres-0 -- pg_dump -U policy_miner policy_miner > backup.sql

# Restore
kubectl exec -i -n policy-miner postgres-0 -- psql -U policy_miner policy_miner < backup.sql
```

**Automated Backups**:
- AWS RDS: Automatic backups to S3
- Azure Database: Automatic backups with point-in-time restore

### Object Storage Backups

**MinIO**:
```bash
# Use mc (MinIO Client) for backups
mc mirror policy-miner-pod:/policy-miner /backup/location
```

**Cloud Storage**:
- AWS S3: Enable versioning and cross-region replication
- Azure Blob: Enable soft delete and geo-redundancy

## Security Hardening

1. **Network Policies**: Restrict pod-to-pod communication
2. **Pod Security Standards**: Enforce restricted PSS
3. **Secret Management**: Use external secret stores
4. **Image Scanning**: Scan images for vulnerabilities
5. **RBAC**: Implement least privilege access
6. **TLS Everywhere**: Enable TLS for all services
7. **Private Endpoints**: Use private VPC endpoints for cloud services

## Troubleshooting

### Pods not starting
```bash
kubectl describe pod <pod-name> -n policy-miner
kubectl logs <pod-name> -n policy-miner
```

### Database connection issues
```bash
kubectl exec -it -n policy-miner postgres-0 -- psql -U policy_miner -d policy_miner
```

### Ingress not working
```bash
kubectl describe ingress policy-miner-ingress -n policy-miner
kubectl get svc -n ingress-nginx  # or check your ingress controller namespace
```

### Application errors
```bash
kubectl logs -n policy-miner -l app=backend --tail=200 -f
```

## Cost Optimization

1. **Use spot instances** for non-critical workloads
2. **Right-size resources** based on actual usage
3. **Enable cluster autoscaler** to scale down during off-peak
4. **Use reserved instances** for production workloads
5. **Implement pod disruption budgets** for graceful scaling

## Uninstalling

```bash
# Delete all resources
kubectl delete namespace policy-miner

# Delete PVCs (if not auto-deleted)
kubectl delete pvc -n policy-miner --all
```

## Support

For issues or questions, please open an issue on GitHub:
https://github.com/doogie-bigmack/application-security-policy-miner/issues
