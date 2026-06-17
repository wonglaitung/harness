plugins {
    `java-library`
}

val jtokkitVersion: String by extra
val junitVersion: String by extra

dependencies {
    api(project(":harness-sdk-core"))

    // Token 计数
    api("com.knuddelsgmbh:jtokkit:$jtokkitVersion")

    // 测试依赖
    testImplementation("org.junit.jupiter:junit-jupiter:$junitVersion")
    testRuntimeOnly("org.junit.platform:junit-platform-launcher")
}

tasks.test {
    useJUnitPlatform()
}