# Docker Setup Guide

This project uses **UV** (the fast Python package manager) and **Docker Compose** for containerized deployment.

## Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+
- (Optional) Make utility for convenience commands

## Quick Start

1. **Create `.env` file (REQUIRED before build):**

```bash
cp .env.example .env
```

2. **Edit `.env` and add your API keys:**

```env
KIE_AI_API_KEY=your_actual_key_here
OPENROUTER_API_KEY=your_actual_key_here
```

**Important:** The `.env` file is copied into the Docker image during build. Make sure it exists and contains your keys before running `docker compose build`.

3. **Start all services:**

```bash
docker compose up --build
```

Or using Make:

```bash
make rebuild
```

4. **Access the application:**

- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Frontend UI**: http://localhost:8501

## Docker Compose Commands

### Start services
```bash
docker compose up -d          # Start in background
docker compose up              # Start with logs
docker compose up --build      # Rebuild and start
```

### Stop services
```bash
docker compose down            # Stop and remove containers
docker compose down -v         # Stop and remove volumes too
```

### View logs
```bash
docker compose logs -f         # All services
docker compose logs -f backend # Backend only
docker compose logs -f frontend # Frontend only
```

### Restart services
```bash
docker compose restart         # Restart all
docker compose restart backend # Restart specific service
```

## Make Commands (Optional)

If you have `make` installed, you can use:

```bash
make build      # Build images
make up         # Start services
make down       # Stop services
make logs       # View logs
make restart    # Restart services
make clean      # Remove containers and volumes
make rebuild    # Rebuild and restart
make test       # Test backend health
```

## Architecture

```
┌─────────────────┐
│   Frontend      │  Streamlit (Port 8501)
│   (Container)   │
└────────┬────────┘
         │ HTTP
         ▼
┌─────────────────┐
│   Backend       │  FastAPI (Port 8000)
│   (Container)   │
└─────────────────┘
         │
         ├──► OpenRouter API (LLM)
         └──► Kie.ai API (ElevenLabs TTS)
```

## Environment Variables

The `.env` file is **copied into the Docker image** during build (not passed as environment variables). The application reads from the `.env` file using `python-dotenv`.

**Important:** You must create `.env` file before building the images. The file is copied into the container at build time.

Key variables in `.env`:
- `KIE_AI_API_KEY` - Required for TTS
- `OPENROUTER_API_KEY` - Required for LLM
- `DEBUG` - Set to `True` for development

**Note:** If you change `.env` after building, you need to rebuild the images:
```bash
docker compose build --no-cache
docker compose up
```

## Troubleshooting

### Backend won't start
1. Check logs: `docker compose logs backend`
2. Verify API keys in `.env` file
3. Check if port 8000 is available: `lsof -i :8000`

### Frontend can't connect to backend
1. Ensure backend is healthy: `curl http://localhost:8000/health`
2. Check network: `docker network ls`
3. Verify `API_BASE_URL` in frontend container

### Build fails
1. Clear Docker cache: `docker system prune -a`
2. Rebuild without cache: `docker compose build --no-cache`
3. Check Dockerfile syntax

### Port already in use
Change ports in `docker compose.yml`:
```yaml
ports:
  - "8001:8000"  # Backend on 8001
  - "8502:8501"  # Frontend on 8502
```

## Development Mode

For development with hot-reload, the backend code is mounted as a volume:

```yaml
volumes:
  - ./backend:/app/backend
```

Changes to backend code will be reflected after container restart or if using a file watcher.

## Production Considerations

For production deployment:

1. Remove volume mounts (code should be in image)
2. Set `DEBUG=False` in `.env`
3. Use proper secrets management (not `.env` files)
4. Add reverse proxy (nginx/traefik)
5. Enable HTTPS
6. Set up proper logging and monitoring
7. Use Docker secrets or external secret management

## UV Package Manager

This project uses **UV** for fast Python package management. The Dockerfiles use the official UV base image:

```dockerfile
FROM ghcr.io/astral-sh/uv:python3.11-bookworm
```

UV provides:
- ⚡ Fast dependency resolution
- 🔒 Reliable dependency locking
- 📦 Efficient package installation
- 🐍 Python version management

Dependencies are defined in `pyproject.toml` and installed directly in the Dockerfiles for optimal caching.

