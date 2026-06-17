package com.harness.mcp;

/**
 * MCP integration module for Harness SDK Java.
 *
 * Provides integration with Model Context Protocol (MCP) servers.
 *
 * Core Components:
 * - {@link McpManager}: Manages connections to multiple MCP servers
 * - {@link McpServerConfig}: Configuration for MCP server connections
 * - {@link McpToolWrapper}: Wraps MCP tools as Harness Tools
 * - {@link McpToolInfo}: MCP tool metadata
 *
 * Usage:
 * ```java
 * // Create manager
 * McpManager manager = new McpManager();
 *
 * // Register servers
 * manager.registerServer(McpServerConfig.stdio("filesystem", "npx", "-y", "@modelcontextprotocol/server-filesystem"));
 * manager.registerServer(McpServerConfig.sse("custom", "http://localhost:8080/mcp"));
 *
 * // Connect
 * manager.connectAll();
 *
 * // Get tools
 * List<McpToolWrapper> tools = manager.getAllTools();
 *
 * // Disconnect
 * manager.disconnectAll();
 * ```
 *
 * Transport Types:
 * - STDIO: Process-based communication (npm packages)
 * - SSE: HTTP Server-Sent Events (remote servers)
 *
 * @see com.harness.core.Tool
 */
package com.harness.mcp;