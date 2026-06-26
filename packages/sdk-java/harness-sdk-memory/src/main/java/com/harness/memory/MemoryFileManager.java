package com.harness.memory;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Comparator;
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
 *
 * Supports memory scoring and archival:
 * - Retrieval Strength: Time decay + access bonus
 * - Archive low-importance entries when capacity exceeded
 */
public class MemoryFileManager {

    private static final Logger logger = LoggerFactory.getLogger(MemoryFileManager.class);

    public static final String FILE_NAME = "MEMORY.md";
    public static final String ARCHIVE_FILE_NAME = "MEMORY_ARCHIVE.md";

    private final Path projectRoot;
    private final Path memoryFile;
    private final Path archiveFile;
    private final MemoryScoringConfig scoringConfig;

    public MemoryFileManager(Path projectRoot, MemoryScoringConfig scoringConfig) {
        this.projectRoot = projectRoot;
        this.memoryFile = projectRoot.resolve(FILE_NAME);
        this.archiveFile = projectRoot.resolve(ARCHIVE_FILE_NAME);
        this.scoringConfig = scoringConfig != null ? scoringConfig : MemoryScoringConfig.defaults();
    }

    public MemoryFileManager(Path projectRoot) {
        this(projectRoot, MemoryScoringConfig.defaults());
    }

    public MemoryFileManager() {
        this(Path.of(System.getProperty("user.home"), ".harness"), MemoryScoringConfig.defaults());
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

    /**
     * Get the archive file path.
     */
    public Path getArchiveFilePath() {
        return archiveFile;
    }

    // ==================== Capacity Management ====================

    /**
     * Check if Core Memory exceeds token limit.
     *
     * @return Array of [isOverLimit, currentTokens]
     */
    public Object[] checkCapacity() {
        String content = toContextString();
        int tokens = estimateTokens(content);
        return new Object[]{tokens > scoringConfig.maxCoreMemoryTokens(), tokens};
    }

    /**
     * Estimate token count for text.
     * Simple estimation: ~4 characters per token for mixed Chinese/English.
     */
    private int estimateTokens(String text) {
        return text.length() / 4;
    }

    /**
     * Load entries with full metadata for a category.
     */
    private List<MemoryEntry> loadEntriesWithMetadata(MemoryCategory category) {
        if (!exists()) {
            return new ArrayList<>();
        }

        try {
            String content = Files.readString(memoryFile);
            List<MemoryEntry> entries = new ArrayList<>();
            boolean inSection = false;

            for (String line : content.split("\n")) {
                // Check for section header
                if (line.startsWith("## ")) {
                    String header = line.substring(3).trim();
                    inSection = MemoryCategory.fromHeader(header) == category;
                    continue;
                }

                // Parse entry if in target section
                if (inSection && line.strip().startsWith("-")) {
                    MemoryEntry entry = parseEntryWithMetadata(line, category);
                    if (entry != null) {
                        entries.add(entry);
                    }
                }
            }

            return entries;
        } catch (IOException e) {
            logger.warn("Failed to load entries with metadata: {}", e.getMessage());
            return new ArrayList<>();
        }
    }

    /**
     * Parse entry with metadata from markdown line.
     */
    private MemoryEntry parseEntryWithMetadata(String line, MemoryCategory category) {
        line = line.strip();
        if (!line.startsWith("-")) {
            return null;
        }

        String content = line.substring(1).strip();
        double importance = 1.0;
        int accessCount = 0;

        // Extract metadata from HTML comment if present
        Pattern metaPattern = Pattern.compile("<!-- importance=(\\d+\\.\\d+), accesses=(\\d+) -->");
        Matcher metaMatcher = metaPattern.matcher(content);
        if (metaMatcher.find()) {
            importance = Double.parseDouble(metaMatcher.group(1));
            accessCount = Integer.parseInt(metaMatcher.group(2));
            content = content.substring(0, metaMatcher.start()).strip();
        }

        // Check for date prefix
        Instant createdAt = Instant.now();
        Pattern datePattern = Pattern.compile("(\\d{4}-\\d{2}-\\d{2}):\\s*(.+)");
        Matcher dateMatcher = datePattern.matcher(content);
        if (dateMatcher.matches()) {
            try {
                createdAt = Instant.parse(dateMatcher.group(1) + "T00:00:00Z");
                content = dateMatcher.group(2);
            } catch (Exception e) {
                // Ignore parse errors
            }
        }

        if (content.isEmpty()) {
            return null;
        }

        return MemoryEntry.builder()
            .category(category)
            .content(content)
            .source(MemorySource.AGENT_OBSERVATION)
            .createdAt(createdAt)
            .importance(importance)
            .accessCount(accessCount)
            .build();
    }

    /**
     * Load all entries with metadata across all sections.
     */
    private List<MemoryEntryInfo> loadAllEntriesWithMetadata() {
        List<MemoryEntryInfo> allEntries = new ArrayList<>();
        for (MemoryCategory category : MemoryCategory.values()) {
            List<MemoryEntry> entries = loadEntriesWithMetadata(category);
            for (int i = 0; i < entries.size(); i++) {
                allEntries.add(new MemoryEntryInfo(category, i, entries.get(i)));
            }
        }
        return allEntries;
    }

    /**
     * Archive low-importance entries when capacity exceeded.
     *
     * @return Number of entries archived
     */
    public int archiveLowImportance() {
        Object[] capacity = checkCapacity();
        boolean isOver = (boolean) capacity[0];
        if (!isOver) {
            return 0;
        }

        // Collect all entries with metadata
        List<MemoryEntryInfo> allEntries = loadAllEntriesWithMetadata();

        // Sort by importance (lowest first)
        allEntries.sort(Comparator.comparingDouble(e -> e.entry.importance()));

        int archivedCount = 0;
        for (MemoryEntryInfo item : allEntries) {
            // Archive the entry
            archiveToFile(item.entry);

            // Remove from Core Memory
            removeEntry(item.category, item.index - archivedCount);
            archivedCount++;

            // Check if we've freed enough space (keep 20% buffer)
            Object[] newCapacity = checkCapacity();
            boolean stillOver = (boolean) newCapacity[0];
            int newTokens = (int) newCapacity[1];
            if (!stillOver && newTokens <= scoringConfig.maxCoreMemoryTokens() * 0.8) {
                break;
            }
        }

        logger.info("Archived {} entries from Core Memory", archivedCount);
        return archivedCount;
    }

    /**
     * Archive entry to MEMORY_ARCHIVE.md file.
     */
    private void archiveToFile(MemoryEntry entry) {
        if (scoringConfig.archiveFallback() == MemoryScoringConfig.ArchiveFallback.NONE) {
            return;
        }

        if (scoringConfig.archiveFallback() == MemoryScoringConfig.ArchiveFallback.DELETE) {
            logger.info("Deleting low-importance entry: {}", entry.content().substring(0, Math.min(50, entry.content().length())));
            return;
        }

        // Load existing archive sections
        ArchiveSections archiveSections = loadArchiveSections();

        // Add entry to appropriate section
        archiveSections.addEntry(entry);

        // Save archive file
        saveArchiveSections(archiveSections);
        logger.info("Archived entry to {}: {}...", archiveFile, entry.content().substring(0, Math.min(50, entry.content().length())));
    }

    /**
     * Load MEMORY_ARCHIVE.md content.
     */
    private ArchiveSections loadArchiveSections() {
        ArchiveSections sections = new ArchiveSections();

        if (!Files.exists(archiveFile)) {
            return sections;
        }

        try {
            String content = Files.readString(archiveFile);
            String currentSection = null;

            for (String line : content.split("\n")) {
                if (line.startsWith("## ")) {
                    currentSection = line.substring(3).trim().toLowerCase().replace(" ", "_");
                    continue;
                }

                if (currentSection != null && line.strip().startsWith("-")) {
                    // Parse archive entry: - [YYYY-MM-DD, importance=X] content
                    Pattern pattern = Pattern.compile("- \\[(\\d{4}-\\d{2}-\\d{2}), importance=(\\d+\\.\\d+)\\] (.+)");
                    Matcher matcher = pattern.matcher(line.strip().substring(2));
                    if (matcher.matches()) {
                        sections.addArchivedEntry(currentSection, new ArchivedEntry(
                            Instant.parse(matcher.group(1) + "T00:00:00Z"),
                            Double.parseDouble(matcher.group(2)),
                            matcher.group(3)
                        ));
                    }
                }
            }
        } catch (IOException e) {
            logger.warn("Failed to load archive file: {}", e.getMessage());
        }

        return sections;
    }

    /**
     * Save to MEMORY_ARCHIVE.md file.
     */
    private void saveArchiveSections(ArchiveSections sections) {
        StringBuilder sb = new StringBuilder();
        sb.append("# Archived Memory\n\n");
        sb.append("> 以下记忆已从 Core Memory 归档。可通过全文搜索查找。\n\n");

        String[] sectionOrder = {"user_profile", "key_decisions", "learned_patterns", "project_context"};
        String[] sectionNames = {"User Profile", "Key Decisions", "Learned Patterns", "Project Context"};

        for (int i = 0; i < sectionOrder.length; i++) {
            List<ArchivedEntry> entries = sections.getSection(sectionOrder[i]);
            if (!entries.isEmpty()) {
                sb.append("## ").append(sectionNames[i]).append("\n");
                for (ArchivedEntry entry : entries) {
                    String dateStr = entry.archivedAt.toString().substring(0, 10);
                    sb.append(String.format("- [%s, importance=%.2f] %s\n", dateStr, entry.importance, entry.content));
                }
                sb.append("\n");
            }
        }

        try {
            Files.writeString(archiveFile, sb.toString());
        } catch (IOException e) {
            logger.error("Failed to save archive file: {}", e.getMessage());
        }
    }

    /**
     * Helper class for entry info during archive.
     */
    private record MemoryEntryInfo(MemoryCategory category, int index, MemoryEntry entry) {}

    /**
     * Helper class for archived entry.
     */
    private record ArchivedEntry(Instant archivedAt, double importance, String content) {}

    /**
     * Helper class for archive sections.
     */
    private static class ArchiveSections {
        private final java.util.Map<String, List<ArchivedEntry>> sections = new java.util.HashMap<>();

        ArchiveSections() {
            sections.put("user_profile", new ArrayList<>());
            sections.put("key_decisions", new ArrayList<>());
            sections.put("learned_patterns", new ArrayList<>());
            sections.put("project_context", new ArrayList<>());
        }

        void addEntry(MemoryEntry entry) {
            String sectionKey = getCategoryKey(entry.category());
            sections.get(sectionKey).add(new ArchivedEntry(
                Instant.now(),
                entry.importance(),
                entry.content()
            ));
        }

        void addArchivedEntry(String section, ArchivedEntry entry) {
            if (sections.containsKey(section)) {
                sections.get(section).add(entry);
            }
        }

        List<ArchivedEntry> getSection(String key) {
            return sections.getOrDefault(key, new ArrayList<>());
        }

        private String getCategoryKey(MemoryCategory category) {
            return switch (category) {
                case USER_PROFILE -> "user_profile";
                case KEY_DECISIONS -> "key_decisions";
                case LEARNED_PATTERNS -> "learned_patterns";
                case PROJECT_CONTEXT -> "project_context";
            };
        }
    }
}