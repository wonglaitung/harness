package com.harness.skills;

import java.io.*;
import java.nio.file.*;
import java.util.*;
import java.util.regex.*;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Progressive skill loader for context-efficient skill management.
 *
 * Implements three-level loading:
 * 1. Level 1 (Frontmatter): Load only metadata for all skills (~100 tokens)
 * 2. Level 2 (Full Content): Load complete content for matched skills
 * 3. Level 3 (References): Load reference files on demand
 *
 * Example:
 * <pre>
 * ProgressiveSkillLoader loader = new ProgressiveSkillLoader();
 *
 * // Level 1: Discover all skills (metadata only)
 * List&lt;SkillMetadata&gt; allSkills = loader.discoverSkills(Path.of("./skills"));
 *
 * // Build skill selection prompt
 * String available = loader.buildSkillSelectionPrompt(allSkills, "list");
 *
 * // Match skills to user input
 * List&lt;SkillMetadata&gt; matched = loader.matchSkills("Write a test", allSkills);
 *
 * // Level 2: Load full content for matched skills
 * for (SkillMetadata meta : matched) {
 *     Skill skill = loader.loadFullContent(meta);
 *     // Use skill.content() in context
 * }
 * </pre>
 */
public class ProgressiveSkillLoader {

    private static final Logger logger = LoggerFactory.getLogger(ProgressiveSkillLoader.class);

    private final Map<String, SkillMetadata> metadataCache = new HashMap<>();
    private final Map<String, Skill> skillCache = new HashMap<>();
    private final int cacheSize;

    /**
     * Lightweight skill metadata for Level 1 loading.
     */
    public static class SkillMetadata {
        private final String name;
        private final String description;
        private final Path path;
        private final Map<String, List<String>> triggers;
        private final String version;
        private Skill cachedSkill;
        private boolean loaded;

        public SkillMetadata(String name, String description, Path path,
                            Map<String, List<String>> triggers, String version) {
            this.name = name;
            this.description = description;
            this.path = path;
            this.triggers = triggers != null ? triggers : Map.of();
            this.version = version != null ? version : "1.0.0";
            this.loaded = false;
        }

        public String name() { return name; }
        public String description() { return description; }
        public Path path() { return path; }
        public Map<String, List<String>> triggers() { return triggers; }
        public String version() { return version; }
        public boolean isLoaded() { return loaded; }
        public Skill cachedSkill() { return cachedSkill; }

        /**
         * Format as a list item for skill selection.
         */
        public String toListItem() {
            return "- " + name + ": " + description;
        }

        /**
         * Check if text matches this skill's triggers.
         *
         * @param text Input text - can be a String or multimodal content List
         */
        public boolean matches(Object text) {
            // Handle multimodal content (List of Map)
            if (text instanceof List) {
                @SuppressWarnings("unchecked")
                List<?> contentList = (List<?>) text;
                StringBuilder textBuilder = new StringBuilder();
                for (Object block : contentList) {
                    if (block instanceof Map) {
                        @SuppressWarnings("unchecked")
                        Map<?, ?> blockMap = (Map<?, ?>) block;
                        if ("text".equals(blockMap.get("type"))) {
                            Object textObj = blockMap.get("text");
                            if (textObj instanceof String) {
                                textBuilder.append((String) textObj);
                            }
                        }
                    }
                }
                text = textBuilder.toString();
            }

            if (text == null || !(text instanceof String)) {
                return false;
            }

            String textStr = (String) text;
            if (textStr.isEmpty()) {
                return false;
            }

            String textLower = textStr.toLowerCase();

            // Keyword matching
            List<String> keywords = triggers.get("keywords");
            if (keywords != null) {
                for (String keyword : keywords) {
                    if (textLower.contains(keyword.toLowerCase())) {
                        return true;
                    }
                }
            }

            // Pattern matching
            List<String> patterns = triggers.get("patterns");
            if (patterns != null) {
                for (String pattern : patterns) {
                    try {
                        if (Pattern.compile(pattern, Pattern.CASE_INSENSITIVE).matcher(textStr).find()) {
                            return true;
                        }
                    } catch (PatternSyntaxException e) {
                        // Ignore invalid patterns
                    }
                }
            }

            return false;
        }
    }

    /**
     * Result of progressive loading operation.
     */
    public static class ProgressiveLoadResult {
        private final int level;
        private final List<?> skills;
        private final int totalTokensEstimate;
        private final int loadedFromCache;

        public ProgressiveLoadResult(int level, List<?> skills, int totalTokensEstimate, int loadedFromCache) {
            this.level = level;
            this.skills = skills;
            this.totalTokensEstimate = totalTokensEstimate;
            this.loadedFromCache = loadedFromCache;
        }

        public int level() { return level; }
        public List<?> skills() { return skills; }
        public int totalTokensEstimate() { return totalTokensEstimate; }
        public int loadedFromCache() { return loadedFromCache; }
    }

    public ProgressiveSkillLoader() {
        this(50);
    }

    public ProgressiveSkillLoader(int cacheSize) {
        this.cacheSize = cacheSize;
    }

    /**
     * Loading level constants.
     */
    public static class LoadingLevel {
        public static final int FRONTMATTER = 1;
        public static final int FULL_CONTENT = 2;
        public static final int REFERENCES = 3;
    }

    /**
     * Discover all skills in a directory (Level 1 loading).
     *
     * Only reads frontmatter, not full content.
     */
    public List<SkillMetadata> discoverSkills(Path directory) {
        List<SkillMetadata> skills = new ArrayList<>();

        if (!Files.exists(directory)) {
            return skills;
        }

        try (var stream = Files.walk(directory)) {
            stream.filter(Files::isRegularFile)
                  .filter(p -> p.toString().endsWith(".md"))
                  .forEach(skillFile -> {
                      try {
                          SkillMetadata metadata = loadFrontmatterOnly(skillFile);
                          if (metadata != null) {
                              skills.add(metadata);
                              metadataCache.put(metadata.name(), metadata);
                          }
                      } catch (Exception e) {
                          logger.debug("Failed to load skill from {}: {}", skillFile, e.getMessage());
                      }
                  });
        } catch (IOException e) {
            logger.warn("Error walking skill directory: {}", e.getMessage());
        }

        return skills;
    }

    /**
     * Load only frontmatter from a skill file.
     */
    private SkillMetadata loadFrontmatterOnly(Path path) {
        try {
            String content = Files.readString(path);

            if (!content.startsWith("---")) {
                return null;
            }

            // Split by ---
            String[] parts = content.split("---", 3);
            if (parts.length < 3) {
                return null;
            }

            // Parse YAML frontmatter
            String frontmatter = parts[1].trim();
            Map<String, Object> data = parseYamlFrontmatter(frontmatter);

            if (!data.containsKey("name") && !data.containsKey("description")) {
                return null;
            }

            String name = (String) data.getOrDefault("name", path.getFileName().toString().replace(".md", ""));
            String description = (String) data.getOrDefault("description", "");
            String version = (String) data.getOrDefault("version", "1.0.0");

            @SuppressWarnings("unchecked")
            Map<String, List<String>> triggers = (Map<String, List<String>>) data.getOrDefault("triggers", Map.of());

            return new SkillMetadata(name, description, path, triggers, version);

        } catch (IOException e) {
            return null;
        }
    }

    /**
     * Simple YAML frontmatter parser.
     */
    private Map<String, Object> parseYamlFrontmatter(String yaml) {
        Map<String, Object> result = new HashMap<>();

        String[] lines = yaml.split("\n");
        String currentKey = null;
        List<String> currentList = null;

        for (String line : lines) {
            if (line.trim().isEmpty()) {
                continue;
            }

            // Check for list item
            if (line.trim().startsWith("- ") && currentKey != null && currentList != null) {
                currentList.add(line.trim().substring(2));
                continue;
            }

            // Check for key: value
            int colonIndex = line.indexOf(':');
            if (colonIndex > 0) {
                String key = line.substring(0, colonIndex).trim();
                String value = line.substring(colonIndex + 1).trim();

                if (value.isEmpty()) {
                    // Start of a nested structure or list
                    currentKey = key;
                    currentList = new ArrayList<>();
                    result.put(key, currentList);
                } else {
                    // Simple key-value
                    result.put(key, value);
                    currentKey = null;
                    currentList = null;
                }
            }
        }

        return result;
    }

    /**
     * Load full skill content (Level 2 loading).
     */
    public Skill loadFullContent(SkillMetadata metadata) {
        // Check if already loaded
        if (metadata.isLoaded() && metadata.cachedSkill() != null) {
            return metadata.cachedSkill();
        }

        // Check global cache
        if (skillCache.containsKey(metadata.name())) {
            Skill cached = skillCache.get(metadata.name());
            metadata.cachedSkill = cached;
            metadata.loaded = true;
            return cached;
        }

        // Load from file
        try {
            Skill skill = Skill.fromFile(metadata.path());

            // Update metadata
            metadata.cachedSkill = skill;
            metadata.loaded = true;

            // Add to global cache with LRU eviction
            if (skillCache.size() >= cacheSize) {
                // Remove oldest entry
                String oldestKey = skillCache.keySet().iterator().next();
                skillCache.remove(oldestKey);
            }

            skillCache.put(metadata.name(), skill);
            return skill;

        } catch (Exception e) {
            logger.error("Failed to load skill from {}: {}", metadata.path(), e.getMessage());
            return null;
        }
    }

    /**
     * Match skills to user input text.
     *
     * @param text Input text - can be a String or multimodal content List
     * @param skills List of skill metadata
     * @return List of matching skills
     */
    public List<SkillMetadata> matchSkills(Object text, List<SkillMetadata> skills) {
        return matchSkills(text, skills, 3);
    }

    /**
     * Match skills to user input text with max matches limit.
     *
     * @param text Input text - can be a String or multimodal content List
     * @param skills List of skill metadata
     * @param maxMatches Maximum number of matches to return
     * @return List of matching skills
     */
    public List<SkillMetadata> matchSkills(Object text, List<SkillMetadata> skills, int maxMatches) {
        List<SkillMetadata> matches = new ArrayList<>();

        for (SkillMetadata skill : skills) {
            if (skill.matches(text)) {
                matches.add(skill);
                if (matches.size() >= maxMatches) {
                    break;
                }
            }
        }

        return matches;
    }

    /**
     * Load skill with all references (Level 3 loading).
     */
    public SkillWithReferences loadWithReferences(SkillMetadata metadata) {
        Skill skill = loadFullContent(metadata);
        List<String> references = new ArrayList<>();

        if (skill == null) {
            return new SkillWithReferences(skill, references);
        }

        // Extract reference patterns from skill content
        String content = skill.content();

        // Pattern: @file:path or @path
        Pattern refPattern = Pattern.compile("@(?:file:)?([^\\s,]+)");
        Matcher matcher = refPattern.matcher(content);

        while (matcher.find()) {
            String refPath = matcher.group(1);
            try {
                Path fullPath = metadata.path().getParent().resolve(refPath);
                if (Files.exists(fullPath)) {
                    String refContent = Files.readString(fullPath);
                    references.add("--- " + refPath + " ---\n" + refContent);
                }
            } catch (Exception e) {
                logger.debug("Failed to load reference {}: {}", refPath, e.getMessage());
            }
        }

        return new SkillWithReferences(skill, references);
    }

    /**
     * Skill with loaded references.
     */
    public static record SkillWithReferences(Skill skill, List<String> references) {}

    /**
     * Build a prompt for skill selection.
     */
    public String buildSkillSelectionPrompt(List<SkillMetadata> skills, String formatStyle) {
        if (skills.isEmpty()) {
            return "No skills available.";
        }

        switch (formatStyle) {
            case "markdown":
                StringBuilder sb = new StringBuilder("## Available Skills\n\n");
                for (SkillMetadata skill : skills) {
                    sb.append("### ").append(skill.name()).append("\n");
                    sb.append(skill.description()).append("\n\n");
                }
                return sb.toString();

            case "compact":
                StringJoiner joiner = new StringJoiner(" | ");
                for (SkillMetadata skill : skills) {
                    String desc = skill.description();
                    if (desc.length() > 50) {
                        desc = desc.substring(0, 50) + "...";
                    }
                    joiner.add(skill.name() + ": " + desc);
                }
                return joiner.toString();

            default: // "list"
                StringJoiner listJoiner = new StringJoiner("\n");
                for (SkillMetadata skill : skills) {
                    listJoiner.add(skill.toListItem());
                }
                return listJoiner.toString();
        }
    }

    /**
     * Estimate token count for a list of skills.
     */
    public int estimateTokens(List<?> skills, int level) {
        int total = 0;

        for (Object item : skills) {
            if (item instanceof SkillMetadata) {
                SkillMetadata meta = (SkillMetadata) item;
                if (level == LoadingLevel.FRONTMATTER) {
                    // Metadata only: ~50-100 tokens
                    total += 50 + meta.name().length() / 4 + meta.description().length() / 4;
                } else if (level == LoadingLevel.FULL_CONTENT) {
                    // Estimate full content
                    total += 500;
                }
            } else if (item instanceof Skill) {
                Skill skill = (Skill) item;
                total += 100 + skill.content().length() / 4;
            }
        }

        return total;
    }

    /**
     * Clear all cached skills.
     */
    public void clearCache() {
        metadataCache.clear();
        skillCache.clear();
    }
}
