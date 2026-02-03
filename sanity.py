from dotenv import load_dotenv
import os
import requests

load_dotenv()

base = os.getenv("OLLAMA_BASE_URL", "")
model = os.getenv("OLLAMA_MODEL", "")

print("OLLAMA_BASE_URL:", base)
print("OLLAMA_MODEL:", model)

if not base:
    raise SystemExit("Missing OLLAMA_BASE_URL in .env")
if not model:
    raise SystemExit("Missing OLLAMA_MODEL in .env")

r = requests.get(f"{base}/api/tags", timeout=10)
print("Ollama OK:", r.status_code == 200)
