package com.harness.skills;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

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

    private static final Logger logger = LoggerFactory.getLogger(Skill.class);

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
     * Get skill enabled status.
     */
    public boolean enabled() {
        return metadata.enabled();
    }

    /**
     * Create a skill without file path.
     */
    public static Skill of(String name, String description, String content) {
        return new Skill(name, new SkillMetadata(description, "1.0", List.of(), List.of(), List.of(), true), content, null);
    }

    /**
     * Create a skill with enabled status.
     */
    public static Skill of(String name, String description, String content, boolean enabled) {
        return new Skill(name, new SkillMetadata(description, "1.0", List.of(), List.of(), List.of(), enabled), content, null);
    }

    /**
     * Load a skill from a markdown file.
     *
     * @param path Path to the skill markdown file
     * @return Loaded skill
     * @throws IOException if file cannot be read
     */
    public static Skill fromFile(Path path) throws IOException {
        String content = Files.readString(path);
        String fileName = path.getFileName().toString();

        // Extract skill name from filename (remove .md extension)
        String name = fileName.endsWith(".md")
            ? fileName.substring(0, fileName.length() - 3)
            : fileName;

        // Parse metadata from frontmatter
        SkillMetadata metadata = parseMetadata(content, name);
        String body = extractBody(content);

        return new Skill(name, metadata, body, path);
    }

    /**
     * Parse skill metadata from frontmatter.
     */
    private static SkillMetadata parseMetadata(String content, String skillName) {
        String description = "";
        String version = "1.0";
        boolean enabled = true;
        List<String> tools = List.of();

        if (content.startsWith("---")) {
            int endIdx = content.indexOf("---", 3);
            if (endIdx > 0) {
                String frontmatter = content.substring(3, endIdx).trim();

                for (String line : frontmatter.split("\n")) {
                    if (line.startsWith("description:")) {
                        description = line.substring("description:".length()).trim();
                    } else if (line.startsWith("version:")) {
                        version = line.substring("version:".length()).trim();
                    } else if (line.startsWith("enabled:")) {
                        String value = line.substring("enabled:".length()).trim().toLowerCase();
                        enabled = !value.equals("false") && !value.equals("no") && !value.equals("0");
                    }
                }
            }
        }

        // Fallback to extracting description from content
        if (description.isEmpty()) {
            description = extractDescription(content, skillName);
        }

        tools = extractTools(content);

        return new SkillMetadata(description, version, List.of(), tools, List.of(), enabled);
    }

    /**
     * Extract body content after frontmatter.
     */
    private static String extractBody(String content) {
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
     * Extract description from skill content.
     */
    private static String extractDescription(String content, String skillName) {
        // Look for first paragraph after title
        String[] lines = content.split("\n");
        for (int i = 0; i < lines.length; i++) {
            String line = lines[i].trim();
            if (line.startsWith("# ") && i + 1 < lines.length) {
                // Find next non-empty, non-header line
                for (int j = i + 1; j < lines.length; j++) {
                    String nextLine = lines[j].trim();
                    if (!nextLine.isEmpty() && !nextLine.startsWith("#")) {
                        return nextLine.length() > 200
                            ? nextLine.substring(0, 200) + "..."
                            : nextLine;
                    }
                }
            }
        }
        return "Skill: " + skillName;
    }

    /**
     * Extract tool requirements from skill content.
     */
    private static List<String> extractTools(String content) {
        // Simple extraction - look for "Tools:" or "工具:" section
        List<String> tools = List.of();
        String[] lines = content.split("\n");
        for (int i = 0; i < lines.length; i++) {
            String line = lines[i].trim();
            if (line.startsWith("Tools:") || line.startsWith("工具:") || line.startsWith("## Tools")) {
                // Collect tools from following lines
                List<String> foundTools = new ArrayList<>();
                for (int j = i + 1; j < lines.length && j < i + 20; j++) {
                    String toolLine = lines[j].trim();
                    if (toolLine.isEmpty() || toolLine.startsWith("#")) break;
                    if (toolLine.startsWith("- ") || toolLine.startsWith("* ")) {
                        foundTools.add(toolLine.substring(2));
                    }
                }
                if (!foundTools.isEmpty()) {
                    return foundTools;
                }
            }
        }
        return tools;
    }
}