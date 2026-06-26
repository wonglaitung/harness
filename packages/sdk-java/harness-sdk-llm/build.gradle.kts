plugins {
    `java-library`
}

val anthropicVersion: String by extra
val openaiVersion: String by extra
val junitVersion: String by extra

dependencies {
    api(project(":harness-sdk-core"))

    // Anthropic Java SDK (官方)
    api("com.anthropic:anthropic-java:$anthropicVersion")

    // OpenAI Java SDK (官方，支持第三方 API)
    api("com.openai:openai-java:$openaiVersion")

    // Test dependencies
    testImplementation("org.junit.jupiter:junit-jupiter-api:$junitVersion")
    testRuntimeOnly("org.junit.jupiter:junit-jupiter-engine:$junitVersion")
}
