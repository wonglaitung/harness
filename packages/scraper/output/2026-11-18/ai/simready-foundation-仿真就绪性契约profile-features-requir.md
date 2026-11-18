# SimReady Foundation — 仿真就绪性契约（Profile → Features → Requirements）

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆☆/5 | 明确命名了三层结构：Profile（用例）/ Features（能力）/ Requirements（参数检查）；把「仿真就绪」从形容词变成了可校验的规格对象，并输出 validation.json 作为证据 |
| 采用广度 | ☆☆☆☆/5 | 已接入多品类 OEM：Comau、FANUC、Franka Robotics、Robotiq、Standard Bots、Universal Robots（机器人）；Vertiv（AI 工厂基础设施）；LG Electronics（家电+家用机器人）；Palatial、ForgeCAD（资产生成）。2,000+ 资产已上架 |
| 时间新鲜 | ☆☆☆☆/5 | SimReady Central 于 2026-10-21 公开发布；Foundation 8.0 为当前版本 |
| 社区热度 | ☆☆☆/5 | HF 官方博客双篇（发布 + 实操 walkthrough）；尚无 HN 大讨论，属于机构推动而非社区自发 |
| **总体判断** | ✅ | **新范式（满足概念创新 + 采用广度 + 时间新鲜 3 项）** |

## 技术定义 (What)

SimReady 是 OpenUSD 资产的「仿真就绪性」声明式契约。它把「这个模型能不能真的拿来跑物理仿真」拆成三层可机器校验的结构：

- **Profile**：用例分组，如 `Robot-Body 4.0.0`、`Robot-Gripper 3.0.0`
- **Features**：该用例需要的能力，如「可被控制的关节」
- **Requirements**：对每项能力的具体参数检查，如关节 drive 设置、碰撞几何、质量、摩擦、语义标签、传感器属性

资产方按 profile 打包并附上 validation report（JSON 证据），消费方按 profile 检索资产、直接组装场景。配套的 SimReady Central 在 Hugging Face 上托管 **2,000+ 个免费无门槛资产**，并提供 SKILL.md 形式的提交技能供 Agent 自动校验与提交。

## 行业痛点 (Why)

高质量 CAD/3D 模型 **不等于** 可仿真资产。开发者拿到一个漂亮模型后，必须手工补碰撞体、质量、摩擦、关节限位、驱动参数、语义标注，才能进 Isaac Sim 训练或做数字孪生。

这段「补物理属性」的脏活有三个致命问题：

1. **不可复用** —— 同一台机械臂，每个团队都要重新调一遍
2. **不可验证** —— 「看起来对」的资产，一跑仿真就穿模、抓不住、关节乱飞
3. **不可组合** —— A 家的臂 + B 家的夹爪 + C 家的箱子，几乎没有互操作保障

跨供应商组装场景是物理 AI 训练环境最贵的隐性成本。

## 旧范式 vs 新范式

**旧做法**
- 给开发者一个 3D 文件（STEP/CAD/GLB），文档里写「需自行配置碰撞与关节参数」
- 物理属性靠口口相传的调参经验
- 资产质量由人眼在视口里判断（静止时对 = 正确）
- 跨厂商资产组合靠试错

**新做法**
- 资产随包携带可机器校验的就绪性契约：Profile 声明用例，Features 声明能力，Requirements 声明参数检查项，validation.json 作为通过证据
- 消费方按 **profile 过滤**资产（而不是按文件夹翻）
- 组装后由仿真验证接触与抓取行为（静止正确 ≠ 运行正确，这一点被明确写进检查项）
- OEM 用 SKILL.md 技能让 Agent 完成「校验 → 打包 → 提交」闭环，资产经 HF 数据集直接分发

## 生产力影响 (How)

把「物理属性配置」从**每个团队的一次性劳动**，变成**资产供应链上游的一次性交付**。

- 原本需要数天调参的「机械臂 + 夹爪 + 物体」场景，现在可下载即组装，由 Agent 生成控制代码直接跑 pick-and-place
- 对物理 AI 训练环境的核心意义：训练数据的**物理保真度**第一次有了可审计的合同，而非依赖某个工程师的调参手艺
- Profile 化结构让合成数据生成（语义标签、传感器属性）能按用例**批量保证质量**，而不是逐资产抽查

## 采用成本

**消费方**：近乎零 —— HF 上免费、无门槛下载，2,000+ 资产现成可用。

**生产方（OEM）**：
- 需把 CAD 转 OpenUSD 并逐项补齐 profile 要求
- 需装 Python 3.12 专用 venv（`simready-validate` 与 `usd-core` 易与其他包冲突，官方明确警告）
- 需跑 validation 与 packaging 两个 CLI（两者都需 `--project-config` 传入 profile 定义）
- 仓库走 Git LFS（`.usda/.usdc/.usd/.usdz` 均为 LFS 追踪）
- 整车/整厂级资产门槛不低，但一旦完成即对所有下游复用

## 采用案例

- **Universal Robots + Robotiq + 饮料罐**：官方 walkthrough 展示用 UR17G 臂 + Robotiq 2F-140 夹爪 + 罐头资产组装 Isaac Sim 场景，由 GPT-6 Sol 生成控制代码完成 pick-and-place
- **Vertiv（AI 工厂）**：机架、服务器机架、冷却设备资产用于 AI 工厂数字孪生，复用 SimReady profile 指定的几何与属性
- **LG Electronics**：冰箱、洗碗机等家电资产 + 家用机器人，构建家居仿真环境做机器人训练与合成数据
- **Palatial**：随 NVIDIA Robotics 发布 Robotics 1K Dataset，并提供由文本/图像/扫描/数据表/CAD 生成的可动资产

## 风险/局限

- **机构推动，非社区自发**：0 stars 讨论热度，标准能否成为行业事实标准取决于 NVIDIA Omniverse 生态的锁定程度
- **仓库不接受外部贡献**（CONTRIBUTING.md 明确说明），标准演进由 NVIDIA 单方掌控
- **版本耦合**：Foundation 8.0 必须搭配 8.0 库；虽然 8.0 库向后兼容 6.0/7.1，但版本矩阵仍需谨慎匹配
- **Profile 覆盖边界**：现有 profile 集中在机器人本体/夹爪/AI 工厂设备，软体、流体、柔性物体等用例尚未覆盖
- **静止正确 ≠ 运行正确**：官方明确要求跑仿真验证接触行为，说明 validation 报告只保证参数合规，不保证任务成功

## 核心线索

- **SimReady Foundation 仓库**：https://github.com/NVIDIA/simready-foundation
- **SimReady Central（HF 资产库）**：https://huggingface.co/spaces/nvidia/simready-central
- **发布博客**：https://huggingface.co/blog/nvidia/simready-central-assets-robotics-ai-factories
- **实操 walkthrough**：https://huggingface.co/blog/nvidia/simready-assets-robot-pick-and-place
- **提交技能（SKILL.md）**：https://github.com/NVIDIA-Omniverse/simready-central/blob/main/.agents/skills/submit-simready-assets/SKILL.md
- **发布时间**：2026-10-21
- **当前状态**：活跃（机构生态推进中）

## 为什么这是新范式

判断依据是**「就绪性」从形容词变成契约对象**。

在此之前的同类工作（URDF / MJCF / USD 本身）都只描述**结构**——有什么连杆、什么关节、什么网格。SimReady 首次把**「够不够用」**也编码进资产：profile 绑定用例，feature 绑定能力，requirement 绑定参数检查，validation.json 绑定证据。

这带来一个结构性后果：**资产可以被程序化检索和组合**。没有契约时，你只能人眼挑资产；有了契约，Agent 可以「给我所有满足 Robot-Gripper 3.0.0 的两指夹爪」并直接组装验证。这正是物理 AI 数据管线从手工走向自动化的前提。
