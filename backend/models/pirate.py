"""
Pirate character models
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum


class PiratePersonality(str, Enum):
    """Pirate personality types"""
    GULLIBLE = "gullible"
    CAUTIOUS = "cautious"
    PARANOID = "paranoid"


class PirateCharacter(BaseModel):
    """Pirate character model"""
    name: str = Field(default="Kapitan", description="Pirate's name")
    personality: PiratePersonality = Field(default=PiratePersonality.GULLIBLE)
    difficulty: str = Field(..., description="Difficulty level")
    merit_mode: str = Field(default="sarcastic", description="'lenient' or 'sarcastic'")
    conversation_count: int = Field(default=0)
    refused_count: int = Field(default=0)







