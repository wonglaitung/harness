package com.harness.skills;

import java.util.List;

/**
 * Skill metadata from frontmatter.
 */
public record SkillMetadata(
    String description,
    String version,
    List<String> tags,
    List<String> tools,       // Allowed tools for this skill
    List<String> triggers,    // Keywords that trigger this skill
    boolean enabled           // Whether this skill is enabled (sync with Python SDK)
) {

    public SkillMetadata(String description, String version, List<String> tags) {
        this(description, version, tags, List.of(), List.of(), true);
    }
}