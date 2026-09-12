package com.harness.gate;

import static org.junit.jupiter.api.Assertions.*;

import java.util.List;
import java.util.Set;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

/**
 * Tests for FactGrounder (C2).
 */
class FactGrounderTest {

    private FactGrounder grounder;

    @BeforeEach
    void setUp() {
        grounder = new FactGrounder();
    }

    @Test
    void claimWithNoSourceEmitsFinding() {
        String content = "The total revenue is $1,234,567 for this quarter.";
        var findings = grounder.ground(content, Set.of(), List.of());
        assertTrue(findings.stream().anyMatch(f -> "fact:no-source".equals(f.id())));
    }

    @Test
    void claimWithMarkdownLinkPasses() {
        String content = "The total revenue is $1,234,567 [source: Q4 report](http://example.com).";
        var findings = grounder.ground(content, Set.of(), List.of());
        assertTrue(findings.isEmpty() || findings.stream().noneMatch(f ->
            "fact:no-source".equals(f.id()) && f.severity() == GateSeverity.ERROR));
    }

    @Test
    void claimWithToolRecordPasses() {
        String content = "The total revenue is $1,234,567 according to the database.";
        var findings = grounder.ground(content, Set.of(), List.of("database"));
        assertTrue(findings.stream().noneMatch(f -> "fact:no-source".equals(f.id())));
    }

    @Test
    void noClaimContentPasses() {
        String content = "# Heading\n\nSome paragraph text without any factual claims.";
        var findings = grounder.ground(content, Set.of(), List.of());
        assertTrue(findings.isEmpty());
    }
}
