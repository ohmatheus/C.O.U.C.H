from typing import Any

from llm.base import BaseLLMProvider


def create_provider(config: dict[str, Any]) -> BaseLLMProvider:
    provider_name: str = config.get("llm_provider", "ollama")

    if provider_name == "anthropic":
        from llm.anthropic import AnthropicProvider
        from settings import EnvSettings
        env = EnvSettings()
        if env.anthropic_api_key is None:
            raise ValueError("ANTHROPIC_API_KEY not set — add it to .env")
        return AnthropicProvider(model=config["llm_model"], api_key=env.anthropic_api_key.get_secret_value())

    from llm.ollama import OllamaProvider
    return OllamaProvider(model=config["llm_model"], keepalive=config.get("llm_keepalive", -1))
