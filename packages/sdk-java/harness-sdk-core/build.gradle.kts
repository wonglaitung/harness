plugins {
    `java-library`
}

val jacksonVersion: String by extra
val slf4jVersion: String by extra
val junitVersion: String by extra
val mockitoVersion: String by extra
val caffeineVersion: String by extra

dependencies {
    // JSON 处理
    api("com.fasterxml.jackson.core:jackson-databind:$jacksonVersion")
    api("com.fasterxml.jackson.datatype:jackson-datatype-jsr310:$jacksonVersion")

    // 日志接口
    api("org.slf4j:slf4j-api:$slf4jVersion")

    // 缓存
    api("com.github.ben-manes.caffeine:caffeine:$caffeineVersion")

    // 测试依赖
    testImplementation("org.junit.jupiter:junit-jupiter:$junitVersion")
    testImplementation("org.mockito:mockito-core:$mockitoVersion")
    testImplementation("org.mockito:mockito-junit-jupiter:$mockitoVersion")
    testRuntimeOnly("org.junit.platform:junit-platform-launcher")
}
