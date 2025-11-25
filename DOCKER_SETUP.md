# 🐳 Docker Setup Guide

Run the entire AI Coding Mentor stack with one command!

## Prerequisites

- Docker Desktop installed ([Download here](https://www.docker.com/products/docker-desktop))
- Docker Compose (included with Docker Desktop)
- Ollama running on host machine (optional, can use MOCK_LLM=true)

## Quick Start

### 1. Create Environment File
```bash
cp .env.example .env
```

Edit `.env` and set your passwords:
```bash
POSTGRES_PASSWORD=your_secure_password
DATABASE_URL=postgresql://postgres:your_secure_password@postgres:5432/agentic_db
```

### 2. Start Everything
```bash
docker-compose up -d
```

This starts:
- ✅ PostgreSQL database
- ✅ Redis (for rate limiting)
- ✅ FastAPI backend

### 3. Initialize Database

First time only:
```bash
# Enter backend container
docker exec -it ai-mentor-backend bash

# Run database initialization
python init_db.py

# Exit container
exit
```

### 4. Access the Application

- **API:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs
- **Health Check:** http://localhost:8000/health

## Common Commands

### View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f postgres
docker-compose logs -f redis
```

### Stop Everything
```bash
docker-compose down
```

### Stop and Remove Data
```bash
docker-compose down -v
```

### Rebuild After Code Changes
```bash
docker-compose up -d --build
```

### Check Service Status
```bash
docker-compose ps
```

## Troubleshooting

### Backend can't connect to Ollama

**Solution 1:** Make sure Ollama is running on your host:
```bash
ollama serve
```

**Solution 2:** Use mock mode:
```bash
# In .env file
MOCK_LLM=true
```

### Database connection errors

Check if PostgreSQL is ready:
```bash
docker-compose logs postgres
```

Wait for: `database system is ready to accept connections`

### Port already in use

Change ports in `.env`:
```bash
BACKEND_PORT=8001
POSTGRES_PORT=5433
REDIS_PORT=6380
```

Then restart:
```bash
docker-compose down
docker-compose up -d
```

## Production Deployment

For production, update these settings:
```bash
# Use strong passwords
POSTGRES_PASSWORD=<generate-strong-password>

# Set production environment
ENVIRONMENT=production

# Configure Redis with password
REDIS_URL=redis://:your_redis_password@redis:6379/0
```

## Architecture
```
┌─────────────────┐
│   Docker Host   │
│                 │
│  ┌───────────┐  │
│  │  Ollama   │  │ (runs on host)
│  └─────┬─────┘  │
│        │        │
└────────┼────────┘
         │
    ┌────▼─────────────────────────┐
    │     Docker Network           │
    │                              │
    │  ┌──────────┐  ┌──────────┐  │
    │  │PostgreSQL│  │  Redis   │  │
    │  └────┬─────┘  └────┬─────┘  │
    │       │             │        │
    │  ┌────▼─────────────▼─────┐  │
    │  │   FastAPI Backend      │  │
    │  │   Port: 8000           │  │
    │  └────────────────────────┘  │
    └──────────────────────────────┘
```

## Next Steps

1. Set up CI/CD with GitHub Actions
2. Deploy to AWS ECS/Fargate
3. Add NGINX reverse proxy
4. Configure SSL certificates
5. Set up monitoring (Prometheus + Grafana)

---

**Need help?** Check the main README.md or open an issue on GitHub.