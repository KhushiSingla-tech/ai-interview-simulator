from supabase import create_client
import streamlit as st

url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]

supabase = create_client(url, key)

# Test connection
result = supabase.table("users").select("*").execute()
print("Connection successful!")
print(result)
