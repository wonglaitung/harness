pluginManagement {
    repositories {
        gradlePluginPortal()
        mavenCentral()
    }
}

rootProject.name = "harness-sdk-java"

// 多模块项目
include("harness-sdk-core")
include("harness-sdk-llm")
include("harness-sdk-mcp")
include("harness-sdk-tools")
include("harness-sdk-memory")
include("harness-sdk-skills")
include("harness-sdk-security")
include("harness-sdk-guardrails")
include("harness-sdk-integration")
include("harness-sdk-loop")
include("harness-sdk-connectors")
include("harness-sdk-orchestrator")
include("harness-sdk-triggers")
// include("harness-sdk-all")  // Requires shadow plugin
