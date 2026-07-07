import json
import math
import struct
import sys
import wave
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR / "main_ai_canri"))

from Voice_brain import VoiceBrain


TEST_DIR = PROJECT_DIR / "tmp"
TEST_DIR.mkdir(exist_ok=True)

wav_path = TEST_DIR / "voice_test.wav"
sample_rate = 8000
duration = 0.15
frames = []

for index in range(int(sample_rate * duration)):
    value = int(12000 * math.sin(2 * math.pi * 440 * index / sample_rate))
    frames.append(struct.pack("<h", value))

with wave.open(str(wav_path), "wb") as wav_file:
    wav_file.setnchannels(1)
    wav_file.setsampwidth(2)
    wav_file.setframerate(sample_rate)
    wav_file.writeframes(b"".join(frames))

brain = VoiceBrain()

result = brain.process({
    "understanding": {
        "original_text": "Analyze this recording and transcribe audio from clip.mp4",
        "main_topic": "voice",
        "intent": "audio_analysis",
        "words": [
            {
                "word": "recording",
                "exists": True,
                "connections": ["audio", "speech", "metadata"]
            }
        ]
    },
    "files": [
        str(wav_path),
        {
            "path": "clip.mp4",
            "context": "attachment"
        }
    ]
})

print(json.dumps({
    "brain": result["brain"],
    "media_detected": result["media_detected"],
    "summary": result["summary"],
    "first_media": result["media"][0],
    "second_media": result["media"][1],
    "needs_transcription_engine": result["needs_transcription_engine"],
    "needs_video_audio_extraction": result["needs_video_audio_extraction"],
    "suggested_next_brains": result["suggested_next_brains"],
    "confidence": result["confidence"]
}, ensure_ascii=False, indent=2))

wav_path.unlink(missing_ok=True)
