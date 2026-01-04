# Setup Instructions

## Quick Start

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Create .env file:**
   ```bash
   cp .env.example .env
   ```
   
   Then edit `.env` and add your API keys:
   - `KIE_AI_API_KEY` - Get from https://kie.ai
   - `OPENROUTER_API_KEY` - Get from https://openrouter.ai

3. **Start the backend:**
   ```bash
   python -m backend.main
   ```
   Or:
   ```bash
   uvicorn backend.main:app --reload
   ```

4. **Start the frontend (in another terminal):**
   ```bash
   streamlit run frontend/app.py
   ```

## API Keys

### Kie.ai (for ElevenLabs TTS)
1. Go to https://kie.ai
2. Sign up / Log in
3. Get your API key from the dashboard
4. Add to `.env` as `KIE_AI_API_KEY`

### OpenRouter (for LLM)
1. Go to https://openrouter.ai
2. Sign up / Log in
3. Get your API key from the dashboard
4. Add to `.env` as `OPENROUTER_API_KEY`

## Testing the API

Once the backend is running, you can test it:

```bash
# Health check
curl http://localhost:8000/health

# Start a game
curl -X POST http://localhost:8000/api/game/start \
  -H "Content-Type: application/json" \
  -d '{"difficulty": "easy", "pirate_name": "Kapitan"}'

# Send a message (replace GAME_ID)
curl -X POST http://localhost:8000/api/game/conversation \
  -H "Content-Type: application/json" \
  -d '{
    "game_id": "YOUR_GAME_ID",
    "message": "Cześć kapitanie!",
    "include_audio": false
  }'
```

## Troubleshooting

### Import Errors
If you get import errors, make sure all dependencies are installed:
```bash
pip install -r requirements.txt
```

### API Key Errors
Make sure your `.env` file exists and contains valid API keys.

### Port Already in Use
Change the port in `.env`:
```env
PORT=8001
```

### Streamlit Can't Connect to API
Make sure the backend is running and check the API URL in `frontend/app.py`:
```python
API_BASE_URL = "http://localhost:8000"  # Update if needed
```





