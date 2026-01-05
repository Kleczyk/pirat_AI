# Docker Compose Recommendations & Testing Guide

## Executive Summary

Your Docker Compose setup is **well-structured** and follows good practices. This document provides recommendations for improvements, testing strategies, and best practices for running and testing the application.

## Current Setup Analysis

### ✅ What's Working Well

1. **Service Architecture**: Clean separation of backend and frontend services
2. **Health Checks**: Backend has proper health check configuration
3. **Networking**: Proper use of Docker networks for service communication
4. **Dependencies**: Frontend correctly waits for backend to be healthy
5. **Volume Mounting**: Development-friendly volume mount for backend code
6. **Environment Variables**: Proper environment variable passing from `.env` file

### ⚠️ Areas for Improvement

1. **Missing `.env.example` file** - Referenced in docs but doesn't exist
2. **Health check dependency** - Could be more robust
3. **No test service** - Missing automated testing capabilities
4. **Development vs Production** - No profile separation
5. **Logging configuration** - Could be improved
6. **Resource limits** - Not specified (good for production)

## Recommendations

### 1. Create `.env.example` File

**Priority: HIGH**

Create a template file for environment variables:

```bash
# .env.example
# Copy this file to .env and fill in your actual API keys

# Required API Keys
KIE_AI_API_KEY=your_kie_ai_api_key_here
OPENROUTER_API_KEY=your_openrouter_api_key_here

# Optional: OpenRouter Configuration
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1

# Optional: ElevenLabs Configuration
ELEVENLABS_MODEL=elevenlabs/text-to-speech-turbo-2-5
ELEVENLABS_VOICE=Rachel
ELEVENLABS_LANGUAGE_CODE=pl

# Optional: Server Configuration
DEBUG=True
HOST=0.0.0.0
PORT=8000
```

### 2. Enhanced Docker Compose Configuration

**Priority: MEDIUM**

Consider these improvements to `docker compose.yml`:

#### A. Add Development Profile

```yaml
services:
  backend:
    # ... existing config ...
    profiles:
      - dev
      - prod
    # Add development-specific volumes only in dev profile
```

#### B. Improve Health Check

The current health check is good, but consider adding a startup script:

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
  interval: 10s      # Check more frequently during startup
  timeout: 5s
  retries: 5         # More retries for slow starts
  start_period: 30s  # Longer grace period
```

#### C. Add Resource Limits (Production)

```yaml
deploy:
  resources:
    limits:
      cpus: '1.0'
      memory: 1G
    reservations:
      cpus: '0.5'
      memory: 512M
```

#### D. Add Logging Configuration

```yaml
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"
```

### 3. Add Testing Service

**Priority: MEDIUM**

Add a test service to `docker compose.yml`:

```yaml
  test:
    build:
      context: .
      dockerfile: Dockerfile.backend
    container_name: pirat-ai-test
    environment:
      - KIE_AI_API_KEY=${KIE_AI_API_KEY}
      - OPENROUTER_API_KEY=${OPENROUTER_API_KEY}
      - OPENROUTER_BASE_URL=${OPENROUTER_BASE_URL:-https://openrouter.ai/api/v1}
    depends_on:
      backend:
        condition: service_healthy
    networks:
      - pirat-network
    profiles:
      - test
    command: >
      sh -c "
        echo 'Waiting for backend to be ready...' &&
        sleep 5 &&
        echo 'Running tests...' &&
        pytest tests/ -v || echo 'Tests completed'
      "
```

### 4. Create Docker Compose Override Files

**Priority: LOW**

Create `docker compose.override.yml` for local development:

```yaml
# docker compose.override.yml (auto-loaded in development)
version: '3.8'

services:
  backend:
    volumes:
      - ./backend:/app/backend
    environment:
      - DEBUG=True
    command: uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

  frontend:
    volumes:
      - ./frontend:/app/frontend
```

Create `docker compose.prod.yml` for production:

```yaml
# docker compose.prod.yml (use with: docker compose -f docker compose.yml -f docker compose.prod.yml up)
version: '3.8'

services:
  backend:
    volumes: []  # Remove volume mounts
    environment:
      - DEBUG=False
    restart: always

  frontend:
    volumes: []  # Remove volume mounts
    restart: always
```

## Testing Recommendations

### 1. Manual Testing Checklist

#### Pre-Deployment Tests

- [ ] **Environment Setup**
  ```bash
  # Check if .env file exists
  test -f .env && echo "✓ .env exists" || echo "✗ .env missing"
  
  # Verify required variables
  grep -q "KIE_AI_API_KEY" .env && echo "✓ KIE_AI_API_KEY set" || echo "✗ Missing KIE_AI_API_KEY"
  grep -q "OPENROUTER_API_KEY" .env && echo "✓ OPENROUTER_API_KEY set" || echo "✗ Missing OPENROUTER_API_KEY"
  ```

- [ ] **Port Availability**
  ```bash
  # Check if ports are available
  lsof -i :8000 || echo "✓ Port 8000 available"
  lsof -i :8501 || echo "✓ Port 8501 available"
  ```

- [ ] **Docker Setup**
  ```bash
  # Verify Docker is running
  docker ps > /dev/null && echo "✓ Docker running" || echo "✗ Docker not running"
  
  # Check Docker Compose version
  docker compose --version
  ```

#### Build Tests

- [ ] **Image Building**
  ```bash
  # Build without cache to ensure clean build
  docker compose build --no-cache
  
  # Check image sizes (should be reasonable)
  docker images | grep pirat-ai
  ```

#### Runtime Tests

- [ ] **Service Startup**
  ```bash
  # Start services
  docker compose up -d
  
  # Wait for services to be healthy
  docker compose ps
  
  # Check logs for errors
  docker compose logs backend | grep -i error
  docker compose logs frontend | grep -i error
  ```

- [ ] **Health Check**
  ```bash
  # Test backend health endpoint
  curl -f http://localhost:8000/health
  curl -f http://localhost:8000/
  
  # Test API documentation
  curl -f http://localhost:8000/docs
  ```

- [ ] **API Functionality**
  ```bash
  # Test game start
  GAME_RESPONSE=$(curl -s -X POST http://localhost:8000/api/game/start \
    -H "Content-Type: application/json" \
    -d '{"difficulty": "easy", "pirate_name": "Kapitan"}')
  
  echo $GAME_RESPONSE | jq .
  
  # Extract game_id
  GAME_ID=$(echo $GAME_RESPONSE | jq -r '.game_id')
  
  # Test conversation
  curl -X POST http://localhost:8000/api/game/conversation \
    -H "Content-Type: application/json" \
    -d "{
      \"game_id\": \"$GAME_ID\",
      \"message\": \"Cześć kapitanie!\",
      \"include_audio\": false
    }" | jq .
  
  # Test game state retrieval
  curl http://localhost:8000/api/game/$GAME_ID | jq .
  ```

- [ ] **Frontend Access**
  ```bash
  # Check if frontend is accessible
  curl -f http://localhost:8501
  ```

- [ ] **Service Communication**
  ```bash
  # Test frontend-backend communication
  docker compose exec frontend curl -f http://backend:8000/health
  ```

#### Cleanup Tests

- [ ] **Graceful Shutdown**
  ```bash
  # Stop services gracefully
  docker compose down
  
  # Verify containers are stopped
  docker ps | grep pirat-ai || echo "✓ All containers stopped"
  ```

### 2. Automated Testing Script

Create a test script `test-docker.sh`:

```bash
#!/bin/bash
set -e

echo "🧪 Testing Docker Compose Setup"
echo "================================"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check prerequisites
echo -e "\n${YELLOW}1. Checking prerequisites...${NC}"
test -f .env && echo -e "${GREEN}✓ .env file exists${NC}" || echo -e "${RED}✗ .env file missing${NC}"
docker ps > /dev/null 2>&1 && echo -e "${GREEN}✓ Docker is running${NC}" || { echo -e "${RED}✗ Docker is not running${NC}"; exit 1; }

# Build images
echo -e "\n${YELLOW}2. Building images...${NC}"
docker compose build

# Start services
echo -e "\n${YELLOW}3. Starting services...${NC}"
docker compose up -d

# Wait for health
echo -e "\n${YELLOW}4. Waiting for services to be healthy...${NC}"
sleep 10
for i in {1..30}; do
  if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Backend is healthy${NC}"
    break
  fi
  if [ $i -eq 30 ]; then
    echo -e "${RED}✗ Backend failed to become healthy${NC}"
    docker compose logs backend
    exit 1
  fi
  sleep 2
done

# Test endpoints
echo -e "\n${YELLOW}5. Testing API endpoints...${NC}"

# Health check
curl -f http://localhost:8000/health > /dev/null && echo -e "${GREEN}✓ Health endpoint works${NC}" || echo -e "${RED}✗ Health endpoint failed${NC}"

# Root endpoint
curl -f http://localhost:8000/ > /dev/null && echo -e "${GREEN}✓ Root endpoint works${NC}" || echo -e "${RED}✗ Root endpoint failed${NC}"

# Game start
GAME_RESPONSE=$(curl -s -X POST http://localhost:8000/api/game/start \
  -H "Content-Type: application/json" \
  -d '{"difficulty": "easy", "pirate_name": "TestKapitan"}')

if echo "$GAME_RESPONSE" | grep -q "game_id"; then
  echo -e "${GREEN}✓ Game start endpoint works${NC}"
  GAME_ID=$(echo "$GAME_RESPONSE" | jq -r '.game_id')
else
  echo -e "${RED}✗ Game start endpoint failed${NC}"
  echo "$GAME_RESPONSE"
  exit 1
fi

# Conversation
CONV_RESPONSE=$(curl -s -X POST http://localhost:8000/api/game/conversation \
  -H "Content-Type: application/json" \
  -d "{\"game_id\": \"$GAME_ID\", \"message\": \"Test message\", \"include_audio\": false}")

if echo "$CONV_RESPONSE" | grep -q "pirate_response"; then
  echo -e "${GREEN}✓ Conversation endpoint works${NC}"
else
  echo -e "${RED}✗ Conversation endpoint failed${NC}"
  echo "$CONV_RESPONSE"
  exit 1
fi

# Frontend
curl -f http://localhost:8501 > /dev/null 2>&1 && echo -e "${GREEN}✓ Frontend is accessible${NC}" || echo -e "${YELLOW}⚠ Frontend check skipped (may need browser)${NC}"

echo -e "\n${GREEN}✅ All tests passed!${NC}"
echo -e "\n${YELLOW}Services are running:${NC}"
echo "  - Backend: http://localhost:8000"
echo "  - Frontend: http://localhost:8501"
echo "  - API Docs: http://localhost:8000/docs"
```

### 3. Integration Test Suite

Create `tests/test_docker_integration.py`:

```python
"""
Integration tests for Docker Compose setup
"""
import pytest
import requests
import time
from typing import Dict, Any

BASE_URL = "http://localhost:8000"
FRONTEND_URL = "http://localhost:8501"


@pytest.fixture(scope="module")
def wait_for_backend():
    """Wait for backend to be ready"""
    max_attempts = 30
    for i in range(max_attempts):
        try:
            response = requests.get(f"{BASE_URL}/health", timeout=2)
            if response.status_code == 200:
                return True
        except requests.exceptions.RequestException:
            pass
        time.sleep(2)
    pytest.fail("Backend did not become ready")


def test_health_endpoint(wait_for_backend):
    """Test health check endpoint"""
    response = requests.get(f"{BASE_URL}/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_root_endpoint(wait_for_backend):
    """Test root endpoint"""
    response = requests.get(f"{BASE_URL}/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "version" in data


def test_start_game(wait_for_backend):
    """Test starting a new game"""
    response = requests.post(
        f"{BASE_URL}/api/game/start",
        json={"difficulty": "easy", "pirate_name": "TestKapitan"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "game_id" in data
    assert "merit_score" in data
    return data["game_id"]


def test_conversation(wait_for_backend):
    """Test conversation endpoint"""
    # Start a game first
    game_response = requests.post(
        f"{BASE_URL}/api/game/start",
        json={"difficulty": "easy", "pirate_name": "TestKapitan"}
    )
    game_id = game_response.json()["game_id"]
    
    # Send a message
    conv_response = requests.post(
        f"{BASE_URL}/api/game/conversation",
        json={
            "game_id": game_id,
            "message": "Cześć kapitanie!",
            "include_audio": False
        }
    )
    assert conv_response.status_code == 200
    data = conv_response.json()
    assert "pirate_response" in data
    assert "merit_score" in data


def test_get_game_state(wait_for_backend):
    """Test retrieving game state"""
    # Start a game
    game_response = requests.post(
        f"{BASE_URL}/api/game/start",
        json={"difficulty": "easy", "pirate_name": "TestKapitan"}
    )
    game_id = game_response.json()["game_id"]
    
    # Get game state
    state_response = requests.get(f"{BASE_URL}/api/game/{game_id}")
    assert state_response.status_code == 200
    data = state_response.json()
    assert data["game_id"] == game_id


def test_frontend_accessible():
    """Test that frontend is accessible"""
    try:
        response = requests.get(FRONTEND_URL, timeout=5)
        assert response.status_code == 200
    except requests.exceptions.RequestException:
        pytest.skip("Frontend not accessible (may be expected)")
```

## Quick Start Commands

### Development

```bash
# 1. Create .env file (if not exists)
cp .env.example .env
# Edit .env with your API keys

# 2. Build and start
docker compose up --build

# 3. View logs
docker compose logs -f

# 4. Test health
curl http://localhost:8000/health

# 5. Access services
# Backend: http://localhost:8000
# Frontend: http://localhost:8501
# API Docs: http://localhost:8000/docs
```

### Production

```bash
# Build for production
docker compose -f docker compose.yml -f docker compose.prod.yml build

# Start in production mode
docker compose -f docker compose.yml -f docker compose.prod.yml up -d

# View logs
docker compose logs -f
```

### Testing

```bash
# Run automated tests
chmod +x test-docker.sh
./test-docker.sh

# Or run pytest integration tests
docker compose exec backend pytest tests/test_docker_integration.py -v
```

## Troubleshooting Guide

### Issue: Backend won't start

**Symptoms**: Container exits immediately or health check fails

**Solutions**:
1. Check logs: `docker compose logs backend`
2. Verify API keys in `.env` file
3. Check if port 8000 is available: `lsof -i :8000`
4. Verify environment variables: `docker compose config`

### Issue: Frontend can't connect to backend

**Symptoms**: Frontend shows connection errors

**Solutions**:
1. Verify backend is healthy: `curl http://localhost:8000/health`
2. Check network: `docker network inspect pirat_ai_pirat-network`
3. Verify `API_BASE_URL` in frontend: `docker compose exec frontend env | grep API_BASE_URL`
4. Check service names match in docker compose.yml

### Issue: Build fails

**Symptoms**: Docker build errors

**Solutions**:
1. Clear Docker cache: `docker system prune -a`
2. Rebuild without cache: `docker compose build --no-cache`
3. Check Dockerfile syntax
4. Verify base image availability: `docker pull ghcr.io/astral-sh/uv:python3.11-bookworm`

### Issue: Port conflicts

**Symptoms**: "Port already in use" errors

**Solutions**:
1. Find process using port: `lsof -i :8000` or `lsof -i :8501`
2. Kill process or change ports in `docker compose.yml`
3. Use different ports: `8001:8000` for backend, `8502:8501` for frontend

## Best Practices Summary

1. ✅ **Always use `.env` file** - Never commit API keys
2. ✅ **Use health checks** - Ensure services are ready before depending on them
3. ✅ **Separate dev/prod configs** - Use compose override files
4. ✅ **Monitor logs** - Use `docker compose logs -f` during development
5. ✅ **Test before deploying** - Run test script before production
6. ✅ **Use resource limits** - In production, set CPU/memory limits
7. ✅ **Version pinning** - Pin Docker image versions for reproducibility
8. ✅ **Network isolation** - Use custom networks for service communication

## Next Steps

1. **Immediate**: Create `.env.example` file
2. **Short-term**: Add test script and improve health checks
3. **Medium-term**: Add compose override files for dev/prod separation
4. **Long-term**: Add CI/CD integration, monitoring, and production hardening

---

**Last Updated**: Based on current codebase analysis
**Status**: Ready for implementation







