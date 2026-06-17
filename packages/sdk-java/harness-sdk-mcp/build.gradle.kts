plugins {
    `java-library`
}

val mcpVersion: String by extra

dependencies {
    api(project(":harness-sdk-core"))

    // MCP Java SDK (官方)
    api("io.modelcontextprotocol:mcp-java-sdk:$mcpVersion")
}
