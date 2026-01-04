# Docker Compose Quick Start Guide

## 🚀 Quick Start (3 Steps)

### 1. Setup Environment
```bash
# Create .env file from template
cp .env.example .env

# Edit .env and add your API keys:
# - KIE_AI_API_KEY (from https://kie.ai)
# - OPENROUTER_API_KEY (from https://openrouter.ai)
```

### 2. Start Services
```bash
# Build and start all services
docker compose up --build

# Or in background:
docker compose up --build -d
```

### 3. Access Application
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Frontend UI**: http://localhost:8501

## 🧪 Testing

### Automated Test
```bash
# Run comprehensive test script
./test-docker.sh
```

### Manual Tests
```bash
# Health check
curl http://localhost:8000/health

# Start a game
curl -X POST http://localhost:8000/api/game/start \
  -H "Content-Type: application/json" \
  -d '{"difficulty": "easy", "pirate_name": "Kapitan"}'

# View logs
docker compose logs -f
```

## 📋 Common Commands

```bash
# Start services
docker compose up -d

# Stop services
docker compose down

# View logs
docker compose logs -f
docker compose logs -f backend
docker compose logs -f frontend

# Restart services
docker compose restart

# Rebuild and restart
docker compose up --build -d

# Check service status
docker compose ps
```

## 🔧 Troubleshooting

### Backend not starting?
```bash
# Check logs
docker compose logs backend

# Verify API keys
cat .env | grep API_KEY

# Check port availability
lsof -i :8000
```

### Frontend can't connect?
```bash
# Verify backend is healthy
curl http://localhost:8000/health

# Check network
docker network inspect pirat_ai_pirat-network
```

### Port conflicts?
Change ports in `docker compose.yml`:
```yaml
ports:
  - "8001:8000"  # Backend
  - "8502:8501"  # Frontend
```

## 📚 More Information

- **Full Recommendations**: See [DOCKER_RECOMMENDATIONS.md](DOCKER_RECOMMENDATIONS.md)
- **Docker Guide**: See [DOCKER.md](DOCKER.md)
- **Setup Guide**: See [SETUP.md](SETUP.md)





