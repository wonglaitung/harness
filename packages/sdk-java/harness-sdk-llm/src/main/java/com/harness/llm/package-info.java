/**
 * LLM client implementations for Harness SDK Java.
 *
 * Supported providers:
 * - {@link OpenAIClient}: OpenAI-compatible APIs (推荐，支持任意第三方提供者)
 * - {@link AnthropicClient}: Anthropic Claude API (备用)
 *
 * Usage:
 * <pre>
 * // OpenAI 兼容的第三方提供者（推荐）
 * LLMClient client = new OpenAIClient(apiKey, "https://api.your-provider.com/v1", "gpt-4o");
 *
 * // Anthropic Claude
 * LLMClient client = new AnthropicClient(apiKey, "claude-sonnet-4-6");
 * </pre>
 */
package com.harness.llm;
