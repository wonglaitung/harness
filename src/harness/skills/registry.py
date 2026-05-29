"""
Skill Registry - Manage and lookup skills.

Provides registration, lookup, activation, and matching capabilities.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from harness.skills.base import Skill


@dataclass
class SkillRegistry:
    """
    Skill registry for managing and looking up skills.

    Features:
    - Register/unregister skills
    - Load skills from directories
    - Find matching skills for user input
    - Activate/deactivate skills
    - Check tool permissions
    """

    _skills: dict[str, Skill] = field(default_factory=dict)
    _active_skills: list[str] = field(default_factory=list)
    _skill_dirs: list[Path] = field(default_factory=list)

    def __init__(self):
        self._skills: dict[str, Skill] = {}
        self._active_skills: list[str] = []
        self._skill_dirs: list[Path] = []

    def add_skill_dir(self, directory: Path) -> None:
        """
        Add a skill directory and load all skills from it.

        Args:
            directory: Path to directory containing skill files
        """
        self._skill_dirs.append(directory)
        self._load_from_dir(directory)

    def _load_from_dir(self, directory: Path) -> None:
        """
        Load all skill files from a directory.

        Args:
            directory: Path to directory
        """
        if not directory.exists():
            return

        from harness.skills.base import Skill

        for skill_file in directory.glob("*.md"):
            try:
                skill = Skill.from_file(skill_file)
                self.register(skill)
            except Exception:
                # Skip invalid skill files
                continue

        # Also check subdirectories
        for subdir in directory.iterdir():
            if subdir.is_dir():
                self._load_from_dir(subdir)

    def register(self, skill: Skill) -> None:
        """
        Register a skill.

        If a skill with the same name exists, the newer version replaces it.

        Args:
            skill: Skill to register
        """
        if skill.name in self._skills:
            # Version check - replace if newer
            existing = self._skills[skill.name]
            if self._compare_versions(skill.version, existing.version) > 0:
                self._skills[skill.name] = skill
        else:
            self._skills[skill.name] = skill

    def _compare_versions(self, v1: str, v2: str) -> int:
        """
        Compare two version strings.

        Returns:
            Positive if v1 > v2, negative if v1 < v2, zero if equal
        """
        try:
            parts1 = [int(p) for p in v1.split(".")]
            parts2 = [int(p) for p in v2.split(".")]

            for p1, p2 in zip(parts1, parts2):
                if p1 != p2:
                    return p1 - p2

            return len(parts1) - len(parts2)
        except ValueError:
            # Non-numeric versions, compare as strings
            return (v1 > v2) - (v1 < v2)

    def unregister(self, name: str) -> bool:
        """
        Unregister a skill.

        Args:
            name: Skill name to unregister

        Returns:
            True if skill was unregistered, False if not found
        """
        if name in self._skills:
            del self._skills[name]
            if name in self._active_skills:
                self._active_skills.remove(name)
            return True
        return False

    def get(self, name: str) -> Skill | None:
        """
        Get a skill by name.

        Args:
            name: Skill name

        Returns:
            Skill instance or None if not found
        """
        return self._skills.get(name)

    def list_skills(self) -> list[Skill]:
        """
        List all registered skills.

        Returns:
            List of all skills
        """
        return list(self._skills.values())

    def find_matching_skills(self, user_input: str) -> list[Skill]:
        """
        Find skills that match the user input.

        Args:
            user_input: User's input text

        Returns:
            List of matching skills
        """
        matches = []
        for skill in self._skills.values():
            if skill.should_activate(user_input):
                matches.append(skill)
        return matches

    def activate(self, skill_name: str) -> bool:
        """
        Activate a skill.

        Args:
            skill_name: Name of skill to activate

        Returns:
            True if activated, False if not found
        """
        if skill_name in self._skills:
            if skill_name not in self._active_skills:
                self._active_skills.append(skill_name)
            return True
        return False

    def deactivate(self, skill_name: str) -> bool:
        """
        Deactivate a skill.

        Args:
            skill_name: Name of skill to deactivate

        Returns:
            True if deactivated, False if not active
        """
        if skill_name in self._active_skills:
            self._active_skills.remove(skill_name)
            return True
        return False

    def get_active_skills(self) -> list[Skill]:
        """
        Get all currently active skills.

        Returns:
            List of active skills
        """
        return [
            self._skills[name]
            for name in self._active_skills
            if name in self._skills
        ]

    def clear_active(self) -> None:
        """Clear all active skills."""
        self._active_skills.clear()

    def is_tool_allowed(self, tool_name: str) -> bool:
        """
        Check if a tool is allowed across all active skills.

        Args:
            tool_name: Name of tool to check

        Returns:
            True if tool is allowed by all active skills
        """
        active = self.get_active_skills()
        if not active:
            return True  # No active skills means all tools allowed

        for skill in active:
            if not skill.tools.is_allowed(tool_name):
                return False
        return True

    def reload(self) -> None:
        """
        Reload all skills from registered directories.
        """
        self._skills.clear()
        self._active_skills.clear()
        for directory in self._skill_dirs:
            self._load_from_dir(directory)

    def __len__(self) -> int:
        return len(self._skills)

    def __contains__(self, name: str) -> bool:
        return name in self._skills

    def __iter__(self):
        return iter(self._skills.values())