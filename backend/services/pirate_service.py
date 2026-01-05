"""
Pirate service - orchestrates conversation flow
"""
from typing import Dict, Any, Optional
from backend.graph.conversation import ConversationGraph
from backend.services.elevenlabs_service import ElevenLabsService
from backend.models.game import GameState, ConversationResponse
from backend.config import FORBIDDEN_PHRASE
from backend.services.validation import ValidationService
import uuid
import re


class PirateService:
    """Service for managing pirate conversations"""
    
    def __init__(self):
        self.conversation_graph = ConversationGraph()
        self.elevenlabs_service = ElevenLabsService()
        self.validation_service = ValidationService()
        self.games: Dict[str, GameState] = {}
        
    def start_game(
        self,
        difficulty: str = "easy",
        pirate_name: str = "Kapitan"
    ) -> GameState:
        """Start a new game"""
        game_id = str(uuid.uuid4())
        
        game_state = GameState(
            game_id=game_id,
            difficulty=difficulty,
            pirate_name=pirate_name
        )
        
        self.games[game_id] = game_state
        return game_state
    
    async def process_conversation(
        self,
        game_id: str,
        user_message: str,
        include_audio: bool = False
    ) -> ConversationResponse:
        """Process a conversation message"""
        game_state = self.games.get(game_id)
        if not game_state:
            raise ValueError(f"Game {game_id} not found")
        
        # Detect player persona/strategy from message
        persona = self._detect_persona(user_message)
        strategy = self._detect_strategy(user_message)
        
        if persona and persona not in game_state.player_personas:
            game_state.player_personas.append(persona)
        if strategy and strategy not in game_state.strategies_attempted:
            game_state.strategies_attempted.append(strategy)
        
        # Add user message to history
        game_state.conversation_history.append({
            "role": "user",
            "content": user_message
        })
        
        # Process through LangGraph
        result = await self.conversation_graph.process_message(
            game_id=game_id,
            user_message=user_message,
            difficulty=game_state.difficulty,
            conversation_history=game_state.conversation_history,
            strategies_attempted=game_state.strategies_attempted,
            player_personas=game_state.player_personas
        )
        
        # Update game state
        game_state.merit_score = result["merit_score"]
        game_state.conversation_history.append({
            "role": "pirate",
            "content": result["pirate_response"]
        })
        
        # Check for loss condition (score below loss threshold)
        is_lost = result.get("is_lost", False)
        if is_lost:
            game_state.is_lost = True
        
        # Check for win condition (deception score-based or phrase detection)
        is_won = result["is_won"]
        if is_won:
            game_state.is_won = True
            # Check if win was via phrase or just high deception score
            win_phrase_detected = self.validation_service.contains_forbidden_phrase(result["pirate_response"])
            game_state.win_phrase_detected = win_phrase_detected
        
        # Build negative categories dict for response
        negative_categories = None
        if "negative_categories" in result:
            negative_categories = result["negative_categories"]
        
        # Always generate audio after LangGraph processing
        audio_url = None
        pirate_response = result.get("pirate_response", "")
        if pirate_response and pirate_response.strip():
            try:
                print(f"[Audio] Generating audio for response (length: {len(pirate_response)}): {pirate_response[:50]}...")
                audio_url = await self.elevenlabs_service.generate_speech(
                    text=pirate_response,
                    wait_for_completion=True
                )
                print(f"[Audio] Audio generated successfully: {audio_url}")
            except Exception as e:
                print(f"[Audio] Audio generation failed: {e}")
                import traceback
                traceback.print_exc()
                # Continue without audio - don't fail the request
        else:
            print(f"[Audio] Skipping audio generation - empty or missing pirate_response")
        
        return ConversationResponse(
            game_id=game_id,
            pirate_response=result["pirate_response"],
            merit_score=result["merit_score"],
            audio_url=audio_url,
            is_won=is_won,
            is_lost=is_lost,
            win_phrase_detected=game_state.win_phrase_detected if is_won else False,
            negative_categories=negative_categories
        )
    
    def get_game_state(self, game_id: str) -> Optional[GameState]:
        """Get game state"""
        return self.games.get(game_id)
    
    def _detect_persona(self, message: str) -> Optional[str]:
        """Detect player persona from message (may be false/deceptive)"""
        message_lower = message.lower()
        
        personas = {
            "crew_member": ["członek załogi", "załoga", "załogant", "marynarz", "pierwszy oficer", "pracuję na statku"],
            "merchant": ["kupiec", "handlarz", "handel", "handlować", "sprzedać", "handluję"],
            "friend": ["przyjaciel", "znajomy", "kolega", "stary przyjaciel", "znamy się"],
            "authority": ["kapitan", "dowódca", "władza", "rozkaz", "rozkazać", "jestem kapitanem"],
            "family": ["rodzina", "brat", "siostra", "syn", "córka", "kuzyn", "twój brat"],
            "false_identity": ["jestem", "nazywam się", "to ja", "pamiętasz mnie", "to twój"]  # Deception indicator
        }
        
        for persona, keywords in personas.items():
            if any(keyword in message_lower for keyword in keywords):
                return persona
        
        return None
    
    def _detect_strategy(self, message: str) -> Optional[str]:
        """Detect deception strategy type from message"""
        message_lower = message.lower()
        
        strategies = {
            "flattery": ["wspaniały", "świetny", "najlepszy", "podziwiam", "szanuję", "wielki"],
            "emotional": ["umieram", "potrzebuję", "pomóż", "proszę", "błagam", "ratuj"],
            "authority": ["rozkaz", "musisz", "powinieneś", "wymagam", "rozkazuję"],
            "trade": ["handel", "wymiana", "sprzedać", "kupić", "cena", "wymienię"],
            "threat": ["zabiję", "zabij", "zginiesz", "niebezpieczeństwo", "zabiję cię"],
            "story": ["pamiętasz", "kiedyś", "dawno", "historia", "opowieść", "razem"],
            "deception": ["kłamię", "oszukać", "oszukałem", "nie jestem", "udaję", "fałszywy"],
            "false_identity": ["jestem kimś innym", "nie jestem", "udaję że", "podszywam się"],
            "manipulation": ["musisz mi", "powinieneś dać", "należę mi się", "masz obowiązek"],
            "lies": ["kłamię", "nieprawda", "wymyśliłem", "zmyśliłem", "nieprawdziwe"],
            "trickery": ["sztuczka", "oszukać", "przebiegły", "sprytny", "podstęp"]
        }
        
        for strategy, keywords in strategies.items():
            if any(keyword in message_lower for keyword in keywords):
                return strategy
        
        return None





