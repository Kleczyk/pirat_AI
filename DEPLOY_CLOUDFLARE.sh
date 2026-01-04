#!/bin/bash
# Quick deployment script for Cloudflare Tunnel (with or without domain)

set -e

echo "🚀 Deploying Outwit the AI Pirate Game with Cloudflare Tunnel"

# Check for --no-domain flag
NO_DOMAIN=false
if [[ "$1" == "--no-domain" ]] || [[ "$1" == "-n" ]]; then
    NO_DOMAIN=true
    echo "🌐 Mode: No domain (using random Cloudflare URL)"
else
    echo "🌐 Mode: With domain (requires Cloudflare account with domain)"
fi

# Check if cloudflared is installed
if ! command -v cloudflared &> /dev/null; then
    echo "❌ cloudflared is not installed"
    echo "📥 Installing cloudflared..."
    curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o /tmp/cloudflared
    chmod +x /tmp/cloudflared
    sudo mv /tmp/cloudflared /usr/local/bin/cloudflared
    echo "✅ cloudflared installed"
fi

# Build and start Docker containers
echo "🐳 Building and starting Docker containers..."
docker compose -f docker-compose.prod.yml up -d --build

# Wait for services to be healthy
echo "⏳ Waiting for services to start..."
sleep 10

# Check if services are running
if docker compose -f docker-compose.prod.yml ps | grep -q "Up"; then
    echo "✅ Services are running"
    echo "   Backend: http://localhost:8000"
    echo "   Frontend: http://localhost:8501"
else
    echo "❌ Services failed to start"
    docker compose -f docker-compose.prod.yml logs
    exit 1
fi

if [ "$NO_DOMAIN" = true ]; then
    # Quick tunnel mode (no domain required)
    echo ""
    echo "🌐 Starting Cloudflare Tunnel (Quick Mode - No Domain Required)"
    echo "   This will create a temporary public URL"
    echo "   Press Ctrl+C to stop"
    echo ""
    echo "⚠️  Note: The URL will change each time you restart"
    echo ""
    
    # Run quick tunnel for frontend
    cloudflared tunnel --url http://localhost:8501
else
    # Domain mode (requires Cloudflare account)
    echo ""
    echo "🌐 Setting up Cloudflare Tunnel with Domain"
    
    # Check if user is authenticated
    if [ ! -f ~/.cloudflared/cert.pem ]; then
        echo "🔐 Authenticating with Cloudflare..."
        cloudflared tunnel login
    fi
    
    # Create tunnel if it doesn't exist
    TUNNEL_NAME="pirat-ai"
    if ! cloudflared tunnel list 2>/dev/null | grep -q "$TUNNEL_NAME"; then
        echo "🏗️  Creating tunnel: $TUNNEL_NAME"
        cloudflared tunnel create "$TUNNEL_NAME"
    fi
    
    TUNNEL_UUID=$(cloudflared tunnel list 2>/dev/null | grep "$TUNNEL_NAME" | awk '{print $1}' | head -n1)
    
    if [ -z "$TUNNEL_UUID" ]; then
        echo "❌ Failed to get tunnel UUID. Please create tunnel manually:"
        echo "   cloudflared tunnel create pirat-ai"
        exit 1
    fi
    
    echo "✅ Tunnel UUID: $TUNNEL_UUID"
    
    # Ask for domain
    read -p "Enter your domain (e.g., pirat-ai.example.com): " DOMAIN
    read -p "Enter API subdomain (e.g., api.pirat-ai.example.com) or press Enter to skip: " API_DOMAIN
    
    # Create config directory
    mkdir -p ~/.cloudflared
    
    # Create config file
    CONFIG_FILE="$HOME/.cloudflared/config.yml"
    cat > "$CONFIG_FILE" <<EOF
tunnel: $TUNNEL_UUID
credentials-file: $HOME/.cloudflared/$TUNNEL_UUID.json

ingress:
  # Frontend (Streamlit)
  - hostname: $DOMAIN
    service: http://localhost:8501
EOF
    
    if [ -n "$API_DOMAIN" ]; then
        cat >> "$CONFIG_FILE" <<EOF
  
  # Backend API
  - hostname: $API_DOMAIN
    service: http://localhost:8000
EOF
    fi
    
    cat >> "$CONFIG_FILE" <<EOF
  
  # Catch-all rule
  - service: http_status:404
EOF
    
    echo "✅ Configuration file created: $CONFIG_FILE"
    
    # Route DNS
    echo "🌐 Routing DNS..."
    cloudflared tunnel route dns "$TUNNEL_UUID" "$DOMAIN" || echo "⚠️  DNS routing may have failed. Check manually in Cloudflare dashboard."
    if [ -n "$API_DOMAIN" ]; then
        cloudflared tunnel route dns "$TUNNEL_UUID" "$API_DOMAIN" || echo "⚠️  DNS routing may have failed. Check manually in Cloudflare dashboard."
    fi
    
    # Install cloudflared as service
    read -p "Install cloudflared as a systemd service? (y/n): " INSTALL_SERVICE
    if [ "$INSTALL_SERVICE" = "y" ]; then
        sudo cloudflared service install
        sudo systemctl start cloudflared
        sudo systemctl enable cloudflared
        echo "✅ Cloudflare Tunnel installed as service"
        echo "📝 Check status: sudo systemctl status cloudflared"
        echo "📝 View logs: sudo journalctl -u cloudflared -f"
    else
        echo "📝 Run tunnel manually: cloudflared tunnel --config $CONFIG_FILE run"
    fi
    
    echo ""
    echo "🎉 Deployment complete!"
    echo "🌐 Frontend: https://$DOMAIN"
    if [ -n "$API_DOMAIN" ]; then
        echo "🔧 API: https://$API_DOMAIN/docs"
    fi
fi

echo ""
echo "📝 Useful commands:"
echo "  - View logs: docker compose -f docker-compose.prod.yml logs -f"
echo "  - Stop services: docker compose -f docker-compose.prod.yml down"
echo "  - Restart tunnel (no-domain mode): cloudflared tunnel --url http://localhost:8501"
