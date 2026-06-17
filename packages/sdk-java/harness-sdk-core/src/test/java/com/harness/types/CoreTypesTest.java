package com.harness.types;

import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class TokenUsageTest {

    @Test
    void testTokenUsageCreation() {
        TokenUsage usage = new TokenUsage(100, 50);
        assertEquals(100, usage.inputTokens());
        assertEquals(50, usage.outputTokens());
        assertEquals(150, usage.totalTokens());
    }

    @Test
    void testTokenUsageAdd() {
        TokenUsage a = new TokenUsage(100, 50);
        TokenUsage b = new TokenUsage(200, 100);
        TokenUsage c = a.add(b);
        assertEquals(300, c.inputTokens());
        assertEquals(150, c.outputTokens());
    }

    @Test
    void testTokenUsageBuilder() {
        TokenUsage usage = TokenUsage.builder()
            .inputTokens(100)
            .outputTokens(50)
            .build();
        assertEquals(100, usage.inputTokens());
        assertEquals(50, usage.outputTokens());
    }
}

class MessageTest {

    @Test
    void testMessageCreation() {
        Message msg = new Message("user", "Hello");
        assertEquals("user", msg.role());
        assertEquals("Hello", msg.contentAsString());
    }

    @Test
    void testStaticFactories() {
        Message system = Message.system("System prompt");
        assertEquals("system", system.role());

        Message user = Message.user("User message");
        assertEquals("user", user.role());

        Message assistant = Message.assistant("Assistant message");
        assertEquals("assistant", assistant.role());
    }

    @Test
    void testInvalidRole() {
        assertThrows(IllegalArgumentException.class, () -> {
            new Message("invalid", "content");
        });
    }
}

class SessionTest {

    @Test
    void testSessionCreation() {
        Session session = Session.create();
        assertNotNull(session.id());
        assertTrue(session.messages().isEmpty());
    }

    @Test
    void testSessionAddMessage() {
        Session session = Session.create();
        session = session.addMessage(Message.user("Hello"));
        assertEquals(1, session.messages().size());
        assertEquals("Hello", session.messages().get(0).contentAsString());
    }
}

class LoopResultTest {

    @Test
    void testCompletedResult() {
        Session session = Session.create();
        TokenUsage usage = new TokenUsage(100, 50);
        LoopResult result = LoopResult.completed(session, "Done", 2, usage);
        assertTrue(result.isSuccess());
        assertEquals("Done", result.content());
        assertEquals(2, result.iterations());
    }

    @Test
    void testErrorResult() {
        Session session = Session.create();
        LoopResult result = LoopResult.error(session, 1, "Something went wrong");
        assertTrue(result.hasError());
        assertEquals("Something went wrong", result.error());
    }
}
