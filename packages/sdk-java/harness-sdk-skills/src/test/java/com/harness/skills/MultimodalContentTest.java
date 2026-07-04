package com.harness.skills;

import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;
import java.util.*;

/**
 * Test multimodal content handling in ProgressiveSkillLoader.
 */
class MultimodalContentTest {

    @Test
    void testMatchesWithString() {
        Map<String, List<String>> triggers = new HashMap<>();
        triggers.put("keywords", Arrays.asList("test", "hello"));

        ProgressiveSkillLoader.SkillMetadata meta = new ProgressiveSkillLoader.SkillMetadata(
            "test-skill", "Test skill",
            java.nio.file.Path.of("/tmp/test.md"), triggers, "1.0.0"
        );

        assertTrue(meta.matches("hello world"));
        assertTrue(meta.matches("this is a test"));
        assertFalse(meta.matches("no match here"));
    }

    @Test
    void testMatchesWithMultimodalContent() {
        Map<String, List<String>> triggers = new HashMap<>();
        triggers.put("keywords", Arrays.asList("test", "hello"));

        ProgressiveSkillLoader.SkillMetadata meta = new ProgressiveSkillLoader.SkillMetadata(
            "test-skill", "Test skill",
            java.nio.file.Path.of("/tmp/test.md"), triggers, "1.0.0"
        );

        // Create multimodal content (List of Map)
        List<Map<String, Object>> multimodal = new ArrayList<>();
        Map<String, Object> textBlock = new HashMap<>();
        textBlock.put("type", "text");
        textBlock.put("text", "hello world from multimodal");
        multimodal.add(textBlock);

        Map<String, Object> imageBlock = new HashMap<>();
        imageBlock.put("type", "image");
        imageBlock.put("source", Map.of("type", "base64", "data", "abc123"));
        multimodal.add(imageBlock);

        assertTrue(meta.matches(multimodal));
    }

    @Test
    void testMatchesWithNonMatchingMultimodalContent() {
        Map<String, List<String>> triggers = new HashMap<>();
        triggers.put("keywords", Arrays.asList("test", "hello"));

        ProgressiveSkillLoader.SkillMetadata meta = new ProgressiveSkillLoader.SkillMetadata(
            "test-skill", "Test skill",
            java.nio.file.Path.of("/tmp/test.md"), triggers, "1.0.0"
        );

        List<Map<String, Object>> noMatch = new ArrayList<>();
        Map<String, Object> noMatchBlock = new HashMap<>();
        noMatchBlock.put("type", "text");
        noMatchBlock.put("text", "nothing here");
        noMatch.add(noMatchBlock);

        assertFalse(meta.matches(noMatch));
    }

    @Test
    void testMatchSkillsWithMultimodalContent() {
        ProgressiveSkillLoader loader = new ProgressiveSkillLoader();

        Map<String, List<String>> triggers = new HashMap<>();
        triggers.put("keywords", Arrays.asList("test", "hello"));

        ProgressiveSkillLoader.SkillMetadata meta = new ProgressiveSkillLoader.SkillMetadata(
            "test-skill", "Test skill",
            java.nio.file.Path.of("/tmp/test.md"), triggers, "1.0.0"
        );

        List<ProgressiveSkillLoader.SkillMetadata> skills = Arrays.asList(meta);

        // Create multimodal content
        List<Map<String, Object>> multimodal = new ArrayList<>();
        Map<String, Object> textBlock = new HashMap<>();
        textBlock.put("type", "text");
        textBlock.put("text", "hello world");
        multimodal.add(textBlock);

        List<ProgressiveSkillLoader.SkillMetadata> matched = loader.matchSkills(multimodal, skills);
        assertEquals(1, matched.size());
        assertEquals("test-skill", matched.get(0).name());
    }

    @Test
    void testMatchesWithNullInput() {
        Map<String, List<String>> triggers = new HashMap<>();
        triggers.put("keywords", Arrays.asList("test"));

        ProgressiveSkillLoader.SkillMetadata meta = new ProgressiveSkillLoader.SkillMetadata(
            "test-skill", "Test skill",
            java.nio.file.Path.of("/tmp/test.md"), triggers, "1.0.0"
        );

        assertFalse(meta.matches(null));
        assertFalse(meta.matches(""));
    }

    @Test
    void testMatchesWithEmptyList() {
        Map<String, List<String>> triggers = new HashMap<>();
        triggers.put("keywords", Arrays.asList("test"));

        ProgressiveSkillLoader.SkillMetadata meta = new ProgressiveSkillLoader.SkillMetadata(
            "test-skill", "Test skill",
            java.nio.file.Path.of("/tmp/test.md"), triggers, "1.0.0"
        );

        List<Map<String, Object>> emptyList = new ArrayList<>();
        assertFalse(meta.matches(emptyList));
    }
}
