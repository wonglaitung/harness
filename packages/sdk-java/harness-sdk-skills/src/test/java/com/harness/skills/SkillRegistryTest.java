package com.harness.skills;

import static org.junit.jupiter.api.Assertions.*;

import java.nio.file.Path;
import java.util.List;
import java.util.Optional;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

/**
 * Tests for SkillRegistry.
 */
class SkillRegistryTest {

    @TempDir
    Path tempDir;

    private SkillRegistry registry;

    @BeforeEach
    void setUp() {
        // Create registry with empty temp directory
        registry = new SkillRegistry(tempDir);
    }

    @Test
    void testEmptyRegistry() {
        assertTrue(registry.listSkills().isEmpty());
        assertTrue(registry.getAllSkills().isEmpty());
    }

    @Test
    void testRegisterSkill() {
        SkillMetadata metadata = new SkillMetadata("Test skill description", "1.0", List.of());
        Skill skill = new Skill("test", metadata, "Test content", null);

        registry.registerSkill(skill);

        assertEquals(1, registry.listSkills().size());
        assertTrue(registry.listSkills().contains("test"));
    }

    @Test
    void testGetSkill() {
        SkillMetadata metadata = new SkillMetadata("Test skill description", "1.0", List.of());
        Skill skill = new Skill("my-skill", metadata, "Content", null);
        registry.registerSkill(skill);

        Optional<Skill> found = registry.getSkill("my-skill");

        assertTrue(found.isPresent());
        assertEquals("my-skill", found.get().name());
    }

    @Test
    void testGetNonExistentSkill() {
        Optional<Skill> found = registry.getSkill("nonexistent");

        assertFalse(found.isPresent());
    }

    @Test
    void testFindMatchingSkills() {
        // Register skills with triggers
        SkillMetadata codeMeta = new SkillMetadata("Code helper", "1.0",
            List.of(), List.of(), List.of("code", "function", "class"), false);
        Skill codeSkill = new Skill("code-assistant", codeMeta, "Help with code", null);

        SkillMetadata translateMeta = new SkillMetadata("Translator", "1.0",
            List.of(), List.of(), List.of("translate", "翻译"), false);
        Skill translateSkill = new Skill("translator", translateMeta, "Translate text", null);

        registry.registerSkill(codeSkill);
        registry.registerSkill(translateSkill);

        // Test matching
        List<Skill> codeMatches = registry.findMatchingSkills("Help me write code");
        assertTrue(codeMatches.stream().anyMatch(s -> s.name().equals("code-assistant")));

        List<Skill> translateMatches = registry.findMatchingSkills("Please translate this");
        assertTrue(translateMatches.stream().anyMatch(s -> s.name().equals("translator")));

        List<Skill> noMatches = registry.findMatchingSkills("What's the weather?");
        assertTrue(noMatches.isEmpty());
    }

    @Test
    void testFindMatchingSkillsBySkillName() {
        SkillMetadata meta = new SkillMetadata("Test description", "1.0", List.of());
        Skill skill = new Skill("my-custom-skill", meta, "Content", null);
        registry.registerSkill(skill);

        // Skill name in input should match
        List<Skill> matches = registry.findMatchingSkills("Use my-custom-skill for this");
        assertTrue(matches.stream().anyMatch(s -> s.name().equals("my-custom-skill")));
    }

    @Test
    void testIsToolAllowedWithNoActiveSkills() {
        // No active skills = all tools allowed
        assertTrue(registry.isToolAllowed("read_file"));
        assertTrue(registry.isToolAllowed("bash"));
        assertTrue(registry.isToolAllowed("any_tool"));
    }

    @Test
    void testGetActiveSkills() {
        // Register active and inactive skills
        SkillMetadata activeMeta = new SkillMetadata("Active", "1.0", List.of(), List.of(), List.of(), true);
        Skill activeSkill = new Skill("active-skill", activeMeta, "Content", null);

        SkillMetadata inactiveMeta = new SkillMetadata("Inactive", "1.0", List.of(), List.of(), List.of(), false);
        Skill inactiveSkill = new Skill("inactive-skill", inactiveMeta, "Content", null);

        registry.registerSkill(activeSkill);
        registry.registerSkill(inactiveSkill);

        List<Skill> activeSkills = registry.getActiveSkills();
        assertEquals(1, activeSkills.size());
        assertEquals("active-skill", activeSkills.get(0).name());
    }

    @Test
    void testReload() {
        // Register a skill
        Skill skill = new Skill("test", new SkillMetadata("Test description", "1.0", List.of()), "Content", null);
        registry.registerSkill(skill);
        assertEquals(1, registry.listSkills().size());

        // Reload clears and reloads from disk
        registry.reload();

        // Should be empty since temp dir is empty
        assertTrue(registry.listSkills().isEmpty());
    }
}