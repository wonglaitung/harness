package com.harness.core;

import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

import com.knuddelsgmbh.jtokkit.TokenEncoding;
import com.knuddelsgmbh.jtokkit.TokenEncoder;

class TokenCounterTest {

    @Test
    void testCountTokens() {
        TokenCounter counter = new TokenCounter();

        String text = "Hello, world!";
        int tokens = counter.countTokens(text);

        // cl100k_base: "Hello, world!" should be around 4 tokens
        assertTrue(tokens > 0);
        assertTrue(tokens < 10);
    }

    @Test
    void testCountEmptyString() {
        TokenCounter counter = new TokenCounter();
        assertEquals(0, counter.countTokens(""));
    }

    @Test
    void testCountMessages() {
        TokenCounter counter = new TokenCounter();

        java.util.List<com.harness.types.Message> messages = java.util.List.of(
            com.harness.types.Message.system("You are a helpful assistant."),
            com.harness.types.Message.user("Hello!")
        );

        int tokens = counter.countMessages(messages);
        assertTrue(tokens > 0);
    }

    @Test
    void testEncodingType() {
        TokenCounter counter = new TokenCounter();
        assertEquals(TokenEncoding.CL100K_BASE, counter.getEncoding());
    }

    @Test
    void testTokenEstimation() {
        TokenCounter counter = new TokenCounter();

        // Approximate: 1 token ≈ 4 characters for English
        String longText = "This is a longer text that should have more tokens.";
        int tokens = counter.countTokens(longText);

        // Should be roughly 10-15 tokens for this sentence
        assertTrue(tokens >= 8);
        assertTrue(tokens <= 20);
    }
}