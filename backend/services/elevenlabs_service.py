"""
ElevenLabs TTS service via Kie.ai API
"""
import httpx
import asyncio
from typing import Optional
from backend.config import settings, ELEVENLABS_VOICES


class ElevenLabsService:
    """Service for ElevenLabs text-to-speech via Kie.ai"""
    
    def __init__(self):
        self.api_key = settings.kie_ai_api_key
        self.base_url = "https://api.kie.ai/api/v1"
        self.model = settings.elevenlabs_model
        self.default_voice = settings.elevenlabs_voice
        self.language_code = settings.elevenlabs_language_code
        
    async def create_tts_task(
        self,
        text: str,
        voice: Optional[str] = None,
        stability: float = 0.5,
        similarity_boost: float = 0.75,
        style: float = 0.0,
        speed: float = 1.0,
        callback_url: Optional[str] = None
    ) -> dict:
        """
        Create a TTS task via Kie.ai API
        
        Args:
            text: Text to convert to speech (max 5000 chars)
            voice: Voice name (default from config)
            stability: Voice stability (0-1)
            similarity_boost: Similarity boost (0-1)
            style: Style exaggeration (0-1)
            speed: Speech speed (0.7-1.2)
            callback_url: Optional callback URL for completion
            
        Returns:
            Task creation response with taskId
        """
        if not self.api_key:
            raise ValueError("KIE_AI_API_KEY not set in environment")
            
        if len(text) > 5000:
            raise ValueError("Text exceeds 5000 character limit")
            
        voice = voice or self.default_voice
        if voice not in ELEVENLABS_VOICES:
            voice = self.default_voice
            
        payload = {
            "model": self.model,
            "input": {
                "text": text,
                "voice": voice,
                "stability": stability,
                "similarity_boost": similarity_boost,
                "style": style,
                "speed": speed,
                "timestamps": False,
                "language_code": self.language_code
            }
        }
        
        if callback_url:
            payload["callBackUrl"] = callback_url
            
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/jobs/createTask",
                json=payload,
                headers=headers
            )
            response.raise_for_status()
            return response.json()
    
    async def get_task_status(self, task_id: str) -> dict:
        """
        Get status of a TTS task
        
        Args:
            task_id: Task identifier from create_tts_task
            
        Returns:
            Task status and result if completed
        """
        if not self.api_key:
            raise ValueError("KIE_AI_API_KEY not set in environment")
            
        headers = {
            "Authorization": f"Bearer {self.api_key}"
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.base_url}/jobs/recordInfo",
                params={"taskId": task_id},
                headers=headers
            )
            response.raise_for_status()
            return response.json()
    
    async def generate_speech(
        self,
        text: str,
        voice: Optional[str] = None,
        wait_for_completion: bool = True,
        max_wait_time: int = 60
    ) -> Optional[str]:
        """
        Generate speech and wait for completion
        
        Args:
            text: Text to convert to speech
            voice: Voice name (optional)
            wait_for_completion: Whether to wait for task completion
            max_wait_time: Maximum seconds to wait
            
        Returns:
            Audio URL if completed, None if async
        """
        # Create task
        task_response = await self.create_tts_task(text, voice=voice)
        task_id = task_response.get("data", {}).get("taskId")
        
        if not task_id:
            raise ValueError("Failed to create TTS task")
            
        if not wait_for_completion:
            return None  # Return task_id for async processing
            
        # Poll for completion
        import time
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            status_response = await self.get_task_status(task_id)
            data = status_response.get("data", {})
            state = data.get("state")
            
            if state == "success":
                result_json = data.get("resultJson", "{}")
                import json
                result = json.loads(result_json)
                result_urls = result.get("resultUrls", [])
                if result_urls:
                    return result_urls[0]  # Return first audio URL
                    
            elif state == "failed":
                fail_msg = data.get("failMsg", "Unknown error")
                raise Exception(f"TTS task failed: {fail_msg}")
                
            # Wait before next poll
            await asyncio.sleep(2)
            
        raise TimeoutError(f"TTS task did not complete within {max_wait_time} seconds")







