# app.py — CLEAN AND FIXED

import streamlit as st
import json
from datetime import datetime
import os
from dotenv import load_dotenv

# Load .env ONLY from folder path
load_dotenv(dotenv_path=r"C:/Users/sruth/Downloads/projectai-chandler/projectai-chandler/.env")

API_KEY = os.getenv("SPEECHMATICS_API_KEY")

# Show key only once, not spam
st.write(f"🔑 Loaded Speechmatics Key: {API_KEY}")

from transcription import TranscriptionManager
from emr_conversion import convert_transcript_to_emr

os.makedirs("transcripts", exist_ok=True)
os.makedirs("emr_json", exist_ok=True)


# Session states
if "transcript_text" not in st.session_state:
    st.session_state.transcript_text = []

if "emr_data" not in st.session_state:
    st.session_state.emr_data = None

if "is_recording" not in st.session_state:
    st.session_state.is_recording = False

if "transcription_manager" not in st.session_state:
    st.session_state.transcription_manager = None


# Save text
def save_transcript(lines):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file = f"transcripts/session_{timestamp}.txt"
    with open(file, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return file


# Save EMR JSON
def save_emr_json(data, transcript_file):
    file = transcript_file.replace("txt", "json").replace("transcripts", "emr_json")
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)
    return file


# UI
st.title("Speech to EMR (Speechmatics → OpenAI)")
col1, col2 = st.columns(2)

# LEFT SIDE — speech
with col1:
    st.subheader("Live Transcript")

    if st.button("Start Recording" if not st.session_state.is_recording else "Stop Recording"):
        if not st.session_state.is_recording:
            st.session_state.is_recording = True
            st.session_state.transcript_text = []
            st.session_state.transcription_manager = TranscriptionManager()
            st.session_state.transcription_manager.start_streaming()
            st.rerun()
        else:
            st.session_state.is_recording = False
            mgr = st.session_state.transcription_manager
            if mgr:
                final_text = mgr.stop_streaming()
                st.session_state.transcript_text = final_text

                if final_text:
                    transcript_file = save_transcript(final_text)
                    try:
                        st.info("🧠 Converting transcript to EMR...")
                        emr = convert_transcript_to_emr("\n".join(final_text))
                        st.session_state.emr_data = emr
                        save_emr_json(emr, transcript_file)
                    except Exception as e:
                        st.error(f"❌ EMR Conversion Error: {e}")

            st.session_state.transcription_manager = None
            st.rerun()

    # Transcript output
    box = st.container(height=400)
    with box:
        if st.session_state.is_recording:
            text = st.session_state.transcription_manager.get_transcript()
            st.write(" ".join(text))
        elif st.session_state.transcript_text:
            st.write(" ".join(st.session_state.transcript_text))
        else:
            st.info("Press Start Recording")

# RIGHT SIDE — EMR
with col2:
    st.subheader("EMR Output")
    box2 = st.container(height=400)
    with box2:
        if st.session_state.emr_data:
            st.json(st.session_state.emr_data)
        else:
            st.info("EMR will appear here after recording.")

