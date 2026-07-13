# Clawk — Agent用一次性VM替代本机的新范式

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆☆/5 | 首次提出"给Agent自己的机器而非你的机器"——VM边界替代进程策略 |
| 采用广度 | ☆☆☆/5 | 支持 Claude Code、Codex、OpenCode 等主流编码Agent |
| 时间新鲜 | ☆☆☆☆☆/5 | Pre-1.0，2026年7月首次公开发布 |
| 社区热度 | ☆☆☆☆/5 | HN 165分，GitHub活跃开发 |
| **总体判断** | ✅ | **新范式** |

## 技术定义 (What)
Clawk 是一个为编码Agent提供一次性Linux VM的本地环境工具。Agent在独立VM中运行（代码挂载进去、拥有root权限、无需权限确认），而你的本机文件、密钥和网络完全隔离。一条命令 `clawk` 即可启动。

## 行业痛点 (Why)
当前编码Agent面临两难：要么逐条审批命令（每几秒弹一次确认），要么 `--dangerously-skip-permissions` 全开（ risking `rm -rf`、token泄露）。进程级沙箱（syscall filter）容易被绕过，且限制Agent安装包、运行服务、执行系统级操作。

## 旧范式 vs 新范式
- **旧做法**：Agent在本机运行，依赖进程沙箱策略（seccomp/namespace）或逐条权限审批
- **新做法**：Agent获得独立VM（独立内核、独立文件系统），VM边界即安全边界，Agent可自由操作而本机不受影响

## 生产力影响 (How)
- Agent可全速运行（`--dangerously-skip-permissions`），无需人工审批
- 支持安装系统包、运行数据库/队列/开发服务器、执行不可信构建
- VM损坏一键重建（`clawk destroy && clawk`），代码和对话历史保留在宿主机
- 支持多项目并行沙箱，空闲VM自动释放内存挂起

## 采用成本
- 需要 macOS 14+ Apple Silicon（Linux实验性支持）
- 无需Docker/qemu/sudo，Homebrew一键安装
- 学习曲线低：`cd repo && clawk` 即可使用

## 采用案例
- Claude Code：在VM中全自主运行，网络白名单阻止数据外泄
- Codex：`--dangerously-bypass-approvals-and-sandbox` 在VM中安全使用
- 多仓库Ticket：`clawk work INFRA-123` 创建多worktree沙箱，`clawk pr` 批量开PR

## 风险/局限
- Pre-1.0，API可能频繁变更
- 网络白名单允许github.com，ssh-agent转发可push——Agent能读的代码理论上可发布
- Linux支持仍为实验性
- 仅支持OCI镜像作为rootfs，定制需一定学习

## 核心线索
- GitHub：https://github.com/clawkwork/clawk
- 首发来源：Hacker News Show HN
- 发布时间：2026年7月
- 当前状态：Pre-1.0，活跃开发中