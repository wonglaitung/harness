# Ant Sandbox — 运行时级VM沙箱为Agent安全执行的新范式

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆☆/5 | 首次在JS运行时中原生集成KVM/Hypervisor VM沙箱，`ant:sandbox` API一行代码创建硬件隔离沙箱 |
| 采用广度 | ☆☆/5 | 新发布运行时，生态尚在建设（ants.land注册表） |
| 时间新鲜 | ☆☆☆☆☆/5 | 2026年7月Show HN首次公开，324分 |
| 社区热度 | ☆☆☆☆/5 | HN 324分，社区高度关注 |
| **总体判断** | ✅ | **新范式（早期）** |

## 技术定义 (What)
Ant 是一个从零构建的轻量级JavaScript运行时（8.6MB二进制），内置自研引擎 Ant Silver（非V8/JSC/SpiderMonkey包装）。核心创新是 `ant:sandbox` API——通过一行代码创建KVM/Hypervisor.framework硬件隔离VM沙箱，文件系统只读挂载、网络默认拒绝、仅开放指定端口。不可信代码在硬边界后执行。

## 行业痛点 (Why)
当前AI Agent执行不可信代码面临根本安全问题：Node.js/Deno/Bun仅提供权限提示（permission prompt），Agent可被诱导绕过；Docker容器共享宿主内核，存在逃逸风险。Agent需要一种"运行即隔离"的执行模型，而非"提示即安全"的软约束。

## 旧范式 vs 新范式
- **旧做法**：进程级权限控制（Deno --allow-net、Node --permission）——Agent可social-engineering绕过提示；Docker容器——共享内核，配置复杂
- **新做法**：运行时原生VM沙箱——`new Sandbox({mount: '.:/workspace'})` 一行代码创建硬件隔离环境，文件只读、网络拒绝、独立内核

## 生产力影响 (How)
- Agent开发者无需额外配置Docker/KVM，运行时内置沙箱能力
- 不可信代码执行从"谨慎审批"变为"放心运行"
- 9MB二进制零依赖部署，冷启动5.4ms（比Bun快2.4x、比Node快5.8x）
- 对AI Agent工具链：可直接将Ant作为Agent代码执行运行时，安全边界由硬件保证

## 采用成本
- 学习成本：低——标准JS/TS API，`ant:sandbox` 接口简洁
- 迁移成本：中——需从Node/Bun生态迁移，npm兼容但自研引擎可能有边缘case
- 基础设施：零——单二进制，无需Docker/QEMU/sudo
- 限制：仅macOS/Linux arm64/x86_64，Windows暂不支持

## 采用案例
- AI Agent安全执行：Agent生成的代码在 `ant:sandbox` 中运行，无法访问宿主文件或网络
- 不可信npm包测试：在只读挂载+无网络沙箱中运行第三方代码
- CI/CD流水线：轻量沙箱替代Docker容器执行构建脚本

## 风险/局限
- 自研引擎（Ant Silver）兼容性待验证——100% compat-table声称需实际验证
- 生态尚早期——ants.land注册表包数量有限
- 沙箱仅支持macOS/Linux，KVM需硬件支持
- 非AI原生项目——沙箱能力可被Agent利用，但Ant本身不是Agent框架

## 核心线索
- 官网：https://antjs.org/
- 首发来源：Show HN (324分)
- 发布时间：2026年7月
- 当前状态：试验中（早期发布）
- 关键创新：运行时原生VM沙箱 API (`ant:sandbox`)