package com.harness.skills;

import java.nio.file.Path;
import java.util.List;

/**
 * A skill definition.
 *
 * Skills are markdown files that define domain-specific knowledge
 * for the agent to follow.
 */
public record Skill(
    String name,
    SkillMetadata metadata,
    String content,
    Path filePath
) {

    /**
     * Get skill description.
     */
    public String description() {
        return metadata.description();
    }

    /**
     * Get skill version.
     */
    public String version() {
        return metadata.version();
    }

    /**
     * Create a skill without file path.
     */
    public static Skill of(String name, String description, String content) {
        return new Skill(name, new SkillMetadata(description, "1.0", List.of()), content, null);
    }
}