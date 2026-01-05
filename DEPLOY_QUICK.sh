#!/bin/bash
# Quick deployment script for no-domain/public IP scenarios

set -e

echo "🚀 Quick Deployment - No Domain Required"
echo ""
echo "Choose deployment method:"
echo "1) Cloudflare Tunnel (Quick Mode - Random URL)"
echo "2) Railway (Free tier, automatic HTTPS)"
echo "3) Render (Free tier, automatic HTTPS)"
echo "4) VPS with Public IP (Direct access)"
echo ""
read -p "Enter choice (1-4): " CHOICE

case $CHOICE in
    1)
        echo ""
        echo "🌐 Deploying with Cloudflare Tunnel (Quick Mode)"
        echo ""
        
        # Check if cloudflared is installed
        if ! command -v cloudflared &> /dev/null; then
            echo "📥 Installing cloudflared..."
            curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o /tmp/cloudflared
            chmod +x /tmp/cloudflared
            sudo mv /tmp/cloudflared /usr/local/bin/cloudflared
        fi
        
        # Start Docker containers
        echo "🐳 Starting Docker containers..."
        docker compose -f docker-compose.prod.yml up -d
        
        echo "⏳ Waiting for services..."
        sleep 10
        
        # Check health
        if curl -f http://localhost:8000/health > /dev/null 2>&1; then
            echo "✅ Backend is healthy"
        else
            echo "❌ Backend health check failed"
            exit 1
        fi
        
        echo ""
        echo "🌐 Starting Cloudflare Tunnel..."
        echo "   Your public URL will appear below:"
        echo "   Press Ctrl+C to stop"
        echo ""
        
        cloudflared tunnel --url http://localhost:8501
        ;;
        
    2)
        echo ""
        echo "🚂 Deploying to Railway"
        echo ""
        echo "Steps:"
        echo "1. Go to https://railway.app"
        echo "2. Create new project"
        echo "3. Connect GitHub repository"
        echo "4. Add service for backend (Dockerfile.backend)"
        echo "5. Add service for frontend (Dockerfile.frontend)"
        echo "6. Set environment variables (see CLOUDFLARE_DEPLOYMENT.md)"
        echo "7. Copy backend URL to frontend API_BASE_URL"
        echo ""
        echo "Railway will provide public URLs automatically!"
        echo ""
        echo "📚 See CLOUDFLARE_DEPLOYMENT.md for detailed instructions"
        ;;
        
    3)
        echo ""
        echo "🎨 Deploying to Render"
        echo ""
        echo "Steps:"
        echo "1. Go to https://render.com"
        echo "2. Create new Web Service"
        echo "3. Connect GitHub repository"
        echo "4. Backend: Use Dockerfile.backend"
        echo "5. Frontend: Use Dockerfile.frontend"
        echo "6. Set environment variables (see CLOUDFLARE_DEPLOYMENT.md)"
        echo "7. Copy backend URL to frontend API_BASE_URL"
        echo ""
        echo "Render will provide public URLs automatically!"
        echo ""
        echo "📚 See CLOUDFLARE_DEPLOYMENT.md for detailed instructions"
        ;;
        
    4)
        echo ""
        echo "🖥️  Deploying to VPS with Public IP"
        echo ""
        
        # Update docker-compose for direct access
        read -p "Enter your VPS public IP: " PUBLIC_IP
        
        echo "🐳 Starting Docker containers (accessible on $PUBLIC_IP:8501 and :8000)..."
        docker compose -f docker-compose.prod.yml up -d --build
        
        echo "⏳ Waiting for services..."
        sleep 10
        
        # Check health
        if curl -f http://localhost:8000/health > /dev/null 2>&1; then
            echo "✅ Services are running"
        else
            echo "❌ Services failed to start"
            exit 1
        fi
        
        echo ""
        echo "✅ Deployment complete!"
        echo "🌐 Frontend: http://$PUBLIC_IP:8501"
        echo "🔧 Backend: http://$PUBLIC_IP:8000"
        echo "📚 API Docs: http://$PUBLIC_IP:8000/docs"
        echo ""
        echo "⚠️  Security Note:"
        echo "   - This is HTTP only (not HTTPS)"
        echo "   - Consider using firewall rules"
        echo "   - For HTTPS, use Cloudflare Tunnel or nginx/caddy"
        echo ""
        echo "💡 Tip: Use Cloudflare Tunnel for automatic HTTPS:"
        echo "   ./DEPLOY_CLOUDFLARE.sh --no-domain"
        ;;
        
    *)
        echo "❌ Invalid choice"
        exit 1
        ;;
esac



