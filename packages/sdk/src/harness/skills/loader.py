"""
Skill Loader - Load skills from files and directories.

Handles discovery and loading of skill files from various locations.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from harness.skills.base import Skill
    from harness.skills.registry import SkillRegistry


# Default skill search paths (in priority order)
DEFAULT_SKILL_PATHS = [
    Path("./.agent/skills"),  # Project-level (highest priority)
    Path("./skills"),  # Project-level (alternate)
    Path("~/.harness/skills").expanduser(),  # User-level
    Path("~/.harness/shared-skills").expanduser(),  # Shared
]


class SkillLoader:
    """
    Skill loader for loading skills from files and directories.

    Features:
    - Load from file paths
    - Load from directories
    - Auto-discovery of skill files
    - Default skill directories
    """

    def __init__(self, registry: SkillRegistry):
        """
        Initialize loader.

        Args:
            registry: Skill registry to load into
        """
        self.registry = registry
        self.loaded_paths: list[Path] = []

    def load_defaults(self) -> int:
        """
        Load skills from default directories.

        Returns:
            Number of skills loaded
        """
        count = 0
        for directory in DEFAULT_SKILL_PATHS:
            if directory.exists():
                skills_loaded = self.load_from_dir(directory)
                count += skills_loaded
        return count

    def load_from_path(self, path: str | Path) -> bool:
        """
        Load skill from a file or directory path.

        Args:
            path: Path to file or directory

        Returns:
            True if loaded successfully
        """
        p = Path(path).expanduser()

        if p.is_file() and p.suffix == ".md":
            return self.load_from_file(p)
        elif p.is_dir():
            return self.load_from_dir(p) > 0

        return False

    def load_from_file(self, path: Path) -> bool:
        """
        Load a single skill file.

        Args:
            path: Path to skill file

        Returns:
            True if loaded successfully
        """
        from harness.skills.base import Skill

        try:
            skill = Skill.from_file(path)
            self.registry.register(skill)
            self.loaded_paths.append(path)
            return True
        except Exception:
            return False

    def load_from_dir(self, directory: Path) -> int:
        """
        Load all skill files from a directory.

        Args:
            directory: Path to directory

        Returns:
            Number of skills loaded
        """
        if not directory.exists():
            return 0

        count = 0
        for skill_file in self.discover_skills(directory):
            if self.load_from_file(skill_file):
                count += 1

        self.loaded_paths.append(directory)
        return count

    def discover_skills(self, directory: Path) -> list[Path]:
        """
        Discover all skill files in a directory.

        Args:
            directory: Path to search

        Returns:
            List of skill file paths
        """
        skill_files = []

        if not directory.exists():
            return skill_files

        # Search for .md files
        for md_file in directory.rglob("*.md"):
            # Check if it has skill frontmatter
            try:
                content = md_file.read_text(encoding="utf-8")
                if content.startswith("---"):
                    parts = content.split("---", 2)
                    if len(parts) >= 2:
                        frontmatter = parts[1]
                        # Check for skill markers
                        if "name:" in frontmatter or "description:" in frontmatter:
                            skill_files.append(md_file)
            except Exception:
                continue

        return skill_files

    async def load_from_url(self, url: str) -> bool:
        """
        Load skill from a URL (async).

        Args:
            url: URL to skill file

        Returns:
            True if loaded successfully
        """
        try:
            import aiohttp

            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        return False
                    content = await response.text()

            # Create temp file
            temp_path = Path("/tmp") / Path(url).name
            temp_path.write_text(content, encoding="utf-8")

            # Load skill
            from harness.skills.base import Skill

            skill = Skill.from_file(temp_path)
            self.registry.register(skill)

            return True
        except Exception:
            return False

    def get_loaded_paths(self) -> list[Path]:
        """
        Get list of loaded paths.

        Returns:
            List of paths that were loaded
        """
        return self.loaded_paths.copy()

    def clear_loaded(self) -> None:
        """Clear loaded paths list."""
        self.loaded_paths.clear()
