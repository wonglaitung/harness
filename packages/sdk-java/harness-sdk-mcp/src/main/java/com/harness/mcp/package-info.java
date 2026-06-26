/**
 * MCP integration module for Harness SDK Java.
 *
 * Provides configuration and management for Model Context Protocol (MCP) servers.
 *
 * Core Components:
 * - {@link McpManager}: Manages configurations for multiple MCP servers
 * - {@link McpServerConfig}: Configuration for MCP server connections
 * - {@link McpToolInfo}: MCP tool metadata
 *
 * Usage:
 * ```java
 * // Create manager
 * McpManager manager = new McpManager();
 *
 * // Register servers (SSE/HTTP transport)
 * manager.registerServer(McpServerConfig.sse("filesystem", "http://localhost:3000/mcp"));
 *
 * // Get registered servers
 * List<String> servers = manager.getRegisteredServers();
 *
 * // Get status
 * Map<String, String> status = manager.getStatus();
 * ```
 *
 * Transport Types:
 * - SSE: HTTP Server-Sent Events (recommended for remote servers)
 * - STDIO: Process-based communication (requires native process management)
 *
 * Note: This module provides configuration management. Actual client connections
 * require Kotlin SDK integration (io.modelcontextprotocol:kotlin-sdk-jvm).
 *
 * @see com.harness.core.Tool
 */
package com.harness.mcp;