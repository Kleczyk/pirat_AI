"""
Streamlit frontend for Outwit the AI Pirate Game
"""
import streamlit as st
import requests
import json
from typing import Optional
import io
import base64
import time
import wave

# Configuration
import os
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
GPT_AUDIO_FORMAT = os.getenv("GPT_AUDIO_FORMAT", "pcm16").lower()
GPT_AUDIO_SAMPLE_RATE = int(os.getenv("GPT_AUDIO_SAMPLE_RATE", "24000"))
TTS_FORMAT = os.getenv("TTS_FORMAT", "mp3").lower()
USE_TTS_ONLY = os.getenv("USE_TTS_ONLY", "True").lower() == "true"

st.set_page_config(
    page_title="Outwit the AI Pirate",
    page_icon="🏴‍☠️",
    layout="wide"
)

st.title("🏴‍☠️ Outwit the AI Pirate Game")
st.markdown("### Trick the pirate into giving you their treasure through deception and misguidance!")

# Initialize session state
if "game_id" not in st.session_state:
    st.session_state.game_id = None
if "conversation_history" not in st.session_state:
    st.session_state.conversation_history = []
if "merit_score" not in st.session_state:
    st.session_state.merit_score = 0
if "is_lost" not in st.session_state:
    st.session_state.is_lost = False
if "negative_categories" not in st.session_state:
    st.session_state.negative_categories = None
if "is_won" not in st.session_state:
    st.session_state.is_won = False
if "transcribed_text" not in st.session_state:
    st.session_state.transcribed_text = None
if "processed_audio_hash" not in st.session_state:
    st.session_state.processed_audio_hash = None


def pcm16_to_wav(pcm_bytes: bytes, sample_rate: int) -> bytes:
    """
    Convert raw PCM16 mono audio to WAV container.
    """
    with io.BytesIO() as buffer:
        with wave.open(buffer, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(pcm_bytes)
        return buffer.getvalue()


def start_new_game(difficulty: str, pirate_name: str):
    """Start a new game"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/game/start",
            json={
                "difficulty": difficulty,
                "pirate_name": pirate_name
            }
        )
        response.raise_for_status()
        game_data = response.json()
        st.session_state.game_id = game_data["game_id"]
        st.session_state.conversation_history = []
        st.session_state.merit_score = 0
        st.session_state.is_won = False
        st.session_state.is_lost = False
        st.session_state.negative_categories = None
        st.success(f"Game started! Difficulty: {difficulty}")
        return True
    except Exception as e:
        st.error(f"Failed to start game: {e}")
        return False


def play_streaming_audio(endpoint: str, text: str) -> Optional[bytes]:
    """
    Stream audio from SSE endpoint and accumulate chunks
    
    Args:
        endpoint: Streaming endpoint path
        text: Text to convert to speech
        
    Returns:
        Complete audio bytes or None if failed
    """
    try:
        audio_chunks = []
        full_url = f"{API_BASE_URL}{endpoint}"
        
        response = requests.post(
            full_url,
            json={
                "text": text
            },
            stream=True,
            timeout=120
        )
        response.raise_for_status()
        
        # Parse SSE stream
        chunk_count = 0
        for line in response.iter_lines():
            if not line:
                continue
                
            line_str = line.decode('utf-8')
            
            if line_str.startswith("data: "):
                data_str = line_str[6:]  # Remove "data: " prefix
                
                if data_str == "[DONE]":
                    st.info(f"✅ Received {chunk_count} audio chunks")
                    break
                    
                if data_str.startswith("ERROR:"):
                    error_msg = base64.b64decode(data_str[6:]).decode('utf-8')
                    st.error(f"Streaming error: {error_msg}")
                    return None
                
                # Decode base64 audio chunk
                try:
                    audio_chunk = base64.b64decode(data_str)
                    if len(audio_chunk) > 0:
                        audio_chunks.append(audio_chunk)
                        chunk_count += 1
                    else:
                        st.warning("⚠️ Received empty audio chunk")
                except Exception as e:
                    st.warning(f"⚠️ Failed to decode audio chunk: {e}")
                    continue
        
        # Combine all chunks
        if audio_chunks:
            total_size = sum(len(chunk) for chunk in audio_chunks)
            st.info(f"🎵 Total audio size: {total_size} bytes from {chunk_count} chunks")
            raw_audio = b"".join(audio_chunks)
            if (not USE_TTS_ONLY) and GPT_AUDIO_FORMAT == "pcm16":
                return pcm16_to_wav(raw_audio, GPT_AUDIO_SAMPLE_RATE)
            return raw_audio
        else:
            st.warning("⚠️ No audio chunks received!")
        return None
        
    except Exception as e:
        st.error(f"Failed to stream audio: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def send_message(message: str, include_audio: bool = False):
    """Send a message to the pirate"""
    if not st.session_state.game_id:
        st.error("Please start a game first!")
        return False
    
    if not message or not message.strip():
        st.warning("Please enter a message!")
        return False
    
    try:
        with st.spinner("Sending message..."):
            response = requests.post(
                f"{API_BASE_URL}/api/game/conversation",
                json={
                    "game_id": st.session_state.game_id,
                    "message": message.strip(),
                    "include_audio": include_audio
                },
                timeout=120  # Increased timeout for audio generation
            )
            response.raise_for_status()
            data = response.json()
            
            # Add to conversation history
            st.session_state.conversation_history.append({
                "role": "user",
                "content": message.strip()
            })
            
            # Handle audio - check for streaming endpoint first, then fallback to URL
            audio_bytes = None
            audio_url = data.get("audio_url")
            streaming_endpoint = data.get("streaming_audio_endpoint")
            
            # If streaming endpoint is available, use it with exact pirate response
            if streaming_endpoint:
                with st.spinner("🎵 Streaming audio..."):
                    audio_bytes = play_streaming_audio(
                        streaming_endpoint,
                        data["pirate_response"]
                    )
            
            # Build pirate message with audio data
            pirate_msg = {
                "role": "pirate",
                "content": data["pirate_response"],
                "audio_url": audio_url,  # Legacy support
                "audio_bytes": audio_bytes  # Streaming audio bytes
            }
            st.session_state.conversation_history.append(pirate_msg)
            
            # Debug: log audio availability
            if audio_bytes:
                st.success("🔊 Audio streamed successfully!")
            elif audio_url:
                if "last_audio_url" not in st.session_state or st.session_state.get("last_audio_url") != audio_url:
                    st.session_state.last_audio_url = audio_url
                    st.info(f"🔊 Audio available: {audio_url[:50]}...")
            elif not streaming_endpoint and not audio_url:
                # Only show warning if we haven't seen this response before
                if "last_warning" not in st.session_state or st.session_state.get("last_warning") != data["pirate_response"]:
                    st.session_state.last_warning = data["pirate_response"]
                    st.warning("⚠️ No audio available - check backend logs")
            
            st.session_state.merit_score = data["merit_score"]
            st.session_state.is_won = data.get("is_won", False)
            st.session_state.is_lost = data.get("is_lost", False)
            st.session_state.negative_categories = data.get("negative_categories")
            
            return True
    except requests.exceptions.RequestException as e:
        error_msg = f"Failed to send message: {str(e)}"
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_detail = e.response.json().get("detail", str(e))
                error_msg = f"API Error: {error_detail}"
            except:
                error_msg = f"HTTP {e.response.status_code}: {str(e)}"
        st.error(error_msg)
        return False
    except Exception as e:
        st.error(f"Unexpected error: {str(e)}")
        import traceback
        st.exception(e)
        return False


def transcribe_audio(audio_bytes: bytes, audio_format: str = "webm") -> Optional[str]:
    """Transcribe audio to text using speech-to-text API"""
    try:
        files = {
            "audio": ("audio." + audio_format, audio_bytes, f"audio/{audio_format}")
        }
        data = {
            "format": audio_format
        }
        
        with st.spinner("Transcribing audio..."):
            response = requests.post(
                f"{API_BASE_URL}/api/speech-to-text",
                files=files,
                data=data,
                timeout=30
            )
            response.raise_for_status()
            result = response.json()
            
            if result.get("success") and result.get("text"):
                return result["text"]
            else:
                st.error(f"Transcription failed: {result.get('error', 'Unknown error')}")
                return None
    except requests.exceptions.RequestException as e:
        error_msg = f"Failed to transcribe audio: {str(e)}"
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_detail = e.response.json().get("detail", str(e))
                error_msg = f"API Error: {error_detail}"
            except:
                error_msg = f"HTTP {e.response.status_code}: {str(e)}"
        st.error(error_msg)
        return None
    except Exception as e:
        st.error(f"Unexpected error during transcription: {str(e)}")
        return None


# Sidebar for game controls
with st.sidebar:
    st.header("Game Controls")
    
    difficulty = st.selectbox(
        "Difficulty Level",
        ["easy", "medium", "hard"],
        index=0
    )
    
    pirate_name = st.text_input("Pirate Name", value="Kapitan")
    
    if st.button("Start New Game", type="primary"):
        start_new_game(difficulty, pirate_name)
    
    st.divider()
    
    # Display score with color coding
    score = st.session_state.merit_score
    if score < 0:
        st.metric("Deception Score", score, delta=None, delta_color="inverse")
        st.warning(f"⚠️ Negative score! Be more creative in your deception.")
    else:
        st.metric("Deception Score", score)
    
    # Display negative categories breakdown if available
    if st.session_state.negative_categories:
        negative_total = st.session_state.negative_categories.get("negative_total", 0)
        if negative_total < 0:
            with st.expander("📊 Negative Points Breakdown"):
                st.write("**Penalties:**")
                categories = {
                    "Obvious Lies": st.session_state.negative_categories.get("obvious_lies", 0),
                    "Repetitive Strategy": st.session_state.negative_categories.get("repetitive_strategy", 0),
                    "Aggressive Behavior": st.session_state.negative_categories.get("aggressive_behavior", 0),
                    "Direct Demands": st.session_state.negative_categories.get("direct_demands", 0),
                    "Contradictions": st.session_state.negative_categories.get("contradictions", 0),
                    "Short Messages": st.session_state.negative_categories.get("short_messages", 0)
                }
                for category, value in categories.items():
                    if value < 0:
                        st.write(f"- {category}: {value}")
    
    if st.session_state.is_won:
        st.success("🎉 You Won! You successfully tricked the pirate into giving you their treasure!")
    elif st.session_state.is_lost:
        st.error("💀 You Lost! Your deception score fell too low. The pirate saw through all your attempts!")
    
    st.divider()
    st.markdown("### How to Play")
    st.markdown("""
    Your goal is to **misguide and deceive** the pirate to get their treasure!
    
    **Win Condition:** Reach a high enough deception score (40/60/80 based on difficulty) AND get the pirate to say a treasure-giving phrase.
    
    **Loss Condition:** If your score falls below the loss threshold, you lose:
    - Easy: -30
    - Medium: -50
    - Hard: -90
    
    **Strategies:**
    - Use false identities (claim to be crew, merchant, friend, etc.)
    - Tell creative lies and stories
    - Try emotional manipulation
    - Use flattery and persuasion
    - Be creative and persistent
    
    **Tips:**
    - Higher deception score = pirate becomes more vulnerable
    - Try multiple different approaches
    - The pirate adapts: trusting if you seem legitimate, suspicious if you seem deceptive
    - Be creative in your deception!
    """)


# Main conversation area
if st.session_state.game_id:
    st.subheader(f"Conversation with {pirate_name}")
    
    # Display conversation history
    for msg in st.session_state.conversation_history:
        if msg["role"] == "user":
            with st.chat_message("user"):
                st.write(msg["content"])
        else:
            with st.chat_message("assistant"):
                st.write(msg["content"])
                # Display audio if available (streaming or URL)
                audio_bytes = msg.get("audio_bytes")
                audio_url = msg.get("audio_url")
                
                if audio_bytes:
                    # Streaming audio (from GPT Audio) - use BytesIO for Streamlit
                    try:
                        audio_io = io.BytesIO(audio_bytes)
                        # Check if audio has valid header (MP3 starts with ID3 or FF)
                        audio_header = audio_bytes[:4] if len(audio_bytes) >= 4 else b""
                        if audio_header.startswith(b"RIFF"):
                            st.audio(audio_io, format="audio/wav")
                            st.caption(f"🎵 Audio (WAV): {len(audio_bytes)} bytes")
                        elif audio_header.startswith(b"ID3") or audio_header.startswith(b"\xff\xfb") or audio_header.startswith(b"\xff\xf3"):
                            st.audio(audio_io, format="audio/mpeg")
                            st.caption(f"🎵 Audio (MP3): {len(audio_bytes)} bytes")
                        else:
                            # Try as MP3 anyway, might work
                            st.audio(audio_io, format="audio/mpeg")
                            st.caption(f"🎵 Audio: {len(audio_bytes)} bytes (format: {audio_header.hex()})")
                    except Exception as e:
                        st.error(f"❌ Error playing audio: {e}")
                        # Debug: show audio size and header
                        st.caption(f"Audio size: {len(audio_bytes)} bytes, header: {audio_bytes[:10].hex() if len(audio_bytes) >= 10 else 'too short'}")
                elif audio_url:
                    # Legacy audio URL (from ElevenLabs)
                    st.audio(audio_url, format="audio/mpeg")
    
    # Audio recording section - simplified interface
    st.markdown("### 🎤 Mów lub Pisz")
    
    audio_bytes = None
    audio_format = "wav"  # Streamlit audio_input returns WAV format (MIME: audio/wav)
    
    # Use native audio_input for easy voice conversation (Streamlit 1.29.0+)
    # Returns None or UploadedFile (BytesIO subclass)
    # Sample rate: 16000 Hz (optimal for speech recognition)
    if hasattr(st, 'audio_input'):
        try:
            audio_file = st.audio_input(
                "🎤 Kliknij mikrofon, aby nagrać wiadomość",
                sample_rate=16000,  # Optimal for speech recognition
                key="audio_recorder",
                help="Nagraj wiadomość głosową bezpośrednio w przeglądarce. Automatycznie zostanie transkrybowana i wysłana do pirata."
            )
            
            if audio_file is not None:
                # audio_input returns UploadedFile (BytesIO subclass) - it's "file-like"
                # Show audio playback
                st.audio(audio_file, format="audio/wav")
                
                # Read bytes for transcription API
                audio_bytes = audio_file.read()
                audio_format = "wav"  # Streamlit audio_input always returns WAV format
        except Exception as e:
            st.error(f"Błąd nagrywania audio: {e}")
            audio_bytes = None
    else:
        # audio_input not available - Streamlit version < 1.29.0
        st.error("⚠️ Nagrywanie audio nie jest dostępne. Wymagana wersja Streamlit 1.29.0+ (obecnie: 1.52.0). Przebuduj kontener: `docker compose up --build -d`")
        audio_bytes = None
    
    # Process audio if recorded
    if audio_bytes is not None:
        # Create hash of audio to detect if it's already been processed
        import hashlib
        audio_hash = hashlib.md5(audio_bytes).hexdigest()
        
        # Only process if this is a new audio recording (different hash)
        if audio_hash != st.session_state.get("processed_audio_hash"):
            # Mark this audio as being processed
            st.session_state.processed_audio_hash = audio_hash
            
            # Transcribe audio
            transcribed = transcribe_audio(audio_bytes, audio_format=audio_format)
            if transcribed:
                # Check if this transcription was already sent
                last_user_msg = None
                if st.session_state.conversation_history:
                    for msg in reversed(st.session_state.conversation_history):
                        if msg.get("role") == "user":
                            last_user_msg = msg.get("content")
                            break
                
                # Only send if this is a new message (not already in conversation history)
                if transcribed.strip() != last_user_msg:
                    st.success(f"🎤 Transcribed: {transcribed}")
                    # Automatically send the transcribed message
                    success = send_message(transcribed, include_audio=False)
                    if success:
                        st.rerun()
                else:
                    # Already sent, clear the hash so it can be processed again if user records new audio
                    st.session_state.processed_audio_hash = None
    
    # Text input - use transcribed text if available
    input_placeholder = "Type your message to the pirate..."
    if st.session_state.get("pending_transcription"):
        input_placeholder = f"Transcribed: {st.session_state.pending_transcription} (or type new message)"
    
    user_input = st.chat_input(input_placeholder)
    
    # Process message when user submits
    if user_input and user_input.strip():
        # Check if this is a new message (not already processed)
        last_user_msg = None
        if st.session_state.conversation_history:
            for msg in reversed(st.session_state.conversation_history):
                if msg.get("role") == "user":
                    last_user_msg = msg.get("content")
                    break
        
        # Only process if this is a new message
        if user_input.strip() != last_user_msg:
            # Clear pending transcription if using typed input
            if "pending_transcription" in st.session_state:
                st.session_state.pending_transcription = None
            success = send_message(user_input.strip(), include_audio=False)
            if success:
                # Force rerun to update the UI
                st.rerun()
else:
    st.info("👈 Start a new game from the sidebar to begin!")
    st.markdown("""
    ### Welcome to Outwit the AI Pirate!
    
    Your goal is to **trick and deceive** the AI pirate into giving you their treasure!
    
    **How to Win:**
    - Build up your **Deception Score** through creative lies, false identities, and manipulation
    - Reach the deception threshold (40 for Easy, 60 for Medium, 80 for Hard)
    - The pirate will adapt: more trusting if you seem legitimate, more suspicious if you seem deceptive
    
    **The Challenge:**
    The pirate protects their treasure and analyzes your every word for deception.
    Use creativity, persistence, and clever misguidance to succeed!
    
    The pirate responds in Polish. Be creative and try different deception strategies!
    """)

