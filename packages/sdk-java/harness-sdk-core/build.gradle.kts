plugins {
    `java-library`
}

val jtokkitVersion: String by extra
val junitVersion: String by extra
val jacksonVersion: String by extra
val slf4jVersion: String by extra
val caffeineVersion: String by extra

dependencies {
    // Token 计数
    api("com.knuddels:jtokkit:1.0.0")

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