"""
API handler: returns which providers have API keys configured (masked).
"""

import os
from helpers.api import ApiHandler, Request, Response

PROVIDER_KEYS = {
    "ollama_cloud": "API_KEY_OLLAMA_CLOUD",
    "openrouter": "API_KEY_OPENROUTER",
    "ollama": "API_KEY_OLLAMA",
    "openai": "API_KEY_OPENAI",
    "anthropic": "API_KEY_ANTHROPIC",
    "google": "API_KEY_GOOGLE",
    "groq": "API_KEY_GROQ",
    "xai": "API_KEY_XAI",
    "mistral": "API_KEY_MISTRAL",
    "deepseek": "API_KEY_DEEPSEEK",
    "venice": "API_KEY_VENICE",
    "sambanova": "API_KEY_SAMBANOVA",
    "huggingface": "API_KEY_HUGGINGFACE",
    "nebius": "API_KEY_NEBIUS",
    "moonshot": "API_KEY_MOONSHOT",
}


class AvailableProviders(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict | Response:
        configured = {}
        for provider_id, env_var in PROVIDER_KEYS.items():
            key = os.environ.get(env_var, "").strip()
            if key:
                # Return masked key: first 8 chars + ****
                masked = key[:8] + "****" if len(key) > 8 else "****"
                configured[provider_id] = {"has_key": True, "masked": masked, "env_var": env_var}
            else:
                configured[provider_id] = {"has_key": False, "masked": "", "env_var": env_var}
        return {"configured": configured}
