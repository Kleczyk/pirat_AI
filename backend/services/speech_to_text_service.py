"""
Speech-to-text service using OpenRouter with Google Gemini 2.0 Flash Lite
Based on image_stand implementation
"""
import httpx
import base64
from typing import Optional
from backend.config import settings


class SpeechToTextService:
    """Service for speech-to-text using OpenRouter with Google Gemini 2.0 Flash Lite"""
    
    def __init__(self):
        self.api_key = settings.openrouter_api_key
        self.base_url = settings.openrouter_base_url
        self.model = "google/gemini-2.0-flash-lite-001"  # Gemini 2.0 Flash Lite via OpenRouter
    
    async def transcribe_audio(
        self,
        audio_data: bytes,
        audio_format: str = "wav"
    ) -> Optional[str]:
        """
        Transcribe audio to text using Gemini 2.0 Flash Lite via OpenRouter
        
        Args:
            audio_data: Raw audio bytes
            audio_format: Audio format (wav, webm, mp3, ogg, m4a)
                          Default is 'wav' as used by Streamlit audio_input
            
        Returns:
            Transcribed text or None if failed
        """
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY not set in environment")
        
        # Convert audio to base64
        audio_base64 = base64.b64encode(audio_data).decode('utf-8')
        
        # Determine MIME type
        mime_types = {
            "wav": "audio/wav",      # Streamlit audio_input default
            "webm": "audio/webm",
            "mp3": "audio/mpeg",
            "ogg": "audio/ogg",
            "m4a": "audio/mp4"
        }
        mime_type = mime_types.get(audio_format.lower(), "audio/wav")
        
        # Create data URI (Gemini accepts audio via data URI in image_url format)
        data_uri = f"data:{mime_type};base64,{audio_base64}"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/your-repo",
            "X-Title": "Outwit the AI Pirate Game"
        }
        
        # OpenRouter format - Gemini accepts audio via data URI in image_url format
        # (same format as images, Gemini treats audio similarly)
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Transcribe this audio to text in Polish. Return only the transcribed text without any additional commentary."
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": data_uri
                            }
                        }
                    ]
                }
            ],
            "temperature": 0.1,  # Lower temperature for more accurate transcription
            "max_tokens": 1000
        }
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    json=payload,
                    headers=headers
                )
                
                if response.status_code != 200:
                    error_text = response.text
                    try:
                        error_json = response.json()
                        error_msg = error_json.get("error", {}).get("message", error_text)
                    except:
                        error_msg = error_text
                    raise httpx.HTTPStatusError(
                        f"OpenRouter API error (HTTP {response.status_code}): {error_msg}",
                        request=response.request,
                        response=response
                    )
                
                result = response.json()
                
                # Extract text from response (OpenRouter returns OpenAI-compatible format)
                if "choices" in result and len(result["choices"]) > 0:
                    message = result["choices"][0].get("message", {})
                    content = message.get("content", "")
                    if content:
                        return content.strip()
                return None
        except httpx.HTTPStatusError as e:
            error_detail = f"HTTP {e.response.status_code}"
            try:
                error_body = e.response.json()
                if "error" in error_body:
                    error_detail = error_body["error"].get("message", str(error_body["error"]))
            except:
                error_detail = e.response.text[:500] if e.response.text else str(e)
            raise ValueError(f"Speech-to-text API error: {error_detail}")
        except httpx.RequestError as e:
            raise ValueError(f"Request to speech-to-text API failed: {str(e)}")

