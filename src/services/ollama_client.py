from __future__ import annotations
import requests
from src.config.settings import get_settings
import json
import re
import subprocess

_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


class OllamaClient:
    """
    CLI-based Ollama client (Windows-safe decoding).
    """

    def __init__(self) -> None:
        s = get_settings()
        self.model = s.ollama_model

    def _extract_json(self, text: str) -> dict:
        text = text.strip()

        # direct JSON
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # find first {...}
        m = _JSON_RE.search(text)
        if not m:
            raise ValueError(f"Model did not return JSON.\nRaw output:\n{text[:2000]}")

        block = m.group(0)
        try:
            return json.loads(block)
        except json.JSONDecodeError as e:
            raise ValueError(f"Couldn't parse JSON block:\n{block[:2000]}") from e

    def chat_json(self, system: str, user: str) -> dict:
        """
        Runs ollama via CLI and parses JSON output.
        Uses bytes capture + UTF-8 decode to avoid cp1252 decode crashes.
        """
        # keep prompt minimal to reduce latency
        prompt = f"{system}\n{user}\nReturn ONLY JSON."

        proc = subprocess.run(
            ["ollama", "run", self.model, prompt],
            capture_output=True,   # bytes because text=False
            text=False,
            timeout=600,           # 10 minutes to survive first-load
        )

        stdout = proc.stdout.decode("utf-8", errors="replace") if proc.stdout else ""
        stderr = proc.stderr.decode("utf-8", errors="replace") if proc.stderr else ""

        if proc.returncode != 0:
            raise RuntimeError(
                f"ollama CLI failed (exit {proc.returncode}).\nSTDERR:\n{stderr[:2000]}\nSTDOUT:\n{stdout[:2000]}"
            )

        return self._extract_json(stdout)

    def embed(self, text: str) -> list[float]:
        s = get_settings()
        url = f"{s.ollama_base_url.rstrip('/')}/api/embeddings"
        payload = {"model": s.ollama_embed_model, "prompt": text}
        r = requests.post(url, json=payload, timeout=120)
        r.raise_for_status()
        return r.json()["embedding"]
