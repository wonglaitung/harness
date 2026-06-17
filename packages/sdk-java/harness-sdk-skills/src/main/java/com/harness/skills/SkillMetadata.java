package com.harness.skills;

import java.util.List;

/**
 * Skill metadata from frontmatter.
 */
public record SkillMetadata(
    String description,
    String version,
    List<String> tags
) {}