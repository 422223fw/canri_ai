import base64
import json
import sys
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR / "main_ai_canri"))

from Vision_brain import VisionBrain


TEST_DIR = PROJECT_DIR / "tmp"
TEST_DIR.mkdir(exist_ok=True)

png_path = TEST_DIR / "vision_test.png"
png_path.write_bytes(
    base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
    )
)

brain = VisionBrain()

result = brain.process({
    "understanding": {
        "original_text": "Analyze this image file and suspicious installer",
        "main_topic": "vision",
        "intent": "file_analysis",
        "words": [
            {
                "word": "image",
                "exists": True,
                "connections": ["file", "png", "metadata"]
            }
        ]
    },
    "files": [
        str(png_path),
        {
            "path": "setup.exe",
            "context": "attachment"
        }
    ]
})

print(json.dumps({
    "brain": result["brain"],
    "files_detected": result["files_detected"],
    "summary": result["summary"],
    "first_file": result["files"][0],
    "second_file": result["files"][1],
    "needs_security": result["needs_security"],
    "suggested_next_brains": result["suggested_next_brains"],
    "confidence": result["confidence"]
}, ensure_ascii=False, indent=2))

png_path.unlink(missing_ok=True)
