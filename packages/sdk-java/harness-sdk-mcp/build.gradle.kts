plugins {
    `java-library`
}

val mcpVersion: String by extra

dependencies {
    api(project(":harness-sdk-core"))

    // MCP Java SDK (官方)
    api("io.modelcontextprotocol:mcp-java-sdk:$mcpVersion")

    // Logging
    implementation("org.slf4j:slf4j-api:2.0.0")
}