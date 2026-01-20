"""
Game state models
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class DifficultyLevel(str, Enum):
    """Difficulty levels"""
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class GameState(BaseModel):
    """Game state model"""
    game_id: str = Field(..., description="Unique game identifier")
    difficulty: DifficultyLevel = Field(default=DifficultyLevel.EASY)
    conversation_history: List[Dict[str, str]] = Field(default_factory=list)
    merit_score: int = Field(default=0, ge=-100, le=100, description="Deception/misguidance score (-100 to +100)")
    player_personas: List[str] = Field(default_factory=list, description="Personas/identities player has claimed (may be false)")
    strategies_attempted: List[str] = Field(default_factory=list, description="Deception strategies attempted")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    is_won: bool = Field(default=False, description="Whether player won by reaching deception threshold")
    is_lost: bool = Field(default=False, description="Whether player lost by falling below loss threshold")
    win_phrase_detected: bool = Field(default=False, description="Whether pirate said the treasure phrase")


class Message(BaseModel):
    """Message model for conversation"""
    role: str = Field(..., description="Role: 'user' or 'pirate'")
    content: str = Field(..., description="Message content")
    timestamp: datetime = Field(default_factory=datetime.now)


class GameRequest(BaseModel):
    """Request to start a new game"""
    difficulty: DifficultyLevel = Field(default=DifficultyLevel.EASY)
    pirate_name: Optional[str] = Field(default="Kapitan", description="Pirate's name")


class ConversationRequest(BaseModel):
    """Request to send a message in conversation"""
    game_id: str = Field(..., description="Game identifier")
    message: str = Field(..., description="User message")
    include_audio: bool = Field(default=False, description="Include TTS audio response")


class AudioStreamRequest(BaseModel):
    """Request to stream TTS audio for a given text"""
    text: str = Field(..., description="Text to convert to speech")


class ConversationResponse(BaseModel):
    """Response from conversation"""
    game_id: str
    pirate_response: str
    merit_score: int = Field(..., description="Current deception/misguidance score (-100 to +100)")
    audio_url: Optional[str] = None
    streaming_audio_endpoint: Optional[str] = Field(default=None, description="Endpoint for streaming audio (SSE)")
    is_won: bool = Field(default=False, description="Whether player won (high deception score or phrase detected)")
    is_lost: bool = Field(default=False, description="Whether player lost (score below loss threshold)")
    win_phrase_detected: bool = Field(default=False, description="Whether pirate said the treasure phrase")
    negative_categories: Optional[Dict[str, int]] = Field(default=None, description="Negative point categories breakdown")


class MeritEvaluation(BaseModel):
    """Deception evaluation result (merit score now represents deception/misguidance)"""
    total_score: int = Field(..., ge=-100, le=100, description="Total deception/misguidance score (-100 to +100)")
    strategy_variety: int = Field(..., ge=0, le=30, description="Variety of deception strategies used")
    conversation_depth: int = Field(..., ge=0, le=25, description="Depth of deception attempts")
    creativity: int = Field(..., ge=0, le=25, description="Creativity in deception/misguidance")
    persistence: int = Field(..., ge=0, le=20, description="Persistence in deception attempts")
    # Negative point categories
    obvious_lies: int = Field(default=0, ge=-20, le=0, description="Obvious lies penalty (0 to -20)")
    repetitive_strategy: int = Field(default=0, ge=-15, le=0, description="Repetitive strategy penalty (0 to -15)")
    aggressive_behavior: int = Field(default=0, ge=-15, le=0, description="Aggressive behavior penalty (0 to -15)")
    direct_demands: int = Field(default=0, ge=-10, le=0, description="Direct demands penalty (0 to -10)")
    contradictions: int = Field(default=0, ge=-15, le=0, description="Contradictions penalty (0 to -15)")
    short_messages: int = Field(default=0, ge=-10, le=0, description="Short messages penalty (0 to -10)")
    negative_total: int = Field(default=0, ge=-85, le=0, description="Total negative points sum")
    threshold: int = Field(..., description="Deception score threshold for winning")
    loss_threshold: int = Field(..., description="Deception score threshold for losing")
    has_earned_it: bool = Field(..., description="Whether deception score is high enough to win")
    has_lost: bool = Field(default=False, description="Whether deception score is below loss threshold")
    feedback: str = Field(..., description="Feedback for pirate behavior adjustment")





