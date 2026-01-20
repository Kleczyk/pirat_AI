"""
GPT Audio TTS service via OpenRouter API
Supports streaming audio generation
"""
import httpx
import base64
import json
from typing import Optional, AsyncIterator, Dict, Any, List
from backend.config import settings
from backend.services.elevenlabs_service import ElevenLabsService


class GPTAudioService:
    """Service for GPT Audio text-to-speech via OpenRouter"""
    
    def __init__(self):
        self.api_key = settings.openrouter_api_key
        self.base_url = settings.openrouter_base_url
        self.model = settings.gpt_audio_model
        self.audio_format = settings.gpt_audio_format
        self.use_tts_only = settings.use_tts_only
        self.tts_model = settings.tts_model
        self.tts_voice = settings.tts_voice
        self.tts_format = settings.tts_format
        self.elevenlabs_service = ElevenLabsService()

    async def generate_tts_audio(self, text: str) -> bytes:
        """
        Generate complete TTS audio using Kie.ai (ElevenLabs).
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")

        audio_url = await self.elevenlabs_service.generate_speech(
            text=text.strip(),
            wait_for_completion=True
        )
        if not audio_url:
            raise ValueError("Kie.ai TTS error: No audio URL returned")

        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream("GET", audio_url) as response:
                response.raise_for_status()
                audio_bytes = await response.aread()
                if not audio_bytes:
                    raise ValueError("Kie.ai TTS error: Empty audio content")
                return audio_bytes
        
    async def generate_audio_stream(
        self,
        text: str,
        voice: Optional[str] = None
    ) -> AsyncIterator[bytes]:
        """
        Generate audio stream from text using GPT Audio via OpenRouter
        
        Args:
            text: Text to convert to speech
            voice: Voice name (optional, if supported by model)
            
        Yields:
            Audio chunks as bytes (decoded from base64)
        """
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY not set in environment")
            
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")
            
        # If using TTS-only, generate audio via Kie.ai and stream chunks
        if self.use_tts_only:
            audio_bytes = await self.generate_tts_audio(text)
            chunk_size = 16384
            for i in range(0, len(audio_bytes), chunk_size):
                yield audio_bytes[i:i + chunk_size]
            return

        # Build messages for GPT Audio
        # GPT Audio expects text in messages format
        messages = [
            {
                "role": "user",
                "content": text.strip()
            }
        ]
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://github.com/your-repo",
            "X-Title": "Outwit the AI Pirate Game",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "modalities": ["text", "audio"],  # Required for GPT Audio to generate audio output
            "audio": {
                "voice": settings.gpt_audio_voice or "alloy",
                "format": self.audio_format  # Must be pcm16 when stream=True per provider
            }
        }
        
        # Override voice if specified
        if voice:
            payload["audio"]["voice"] = voice

        # Provider requirement: streaming audio only supports pcm16
        if payload["audio"]["format"] != "pcm16":
            print(f"[GPT Audio] Overriding audio.format '{payload['audio']['format']}' -> 'pcm16' for stream=true")
            payload["audio"]["format"] = "pcm16"
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/chat/completions",
                    json=payload,
                    headers=headers
                ) as response:
                    if response.status_code != 200:
                        error_bytes = await response.aread()
                        error_text = error_bytes.decode("utf-8", errors="replace")[:1000]
                        print(f"[GPT Audio] Non-200 response ({response.status_code}): {error_text}")
                        raise ValueError(f"GPT Audio API error: HTTP {response.status_code}: {error_text}")
                    
                    response.raise_for_status()
                    
                    chunk_count = 0
                    line_count = 0
                    async for line in response.aiter_lines():
                        line_count += 1
                        if not line.strip():
                            continue
                            
                        # Parse SSE format: "data: {...}"
                        if line.startswith("data: "):
                            data_str = line[6:]  # Remove "data: " prefix
                            
                            if data_str == "[DONE]":
                                print(f"[GPT Audio] Stream completed. Total chunks: {chunk_count}, Total lines: {line_count}")
                                break
                                
                            try:
                                data = json.loads(data_str)
                                
                                # Debug: log full structure for first few chunks
                                if chunk_count < 2:
                                    print(f"[GPT Audio] Raw data keys: {list(data.keys())}")
                                
                                choices = data.get("choices", [])
                                
                                if choices:
                                    delta = choices[0].get("delta", {})
                                    
                                    # Debug: log delta structure
                                    if chunk_count < 3:  # Log first 3 chunks for debugging
                                        print(f"[GPT Audio] Chunk {chunk_count} delta keys: {list(delta.keys())}")
                                        if "audio" not in delta:
                                            print(f"[GPT Audio] Chunk {chunk_count} full delta: {delta}")
                                    
                                    # Check for audio data - format: {"audio": {"id": "...", "data": "base64...", "transcript": "..."}}
                                    audio_data = delta.get("audio")
                                    if audio_data:
                                        chunk_count += 1
                                        # Audio should be a dict with "id", "data", "transcript"
                                        if isinstance(audio_data, dict):
                                            # Format: {"id": "...", "data": "base64...", "transcript": "..."}
                                            audio_base64 = audio_data.get("data", "")
                                            if audio_base64:
                                                try:
                                                    audio_bytes = base64.b64decode(audio_base64)
                                                    print(f"[GPT Audio] ✅ Decoded audio chunk {chunk_count}, size: {len(audio_bytes)} bytes")
                                                    yield audio_bytes
                                                except Exception as e:
                                                    print(f"[GPT Audio] ❌ Failed to decode base64 audio: {e}")
                                                    continue
                                            else:
                                                print(f"[GPT Audio] ⚠️ Audio dict has no 'data' field. Keys: {list(audio_data.keys())}")
                                        elif isinstance(audio_data, str):
                                            # Direct base64 string (fallback)
                                            try:
                                                audio_bytes = base64.b64decode(audio_data)
                                                print(f"[GPT Audio] ✅ Decoded audio chunk {chunk_count} (string format), size: {len(audio_bytes)} bytes")
                                                yield audio_bytes
                                            except Exception as e:
                                                print(f"[GPT Audio] ❌ Failed to decode base64 audio string: {e}")
                                                continue
                                    else:
                                        # Check for other content types - might be text-only response
                                        if "content" in delta:
                                            if chunk_count < 3:
                                                print(f"[GPT Audio] ⚠️ Chunk {chunk_count} has text content only, no audio. Delta keys: {list(delta.keys())}")
                                        # Check if this is the first chunk with model info
                                        if "role" in delta and chunk_count == 0:
                                            print(f"[GPT Audio] First chunk - role: {delta.get('role')}")
                                    
                                    # Also check for transcript (optional)
                                    transcript = delta.get("transcript", "")
                                    if transcript:
                                        if chunk_count < 3:
                                            print(f"[GPT Audio] Transcript chunk: {transcript[:50]}")
                                        
                            except json.JSONDecodeError as e:
                                print(f"[GPT Audio] Failed to parse JSON: {e}, line: {line[:200]}")
                                continue
                    
                    if chunk_count == 0:
                        print(f"[GPT Audio] WARNING: No audio chunks received!")
                                
            except httpx.HTTPStatusError as e:
                error_detail = f"HTTP {e.response.status_code}"
                try:
                    # Read error response if possible
                    if hasattr(e.response, 'read'):
                        try:
                            error_text = e.response.read().decode('utf-8')[:500]
                            try:
                                error_body = json.loads(error_text)
                                if "error" in error_body:
                                    error_detail = error_body["error"].get("message", str(error_body["error"]))
                                elif "detail" in error_body:
                                    error_detail = error_body["detail"]
                                else:
                                    error_detail = error_text
                            except:
                                error_detail = error_text
                        except:
                            error_detail = str(e)
                    else:
                        error_detail = str(e)
                except Exception as read_error:
                    print(f"[GPT Audio] Could not read error response: {read_error}")
                    error_detail = f"HTTP {e.response.status_code}: {str(e)}"
                raise ValueError(f"GPT Audio API error: {error_detail}")
            except httpx.RequestError as e:
                raise ValueError(f"Request to GPT Audio API failed: {str(e)}")
            except Exception as e:
                print(f"[GPT Audio] Unexpected error in generate_audio_stream: {e}")
                import traceback
                traceback.print_exc()
                raise
    
    async def generate_audio_complete(
        self,
        text: str,
        voice: Optional[str] = None
    ) -> bytes:
        """
        Generate complete audio (non-streaming) - accumulates all chunks
        
        Args:
            text: Text to convert to speech
            voice: Voice name (optional)
            
        Returns:
            Complete audio file as bytes
        """
        audio_chunks = []
        async for chunk in self.generate_audio_stream(text, voice):
            audio_chunks.append(chunk)
        
        # Combine all chunks
        return b"".join(audio_chunks)
