"""
Skill controller - proxy to AgentHarness skill methods.

This controller wraps AgentHarness skill APIs for UI convenience,
providing change notifications and UI-friendly data structures.
"""

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

# SDK imports
from harness import Skill


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
    Controller for managing skills - proxies to AgentHarness.

    This is a thin wrapper around AgentHarness skill methods,
    adding UI-specific features like change callbacks.
    """

    def __init__(self):
        # AgentHarness instance (set by set_agent)
        self._agent = None
        self._on_change: Callable | None = None
        # Local cache for UI display (enabled/disabled state)
        self._skill_states: dict[str, bool] = {}

    def set_agent(self, agent) -> None:
        """
        Set the AgentHarness instance to proxy to.

        Args:
            agent: AgentHarness instance
        """
        self._agent = agent
        if self._on_change:
            self._on_change()

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
        if not self._agent:
            return False
        try:
            count = self._agent.load_skills_from_dir(path.parent)
            if self._on_change:
                self._on_change()
            return count > 0
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
        if not self._agent:
            return 0
        count = self._agent.load_skills_from_dir(path)
        if self._on_change:
            self._on_change()
        return count

    def load_defaults(self) -> int:
        """Load skills from default directories."""
        if not self._agent:
            return 0
        # AgentHarness loads skills on init, just trigger callback
        if self._on_change:
            self._on_change()
        return len(self._agent.list_skills())

    def enable_skill(self, name: str):
        """Enable a skill."""
        if self._agent:
            self._agent.activate_skill(name)
            self._skill_states[name] = True
            if self._on_change:
                self._on_change()

    def disable_skill(self, name: str):
        """Disable a skill."""
        if self._agent:
            self._agent.deactivate_skill(name)
            self._skill_states[name] = False
            if self._on_change:
                self._on_change()

    def remove_skill(self, name: str):
        """Remove a skill from registry."""
        # Note: SDK doesn't have unregister, just mark as disabled
        self._skill_states[name] = False
        if self._on_change:
            self._on_change()

    def inject_skills(self, base_prompt: str, user_input: str) -> str:
        """
        Inject matching skills into the prompt.

        Note: This is handled automatically by AgentHarness.run(),
        but kept for backward compatibility.

        Args:
            base_prompt: Original system prompt
            user_input: User's input message

        Returns:
            Enhanced prompt with skill content
        """
        # AgentHarness handles injection internally
        return base_prompt

    def get_matching_skills(self, user_input: str) -> list[Skill]:
        """
        Get skills that match the user input.

        Args:
            user_input: User's input message

        Returns:
            List of matching skills
        """
        if not self._agent:
            return []
        return self._agent.get_matching_skills(user_input)

    def get_skill_list(self) -> list[SkillInfo]:
        """Get list of all discovered skills (including metadata-only)."""
        if not self._agent:
            return []

        skills = []
        # Use list_discovered_skills() to get all skills (Level 1 metadata)
        for meta in self._agent.list_discovered_skills():
            enabled = self._skill_states.get(meta.name, True)
            skills.append(SkillInfo(
                name=meta.name,
                version=meta.version,
                description=meta.description,
                enabled=enabled,
            ))
        return skills

    def get_skill(self, name: str) -> Skill | None:
        """Get a skill by name."""
        if not self._agent:
            return None
        return self._agent.get_skill(name)

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

            # Load into agent if available
            if self._agent:
                self._agent.load_skills_from_dir(path.parent)

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
        # Update local state
        if 'enabled' in kwargs:
            self._skill_states[name] = kwargs['enabled']

        if self._on_change:
            self._on_change()
        return True
