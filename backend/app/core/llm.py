import httpx
import traceback
from typing import Optional

OLLAMA_ENDPOINT = "http://127.0.0.1:11434/api/generate"

class LocalOllamaClient:
    """Connects to local Ollama daemon for open-weights agent inference."""
    def __init__(self, model_name: str = "llama3:latest"):
        self.endpoint = OLLAMA_ENDPOINT
        self.model_name = model_name

    async def generate_response(self, prompt: str, system_prompt: str, context_data: str) -> Optional[str]:
        full_system = (
            f"{system_prompt}\n\n"
            f"ENTERPRISE FACTS:\n{context_data}\n\n"
            f"Instructions:\n"
            f"- Speak naturally in your agent role.\n"
            f"- Use the exact figures from ENTERPRISE FACTS.\n"
            f"- Keep it direct and under 3 sentences."
        )

        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "system": full_system,
            "stream": False,
            "options": {
                "temperature": 0.2,
                "num_predict": 120
            }
        }

        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                res = await client.post(self.endpoint, json=payload)
                if res.status_code == 200:
                    out = res.json().get("response", "").strip()
                    if out:
                        return out
                else:
                    print(f"[Ollama Error] HTTP Status: {res.status_code} - {res.text}")
        except Exception as e:
            print(f"[Ollama Connection Failed]: {e}")

        return None

ollama_client = LocalOllamaClient(model_name="llama3:latest")