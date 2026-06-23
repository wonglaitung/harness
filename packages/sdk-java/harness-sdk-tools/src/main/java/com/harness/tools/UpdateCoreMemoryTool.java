package com.harness.tools;

import com.harness.core.Tool;
import com.harness.core.ToolContext;
import com.harness.memory.*;
import com.harness.types.ToolResult;

import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;

/**
 * Tool for Agent to update Core Memory (MEMORY.md).
 *
 * Allows the Agent to persist user preferences, project conventions,
 * and important decisions to long-term memory.
 *
 * This tool should be explicitly added to the tools list (Mem0 pattern).
 */
public class UpdateCoreMemoryTool implements Tool {

    @Override
    public String name() {
        return "update_core_memory";
    }

    @Override
    public String description() {
        return """
            更新用户偏好或项目约定到长期记忆。

            重要规则：
            1. **提炼内容**：不要存储用户原话，要提炼成简洁的陈述
               - 用户说「使用 cmd，不要用 powershell」→ 存储「Shell：使用 cmd（不使用 PowerShell）」
               - 用户说「我使用 Windows」→ 存储「操作系统：Windows」
            2. **避免重复**：添加前先检查是否已有类似记忆，如有则不要重复添加
            3. **适用场景**：用户提到长期偏好、工作环境、项目约束等

            示例：
            - 用户：「我习惯用深色主题」→ category=user_profile, content="主题偏好：深色"
            - 用户：「以后回复简短一点」→ category=learned_patterns, content="回复风格：简洁"
            """;
    }

    @Override
    public Map<String, Object> inputSchema() {
        return Map.of(
            "type", "object",
            "properties", Map.of(
                "category", Map.of(
                    "type", "string",
                    "enum", List.of("user_profile", "key_decisions", "learned_patterns", "project_context"),
                    "description", "记忆类别"
                ),
                "content", Map.of(
                    "type", "string",
                    "description", "记忆内容"
                ),
                "action", Map.of(
                    "type", "string",
                    "enum", List.of("add", "remove"),
                    "description", "操作类型"
                )
            ),
            "required", List.of("category", "content", "action")
        );
    }

    @Override
    public CompletableFuture<ToolResult> execute(Map<String, Object> args, ToolContext context) {
        String categoryStr = (String) args.get("category");
        String content = (String) args.get("content");
        String action = (String) args.get("action");

        MemoryCategory category;
        try {
            category = MemoryCategory.fromValue(categoryStr);
        } catch (Exception e) {
            return CompletableFuture.completedFuture(
                ToolResult.failure("", "Invalid category: " + categoryStr
                    + ". Must be one of: user_profile, key_decisions, learned_patterns, project_context", name())
            );
        }

        MemoryFileManager manager = new MemoryFileManager();

        if ("add".equals(action)) {
            MemoryEntry entry = new MemoryEntry(category, content, MemorySource.USER_INPUT);
            boolean added = manager.addEntry(entry);

            if (added) {
                return CompletableFuture.completedFuture(
                    ToolResult.success("", "已添加到 " + category.getValue() + ": " + content, name(),
                        Map.of("refresh_memory", true))
                );
            } else {
                return CompletableFuture.completedFuture(
                    ToolResult.success("", "跳过重复记忆: 已有类似内容", name())
                );
            }

        } else if ("remove".equals(action)) {
            List<String> entries = manager.getEntries(category);
            for (int i = 0; i < entries.size(); i++) {
                if (entries.get(i).contains(content)) {
                    String removedContent = entries.get(i);
                    manager.removeEntry(category, i);
                    return CompletableFuture.completedFuture(
                        ToolResult.success("", "已从 " + category.getValue() + " 移除: " + removedContent, name(),
                            Map.of("refresh_memory", true))
                    );
                }
            }
            return CompletableFuture.completedFuture(
                ToolResult.failure("", "未找到匹配的记忆: " + content, name())
            );
        }

        return CompletableFuture.completedFuture(
            ToolResult.failure("", "Invalid action: " + action + ". Must be 'add' or 'remove'", name())
        );
    }
}
