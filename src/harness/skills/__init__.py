"""
Skills System - Define agent behavior boundaries and capabilities.

Skills are structured, modular capability units that guide the LLM
on how to execute specific tasks.
"""

from harness.skills.base import (
    Skill,
    SkillParameter,
    SkillTools,
    SkillTrigger,
)
from harness.skills.injector import InjectionConfig, SkillInjector
from harness.skills.loader import SkillLoader
from harness.skills.registry import SkillRegistry

__all__ = [
    # Core classes
    "Skill",
    "SkillTrigger",
    "SkillTools",
    "SkillParameter",
    # Registry
    "SkillRegistry",
    # Injection
    "SkillInjector",
    "InjectionConfig",
    # Loading
    "SkillLoader",
]
