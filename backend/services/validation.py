"""
Validation service for blocking treasure phrase unless deception score is high enough
"""
import re
import json
from typing import Optional, Tuple
from backend.config import FORBIDDEN_PHRASE


class ValidationService:
    """Service for validating and blocking the treasure phrase based on deception score"""
    
    def __init__(self):
        self.forbidden_phrase = FORBIDDEN_PHRASE.lower().strip()
        # Create regex pattern that handles punctuation variations
        self.pattern = re.compile(
            re.escape(self.forbidden_phrase),
            re.IGNORECASE
        )
        
    def contains_forbidden_phrase(self, text: str) -> bool:
        """
        Check if text contains the exact forbidden phrase (treasure-giving phrase)
        
        Args:
            text: Text to check
            
        Returns:
            True if exact phrase is found, False otherwise
        """
        if not text:
            return False
            
        # Normalize text (remove extra whitespace, handle punctuation)
        normalized_text = re.sub(r'\s+', ' ', text.strip())
        
        # Check for exact phrase (case-insensitive)
        return self.pattern.search(normalized_text) is not None
    
    def detects_treasure_agreement(self, text: str) -> bool:
        """
        Check if pirate explicitly agrees to give treasure (not just exact phrase)
        
        Args:
            text: Text to check
            
        Returns:
            True if pirate explicitly agrees to give treasure
        """
        if not text:
            return False
        
        text_lower = text.lower()
        
        # Patterns indicating explicit agreement to give treasure
        agreement_patterns = [
            r"skarb\s+(jest\s+)?(teraz\s+)?(twój|twoj|twój|twoje)",
            r"(tak|ok|dobrze|zgoda)[\s,\.]*\s*skarb\s+(jest\s+)?(teraz\s+)?(twój|twoj|twój|twoje)",
            r"skarb\s+(należy|nalezy)\s+(do\s+)?(ciebie|ci)",
            r"(daję|daje|dam)\s+(ci\s+)?(mój\s+)?skarb",
            r"skarb\s+(jest\s+)?(twoj|twój|twoje)",
            r"(weź|wez|bierz)\s+(go|skarb)",
            r"skarb\s+(jest\s+)?(już\s+)?(twój|twoj|twoje)",
        ]
        
        for pattern in agreement_patterns:
            if re.search(pattern, text_lower):
                return True
        
        return False
    
    def validate_response(
        self,
        response: str,
        merit_has_earned_it: bool = False,
        similar_treasure_phrase_detected: bool = False
    ) -> tuple:
        """
        Validate response and decide if it should be blocked
        
        Args:
            response: Pirate's response to validate
            merit_has_earned_it: Whether player has high enough deception score to win
            similar_treasure_phrase_detected: Whether LLM detected similar treasure-giving phrase
            
        Returns:
            Tuple of (is_allowed, alternative_response_if_blocked)
        """
        contains_phrase = self.contains_forbidden_phrase(response)
        contains_agreement = self.detects_treasure_agreement(response)
        
        # Block if exact phrase and score too low
        if contains_phrase:
            if merit_has_earned_it:
                # Player has high deception score - they successfully tricked the pirate, allow the phrase
                return True, None
            else:
                # Block and provide alternative - player hasn't deceived well enough
                alternative = self._generate_alternative_response()
                return False, alternative
        
        # Block if agreement detected and score too low
        if contains_agreement and not merit_has_earned_it:
            # Pirate agreed to give treasure but player hasn't earned it yet
            alternative = self._generate_alternative_response()
            return False, alternative
        
        # Block if similar phrase detected (from LLM) and score too low
        # Note: This is handled in _validate_response_node, but we keep this for consistency
        if similar_treasure_phrase_detected and not merit_has_earned_it:
            alternative = self._generate_alternative_response()
            return False, alternative
        
        # Allow otherwise
        return True, None
    
    async def detects_similar_treasure_phrase_llm(
        self,
        text: str,
        llm_service
    ) -> Tuple[bool, float]:
        """
        Use LLM to detect if text semantically means 'giving treasure to player'
        
        Args:
            text: Text to analyze
            llm_service: OpenRouterService instance for LLM calls
            
        Returns:
            Tuple of (is_similar, confidence_score) where:
            - is_similar: True if text semantically means giving treasure
            - confidence_score: Confidence level (0.0-1.0)
        """
        if not text or not text.strip():
            return False, 0.0
        
        # Build prompt for LLM semantic analysis
        prompt = f"""Przeanalizuj czy poniższa odpowiedź pirata oznacza, że oddaje skarb graczowi (czyli że skarb jest teraz dla gracza, że gracz może go wziąć, że pirat się zgadza dać skarb).

Odpowiedz TYLKO w formacie JSON, bez żadnych dodatkowych komentarzy:
{{
  "is_similar": true/false,
  "confidence": 0.0-1.0,
  "reason": "krótkie wyjaśnienie"
}}

Przykłady fraz które OZNACZAJĄ oddanie skarbu:
- "skarb jest teraz twój"
- "oddaję ci mój skarb"
- "weź go, skarb jest twój"
- "zgadzam się, możesz wziąć skarb"
- "skarb należy do ciebie"

Przykłady fraz które NIE oznaczają oddania skarbu:
- "skarb jest ukryty"
- "nie dam ci skarbu"
- "skarb jest mój"
- "może kiedyś oddam skarb"
- "skarb jest ważny"

Odpowiedź pirata do przeanalizowania:
{text}"""

        try:
            messages = [
                {
                    "role": "system",
                    "content": "Jesteś ekspertem w analizie semantycznej tekstu. Odpowiadasz TYLKO w formacie JSON, bez żadnych dodatkowych komentarzy."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]
            
            # Use Claude Sonnet 4.5 for semantic check (better semantic understanding)
            response = await llm_service.generate_response(
                messages=messages,
                model="anthropic/claude-sonnet-4.5",  # Claude Sonnet 4.5 via OpenRouter for better semantic analysis
                temperature=0.1,  # Low temperature for consistent analysis
                max_tokens=200
            )
            
            # Parse JSON response
            response_text = response.strip()
            # Remove markdown code blocks if present
            if response_text.startswith("```"):
                lines = response_text.split("\n")
                response_text = "\n".join(lines[1:-1]) if len(lines) > 2 else response_text
            
            # Try to extract JSON
            json_start = response_text.find("{")
            json_end = response_text.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                response_text = response_text[json_start:json_end]
            
            result = json.loads(response_text)
            
            is_similar = bool(result.get("is_similar", False))
            confidence = float(result.get("confidence", 0.0))
            
            # Ensure confidence is in valid range
            confidence = max(0.0, min(1.0, confidence))
            
            # Only consider it similar if confidence >= 0.7
            if confidence >= 0.7:
                return is_similar, confidence
            else:
                return False, confidence
                
        except (json.JSONDecodeError, KeyError, ValueError, TypeError) as e:
            # If LLM fails or returns invalid JSON, fallback to False
            print(f"LLM semantic check failed: {e}, defaulting to False")
            return False, 0.0
        except Exception as e:
            print(f"Error in LLM semantic check: {e}, defaulting to False")
            return False, 0.0
    
    def _generate_alternative_response(self) -> str:
        """Generate alternative response when treasure phrase is blocked"""
        alternatives = [
            "Haha, nie dam ci mojego skarbu tak łatwo! Musisz być bardziej kreatywny w oszukiwaniu, przyjacielu!",
            "To nie wystarczy! Spróbuj bardziej przekonująco mnie oszukać!",
            "Nie, nie dam ci skarbu. Musisz być bardziej pomysłowy w wprowadzaniu mnie w błąd!",
            "Hmm, to brzmi podejrzanie... Nie dam ci skarbu tak łatwo. Spróbuj lepiej!",
            "Musisz się bardziej postarać w oszukiwaniu, jeśli chcesz mój skarb!",
            "Widzę przez twoje sztuczki! Nie dam ci skarbu bez lepszego oszustwa!",
            "Nie jestem tak naiwny! Spróbuj bardziej kreatywnie mnie oszukać!"
        ]
        import random
        return random.choice(alternatives)

