plugins {
    `java-library`
}

val jacksonVersion: String by extra
val slf4jVersion: String by extra
val junitVersion: String by extra

dependencies {
    api(project(":harness-sdk-core"))

    // JSON 处理
    api("com.fasterxml.jackson.core:jackson-databind:$jacksonVersion")
    api("com.fasterxml.jackson.datatype:jackson-datatype-jsr310:$jacksonVersion")

    // Logging
    implementation("org.slf4j:slf4j-api:$slf4jVersion")

    // SQLite 持久化（FileStateStore 运行时按需加载驱动）
    implementation("org.xerial:sqlite-jdbc:3.45.1.0")

    // 测试依赖
    testImplementation("org.junit.jupiter:junit-jupiter:$junitVersion")
    testRuntimeOnly("org.junit.platform:junit-platform-launcher")
}

tasks.test {
    useJUnitPlatform()
}