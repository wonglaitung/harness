plugins {
    `java-library`
}

val junitVersion: String by extra
val jacksonVersion: String by extra
val slf4jVersion: String by extra

dependencies {
    // 日志
    api("org.slf4j:slf4j-api:$slf4jVersion")

    // JSON 处理（load_rule_specs 解析）
    api("com.fasterxml.jackson.core:jackson-databind:$jacksonVersion")

    // 测试依赖
    testImplementation("org.junit.jupiter:junit-jupiter:$junitVersion")
    testRuntimeOnly("org.junit.platform:junit-platform-launcher")
}

tasks.test {
    useJUnitPlatform()
}
