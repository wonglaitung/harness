plugins {
    `java-library`
}

dependencies {
    api(project(":harness-sdk-core"))

    // Logging
    implementation("org.slf4j:slf4j-api:2.0.0")
}