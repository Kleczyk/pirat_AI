# Cloudflare Deployment Guide (No Domain Required)

Guide for deploying Outwit the AI Pirate Game using Cloudflare or other hosting platforms - **without a custom domain, using public IP or free URLs**.

## Option 1: Cloudflare Tunnel with Random URL (Quickest, Free)

Cloudflare Tunnel can provide a temporary public URL without requiring a domain.

### Prerequisites

- A server/VPS with Docker installed (or local machine)
- A Cloudflare account (free)

### Step 1: Install Cloudflare Tunnel (cloudflared)

```bash
# Download and install cloudflared
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o cloudflared
chmod +x cloudflared
sudo mv cloudflared /usr/local/bin/
```

### Step 2: Deploy Application Locally

```bash
# Start Docker containers
docker compose -f docker-compose.prod.yml up -d

# Verify services are running
curl http://localhost:8000/health
curl http://localhost:8501
```

### Step 3: Create Quick Tunnel (No Domain Required)

```bash
# Frontend (Streamlit) - creates random *.trycloudflare.com URL
cloudflared tunnel --url http://localhost:8501

# This will output something like:
# +--------------------------------------------------------------------------------------------+
# |  Your quick Tunnel has been created! Visit it at (it may take some time to be reachable): |
# |  https://random-words-1234.trycloudflare.com                                               |
# +--------------------------------------------------------------------------------------------+
```

Note: This creates a **temporary tunnel** that expires when you close the terminal.

### Step 4: Create Persistent Tunnel (Recommended)

For a more stable solution, create a named tunnel:

```bash
# Login to Cloudflare (opens browser)
cloudflared tunnel login

# Create a named tunnel
cloudflared tunnel create pirat-ai

# Run tunnel without domain (Cloudflare will assign a random hostname)
cloudflared tunnel --url http://localhost:8501 run pirat-ai
```

### Step 5: Run as System Service (Optional)

To keep the tunnel running even after logout:

```bash
sudo cloudflared service install
sudo cloudflared service start
```

## Option 2: Railway (Easiest, Free Tier Available)

Railway provides automatic HTTPS and public URLs without requiring a domain.

### Step 1: Deploy to Railway

1. Go to [railway.app](https://railway.app)
2. Create a new project
3. Connect your GitHub repository
4. Add two services:
   - Backend: Use `Dockerfile.backend`
   - Frontend: Use `Dockerfile.frontend`

### Step 2: Configure Environment Variables

In Railway dashboard, add these environment variables for **Backend**:

```env
KIE_AI_API_KEY=your_key
OPENROUTER_API_KEY=your_key
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
ELEVENLABS_MODEL=elevenlabs/text-to-speech-turbo-2-5
ELEVENLABS_VOICE=Rachel
ELEVENLABS_LANGUAGE_CODE=pl
HOST=0.0.0.0
PORT=8000
DEBUG=False
```

For **Frontend**, add:

```env
API_BASE_URL=<railway_backend_url>
```

### Step 3: Get Public URLs

Railway automatically provides public URLs:
- Backend: `https://pirat-ai-backend-production.up.railway.app`
- Frontend: `https://pirat-ai-frontend-production.up.railway.app`

### Step 4: Update Frontend API URL

1. Copy the backend URL from Railway
2. In Frontend service settings, set:
   ```
   API_BASE_URL=https://pirat-ai-backend-production.up.railway.app
   ```
3. Redeploy frontend

### Step 5: Access Your Application

- Visit the frontend URL from Railway dashboard
- The app will use the Railway backend URL automatically

## Option 3: Render (Free Tier Available)

Similar to Railway, but using Render.com.

### Step 1: Deploy to Render

1. Go to [render.com](https://render.com)
2. Create a new "Web Service"
3. Connect your GitHub repository
4. Configure:
   - **Name**: `pirat-ai-backend`
   - **Build Command**: (leave empty, Docker handles it)
   - **Start Command**: (handled by Dockerfile)
   - **Dockerfile Path**: `Dockerfile.backend`
   - **Plan**: Free

### Step 2: Repeat for Frontend

Create another service:
- **Name**: `pirat-ai-frontend`
- **Dockerfile Path**: `Dockerfile.frontend`
- **Environment Variables**:
  ```
  API_BASE_URL=https://pirat-ai-backend.onrender.com
  ```

### Step 3: Configure Environment Variables

For Backend service:

```env
KIE_AI_API_KEY=your_key
OPENROUTER_API_KEY=your_key
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
ELEVENLABS_MODEL=elevenlabs/text-to-speech-turbo-2-5
ELEVENLABS_VOICE=Rachel
ELEVENLABS_LANGUAGE_CODE=pl
HOST=0.0.0.0
PORT=8000
DEBUG=False
```

### Step 4: Get Public URLs

Render provides:
- Backend: `https://pirat-ai-backend.onrender.com`
- Frontend: `https://pirat-ai-frontend.onrender.com`

## Option 4: Fly.io (Free Tier Available)

Fly.io provides automatic HTTPS and public IPs.

### Step 1: Install Fly CLI

```bash
curl -L https://fly.io/install.sh | sh
```

### Step 2: Login and Initialize

```bash
fly auth login
fly launch
```

Follow the prompts. Fly.io will:
- Detect your Dockerfile
- Assign a random app name (or you can specify)
- Create a public URL like `pirat-ai-1234.fly.dev`

### Step 3: Deploy

```bash
fly deploy
```

### Step 4: Get Public URL

```bash
fly info
# Shows your app URL: https://pirat-ai-1234.fly.dev
```

## Option 5: VPS with Public IP (DigitalOcean, AWS, etc.)

If you have a VPS with a public IP, you can expose it directly or use Cloudflare Tunnel.

### Direct Access (Simple but less secure)

1. **Update docker-compose.prod.yml**:
   ```yaml
   ports:
     - "8000:8000"  # Backend - accessible on public IP
     - "8501:8501"  # Frontend - accessible on public IP
   ```

2. **Deploy**:
   ```bash
   docker compose -f docker-compose.prod.yml up -d
   ```

3. **Access via Public IP**:
   - Frontend: `http://YOUR_PUBLIC_IP:8501`
   - Backend: `http://YOUR_PUBLIC_IP:8000`

4. **Security Note**: 
   - Consider using a firewall (UFW, iptables)
   - Use HTTPS with nginx/caddy as reverse proxy
   - Or use Cloudflare Tunnel for automatic HTTPS

### With Cloudflare Tunnel (Recommended for VPS)

Use Option 1 (Cloudflare Tunnel) with your VPS's public IP or localhost.

## Quick Start Script (Cloudflare Tunnel)

Use the provided script for quick setup:

```bash
chmod +x DEPLOY_CLOUDFLARE.sh
./DEPLOY_CLOUDFLARE.sh --no-domain
```

## Production Checklist

- [ ] Set `DEBUG=False` in environment variables
- [ ] Use strong API keys
- [ ] Configure CORS properly (see `backend/main.prod.py.example`)
- [ ] Set up monitoring and alerts
- [ ] Configure backup strategy
- [ ] Test audio recording functionality
- [ ] Test API endpoints
- [ ] Review security settings
- [ ] Document your public URLs

## Environment Variables for Production

Create `.env.production`:

```env
# API Keys
KIE_AI_API_KEY=your_production_key
OPENROUTER_API_KEY=your_production_key
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1

# ElevenLabs
ELEVENLABS_MODEL=elevenlabs/text-to-speech-turbo-2-5
ELEVENLABS_VOICE=Rachel
ELEVENLABS_LANGUAGE_CODE=pl

# Server
HOST=0.0.0.0
PORT=8000
DEBUG=False

# Game Configuration
WIN_PHRASE=Oto mój skarb, weź go
PRIMARY_LANGUAGE=pl
```

## Security Recommendations

1. **Update CORS in production**:
   ```python
   # In backend/main.py - update for your actual URLs
   app.add_middleware(
       CORSMiddleware,
       allow_origins=[
           "https://pirat-ai-frontend-production.up.railway.app",
           "https://pirat-ai-frontend.onrender.com",
           "https://random-words-1234.trycloudflare.com",
           # Add your actual frontend URLs
       ],
       allow_credentials=True,
       allow_methods=["GET", "POST", "OPTIONS"],
       allow_headers=["*"],
   )
   ```

2. **For Cloudflare Tunnel**: No additional security needed (Cloudflare handles it)

3. **For Direct IP Access**: 
   - Use firewall rules
   - Consider using nginx/caddy for HTTPS
   - Or use Cloudflare Tunnel instead

## Troubleshooting

### Cloudflare Tunnel not connecting
- Check if services are running: `docker compose ps`
- Verify local access: `curl http://localhost:8501`
- Check tunnel logs: `cloudflared tunnel --url http://localhost:8501`

### Railway/Render timeout
- Free tiers may have cold starts (15-30 seconds)
- Check service logs in dashboard
- Verify environment variables

### Audio recording not working
- Check browser console for errors
- Verify microphone permissions
- Check HTTPS (required for microphone API)
- Test with direct service URLs

### API timeouts
- Increase timeout in frontend API calls
- Check backend health endpoint
- Review backend logs

## Monitoring

Set up monitoring with:
- Railway/Render built-in metrics
- Application logs (check dashboard)
- Health check endpoints (`/health`)
- Cloudflare Tunnel metrics (if using)

## Support

- **Cloudflare Tunnel**: https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/
- **Railway**: https://docs.railway.app/
- **Render**: https://render.com/docs
- **Fly.io**: https://fly.io/docs/

## Recommended Approach

For **no domain / public IP only** scenarios:

1. **Quick Testing**: Use Cloudflare Tunnel quick mode (`cloudflared tunnel --url`)
2. **Production (Free)**: Use Railway or Render (automatic HTTPS, free tier)
3. **Production (VPS)**: Use VPS with Cloudflare Tunnel (automatic HTTPS, no domain needed)
4. **Production (Paid)**: Use Fly.io for better performance
