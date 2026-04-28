import streamlit as st
import requests
import pdfplumber
import base64
import json
import os
import platform

# Cloud detection
IS_CLOUD = os.environ.get("STREAMLIT_SHARING_MODE") is not None or \
           "streamlit" in os.environ.get("HOME", "").lower() or \
           os.environ.get("IS_CLOUD", "false").lower() == "true"

# Only import voice libs if running locally
if not IS_CLOUD:
    try:
        import sounddevice as sd
        import soundfile as sf
        import numpy as np
        import tempfile
        import whisper
        VOICE_INPUT_AVAILABLE = True
    except ImportError:
        VOICE_INPUT_AVAILABLE = False
else:
    VOICE_INPUT_AVAILABLE = False

try:
    from elevenlabs.client import ElevenLabs
    VOICE_OUTPUT_AVAILABLE = True
except ImportError:
    VOICE_OUTPUT_AVAILABLE = False

try:
    from database import (
        get_or_create_user, create_session, complete_session,
        save_qa, save_final_scores, get_user_history, get_session_qa
    )
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False

# ── Configuration ───────────────────────────────────────
N8N_BASE_URL = st.secrets.get("N8N_BASE_URL", "https://n8n-production-1cf5.up.railway.app/webhook")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
MAX_QUESTIONS = 5

st.set_page_config(
    page_title="AI Interview Simulator",
    page_icon="🎤",
    layout="wide"
)

# ── Session State Init ──────────────────────────────────
for key, val in {
    "user_id": None,
    "user_name": None,
    "session_id": None,
    "started": False,
    "history": [],
    "finished": False,
    "q_count": 0,
    "scores": [],
    "resume_text": "",
    "scores_saved": False,
    "current_audio": None,
    "voice_input": None
}.items():
    if key not in st.session_state:
        st.session_state[key] = val

# ── User Login Screen ───────────────────────────────────
if not st.session_state.user_id:
    st.title("🎤 AI Interview Simulator")
    st.subheader("Enter your details to begin")

    col1, col2 = st.columns(2)
    with col1:
        name = st.text_input("Your Name")
    with col2:
        email = st.text_input("Your Email")

    if st.button("Continue →", type="primary"):
        if name and email:
            if DB_AVAILABLE:
                user_id = get_or_create_user(name, email)
            else:
                user_id = f"user_{name.lower().replace(' ', '_')}"
            if user_id:
                st.session_state.user_id = user_id
                st.session_state.user_name = name
                st.rerun()
        else:
            st.warning("Please enter both name and email")
    st.stop()

# ════════════════════════════════════════════════════════
# VOICE OUTPUT — ElevenLabs TTS
# ════════════════════════════════════════════════════════
def speak_question(text: str):
    if not VOICE_OUTPUT_AVAILABLE:
        return
    try:
        client = ElevenLabs(
            api_key=st.secrets.get("ELEVENLABS_KEY", "")
        )
        audio = client.text_to_speech.convert(
            voice_id="pNInz6obpgDQGcFmaJgB",
            text=text,
            model_id="eleven_turbo_v2_5",
            output_format="mp3_44100_128"
        )
        audio_bytes = b"".join(audio)
        audio_b64 = base64.b64encode(audio_bytes).decode()
        st.session_state.current_audio = audio_b64
    except Exception as e:
        st.warning(f"Voice unavailable: {str(e)}")

def display_audio():
    if st.session_state.current_audio:
        st.markdown(
            f'<audio controls autoplay>'
            f'<source src="data:audio/mp3;base64,{st.session_state.current_audio}" '
            f'type="audio/mp3"></audio>',
            unsafe_allow_html=True
        )

# ════════════════════════════════════════════════════════
# VOICE INPUT — Whisper STT (local only)
# ════════════════════════════════════════════════════════
if VOICE_INPUT_AVAILABLE:
    @st.cache_resource
    def load_whisper_model():
        return whisper.load_model("base")

    def record_answer(duration: int = 10) -> str:
        try:
            model = load_whisper_model()
            sample_rate = 16000
            recording = sd.rec(
                int(duration * sample_rate),
                samplerate=sample_rate,
                channels=1,
                dtype="float32"
            )
            sd.wait()
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                temp_path = f.name
            sf.write(temp_path, recording, sample_rate)
            result = model.transcribe(temp_path, language="en", fp16=False)
            os.unlink(temp_path)
            return result["text"].strip()
        except Exception as e:
            return f"❌ Recording error: {str(e)}"

# ════════════════════════════════════════════════════════
# EMOTION ANALYSIS — Groq LLM
# ════════════════════════════════════════════════════════
def analyse_emotion(answer_text: str) -> dict:
    try:
        payload = {
            "model": "llama-3.1-8b-instant",
            "max_tokens": 150,
            "temperature": 0.3,
            "messages": [
                {
                    "role": "system",
                    "content": "You are an expert speech coach analysing interview answers for emotional signals. Respond ONLY with valid JSON, no extra text, no markdown: {\"emotion\": \"confident\", \"energy\": 7, \"nervousness\": 3, \"suggestion\": \"one sentence coaching tip here\"} emotion must be exactly one of: confident, nervous, hesitant, enthusiastic, calm, neutral. energy and nervousness are integers 1-10."
                },
                {
                    "role": "user",
                    "content": f"Analyse this interview answer for emotional signals: {answer_text}"
                }
            ]
        }
        r = requests.post(
            GROQ_API_URL,
            headers={
                "Authorization": f"Bearer {st.secrets.get('GROQ_KEY', '')}",
                "Content-Type": "application/json"
            },
            json=payload,
            timeout=15
        )
        raw = r.json()["choices"][0]["message"]["content"].strip()
        cleaned = raw.replace("```json", "").replace("```", "").strip()
        return json.loads(cleaned)
    except Exception:
        return {
            "emotion": "neutral",
            "energy": 5,
            "nervousness": 5,
            "suggestion": "Keep practising to improve your communication!"
        }

# ── Sidebar ─────────────────────────────────────────────
with st.sidebar:
    st.title("⚙️ Interview Setup")
    st.caption(f"👤 {st.session_state.user_name}")

    industry = st.selectbox(
        "Select Industry",
        ["General", "Tech / Software", "HR / People Ops", "Sales / Business Dev"]
    )

    difficulty = st.selectbox(
        "Difficulty Level",
        ["Entry Level", "Mid Level", "Senior Level"]
    )

    resume_file = st.file_uploader("Upload Your Resume (PDF)", type=["pdf"])
    if resume_file:
        resume_text = ""
        with pdfplumber.open(resume_file) as pdf:
            for page in pdf.pages:
                resume_text += page.extract_text() or ""
        st.session_state.resume_text = resume_text
        st.success("✅ Resume loaded!")
        with st.expander("Preview extracted text"):
            st.write(st.session_state.resume_text[:500] + "...")

    voice_enabled = st.toggle("🔊 Voice Output", value=True)

    if IS_CLOUD:
        st.info("🌐 Running on cloud — voice input available in local version")

    if st.button("🔄 Reset Interview"):
        for key in ["started", "history", "finished",
                    "q_count", "scores", "session_id",
                    "resume_text", "scores_saved",
                    "current_audio", "voice_input"]:
            st.session_state[key] = (
                [] if key in ["history", "scores"] else
                False if key in ["started", "finished", "scores_saved"] else
                0 if key == "q_count" else
                None if key in ["current_audio", "voice_input"] else ""
            )
        st.rerun()

    if st.button("🚪 Logout"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

# ── Helpers ──────────────────────────────────────────────
def build_history_string():
    lines = []
    q_num = 1
    for item in st.session_state.history:
        if item["role"] == "Q":
            lines.append(f"Interviewer Q{q_num}: {item['text']}")
        else:
            lines.append(f"Candidate A{q_num}: {item['text']}")
            q_num += 1
    return "\n".join(lines)

def get_next_question(user_answer: str) -> str:
    payload = {
        "user_answer": user_answer,
        "history": build_history_string(),
        "question_count": st.session_state.q_count,
        "industry": industry,
        "difficulty": difficulty,
        "resume_text": st.session_state.resume_text[:1000]
    }
    try:
        r = requests.post(f"{N8N_BASE_URL}/interview", json=payload, timeout=30)
        r.raise_for_status()
        question = r.json().get("next_question", "Could not generate question.")
        return question.lstrip("= ").strip()
    except Exception as e:
        return f"❌ Error: {str(e)}"

def get_score(question: str, answer: str) -> dict:
    payload = {"question": question, "answer": answer}
    try:
        r = requests.post(f"{N8N_BASE_URL}/score", json=payload, timeout=30)
        r.raise_for_status()
        data = r.json()
        return {
            "clarity": int(data.get("clarity", 5)),
            "confidence": int(data.get("confidence", 5)),
            "relevance": int(data.get("relevance", 5)),
            "feedback": str(data.get("feedback", "No feedback."))
        }
    except Exception as e:
        return {
            "clarity": 5, "confidence": 5,
            "relevance": 5, "feedback": f"Error: {str(e)}"
        }

def process_answer(user_input: str):
    st.session_state.current_audio = None
    st.session_state.history.append({"role": "A", "text": user_input})

    if len(st.session_state.history) >= 2:
        last_q = st.session_state.history[-2]["text"]

        with st.spinner("Analysing your answer..."):
            score = get_score(last_q, user_input)
            emotion_data = analyse_emotion(user_input)

        score["emotion"] = emotion_data.get("emotion", "neutral")
        score["energy"] = emotion_data.get("energy", 5)
        score["nervousness"] = emotion_data.get("nervousness", 5)
        score["suggestion"] = emotion_data.get("suggestion", "")

        st.session_state.scores.append(score)

        if DB_AVAILABLE and st.session_state.session_id:
            save_qa(
                session_id=st.session_state.session_id,
                question_number=st.session_state.q_count,
                question=last_q,
                answer=user_input,
                clarity=score["clarity"],
                confidence=score["confidence"],
                relevance=score["relevance"],
                feedback=score["feedback"],
                emotion=score["emotion"]
            )

    if st.session_state.q_count >= MAX_QUESTIONS:
        st.session_state.finished = True
        st.rerun()

    with st.spinner("Interviewer is thinking..."):
        next_q = get_next_question(user_input)
        if "interview is now complete" not in next_q.lower():
            if voice_enabled and VOICE_OUTPUT_AVAILABLE:
                speak_question(next_q)

    if "interview is now complete" in next_q.lower():
        st.session_state.finished = True
    else:
        st.session_state.history.append({"role": "Q", "text": next_q})
        st.session_state.q_count += 1
    st.rerun()

# ── Main Tabs ────────────────────────────────────────────
tab1, tab2 = st.tabs(["🎤 Interview", "📊 My History"])

# ════════════════════════════════════════════════════════
# TAB 1 — INTERVIEW
# ════════════════════════════════════════════════════════
with tab1:
    col1, col2 = st.columns([2, 1])

    with col1:
        st.title("🎤 AI Interview Simulator")
        st.caption(f"Mode: **{industry}** | Level: **{difficulty}**")

        for item in st.session_state.history:
            if item["role"] == "Q":
                with st.chat_message("assistant"):
                    st.write(item["text"])
            else:
                with st.chat_message("user"):
                    st.write(item["text"])

        display_audio()

        # Screen 1: Not started
        if not st.session_state.started:
            st.info("Configure your interview in the sidebar, then click Start.")
            if st.button("🚀 Start Interview", type="primary"):
                if DB_AVAILABLE:
                    session_id = create_session(
                        st.session_state.user_id,
                        industry,
                        difficulty
                    )
                    st.session_state.session_id = session_id

                with st.spinner("Preparing your interview..."):
                    first_q = get_next_question("Start the interview now.")
                    if voice_enabled and VOICE_OUTPUT_AVAILABLE:
                        speak_question(first_q)

                st.session_state.started = True
                st.session_state.history.append({"role": "Q", "text": first_q})
                st.session_state.q_count = 1
                st.rerun()

        # Screen 2: Finished
        elif st.session_state.finished:
            st.success("✅ Interview Complete!")
            st.balloons()
            st.session_state.current_audio = None

            if st.session_state.scores and not st.session_state.scores_saved:
                if DB_AVAILABLE and st.session_state.session_id:
                    save_final_scores(
                        st.session_state.session_id,
                        st.session_state.scores
                    )
                    complete_session(st.session_state.session_id)
                st.session_state.scores_saved = True

            st.subheader("📋 Interview Summary")
            q_num = 1
            for item in st.session_state.history:
                if item["role"] == "Q":
                    st.markdown(f"**Q{q_num}:** {item['text']}")
                else:
                    st.markdown(f"**Your answer:** {item['text']}")
                    q_num += 1

        # Screen 3: In progress
        else:
            progress = st.session_state.q_count / MAX_QUESTIONS
            st.progress(
                progress,
                text=f"Question {st.session_state.q_count} of {MAX_QUESTIONS}"
            )

            if IS_CLOUD or not VOICE_INPUT_AVAILABLE:
                # Cloud — typing only
                user_input = st.chat_input("Type your answer and press Enter...")
                if user_input:
                    process_answer(user_input)
            else:
                # Local — typing and voice
                input_method = st.radio(
                    "Answer method:",
                    ["⌨️ Type", "🎤 Speak"],
                    horizontal=True,
                    key="input_method"
                )

                if input_method == "⌨️ Type":
                    user_input = st.chat_input("Type your answer and press Enter...")
                    if user_input:
                        process_answer(user_input)
                else:
                    duration = st.slider(
                        "Recording duration (seconds)",
                        min_value=5,
                        max_value=30,
                        value=10,
                        key="rec_duration"
                    )
                    if st.button("🎤 Start Recording", type="primary"):
                        with st.spinner(f"🔴 Recording for {duration} seconds... speak now!"):
                            transcribed = record_answer(duration)
                        if transcribed and not transcribed.startswith("❌"):
                            st.success(f"✅ You said: **{transcribed}**")
                            st.session_state.voice_input = transcribed
                            st.rerun()
                        else:
                            st.error(transcribed)

                    if st.session_state.voice_input:
                        user_input = st.session_state.voice_input
                        st.session_state.voice_input = None
                        process_answer(user_input)

    # ── Score Dashboard ───────────────────────────────────
    with col2:
        st.subheader("📊 Live Scores")
        if st.session_state.scores:
            for i, score in enumerate(st.session_state.scores):
                with st.expander(
                    f"Answer {i+1} Scores",
                    expanded=(i == len(st.session_state.scores) - 1)
                ):
                    st.metric("Clarity", f"{score.get('clarity', 5)}/10")
                    st.metric("Confidence", f"{score.get('confidence', 5)}/10")
                    st.metric("Relevance", f"{score.get('relevance', 5)}/10")
                    st.caption(f"💬 {score.get('feedback', '')}")

                    if score.get("emotion"):
                        st.divider()
                        emotion = score.get("emotion", "neutral")
                        emotion_emoji = {
                            "confident": "💪",
                            "nervous": "😰",
                            "hesitant": "🤔",
                            "enthusiastic": "🔥",
                            "calm": "😌",
                            "neutral": "😐"
                        }.get(emotion, "😐")
                        st.markdown(f"**Emotion:** {emotion_emoji} {emotion.title()}")
                        st.metric("Energy", f"{score.get('energy', 5)}/10")
                        st.metric("Nervousness", f"{score.get('nervousness', 5)}/10")
                        if score.get("suggestion"):
                            st.info(f"💡 {score.get('suggestion')}")

            if st.session_state.finished:
                avg_c = sum(s.get("clarity", 5) for s in st.session_state.scores) / len(st.session_state.scores)
                avg_conf = sum(s.get("confidence", 5) for s in st.session_state.scores) / len(st.session_state.scores)
                avg_r = sum(s.get("relevance", 5) for s in st.session_state.scores) / len(st.session_state.scores)
                avg_energy = sum(s.get("energy", 5) for s in st.session_state.scores) / len(st.session_state.scores)
                avg_nerv = sum(s.get("nervousness", 5) for s in st.session_state.scores) / len(st.session_state.scores)
                st.divider()
                st.subheader("🏆 Final Scores")
                st.metric("Avg Clarity", f"{avg_c:.1f}/10")
                st.metric("Avg Confidence", f"{avg_conf:.1f}/10")
                st.metric("Avg Relevance", f"{avg_r:.1f}/10")
                st.metric("Avg Energy", f"{avg_energy:.1f}/10")
                st.metric("Avg Nervousness", f"{avg_nerv:.1f}/10")
        else:
            st.info("Scores will appear here as you answer questions.")

# ════════════════════════════════════════════════════════
# TAB 2 — HISTORY
# ════════════════════════════════════════════════════════
with tab2:
    st.subheader(f"📊 {st.session_state.user_name}'s Interview History")

    if not DB_AVAILABLE:
        st.warning("Database not available in this environment.")
    else:
        history = get_user_history(st.session_state.user_id)

        if not history:
            st.info("No interviews yet. Complete your first interview to see history!")
        else:
            total = len(history)
            completed = [h for h in history if h.get("session_scores")]
            scores_list = [
                h["session_scores"][0].get("overall_score", 0)
                for h in completed if h.get("session_scores")
            ]
            avg_overall = sum(scores_list) / len(scores_list) if scores_list else 0

            c1, c2, c3 = st.columns(3)
            c1.metric("Total Sessions", total)
            c2.metric("Completed", len(completed))
            c3.metric("Avg Overall Score", f"{avg_overall:.1f}/10")
            st.divider()

            for session in history:
                scores = session.get("session_scores", [])
                score_data = scores[0] if scores else {}
                overall = score_data.get("overall_score", "N/A")
                date = session["created_at"][:10]
                ind = session.get("industry", "General")
                diff = session.get("difficulty", "Entry Level")

                with st.expander(
                    f"📅 {date} | {ind} | {diff} | Score: {overall}/10"
                ):
                    if score_data:
                        c1, c2, c3 = st.columns(3)
                        c1.metric("Clarity", f"{score_data.get('avg_clarity', 0):.1f}/10")
                        c2.metric("Confidence", f"{score_data.get('avg_confidence', 0):.1f}/10")
                        c3.metric("Relevance", f"{score_data.get('avg_relevance', 0):.1f}/10")

                    qa_list = get_session_qa(session["id"])
                    if qa_list:
                        st.divider()
                        for qa in qa_list:
                            st.markdown(f"**Q{qa['question_number']}:** {qa['question_text']}")
                            st.markdown(f"**Answer:** {qa['answer_text']}")
                            c1, c2, c3 = st.columns(3)
                            c1.metric("Clarity", qa.get("clarity_score", "-"))
                            c2.metric("Confidence", qa.get("confidence_score", "-"))
                            c3.metric("Relevance", qa.get("relevance_score", "-"))
                            st.caption(f"💬 {qa.get('feedback', '')}")
                            st.caption(f"🎭 Emotion: {qa.get('emotion', 'neutral')}")
                            st.divider()