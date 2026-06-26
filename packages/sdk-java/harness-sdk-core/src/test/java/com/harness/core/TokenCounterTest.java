package com.harness.core;

import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

import java.util.List;

import com.harness.types.Message;

class TokenCounterTest {

    @Test
    void testCountTokens() {
        TokenCounter counter = new TokenCounter();

        String text = "Hello, world!";
        int tokens = counter.count(text);

        // cl100k_base: "Hello, world!" should be around 4 tokens
        assertTrue(tokens > 0);
        assertTrue(tokens < 10);
    }

    @Test
    void testCountEmptyString() {
        TokenCounter counter = new TokenCounter();
        assertEquals(0, counter.count(""));
    }

    @Test
    void testCountNullString() {
        TokenCounter counter = new TokenCounter();
        assertEquals(0, counter.count(null));
    }

    @Test
    void testCountMessages() {
        TokenCounter counter = new TokenCounter();

        List<Message> messages = List.of(
            Message.system("You are a helpful assistant."),
            Message.user("Hello!")
        );

        int tokens = counter.countMessages(messages);
        assertTrue(tokens > 0);
    }

    @Test
    void testTokenEstimation() {
        TokenCounter counter = new TokenCounter();

        // Approximate: 1 token ≈ 4 characters for English
        String longText = "This is a longer text that should have more tokens.";
        int tokens = counter.count(longText);

        // Should be roughly 10-15 tokens for this sentence
        assertTrue(tokens >= 8);
        assertTrue(tokens <= 20);
    }

    @Test
    void testCountAll() {
        TokenCounter counter = new TokenCounter();

        List<String> texts = List.of("Hello", "World", "Test");
        int tokens = counter.countAll(texts);

        assertTrue(tokens > 0);
    }

    @Test
    void testCache() {
        TokenCounter counter = new TokenCounter();

        String text = "Cached text";
        int tokens1 = counter.count(text);
        int tokens2 = counter.count(text);

        assertEquals(tokens1, tokens2);

        counter.clearCache();
        int tokens3 = counter.count(text);
        assertEquals(tokens1, tokens3);
    }
}
