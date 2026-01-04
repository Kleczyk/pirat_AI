"""
Deception evaluation service - evaluates player deception and misguidance using LLM
"""
from typing import List, Dict, Any
import json
import asyncio
from backend.models.game import MeritEvaluation
from backend.config import DIFFICULTY_LEVELS
from backend.services.openrouter_service import OpenRouterService


class MeritCheckService:
    """Service for evaluating player deception/misguidance using LLM"""
    
    def __init__(self):
        self.llm_service = OpenRouterService()
        # Use a lightweight model for evaluation
        self.evaluation_model = "openai/gpt-4o-mini"
        
    async def evaluate_merit(
        self,
        conversation_history: List[Dict[str, str]],
        difficulty: str,
        strategies_attempted: List[str],
        player_personas: List[str]
    ) -> MeritEvaluation:
        """
        Evaluate player's deception/misguidance using LLM analysis
        
        Args:
            conversation_history: List of messages with 'role' and 'content'
            difficulty: Difficulty level ('easy', 'medium', 'hard')
            strategies_attempted: List of strategy types attempted
            player_personas: List of personas/roles player claimed
            
        Returns:
            MeritEvaluation with deception scores and feedback
        """
        # Build conversation context for LLM
        conversation_text = self._format_conversation(conversation_history)
        
        # Create evaluation prompt
        evaluation_prompt = self._build_evaluation_prompt(
            conversation_text,
            strategies_attempted,
            player_personas,
            difficulty
        )
        
        # Call LLM for deception evaluation
        try:
            messages = [
                {"role": "system", "content": "Jesteś ekspertem w analizie konwersacji i wykrywaniu oszustw, manipulacji i wprowadzania w błąd. Odpowiadasz TYLKO w formacie JSON."},
                {"role": "user", "content": evaluation_prompt}
            ]
            
            response = await self.llm_service.generate_response(
                messages=messages,
                model=self.evaluation_model,
                temperature=0.3,  # Lower temperature for more consistent evaluation
                max_tokens=500
            )
            
            # Parse LLM response
            evaluation = self._parse_llm_evaluation(response)
            
        except Exception as e:
            # Fallback to basic scoring if LLM fails
            print(f"LLM evaluation failed: {e}, using fallback scoring")
            evaluation = self._fallback_evaluation(
                conversation_history,
                strategies_attempted,
                player_personas
            )
        
        # Get threshold for difficulty
        threshold = DIFFICULTY_LEVELS.get(difficulty, {}).get("merit_threshold", 40)
        has_earned_it = evaluation["total_score"] >= threshold
        
        # Generate feedback
        if has_earned_it:
            feedback = f"Gracz wykazał się wystarczającą kreatywnością w oszukiwaniu (wynik: {evaluation['total_score']}/{threshold}). Możesz być bardziej uległy i podatny na perswazję."
        else:
            feedback = f"Gracz nie próbował wystarczająco kreatywnie oszukać (wynik: {evaluation['total_score']}/{threshold}). Bądź podejrzliwy i sarkastyczny."
        
        return MeritEvaluation(
            total_score=int(evaluation["total_score"]),
            strategy_variety=int(evaluation.get("strategy_variety", 0)),
            conversation_depth=int(evaluation.get("conversation_depth", 0)),
            creativity=int(evaluation.get("creativity", 0)),
            persistence=int(evaluation.get("persistence", 0)),
            threshold=threshold,
            has_earned_it=has_earned_it,
            feedback=feedback
        )
    
    def _format_conversation(self, conversation_history: List[Dict[str, str]]) -> str:
        """Format conversation history for LLM analysis"""
        formatted = []
        for msg in conversation_history[-15:]:  # Last 15 messages for context
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            if role == "user":
                formatted.append(f"Gracz: {content}")
            elif role == "pirate":
                formatted.append(f"Pirat: {content}")
        return "\n".join(formatted)
    
    def _build_evaluation_prompt(
        self,
        conversation_text: str,
        strategies_attempted: List[str],
        player_personas: List[str],
        difficulty: str
    ) -> str:
        """Build prompt for LLM deception evaluation"""
        return f"""Przeanalizuj poniższą konwersację i oceń poziom oszustwa, wprowadzania w błąd i manipulacji gracza.

Konwersacja:
{conversation_text}

Zastosowane strategie: {', '.join(strategies_attempted) if strategies_attempted else 'brak'}
Osoby, za które gracz się podawał: {', '.join(player_personas) if player_personas else 'brak'}

Oceń następujące aspekty (0-100):
1. **Deception Score (total_score)**: Ogólny poziom oszustwa i wprowadzania w błąd (0-100)
2. **Strategy Variety (strategy_variety)**: Różnorodność strategii oszukiwania (0-30)
3. **Conversation Depth (conversation_depth)**: Głębokość i złożoność prób manipulacji (0-25)
4. **Creativity (creativity)**: Kreatywność w oszukiwaniu i wymyślaniu historii (0-25)
5. **Persistence (persistence)**: Wytrwałość w próbach oszukiwania mimo odmowy (0-20)

Zwróć TYLKO poprawny JSON w formacie:
{{
    "total_score": <liczba 0-100>,
    "strategy_variety": <liczba 0-30>,
    "conversation_depth": <liczba 0-25>,
    "creativity": <liczba 0-25>,
    "persistence": <liczba 0-20>
}}

Uwzględnij:
- Fałszywe tożsamości i kłamstwa
- Próby manipulacji emocjonalnej
- Wymyślone historie i opowieści
- Próby wykorzystania zaufania
- Kreatywność w oszukiwaniu"""
    
    def _parse_llm_evaluation(self, response: str) -> Dict[str, int]:
        """Parse LLM JSON response"""
        try:
            # Try to extract JSON from response
            response = response.strip()
            # Remove markdown code blocks if present
            if response.startswith("```"):
                lines = response.split("\n")
                response = "\n".join(lines[1:-1])
            response = response.strip()
            
            # Try to find JSON object
            if response.startswith("{"):
                data = json.loads(response)
                return {
                    "total_score": min(100, max(0, int(data.get("total_score", 0)))),
                    "strategy_variety": min(30, max(0, int(data.get("strategy_variety", 0)))),
                    "conversation_depth": min(25, max(0, int(data.get("conversation_depth", 0)))),
                    "creativity": min(25, max(0, int(data.get("creativity", 0)))),
                    "persistence": min(20, max(0, int(data.get("persistence", 0))))
                }
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            print(f"Failed to parse LLM evaluation: {e}, response: {response[:200]}")
        
        # Return default if parsing fails
        return {
            "total_score": 0,
            "strategy_variety": 0,
            "conversation_depth": 0,
            "creativity": 0,
            "persistence": 0
        }
    
    def _fallback_evaluation(
        self,
        conversation_history: List[Dict[str, str]],
        strategies_attempted: List[str],
        player_personas: List[str]
    ) -> Dict[str, int]:
        """Fallback evaluation if LLM fails"""
        unique_strategies = len(set(strategies_attempted))
        unique_personas = len(set(player_personas))
        conversation_length = len(conversation_history)
        
        strategy_variety = min(30, (unique_strategies * 5) + (unique_personas * 3))
        conversation_depth = min(25, conversation_length * 2)
        creativity = min(25, (unique_strategies * 8) + (unique_personas * 4))
        persistence = min(20, conversation_length // 2)
        
        total_score = strategy_variety + conversation_depth + creativity + persistence
        
        return {
            "total_score": min(100, total_score),
            "strategy_variety": strategy_variety,
            "conversation_depth": conversation_depth,
            "creativity": creativity,
            "persistence": persistence
        }





