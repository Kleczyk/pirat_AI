"""
FastAPI main application
"""
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from backend.models.game import GameRequest, ConversationRequest, ConversationResponse, GameState
from backend.services.pirate_service import PirateService
from backend.services.speech_to_text_service import SpeechToTextService
from backend.config import settings
import uvicorn

app = FastAPI(
    title="Outwit the AI Pirate Game API",
    description="API for the Outwit the AI Pirate conversation game",
    version="1.0.0"
)

# CORS middleware for Streamlit frontend
# For production CORS configuration, see backend/main.prod.py.example
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
pirate_service = PirateService()
speech_to_text_service = SpeechToTextService()


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Outwit the AI Pirate Game API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


@app.post("/api/game/start", response_model=GameState)
async def start_game(request: GameRequest):
    """Start a new game"""
    try:
        game_state = pirate_service.start_game(
            difficulty=request.difficulty.value,
            pirate_name=request.pirate_name or "Kapitan"
        )
        return game_state
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/game/conversation", response_model=ConversationResponse)
async def send_message(request: ConversationRequest):
    """Send a message in the conversation"""
    try:
        response = await pirate_service.process_conversation(
            game_id=request.game_id,
            user_message=request.message,
            include_audio=request.include_audio
        )
        return response
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/game/{game_id}", response_model=GameState)
async def get_game_state(game_id: str):
    """Get current game state"""
    game_state = pirate_service.get_game_state(game_id)
    if not game_state:
        raise HTTPException(status_code=404, detail="Game not found")
    return game_state


@app.post("/api/speech-to-text")
async def speech_to_text(
    audio: UploadFile = File(...),
    format: str = Form(default="wav")
):
    """Convert audio to text using Google Gemini 2.0 Flash Lite via OpenRouter"""
    try:
        audio_data = await audio.read()
        transcribed_text = await speech_to_text_service.transcribe_audio(
            audio_data=audio_data,
            audio_format=format
        )
        
        if not transcribed_text:
            raise HTTPException(status_code=500, detail="Failed to transcribe audio")
        
        return {
            "success": True,
            "text": transcribed_text,
            "error": None
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(
        "backend.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )





