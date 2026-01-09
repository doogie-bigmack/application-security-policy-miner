# Application Security Policy Miner

AI-powered tool for analyzing and mining security policies from code, databases, and infrastructure.

## Features

- **AI Rule Mining**: Extract Who/What/How/When policies using Claude Sonnet 4
- **Multi-Source Support**: Git repositories, databases, mainframes
- **Policy Translation**: Convert policies to OPA Rego, AWS Cedar, or custom formats
- **Risk Scoring**: Multi-dimensional risk analysis
- **Conflict Detection**: Identify contradictory policies
- **Change Detection**: Auto-detect policy changes with git integration
- **Multi-Tenancy**: Full tenant isolation with RLS
- **Enterprise Scale**: Process 1,000+ applications with batch scanning

## Tech Stack

- **Frontend**: Bun, React, TailwindCSS, TypeScript
- **Backend**: FastAPI, SQLAlchemy, PostgreSQL 16, Redis
- **AI**: Claude Sonnet 4 via AWS Bedrock or Azure OpenAI
- **Deployment**: Docker Compose (local), Kubernetes (cloud)

## Quick Start (Local Development)

### Prerequisites

- Docker 27.x and Docker Compose 2.x
- Bun 1.1.x (for frontend development)
- Python 3.12.x (for backend development)

### 1. Clone Repository

```bash
git clone https://github.com/doogie-bigmack/application-security-policy-miner.git
cd application-security-policy-miner
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env and set your ANTHROPIC_API_KEY or configure AWS Bedrock/Azure OpenAI
```

### 3. Start Services

```bash
docker-compose up -d
```

### 4. Access Application

- **Frontend**: http://localhost:3333
- **Backend API**: http://localhost:7777
- **API Docs**: http://localhost:7777/docs
- **Grafana**: http://localhost:4000
- **MinIO Console**: http://localhost:9005

### 5. Create First Repository

1. Navigate to http://localhost:3333
2. Click "Repositories" → "Add Repository"
3. Enter a Git repository URL
4. Click "Start Scan" to extract policies

<<<<<<< HEAD
## Cloud Deployment (Kubernetes)

For production deployments to AWS EKS, Azure AKS, or any Kubernetes cluster:

### Quick Deploy

=======
## Deployment Options

### Option 1: On-Premises Deployment (Docker Compose)

For on-premises or self-hosted deployments with NGINX reverse proxy, TLS, and production hardening:

**Quick Deploy:**
```bash
cd onprem
cp .env.example .env
# Edit .env with your configuration
./deploy.sh
```

**Features:**
- NGINX reverse proxy with TLS/SSL
- PostgreSQL, Redis, MinIO with encryption at rest and in transit
- Automated backup/restore scripts
- No external dependencies (air-gapped support)
- Integration with on-prem Git servers (GitLab, GitHub Enterprise, Bitbucket Server)

See [onprem/DEPLOYMENT.md](onprem/DEPLOYMENT.md) for detailed on-premises deployment guide.

### Option 2: Cloud Deployment (Kubernetes)

For production deployments to AWS EKS, Azure AKS, or any Kubernetes cluster:

**Quick Deploy:**
>>>>>>> d2cadf0 (feat: Add comprehensive on-premises deployment support with NGINX, TLS, and automation scripts)
```bash
cd kubernetes
./deploy.sh
```

<<<<<<< HEAD
### Manual Deploy

=======
**Manual Deploy:**
>>>>>>> d2cadf0 (feat: Add comprehensive on-premises deployment support with NGINX, TLS, and automation scripts)
```bash
# Update secrets and images first
kubectl apply -k kubernetes/overlays/aws  # or azure
```

<<<<<<< HEAD
See [kubernetes/README.md](kubernetes/README.md) for detailed deployment guide.
=======
See [kubernetes/README.md](kubernetes/README.md) for detailed cloud deployment guide.
>>>>>>> d2cadf0 (feat: Add comprehensive on-premises deployment support with NGINX, TLS, and automation scripts)

## Development

### Frontend

```bash
cd frontend
bun install
bun run dev
```

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Linting

```bash
# Frontend
cd frontend
bun run lint
bun run format

# Backend
cd backend
ruff check --fix
ruff format
```

### Testing

```bash
# Backend unit tests
cd backend
pytest

# Frontend tests
cd frontend
bun test
```

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌──────────────┐
│   Frontend  │────▶│   Backend   │────▶│  PostgreSQL  │
│   (React)   │     │  (FastAPI)  │     │  (pgvector)  │
└─────────────┘     └─────────────┘     └──────────────┘
                           │
                    ┌──────┴──────┐
                    │             │
              ┌─────▼─────┐ ┌─────▼─────┐
              │   Redis   │ │   MinIO   │
              │  (Cache)  │ │ (Storage) │
              └───────────┘ └───────────┘
                    │
              ┌─────▼─────────┐
              │ Claude Agent  │
              │  AWS Bedrock  │
              │  Azure OpenAI │
              └───────────────┘
```

## Configuration

### LLM Provider

**AWS Bedrock (Recommended for Production)**:
```bash
export LLM_PROVIDER=aws_bedrock
export AWS_BEDROCK_REGION=us-east-1
export AWS_ACCESS_KEY_ID=your-key
export AWS_SECRET_ACCESS_KEY=your-secret
```

**Azure OpenAI**:
```bash
export LLM_PROVIDER=azure_openai
export AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
export AZURE_OPENAI_API_KEY=your-key
export AZURE_OPENAI_DEPLOYMENT_NAME=your-deployment
```

**Anthropic Direct API (Development Only)**:
```bash
export ANTHROPIC_API_KEY=sk-ant-your-key
```

### Database

PostgreSQL with pgvector extension for semantic policy similarity.

### Security

- Encryption at rest (Fernet)
- Encryption in transit (TLS)
- Secret detection (pre-scan)
- Audit logging (all AI operations)
- Multi-tenancy (RLS)

## Documentation

- [PRD](prd.json) - Product requirements and user stories
- [Progress](progress.txt) - Implementation progress
- [Kubernetes Deployment](kubernetes/README.md) - Cloud deployment guide
- [API Documentation](http://localhost:7777/docs) - Interactive API docs

## Contributing

1. Pick a task from `prd.json` with `passes: false`
2. Create feature branch: `git checkout -b feat/task-name`
3. Implement feature
4. Run linting and tests
5. Update `prd.json` and `progress.txt`
6. Create PR

## License

MIT License - see LICENSE file

## Support

For issues or questions:
- GitHub Issues: https://github.com/doogie-bigmack/application-security-policy-miner/issues
- Email: support@example.com

## Acknowledgments

- Built with Claude Sonnet 4.5
- Uses Claude Agent SDK for policy translation
- Tree-sitter for multi-language code parsing
- pgvector for semantic similarity search
