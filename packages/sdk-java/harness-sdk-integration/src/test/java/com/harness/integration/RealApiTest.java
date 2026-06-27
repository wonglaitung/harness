package com.harness.integration;

import com.harness.core.*;
import com.harness.types.*;
import com.harness.tools.*;
import com.harness.llm.OpenAIClient;

import org.junit.jupiter.api.*;
import static org.junit.jupiter.api.Assertions.*;

import java.util.*;

/**
 * 真实 API 测试
 */
@TestMethodOrder(MethodOrderer.OrderAnnotation.class)
public class RealApiTest {

    // API 配置
    private static final String BASE_URL = "https://maas-coding-api.cn-huabei-1.xf-yun.com/v2";
    private static final String API_KEY = "16a9dd623e0d9970b082f7d5ba01475d:YmM2NzI5M2VjOGJjNzNmYjc1N2QzNTA1";
    private static final String MODEL = "xopglm5";

    @Test
    @Order(1)
    void testBasicConversation() {
        System.out.println("\n=== 测试 1: 基础对话 ===");

        OpenAIClient llmClient = new OpenAIClient(API_KEY, BASE_URL, MODEL);
        HarnessConfig config = HarnessConfig.builder()
            .model(MODEL)
            .maxIterations(1)
            .build();

        AgentHarness agent = new AgentHarness(llmClient, config);

        System.out.println("用户: 你好，请用一句话介绍自己。");
        LoopResult result = agent.run("你好，请用一句话介绍自己。").join();

        System.out.println("Agent: " + result.content());
        System.out.println("状态: " + result.status());
        System.out.println("迭代次数: " + result.iterations());

        assertNotNull(result.content());
        assertTrue(result.content().length() > 0);
    }

    @Test
    @Order(2)
    void testWithTools() {
        System.out.println("\n=== 测试 2: 带工具的对话 ===");

        OpenAIClient llmClient = new OpenAIClient(API_KEY, BASE_URL, MODEL);
        HarnessConfig config = HarnessConfig.builder()
            .model(MODEL)
            .maxIterations(5)
            .systemPrompt("你是一个有帮助的 AI 助手。")
            .build();

        AgentHarness agent = new AgentHarness(
            llmClient,
            config,
            Arrays.asList(new ReadTool(), new GlobTool())
        );

        System.out.println("用户: 请列出当前目录下的所有 Java 文件。");
        LoopResult result = agent.run("请列出当前目录下的所有 Java 文件。").join();

        System.out.println("Agent: " + result.content());
        System.out.println("状态: " + result.status());
        System.out.println("迭代次数: " + result.iterations());

        assertNotNull(result.content());
    }

    @Test
    @Order(3)
    void testMultiTurn() {
        System.out.println("\n=== 测试 3: 多轮对话 ===");

        OpenAIClient llmClient = new OpenAIClient(API_KEY, BASE_URL, MODEL);
        HarnessConfig config = HarnessConfig.builder()
            .model(MODEL)
            .maxIterations(1)
            .build();

        AgentHarness agent = new AgentHarness(llmClient, config);
        String sessionId = "test-session-001";

        System.out.println("[Session: " + sessionId + "] 用户: 我的名字叫小明。");
        LoopResult result1 = agent.run("我的名字叫小明。", sessionId).join();
        System.out.println("Agent: " + result1.content());

        System.out.println("[Session: " + sessionId + "] 用户: 你还记得我叫什么名字吗？");
        LoopResult result2 = agent.run("你还记得我叫什么名字吗？", sessionId).join();
        System.out.println("Agent: " + result2.content());

        assertNotNull(result2.content());
    }
}
