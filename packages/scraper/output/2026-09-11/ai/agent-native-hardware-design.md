# Agent-Native Hardware Design

## 技术定义 (What)


## 行业痛点 (Why)
硬件设计的核心痛点"Drift"：一个设计决策分散在schematic、BOM、power budget和多个文档中，当它们不同步时没有任何东西报错。不一致性在bring-up才发现，返工成本极高

## 旧范式 vs 新范式
- **旧做法**：人工手动在KiCad/Altium中设计PCB，schematic和BOM靠人工保持一致性。设计变更时文档（spec、BOM、power budget）与设计文件脱节（"drift"），错误在bring-up阶段才发现，一次respin花费$5k-$50k和6-8周
- **新做法**：Agent驱动8阶段门控流水线：brief → spec → architecture → parts → schematic → layout → outputs → firmware → dev plan。每阶段必须在磁盘上留下可验证产物后才进入下一阶段。所有编辑是外科手术式的s-expression修改，diff小而可审查。KiCad原生ERC/DRC验证。

## 生产力影响 (How)
将硬件设计从"人工协调多文件一致性"变为"Agent自动门控验证"，大幅降低respin风险。对于开源硬件社区，显著降低PCB设计门槛

## 采用成本
免费CLI + Node 20 + KiCad安装；Agent调用需自带Claude/GPT API key；学习曲线：理解8阶段硬件设计流水线和约束文件编写

## 核心线索
- GitHub：https://github.com/animesh-chouhan/open-telegraph
- 来源：https://copperhead.sh/
- 发布时间：2026-09-11
