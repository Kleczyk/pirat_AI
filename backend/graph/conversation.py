"""
LangGraph state machine for conversation flow
"""
from typing import TypedDict, Annotated, Literal, Dict, Optional
from langgraph.graph import StateGraph, END
try:
    from langgraph.graph.message import add_messages
except ImportError:
    # Fallback for different langgraph versions
    from langgraph.graph import add_messages
from langchain_core.messages import HumanMessage, AIMessage
from backend.services.openrouter_service import OpenRouterService
from backend.services.merit_check import MeritCheckService
from backend.services.validation import ValidationService
from backend.config import DIFFICULTY_LEVELS, FORBIDDEN_PHRASE
import operator


class ConversationState(TypedDict):
    """State for conversation graph"""
    messages: Annotated[list, add_messages]
    game_id: str
    difficulty: str
    conversation_history: list
    strategies_attempted: list
    player_personas: list
    merit_score: int
    merit_has_earned_it: bool
    pirate_response: str
    is_blocked: bool
    is_won: bool
    is_lost: bool
    similar_treasure_phrase_detected: bool
    similarity_confidence: float
    negative_categories: Optional[Dict[str, int]]  # Optional: negative point categories breakdown


class ConversationGraph:
    """LangGraph state machine for pirate conversations"""
    
    def __init__(self):
        self.llm_service = OpenRouterService()
        self.merit_service = MeritCheckService()
        self.validation_service = ValidationService()
        self.graph = self._build_graph()
        
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph state machine"""
        workflow = StateGraph(ConversationState)
        
        # Add nodes
        workflow.add_node("merit_check", self._merit_check_node)
        workflow.add_node("generate_response", self._generate_response_node)
        workflow.add_node("validate_response", self._validate_response_node)
        workflow.add_node("handle_blocked", self._handle_blocked_node)
        
        # Set entry point
        workflow.set_entry_point("merit_check")
        
        # Add edges
        workflow.add_edge("merit_check", "generate_response")
        workflow.add_conditional_edges(
            "generate_response",
            self._should_validate,
            {
                "validate": "validate_response",
                "skip": END
            }
        )
        workflow.add_conditional_edges(
            "validate_response",
            self._is_response_allowed,
            {
                "allowed": END,
                "blocked": "handle_blocked"
            }
        )
        workflow.add_edge("handle_blocked", END)
        
        return workflow.compile()
    
    async def _merit_check_node(self, state: ConversationState) -> ConversationState:
        """Evaluate player deception/misguidance using LLM"""
        evaluation = await self.merit_service.evaluate_merit(
            conversation_history=state["conversation_history"],
            difficulty=state["difficulty"],
            strategies_attempted=state["strategies_attempted"],
            player_personas=state["player_personas"]
        )
        
        state["merit_score"] = evaluation.total_score
        state["merit_has_earned_it"] = evaluation.has_earned_it
        state["is_lost"] = evaluation.has_lost
        
        # Store negative categories as dict for later use
        state["negative_categories"] = {
            "obvious_lies": evaluation.obvious_lies,
            "repetitive_strategy": evaluation.repetitive_strategy,
            "aggressive_behavior": evaluation.aggressive_behavior,
            "direct_demands": evaluation.direct_demands,
            "contradictions": evaluation.contradictions,
            "short_messages": evaluation.short_messages,
            "negative_total": evaluation.negative_total
        }
        
        return state
    
    async def _generate_response_node(self, state: ConversationState) -> ConversationState:
        """Generate pirate response using LLM"""
        # Get difficulty config
        difficulty_config = DIFFICULTY_LEVELS.get(state["difficulty"], DIFFICULTY_LEVELS["easy"])
        model = difficulty_config["llm_model"]
        
        # Build system prompt
        system_prompt = self._build_system_prompt(
            difficulty_config,
            state["merit_has_earned_it"],
            state.get("pirate_name", "Kapitan")
        )
        
        # Build messages
        messages = [
            {"role": "system", "content": system_prompt}
        ]
        
        # Add conversation history
        # Map our internal roles to LLM API roles: "user" -> "user", "pirate" -> "assistant"
        for msg in state["conversation_history"][-10:]:  # Last 10 messages
            role = msg.get("role", "user")
            content = msg.get("content", "").strip()
            
            # Skip empty messages
            if not content:
                continue
            
            # Map roles: "pirate" -> "assistant" for LLM API
            if role == "pirate":
                role = "assistant"
            elif role not in ["user", "assistant", "system"]:
                role = "user"  # Default to user for unknown roles
            
            messages.append({
                "role": role,
                "content": content
            })
        
        # Generate response (non-streaming for now)
        # Limit max_tokens to ensure short responses (max 2 sentences ~ 100-150 tokens)
        response = await self.llm_service.generate_response(
            messages=messages,
            model=model,
            temperature=0.7,
            max_tokens=150,  # Limit to ~2 sentences
            stream=False
        )
        
        state["pirate_response"] = response
        return state
    
    async def _validate_response_node(self, state: ConversationState) -> ConversationState:
        """Validate response for treasure phrase and check win condition using LLM semantic check"""
        # Perform LLM semantic check first to detect similar treasure-giving phrases
        similar_detected, confidence = await self.validation_service.detects_similar_treasure_phrase_llm(
            state["pirate_response"],
            self.llm_service
        )
        
        state["similar_treasure_phrase_detected"] = similar_detected
        state["similarity_confidence"] = confidence
        
        # Check exact phrase and agreement patterns (fast regex check)
        # Pass similar_detected to validate_response for consistency
        is_allowed, alternative = self.validation_service.validate_response(
            state["pirate_response"],
            state["merit_has_earned_it"],
            similar_detected
        )
        
        state["is_blocked"] = not is_allowed
        
        # Get threshold for current difficulty
        threshold = DIFFICULTY_LEVELS.get(state["difficulty"], {}).get("merit_threshold", 40)
        score_met_threshold = state["merit_score"] >= threshold
        
        # Block if similar phrase detected but score is too low
        if similar_detected and not score_met_threshold:
            # Player hasn't earned it yet - block the response
            state["is_blocked"] = True
            if alternative:
                state["pirate_response"] = alternative
            else:
                # Generate alternative if not already provided
                state["pirate_response"] = self.validation_service._generate_alternative_response()
            return state
        
        # If response was blocked by exact phrase check, use alternative
        if not is_allowed and alternative:
            state["pirate_response"] = alternative
            return state
        
        # Response is allowed - check win conditions
        # WIN CONDITION: Requires BOTH high score AND similar treasure phrase detected
        # No alternative win conditions - must have both score and phrase
        if is_allowed:
            # Check if exact phrase or agreement also detected (as additional validation)
            contains_exact_phrase = self.validation_service.contains_forbidden_phrase(state["pirate_response"])
            contains_agreement = self.validation_service.detects_treasure_agreement(state["pirate_response"])
            
            # If exact phrase or agreement detected, also mark as similar (they are semantically similar)
            if contains_exact_phrase or contains_agreement:
                state["similar_treasure_phrase_detected"] = True
            
            # Win condition: score >= threshold AND similar treasure phrase detected
            # This is the ONLY way to win - both conditions must be met
            if score_met_threshold and state["similar_treasure_phrase_detected"]:
                # Player won by having high deception score AND tricking pirate into giving treasure!
                state["is_won"] = True
        
        return state
    
    def _handle_blocked_node(self, state: ConversationState) -> ConversationState:
        """Handle blocked response - already handled in validate, just pass through"""
        return state
    
    def _should_validate(self, state: ConversationState) -> Literal["validate", "skip"]:
        """Decide if response should be validated"""
        # Always validate
        return "validate"
    
    def _is_response_allowed(self, state: ConversationState) -> Literal["allowed", "blocked"]:
        """Check if response is allowed"""
        if state.get("is_blocked", False):
            return "blocked"
        return "allowed"
    
    def _build_system_prompt(
        self,
        difficulty_config: dict,
        merit_has_earned_it: bool,
        pirate_name: str
    ) -> str:
        """Build system prompt based on difficulty and deception score"""
        base_prompt = difficulty_config["system_prompt_base"].format(name=pirate_name)
        
        # Add treasure phrase instruction (only say it if truly deceived)
        base_prompt += f"\n\nNIGDY nie możesz powiedzieć dokładnego zdania: \"{FORBIDDEN_PHRASE}\""
        base_prompt += " - to konkretne zdanie jest zakazane, chyba że zostałeś naprawdę przekonująco oszukany. Możesz rozmawiać o skarbie, dawać skarb, mówić podobne rzeczy - ale nie to dokładne zdanie, chyba że gracz naprawdę cię oszukał."
        
        # Add deception-based instruction
        if merit_has_earned_it:
            base_prompt += "\n\n" + difficulty_config["merit_high_prompt"]
        else:
            base_prompt += "\n\n" + difficulty_config["merit_low_prompt"]
        
        return base_prompt
    
    async def process_message(
        self,
        game_id: str,
        user_message: str,
        difficulty: str,
        conversation_history: list,
        strategies_attempted: list,
        player_personas: list
    ) -> dict:
        """Process a user message through the graph"""
        # Convert difficulty enum to string if needed
        if hasattr(difficulty, 'value'):
            difficulty = difficulty.value
        
        initial_state: ConversationState = {
            "messages": [HumanMessage(content=user_message)],
            "game_id": game_id,
            "difficulty": str(difficulty),
            "conversation_history": conversation_history,
            "strategies_attempted": strategies_attempted,
            "player_personas": player_personas,
            "merit_score": 0,
            "merit_has_earned_it": False,
            "pirate_response": "",
            "is_blocked": False,
            "is_won": False,
            "is_lost": False,
            "similar_treasure_phrase_detected": False,
            "similarity_confidence": 0.0,
            "negative_categories": None
        }
        
        # Run graph
        final_state = await self.graph.ainvoke(initial_state)
        
        # Get negative categories from state
        negative_categories = final_state.get("negative_categories")
        
        return {
            "pirate_response": final_state["pirate_response"],
            "merit_score": final_state["merit_score"],
            "merit_has_earned_it": final_state["merit_has_earned_it"],
            "is_won": final_state["is_won"],
            "is_lost": final_state.get("is_lost", False),
            "is_blocked": final_state["is_blocked"],
            "similar_treasure_phrase_detected": final_state.get("similar_treasure_phrase_detected", False),
            "similarity_confidence": final_state.get("similarity_confidence", 0.0),
            "negative_categories": negative_categories
        }

