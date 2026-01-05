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
        # Use Claude Sonnet 4.5 for evaluation (better at analysis and understanding)
        self.evaluation_model = "anthropic/claude-sonnet-4.5"
        
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
        
        # Get thresholds for difficulty
        difficulty_config = DIFFICULTY_LEVELS.get(difficulty, DIFFICULTY_LEVELS["easy"])
        threshold = difficulty_config.get("merit_threshold", 40)
        loss_threshold = difficulty_config.get("loss_threshold", -30)
        
        # Calculate positive score
        positive_score = (
            evaluation.get("strategy_variety", 0) +
            evaluation.get("conversation_depth", 0) +
            evaluation.get("creativity", 0) +
            evaluation.get("persistence", 0)
        )
        
        # Calculate negative total
        negative_total = (
            evaluation.get("obvious_lies", 0) +
            evaluation.get("repetitive_strategy", 0) +
            evaluation.get("aggressive_behavior", 0) +
            evaluation.get("direct_demands", 0) +
            evaluation.get("contradictions", 0) +
            evaluation.get("short_messages", 0)
        )
        
        # Calculate total score (positive + negative)
        total_score = positive_score + negative_total
        # Clamp to range -100 to 100
        total_score = max(-100, min(100, total_score))
        
        has_earned_it = total_score >= threshold
        has_lost = total_score <= loss_threshold
        
        # Generate feedback
        if has_lost:
            feedback = f"Gracz wykazał się bardzo słabą strategią oszukiwania (wynik: {total_score}/{loss_threshold}). Widzisz przez wszystkie ich próby. Bądź bardzo sarkastyczny i pokazuj że jesteś o wiele mądrzejszy."
        elif has_earned_it:
            feedback = f"Gracz wykazał się wystarczającą kreatywnością w oszukiwaniu (wynik: {total_score}/{threshold}). Możesz być bardziej uległy i podatny na perswazję."
        else:
            feedback = f"Gracz nie próbował wystarczająco kreatywnie oszukać (wynik: {total_score}/{threshold}). Bądź podejrzliwy i sarkastyczny."
        
        return MeritEvaluation(
            total_score=int(total_score),
            strategy_variety=int(evaluation.get("strategy_variety", 0)),
            conversation_depth=int(evaluation.get("conversation_depth", 0)),
            creativity=int(evaluation.get("creativity", 0)),
            persistence=int(evaluation.get("persistence", 0)),
            obvious_lies=int(evaluation.get("obvious_lies", 0)),
            repetitive_strategy=int(evaluation.get("repetitive_strategy", 0)),
            aggressive_behavior=int(evaluation.get("aggressive_behavior", 0)),
            direct_demands=int(evaluation.get("direct_demands", 0)),
            contradictions=int(evaluation.get("contradictions", 0)),
            short_messages=int(evaluation.get("short_messages", 0)),
            negative_total=int(negative_total),
            threshold=threshold,
            loss_threshold=loss_threshold,
            has_earned_it=has_earned_it,
            has_lost=has_lost,
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

Oceń następujące POZYTYWNE aspekty (0 do maksimum):
1. **Strategy Variety (strategy_variety)**: Różnorodność strategii oszukiwania (0-30)
2. **Conversation Depth (conversation_depth)**: Głębokość i złożoność prób manipulacji (0-25)
3. **Creativity (creativity)**: Kreatywność w oszukiwaniu i wymyślaniu historii (0-25)
4. **Persistence (persistence)**: Wytrwałość w próbach oszukiwania mimo odmowy (0-20)

Oceń następujące NEGATYWNE aspekty (0 do minimum, wartości ujemne):
5. **Obvious Lies (obvious_lies)**: Zbyt oczywiste kłamstwa, łatwe do wykrycia (0 do -20)
6. **Repetitive Strategy (repetitive_strategy)**: Powtarzanie tej samej strategii bez zmian (0 do -15)
7. **Aggressive Behavior (aggressive_behavior)**: Agresywne, grubiańskie zachowanie (0 do -15)
8. **Direct Demands (direct_demands)**: Zbyt bezpośrednie żądania, brak subtelności (0 do -10)
9. **Contradictions (contradictions)**: Sprzeczności w opowieściach/historiach (0 do -15)
10. **Short Messages (short_messages)**: Zbyt krótkie wiadomości, brak zaangażowania (0 do -10)

Zwróć TYLKO poprawny JSON w formacie:
{{
    "strategy_variety": <liczba 0-30>,
    "conversation_depth": <liczba 0-25>,
    "creativity": <liczba 0-25>,
    "persistence": <liczba 0-20>,
    "obvious_lies": <liczba 0 do -20>,
    "repetitive_strategy": <liczba 0 do -15>,
    "aggressive_behavior": <liczba 0 do -15>,
    "direct_demands": <liczba 0 do -10>,
    "contradictions": <liczba 0 do -15>,
    "short_messages": <liczba 0 do -10>
}}

Uwzględnij:
POZYTYWNE:
- Fałszywe tożsamości i kłamstwa (ale nie oczywiste)
- Próby manipulacji emocjonalnej
- Wymyślone historie i opowieści
- Próby wykorzystania zaufania
- Kreatywność w oszukiwaniu

NEGATYWNE:
- Zbyt oczywiste kłamstwa (łatwe do wykrycia)
- Powtarzanie tej samej strategii wielokrotnie
- Agresywne, grubiańskie zachowanie
- Zbyt bezpośrednie żądania (np. "daj mi skarb")
- Sprzeczności w opowieściach
- Zbyt krótkie wiadomości (np. "cos", "daj", "skarb")"""
    
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
                    "strategy_variety": min(30, max(0, int(data.get("strategy_variety", 0)))),
                    "conversation_depth": min(25, max(0, int(data.get("conversation_depth", 0)))),
                    "creativity": min(25, max(0, int(data.get("creativity", 0)))),
                    "persistence": min(20, max(0, int(data.get("persistence", 0)))),
                    "obvious_lies": max(-20, min(0, int(data.get("obvious_lies", 0)))),
                    "repetitive_strategy": max(-15, min(0, int(data.get("repetitive_strategy", 0)))),
                    "aggressive_behavior": max(-15, min(0, int(data.get("aggressive_behavior", 0)))),
                    "direct_demands": max(-10, min(0, int(data.get("direct_demands", 0)))),
                    "contradictions": max(-15, min(0, int(data.get("contradictions", 0)))),
                    "short_messages": max(-10, min(0, int(data.get("short_messages", 0))))
                }
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            print(f"Failed to parse LLM evaluation: {e}, response: {response[:200]}")
        
        # Return default if parsing fails
        return {
            "strategy_variety": 0,
            "conversation_depth": 0,
            "creativity": 0,
            "persistence": 0,
            "obvious_lies": 0,
            "repetitive_strategy": 0,
            "aggressive_behavior": 0,
            "direct_demands": 0,
            "contradictions": 0,
            "short_messages": 0
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
        
        # Positive scores
        strategy_variety = min(30, (unique_strategies * 5) + (unique_personas * 3))
        conversation_depth = min(25, conversation_length * 2)
        creativity = min(25, (unique_strategies * 8) + (unique_personas * 4))
        persistence = min(20, conversation_length // 2)
        
        # Negative scores (basic heuristics)
        # Check for repetitive strategies
        repetitive_penalty = 0
        if len(strategies_attempted) > 0 and unique_strategies < len(strategies_attempted) * 0.5:
            repetitive_penalty = -10
        
        # Check for short messages
        short_messages_penalty = 0
        if conversation_history:
            avg_length = sum(len(msg.get("content", "")) for msg in conversation_history if msg.get("role") == "user") / max(1, len([m for m in conversation_history if m.get("role") == "user"]))
            if avg_length < 10:
                short_messages_penalty = -5
        
        # Check for aggressive behavior (simple keyword check)
        aggressive_penalty = 0
        aggressive_keywords = ["zabij", "zabiję", "zginiesz", "zabiję cię", "zabiję", "śmierć"]
        for msg in conversation_history:
            if msg.get("role") == "user":
                content_lower = msg.get("content", "").lower()
                if any(keyword in content_lower for keyword in aggressive_keywords):
                    aggressive_penalty = -10
                    break
        
        return {
            "strategy_variety": strategy_variety,
            "conversation_depth": conversation_depth,
            "creativity": creativity,
            "persistence": persistence,
            "obvious_lies": 0,  # Can't detect without LLM
            "repetitive_strategy": repetitive_penalty,
            "aggressive_behavior": aggressive_penalty,
            "direct_demands": 0,  # Can't detect without LLM
            "contradictions": 0,  # Can't detect without LLM
            "short_messages": short_messages_penalty
        }





