"""
Skill controller - proxy to AgentHarness skill methods.

This controller wraps AgentHarness skill APIs for UI convenience,
providing change notifications and UI-friendly data structures.
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

# SDK imports
from harness import Skill

logger = logging.getLogger(__name__)


def get_skill_directory() -> Path:
    """
    Get the skill directory path (~/.harness/skills).

    Works on both Windows and Linux/macOS.

    Returns:
        Path to the skill directory
    """
    # Path.home() works correctly on all platforms
    # Windows: C:\Users\<user>\.harness\skills
    # Linux/macOS: /home/<user>/.harness/skills
    return Path.home() / ".harness" / "skills"


@dataclass
class SkillInfo:
    """Information about a skill."""

    name: str
    version: str
    description: str
    enabled: bool = True
    source_path: str | None = None  # Path to skill file for editing


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
        # Cache skills discovered from filesystem (before agent is available)
        self._cached_skills: dict[str, SkillInfo] = {}

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

    def _discover_skills_from_filesystem(self) -> list[SkillInfo]:
        """
        Discover skills from filesystem without loading full content.

        Scans ~/.harness/skills directory only (user-level skills).

        Returns:
            List of SkillInfo from filesystem
        """
        skill_dir = get_skill_directory()
        logger.info(f"[SkillController] Scanning skill directory: {skill_dir}, exists: {skill_dir.exists()}")

        if not skill_dir.exists():
            logger.info(f"[SkillController] Skill directory does not exist: {skill_dir}")
            return []

        skills = []

        # Recursively find all SKILL.md files (nested directories)
        for skill_file in skill_dir.rglob("SKILL.md"):
            try:
                skill_info = self._parse_skill_file(skill_file)
                if skill_info:
                    # Skip if already in cache (avoid duplicates)
                    if skill_info.name not in self._cached_skills:
                        logger.info(f"[SkillController] Found SKILL.md: {skill_file} -> {skill_info.name}")
                        skills.append(skill_info)
                        self._cached_skills[skill_info.name] = skill_info
                    else:
                        logger.info(f"[SkillController] Skipping duplicate skill: {skill_info.name} from {skill_file}")

            except Exception as e:
                logger.warning(f"Failed to read skill {skill_file}: {e}")

        # Also check for {name}.md files at top level
        for skill_file in skill_dir.glob("*.md"):
            if skill_file.name == "SKILL.md":
                continue
            try:
                skill_info = self._parse_skill_file(skill_file)
                if skill_info:
                    # Skip if already in cache (avoid duplicates)
                    if skill_info.name not in self._cached_skills:
                        logger.info(f"[SkillController] Found {skill_file.name} -> {skill_info.name}")
                        skills.append(skill_info)
                        self._cached_skills[skill_info.name] = skill_info
                    else:
                        logger.info(f"[SkillController] Skipping duplicate skill: {skill_info.name} from {skill_file}")

            except Exception as e:
                logger.warning(f"Failed to read skill {skill_file}: {e}")

        logger.info(f"[SkillController] _discover_skills_from_filesystem done, found {len(skills)} skills, cache size now: {len(self._cached_skills)}")
        return skills

    def _parse_skill_file(self, skill_file: Path) -> SkillInfo | None:
        """Parse a skill file and return SkillInfo."""
        content = skill_file.read_text(encoding="utf-8")
        if not content.startswith("---"):
            return None

        # Parse frontmatter
        end_idx = content.find("---", 3)
        if end_idx == -1:
            return None

        frontmatter = content[3:end_idx].strip()
        lines = frontmatter.split("\n")
        metadata = {}
        for line in lines:
            if ":" in line:
                key, value = line.split(":", 1)
                metadata[key.strip()] = value.strip()

        name = metadata.get("name", skill_file.stem)
        version = metadata.get("version", "1.0")
        description = metadata.get("description", "")

        return SkillInfo(
            name=name,
            version=version,
            description=description,
            enabled=True,
            source_path=str(skill_file),
        )

    def load_from_file(self, path: Path) -> bool:
        """
        Load a skill from file.

        Args:
            path: Path to skill file (.md)

        Returns:
            True if loaded successfully
        """
        # Cache skill info from file for UI display
        try:
            content = Path(path).read_text(encoding="utf-8")
            if content.startswith("---"):
                end_idx = content.find("---", 3)
                if end_idx != -1:
                    frontmatter = content[3:end_idx].strip()
                    lines = frontmatter.split("\n")
                    metadata = {}
                    for line in lines:
                        if ":" in line:
                            key, value = line.split(":", 1)
                            metadata[key.strip()] = value.strip()

                    name = metadata.get("name", Path(path).stem)
                    skill_info = SkillInfo(
                        name=name,
                        version=metadata.get("version", "1.0"),
                        description=metadata.get("description", ""),
                        enabled=True,
                        source_path=str(path),
                    )
                    self._cached_skills[name] = skill_info

                    if self._on_change:
                        self._on_change()
                    return True
        except Exception as e:
            logger.warning(f"Failed to load skill from {path}: {e}")

        # Also load into agent if available
        if self._agent:
            try:
                self._agent.load_skills_from_dir(path.parent)
            except Exception:
                pass

        return True

    def load_from_dir(self, path: Path) -> int:
        """
        Load all skills from directory.

        Args:
            path: Directory path

        Returns:
            Number of skills loaded
        """
        if self._agent:
            count = self._agent.load_skills_from_dir(path)
        else:
            # Cache from filesystem
            count = 0
            for skill_file in Path(path).glob("*.md"):
                if self.load_from_file(skill_file):
                    count += 1

        if self._on_change:
            self._on_change()
        return count

    def load_defaults(self) -> int:
        """
        Load skills from default directory (~/.harness/skills).

        This is the only directory the client reads skills from.
        Works on both Windows and Linux/macOS.

        Returns:
            Number of skills loaded
        """
        logger.info(f"[SkillController] load_defaults called, agent: {self._agent is not None}")
        if self._agent:
            # AgentHarness loads skills on init, just trigger callback
            if self._on_change:
                self._on_change()
            return len(self._agent.list_skills())

        # Discover from filesystem before agent is available
        skills = self._discover_skills_from_filesystem()
        if self._on_change:
            self._on_change()
        return len(skills)

    def get_skill_directory(self) -> Path:
        """
        Get the default skill directory path.

        Returns:
            Path to ~/.harness/skills
        """
        return get_skill_directory()

    def ensure_skill_directory(self) -> Path:
        """
        Ensure the skill directory exists.

        Creates ~/.harness/skills if it doesn't exist.

        Returns:
            Path to the skill directory
        """
        skill_dir = get_skill_directory()
        skill_dir.mkdir(parents=True, exist_ok=True)
        return skill_dir

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
        """
        Get list of all skills from ~/.harness/skills.

        Client only reads skills from ~/.harness/skills directory,
        not from project-level or other SDK default paths.

        Returns:
            List of SkillInfo from user-level skill directory
        """
        logger.info(f"[SkillController] get_skill_list called, cache size: {len(self._cached_skills)}")

        # Always return cached skills (populated from ~/.harness/skills only)
        # This ensures client only shows user-level skills, not project-level
        return list(self._cached_skills.values())

    def get_skill(self, name: str) -> SkillInfo | None:
        """
        Get a skill by name from ~/.harness/skills.

        Client only reads skills from ~/.harness/skills directory.

        Args:
            name: Skill name

        Returns:
            SkillInfo if found in user-level cache, None otherwise
        """
        return self._cached_skills.get(name)

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
