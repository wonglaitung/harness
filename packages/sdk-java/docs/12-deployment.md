# 12 - JAR 包部署指南

## 概述

本文档详细说明如何构建、交付和部署 Harness SDK Java 版本的 JAR 包。

## 构建方式

### 开发环境构建

```bash
# 克隆仓库
git clone https://github.com/wonglaitung/harness.git
cd harness/packages/sdk-java

# 构建所有模块
./gradlew build

# 构建聚合 JAR (Shadow JAR)
./gradlew :harness-sdk-all:shadowJar

# 输出位置
# harness-sdk-all/build/libs/harness-sdk-all-1.0.0.jar
```

### 生产环境构建

```bash
# 完整构建（包含测试）
./gradlew clean build shadowJar

# 跳过测试（更快）
./gradlew build shadowJar -x test

# 构建并生成校验和
./gradlew shadowJar && sha256sum harness-sdk-all/build/libs/*.jar > checksums.sha256
```

## JAR 包类型

### 1. Shadow JAR (All-in-One)

**文件名**: `harness-sdk-all-1.0.0.jar`

**包含内容**:
- 所有模块代码
- 所有依赖库
- 配置文件

**大小**: ~15 MB

**适用场景**: 
- 银行离线环境
- 快速集成
- 无需管理依赖

**使用方式**:
```kotlin
// Gradle
implementation(files("libs/harness-sdk-all-1.0.0.jar"))
```

### 2. 模块化 JAR

**文件结构**:
```
libs/
├── harness-sdk-core-1.0.0.jar       # 核心 (~500 KB)
├── harness-sdk-anthropic-1.0.0.jar  # Anthropic 集成
├── harness-sdk-mcp-1.0.0.jar        # MCP 集成
├── harness-sdk-tools-1.0.0.jar      # 内置工具
├── harness-sdk-memory-1.0.0.jar     # 记忆系统
└── harness-sdk-skills-1.0.0.jar     # 技能系统
```

**适用场景**:
- 已有部分依赖的项目
- 需要精细化控制依赖
- 减少重复依赖

**使用方式**:
```kotlin
// Gradle
implementation(files("libs/harness-sdk-core-1.0.0.jar"))
implementation(files("libs/harness-sdk-anthropic-1.0.0.jar"))
// ... 根据需要引入其他模块
```

## Gradle 配置详解

### Shadow JAR 插件配置

```kotlin
// harness-sdk-all/build.gradle.kts

plugins {
    id("java-library")
    id("com.github.johnrengelman.shadow") version "8.1.1"
}

dependencies {
    // 引入所有模块
    implementation(project(":harness-sdk-core"))
    implementation(project(":harness-sdk-anthropic"))
    implementation(project(":harness-sdk-mcp"))
    implementation(project(":harness-sdk-tools"))
    implementation(project(":harness-sdk-memory"))
    implementation(project(":harness-sdk-skills"))
}

tasks.shadowJar {
    // 不添加 classifier，直接使用主版本号
    archiveClassifier.set("")
    
    // 合并服务文件
    mergeServiceFiles()
    
    // 排除签名文件（避免冲突）
    exclude("META-INF/*.SF")
    exclude("META-INF/*.DSA")
    exclude("META-INF/*.RSA")
    
    // 排除不需要的模块
    exclude("META-INF/DEPENDENCIES")
    exclude("META-INF/LICENSE*")
    exclude("META-INF/NOTICE*")
    
    // 最小化依赖
    minimize()
}

// 构建后自动生成校验和
tasks.register("generateChecksum") {
    dependsOn(tasks.shadowJar)
    
    doLast {
        val jarFile = tasks.shadowJar.get().archiveFile.get().asFile
        val checksumFile = File(jarFile.parentFile, "${jarFile.name}.sha256")
        
        checksumFile.writeText(
            java.security.MessageDigest.getInstance("SHA-256")
                .digest(jarFile.readBytes())
                .joinToString("") { "%02x".format(it) }
        )
    }
}
```

## 项目集成方式

### 方式一：直接引入 JAR 文件

**Gradle (Kotlin DSL)**:
```kotlin
// build.gradle.kts

dependencies {
    // 单个 JAR 文件
    implementation(files("libs/harness-sdk-all-1.0.0.jar"))
    
    // 或使用目录
    implementation(fileTree("libs") { include("*.jar") })
}
```

**Gradle (Groovy DSL)**:
```groovy
// build.gradle

dependencies {
    implementation files("libs/harness-sdk-all-1.0.0.jar")
    
    // 或使用目录
    implementation fileTree(dir: "libs", include: "*.jar")
}
```

**Maven**:
```xml
<!-- pom.xml -->

<dependencies>
    <dependency>
        <groupId>com.harness</groupId>
        <artifactId>harness-sdk</artifactId>
        <version>1.0.0</version>
        <scope>system</scope>
        <systemPath>${project.basedir}/libs/harness-sdk-all-1.0.0.jar</systemPath>
    </dependency>
</dependencies>
```

### 方式二：本地 Maven 仓库

```bash
# 安装到本地 Maven 仓库
./gradlew publishToMavenLocal
```

**Gradle 使用**:
```kotlin
repositories {
    mavenLocal()
}

dependencies {
    implementation("com.harness:harness-sdk-all:1.0.0")
}
```

**Maven 使用**:
```xml
<repositories>
    <repository>
        <id>local-maven-repo</id>
        <url>file://${user.home}/.m2/repository</url>
    </repository>
</repositories>

<dependencies>
    <dependency>
        <groupId>com.harness</groupId>
        <artifactId>harness-sdk-all</artifactId>
        <version>1.0.0</version>
    </dependency>
</dependencies>
```

## 交付包结构

### 标准交付包

```
harness-sdk-java-1.0.0.zip
├── jars/
│   ├── harness-sdk-all-1.0.0.jar      # 聚合 JAR（推荐使用）
│   ├── harness-sdk-core-1.0.0.jar     # 核心模块
│   ├── harness-sdk-anthropic-1.0.0.jar
│   ├── harness-sdk-mcp-1.0.0.jar
│   ├── harness-sdk-tools-1.0.0.jar
│   ├── harness-sdk-memory-1.0.0.jar
│   └── harness-sdk-skills-1.0.0.jar
├── docs/
│   ├── README.md                       # 快速入门
│   ├── API-reference.md                # API 参考
│   ├── integration-guide.md            # 集成指南
│   └── examples/                       # 示例代码
│       ├── simple-agent/
│       └── mcp-integration/
├── lib/                                # 第三方依赖（可选）
│   └── (如果需要单独引入)
├── reports/
│   ├── dependency-check-report.html    # OWASP 依赖扫描
│   └── sbom.json                       # SBOM
├── metadata.json                       # 版本信息
├── checksums.sha256                    # SHA256 校验和
└── LICENSE                             # MIT 许可证
```

### metadata.json 内容

```json
{
  "name": "harness-sdk-java",
  "version": "1.0.0",
  "buildDate": "2026-06-17",
  "javaVersion": "17",
  "gradleVersion": "8.5",
  "modules": [
    "harness-sdk-core",
    "harness-sdk-anthropic",
    "harness-sdk-mcp",
    "harness-sdk-tools",
    "harness-sdk-memory",
    "harness-sdk-skills"
  ],
  "dependencies": [
    {
      "name": "anthropic-java",
      "version": "2.40.1",
      "license": "MIT"
    },
    {
      "name": "mcp-java-sdk",
      "version": "0.5.0",
      "license": "MIT"
    },
    {
      "name": "jtokkit",
      "version": "1.0.0",
      "license": "MIT"
    },
    {
      "name": "jackson-databind",
      "version": "2.17.0",
      "license": "Apache-2.0"
    },
    {
      "name": "okhttp",
      "version": "4.12.0",
      "license": "Apache-2.0"
    }
  ],
  "checksums": {
    "harness-sdk-all-1.0.0.jar": "sha256:abc123..."
  }
}
```

## 安全与合规

### 1. 依赖扫描

```bash
# OWASP 依赖检查
./gradlew dependencyCheckAnalyze

# 输出报告
# build/reports/dependency-check-report.html
```

### 2. SBOM 生成

```kotlin
// build.gradle.kts

plugins {
    id("org.cyclonedx.bom") version "1.8.2"
}

cyclonedxBom {
    includeConfigs.set(listOf("runtimeClasspath"))
}
```

```bash
# 生成 SBOM
./gradlew cyclonedxBom

# 输出
# build/reports/bom.json
```

### 3. 签名验证（可选）

```bash
# 生成 GPG 签名
gpg --armor --detach-sign harness-sdk-all-1.0.0.jar

# 验证签名
gpg --verify harness-sdk-all-1.0.0.jar.asc harness-sdk-all-1.0.0.jar
```

## 银行环境部署

### 部署检查清单

- [ ] JAR 文件 SHA256 校验通过
- [ ] OWASP 依赖扫描无高危漏洞
- [ ] SBOM 文件已提供
- [ ] 许可证兼容性确认（MIT/Apache 2.0）
- [ ] 离线环境测试通过
- [ ] 与现有系统集成测试通过

### 集成示例

```java
// 在银行项目中使用

import com.harness.Harness;
import com.harness.HarnessConfig;
import com.harness.core.LoopResult;

public class BankAgentService {
    
    private final Harness agent;
    
    public BankAgentService() {
        // 从配置文件加载
        HarnessConfig config = HarnessConfig.builder()
            .model("claude-sonnet-4-6")
            .apiKey(getApiKeyFromVault())  // 从银行密钥管理系统获取
            .tools(List.of(
                new ReadTool(),
                new BashTool(true)  // 沙箱模式
            ))
            .workingDirectory("/secure/workspace")
            .auditEnabled(true)     // 启用审计
            .build();
        
        this.agent = new Harness(config);
    }
    
    public String analyzeTransaction(String transactionData) {
        LoopResult result = agent.run(
            "分析以下交易数据是否存在异常: " + transactionData
        );
        
        if (result.isCompleted()) {
            return result.content();
        } else {
            throw new AgentException(result.error());
        }
    }
    
    private String getApiKeyFromVault() {
        // 从银行密钥管理系统获取 API Key
        // 例如：HashiCorp Vault、Azure Key Vault 等
        return System.getenv("ANTHROPIC_API_KEY");
    }
}
```

## 常见问题

### Q: 如何确认 JAR 文件完整性？

```bash
# 验证 SHA256
sha256sum -c checksums.sha256

# 输出
# harness-sdk-all-1.0.0.jar: OK
```

### Q: 如何在离线环境使用？

1. 下载 `harness-sdk-java-1.0.0.zip`
2. 解压到项目目录
3. 按上述方式引入 JAR 文件
4. 无需网络连接

### Q: 如何处理依赖冲突？

使用模块化 JAR 方式，排除已有依赖：

```kotlin
// 如果项目已有 Jackson
implementation(files("libs/harness-sdk-core-1.0.0.jar"))
implementation(files("libs/harness-sdk-anthropic-1.0.0.jar"))
// 排除包含 Jackson 的模块
```

### Q: 如何更新版本？

1. 下载新版本 ZIP 包
2. 替换 libs 目录中的 JAR 文件
3. 更新版本号引用
4. 重新构建项目

## 下一步

- [13-production-readiness.md](./13-production-readiness.md) - 生产就绪检查
- [14-bank-integration.md](./14-bank-integration.md) - 银行系统集成指南
