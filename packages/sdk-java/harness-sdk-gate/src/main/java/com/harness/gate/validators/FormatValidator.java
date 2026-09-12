package com.harness.gate.validators;

import com.harness.gate.GateValidator;
import com.harness.gate.models.FindingType;
import com.harness.gate.models.GateFinding;
import com.harness.gate.models.GateSeverity;

import java.util.List;
import java.util.Map;
import java.util.function.Predicate;

/**
 * Validate structural well-formedness of the delivery.
 *
 * <p>Without an output model it only performs generic structural sanity checks
 * (non-empty, balanced code fences). When {@code outputModel} is a
 * {@link Predicate}, its {@code test(content)} must return true or an ERROR
 * finding is raised.</p>
 */
public class FormatValidator implements GateValidator {

    private final Object outputModel;

    public FormatValidator() {
        this(null);
    }

    public FormatValidator(Object outputModel) {
        this.outputModel = outputModel;
    }

    @Override
    public List<GateFinding> check(
            String content,
            List<String> sources,
            List<Map<String, Object>> toolRecords) {
        List<GateFinding> findings = new java.util.ArrayList<>();
        if (content == null || content.strip().isEmpty()) {
            findings.add(new GateFinding(
                    "fmt:empty", FindingType.FORMAT, GateSeverity.ERROR, "交付内容为空"));
            return findings;
        }

        if (outputModel instanceof Predicate<?> p) {
            @SuppressWarnings("unchecked")
            Predicate<String> pred = (Predicate<String>) p;
            if (!pred.test(content)) {
                findings.add(new GateFinding(
                        "fmt:model", FindingType.FORMAT, GateSeverity.ERROR,
                        "结构与输出模型不符", null, content.length() > 500 ? content.substring(0, 500) : content));
            }
        }

        // Generic structural sanity: unbalanced code fences are a WARNING.
        long fenceCount = content.chars().filter(c -> c == '`').count();
        if (fenceCount % 2 != 0) {
            findings.add(new GateFinding(
                    "fmt:code-fence", FindingType.FORMAT, GateSeverity.WARNING, "代码围栏 ``` 未闭合"));
        }
        return findings;
    }
}
