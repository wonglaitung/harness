/**
 * LLM client implementations for Harness SDK Java.
 *
 * Supported providers:
 * - {@link AnthropicClient}: Anthropic Claude API
 * - {@link OpenAIClient}: OpenAI-compatible APIs (including third-party gateways)
 *
 * Usage:
 * <pre>
 * // Anthropic Claude
 * LLMClient client = new AnthropicClient(apiKey, "claude-sonnet-4-6");
 *
 * // OpenAI-compatible (bank gateway)
 * LLMClient client = new OpenAIClient(apiKey, "https://api.bank.com/v1", "model-name");
 * </pre>
 */
package com.harness.llm;
