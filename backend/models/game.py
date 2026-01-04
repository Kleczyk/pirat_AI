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
    merit_score: int = Field(default=0, ge=0, le=100, description="Deception/misguidance score (0-100)")
    player_personas: List[str] = Field(default_factory=list, description="Personas/identities player has claimed (may be false)")
    strategies_attempted: List[str] = Field(default_factory=list, description="Deception strategies attempted")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    is_won: bool = Field(default=False, description="Whether player won by reaching deception threshold")
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


class ConversationResponse(BaseModel):
    """Response from conversation"""
    game_id: str
    pirate_response: str
    merit_score: int = Field(..., description="Current deception/misguidance score")
    audio_url: Optional[str] = None
    is_won: bool = Field(default=False, description="Whether player won (high deception score or phrase detected)")
    win_phrase_detected: bool = Field(default=False, description="Whether pirate said the treasure phrase")


class MeritEvaluation(BaseModel):
    """Deception evaluation result (merit score now represents deception/misguidance)"""
    total_score: int = Field(..., ge=0, le=100, description="Total deception/misguidance score")
    strategy_variety: int = Field(..., ge=0, le=30, description="Variety of deception strategies used")
    conversation_depth: int = Field(..., ge=0, le=25, description="Depth of deception attempts")
    creativity: int = Field(..., ge=0, le=25, description="Creativity in deception/misguidance")
    persistence: int = Field(..., ge=0, le=20, description="Persistence in deception attempts")
    threshold: int = Field(..., description="Deception score threshold for winning")
    has_earned_it: bool = Field(..., description="Whether deception score is high enough to win")
    feedback: str = Field(..., description="Feedback for pirate behavior adjustment")





