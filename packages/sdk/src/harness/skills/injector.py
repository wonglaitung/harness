"""
Skill Injector - Inject skills into system prompts.

Injects active and matching skills into the LLM's system prompt.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from harness.skills.base import Skill
    from harness.skills.registry import SkillRegistry


@dataclass
class InjectionConfig:
    """
    Configuration for skill injection.

    Controls how skills are injected into system prompts.
    """

    max_skills_per_prompt: int = 5
    max_skill_length: int = 2000
    inject_method: str = "append"  # append, prepend, section
    skill_separator: str = "\n\n---\n\n"


class SkillInjector:
    """
    Skill injector for system prompts.

    Injects relevant skills into the system prompt based on:
    - User input matching
    - Currently active skills
    """

    def __init__(
        self,
        registry: SkillRegistry,
        config: InjectionConfig | None = None,
    ):
        """
        Initialize injector.

        Args:
            registry: Skill registry to use
            config: Injection configuration
        """
        self.registry = registry
        self.config = config or InjectionConfig()

    def inject_skills(
        self,
        system_prompt: str,
        user_input: str,
        context: dict | None = None,
    ) -> str:
        """
        Inject skills into system prompt.

        Args:
            system_prompt: Original system prompt
            user_input: User's input text
            context: Optional context dictionary

        Returns:
            System prompt with skills injected
        """
        # Find matching skills
        matching_skills = self.registry.find_matching_skills(user_input)

        # Get active skills
        active_skills = self.registry.get_active_skills()

        # Merge and deduplicate
        all_skills = list({s.name: s for s in matching_skills + active_skills}.values())

        # Limit number of skills
        all_skills = all_skills[: self.config.max_skills_per_prompt]

        if not all_skills:
            return system_prompt

        # Build skill prompts
        skill_prompts = []
        for skill in all_skills:
            skill_prompt = self._format_skill(skill)
            # Truncate if too long
            if len(skill_prompt) > self.config.max_skill_length:
                skill_prompt = skill_prompt[: self.config.max_skill_length] + "\n...[truncated]"
            skill_prompts.append(skill_prompt)

        combined_skills = self.config.skill_separator.join(skill_prompts)

        # Inject based on method
        if self.config.inject_method == "append":
            return system_prompt + self.config.skill_separator + combined_skills
        elif self.config.inject_method == "prepend":
            return combined_skills + self.config.skill_separator + system_prompt
        elif self.config.inject_method == "section":
            return f"{system_prompt}\n\n# Active Skills\n\n{combined_skills}"
        else:
            return system_prompt + self.config.skill_separator + combined_skills

    def _format_skill(self, skill: Skill) -> str:
        """
        Format a skill for injection.

        Args:
            skill: Skill to format

        Returns:
            Formatted skill string
        """
        tools_section = ""
        if skill.tools.allowed:
            tools_section = f"\n\n### Available Tools\n{', '.join(skill.tools.allowed)}"
        elif skill.tools.restricted:
            tools_section = f"\n\n### Restricted Tools\n{', '.join(skill.tools.restricted)}"

        return f"""## Skill: {skill.name}

{skill.description}
{tools_section}

{skill.content}"""

    def get_tool_filter(self) -> Callable[[str], bool]:
        """
        Get a tool filter function.

        Returns:
            Function that returns True if a tool is allowed
        """
        return lambda tool_name: self.registry.is_tool_allowed(tool_name)

    def get_injection_preview(
        self,
        system_prompt: str,
        user_input: str,
    ) -> dict:
        """
        Get preview of what would be injected.

        Args:
            system_prompt: Original system prompt
            user_input: User's input text

        Returns:
            Dictionary with injection details
        """
        matching = self.registry.find_matching_skills(user_input)
        active = self.registry.get_active_skills()
        all_skills = list({s.name: s for s in matching + active}.values())

        return {
            "matching_skills": [s.name for s in matching],
            "active_skills": [s.name for s in active],
            "total_to_inject": len(all_skills[: self.config.max_skills_per_prompt]),
            "skill_names": [s.name for s in all_skills[: self.config.max_skills_per_prompt]],
            "original_prompt_length": len(system_prompt),
            "estimated_injected_length": len(
                self.inject_skills(system_prompt, user_input)
            ),
        }
