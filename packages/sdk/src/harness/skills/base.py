"""
Skill base classes - Core skill definitions.

A Skill is a structured, modular capability unit containing:
- Trigger conditions: When to activate
- Tool permissions: Which tools can be used
- Behavior guidance: Execution steps and rules
- Output specification: Expected output format
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class SkillTrigger:
    """
    Skill trigger conditions.

    Defines when a skill should be activated based on:
    - Keywords: Simple text matching
    - Patterns: Regex pattern matching
    - Tools: Tool call triggers
    """

    keywords: list[str] = field(default_factory=list)
    patterns: list[str] = field(default_factory=list)
    tools: list[str] = field(default_factory=list)

    def matches(self, text: str) -> bool:
        """
        Check if text matches trigger conditions.

        Args:
            text: User input text to check

        Returns:
            True if any trigger condition matches
        """
        # Keyword matching (case-insensitive)
        text_lower = text.lower()
        for keyword in self.keywords:
            if keyword.lower() in text_lower:
                return True

        # Regex pattern matching
        for pattern in self.patterns:
            try:
                if re.search(pattern, text, re.IGNORECASE):
                    return True
            except re.error:
                # Invalid regex pattern, skip
                continue

        return False


@dataclass
class SkillTools:
    """
    Skill tool configuration.

    Defines which tools are allowed or restricted for a skill.
    """

    allowed: list[str] = field(default_factory=list)
    restricted: list[str] = field(default_factory=list)
    default_permission: str = "allow"  # allow, deny, ask

    def is_allowed(self, tool_name: str) -> bool:
        """
        Check if a tool is allowed.

        Args:
            tool_name: Name of the tool to check

        Returns:
            True if the tool is allowed
        """
        # Restricted tools are always denied
        if tool_name in self.restricted:
            return False

        # If no allowed list, use default permission
        if not self.allowed:
            return self.default_permission == "allow"

        # Check if in allowed list
        return tool_name in self.allowed


@dataclass
class SkillParameter:
    """
    Skill parameter definition.

    Defines a configurable parameter for a skill.
    """

    name: str
    type: str = "string"
    default: Any = None
    description: str = ""
    required: bool = False


@dataclass
class Skill:
    """
    Skill definition.

    A complete skill containing metadata, triggers, tools, and content.
    """

    name: str
    description: str
    content: str
    triggers: SkillTrigger = field(default_factory=SkillTrigger)
    tools: SkillTools = field(default_factory=SkillTools)
    parameters: list[SkillParameter] = field(default_factory=list)
    version: str = "1.0.0"
    author: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    source_path: str | None = None

    @classmethod
    def from_file(cls, path: Path) -> Skill:
        """
        Load skill from a markdown file with YAML frontmatter.

        Args:
            path: Path to the skill file

        Returns:
            Skill instance
        """
        content = path.read_text(encoding="utf-8")

        # Parse frontmatter
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                frontmatter = yaml.safe_load(parts[1]) or {}
                body = parts[2].strip()
            else:
                frontmatter = {}
                body = content
        else:
            frontmatter = {}
            body = content

        # Parse triggers
        triggers_data = frontmatter.get("triggers", {})
        triggers = SkillTrigger(
            keywords=triggers_data.get("keywords", []),
            patterns=triggers_data.get("patterns", []),
            tools=triggers_data.get("tools", []),
        )

        # Parse tools configuration
        tools_data = frontmatter.get("tools", {})
        tools = SkillTools(
            allowed=tools_data.get("allowed", []),
            restricted=tools_data.get("restricted", []),
            default_permission=tools_data.get("default_permission", "allow"),
        )

        # Parse parameters
        parameters: list[SkillParameter] = []
        params_data = frontmatter.get("parameters", {})
        for param_name, param_info in params_data.items():
            if isinstance(param_info, dict):
                parameters.append(
                    SkillParameter(
                        name=param_name,
                        type=param_info.get("type", "string"),
                        default=param_info.get("default"),
                        description=param_info.get("description", ""),
                        required=param_info.get("required", False),
                    )
                )

        return cls(
            name=frontmatter.get("name", path.stem),
            description=frontmatter.get("description", ""),
            content=body,
            triggers=triggers,
            tools=tools,
            parameters=parameters,
            version=frontmatter.get("version", "1.0.0"),
            author=frontmatter.get("author", ""),
            metadata=frontmatter.get("metadata", {}),
            source_path=str(path),
        )

    def to_file(self, path: Path) -> None:
        """
        Save skill to a markdown file with YAML frontmatter.

        Args:
            path: Path to save the skill file
        """
        frontmatter: dict[str, Any] = {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "author": self.author,
            "triggers": {
                "keywords": self.triggers.keywords,
                "patterns": self.triggers.patterns,
                "tools": self.triggers.tools,
            },
            "tools": {
                "allowed": self.tools.allowed,
                "restricted": self.tools.restricted,
                "default_permission": self.tools.default_permission,
            },
        }

        if self.parameters:
            frontmatter["parameters"] = {
                p.name: {
                    "type": p.type,
                    "default": p.default,
                    "description": p.description,
                    "required": p.required,
                }
                for p in self.parameters
            }

        if self.metadata:
            frontmatter["metadata"] = self.metadata

        content = f"---\n{yaml.dump(frontmatter, default_flow_style=False, allow_unicode=True)}---\n\n{self.content}"
        path.write_text(content, encoding="utf-8")

    def should_activate(self, user_input: str, context: dict | None = None) -> bool:
        """
        Determine if this skill should activate.

        Args:
            user_input: User's input text
            context: Optional context dictionary

        Returns:
            True if the skill should activate
        """
        return self.triggers.matches(user_input)

    def __str__(self) -> str:
        return f"Skill({self.name}, v{self.version})"

    def __repr__(self) -> str:
        return f"Skill(name={self.name!r}, description={self.description!r})"
