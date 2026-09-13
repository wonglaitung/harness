plugins {
    `java-library`
}

val junitVersion: String by extra

dependencies {
    api(project(":harness-sdk-core"))

    // Logging
    implementation("org.slf4j:slf4j-api:2.0.0")

    // JSON parsing
    implementation("com.fasterxml.jackson.core:jackson-databind:2.17.0")

    // Testing
    testImplementation("org.junit.jupiter:junit-jupiter:$junitVersion")
    testRuntimeOnly("org.junit.platform:junit-platform-launcher")
}

tasks.test {
    useJUnitPlatform()
}