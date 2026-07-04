plugins {
    `java-library`
}

val jacksonVersion: String by extra
val slf4jVersion: String by extra
val junitVersion: String by extra

dependencies {
    api(project(":harness-sdk-core"))
    api(project(":harness-sdk-memory"))

    // JSON 处理
    api("com.fasterxml.jackson.core:jackson-databind:$jacksonVersion")
    api("com.fasterxml.jackson.datatype:jackson-datatype-jsr310:$jacksonVersion")

    // 日志接口
    api("org.slf4j:slf4j-api:$slf4jVersion")

    // Playwright for browser automation (optional)
    // Users need to add this dependency explicitly when using browser tools
    compileOnly("com.microsoft.playwright:playwright:1.40.0")

    // 测试依赖
    testImplementation("org.junit.jupiter:junit-jupiter:$junitVersion")
    testRuntimeOnly("org.junit.platform:junit-platform-launcher")
    testImplementation("com.microsoft.playwright:playwright:1.40.0")
}

tasks.test {
    useJUnitPlatform()
}