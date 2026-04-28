import streamlit as st
from elevenlabs.client import ElevenLabs
import base64

st.title("Voice Test")

if st.button("Test Voice"):
    try:
        api_key = st.secrets.get("ELEVENLABS_KEY", "")
        client = ElevenLabs(api_key=api_key)

        audio = client.text_to_speech.convert(
            voice_id="pNInz6obpgDQGcFmaJgB",  # Adam - free tier voice
            text="Hello, this is a voice test.",
            model_id="eleven_turbo_v2_5",
            output_format="mp3_44100_128"
        )

        audio_bytes = b"".join(audio)
        st.write(f"Audio generated: {len(audio_bytes)} bytes")

        # Play audio
        audio_b64 = base64.b64encode(audio_bytes).decode()
        st.markdown(
            f'<audio controls><source src="data:audio/mp3;base64,{audio_b64}" type="audio/mp3"></audio>',
            unsafe_allow_html=True
        )
        st.success("Press play button above!")

    except Exception as e:
        st.error(f"Error: {str(e)}")