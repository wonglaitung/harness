package com.harness.skills;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Skill loader for loading skills from files and directories.
 *
 * Features:
 * - Load from file paths
 * - Load from directories
 * - Auto-discovery of skill files
 * - Default skill directories
 *
 * Example:
 * <pre>
 * SkillRegistry registry = new SkillRegistry();
 * SkillLoader loader = new SkillLoader(registry);
 * int count = loader.loadDefaults();
 * </pre>
 */
public class SkillLoader {

    private static final Logger logger = LoggerFactory.getLogger(SkillLoader.class);

    /**
     * Default skill search paths (in priority order).
     */
    private static final List<Path> DEFAULT_SKILL_PATHS = List.of(
        Path.of(System.getProperty("user.home"), ".harness", "skills"),        // User-level (highest priority)
        Path.of(System.getProperty("user.home"), ".harness", "shared-skills"), // Shared
        Path.of(".agent", "skills"),                                            // Project-level
        Path.of("skills")                                                       // Project-level (alternate)
    );

    private final SkillRegistry registry;
    private final List<Path> loadedPaths;

    public SkillLoader(SkillRegistry registry) {
        this.registry = registry;
        this.loadedPaths = new ArrayList<>();
    }

    /**
     * Load skills from default directories.
     *
     * @return Number of skills loaded
     */
    public int loadDefaults() {
        int count = 0;
        for (Path directory : DEFAULT_SKILL_PATHS) {
            if (Files.exists(directory)) {
                int skillsLoaded = loadFromDir(directory);
                count += skillsLoaded;
                logger.info("Loaded {} skills from {}", skillsLoaded, directory);
            } else {
                logger.debug("Skill directory not found: {}", directory);
            }
        }
        logger.info("Total skills loaded: {}", count);
        return count;
    }

    /**
     * Load skill from a file or directory path.
     *
     * @param path Path to file or directory
     * @return True if loaded successfully
     */
    public boolean loadFromPath(String path) {
        return loadFromPath(Path.of(path));
    }

    /**
     * Load skill from a file or directory path.
     *
     * @param path Path to file or directory
     * @return True if loaded successfully
     */
    public boolean loadFromPath(Path path) {
        path = path.toAbsolutePath().normalize();

        if (Files.isRegularFile(path) && path.toString().endsWith(".md")) {
            return loadFromFile(path);
        } else if (Files.isDirectory(path)) {
            return loadFromDir(path) > 0;
        }

        return false;
    }

    /**
     * Load a single skill file.
     *
     * @param path Path to skill file
     * @return True if loaded successfully
     */
    public boolean loadFromFile(Path path) {
        try {
            String content = Files.readString(path);
            String name = path.getFileName().toString().replace(".md", "");

            // Parse skill metadata (frontmatter)
            SkillMetadata metadata = parseMetadata(content);
            String body = extractBody(content);

            Skill skill = new Skill(name, metadata, body, path);
            registry.registerSkill(skill);
            loadedPaths.add(path);
            logger.debug("Loaded skill: {} from {}", name, path);
            return true;

        } catch (IOException e) {
            logger.warn("Failed to load skill {}: {}", path, e.getMessage());
            return false;
        }
    }

    /**
     * Load all skill files from a directory.
     *
     * @param directory Path to directory
     * @return Number of skills loaded
     */
    public int loadFromDir(Path directory) {
        if (!Files.exists(directory)) {
            return 0;
        }

        int count = 0;
        for (Path skillFile : discoverSkills(directory)) {
            if (loadFromFile(skillFile)) {
                count++;
            }
        }

        loadedPaths.add(directory);
        return count;
    }

    /**
     * Discover all skill files in a directory.
     *
     * @param directory Path to search
     * @return List of skill file paths
     */
    public List<Path> discoverSkills(Path directory) {
        List<Path> skillFiles = new ArrayList<>();

        if (!Files.exists(directory)) {
            return skillFiles;
        }

        try {
            Files.walk(directory)
                .filter(p -> p.toString().endsWith(".md"))
                .forEach(p -> {
                    // Check if it has skill frontmatter
                    try {
                        String content = Files.readString(p);
                        if (content.startsWith("---")) {
                            int endIdx = content.indexOf("---", 3);
                            if (endIdx > 0) {
                                String frontmatter = content.substring(3, endIdx);
                                // Check for skill markers
                                if (frontmatter.contains("name:") || frontmatter.contains("description:")) {
                                    skillFiles.add(p);
                                }
                            }
                        }
                    } catch (IOException e) {
                        // Skip files that can't be read
                    }
                });
        } catch (IOException e) {
            logger.warn("Failed to walk directory {}: {}", directory, e.getMessage());
        }

        return skillFiles;
    }

    /**
     * Parse skill metadata from frontmatter.
     */
    private SkillMetadata parseMetadata(String content) {
        if (!content.startsWith("---")) {
            return new SkillMetadata("", "1.0", List.of());
        }

        int endIdx = content.indexOf("---", 3);
        if (endIdx == -1) {
            return new SkillMetadata("", "1.0", List.of());
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
     * Get list of loaded paths.
     *
     * @return List of paths that were loaded
     */
    public List<Path> getLoadedPaths() {
        return new ArrayList<>(loadedPaths);
    }

    /**
     * Clear loaded paths list.
     */
    public void clearLoaded() {
        loadedPaths.clear();
    }

    /**
     * Get the default skill search paths.
     */
    public static List<Path> getDefaultSkillPaths() {
        return DEFAULT_SKILL_PATHS;
    }
}
