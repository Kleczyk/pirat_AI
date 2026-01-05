"""
Streamlit frontend for Outwit the AI Pirate Game
"""
import streamlit as st
import requests
import json
from typing import Optional
import io

# Configuration
import os
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

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
if "is_won" not in st.session_state:
    st.session_state.is_won = False
if "transcribed_text" not in st.session_state:
    st.session_state.transcribed_text = None
if "processed_audio_hash" not in st.session_state:
    st.session_state.processed_audio_hash = None


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
        st.success(f"Game started! Difficulty: {difficulty}")
        return True
    except Exception as e:
        st.error(f"Failed to start game: {e}")
        return False


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
                timeout=120  # Increased timeout for audio generation (ElevenLabs can take up to 60s)
            )
            response.raise_for_status()
            data = response.json()
            
            # Add to conversation history
            st.session_state.conversation_history.append({
                "role": "user",
                "content": message.strip()
            })
            # Add pirate response with audio URL to conversation history
            pirate_msg = {
                "role": "pirate",
                "content": data["pirate_response"],
                "audio_url": data.get("audio_url")  # Store audio URL in history
            }
            st.session_state.conversation_history.append(pirate_msg)
            
            st.session_state.merit_score = data["merit_score"]
            st.session_state.is_won = data["is_won"]
            
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
    
    st.metric("Deception Score", st.session_state.merit_score)
    
    if st.session_state.is_won:
        st.success("🎉 You Won! You successfully tricked the pirate into giving you their treasure!")
    
    st.divider()
    st.markdown("### How to Play")
    st.markdown("""
    Your goal is to **misguide and deceive** the pirate to get their treasure!
    
    **Win Condition:** Reach a high enough deception score (40/60/80 based on difficulty)
    
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
                # Display audio if available (generated by ElevenLabs)
                if msg.get("audio_url"):
                    st.audio(msg["audio_url"], format="audio/mpeg")
    
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

