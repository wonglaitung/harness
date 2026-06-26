package com.harness.memory;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import static org.junit.jupiter.api.Assertions.*;

import java.nio.file.Path;
import java.time.Instant;
import java.util.List;

class MemoryFileManagerTest {

    @TempDir
    Path tempDir;

    @Test
    void testCreateMemoryFile() {
        Path memoryFile = tempDir.resolve("MEMORY.md");
        MemoryFileManager manager = new MemoryFileManager(tempDir);

        // The manager doesn't create the file until we write to it
        assertFalse(manager.exists());
    }

    @Test
    void testAddAndGetMemory() {
        MemoryFileManager manager = new MemoryFileManager(tempDir);

        MemoryEntry entry = new MemoryEntry(
            MemoryCategory.USER_PROFILE,
            "Test content",
            MemorySource.USER_INPUT
        );

        manager.addEntry(entry);

        List<String> memories = manager.getEntries(MemoryCategory.USER_PROFILE);
        assertFalse(memories.isEmpty());
        assertTrue(memories.get(0).contains("Test content"));
    }

    @Test
    void testGetEntriesByCategory() {
        MemoryFileManager manager = new MemoryFileManager(tempDir);

        MemoryEntry userEntry = new MemoryEntry(
            MemoryCategory.USER_PROFILE, "User content", MemorySource.USER_INPUT
        );
        MemoryEntry projectEntry = new MemoryEntry(
            MemoryCategory.PROJECT_CONTEXT, "Project content", MemorySource.USER_INPUT
        );

        manager.addEntry(userEntry);
        manager.addEntry(projectEntry);

        List<String> userMemories = manager.getEntries(MemoryCategory.USER_PROFILE);
        assertEquals(1, userMemories.size());
        assertTrue(userMemories.get(0).contains("User content"));
    }

    @Test
    void testRemoveEntry() {
        MemoryFileManager manager = new MemoryFileManager(tempDir);

        MemoryEntry entry = new MemoryEntry(
            MemoryCategory.USER_PROFILE, "Test content", MemorySource.USER_INPUT
        );

        manager.addEntry(entry);
        assertEquals(1, manager.getEntries(MemoryCategory.USER_PROFILE).size());

        manager.removeEntry(MemoryCategory.USER_PROFILE, 0);
        assertTrue(manager.getEntries(MemoryCategory.USER_PROFILE).isEmpty());
    }
}