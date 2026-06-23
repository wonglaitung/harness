package com.harness.memory;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Instant;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Manager for MEMORY.md files.
 *
 * Handles reading, writing, and updating memory files in the standard format.
 *
 * MEMORY.md files store persistent context across sessions:
 * - User Profile: Role, preferences, response style
 * - Key Decisions: Important architectural choices
 * - Learned Patterns: User preferences discovered over time
 * - Project Context: Project-specific conventions
 */
public class MemoryFileManager {

    private static final Logger logger = LoggerFactory.getLogger(MemoryFileManager.class);

    public static final String FILE_NAME = "MEMORY.md";

    private final Path projectRoot;
    private final Path memoryFile;

    public MemoryFileManager(Path projectRoot) {
        this.projectRoot = projectRoot;
        this.memoryFile = projectRoot.resolve(FILE_NAME);
    }

    public MemoryFileManager() {
        this(Path.of(System.getProperty("user.home"), ".harness"));
    }

    /**
     * Check if MEMORY.md exists.
     */
    public boolean exists() {
        return Files.exists(memoryFile);
    }

    /**
     * Load MEMORY.md content.
     */
    public MemorySections load() {
        MemorySections sections = new MemorySections();

        if (!exists()) {
            return sections;
        }

        try {
            String content = Files.readString(memoryFile);
            return parseContent(content);
        } catch (IOException e) {
            logger.warn("Failed to load MEMORY.md: {}", e.getMessage());
            return sections;
        }
    }

    /**
     * Parse MEMORY.md content into sections.
     */
    private MemorySections parseContent(String content) {
        MemorySections sections = new MemorySections();
        MemoryCategory currentCategory = null;

        for (String line : content.split("\n")) {
            // Check for section header
            if (line.startsWith("## ")) {
                String header = line.substring(3).trim();
                currentCategory = MemoryCategory.fromHeader(header);
                continue;
            }

            // Parse entry
            if (currentCategory != null && line.strip().startsWith("-")) {
                String entry = parseEntry(line);
                if (entry != null && !entry.isEmpty()) {
                    sections.addEntry(currentCategory, entry);
                }
            }
        }

        return sections;
    }

    /**
     * Parse a single entry from markdown list item.
     */
    private String parseEntry(String line) {
        line = line.strip();
        if (!line.startsWith("-")) {
            return null;
        }

        String content = line.substring(1).strip();

        // Check for date prefix (YYYY-MM-DD:)
        Pattern datePattern = Pattern.compile("(\\d{4}-\\d{2}-\\d{2}):\\s*(.+)");
        Matcher matcher = datePattern.matcher(content);
        if (matcher.matches()) {
            content = matcher.group(2);
        }

        return content;
    }

    /**
     * Save sections to MEMORY.md.
     */
    public void save(MemorySections sections) {
        try {
            String content = buildContent(sections);
            Files.writeString(memoryFile, content);
            logger.info("Saved memory to {}", memoryFile);
        } catch (IOException e) {
            logger.error("Failed to save MEMORY.md: {}", e.getMessage());
        }
    }

    /**
     * Build MEMORY.md content from sections.
     */
    private String buildContent(MemorySections sections) {
        StringBuilder sb = new StringBuilder();
        sb.append("# MEMORY.md\n\n");

        // User Profile
        List<String> userProfile = sections.getSection(MemoryCategory.USER_PROFILE);
        if (!userProfile.isEmpty()) {
            sb.append("## User Profile\n");
            for (String entry : userProfile) {
                sb.append("- ").append(entry).append("\n");
            }
            sb.append("\n");
        }

        // Key Decisions
        List<String> keyDecisions = sections.getSection(MemoryCategory.KEY_DECISIONS);
        if (!keyDecisions.isEmpty()) {
            sb.append("## Key Decisions\n");
            for (String entry : keyDecisions) {
                // Add date prefix if not present
                if (!entry.matches("\\d{4}-\\d{2}-\\d{2}:.*")) {
                    String dateStr = Instant.now().toString().substring(0, 10);
                    sb.append("- ").append(dateStr).append(": ").append(entry).append("\n");
                } else {
                    sb.append("- ").append(entry).append("\n");
                }
            }
            sb.append("\n");
        }

        // Learned Patterns
        List<String> learnedPatterns = sections.getSection(MemoryCategory.LEARNED_PATTERNS);
        if (!learnedPatterns.isEmpty()) {
            sb.append("## Learned Patterns\n");
            for (String entry : learnedPatterns) {
                sb.append("- ").append(entry).append("\n");
            }
            sb.append("\n");
        }

        // Project Context
        List<String> projectContext = sections.getSection(MemoryCategory.PROJECT_CONTEXT);
        if (!projectContext.isEmpty()) {
            sb.append("## Project Context\n");
            for (String entry : projectContext) {
                sb.append("- ").append(entry).append("\n");
            }
            sb.append("\n");
        }

        return sb.toString();
    }

    /**
     * Add a new entry to MEMORY.md.
     *
     * @param entry The memory entry to add
     * @return true if entry was added, false if skipped as duplicate
     */
    public boolean addEntry(MemoryEntry entry) {
        return addEntry(entry, true);
    }

    /**
     * Add a new entry to MEMORY.md.
     *
     * @param entry The memory entry to add
     * @param checkDuplicate If true, check for similar existing entries and skip if duplicate
     * @return true if entry was added, false if skipped as duplicate
     */
    public boolean addEntry(MemoryEntry entry, boolean checkDuplicate) {
        MemorySections sections = load();
        List<String> section = sections.getSection(entry.category());

        if (checkDuplicate) {
            for (String existing : section) {
                double similarity = calculateSimilarity(entry.content(), existing);
                if (similarity > 0.7) {
                    logger.info("Skipping duplicate memory: '{}' similar to '{}' (similarity={})",
                        entry.content(), existing, String.format("%.2f", similarity));
                    return false;
                }
            }
        }

        sections.addEntry(entry.category(), entry.content());
        save(sections);
        return true;
    }

    /**
     * Calculate text similarity using character-level Jaccard similarity.
     *
     * Supports both Chinese and English text without requiring word segmentation.
     *
     * @param text1 First text
     * @param text2 Second text
     * @return Similarity score (0.0 to 1.0)
     */
    private double calculateSimilarity(String text1, String text2) {
        text1 = text1.toLowerCase();
        text2 = text2.toLowerCase();

        if (text1.isEmpty() || text2.isEmpty()) {
            return 0.0;
        }

        Set<String> ngrams1 = getNgrams(text1, 2);
        Set<String> ngrams2 = getNgrams(text2, 2);

        Set<String> intersection = new HashSet<>(ngrams1);
        intersection.retainAll(ngrams2);

        Set<String> union = new HashSet<>(ngrams1);
        union.addAll(ngrams2);

        return (double) intersection.size() / union.size();
    }

    /**
     * Get character n-grams from text.
     *
     * @param text Input text
     * @param n N-gram size
     * @return Set of n-grams
     */
    private Set<String> getNgrams(String text, int n) {
        if (text.length() < n) {
            return Set.of(text);
        }
        Set<String> ngrams = new HashSet<>();
        for (int i = 0; i <= text.length() - n; i++) {
            ngrams.add(text.substring(i, i + n));
        }
        return ngrams;
    }

    /**
     * Remove an entry from a section.
     */
    public boolean removeEntry(MemoryCategory category, int index) {
        MemorySections sections = load();
        if (sections.removeEntry(category, index)) {
            save(sections);
            return true;
        }
        return false;
    }

    /**
     * Get all entries in a category.
     */
    public List<String> getEntries(MemoryCategory category) {
        MemorySections sections = load();
        return sections.getSection(category);
    }

    /**
     * Format memory as context string for LLM.
     */
    public String toContextString() {
        MemorySections sections = load();

        if (sections.isEmpty()) {
            return "";
        }

        StringBuilder sb = new StringBuilder();
        sb.append("# Project Memory\n\n");

        for (MemoryCategory cat : MemoryCategory.values()) {
            List<String> entries = sections.getSection(cat);
            if (!entries.isEmpty()) {
                sb.append("## ").append(cat.getHeader()).append("\n");
                for (String entry : entries) {
                    sb.append("- ").append(entry).append("\n");
                }
                sb.append("\n");
            }
        }

        return sb.toString();
    }

    /**
     * Clear all memory by deleting MEMORY.md.
     */
    public void clear() {
        if (exists()) {
            try {
                Files.delete(memoryFile);
                logger.info("Deleted {}", memoryFile);
            } catch (IOException e) {
                logger.error("Failed to delete MEMORY.md: {}", e.getMessage());
            }
        }
    }

    /**
     * Get the memory file path.
     */
    public Path getMemoryFilePath() {
        return memoryFile;
    }
}