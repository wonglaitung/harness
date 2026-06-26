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
     * Create a skill without file path.
     */
    public static Skill of(String name, String description, String content) {
        return new Skill(name, new SkillMetadata(description, "1.0", List.of()), content, null);
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

        // Parse metadata from content (simple extraction)
        String description = extractDescription(content, name);
        List<String> tools = extractTools(content);

        SkillMetadata metadata = new SkillMetadata(description, "1.0", tools);
        return new Skill(name, metadata, content, path);
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