"""
Skill Injector - Inject skills into system prompts.

Injects active and matching skills into the LLM's system prompt.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from harness.skills.base import Skill
    from harness.skills.registry import SkillRegistry

logger = logging.getLogger(__name__)


@dataclass
class InjectionConfig:
    """
    Configuration for skill injection.

    Controls how skills are injected into system prompts.
    """

    max_skills_per_prompt: int = 5
    max_skill_length: int = 0  # 0 = no limit, user controls via logging
    warn_skill_length: int = 8000  # Log warning if skill exceeds this length
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
        logger.debug(f"[SkillInjector] Matching skills: {[s.name for s in matching_skills]}")

        # Get active skills
        active_skills = self.registry.get_active_skills()
        logger.info(f"[SkillInjector] Active skills: {[s.name for s in active_skills]}")

        # Merge and deduplicate
        all_skills = list({s.name: s for s in matching_skills + active_skills}.values())

        # Limit number of skills
        all_skills = all_skills[: self.config.max_skills_per_prompt]

        if not all_skills:
            logger.debug(f"No skills matched for input: {user_input[:50]}...")
            return system_prompt

        logger.info(f"Injecting {len(all_skills)} skills: {[s.name for s in all_skills]}")

        # Build skill prompts
        skill_prompts = []
        for skill in all_skills:
            skill_prompt = self._format_skill(skill)

            # Check length and log warning if too long (but don't truncate)
            skill_len = len(skill_prompt)
            if self.config.warn_skill_length > 0 and skill_len > self.config.warn_skill_length:
                logger.warning(
                    f"Skill '{skill.name}' is {skill_len} chars (>{self.config.warn_skill_length}). "
                    f"Consider shortening for better LLM performance."
                )

            # Only truncate if max_skill_length is explicitly set (> 0)
            if self.config.max_skill_length > 0 and skill_len > self.config.max_skill_length:
                skill_prompt = skill_prompt[: self.config.max_skill_length] + "\n...[truncated]"
                logger.warning(
                    f"Skill '{skill.name}' truncated from {skill_len} to {self.config.max_skill_length} chars"
                )

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
        # Add skill directory path info
        skill_dir_info = ""
        if skill.source_path:
            skill_dir = Path(skill.source_path).parent
            skill_dir_info = f"\n\n**Skill Directory**: `{skill_dir}`"

        tools_section = ""
        if skill.tools.allowed:
            tools_section = f"\n\n### Available Tools\n{', '.join(skill.tools.allowed)}"
        elif skill.tools.restricted:
            tools_section = f"\n\n### Restricted Tools\n{', '.join(skill.tools.restricted)}"

        return f"""## Skill: {skill.name}

{skill.description}{skill_dir_info}{tools_section}

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
