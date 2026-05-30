"""
Model presets for automatic context window configuration.

Provides predefined configurations for common LLM models to simplify setup.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ModelPreset:
    """
    Model preset configuration.

    Attributes:
        name: Model name identifier
        context_window: Maximum context window size in tokens
        default_output_tokens: Default maximum output tokens
        provider: Provider type (anthropic, openai, etc.)
    """

    name: str
    context_window: int
    default_output_tokens: int
    provider: str = "auto"


# Context level shortcuts
CONTEXT_LEVELS: dict[str, int] = {
    "32k": 32768,
    "64k": 65536,
    "128k": 131072,
    "200k": 204800,
}

# Default preset for unknown models
DEFAULT_PRESET = ModelPreset(
    name="default",
    context_window=65536,  # 64K as reasonable default
    default_output_tokens=4096,
    provider="auto",
)

# Predefined model configurations
MODEL_PRESETS: dict[str, ModelPreset] = {
    # Anthropic Claude
    "claude-opus-4-6": ModelPreset("claude-opus-4-6", 200000, 16384, "anthropic"),
    "claude-opus-4": ModelPreset("claude-opus-4", 200000, 16384, "anthropic"),
    "claude-sonnet-4-6": ModelPreset("claude-sonnet-4-6", 200000, 16384, "anthropic"),
    "claude-sonnet-4": ModelPreset("claude-sonnet-4", 200000, 16384, "anthropic"),
    "claude-haiku-4-5": ModelPreset("claude-haiku-4-5", 200000, 8192, "anthropic"),
    "claude-haiku-4": ModelPreset("claude-haiku-4", 200000, 8192, "anthropic"),
    "claude-3-opus": ModelPreset("claude-3-opus", 200000, 4096, "anthropic"),
    "claude-3-sonnet": ModelPreset("claude-3-sonnet", 200000, 4096, "anthropic"),
    "claude-3-haiku": ModelPreset("claude-3-haiku", 200000, 4096, "anthropic"),
    "claude-3-5-sonnet": ModelPreset("claude-3-5-sonnet", 200000, 8192, "anthropic"),
    "claude-3-5-haiku": ModelPreset("claude-3-5-haiku", 200000, 8192, "anthropic"),

    # OpenAI GPT
    "gpt-4o": ModelPreset("gpt-4o", 128000, 16384, "openai"),
    "gpt-4o-mini": ModelPreset("gpt-4o-mini", 128000, 16384, "openai"),
    "gpt-4-turbo": ModelPreset("gpt-4-turbo", 128000, 4096, "openai"),
    "gpt-4": ModelPreset("gpt-4", 8192, 4096, "openai"),
    "gpt-4-32k": ModelPreset("gpt-4-32k", 32768, 4096, "openai"),
    "gpt-3.5-turbo": ModelPreset("gpt-3.5-turbo", 16385, 4096, "openai"),
    "gpt-3.5-turbo-16k": ModelPreset("gpt-3.5-turbo-16k", 16385, 4096, "openai"),
    "o1": ModelPreset("o1", 200000, 100000, "openai"),
    "o1-mini": ModelPreset("o1-mini", 128000, 65536, "openai"),
    "o1-preview": ModelPreset("o1-preview", 128000, 32768, "openai"),

    # GLM (Zhipu AI)
    "glm-4": ModelPreset("glm-4", 128000, 4096, "openai"),
    "glm-4-plus": ModelPreset("glm-4-plus", 128000, 4096, "openai"),
    "glm-4-air": ModelPreset("glm-4-air", 128000, 4096, "openai"),
    "glm-4-flash": ModelPreset("glm-4-flash", 128000, 4096, "openai"),
    "glm-5": ModelPreset("glm-5", 65536, 4096, "openai"),  # 64K

    # Qwen (Alibaba)
    "qwen-turbo": ModelPreset("qwen-turbo", 128000, 6144, "openai"),
    "qwen-plus": ModelPreset("qwen-plus", 128000, 6144, "openai"),
    "qwen-max": ModelPreset("qwen-max", 32768, 6144, "openai"),  # 32K
    "qwen-72b": ModelPreset("qwen-72b", 32768, 4096, "openai"),
    "qwen2.5-72b": ModelPreset("qwen2.5-72b", 131072, 8192, "openai"),

    # DeepSeek
    "deepseek-chat": ModelPreset("deepseek-chat", 64000, 4096, "openai"),  # 64K
    "deepseek-coder": ModelPreset("deepseek-coder", 64000, 4096, "openai"),

    # Yi (01.AI)
    "yi-large": ModelPreset("yi-large", 32768, 4096, "openai"),
    "yi-medium": ModelPreset("yi-medium", 16384, 4096, "openai"),

    # LLaMA variants (typical configurations)
    "llama-3-70b": ModelPreset("llama-3-70b", 8192, 4096, "openai"),
    "llama-3-8b": ModelPreset("llama-3-8b", 8192, 4096, "openai"),
    "llama-3.1-70b": ModelPreset("llama-3.1-70b", 131072, 4096, "openai"),  # 128K
    "llama-3.1-8b": ModelPreset("llama-3.1-8b", 131072, 4096, "openai"),  # 128K

    # Mistral
    "mistral-large": ModelPreset("mistral-large", 128000, 4096, "openai"),
    "mistral-medium": ModelPreset("mistral-medium", 32768, 4096, "openai"),
    "mistral-small": ModelPreset("mistral-small", 32768, 4096, "openai"),
    "mixtral-8x7b": ModelPreset("mixtral-8x7b", 32768, 4096, "openai"),
    "mixtral-8x22b": ModelPreset("mixtral-8x22b", 65536, 4096, "openai"),  # 64K
}


def get_model_preset(model: str) -> ModelPreset:
    """
    Get preset configuration for a model.

    Args:
        model: Model name (e.g., "claude-sonnet-4-6", "gpt-4o", "glm-5")

    Returns:
        ModelPreset: Configuration for the model, or default if unknown
    """
    # Normalize model name (lowercase, remove common prefixes)
    normalized = model.lower().strip()

    # Direct lookup
    if normalized in MODEL_PRESETS:
        return MODEL_PRESETS[normalized]

    # Try partial matching for model name variations
    for key, preset in MODEL_PRESETS.items():
        if normalized in key or key in normalized:
            return preset

    # Return default preset for unknown models
    return DEFAULT_PRESET


def parse_context_window(context_window: int | str, model: str | None = None) -> int:
    """
    Parse context window specification to actual token count.

    Args:
        context_window: Can be:
            - int: Direct token count (e.g., 65536)
            - str: Level shortcut (e.g., "64k", "128k")
            - str: "auto" to use model preset
        model: Model name (required if context_window is "auto")

    Returns:
        int: Context window size in tokens

    Examples:
        >>> parse_context_window(65536)
        65536
        >>> parse_context_window("64k")
        65536
        >>> parse_context_window("auto", "glm-5")
        65536
    """
    if isinstance(context_window, int):
        return context_window

    if isinstance(context_window, str):
        # Check for level shortcuts
        level_lower = context_window.lower().strip()
        if level_lower in CONTEXT_LEVELS:
            return CONTEXT_LEVELS[level_lower]

        # Check for "auto"
        if level_lower == "auto":
            if model is None:
                return DEFAULT_PRESET.context_window
            return get_model_preset(model).context_window

        # Try to parse as integer string
        try:
            return int(context_window)
        except ValueError:
            pass

    # Fallback to default
    return DEFAULT_PRESET.context_window


def get_default_output_tokens(model: str) -> int:
    """
    Get default output tokens for a model.

    Args:
        model: Model name

    Returns:
        int: Default maximum output tokens
    """
    return get_model_preset(model).default_output_tokens
