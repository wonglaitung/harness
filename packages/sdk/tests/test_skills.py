"""
Tests for Skills System.
"""

from pathlib import Path

import pytest

from harness.skills import (
    Skill,
    SkillInjector,
    SkillLoader,
    SkillRegistry,
    SkillTools,
    SkillTrigger,
)


@pytest.fixture
def skill_registry():
    """Create a skill registry with test skills."""
    registry = SkillRegistry()
    registry.add_skill_dir(Path(__file__).parent / "fixtures" / "skills")
    return registry


class TestSkillTrigger:
    """Tests for SkillTrigger."""

    def test_keyword_match(self):
        """Test keyword matching."""
        trigger = SkillTrigger(keywords=["review", "check"])
        assert trigger.matches("please review this code")
        assert trigger.matches("CHECK the file")
        assert not trigger.matches("hello world")

    def test_pattern_match(self):
        """Test regex pattern matching."""
        trigger = SkillTrigger(patterns=[r"review\s+this", r"check\s+my"])
        assert trigger.matches("review this code")
        assert trigger.matches("please check my changes")
        assert not trigger.matches("review code")

    def test_empty_trigger(self):
        """Test empty trigger matches nothing."""
        trigger = SkillTrigger()
        assert not trigger.matches("any text")


class TestSkillTools:
    """Tests for SkillTools."""

    def test_allowed_tools(self):
        """Test allowed tools."""
        tools = SkillTools(allowed=["read", "write"])
        assert tools.is_allowed("read")
        assert tools.is_allowed("write")
        assert not tools.is_allowed("bash")

    def test_restricted_tools(self):
        """Test restricted tools override allowed."""
        tools = SkillTools(
            allowed=["read", "write", "bash"],
            restricted=["bash"]
        )
        assert tools.is_allowed("read")
        assert tools.is_allowed("write")
        assert not tools.is_allowed("bash")

    def test_default_permission(self):
        """Test default permission."""
        tools = SkillTools(default_permission="allow")
        assert tools.is_allowed("any_tool")

        tools = SkillTools(default_permission="deny")
        assert not tools.is_allowed("any_tool")


class TestSkill:
    """Tests for Skill."""

    def test_skill_loading(self, skill_registry):
        """Test skill loading from file."""
        skill = skill_registry.get("code-review")
        assert skill is not None
        assert skill.name == "code-review"
        assert "review" in skill.triggers.keywords

    def test_skill_activation(self):
        """Test skill activation check."""
        skill = Skill(
            name="test",
            description="Test skill",
            content="Test content",
            triggers=SkillTrigger(keywords=["test"]),
        )
        assert skill.should_activate("test this")
        assert not skill.should_activate("hello")

    def test_skill_to_file(self, tmp_path):
        """Test saving skill to file."""
        skill = Skill(
            name="test-skill",
            description="Test description",
            content="Test content",
            triggers=SkillTrigger(keywords=["test"]),
            tools=SkillTools(allowed=["read"]),
            version="1.0.0",
        )

        path = tmp_path / "test-skill.md"
        skill.to_file(path)

        # Load back and verify
        loaded = Skill.from_file(path)
        assert loaded.name == "test-skill"
        assert loaded.description == "Test description"
        assert loaded.content == "Test content"
        assert "test" in loaded.triggers.keywords
        assert "read" in loaded.tools.allowed


class TestSkillRegistry:
    """Tests for SkillRegistry."""

    def test_register_skill(self):
        """Test registering a skill."""
        registry = SkillRegistry()
        skill = Skill(
            name="test",
            description="Test",
            content="Content",
        )
        registry.register(skill)

        assert registry.get("test") == skill
        assert "test" in registry

    def test_unregister_skill(self):
        """Test unregistering a skill."""
        registry = SkillRegistry()
        skill = Skill(name="test", description="Test", content="Content")
        registry.register(skill)

        assert registry.unregister("test")
        assert registry.get("test") is None
        assert not registry.unregister("nonexistent")

    def test_find_matching_skills(self, skill_registry):
        """Test finding matching skills."""
        matches = skill_registry.find_matching_skills("review this code")
        assert len(matches) > 0
        assert any(s.name == "code-review" for s in matches)

    def test_activate_deactivate(self, skill_registry):
        """Test skill activation/deactivation."""
        assert skill_registry.activate("code-review")
        assert "code-review" in [s.name for s in skill_registry.get_active_skills()]

        assert skill_registry.deactivate("code-review")
        assert "code-review" not in [s.name for s in skill_registry.get_active_skills()]

    def test_tool_permission(self, skill_registry):
        """Test tool permission checking."""
        skill_registry.activate("code-review")

        assert skill_registry.is_tool_allowed("read")
        assert skill_registry.is_tool_allowed("grep")
        assert not skill_registry.is_tool_allowed("write")
        assert not skill_registry.is_tool_allowed("edit")


class TestSkillInjector:
    """Tests for SkillInjector."""

    def test_injection(self, skill_registry):
        """Test skill injection."""
        injector = SkillInjector(skill_registry)

        prompt = "You are an AI assistant."
        user_input = "review this code"

        result = injector.inject_skills(prompt, user_input)

        assert "code-review" in result
        assert len(result) > len(prompt)

    def test_no_matching_skill(self, skill_registry):
        """Test injection when no skill matches."""
        injector = SkillInjector(skill_registry)

        prompt = "You are an AI assistant."
        user_input = "hello world"  # No matching skill

        result = injector.inject_skills(prompt, user_input)

        # Should return original prompt when no match
        assert result == prompt

    def test_active_skill_injection(self, skill_registry):
        """Test injection of active skills."""
        skill_registry.activate("summarize")
        injector = SkillInjector(skill_registry)

        prompt = "You are an AI assistant."
        user_input = "hello world"  # Doesn't match summarize trigger

        result = injector.inject_skills(prompt, user_input)

        # Should still inject active skill
        assert "summarize" in result

        skill_registry.deactivate("summarize")


class TestSkillLoader:
    """Tests for SkillLoader."""

    def test_load_from_file(self, tmp_path):
        """Test loading from a single file."""
        skill_content = """---
name: test-skill
description: Test
---
Content here
"""
        path = tmp_path / "test-skill.md"
        path.write_text(skill_content)

        registry = SkillRegistry()
        loader = SkillLoader(registry)

        assert loader.load_from_file(path)
        assert registry.get("test-skill") is not None

    def test_load_from_dir(self, skill_registry):
        """Test loading from directory."""
        # Already loaded via fixture
        assert skill_registry.get("code-review") is not None
        assert skill_registry.get("summarize") is not None

    def test_discover_skills(self):
        """Test skill discovery."""
        registry = SkillRegistry()
        loader = SkillLoader(registry)

        skills_dir = Path(__file__).parent / "fixtures" / "skills"
        discovered = loader.discover_skills(skills_dir)

        assert len(discovered) >= 2
        assert any("code-review" in str(s) for s in discovered)
        assert any("summarize" in str(s) for s in discovered)
