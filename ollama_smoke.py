from src.services.ollama_client import OllamaClient

c = OllamaClient()
out = c.chat_json(
    system='Output JSON exactly like: {"ok": true}',
    user="Respond now."
)
print(out)
