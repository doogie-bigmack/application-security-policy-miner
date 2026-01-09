#!/bin/bash

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Policy Miner Kubernetes Deployment Script${NC}"
echo "=========================================="

# Check prerequisites
echo -e "\n${YELLOW}Checking prerequisites...${NC}"

if ! command -v kubectl &> /dev/null; then
    echo -e "${RED}Error: kubectl not found. Please install kubectl.${NC}"
    exit 1
fi

if ! kubectl cluster-info &> /dev/null; then
    echo -e "${RED}Error: Cannot connect to Kubernetes cluster. Please configure kubectl.${NC}"
    exit 1
fi

echo -e "${GREEN}✓ kubectl configured and cluster accessible${NC}"

# Check if namespace exists
if kubectl get namespace policy-miner &> /dev/null; then
    echo -e "${YELLOW}Warning: Namespace 'policy-miner' already exists.${NC}"
    read -p "Do you want to continue? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Deploy namespace
echo -e "\n${YELLOW}Creating namespace...${NC}"
kubectl apply -f namespace.yaml
echo -e "${GREEN}✓ Namespace created${NC}"

# Deploy secrets
echo -e "\n${YELLOW}Creating secrets...${NC}"
echo -e "${RED}WARNING: Please ensure you have updated secrets.yaml with production values!${NC}"
read -p "Have you updated secrets.yaml? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${RED}Please update secrets.yaml before deploying.${NC}"
    exit 1
fi
kubectl apply -f secrets.yaml
echo -e "${GREEN}✓ Secrets created${NC}"

# Deploy config maps
echo -e "\n${YELLOW}Creating config maps...${NC}"
kubectl apply -f configmap.yaml
echo -e "${GREEN}✓ Config maps created${NC}"

# Deploy PostgreSQL
echo -e "\n${YELLOW}Deploying PostgreSQL...${NC}"
kubectl apply -f postgres-statefulset.yaml
echo -e "${GREEN}✓ PostgreSQL deployment created${NC}"

# Deploy Redis
echo -e "\n${YELLOW}Deploying Redis...${NC}"
kubectl apply -f redis-deployment.yaml
echo -e "${GREEN}✓ Redis deployment created${NC}"

# Deploy MinIO
echo -e "\n${YELLOW}Deploying MinIO...${NC}"
kubectl apply -f minio-deployment.yaml
echo -e "${GREEN}✓ MinIO deployment created${NC}"

# Wait for databases to be ready
echo -e "\n${YELLOW}Waiting for databases to be ready (this may take a few minutes)...${NC}"
kubectl wait --for=condition=ready pod -l app=postgres -n policy-miner --timeout=300s && echo -e "${GREEN}✓ PostgreSQL ready${NC}" || echo -e "${RED}✗ PostgreSQL failed to start${NC}"
kubectl wait --for=condition=ready pod -l app=redis -n policy-miner --timeout=300s && echo -e "${GREEN}✓ Redis ready${NC}" || echo -e "${RED}✗ Redis failed to start${NC}"
kubectl wait --for=condition=ready pod -l app=minio -n policy-miner --timeout=300s && echo -e "${GREEN}✓ MinIO ready${NC}" || echo -e "${RED}✗ MinIO failed to start${NC}"

# Deploy backend
echo -e "\n${YELLOW}Deploying backend...${NC}"
kubectl apply -f backend-deployment.yaml
echo -e "${GREEN}✓ Backend deployment created${NC}"

# Deploy frontend
echo -e "\n${YELLOW}Deploying frontend...${NC}"
kubectl apply -f frontend-deployment.yaml
echo -e "${GREEN}✓ Frontend deployment created${NC}"

# Deploy ingress
echo -e "\n${YELLOW}Deploying ingress...${NC}"
kubectl apply -f ingress.yaml
echo -e "${GREEN}✓ Ingress created${NC}"

# Wait for deployments
echo -e "\n${YELLOW}Waiting for deployments to be ready...${NC}"
kubectl wait --for=condition=available deployment/backend -n policy-miner --timeout=300s && echo -e "${GREEN}✓ Backend ready${NC}" || echo -e "${RED}✗ Backend failed to start${NC}"
kubectl wait --for=condition=available deployment/frontend -n policy-miner --timeout=300s && echo -e "${GREEN}✓ Frontend ready${NC}" || echo -e "${RED}✗ Frontend failed to start${NC}"

# Display status
echo -e "\n${GREEN}=========================================="
echo -e "Deployment Complete!${NC}"
echo -e "${GREEN}==========================================${NC}\n"

echo -e "${YELLOW}Deployment Status:${NC}"
kubectl get pods -n policy-miner

echo -e "\n${YELLOW}Services:${NC}"
kubectl get svc -n policy-miner

echo -e "\n${YELLOW}Ingress:${NC}"
kubectl get ingress -n policy-miner

echo -e "\n${GREEN}Next Steps:${NC}"
echo "1. Configure DNS to point to the ingress load balancer IP"
echo "2. Verify TLS certificate is issued (if using cert-manager)"
echo "3. Access the application at your configured domain"
echo "4. Monitor logs: kubectl logs -n policy-miner -l app=backend -f"

echo -e "\n${YELLOW}Useful Commands:${NC}"
echo "- View all resources: kubectl get all -n policy-miner"
echo "- View logs: kubectl logs -n policy-miner -l app=backend --tail=100 -f"
echo "- Port forward (testing): kubectl port-forward -n policy-miner svc/frontend-service 8080:80"
echo "- Delete deployment: kubectl delete namespace policy-miner"
