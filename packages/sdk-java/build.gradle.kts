plugins {
    kotlin("jvm") version "1.9.24" apply false
}

group = "com.harness"
version = "1.0.0-SNAPSHOT"

subprojects {
    apply(plugin = "java-library")
    apply(plugin = "maven-publish")

    repositories {
        mavenCentral()
    }

    configure<JavaPluginExtension> {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    tasks.withType<JavaCompile> {
        options.encoding = "UTF-8"
    }

    tasks.withType<Test> {
        useJUnitPlatform()
    }

    // 依赖版本管理
    extra["anthropicVersion"] = "2.40.1"
    extra["openaiVersion"] = "4.39.1"
    extra["mcpVersion"] = "0.13.0"  // kotlin-sdk-jvm version
    extra["jtokkitVersion"] = "1.0.0"
    extra["jacksonVersion"] = "2.17.0"
    extra["slf4jVersion"] = "2.0.0"
    extra["junitVersion"] = "5.10.2"
    extra["mockitoVersion"] = "5.12.0"
    extra["caffeineVersion"] = "3.1.8"
}

// 根项目任务
tasks.register("buildAll") {
    dependsOn(subprojects.map { it.tasks.named("build") })
    group = "build"
    description = "Build all modules"
}
