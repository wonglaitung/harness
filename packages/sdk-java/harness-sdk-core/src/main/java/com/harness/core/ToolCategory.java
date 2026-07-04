package com.harness.core;

/**
 * Tool category for classification.
 */
public enum ToolCategory {
    FILE_SYSTEM,    // File system operations (read, write, edit, glob, grep)
    SYSTEM,         // System commands (bash)
    DATABASE,       // Database operations
    NETWORK,        // Network requests (web fetch, browser automation)
    BROWSER,        // Browser automation tools
    MCP,            // MCP tools
    GENERAL,        // General tools
    CUSTOM          // Custom tools
}