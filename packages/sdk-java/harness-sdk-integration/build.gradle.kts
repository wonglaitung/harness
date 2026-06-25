plugins {
    `java-library`
}

val junitVersion: String by extra
val jacksonVersion: String by extra
val slf4jVersion: String by extra
val caffeineVersion: String by extra

dependencies {
    // 核心类型
    api(project(":harness-sdk-core"))

    // LLM 客户端
    api(project(":harness-sdk-llm"))

    // 记忆系统
    api(project(":harness-sdk-memory"))

    // 技能系统
    api(project(":harness-sdk-skills"))

    // MCP 协议
    api(project(":harness-sdk-mcp"))

    // 工具
    api(project(":harness-sdk-tools"))

    // 安全
    api(project(":harness-sdk-security"))

    // JSON 处理
    api("com.fasterxml.jackson.core:jackson-databind:$jacksonVersion")

    // 日志
    api("org.slf4j:slf4j-api:$slf4jVersion")

    // 缓存
    api("com.github.ben-manes.caffeine:caffeine:$caffeineVersion")

    // 测试依赖
    testImplementation("org.junit.jupiter:junit-jupiter:$junitVersion")
    testRuntimeOnly("org.junit.platform:junit-platform-launcher")
}

tasks.test {
    useJUnitPlatform()
}