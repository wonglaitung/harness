"""
Skill controller - manages skill loading and injection.
"""

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

# SDK imports
from harness import Skill, SkillInjector, SkillLoader, SkillRegistry


@dataclass
class SkillInfo:
    """Information about a skill."""

    name: str
    version: str
    description: str
    enabled: bool = True
    file_path: Path | None = None


class SkillController:
    """
    Controller for managing skills.

    Features:
    - Load skills from files/directories
    - Enable/disable skills
    - Inject skills into prompts
    - Create/edit skill files
    """

    def __init__(self):
        self.registry = SkillRegistry()
        self.loader = SkillLoader(self.registry)
        self.injector = SkillInjector(self.registry)
        self.skills: dict[str, SkillInfo] = {}
        self._on_change: Callable | None = None

    def set_change_callback(self, callback: Callable[[], None]):
        """Set callback for skill list changes."""
        self._on_change = callback

    def load_from_file(self, path: Path) -> bool:
        """
        Load a skill from file.

        Args:
            path: Path to skill file (.md)

        Returns:
            True if loaded successfully
        """
        try:
            skill = Skill.from_file(path)
            self.registry.register(skill)
            self.skills[skill.name] = SkillInfo(
                name=skill.name,
                version=skill.version,
                description=skill.description,
                enabled=True,
                file_path=path,
            )
            if self._on_change:
                self._on_change()
            return True
        except Exception:
            return False

    def load_from_dir(self, path: Path) -> int:
        """
        Load all skills from directory.

        Args:
            path: Directory path

        Returns:
            Number of skills loaded
        """
        count = self.loader.load_from_dir(path)

        # Update local tracking
        for skill in self.registry.list_skills():
            if skill.name not in self.skills:
                self.skills[skill.name] = SkillInfo(
                    name=skill.name,
                    version=skill.version,
                    description=skill.description,
                    enabled=True,
                )

        if self._on_change:
            self._on_change()
        return count

    def load_defaults(self) -> int:
        """Load skills from default directories."""
        count = self.loader.load_defaults()

        # Update local tracking
        for skill in self.registry.list_skills():
            if skill.name not in self.skills:
                self.skills[skill.name] = SkillInfo(
                    name=skill.name,
                    version=skill.version,
                    description=skill.description,
                    enabled=True,
                )

        if self._on_change:
            self._on_change()
        return count

    def enable_skill(self, name: str):
        """Enable a skill."""
        if name in self.skills:
            self.skills[name].enabled = True
            if self._on_change:
                self._on_change()

    def disable_skill(self, name: str):
        """Disable a skill."""
        if name in self.skills:
            self.skills[name].enabled = False
            if self._on_change:
                self._on_change()

    def remove_skill(self, name: str):
        """Remove a skill from registry."""
        if name in self.skills:
            del self.skills[name]
            # Note: SkillRegistry doesn't have unregister, so we just remove from local
            if self._on_change:
                self._on_change()

    def inject_skills(self, base_prompt: str, user_input: str) -> str:
        """
        Inject matching skills into the prompt.

        Args:
            base_prompt: Original system prompt
            user_input: User's input message

        Returns:
            Enhanced prompt with skill content
        """
        return self.injector.inject_skills(base_prompt, user_input)

    def get_matching_skills(self, user_input: str) -> list[Skill]:
        """
        Get skills that match the user input.

        Args:
            user_input: User's input message

        Returns:
            List of matching skills
        """
        return self.registry.find_matching_skills(user_input)

    def get_skill_list(self) -> list[SkillInfo]:
        """Get list of all loaded skills."""
        return list(self.skills.values())

    def get_skill(self, name: str) -> Skill | None:
        """Get a skill by name."""
        return self.registry.get(name)

    def create_skill(
        self,
        path: Path,
        name: str,
        description: str,
        content: str,
        keywords: list[str] = None,
        patterns: list[str] = None,
    ) -> bool:
        """
        Create a new skill file.

        Args:
            path: File path to save
            name: Skill name
            description: Skill description
            content: Skill content (markdown)
            keywords: Trigger keywords
            patterns: Trigger patterns (regex)

        Returns:
            True if created successfully
        """
        try:
            from harness import SkillTrigger

            skill = Skill(
                name=name,
                description=description,
                content=content,
                triggers=SkillTrigger(
                    keywords=keywords or [],
                    patterns=patterns or [],
                ),
            )

            skill.to_file(path)
            self.load_from_file(path)
            return True

        except Exception:
            return False

    def update_skill(self, name: str, **kwargs) -> bool:
        """
        Update a skill's properties.

        Args:
            name: Skill name
            **kwargs: Properties to update

        Returns:
            True if updated successfully
        """
        if name not in self.skills:
            return False

        info = self.skills[name]
        for key, value in kwargs.items():
            if hasattr(info, key):
                setattr(info, key, value)

        if self._on_change:
            self._on_change()
        return True
