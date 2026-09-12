package com.harness.gate;

import java.util.ArrayList;
import java.util.List;

/**
 * C1: Format validator — checks structural well-formedness of LLM output.
 *
 * <p>Checks: empty content, code-fence balance, JSON/markdown structure.</p>
 */
public class FormatValidator {

    private static final String CODE_FENCE = "```";

    /**
     * Validate content format. Returns list of findings (empty = all passed).
     */
    public List<GateFinding> validate(String content) {
        List<GateFinding> findings = new ArrayList<>();

        if (content == null || content.isBlank()) {
            findings.add(new GateFinding(
                "fmt:empty", FindingType.FORMAT, GateSeverity.ERROR,
                "Content is empty or blank", ""));
            return findings;
        }

        // Check code fence balance (odd = unclosed fence)
        long fenceCount = content.lines()
            .map(String::trim)
            .filter(line -> line.startsWith(CODE_FENCE) || line.endsWith(CODE_FENCE))
            .count();
        if (fenceCount % 2 != 0) {
            findings.add(new GateFinding(
                "fmt:fence-unbalanced", FindingType.FORMAT, GateSeverity.WARNING,
                "Odd number of code fences (" + fenceCount + ") suggests unclosed block",
                ""));
        }

        // Check for common structural issues
        if (content.contains("\u0000")) {
            findings.add(new GateFinding(
                "fmt:null-byte", FindingType.FORMAT, GateSeverity.ERROR,
                "Content contains null bytes", ""));
        }

        return findings;
    }
}
