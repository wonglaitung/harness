/**
 * 简单测试示例 - 使用真实 LLM API 测试 Java SDK
 */
package com.harness.examples;

import com.harness.core.*;
import com.harness.types.*;
import com.harness.tools.*;
import com.harness.llm.OpenAIClient;

import java.util.*;

public class SimpleTest {

    // API 配置
    private static final String BASE_URL = "https://maas-coding-api.cn-huabei-1.xf-yun.com/v2";
    private static final String API_KEY = "16a9dd623e0d9970b082f7d5ba01475d:YmM2NzI5M2VjOGJjNzNmYjc1N2QzNTA1";
    private static final String MODEL = "xopglm5";

    public static void main(String[] args) {
        System.out.println("=== Harness Java SDK 真实 API 测试 ===\n");

        try {
            test01_BasicConversation();
            test02_WithTools();
        } catch (Exception e) {
            System.err.println("测试失败: " + e.getMessage());
            e.printStackTrace();
        }
    }

    /**
     * 测试 1: 基础对话
     */
    public static void test01_BasicConversation() {
        System.out.println("=== 测试 1: 基础对话 ===");

        // 创建 LLM 客户端
        OpenAIClient llmClient = new OpenAIClient(API_KEY, BASE_URL, MODEL);

        // 创建配置
        HarnessConfig config = HarnessConfig.builder()
            .model(MODEL)
            .maxIterations(1)
            .build();

        // 创建 Agent
        AgentHarness agent = new AgentHarness(llmClient, config);

        // 运行对话
        System.out.println("用户: 你好，请用一句话介绍自己。");
        LoopResult result = agent.run("你好，请用一句话介绍自己。").join();

        System.out.println("Agent: " + result.content());
        System.out.println("状态: " + result.status());
        System.out.println("迭代次数: " + result.iterations());
        System.out.println();
    }

    /**
     * 测试 2: 带工具的对话
     */
    public static void test02_WithTools() {
        System.out.println("=== 测试 2: 带工具的对话 ===");

        // 创建 LLM 客户端
        OpenAIClient llmClient = new OpenAIClient(API_KEY, BASE_URL, MODEL);

        // 创建配置
        HarnessConfig config = HarnessConfig.builder()
            .model(MODEL)
            .maxIterations(5)
            .systemPrompt("你是一个有帮助的 AI 助手。")
            .build();

        // 创建 Agent 并注册工具
        AgentHarness agent = new AgentHarness(
            llmClient,
            config,
            Arrays.asList(new ReadTool(), new GlobTool())
        );

        // 运行对话
        System.out.println("用户: 请列出当前目录下的所有 Java 文件。");
        LoopResult result = agent.run("请列出当前目录下的所有 Java 文件。").join();

        System.out.println("Agent: " + result.content());
        System.out.println("状态: " + result.status());
        System.out.println("迭代次数: " + result.iterations());
        System.out.println();
    }
}
