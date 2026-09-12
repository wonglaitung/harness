package com.harness.gate;

import static org.junit.jupiter.api.Assertions.*;

import java.util.List;
import java.util.Set;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

/**
 * Tests for FormatValidator (C1).
 */
class FormatValidatorTest {

    private FormatValidator validator;

    @BeforeEach
    void setUp() {
        validator = new FormatValidator();
    }

    @Test
    void emptyContentReturnsError() {
        var findings = validator.validate("");
        assertEquals(1, findings.size());
        assertEquals("fmt:empty", findings.get(0).id());
        assertEquals(GateSeverity.ERROR, findings.get(0).severity());
    }

    @Test
    void nullContentReturnsError() {
        var findings = validator.validate(null);
        assertEquals(1, findings.size());
        assertEquals("fmt:empty", findings.get(0).id());
    }

    @Test
    void unbalancedFencesReturnWarning() {
        var findings = validator.validate("Some text\n```\ncode block\nMore text");
        assertTrue(findings.stream().anyMatch(f -> "fmt:fence-unbalanced".equals(f.id())));
    }

    @Test
    void balancedFencesPass() {
        var findings = validator.validate("Text\n```\ncode\n```\nMore text");
        assertTrue(findings.stream().noneMatch(f -> f.severity() == GateSeverity.ERROR));
    }

    @Test
    void nullBytesReturnError() {
        var findings = validator.validate("Hello\u0000World");
        assertTrue(findings.stream().anyMatch(f -> "fmt:null-byte".equals(f.id())));
    }

    @Test
    void normalContentPasses() {
        var findings = validator.validate("This is normal content with no issues.");
        assertTrue(findings.isEmpty());
    }
}
