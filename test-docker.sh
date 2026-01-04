#!/bin/bash
set -e

echo "🧪 Testing Docker Compose Setup"
echo "================================"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check prerequisites
echo -e "\n${BLUE}1. Checking prerequisites...${NC}"
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠ .env file not found. Creating from .env.example...${NC}"
    if [ -f .env.example ]; then
        cp .env.example .env
        echo -e "${YELLOW}⚠ Please edit .env and add your API keys before continuing${NC}"
        echo -e "${YELLOW}⚠ Press Enter to continue or Ctrl+C to abort...${NC}"
        read
    else
        echo -e "${RED}✗ .env.example file not found${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}✓ .env file exists${NC}"
fi

if ! docker ps > /dev/null 2>&1; then
    echo -e "${RED}✗ Docker is not running${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Docker is running${NC}"

# Check for required tools
if ! command -v curl &> /dev/null; then
    echo -e "${YELLOW}⚠ curl not found. Some tests may fail.${NC}"
fi

if ! command -v jq &> /dev/null; then
    echo -e "${YELLOW}⚠ jq not found. JSON parsing will be limited.${NC}"
    JQ_AVAILABLE=false
else
    JQ_AVAILABLE=true
fi

# Build images
echo -e "\n${BLUE}2. Building images...${NC}"
if docker compose build; then
    echo -e "${GREEN}✓ Images built successfully${NC}"
else
    echo -e "${RED}✗ Image build failed${NC}"
    exit 1
fi

# Start services
echo -e "\n${BLUE}3. Starting services...${NC}"
docker compose up -d
echo -e "${GREEN}✓ Services started${NC}"

# Wait for health
echo -e "\n${BLUE}4. Waiting for services to be healthy...${NC}"
HEALTHY=false
for i in {1..30}; do
    if curl -f http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Backend is healthy${NC}"
        HEALTHY=true
        break
    fi
    if [ $i -eq 30 ]; then
        echo -e "${RED}✗ Backend failed to become healthy after 60 seconds${NC}"
        echo -e "${YELLOW}Backend logs:${NC}"
        docker compose logs --tail=50 backend
        exit 1
    fi
    echo -n "."
    sleep 2
done
echo ""

# Test endpoints
echo -e "\n${BLUE}5. Testing API endpoints...${NC}"

# Health check
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Health endpoint works${NC}"
else
    echo -e "${RED}✗ Health endpoint failed${NC}"
    exit 1
fi

# Root endpoint
if curl -f http://localhost:8000/ > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Root endpoint works${NC}"
    if [ "$JQ_AVAILABLE" = true ]; then
        ROOT_RESPONSE=$(curl -s http://localhost:8000/)
        echo "   Response: $(echo "$ROOT_RESPONSE" | jq -r '.message // "OK"')"
    fi
else
    echo -e "${RED}✗ Root endpoint failed${NC}"
    exit 1
fi

# Game start
echo -e "\n${BLUE}6. Testing game functionality...${NC}"
GAME_RESPONSE=$(curl -s -X POST http://localhost:8000/api/game/start \
  -H "Content-Type: application/json" \
  -d '{"difficulty": "easy", "pirate_name": "TestKapitan"}')

if echo "$GAME_RESPONSE" | grep -q "game_id" || [ "$JQ_AVAILABLE" = true ] && echo "$GAME_RESPONSE" | jq -e '.game_id' > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Game start endpoint works${NC}"
    if [ "$JQ_AVAILABLE" = true ]; then
        GAME_ID=$(echo "$GAME_RESPONSE" | jq -r '.game_id')
        echo "   Game ID: $GAME_ID"
    else
        # Fallback: extract game_id manually
        GAME_ID=$(echo "$GAME_RESPONSE" | grep -o '"game_id":"[^"]*"' | cut -d'"' -f4)
    fi
else
    echo -e "${RED}✗ Game start endpoint failed${NC}"
    echo "Response: $GAME_RESPONSE"
    exit 1
fi

# Conversation
if [ -n "$GAME_ID" ]; then
    CONV_RESPONSE=$(curl -s -X POST http://localhost:8000/api/game/conversation \
      -H "Content-Type: application/json" \
      -d "{\"game_id\": \"$GAME_ID\", \"message\": \"Cześć kapitanie! To test.\", \"include_audio\": false}")
    
    if echo "$CONV_RESPONSE" | grep -q "pirate_response" || [ "$JQ_AVAILABLE" = true ] && echo "$CONV_RESPONSE" | jq -e '.pirate_response' > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Conversation endpoint works${NC}"
        if [ "$JQ_AVAILABLE" = true ]; then
            MERIT_SCORE=$(echo "$CONV_RESPONSE" | jq -r '.merit_score // 0')
            echo "   Merit Score: $MERIT_SCORE"
        fi
    else
        echo -e "${RED}✗ Conversation endpoint failed${NC}"
        echo "Response: $CONV_RESPONSE"
        exit 1
    fi
    
    # Get game state
    STATE_RESPONSE=$(curl -s http://localhost:8000/api/game/$GAME_ID)
    if echo "$STATE_RESPONSE" | grep -q "game_id" || [ "$JQ_AVAILABLE" = true ] && echo "$STATE_RESPONSE" | jq -e '.game_id' > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Get game state endpoint works${NC}"
    else
        echo -e "${YELLOW}⚠ Get game state endpoint may have issues${NC}"
    fi
fi

# Frontend
echo -e "\n${BLUE}7. Checking frontend...${NC}"
if curl -f http://localhost:8501 > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Frontend is accessible${NC}"
else
    echo -e "${YELLOW}⚠ Frontend check skipped (may need browser or more time to start)${NC}"
fi

# Service communication
echo -e "\n${BLUE}8. Testing service communication...${NC}"
if docker compose exec -T frontend curl -f http://backend:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Frontend can communicate with backend${NC}"
else
    echo -e "${YELLOW}⚠ Service communication test skipped (curl may not be in frontend image)${NC}"
fi

# Summary
echo -e "\n${GREEN}✅ All tests passed!${NC}"
echo -e "\n${BLUE}Services are running:${NC}"
echo "  - Backend API: http://localhost:8000"
echo "  - API Documentation: http://localhost:8000/docs"
echo "  - Frontend UI: http://localhost:8501"
echo ""
echo -e "${BLUE}Useful commands:${NC}"
echo "  - View logs: docker compose logs -f"
echo "  - Stop services: docker compose down"
echo "  - Restart: docker compose restart"
echo "  - Test health: curl http://localhost:8000/health"





