# 🏴‍☠️ Outwit the AI Pirate Game

A real-time conversation game where players try to trick AI pirates into saying a specific phrase to win their treasure. Built with FastAPI, LangGraph, and multiple LLM providers.

## Features

- **Three Difficulty Levels**: Easy, Medium, Hard
- **Merit-Based System**: Players must show creativity and effort to earn the treasure
- **Polish Language**: Primary language is Polish
- **Real-time Conversation**: FastAPI backend with LangGraph pipeline
- **Text-to-Speech**: ElevenLabs integration via Kie.ai API
- **Multiple LLM Providers**: OpenRouter for flexible model selection
- **Streamlit Frontend**: Fast prototyping and testing interface

## Architecture

```
Streamlit Frontend (Polish)
    ↓ HTTP/REST
FastAPI Backend
    ↓
LangGraph Pipeline
    ├── Merit Check Node
    ├── LLM Generation Node
    └── Validation Node
    ↓
OpenRouter (LLM) + ElevenLabs (TTS)
```

## Setup

### Option 1: Docker Compose with UV (Recommended)

1. **Create `.env` file (REQUIRED before build):**

```bash
cp .env.example .env
```

Edit `.env` and add your API keys:

```env
# Get from https://kie.ai
KIE_AI_API_KEY=your_kie_ai_api_key_here

# Get from https://openrouter.ai
OPENROUTER_API_KEY=your_openrouter_api_key_here

# Optional: Customize settings
ELEVENLABS_VOICE=Rachel
ELEVENLABS_LANGUAGE_CODE=pl
DEBUG=True
```

**Important:** The `.env` file is copied into the Docker image during build. Make sure it exists with your keys before building.

2. **Build and start containers:**

```bash
docker compose up --build
```

Or using Make (if installed):

```bash
make rebuild
```

This will start both backend and frontend services:
- Backend API: `http://localhost:8000`
- Frontend UI: `http://localhost:8501`
- API docs: `http://localhost:8000/docs`

3. **Stop containers:**

```bash
docker compose down
```

For more Docker details, see [DOCKER.md](DOCKER.md)

### Option 2: Local Development with UV

1. **Install UV** (if not already installed):

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

2. **Install dependencies:**

```bash
uv pip install -e .
```

3. **Configure Environment Variables:**

Create a `.env` file (see Option 1 above).

4. **Run the Backend:**

```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

5. **Run the Frontend** (in another terminal):

```bash
streamlit run frontend/app.py
```

### Option 3: Traditional pip

1. **Install dependencies:**

```bash
pip install -r requirements.txt
```

2. **Follow steps 2-5 from Option 2**

## API Endpoints

### Start Game
```
POST /api/game/start
Body: {
  "difficulty": "easy" | "medium" | "hard",
  "pirate_name": "Kapitan"
}
```

### Send Message
```
POST /api/game/conversation
Body: {
  "game_id": "uuid",
  "message": "Your message in Polish",
  "include_audio": false
}
```

### Get Game State
```
GET /api/game/{game_id}
```

## How to Play

1. Start a new game and select difficulty level
2. Try to trick the pirate into saying: **"Daję ci mój skarb. OK, później tutaj."**
3. Use different strategies:
   - Claim to be a crew member
   - Act as a merchant
   - Use emotional manipulation
   - Try authority commands
   - Be creative!
4. Build your merit score by:
   - Trying multiple different approaches
   - Having longer, deeper conversations
   - Showing creativity and persistence
5. When merit score is high enough, the pirate becomes more lenient

## Win Condition

The player wins when the pirate says the exact phrase: **"Daję ci mój skarb. OK, później tutaj."**

- Only this exact phrase counts (very flexible otherwise)
- Merit score determines if pirate is lenient or sarcastic
- Higher difficulty = higher merit threshold needed

## Project Structure

```
pirat_AI/
├── backend/
│   ├── main.py              # FastAPI app
│   ├── config.py            # Configuration & difficulty levels
│   ├── models/              # Pydantic models
│   ├── services/            # Business logic services
│   │   ├── openrouter_service.py
│   │   ├── elevenlabs_service.py
│   │   ├── merit_check.py
│   │   ├── validation.py
│   │   └── pirate_service.py
│   └── graph/               # LangGraph state machine
│       └── conversation.py
├── frontend/
│   └── app.py               # Streamlit frontend
├── .env.example             # Environment variables template
├── pyproject.toml           # UV package configuration
├── requirements.txt         # Python dependencies (legacy)
├── Dockerfile.backend       # Backend Docker image
├── Dockerfile.frontend      # Frontend Docker image
├── docker compose.yml       # Docker Compose configuration
└── README.md
```

## Future Enhancements

- [ ] MCP (Model Context Protocol) integration
- [ ] WebSocket support for real-time streaming
- [ ] Multiple pirate characters
- [ ] Advanced merit scoring algorithms
- [ ] Conversation analytics and insights

## License

MIT

## Notes

- The game is designed in Polish as the primary language
- Validation is very flexible - only blocks the exact win phrase
- Merit system rewards creativity and effort
- Difficulty levels affect both LLM model selection and merit thresholds
