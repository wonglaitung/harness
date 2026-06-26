plugins {
    `java-library`
}

val junitVersion: String by extra
val jacksonVersion: String by extra
val slf4jVersion: String by extra

dependencies {
    // Core types
    api(project(":harness-sdk-core"))

    // JSON processing
    api("com.fasterxml.jackson.core:jackson-databind:$jacksonVersion")

    // Logging
    api("org.slf4j:slf4j-api:$slf4jVersion")

    // HTTP client for Judge service
    implementation("com.squareup.okhttp3:okhttp:4.12.0")

    // Testing
    testImplementation("org.junit.jupiter:junit-jupiter:$junitVersion")
    testRuntimeOnly("org.junit.platform:junit-platform-launcher")
}

tasks.test {
    useJUnitPlatform()
}
