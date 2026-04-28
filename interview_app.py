import streamlit as st
import requests
import json
import pdfplumber
from pathlib import Path

N8N_BASE_URL = "https://n8n-production-1cf5.up.railway.app/webhook"
MAX_QUESTIONS = 5

st.set_page_config(page_title="AI Interview Simulator", page_icon="🎤", layout="wide")

# ── Sidebar ─────────────────────────────────────────────
with st.sidebar:
    st.title("⚙️ Interview Setup")

    industry = st.selectbox(
        "Select Industry",
        ["General", "Tech / Software", "HR / People Ops", "Sales / Business Dev"]
    )

    difficulty = st.selectbox(
        "Difficulty Level",
        ["Entry Level", "Mid Level", "Senior Level"]
    )

    resume_file = st.file_uploader("Upload Your Resume (PDF)", type=["pdf"])
    resume_text = ""
    if resume_file:
        with pdfplumber.open(resume_file) as pdf:
            for page in pdf.pages:
                resume_text += page.extract_text() or ""
        st.success("✅ Resume loaded!")
        with st.expander("Preview extracted text"):
            st.write(resume_text[:500] + "...")

    if st.button("🔄 Reset Interview"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

# ── Session State ────────────────────────────────────────
defaults = {
    "started": False,
    "history": [],
    "finished": False,
    "q_count": 0,
    "scores": [],
    "industry": industry,
    "resume_text": resume_text
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

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
        "industry": st.session_state.industry,
        "difficulty": difficulty,
        "resume_text": st.session_state.resume_text[:1000] if st.session_state.resume_text else ""
    }
    try:
        r = requests.post(f"{N8N_BASE_URL}/interview", json=payload, timeout=30)
        r.raise_for_status()
        question = r.json().get("next_question", "Could not generate question.")
        # Clean any leading = or whitespace
        question = question.lstrip("= ").strip()
        return question
    except Exception as e:
        return f"❌ Error: {str(e)}"

def get_score(question: str, answer: str) -> dict:
    payload = {"question": question, "answer": answer}
    try:
        r = requests.post(f"{N8N_BASE_URL}/score", json=payload, timeout=30)
        r.raise_for_status()
        return r.json()
    except:
        return {"clarity": 5, "confidence": 5, "relevance": 5, "feedback": "Could not score."}

# ── Main Area ─────────────────────────────────────────────
col1, col2 = st.columns([2, 1])

with col1:
    st.title("🎤 AI Interview Simulator")
    st.caption(f"Mode: **{industry}** | Level: **{difficulty}**")

    # Display chat history
    for item in st.session_state.history:
        if item["role"] == "Q":
            with st.chat_message("assistant"):
                st.write(item["text"])
        else:
            with st.chat_message("user"):
                st.write(item["text"])

    # Screen 1: Start
    if not st.session_state.started:
        st.info("Configure your interview in the sidebar, then click Start.")
        if st.button("🚀 Start Interview", type="primary"):
            with st.spinner("Preparing your interview..."):
                first_q = get_next_question("Start the interview now.")
            st.session_state.started = True
            st.session_state.history.append({"role": "Q", "text": first_q})
            st.session_state.q_count = 1
            st.rerun()

    # Screen 2: Finished
    elif st.session_state.finished:
        st.success("✅ Interview Complete!")
        st.balloons()

    # Screen 3: In progress
    else:
        progress = st.session_state.q_count / MAX_QUESTIONS
        st.progress(progress, text=f"Question {st.session_state.q_count} of {MAX_QUESTIONS}")

        user_input = st.chat_input("Type your answer and press Enter...")
        if user_input:
            st.session_state.history.append({"role": "A", "text": user_input})

            # Score this answer
            if len(st.session_state.history) >= 2:
                last_q = st.session_state.history[-2]["text"]
                with st.spinner("Scoring your answer..."):
                    score = get_score(last_q, user_input)
                st.session_state.scores.append(score)

            if st.session_state.q_count >= MAX_QUESTIONS:
                st.session_state.finished = True
                st.rerun()

            with st.spinner("Interviewer is thinking..."):
                next_q = get_next_question(user_input)

            if "interview is now complete" in next_q.lower():
                st.session_state.finished = True
            else:
                st.session_state.history.append({"role": "Q", "text": next_q})
                st.session_state.q_count += 1
            st.rerun()

# ── Score Dashboard (right column) ───────────────────────
with col2:
    st.subheader("📊 Live Scores")
    if st.session_state.scores:
        for i, score in enumerate(st.session_state.scores):
            with st.expander(f"Answer {i+1} Scores"):
                c, conf, r = score.get("clarity",5), score.get("confidence",5), score.get("relevance",5)
                st.metric("Clarity", f"{c}/10")
                st.metric("Confidence", f"{conf}/10")
                st.metric("Relevance", f"{r}/10")
                st.caption(score.get("feedback", ""))

        # Overall average
        if st.session_state.finished:
            avg_clarity = sum(s.get("clarity",5) for s in st.session_state.scores) / len(st.session_state.scores)
            avg_conf = sum(s.get("confidence",5) for s in st.session_state.scores) / len(st.session_state.scores)
            avg_rel = sum(s.get("relevance",5) for s in st.session_state.scores) / len(st.session_state.scores)
            st.divider()
            st.subheader("🏆 Final Scores")
            st.metric("Avg Clarity", f"{avg_clarity:.1f}/10")
            st.metric("Avg Confidence", f"{avg_conf:.1f}/10")
            st.metric("Avg Relevance", f"{avg_rel:.1f}/10")
    else:
        st.info("Scores will appear here as you answer questions.")