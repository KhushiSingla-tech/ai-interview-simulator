import whisper
import sounddevice as sd
import soundfile as sf
import numpy as np
import tempfile
import os

print("Loading Whisper model...")
model = whisper.load_model("base")
print("Model loaded!")

# Better recording settings
sample_rate = 16000
duration = 8  # more time to speak

print("Recording for 8 seconds... speak now!")
recording = sd.rec(
    int(duration * sample_rate),
    samplerate=sample_rate,
    channels=1,
    dtype="float32"
)
sd.wait()
print("Recording done!")

# Check audio levels
max_volume = np.max(np.abs(recording))
print(f"Max volume detected: {max_volume:.4f}")

if max_volume < 0.01:
    print("⚠️ Volume too low - microphone may not be picking up sound")
else:
    print("✅ Audio levels look good")

# Save and transcribe
with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
    temp_path = f.name
sf.write(temp_path, recording, sample_rate)

result = model.transcribe(temp_path, language="en", fp16=False)
os.unlink(temp_path)

print(f"You said: {result['text']}")