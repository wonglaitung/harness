"""
Tests for Progressive Skill Loading.
"""

import tempfile
from pathlib import Path

import pytest

from harness.skills.progressive import (
    LoadingLevel,
    ProgressiveLoadResult,
    ProgressiveSkillLoader,
    SkillMetadata,
)
from harness.skills.base import Skill


class TestSkillMetadata:
    """Test SkillMetadata."""

    def test_create_metadata(self):
        """Test creating skill metadata."""
        meta = SkillMetadata(
            name="test_skill",
            description="A test skill",
            path=Path("/tmp/test.md"),
            triggers={"keywords": ["test", "example"]},
        )
        assert meta.name == "test_skill"
        assert meta.description == "A test skill"
        assert not meta._loaded

    def test_to_list_item(self):
        """Test list item formatting."""
        meta = SkillMetadata(
            name="code_review",
            description="Review code for issues",
            path=Path("/tmp/test.md"),
        )
        item = meta.to_list_item()
        assert "- code_review: Review code for issues" == item

    def test_matches_keywords(self):
        """Test keyword matching."""
        meta = SkillMetadata(
            name="test",
            description="Test",
            path=Path("/tmp/test.md"),
            triggers={"keywords": ["review", "check"]},
        )
        assert meta.matches("Please review my code") is True
        assert meta.matches("Check this file") is True
        assert meta.matches("Write a test") is False

    def test_matches_patterns(self):
        """Test regex pattern matching."""
        meta = SkillMetadata(
            name="test",
            description="Test",
            path=Path("/tmp/test.md"),
            triggers={"patterns": [r"fix\s+bug\s+\w+"]},
        )
        assert meta.matches("fix bug in main.py") is True
        assert meta.matches("fix the bug") is False

    def test_matches_empty_triggers(self):
        """Test matching with no triggers."""
        meta = SkillMetadata(
            name="test",
            description="Test",
            path=Path("/tmp/test.md"),
        )
        assert meta.matches("any text") is False


class TestProgressiveSkillLoader:
    """Test ProgressiveSkillLoader."""

    def test_init(self):
        """Test loader initialization."""
        loader = ProgressiveSkillLoader()
        assert len(loader._metadata_cache) == 0
        assert len(loader._skill_cache) == 0

    def test_discover_skills(self):
        """Test skill discovery."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skills_dir = Path(tmpdir)

            # Create skill files
            skill1 = skills_dir / "skill1.md"
            skill1.write_text("""---
name: code_review
description: Review code for issues
triggers:
  keywords:
    - review
    - check
---

# Code Review Skill

Review the code and provide feedback.
""")

            skill2 = skills_dir / "skill2.md"
            skill2.write_text("""---
name: testing
description: Write tests for code
---

# Testing Skill

Write comprehensive tests.
""")

            loader = ProgressiveSkillLoader()
            skills = loader.discover_skills(skills_dir)

            assert len(skills) == 2
            names = [s.name for s in skills]
            assert "code_review" in names
            assert "testing" in names

    def test_discover_skills_empty_dir(self):
        """Test discovery with empty directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            loader = ProgressiveSkillLoader()
            skills = loader.discover_skills(Path(tmpdir))
            assert skills == []

    def test_discover_skills_nonexistent_dir(self):
        """Test discovery with nonexistent directory."""
        loader = ProgressiveSkillLoader()
        skills = loader.discover_skills(Path("/nonexistent/path"))
        assert skills == []

    def test_load_full_content(self):
        """Test loading full skill content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_path = Path(tmpdir) / "test_skill.md"
            skill_path.write_text("""---
name: test_skill
description: Test skill
---

# Test Skill Content

This is the full content.
""")

            loader = ProgressiveSkillLoader()
            meta = SkillMetadata(
                name="test_skill",
                description="Test skill",
                path=skill_path,
            )

            skill = loader.load_full_content(meta)

            assert isinstance(skill, Skill)
            assert skill.name == "test_skill"
            assert "Test Skill Content" in skill.content
            assert meta._loaded is True

    def test_load_full_content_caching(self):
        """Test that loaded skills are cached."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_path = Path(tmpdir) / "test_skill.md"
            skill_path.write_text("""---
name: test_skill
description: Test skill
---

Content here.
""")

            loader = ProgressiveSkillLoader()
            meta = SkillMetadata(
                name="test_skill",
                description="Test skill",
                path=skill_path,
            )

            # First load
            skill1 = loader.load_full_content(meta)

            # Second load should use cache
            skill2 = loader.load_full_content(meta)

            assert skill1 is skill2
            assert "test_skill" in loader._skill_cache

    def test_match_skills(self):
        """Test skill matching."""
        skills = [
            SkillMetadata(
                name="code_review",
                description="Review code",
                path=Path("/tmp/a.md"),
                triggers={"keywords": ["review", "check"]},
            ),
            SkillMetadata(
                name="testing",
                description="Write tests",
                path=Path("/tmp/b.md"),
                triggers={"keywords": ["test", "testing"]},
            ),
            SkillMetadata(
                name="deploy",
                description="Deploy code",
                path=Path("/tmp/c.md"),
                triggers={"keywords": ["deploy", "release"]},
            ),
        ]

        loader = ProgressiveSkillLoader()

        matches = loader.match_skills("Please review my code", skills)
        assert len(matches) == 1
        assert matches[0].name == "code_review"

        matches = loader.match_skills("Write a test", skills)
        assert len(matches) == 1
        assert matches[0].name == "testing"

    def test_match_skills_max_matches(self):
        """Test max_matches limit."""
        skills = [
            SkillMetadata(
                name="skill1",
                description="Test",
                path=Path("/tmp/a.md"),
                triggers={"keywords": ["test"]},
            ),
            SkillMetadata(
                name="skill2",
                description="Test",
                path=Path("/tmp/b.md"),
                triggers={"keywords": ["test"]},
            ),
            SkillMetadata(
                name="skill3",
                description="Test",
                path=Path("/tmp/c.md"),
                triggers={"keywords": ["test"]},
            ),
        ]

        loader = ProgressiveSkillLoader()
        matches = loader.match_skills("test", skills, max_matches=2)

        assert len(matches) == 2

    def test_build_skill_selection_prompt_list(self):
        """Test building skill selection prompt in list format."""
        skills = [
            SkillMetadata(
                name="skill1",
                description="First skill",
                path=Path("/tmp/a.md"),
            ),
            SkillMetadata(
                name="skill2",
                description="Second skill",
                path=Path("/tmp/b.md"),
            ),
        ]

        loader = ProgressiveSkillLoader()
        prompt = loader.build_skill_selection_prompt(skills, format_style="list")

        assert "- skill1: First skill" in prompt
        assert "- skill2: Second skill" in prompt

    def test_build_skill_selection_prompt_markdown(self):
        """Test building skill selection prompt in markdown format."""
        skills = [
            SkillMetadata(
                name="skill1",
                description="First skill",
                path=Path("/tmp/a.md"),
            ),
        ]

        loader = ProgressiveSkillLoader()
        prompt = loader.build_skill_selection_prompt(skills, format_style="markdown")

        assert "## Available Skills" in prompt
        assert "### skill1" in prompt

    def test_build_skill_selection_prompt_empty(self):
        """Test building prompt with no skills."""
        loader = ProgressiveSkillLoader()
        prompt = loader.build_skill_selection_prompt([])

        assert "No skills available" in prompt

    def test_clear_cache(self):
        """Test cache clearing."""
        loader = ProgressiveSkillLoader()
        loader._metadata_cache["test"] = None
        loader._skill_cache["test"] = None

        loader.clear_cache()

        assert len(loader._metadata_cache) == 0
        assert len(loader._skill_cache) == 0

    def test_estimate_tokens_metadata(self):
        """Test token estimation for metadata."""
        skills = [
            SkillMetadata(
                name="short",
                description="Short",
                path=Path("/tmp/a.md"),
            ),
        ]

        loader = ProgressiveSkillLoader()
        tokens = loader.estimate_tokens(skills, level=1)

        assert tokens > 0
        # Should be relatively small for metadata only
        assert tokens < 200


class TestLoadingLevel:
    """Test LoadingLevel constants."""

    def test_level_values(self):
        """Test that levels have expected values."""
        assert LoadingLevel.FRONTMATTER == 1
        assert LoadingLevel.FULL_CONTENT == 2
        assert LoadingLevel.REFERENCES == 3
