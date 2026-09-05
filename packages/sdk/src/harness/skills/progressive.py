"""
Progressive Skill Loader - Three-level skill loading for context efficiency.

Progressive loading reduces context consumption by loading skills in stages:
- Level 1: Frontmatter only (~100 tokens) - name, description, triggers
- Level 2: Full content (~1000-2000 tokens) - complete skill content
- Level 3: Reference files (on demand) - external files referenced by skill

Usage:
    from harness.skills.progressive import ProgressiveSkillLoader, SkillMetadata

    loader = ProgressiveSkillLoader()

    # Level 1: Load all skill metadata
    all_skills = loader.load_all_metadata(skills_dir)

    # Build context with available skills
    skill_list = [f"- {s.name}: {s.description}" for s in all_skills]

    # Level 2: Load full content for matched skills
    matched = loader.match_skills(user_input, all_skills)
    for skill_meta in matched:
        skill = loader.load_full_content(skill_meta)
        # Inject into context
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

import yaml

if TYPE_CHECKING:
    from harness.skills.base import Skill

logger = logging.getLogger(__name__)


class LoadingLevel:
    """Skill loading levels."""

    FRONTMATTER = 1  # Metadata only
    FULL_CONTENT = 2  # Complete skill content
    REFERENCES = 3  # Including reference files


@dataclass
class SkillMetadata:
    """
    Lightweight skill metadata for Level 1 loading.

    Contains only essential information for skill listing and matching.
    Approximately 50-100 tokens per skill.
    """

    name: str
    description: str
    path: Path
    triggers: dict[str, list[str]] = field(default_factory=dict)
    version: str = "1.0.0"

    # Cached full skill (loaded on demand)
    _skill: Skill | None = field(default=None, repr=False)
    _loaded: bool = field(default=False, repr=False)

    def to_list_item(self) -> str:
        """Format as a list item for skill selection."""
        return f"- {self.name}: {self.description}"

    def matches(self, text: str | list) -> bool:
        """Check if text matches this skill's triggers.

        Args:
            text: Can be a string or a multimodal content list.
                  For multimodal, only the text blocks are checked.
        """
        # Handle multimodal content (list of dicts)
        if isinstance(text, list):
            # Extract text from multimodal content
            text_content = ""
            for block in text:
                if isinstance(block, dict) and block.get("type") == "text":
                    text_content += block.get("text", "")
            text = text_content

        if not text or not isinstance(text, str):
            return False

        keywords = self.triggers.get("keywords", [])
        patterns = self.triggers.get("patterns", [])

        text_lower = text.lower()

        # Keyword matching
        for keyword in keywords:
            if keyword.lower() in text_lower:
                return True

        # Pattern matching
        for pattern in patterns:
            try:
                if re.search(pattern, text, re.IGNORECASE):
                    return True
            except re.error:
                continue

        return False


@dataclass
class ProgressiveLoadResult:
    """Result of progressive loading operation."""

    level: int
    skills: list[SkillMetadata | Skill]
    total_tokens_estimate: int
    loaded_from_cache: int = 0


class ProgressiveSkillLoader:
    """
    Progressive skill loader for context-efficient skill management.

    Implements three-level loading:
    1. Level 1 (Frontmatter): Load only metadata for all skills
    2. Level 2 (Full Content): Load complete content for matched skills
    3. Level 3 (References): Load reference files on demand

    Example:
        loader = ProgressiveSkillLoader()

        # Discover all skills
        all_skills = loader.discover_skills(Path("./skills"))

        # Build skill selection prompt
        available = "\\n".join([s.to_list_item() for s in all_skills])
        prompt = f"Available skills:\\n{available}"

        # Match skills to user input
        matched = loader.match_skills("Write a test", all_skills)

        # Load full content for matched skills
        for meta in matched:
            skill = loader.load_full_content(meta)
            # Use skill.content in context
    """

    def __init__(self, cache_size: int = 50):
        """
        Initialize the progressive loader.

        Args:
            cache_size: Maximum number of skills to cache in memory
        """
        self._metadata_cache: dict[str, SkillMetadata] = {}
        self._skill_cache: dict[str, Skill] = {}
        self._cache_size = cache_size

    def discover_skills(self, directory: Path) -> list[SkillMetadata]:
        """
        Discover all skills in a directory (Level 1 loading).

        Only reads frontmatter, not full content.

        Args:
            directory: Directory to search for skills

        Returns:
            List of skill metadata
        """
        skills = []

        if not directory.exists():
            return skills

        for skill_file in directory.rglob("*.md"):
            try:
                metadata = self._load_frontmatter_only(skill_file)
                if metadata:
                    skills.append(metadata)
                    self._metadata_cache[metadata.name] = metadata
            except Exception as e:
                logger.debug(f"Failed to load skill from {skill_file}: {e}")

        return skills

    def _load_frontmatter_only(self, path: Path) -> SkillMetadata | None:
        """
        Load only frontmatter from a skill file.

        Args:
            path: Path to skill file

        Returns:
            SkillMetadata or None if not a valid skill
        """
        content = path.read_text(encoding="utf-8")

        if not content.startswith("---"):
            return None

        parts = content.split("---", 2)
        if len(parts) < 3:
            return None

        try:
            frontmatter = yaml.safe_load(parts[1]) or {}
        except yaml.YAMLError:
            return None

        # Check if it's a valid skill
        if "name" not in frontmatter and "description" not in frontmatter:
            return None

        return SkillMetadata(
            name=frontmatter.get("name", path.stem),
            description=frontmatter.get("description", ""),
            path=path,
            triggers=frontmatter.get("triggers", {}),
            version=frontmatter.get("version", "1.0.0"),
        )

    def load_full_content(self, metadata: SkillMetadata) -> Skill:
        """
        Load full skill content (Level 2 loading).

        Args:
            metadata: Skill metadata from Level 1

        Returns:
            Full Skill instance
        """
        from harness.skills.base import Skill

        # Check cache
        if metadata._loaded and metadata._skill:
            return metadata._skill

        # Check global cache
        if metadata.name in self._skill_cache:
            cached = self._skill_cache[metadata.name]
            metadata._skill = cached
            metadata._loaded = True
            return cached

        # Load from file
        skill = Skill.from_file(metadata.path)

        # Update cache
        metadata._skill = skill
        metadata._loaded = True

        # Add to global cache (with LRU eviction)
        if len(self._skill_cache) >= self._cache_size:
            # Remove oldest entry
            oldest_key = next(iter(self._skill_cache))
            del self._skill_cache[oldest_key]

        self._skill_cache[metadata.name] = skill

        return skill

    def match_skills(
        self,
        text: str | list,
        skills: list[SkillMetadata],
        max_matches: int = 3,
    ) -> list[SkillMetadata]:
        """
        Match skills to user input text.

        Args:
            text: User input - can be a string or multimodal content list
            skills: List of skill metadata
            max_matches: Maximum number of matches to return

        Returns:
            List of matching skill metadata
        """
        matches = []

        for skill in skills:
            if skill.matches(text):
                matches.append(skill)
                if len(matches) >= max_matches:
                    break

        return matches

    def load_with_references(
        self,
        metadata: SkillMetadata,
        reference_loader: callable | None = None,
    ) -> tuple[Skill, list[str]]:
        """
        Load skill with all references (Level 3 loading).

        Args:
            metadata: Skill metadata
            reference_loader: Optional custom reference loader

        Returns:
            Tuple of (Skill, list of reference contents)
        """
        skill = self.load_full_content(metadata)
        references = []

        # Extract reference patterns from skill content
        # Look for patterns like: @file:path, [reference](path), etc.
        content = skill.content

        # Pattern: @file:path or @path
        file_refs = re.findall(r"@(?:file:)?([^\s,]+)", content)

        for ref_path in file_refs:
            try:
                # Resolve relative to skill directory
                full_path = metadata.path.parent / ref_path
                if full_path.exists():
                    ref_content = full_path.read_text(encoding="utf-8")
                    references.append(f"--- {ref_path} ---\n{ref_content}")
            except Exception as e:
                logger.debug(f"Failed to load reference {ref_path}: {e}")

        return skill, references

    def build_skill_selection_prompt(
        self,
        skills: list[SkillMetadata],
        format_style: str = "list",
    ) -> str:
        """
        Build a prompt for skill selection.

        Args:
            skills: List of skill metadata
            format_style: Output format ("list", "markdown", "compact")

        Returns:
            Formatted skill list string
        """
        if not skills:
            return "No skills available."

        if format_style == "list":
            return "\\n".join([s.to_list_item() for s in skills])

        elif format_style == "markdown":
            lines = ["## Available Skills\\n"]
            for skill in skills:
                lines.append(f"### {skill.name}")
                lines.append(f"{skill.description}\\n")
            return "\\n".join(lines)

        elif format_style == "compact":
            # Ultra-compact format for token efficiency
            return " | ".join([f"{s.name}: {s.description[:50]}" for s in skills])

        else:
            return "\\n".join([s.to_list_item() for s in skills])

    def estimate_tokens(self, skills: list[SkillMetadata | Skill], level: int = 1) -> int:
        """
        Estimate token count for a list of skills.

        Args:
            skills: List of skill metadata or full skills
            level: Loading level (1 = frontmatter, 2 = full)

        Returns:
            Estimated token count
        """
        total = 0

        for skill in skills:
            if isinstance(skill, SkillMetadata):
                if level == 1:
                    # Metadata only: ~50-100 tokens
                    total += 50 + len(skill.name) // 4 + len(skill.description) // 4
                elif level == 2:
                    # Need to estimate full content
                    total += 500  # Rough estimate
            else:
                # Full Skill object
                total += 100 + len(skill.content) // 4

        return total

    def clear_cache(self) -> None:
        """Clear all cached skills."""
        self._metadata_cache.clear()
        self._skill_cache.clear()
