plugins {
    `java-library`
}

val junitVersion: String by extra
val jacksonVersion: String by extra
val slf4jVersion: String by extra

dependencies {
    // 依赖 core 模块
    api(project(":harness-sdk-core"))

    // JSON 处理
    api("com.fasterxml.jackson.core:jackson-databind:$jacksonVersion")

    // 日志
    api("org.slf4j:slf4j-api:$slf4jVersion")

    // JWT for GitHub App authentication
    api("io.jsonwebtoken:jjwt-api:0.12.6")
    runtimeOnly("io.jsonwebtoken:jjwt-impl:0.12.6")
    runtimeOnly("io.jsonwebtoken:jjwt-jackson:0.12.6")

    // 测试依赖
    testImplementation("org.junit.jupiter:junit-jupiter:$junitVersion")
    testRuntimeOnly("org.junit.platform:junit-platform-launcher")
}

tasks.test {
    useJUnitPlatform()
}
