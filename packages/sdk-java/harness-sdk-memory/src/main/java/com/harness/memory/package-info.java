/**
 * Memory system for Harness SDK Java.
 *
 * Provides persistent context storage across sessions:
 * - User Profile: Role, preferences, response style
 * - Key Decisions: Important architectural choices
 * - Learned Patterns: User preferences discovered over time
 * - Project Context: Project-specific conventions
 *
 * Key classes:
 * - {@link MemoryFileManager}: Manages MEMORY.md files
 * - {@link SessionManager}: Manages conversation sessions
 * - {@link MemoryEntry}: A single memory record
 */
package com.harness.memory;
