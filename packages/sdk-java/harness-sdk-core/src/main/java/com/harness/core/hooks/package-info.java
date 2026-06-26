/**
 * Built-in lifecycle hooks for the Harness SDK.
 *
 * This package provides ready-to-use hooks for common scenarios:
 *
 * - {@link com.harness.core.hooks.LoggingHook} - Log all hook events for debugging
 * - {@link com.harness.core.hooks.ConfirmationHook} - Ask user confirmation for dangerous operations
 * - {@link com.harness.core.hooks.AbortOnDangerousToolHook} - Block dangerous tool calls
 * - {@link com.harness.core.hooks.MaxToolCallsHook} - Limit tool calls per session
 *
 * Example usage:
 * <pre>
 * // Add logging for debugging
 * agent.addHook(new LoggingHook());
 *
 * // Block dangerous tools
 * agent.addHook(new AbortOnDangerousToolHook());
 *
 * // Limit bash calls to prevent loops
 * agent.addHook(new MaxToolCallsHook("bash", 10));
 *
 * // Require confirmation for file modifications
 * ConfirmationHook confirmationHook = ConfirmationHook.builder()
 *     .onConfirm((toolName, args) -> showConfirmationDialog(toolName, args))
 *     .isTrusted(key -> trustedCommands.contains(key))
 *     .onTrust(key -> trustedCommands.add(key))
 *     .build();
 * agent.addHook(confirmationHook);
 * </pre>
 *
 * @see com.harness.core.LifecycleHook
 * @see com.harness.core.HookPoint
 */
package com.harness.core.hooks;
