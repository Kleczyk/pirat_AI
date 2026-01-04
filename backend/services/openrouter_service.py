"""
OpenRouter LLM service
"""
import httpx
from typing import Optional, AsyncIterator, Dict, Any, List
from backend.config import settings


class OpenRouterService:
    """Service for OpenRouter LLM API"""
    
    def __init__(self):
        self.api_key = settings.openrouter_api_key
        self.base_url = settings.openrouter_base_url
        
    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False
    ) -> AsyncIterator[str] | str:
        """
        Generate LLM response via OpenRouter
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model identifier (e.g., 'openai/gpt-4-turbo')
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens to generate
            stream: Whether to stream the response
            
        Returns:
            If stream=True: AsyncIterator of text chunks
            If stream=False: Complete response string
        """
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY not set in environment")
        
        # Validate and clean messages
        if not messages:
            raise ValueError("Messages list cannot be empty")
        
        # Ensure messages have required fields and valid format
        cleaned_messages = []
        for msg in messages:
            if not isinstance(msg, dict):
                raise ValueError(f"Invalid message format: {msg}")
            role = msg.get("role", "").strip()
            content = msg.get("content", "").strip()
            
            if not role:
                raise ValueError(f"Message missing 'role' field: {msg}")
            if not content:
                # Skip empty content messages, but allow system messages with empty content
                if role != "system":
                    continue
            
            if role not in ["system", "user", "assistant"]:
                raise ValueError(f"Invalid role '{role}'. Must be 'system', 'user', or 'assistant'")
            
            cleaned_messages.append({
                "role": role,
                "content": content
            })
        
        if not cleaned_messages:
            raise ValueError("No valid messages after cleaning")
        
        if not model or not model.strip():
            raise ValueError("Model name cannot be empty")
            
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://github.com/your-repo",  # Optional
            "X-Title": "Outwit the AI Pirate Game",  # Optional
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": model.strip(),
            "messages": cleaned_messages,
            "temperature": float(temperature)
        }
        
        if max_tokens:
            payload["max_tokens"] = int(max_tokens)
            
        if stream:
            payload["stream"] = True
            return self._stream_response(headers, payload)
        else:
            return await self._get_complete_response(headers, payload)
    
    async def _get_complete_response(
        self,
        headers: Dict[str, str],
        payload: Dict[str, Any]
    ) -> str:
        """Get complete non-streaming response"""
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    json=payload,
                    headers=headers
                )
                response.raise_for_status()
                result = response.json()
                
                # Extract text from response
                choices = result.get("choices", [])
                if choices:
                    return choices[0].get("message", {}).get("content", "")
                return ""
            except httpx.HTTPStatusError as e:
                # Get detailed error message from response
                error_detail = f"HTTP {e.response.status_code}"
                try:
                    error_body = e.response.json()
                    if "error" in error_body:
                        error_detail = error_body["error"].get("message", str(error_body["error"]))
                    elif "detail" in error_body:
                        error_detail = error_body["detail"]
                except:
                    error_detail = e.response.text[:500] if e.response.text else str(e)
                raise ValueError(f"OpenRouter API error: {error_detail}")
            except httpx.RequestError as e:
                raise ValueError(f"Request to OpenRouter failed: {str(e)}")
    
    async def _stream_response(
        self,
        headers: Dict[str, str],
        payload: Dict[str, Any]
    ) -> AsyncIterator[str]:
        """Stream response chunks"""
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=headers
            ) as response:
                response.raise_for_status()
                
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]  # Remove "data: " prefix
                        if data_str == "[DONE]":
                            break
                            
                        try:
                            import json
                            data = json.loads(data_str)
                            choices = data.get("choices", [])
                            if choices:
                                delta = choices[0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    yield content
                        except json.JSONDecodeError:
                            continue





