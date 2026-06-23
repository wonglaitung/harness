package com.harness.memory;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import static org.junit.jupiter.api.Assertions.*;

import java.nio.file.Path;

class MemoryDeduplicationTest {

    @TempDir
    Path tempDir;

    @Test
    void testAddEntryReturnsTrue() {
        Path memoryFile = tempDir.resolve("MEMORY.md");
        MemoryFileManager manager = new MemoryFileManager(memoryFile);

        MemoryEntry entry = new MemoryEntry(
            MemoryCategory.USER_PROFILE,
            "操作系统：Windows",
            MemorySource.USER_INPUT
        );

        boolean added = manager.addEntry(entry);
        assertTrue(added, "First entry should be added successfully");
    }

    @Test
    void testDuplicateEntryReturnsFalse() {
        Path memoryFile = tempDir.resolve("MEMORY.md");
        MemoryFileManager manager = new MemoryFileManager(memoryFile);

        // Add first entry
        MemoryEntry entry1 = new MemoryEntry(
            MemoryCategory.USER_PROFILE,
            "操作系统：Windows",
            MemorySource.USER_INPUT
        );
        boolean added1 = manager.addEntry(entry1);
        assertTrue(added1);

        // Try to add similar entry
        MemoryEntry entry2 = new MemoryEntry(
            MemoryCategory.USER_PROFILE,
            "操作系统：Windows 10",  // Similar content
            MemorySource.USER_INPUT
        );
        boolean added2 = manager.addEntry(entry2);
        assertFalse(added2, "Similar entry should be rejected as duplicate");
    }

    @Test
    void testDifferentEntriesBothAdded() {
        Path memoryFile = tempDir.resolve("MEMORY.md");
        MemoryFileManager manager = new MemoryFileManager(memoryFile);

        // Add first entry
        MemoryEntry entry1 = new MemoryEntry(
            MemoryCategory.USER_PROFILE,
            "操作系统：Windows",
            MemorySource.USER_INPUT
        );
        boolean added1 = manager.addEntry(entry1);
        assertTrue(added1);

        // Add different entry
        MemoryEntry entry2 = new MemoryEntry(
            MemoryCategory.USER_PROFILE,
            "主题偏好：深色",
            MemorySource.USER_INPUT
        );
        boolean added2 = manager.addEntry(entry2);
        assertTrue(added2, "Different entry should be added");
    }

    @Test
    void testSkipDuplicateCheck() {
        Path memoryFile = tempDir.resolve("MEMORY.md");
        MemoryFileManager manager = new MemoryFileManager(memoryFile);

        // Add first entry
        MemoryEntry entry1 = new MemoryEntry(
            MemoryCategory.USER_PROFILE,
            "操作系统：Windows",
            MemorySource.USER_INPUT
        );
        manager.addEntry(entry1);

        // Add similar entry with checkDuplicate=false
        MemoryEntry entry2 = new MemoryEntry(
            MemoryCategory.USER_PROFILE,
            "操作系统：Windows 10",
            MemorySource.USER_INPUT
        );
        boolean added = manager.addEntry(entry2, false);
        assertTrue(added, "Entry should be added when checkDuplicate is false");
    }
}
