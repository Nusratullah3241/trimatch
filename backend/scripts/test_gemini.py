"""Quick check that the Gemini API key works. Run once."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import google.generativeai as genai
from app.config import settings

if not settings.gemini_api_key:
    print("ERROR: GEMINI_API_KEY is empty. Check your .env file.")
    sys.exit(1)

print(f"Key loaded: {settings.gemini_api_key[:8]}...{settings.gemini_api_key[-4:]}")

genai.configure(api_key=settings.gemini_api_key)
model = genai.GenerativeModel("gemini-3.6-flash")

response = model.generate_content("Reply with exactly: CONNECTION OK")
print(response.text.strip())