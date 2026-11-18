# ZigZag — 拒绝订阅的本地制造链 + 机器即 MCP 端点

## 技术定义 (What)
ZigZag 是一个用 Rust 写的刺绣（embroidery）设计与数字化（digitizing）工具，内置 MCP 服务器（含 stdio↔HTTP bridge），让 AI Agent 能直接创建/编辑刺绣设计；引擎输出 PES/DST/EXP/JEF/VP3 等工业绣花格式，并可通过蓝牙直接把花样推送到 Brother Skitch (PP1) 绣花机。仓库把机器档位（hoop 尺寸、文件格式）做成可用户自扩展的 JSON machine profile，并把「数字化检查」（尺寸、线宽、字距、花绷范围）实现为代码内可校验环节。

## 行业痛点 (Why)
消费级硬件（本案例是 300 美元的绣花机）被厂商 App / 订阅制锁死：用户买了机器，却不能自由地把自己的设计送进机器；专业数字化软件（如商用绣花排版软件）价格高、格式封闭、且完全无法被 Agent 调用。设计意图与物理产出之间隔着一整条人工转译链。

## 旧范式 vs 新范式
- **旧做法**：Illustrator 画矢量 → 导入昂贵数字化软件手动排针迹 → 导出厂商格式 → 用厂商订阅 App 传机。任何一个环节都不接受程序化调用，Agent 无从介入，物理制造是「人类专属的最后一步」。
- **新做法**：设计工具自身暴露 MCP 端点，Agent 通过 MCP 直接建/改设计；引擎在写文件前跑「数字化检查」把不可行的设计挡在编译期；最后由 CLI 或 GUI 直接把花样推到机器。物理制造设备第一次成为 Agent 工具链里的一个可调用节点，而不是流程终点的人肉出口。

## 生产力影响 (How)
给出了一条可复用的范式路径：把「机器能力」抽象成 profile 文件（hoop/格式/协议），把「领域规则」抽象成编译期检查，那么任何物理设备（3D 打印机、CNC、激光切割机、绣花机）都可以被包装成 Agent 可操作端点。开发者的价值从「写排版算法」上移到「写机器的能力契约 + 写失败前的校验闸门」。

## 采用成本
时间：中等。有签名公证的 macOS dmg 和 Homebrew cask，Windows/Linux 免装 Rust 也能跑；仅有源码构建需求时才需 cargo。学习曲线在于绣花领域知识（tatami 填充、satin 走线、底衬、pull compensation），但这些已被显式 token 化，Agent 可代为调参。金钱：几乎为零（开源 + 本地运行，无云、无 API key）。

## 核心线索
- GitHub：https://github.com/simpsoka/zigzag
- 来源：https://news.ycombinator.com/show (Show HN 742 points)
- 发布时间：2026-11-18
