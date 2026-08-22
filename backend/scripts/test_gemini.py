"""Lists available models. Makes NO generation call, so quota limits don't apply."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import google.generativeai as genai
from app.config import settings

genai.configure(api_key=settings.gemini_api_key)

print("Models available to your key:\n")
count = 0
for m in genai.list_models():
    if "generateContent" in m.supported_generation_methods:
        print(f"  {m.name}")
        count += 1
print(f"\n{count} models available.")
print(f"At 20 requests/day each, that's up to {count * 20} requests/day free.")