package com.harness.memory;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * All memory sections.
 */
public class MemorySections {

    private final Map<MemoryCategory, List<String>> sections;

    public MemorySections() {
        this.sections = new HashMap<>();
        for (MemoryCategory cat : MemoryCategory.values()) {
            sections.put(cat, new ArrayList<>());
        }
    }

    /**
     * Get a section by category.
     */
    public List<String> getSection(MemoryCategory category) {
        return sections.getOrDefault(category, new ArrayList<>());
    }

    /**
     * Set a section by category.
     */
    public void setSection(MemoryCategory category, List<String> entries) {
        sections.put(category, new ArrayList<>(entries));
    }

    /**
     * Add entry to a section.
     */
    public void addEntry(MemoryCategory category, String entry) {
        sections.get(category).add(entry);
    }

    /**
     * Remove entry from a section.
     */
    public boolean removeEntry(MemoryCategory category, int index) {
        List<String> section = sections.get(category);
        if (index >= 0 && index < section.size()) {
            section.remove(index);
            return true;
        }
        return false;
    }

    /**
     * Check if all sections are empty.
     */
    public boolean isEmpty() {
        return sections.values().stream().allMatch(List::isEmpty);
    }

    /**
     * Get total number of entries.
     */
    public int totalEntries() {
        return sections.values().stream().mapToInt(List::size).sum();
    }
}