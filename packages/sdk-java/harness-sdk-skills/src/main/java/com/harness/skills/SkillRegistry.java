package com.harness.skills;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Skill registry - manages skill files.
 *
 * Skills are markdown files that define domain-specific knowledge:
 * - Tool selection criteria
 * - Judgment standards
 * - Output templates
 *
 * The agent loads skills dynamically and follows the skill's guidance.
 */
public class SkillRegistry {

    private static final Logger logger = LoggerFactory.getLogger(SkillRegistry.class);

    private final Path skillsDir;
    private final Map<String, Skill> skills;

    public SkillRegistry(Path skillsDir) {
        this.skillsDir = skillsDir;
        this.skills = new HashMap<>();
        loadAllSkills();
    }

    public SkillRegistry() {
        this(Path.of(System.getProperty("user.home"), ".harness", "skills"));
    }

    /**
     * Load all skills from the skills directory.
     */
    private void loadAllSkills() {
        if (!Files.exists(skillsDir)) {
            try {
                Files.createDirectories(skillsDir);
            } catch (IOException e) {
                logger.warn("Failed to create skills directory: {}", e.getMessage());
            }
            return;
        }

        try {
            Files.list(skillsDir)
                .filter(p -> p.toString().endsWith(".md"))
                .forEach(this::loadSkill);
        } catch (IOException e) {
            logger.warn("Failed to list skills: {}", e.getMessage());
        }
    }

    /**
     * Load a single skill file.
     */
    private void loadSkill(Path skillFile) {
        try {
            String content = Files.readString(skillFile);
            String name = skillFile.getFileName().toString().replace(".md", "");

            // Parse skill metadata (frontmatter)
            SkillMetadata metadata = parseMetadata(content);
            String body = extractBody(content);

            Skill skill = new Skill(name, metadata, body, skillFile);
            skills.put(name, skill);
            logger.debug("Loaded skill: {}", name);

        } catch (IOException e) {
            logger.warn("Failed to load skill {}: {}", skillFile, e.getMessage());
        }
    }

    /**
     * Parse skill metadata from frontmatter.
     */
    private SkillMetadata parseMetadata(String content) {
        // Simple frontmatter parsing
        if (!content.startsWith("---")) {
            return new SkillMetadata("", "", List.of());
        }

        int endIdx = content.indexOf("---", 3);
        if (endIdx == -1) {
            return new SkillMetadata("", "", List.of());
        }

        String frontmatter = content.substring(3, endIdx).trim();
        String description = "";
        String version = "1.0";

        for (String line : frontmatter.split("\n")) {
            if (line.startsWith("description:")) {
                description = line.substring("description:".length()).trim();
            } else if (line.startsWith("version:")) {
                version = line.substring("version:".length()).trim();
            }
        }

        return new SkillMetadata(description, version, List.of());
    }

    /**
     * Extract body content after frontmatter.
     */
    private String extractBody(String content) {
        if (!content.startsWith("---")) {
            return content;
        }

        int endIdx = content.indexOf("---", 3);
        if (endIdx == -1) {
            return content;
        }

        return content.substring(endIdx + 3).trim();
    }

    /**
     * Get a skill by name.
     */
    public Optional<Skill> getSkill(String name) {
        return Optional.ofNullable(skills.get(name));
    }

    /**
     * List all skill names.
     */
    public List<String> listSkills() {
        return List.copyOf(skills.keySet());
    }

    /**
     * Get all skills.
     */
    public List<Skill> getAllSkills() {
        return List.copyOf(skills.values());
    }

    /**
     * Reload all skills from disk.
     */
    public void reload() {
        skills.clear();
        loadAllSkills();
    }

    /**
     * Register a skill programmatically.
     */
    public void registerSkill(Skill skill) {
        skills.put(skill.name(), skill);
    }
}