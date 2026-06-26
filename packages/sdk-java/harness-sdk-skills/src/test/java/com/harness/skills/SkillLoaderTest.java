package com.harness.skills;

import static org.junit.jupiter.api.Assertions.*;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

/**
 * Tests for SkillLoader.
 */
class SkillLoaderTest {

    @TempDir
    Path tempDir;

    private SkillRegistry registry;
    private SkillLoader loader;

    @BeforeEach
    void setUp() {
        registry = new SkillRegistry();
        registry.listSkills().forEach(name -> registry.getSkill(name).ifPresent(s -> {})); // Clear
        registry.reload(); // Clear by reloading from empty
        loader = new SkillLoader(registry);
    }

    @Test
    void testLoadFromNonExistentDirectory() {
        int count = loader.loadFromDir(tempDir.resolve("nonexistent"));

        assertEquals(0, count);
    }

    @Test
    void testLoadSkillFromFile() throws IOException {
        // Create a skill file with frontmatter
        String skillContent = """
            ---
            name: test-skill
            description: A test skill
            version: 1.0
            ---

            # Test Skill

            This is the skill body content.
            """;

        Path skillFile = tempDir.resolve("test-skill.md");
        Files.writeString(skillFile, skillContent);

        boolean loaded = loader.loadFromFile(skillFile);

        assertTrue(loaded);
        assertTrue(registry.getSkill("test-skill").isPresent());
    }

    @Test
    void testLoadSkillWithoutFrontmatter() throws IOException {
        // Create a skill file without frontmatter
        String skillContent = """
            # Simple Skill

            This skill has no frontmatter.
            """;

        Path skillFile = tempDir.resolve("simple-skill.md");
        Files.writeString(skillFile, skillContent);

        boolean loaded = loader.loadFromFile(skillFile);

        assertTrue(loaded);
        assertTrue(registry.getSkill("simple-skill").isPresent());
    }

    @Test
    void testLoadFromDirectory() throws IOException {
        // Create multiple skill files
        String skill1 = """
            ---
            description: First skill
            ---
            Content 1
            """;
        String skill2 = """
            ---
            description: Second skill
            ---
            Content 2
            """;

        Files.writeString(tempDir.resolve("skill1.md"), skill1);
        Files.writeString(tempDir.resolve("skill2.md"), skill2);

        int count = loader.loadFromDir(tempDir);

        assertEquals(2, count);
        assertTrue(registry.getSkill("skill1").isPresent());
        assertTrue(registry.getSkill("skill2").isPresent());
    }

    @Test
    void testLoadFromPathFile() throws IOException {
        String skillContent = """
            ---
            description: Path skill
            ---
            Content
            """;

        Path skillFile = tempDir.resolve("path-skill.md");
        Files.writeString(skillFile, skillContent);

        boolean loaded = loader.loadFromPath(skillFile);

        assertTrue(loaded);
    }

    @Test
    void testLoadFromPathDirectory() throws IOException {
        String skillContent = """
            ---
            description: Dir skill
            ---
            Content
            """;

        Path skillFile = tempDir.resolve("dir-skill.md");
        Files.writeString(skillFile, skillContent);

        boolean loaded = loader.loadFromPath(tempDir);

        assertTrue(loaded);
    }

    @Test
    void testDiscoverSkills() throws IOException {
        // Create valid skill files
        String validSkill = """
            ---
            name: valid
            description: Valid skill
            ---
            Content
            """;

        // Create non-skill markdown file (no frontmatter markers)
        String regularMd = """
            # Regular Markdown

            Not a skill file.
            """;

        Files.writeString(tempDir.resolve("valid.md"), validSkill);
        Files.writeString(tempDir.resolve("regular.md"), regularMd);

        // Also create a non-md file
        Files.writeString(tempDir.resolve("config.txt"), "Not markdown");

        java.util.List<Path> discovered = loader.discoverSkills(tempDir);

        assertEquals(1, discovered.size());
        assertTrue(discovered.get(0).toString().contains("valid.md"));
    }

    @Test
    void testGetLoadedPaths() throws IOException {
        String skillContent = "---\ndescription: Test\n---\nContent";
        Path skillFile = tempDir.resolve("test.md");
        Files.writeString(skillFile, skillContent);

        loader.loadFromFile(skillFile);

        assertEquals(1, loader.getLoadedPaths().size());
    }

    @Test
    void testClearLoaded() throws IOException {
        String skillContent = "---\ndescription: Test\n---\nContent";
        Files.writeString(tempDir.resolve("test.md"), skillContent);

        loader.loadFromDir(tempDir);
        assertFalse(loader.getLoadedPaths().isEmpty());

        loader.clearLoaded();
        assertTrue(loader.getLoadedPaths().isEmpty());
    }

    @Test
    void testDefaultSkillPaths() {
        java.util.List<Path> paths = SkillLoader.getDefaultSkillPaths();

        assertFalse(paths.isEmpty());
        // Should contain user home path
        assertTrue(paths.stream().anyMatch(p -> p.toString().contains(".harness")));
    }
}