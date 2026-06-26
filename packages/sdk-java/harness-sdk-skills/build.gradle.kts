plugins {
    `java-library`
}

val junitVersion: String by extra

dependencies {
    api(project(":harness-sdk-core"))
    api(project(":harness-sdk-memory"))

    // Test dependencies
    testImplementation("org.junit.jupiter:junit-jupiter-api:$junitVersion")
    testRuntimeOnly("org.junit.jupiter:junit-jupiter-engine:$junitVersion")
}
