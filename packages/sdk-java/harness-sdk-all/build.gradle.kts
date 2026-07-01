plugins {
    `java-library`
    id("com.gradleup.shadow") version "8.3.5"
}

val junitVersion: String by extra

dependencies {
    // Integration module includes all other modules
    api(project(":harness-sdk-integration"))

    // 测试
    testImplementation("org.junit.jupiter:junit-jupiter:$junitVersion")
}

tasks.shadowJar {
    archiveClassifier.set("")
    mergeServiceFiles()

    // 排除签名文件
    exclude("META-INF/*.SF")
    exclude("META-INF/*.DSA")
    exclude("META-INF/*.RSA")

    // 最小化依赖
    minimize()
}

tasks.build {
    dependsOn(tasks.shadowJar)
}

tasks.jar {
    archiveClassifier.set("thin")
}

publishing {
    publications {
        create<MavenPublication>("shadow") {
            project.shadow.component(this)
        }
    }
}
