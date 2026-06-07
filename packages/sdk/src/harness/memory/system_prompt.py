"""
Dynamic System Prompt Assembly.

Supports loading system prompts from multiple sources:
- Base system prompt (from config)
- AGENTS.md file in project root (project-specific instructions)
- MEMORY.md file for persistent context
- Custom system prompt providers

This enables project-level conventions and agent customization.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

logger = logging.getLogger(__name__)


@dataclass
class SystemPromptSource:
    """A source for system prompt content."""

    name: str
    priority: int  # Higher priority = earlier in final prompt
    content: str | Callable[[], str] | None = None
    file_path: Path | None = None
    required: bool = False  # If True, error when file not found

    def get_content(self) -> str:
        """Get the content from this source."""
        if self.content is not None:
            if callable(self.content):
                return self.content()
            return self.content

        if self.file_path is not None:
            if self.file_path.exists():
                content = self.file_path.read_text(encoding="utf-8")
                logger.debug(f"Loaded system prompt from '{self.name}' ({self.file_path}): {len(content)} chars")
                return content
            else:
                logger.warning(f"System prompt file not found for '{self.name}': {self.file_path}")
                if self.required:
                    raise FileNotFoundError(f"Required system prompt file not found: {self.file_path}")
                return ""

        return ""


@dataclass
class SystemPromptConfig:
    """Configuration for dynamic system prompt assembly."""

    base_prompt: str = ""

    # File sources
    agents_md_path: Path | None = None  # Path to AGENTS.md
    memory_md_path: Path | None = None  # Path to MEMORY.md

    # Project root for auto-discovery
    project_root: Path | None = None

    # Enable auto-discovery of AGENTS.md and MEMORY.md
    auto_discover: bool = True

    # Custom sources (name -> source)
    custom_sources: dict[str, SystemPromptSource] = field(default_factory=dict)

    # Separator between sections
    section_separator: str = "\n\n---\n\n"


class SystemPromptBuilder:
    """
    Builds system prompts from multiple sources.

    Priority order (highest first):
    1. Base system prompt
    2. Custom sources (sorted by priority)
    3. AGENTS.md (project instructions)
    4. MEMORY.md (persistent context)

    Example:
        builder = SystemPromptBuilder(
            config=SystemPromptConfig(
                base_prompt="You are a helpful assistant.",
                project_root=Path("/path/to/project"),
            )
        )

        full_prompt = builder.build()
    """

    def __init__(self, config: SystemPromptConfig | None = None):
        self.config = config or SystemPromptConfig()
        self._sources: list[SystemPromptSource] = []
        self._setup_default_sources()

    def _setup_default_sources(self) -> None:
        """Set up default sources based on config."""
        self._sources = []

        # Base prompt (highest priority)
        if self.config.base_prompt:
            self._sources.append(SystemPromptSource(
                name="base",
                priority=100,
                content=self.config.base_prompt,
            ))

        # AGENTS.md (project instructions)
        agents_path = self.config.agents_md_path
        if agents_path is None and self.config.project_root and self.config.auto_discover:
            agents_path = self.config.project_root / "AGENTS.md"

        if agents_path is not None:
            self._sources.append(SystemPromptSource(
                name="AGENTS.md",
                priority=50,
                file_path=agents_path,
            ))

        # MEMORY.md (persistent context)
        memory_path = self.config.memory_md_path
        if memory_path is None and self.config.project_root and self.config.auto_discover:
            memory_path = self.config.project_root / "MEMORY.md"

        if memory_path is not None:
            self._sources.append(SystemPromptSource(
                name="MEMORY.md",
                priority=40,
                file_path=memory_path,
            ))

        # Custom sources
        for name, source in self.config.custom_sources.items():
            self._sources.append(source)

        # Sort by priority (highest first)
        self._sources.sort(key=lambda s: s.priority, reverse=True)

    def add_source(self, source: SystemPromptSource) -> None:
        """Add a new source to the builder."""
        self._sources.append(source)
        self._sources.sort(key=lambda s: s.priority, reverse=True)

    def remove_source(self, name: str) -> bool:
        """Remove a source by name. Returns True if found and removed."""
        for i, source in enumerate(self._sources):
            if source.name == name:
                self._sources.pop(i)
                return True
        return False

    def build(self) -> str:
        """
        Build the full system prompt from all sources.

        Returns:
            Combined system prompt string
        """
        sections = []
        logger.debug(f"Building system prompt from {len(self._sources)} sources: {[s.name for s in self._sources]}")

        for source in self._sources:
            try:
                content = source.get_content()
                if content.strip():
                    sections.append(content)
                    logger.debug(f"Added system prompt section from '{source.name}': {len(content)} chars")
                else:
                    logger.debug(f"Skipped empty system prompt section from '{source.name}'")
            except FileNotFoundError as e:
                logger.warning(f"System prompt source '{source.name}' not found: {e}")
                if source.required:
                    raise
            except Exception as e:
                logger.exception(f"Error loading system prompt source '{source.name}': {e}")
                if source.required:
                    raise

        return self.config.section_separator.join(sections)

    def get_available_sources(self) -> list[str]:
        """Get list of source names that have content."""
        available = []
        for source in self._sources:
            try:
                content = source.get_content()
                if content.strip():
                    available.append(source.name)
            except Exception:
                pass
        return available

    def get_source_content(self, name: str) -> str | None:
        """Get content from a specific source."""
        for source in self._sources:
            if source.name == name:
                try:
                    return source.get_content()
                except Exception:
                    return None
        return None


def discover_project_context(project_root: Path | None = None) -> dict[str, str]:
    """
    Discover project context from AGENTS.md, MEMORY.md, and other sources.

    Args:
        project_root: Project root directory. If None, uses current directory.

    Returns:
        Dict mapping source name to content
    """
    root = project_root or Path.cwd()
    context = {}

    # Check for AGENTS.md
    agents_md = root / "AGENTS.md"
    if agents_md.exists():
        context["AGENTS.md"] = agents_md.read_text(encoding="utf-8")

    # Check for MEMORY.md
    memory_md = root / "MEMORY.md"
    if memory_md.exists():
        context["MEMORY.md"] = memory_md.read_text(encoding="utf-8")

    # Check for CLAUDE.md (Claude Code format)
    claude_md = root / "CLAUDE.md"
    if claude_md.exists():
        context["CLAUDE.md"] = claude_md.read_text(encoding="utf-8")

    return context
