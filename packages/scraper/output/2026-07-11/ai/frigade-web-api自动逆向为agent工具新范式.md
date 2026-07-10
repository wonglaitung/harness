# Frigade — Web API自动逆向为Agent工具

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆☆/5 | 首个"Web Traffic→Agent Tool"自动逆向范式：浏览器内Agent监听Web应用API调用，自动生成MCP工具定义（Recipe），无需源码或API文档 |
| 采用广度 | ☆☆☆/5 | 已集成Jira/Spotify/HN等主流应用；Recipe自动更新跟随API变化 |
| 时间新鲜 | ☆☆☆☆☆/5 | 2026年7月Show HN首发 |
| 社区热度 | ☆☆☆/5 | HN 78分+28评论；社区讨论活跃，涉及WebMCP竞争、GraphQL难点等 |
| **总体判断** | ✅ | **新范式 — Agent工具从"手写MCP Server"到"自动逆向Web流量"** |

## 技术定义 (What)
Frigade是一个浏览器内Agent，运行在已认证的Web应用中，监听应用自身的API调用，自动将API端点、认证方式、请求/响应Schema逆向为"Recipe"——即可复用的Agent工具定义。这些Recipe等效于自动生成的MCP Server，且随应用API变化自动更新。

## 行业痛点 (Why)
当前AI Agent集成Web应用面临三大障碍：
1. **API混乱**：即使现代软件也常有蜘蛛网般的API，Agent无法直接使用
2. **认证碎片**：JWT/Cookie/混合认证标准不统一，每个应用都不同
3. **Computer-use太脆弱**：让浏览器Agent模拟点击操作太慢、太脆弱、token消耗大

## 旧范式 vs 新范式
- **旧做法**：手动编写MCP Server或API集成代码，需要源码访问、API文档、维护认证逻辑；或使用Computer-use模拟点击（慢且脆弱）
- **新做法**：Agent在浏览器内监听Web流量，自动逆向API为Recipe，自动处理认证，API变化时自动更新工具定义

## 生产力影响 (How)
- **零代码集成**：无需接触目标应用源码，无需API文档
- **自动维护**：API变更时Agent自动发现并更新Recipe
- **安全直连**：Agent直接调用应用API（非代理/中继），保持原有认证链
- **效率提升**：比Computer-use快数倍，token消耗降低一个数量级

## 采用成本
- **时间**：部署Agent到应用中约需数分钟
- **金钱**：Frigade为SaaS产品，具体定价未公开
- **学习曲线**：低——无需编写集成代码，但需理解Recipe概念和Dashboard配置

## 采用案例
- **Jira**：Agent自动逆向Jira API，实现"邀请队友到工作区"等操作
- **Spotify**：Agent自动逆向Spotify API，实现音乐搜索和播放控制
- **Hacker News**：Agent自动逆向HN API，实现帖子浏览和评论

## 风险/局限
- **GraphQL逆向困难**：创始人承认GraphQL是最难处理的API类型
- **SaaS依赖**：非完全开源，依赖Frigade云服务
- **认证边界**：复杂的多步OAuth流程可能需要额外配置
- **应用兼容性**：每个应用内部结构不同，边缘情况多

## 核心线索
- 首发来源：https://news.ycombinator.com/item?id=48847834
- 演示：https://demo.frigade.com/hn
- 发布时间：2026年7月
- 当前状态：Public Beta