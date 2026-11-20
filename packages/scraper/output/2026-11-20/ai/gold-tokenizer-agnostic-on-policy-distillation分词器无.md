# GOLD — Tokenizer-Agnostic On-Policy Distillation（分词器无关的在线蒸馏）

## 技术定义 (What)
GOLD 解除了「在线蒸馏（on-policy distillation）要求教师模型与学生模型共享同一分词器」这个长期约束。做法是在两端分词器切分文本方式不同处做 token 合并（merge），使教师与学生被比较的是同一段文本：双方词表都存在的 token 直接比较，其余 token 按排序后的概率分布比较。由此学生可以自回归生成、教师逐 token 打分，且允许学生自由选择架构与词表（如 Rumble-2-Flash 选 Qwen3-ASR 架构，仅因此继承其词表）。产物是 0.5B 语音识别模型，多语种错误率 6.96%（优于 15 倍大的 Meta omniASR-LLM 7B 与 Whisper large-v3），英文 6.6% WER，批量吞吐 >7,000 RTFx（1 小时音频约 0.5 秒）。

## 行业痛点 (Why)
在线蒸馏比离线蒸馏（学教师写的 transcript）效果更好，因为它让学生在「自己犯的错」上被逐 token 纠正，而不是每条音频只拿一个总分。但长期以来 in-policy 蒸馏被绑死在同一 tokenizer 上：想换学生架构就得迁就教师的词表，模型的「架构选择」与「蒸馏方法」被迫二选一。这使得小模型压缩时架构自由度几乎为零，也是小模型蒸馏往往只能沿用教师家族的原因。

## 旧范式 vs 新范式
- **旧做法**：旧做法：在线蒸馏必须先统一 tokenizer —— 要么学生照抄教师的词表（牺牲架构选型自由），要么退回离线蒸馏（只能对完整序列给一个标量分数，纠正粒度粗）。小模型的架构决策因此被蒸馏方法反向绑架。
- **新做法**：新做法：把「对齐」从模型层下移到 token 序列层。GOLD 在分词差异处合并 token，构造出两边共同可比的文本分段，再在分段上做逐 token 概率对齐。于是「学生用哪个词表/架构」与「能否用 on-policy 蒸馏」彻底解耦，教师可以是任意大模型，学生可以是任意小架构，蒸馏照旧逐 token 密集监督。

## 生产力影响 (How)
对小模型/端侧模型团队影响直接：1）架构选型从「教师的词表」中解放，可以按推理引擎、硬件或延迟最优挑骨干，再套 on-policy 蒸馏；2）逐 token 而非逐句的监督信号提升了压缩效率，0.5B 达成 30B 级（Nemotron 3.5 Transcribe）在真实客服通话数据上的水平（7.86% vs 7.78% WER）；3）原生支持 Transformers / vLLM，无 fork runtime、无 trust_remote_code，部署摩擦为零。这实质上把「知识蒸馏」重新变成了一个与 tokenizer 无关的通用压缩算子。

## 采用成本
方法本身是训练侧的，不增加推理侧成本。采用门槛在数据与教师：需要一份教师模型可打分的音频-文本对，且要跑得动教师做逐 token 前向（成本随教师规模线性增长）。GOLD 的对齐逻辑需要接入训练 pipeline（HF 已放出 Space 演示：huggingface.co/spaces/HuggingFaceH4/on-policy-distillation），工程改动集中在 tokenizer 对齐层，不改模型代码。学生端无额外依赖。

## 核心线索
- GitHub：https://huggingface.co/Reson8/Rumble-2-Flash
- 来源：https://huggingface.co/blog/rumble-2-flash
- 发布时间：2026-11-20
