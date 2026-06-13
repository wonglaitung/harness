"""
Configuration loader for scraper.

Supports:
- YAML config file (~/.harness/scraper.yaml)
- Environment variables (HARNESS_LLM_*)
- Default values
"""

import os
from pathlib import Path

import yaml

from harness_scraper.models import ScraperConfig, LLMConfig, SourceConfig, OutputConfig


DEFAULT_CONFIG_PATH = Path.home() / ".harness" / "scraper.yaml"


def load_config(config_path: Path | str | None = None) -> ScraperConfig:
    """
    Load scraper configuration.

    Priority:
    1. Explicit config_path
    2. ~/.harness/scraper.yaml
    3. Environment variables
    4. Defaults

    Args:
        config_path: Optional explicit config file path

    Returns:
        ScraperConfig instance
    """
    if config_path is None:
        config_path = DEFAULT_CONFIG_PATH

    config_path = Path(config_path)

    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            yaml_config = yaml.safe_load(f) or {}
    else:
        yaml_config = {}

    # Merge with environment variables
    llm_config = _merge_llm_config(yaml_config.get("llm", {}))

    # Build complete config
    return ScraperConfig(
        llm=llm_config,
        sources=_build_source_config(yaml_config.get("sources", {})),
        output=_build_output_config(yaml_config.get("output", {})),
    )


def _merge_llm_config(yaml_llm: dict) -> LLMConfig:
    """Merge LLM config with environment variables"""
    return LLMConfig(
        provider=os.getenv("HARNESS_LLM_PROVIDER", yaml_llm.get("provider", "openai")),
        base_url=os.getenv("HARNESS_LLM_BASE_URL", yaml_llm.get("base_url", "https://api.openai.com/v1")),
        api_key=os.getenv("HARNESS_LLM_API_KEY", yaml_llm.get("api_key")),
        model=os.getenv("HARNESS_LLM_MODEL", yaml_llm.get("model", "gpt-4o-mini")),
        temperature=float(os.getenv("HARNESS_LLM_TEMPERATURE", yaml_llm.get("temperature", "0.1"))),
        max_tokens=int(os.getenv("HARNESS_LLM_MAX_TOKENS", yaml_llm.get("max_tokens", "2000"))),
    )


def _build_source_config(yaml_sources: dict) -> SourceConfig:
    """Build source config from YAML"""
    return SourceConfig(
        rss=yaml_sources.get("rss", []),
        hacker_news=yaml_sources.get("hacker_news", {"min_points": 150}),
        github_trending=yaml_sources.get("github_trending", {"languages": ["python", "typescript"], "since": "daily"}),
    )


def _build_output_config(yaml_output: dict) -> OutputConfig:
    """Build output config from YAML"""
    return OutputConfig(
        directory=yaml_output.get("directory", "~/.harness/scraper"),
    )


def create_default_config_file() -> Path:
    """Create default config file with template"""
    config_content = """# Harness Scraper Configuration
# https://github.com/wonglaitung/harness/tree/main/packages/scraper

# LLM Configuration - Used by SDK Agent
# Supports: vllm, ollama, openai, anthropic, or any OpenAI-compatible API
llm:
  provider: "openai"
  base_url: "https://api.openai.com/v1"
  api_key: ""  # Or set via HARNESS_LLM_API_KEY env var
  model: "gpt-4o-mini"
  temperature: 0.1
  max_tokens: 2000

  # Alternative: Local vLLM/Ollama
  # provider: "openai"
  # base_url: "http://localhost:8000/v1"
  # model: "Qwen2.5-7B-Instruct"

  # Alternative: SiliconFlow
  # provider: "openai"
  # base_url: "https://api.siliconflow.cn/v1"
  # api_key: "sk-xxx"
  # model: "Qwen/Qwen2.5-7B-Instruct"

  # Alternative: DeepSeek
  # provider: "openai"
  # base_url: "https://api.deepseek.com/v1"
  # api_key: "sk-xxx"
  # model: "deepseek-chat"

# Data Sources (供 Agent 参考)
sources:
  rss:
    - url: "https://openai.com/blog/rss.xml"
      name: "OpenAI Blog"
    - url: "https://huggingface.co/blog/feed.xml"
      name: "Hugging Face Blog"

  hacker_news:
    min_points: 150

  github_trending:
    languages: ["python", "typescript"]
    since: "daily"

# Output
output:
  directory: "~/.harness/scraper"
"""

    config_path = DEFAULT_CONFIG_PATH
    config_path.parent.mkdir(parents=True, exist_ok=True)

    with open(config_path, "w", encoding="utf-8") as f:
        f.write(config_content)

    return config_path
