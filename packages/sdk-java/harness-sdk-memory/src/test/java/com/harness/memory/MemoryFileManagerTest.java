package com.harness.memory;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import static org.junit.jupiter.api.Assertions.*;

import java.nio.file.Path;
import java.time.Instant;

class MemoryFileManagerTest {

    @TempDir
    Path tempDir;

    @Test
    void testCreateMemoryFile() {
        Path memoryFile = tempDir.resolve("MEMORY.md");
        MemoryFileManager manager = new MemoryFileManager(memoryFile);

        assertTrue(java.nio.file.Files.exists(memoryFile));
    }

    @Test
    void testAddAndGetMemory() {
        Path memoryFile = tempDir.resolve("MEMORY.md");
        MemoryFileManager manager = new MemoryFileManager(memoryFile);

        MemoryEntry entry = new MemoryEntry(
            "user",
            "Test User",
            "Test content",
            MemoryCategory.USER,
            MemorySource.HUMAN,
            Instant.now()
        );

        manager.addEntry(entry);

        java.util.List<MemoryEntry> memories = manager.getEntries();
        assertFalse(memories.isEmpty());
        assertEquals("Test content", memories.get(0).content());
    }

    @Test
    void testGetEntriesByCategory() {
        Path memoryFile = tempDir.resolve("MEMORY.md");
        MemoryFileManager manager = new MemoryFileManager(memoryFile);

        MemoryEntry userEntry = new MemoryEntry(
            "user", "User", "User content",
            MemoryCategory.USER, MemorySource.HUMAN, Instant.now()
        );
        MemoryEntry projectEntry = new MemoryEntry(
            "project", "Project", "Project content",
            MemoryCategory.PROJECT, MemorySource.HUMAN, Instant.now()
        );

        manager.addEntry(userEntry);
        manager.addEntry(projectEntry);

        java.util.List<MemoryEntry> userMemories = manager.getEntriesByCategory(MemoryCategory.USER);
        assertEquals(1, userMemories.size());
        assertEquals("User content", userMemories.get(0).content());
    }

    @Test
    void testRemoveEntry() {
        Path memoryFile = tempDir.resolve("MEMORY.md");
        MemoryFileManager manager = new MemoryFileManager(memoryFile);

        MemoryEntry entry = new MemoryEntry(
            "user", "User", "Test content",
            MemoryCategory.USER, MemorySource.HUMAN, Instant.now()
        );

        manager.addEntry(entry);
        assertEquals(1, manager.getEntries().size());

        manager.removeEntry("user");
        assertTrue(manager.getEntries().isEmpty());
    }
}