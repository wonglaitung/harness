plugins {
    `java-library`
}

val jtokkitVersion: String by extra

dependencies {
    api(project(":harness-sdk-core"))

    // Token 计数
    api("com.knuddelsgmbh:jtokkit:$jtokkitVersion")
}
