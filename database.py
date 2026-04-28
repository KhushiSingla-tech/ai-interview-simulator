from supabase import create_client
import streamlit as st
from datetime import datetime
import uuid

# Initialize Supabase client
@st.cache_resource
def get_supabase():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

# ── User Functions ──────────────────────────────────────

def get_or_create_user(name: str, email: str) -> str:
    supabase = get_supabase()
    try:
        # Check if user exists
        result = supabase.table("users")\
            .select("id")\
            .eq("email", email)\
            .execute()
        
        if result.data:
            return result.data[0]["id"]
        
        # Create new user
        result = supabase.table("users").insert({
            "name": name,
            "email": email
        }).execute()
        
        return result.data[0]["id"]
    except Exception as e:
        st.error(f"User error: {str(e)}")
        return None

# ── Session Functions ───────────────────────────────────

def create_session(user_id: str, industry: str, difficulty: str) -> str:
    supabase = get_supabase()
    try:
        result = supabase.table("interview_sessions").insert({
            "user_id": user_id,
            "industry": industry,
            "difficulty": difficulty,
            "status": "in_progress"
        }).execute()
        return result.data[0]["id"]
    except Exception as e:
        st.error(f"Session error: {str(e)}")
        return None

def complete_session(session_id: str):
    supabase = get_supabase()
    try:
        supabase.table("interview_sessions").update({
            "status": "completed",
            "completed_at": datetime.now().isoformat()
        }).eq("id", session_id).execute()
    except Exception as e:
        st.error(f"Complete session error: {str(e)}")

# ── Q&A Functions ───────────────────────────────────────

def save_qa(session_id: str, question_number: int, 
            question: str, answer: str,
            clarity: int, confidence: int, 
            relevance: int, feedback: str,
            emotion: str = "neutral"):
    supabase = get_supabase()
    try:
        supabase.table("interview_qa").insert({
            "session_id": session_id,
            "question_number": question_number,
            "question_text": question,
            "answer_text": answer,
            "clarity_score": clarity,
            "confidence_score": confidence,
            "relevance_score": relevance,
            "emotion": emotion,
            "feedback": feedback
        }).execute()
    except Exception as e:
        st.error(f"Save QA error: {str(e)}")

# ── Score Functions ─────────────────────────────────────

def save_final_scores(session_id: str, scores: list):
    supabase = get_supabase()
    try:
        avg_clarity = sum(s.get("clarity", 5) for s in scores) / len(scores)
        avg_confidence = sum(s.get("confidence", 5) for s in scores) / len(scores)
        avg_relevance = sum(s.get("relevance", 5) for s in scores) / len(scores)
        overall = (avg_clarity + avg_confidence + avg_relevance) / 3

        supabase.table("session_scores").insert({
            "session_id": session_id,
            "avg_clarity": round(avg_clarity, 2),
            "avg_confidence": round(avg_confidence, 2),
            "avg_relevance": round(avg_relevance, 2),
            "overall_score": round(overall, 2)
        }).execute()
    except Exception as e:
        st.error(f"Save scores error: {str(e)}")

# ── History Functions ───────────────────────────────────

def get_user_history(user_id: str) -> list:
    supabase = get_supabase()
    try:
        result = supabase.table("interview_sessions")\
            .select("*, session_scores(*)")\
            .eq("user_id", user_id)\
            .eq("status", "completed")\
            .order("created_at", desc=True)\
            .execute()
        return result.data
    except Exception as e:
        st.error(f"History error: {str(e)}")
        return []

def get_session_qa(session_id: str) -> list:
    supabase = get_supabase()
    try:
        result = supabase.table("interview_qa")\
            .select("*")\
            .eq("session_id", session_id)\
            .order("question_number")\
            .execute()
        return result.data
    except Exception as e:
        return []
