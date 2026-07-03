package com.harness.skills;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.function.Predicate;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Skill injector for system prompts.
 *
 * Injects relevant skills into the system prompt based on:
 * - User input matching
 * - Currently active skills
 *
 * Example:
 * <pre>
 * SkillRegistry registry = new SkillRegistry();
 * SkillInjector injector = new SkillInjector(registry);
 * String enhancedPrompt = injector.injectSkills(systemPrompt, userInput);
 * </pre>
 */
public class SkillInjector {

    private static final Logger logger = LoggerFactory.getLogger(SkillInjector.class);

    private final SkillRegistry registry;
    private final InjectionConfig config;

    public SkillInjector(SkillRegistry registry) {
        this(registry, InjectionConfig.defaults());
    }

    public SkillInjector(SkillRegistry registry, InjectionConfig config) {
        this.registry = registry;
        this.config = config;
    }

    /**
     * Inject skills into system prompt.
     *
     * @param systemPrompt Original system prompt
     * @param userInput    User's input text
     * @return System prompt with skills injected
     */
    public String injectSkills(String systemPrompt, String userInput) {
        return injectSkills(systemPrompt, userInput, null);
    }

    /**
     * Inject skills into system prompt.
     *
     * @param systemPrompt Original system prompt
     * @param userInput    User's input text
     * @param context      Optional context dictionary
     * @return System prompt with skills injected
     */
    public String injectSkills(String systemPrompt, String userInput, java.util.Map<String, Object> context) {
        // Find matching skills
        List<Skill> matchingSkills = registry.findMatchingSkills(userInput);

        // Get active skills
        List<Skill> activeSkills = registry.getActiveSkills();

        // Merge and deduplicate
        Set<String> seen = new HashSet<>();
        List<Skill> allSkills = new ArrayList<>();
        for (Skill s : matchingSkills) {
            if (seen.add(s.name())) {
                allSkills.add(s);
            }
        }
        for (Skill s : activeSkills) {
            if (seen.add(s.name())) {
                allSkills.add(s);
            }
        }

        // Limit number of skills
        if (allSkills.size() > config.maxSkillsPerPrompt()) {
            allSkills = allSkills.subList(0, config.maxSkillsPerPrompt());
        }

        if (allSkills.isEmpty()) {
            logger.debug("No skills matched for input: {}", userInput.substring(0, Math.min(50, userInput.length())));
            return systemPrompt;
        }

        logger.info("Injecting {} skills: {}", allSkills.size(),
            allSkills.stream().map(Skill::name).toList());

        // Build skill prompts
        List<String> skillPrompts = new ArrayList<>();
        for (Skill skill : allSkills) {
            String skillPrompt = formatSkill(skill);

            // Check length and log warning if too long (but don't truncate)
            int skillLen = skillPrompt.length();
            if (config.warnSkillLength() > 0 && skillLen > config.warnSkillLength()) {
                logger.warn(
                    "Skill '{}' is {} chars (>{}). Consider shortening for better LLM performance.",
                    skill.name(), skillLen, config.warnSkillLength()
                );
            }

            // Only truncate if maxSkillLength is explicitly set (> 0)
            if (config.maxSkillLength() > 0 && skillLen > config.maxSkillLength()) {
                skillPrompt = skillPrompt.substring(0, config.maxSkillLength()) + "\n...[truncated]";
                logger.warn(
                    "Skill '{}' truncated from {} to {} chars",
                    skill.name(), skillLen, config.maxSkillLength()
                );
            }

            skillPrompts.add(skillPrompt);
        }

        String combinedSkills = String.join(config.skillSeparator(), skillPrompts);

        // Inject based on method
        return switch (config.injectMethod()) {
            case "prepend" -> combinedSkills + config.skillSeparator() + systemPrompt;
            case "section" -> systemPrompt + "\n\n# Active Skills\n\n" + combinedSkills;
            default -> systemPrompt + config.skillSeparator() + combinedSkills; // append
        };
    }

    /**
     * Format a skill for injection.
     */
    private String formatSkill(Skill skill) {
        StringBuilder sb = new StringBuilder();
        sb.append("## Skill: ").append(skill.name()).append("\n\n");
        sb.append(skill.description()).append("\n");

        if (skill.metadata() != null && skill.metadata().tools() != null && !skill.metadata().tools().isEmpty()) {
            sb.append("\n### Available Tools\n");
            sb.append(String.join(", ", skill.metadata().tools()));
        }

        sb.append("\n\n").append(skill.content());
        return sb.toString();
    }

    /**
     * Get a tool filter function.
     *
     * @return Predicate that returns true if a tool is allowed
     */
    public Predicate<String> getToolFilter() {
        return toolName -> registry.isToolAllowed(toolName);
    }

    /**
     * Get preview of what would be injected.
     *
     * @param systemPrompt Original system prompt
     * @param userInput    User's input text
     * @return Dictionary with injection details
     */
    public InjectionPreview getInjectionPreview(String systemPrompt, String userInput) {
        List<Skill> matching = registry.findMatchingSkills(userInput);
        List<Skill> active = registry.getActiveSkills();

        Set<String> seen = new HashSet<>();
        List<Skill> allSkills = new ArrayList<>();
        for (Skill s : matching) {
            if (seen.add(s.name())) {
                allSkills.add(s);
            }
        }
        for (Skill s : active) {
            if (seen.add(s.name())) {
                allSkills.add(s);
            }
        }

        int totalToInject = Math.min(allSkills.size(), config.maxSkillsPerPrompt());
        String injected = injectSkills(systemPrompt, userInput);

        return new InjectionPreview(
            matching.stream().map(Skill::name).toList(),
            active.stream().map(Skill::name).toList(),
            totalToInject,
            allSkills.stream().limit(totalToInject).map(Skill::name).toList(),
            systemPrompt.length(),
            injected.length()
        );
    }

    /**
     * Preview of skill injection.
     */
    public record InjectionPreview(
        List<String> matchingSkills,
        List<String> activeSkills,
        int totalToInject,
        List<String> skillNames,
        int originalPromptLength,
        int estimatedInjectedLength
    ) {}
}
