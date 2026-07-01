"""
API handler: returns available API providers based on configured .env keys.
"""

import os
from helpers.api import ApiHandler, Request, Response

# Provider -> env var mapping
PROVIDER_KEYS = {
    "openrouter": {"env": "API_KEY_OPENROUTER", "label": "OpenRouter"},
    "ollama": {"env": "API_KEY_OLLAMA", "label": "Ollama (Local)"},
    "ollama_cloud": {"env": "API_KEY_OLLAMA_CLOUD", "label": "Ollama Cloud"},
    "openai": {"env": "API_KEY_OPENAI", "label": "OpenAI"},
    "anthropic": {"env": "API_KEY_ANTHROPIC", "label": "Anthropic"},
    "google": {"env": "API_KEY_GOOGLE", "label": "Google AI"},
    "groq": {"env": "API_KEY_GROQ", "label": "Groq"},
    "xai": {"env": "API_KEY_XAI", "label": "xAI"},
    "mistral": {"env": "API_KEY_MISTRAL", "label": "Mistral"},
    "deepseek": {"env": "API_KEY_DEEPSEEK", "label": "DeepSeek"},
    "venice": {"env": "API_KEY_VENICE", "label": "Venice"},
    "sambanova": {"env": "API_KEY_SAMBANOVA", "label": "SambaNova"},
    "huggingface": {"env": "API_KEY_HUGGINGFACE", "label": "HuggingFace"},
    "nebius": {"env": "API_KEY_NEBIUS", "label": "Nebius"},
    "moonshot": {"env": "API_KEY_MOONSHOT", "label": "Moonshot"},
}


class AvailableProviders(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict | Response:
        available = []
        unavailable = []

        for provider_id, info in PROVIDER_KEYS.items():
            key = os.environ.get(info["env"], "").strip()
            entry = {
                "id": provider_id,
                "label": info["label"],
                "env_var": info["env"],
                "has_key": bool(key),
            }
            if key:
                available.append(entry)
            else:
                unavailable.append(entry)

        return {
            "available": available,
            "unavailable": unavailable,
        }
