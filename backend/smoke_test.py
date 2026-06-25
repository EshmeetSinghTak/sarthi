"""
SARTHI smoke test — verifies the NVIDIA Build API key works and the default
model responds in a SARTHI-flavoured persona.

This is the very first end-to-end check from TODO.md Phase 1:
    "one-node call to the default model with a 'Hello, Priya' prompt"

Run:
    cd backend
    pip install -r requirements.txt
    python smoke_test.py
"""

import os
import sys

from dotenv import load_dotenv
from openai import OpenAI

# Windows consoles default to cp1252, which can't encode Devanagari / Hinglish
# output. Force UTF-8 so vernacular replies render correctly.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

load_dotenv()

API_KEY = os.getenv("NVIDIA_API_KEY")
BASE_URL = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
MODEL = os.getenv("SARTHI_MODEL_DEFAULT", "meta/llama-3.3-70b-instruct")

if not API_KEY:
    sys.exit("ERROR: NVIDIA_API_KEY not set. Copy .env.example to .env and fill it in.")

SYSTEM_PROMPT = (
    "You are SARTHI (सारथी), an AI mentor guiding Tier-2/3 Indian students "
    "through their study-abroad journey — from 'where do I even go?' to "
    "'my loan is disbursed'. You are warm, concrete, and you speak naturally "
    "in Hinglish when it fits. You are an agent that takes action, not a "
    "generic chatbot. Keep this first reply short."
)

USER_PROMPT = (
    "Hi, I'm Priya from Nagpur. Final-year Mech Eng, CGPA 7.8. I want to do an "
    "MS in Robotics abroad but I have no idea where to start. Can you help?"
)

client = OpenAI(base_url=BASE_URL, api_key=API_KEY)

print(f"→ Model: {MODEL}\n→ Endpoint: {BASE_URL}\n{'-' * 60}")

completion = client.chat.completions.create(
    model=MODEL,
    messages=[
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": USER_PROMPT},
    ],
    temperature=0.7,
    top_p=1,
    max_tokens=1024,
    stream=True,
)

for chunk in completion:
    if not getattr(chunk, "choices", None):
        continue
    delta = chunk.choices[0].delta
    if getattr(delta, "content", None) is not None:
        print(delta.content, end="", flush=True)

print(f"\n{'-' * 60}\n✓ Smoke test complete — API key works, {MODEL} responded.")
