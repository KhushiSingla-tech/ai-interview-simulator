# 🎤 AI Voice Interview Simulator

An intelligent, voice-enabled mock interview platform powered by AI that helps job seekers practice interviews with real-time feedback, emotion analysis, and performance tracking.

## 🌐 Live Demo

| Version | URL | Description |
|---|---|---|
| 🎯 Prototype | [Week 2 Prototype](https://ai-interview-simulator-prototype-bausbh9a9dsxk9e5uvws8w.streamlit.app/) | Text-based interview simulator |
| 🚀 Full Project | [Full Application](https://ai-interview-simulator-web.streamlit.app) | Voice + DB + Emotion Analysis |

---

## 📌 Project Overview

Most job seekers lack access to realistic interview practice. Existing platforms are text-based and fail to simulate real conversational pressure or provide actionable feedback on speaking skills.

This project solves that by building a **voice-based AI interview simulator** that:
- Conducts real-time mock interviews
- Asks adaptive questions based on your responses
- Evaluates your performance across multiple dimensions
- Provides personalized feedback and emotion analysis
- Tracks your progress over time

---

## ✨ Features

### 🎤 Voice Interview Simulation
- AI asks questions via text-to-speech
- Record your answers using your browser microphone
- Automatic transcription using OpenAI Whisper

### 🧠 Dynamic AI Questioning
- Questions adapt based on your previous answers
- Industry-specific modes: General, Tech, HR, Sales
- Difficulty levels: Entry, Mid, Senior
- Resume-based personalized questions

### 📊 Real-Time Performance Scoring
After each answer, AI evaluates:
- **Clarity** — How clearly you express yourself
- **Confidence** — How confident you sound
- **Relevance** — How relevant your answer is

### 🎭 Emotion Analysis
- Detects emotional signals from your answers
- Tracks Energy and Nervousness levels
- Provides coaching suggestions

### 📈 History Dashboard
- Save all interview sessions to database
- Track improvement over multiple sessions
- Review past questions and answers
- View score trends over time

### 🔄 Resume Upload
- Upload your PDF resume
- AI generates questions based on your background
- Personalised interview experience

---

## 🛠️ Tech Stack

| Component | Technology |
|---|---|
| Frontend | Streamlit |
| Workflow Automation | n8n |
| LLM | Groq (llama-3.1-8b-instant) |
| Voice Output | Lemonfox TTS |
| Voice Input | Lemonfox Whisper STT |
| Emotion Analysis | Groq LLM |
| Database | Supabase (PostgreSQL) |
| Backend Deployment | Railway |
| Frontend Deployment | Streamlit Cloud |

---

## 🏗️ Architecture
<img width="467" height="698" alt="image" src="https://github.com/user-attachments/assets/ee077545-52a8-49c3-9048-c77c2f2a5b26" />

---

## 📁 Project Structure
<img width="229" height="299" alt="image" src="https://github.com/user-attachments/assets/30c933c1-f3f7-4174-ac11-c7594fa888a2" />

---

## ⚙️ n8n Workflows

### Workflow 1 — AI Interview
<img width="1375" height="614" alt="image" src="https://github.com/user-attachments/assets/21f3edd4-b555-47ce-977a-fccd8dbde5a2" />

- Receives user answer + conversation history
- Sends to Groq LLM with interviewer prompt
- Returns next question

### Workflow 2 — Answer Scorer
<img width="1022" height="488" alt="image" src="https://github.com/user-attachments/assets/24a0be82-8c9e-4691-b38b-3bac155d6941" />

- Receives question + answer
- Scores on Clarity, Confidence, Relevance (1-10)
- Returns scores + feedback

---

## 🗄️ Database Schema

```sql
-- Users
users (id, name, email, created_at)

-- Interview Sessions
interview_sessions (id, user_id, industry, difficulty, status, created_at, completed_at)

-- Questions and Answers
interview_qa (id, session_id, question_number, question_text, 
              answer_text, clarity_score, confidence_score, 
              relevance_score, emotion, feedback, created_at)

-- Final Scores
session_scores (id, session_id, avg_clarity, avg_confidence, 
                avg_relevance, overall_score, created_at)
```

---

## 🚀 Local Setup

### Prerequisites
- Python 3.10+
- Node.js 22+
- n8n installed globally

### 1. Clone the Repository
```bash
git clone https://github.com/YOUR_USERNAME/ai-interview-simulator.git
cd ai-interview-simulator
```

### 2. Create Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate  # Mac/Linux
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Set Up Secrets
Create `.streamlit/secrets.toml`:
```toml
N8N_BASE_URL = "http://localhost:5678/webhook"
SUPABASE_URL = "your_supabase_url"
SUPABASE_KEY = "your_supabase_key"
GROQ_KEY = "your_groq_key"
LEMONFOX_API_KEY = "your_lemonfox_key"
```

### 5. Start n8n
```bash
n8n start
```

### 6. Import n8n Workflows
1. Open `http://localhost:5678`
2. Import `AI Interview Simulator` workflow
3. Import `Interview Scorer` workflow
4. Add your Groq API key to both workflows
5. Activate both workflows

### 7. Run the App
```bash
streamlit run interview_app.py
```

Open `http://localhost:8501`

---

## 🔑 API Keys Required

| Service | Purpose | Free Tier |
|---|---|---|
| [Groq](https://console.groq.com) | LLM for questions + scoring | ✅ Free |
| [Lemonfox](https://lemonfox.ai) | TTS + STT | ✅ First month free |
| [Supabase](https://supabase.com) | Database | ✅ Free tier |
| [Railway](https://railway.app) | n8n hosting | ✅ $5 free credit |

---

## 📱 How to Use

1. **Login** — Enter your name and email
2. **Setup** — Select industry and difficulty in sidebar
3. **Resume** — Upload your PDF resume (optional)
4. **Start** — Click "Start Interview"
5. **Answer** — Type or speak your answers
6. **Review** — See live scores after each answer
7. **Complete** — View final scores and emotion analysis
8. **History** — Check "My History" tab for past sessions

---

## 📊 Scoring System

| Metric | Description |
|---|---|
| Clarity (1-10) | How clearly you express your thoughts |
| Confidence (1-10) | How confident your answer sounds |
| Relevance (1-10) | How relevant your answer is to the question |
| Energy (1-10) | Communication energy level |
| Nervousness (1-10) | Detected nervousness level |
| Overall Score | Average of all metrics |

---

## 🎭 Emotion Detection

The AI analyses your answer text and detects:

| Emotion | Emoji | Meaning |
|---|---|---|
| Confident | 💪 | Strong, assured responses |
| Enthusiastic | 🔥 | High energy, passionate answers |
| Calm | 😌 | Composed, measured responses |
| Hesitant | 🤔 | Uncertain, unsure responses |
| Nervous | 😰 | Anxious, stressed responses |
| Neutral | 😐 | Balanced, neutral responses |

---

## 🔮 Future Enhancements

- [ ] Real-time emotion detection from voice signals
- [ ] Multi-language support
- [ ] Company-specific interview modes (Google, Amazon, etc.)
- [ ] Progress charts and improvement
