package com.harness.core;

import static org.junit.jupiter.api.Assertions.*;

import org.junit.jupiter.api.Test;

/**
 * Tests for ModelPreset.
 */
class ModelPresetTest {

    @Test
    void testCreateWithDefaults() {
        ModelPreset preset = ModelPreset.of("anthropic", 200000, 16384);

        assertEquals("anthropic", preset.provider());
        assertEquals(200000, preset.contextWindow());
        assertEquals(16384, preset.maxTokens());
        assertEquals(0.0, preset.inputPrice());
        assertEquals(0.0, preset.outputPrice());
    }

    @Test
    void testCreateWithPricing() {
        ModelPreset preset = ModelPreset.of("anthropic", 200000, 16384, 3.0, 15.0);

        assertEquals("anthropic", preset.provider());
        assertEquals(200000, preset.contextWindow());
        assertEquals(16384, preset.maxTokens());
        assertEquals(3.0, preset.inputPrice());
        assertEquals(15.0, preset.outputPrice());
    }

    @Test
    void testOpenAIModel() {
        ModelPreset preset = ModelPreset.of("openai", 128000, 16384);

        assertEquals("openai", preset.provider());
        assertEquals(128000, preset.contextWindow());
    }

    @Test
    void testEquality() {
        ModelPreset preset1 = ModelPreset.of("anthropic", 200000, 16384);
        ModelPreset preset2 = ModelPreset.of("anthropic", 200000, 16384);

        assertEquals(preset1, preset2);
    }

    @Test
    void testInequality() {
        ModelPreset preset1 = ModelPreset.of("anthropic", 200000, 16384);
        ModelPreset preset2 = ModelPreset.of("openai", 200000, 16384);

        assertNotEquals(preset1, preset2);
    }
}