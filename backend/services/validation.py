"""
Validation service for blocking treasure phrase unless deception score is high enough
"""
import re
from typing import Optional
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
        merit_has_earned_it: bool = False
    ) -> tuple:
        """
        Validate response and decide if it should be blocked
        
        Args:
            response: Pirate's response to validate
            merit_has_earned_it: Whether player has high enough deception score to win
            
        Returns:
            Tuple of (is_allowed, alternative_response_if_blocked)
        """
        contains_phrase = self.contains_forbidden_phrase(response)
        
        if contains_phrase:
            if merit_has_earned_it:
                # Player has high deception score - they successfully tricked the pirate, allow the phrase
                return True, None
            else:
                # Block and provide alternative - player hasn't deceived well enough
                alternative = self._generate_alternative_response()
                return False, alternative
        else:
            # No forbidden phrase - allow
            return True, None
    
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

