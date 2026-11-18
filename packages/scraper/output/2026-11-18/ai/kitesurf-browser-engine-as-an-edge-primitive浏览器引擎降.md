# Kitesurf — Browser Engine as an Edge Primitive（浏览器引擎降级为边缘原语）

## 技术定义 (What)
Cloudflare 开源的实验性浏览器引擎：用 Rust + WebAssembly 重写 HTML 解析、CSS 计算、页面 JS 执行与截图渲染，跑在 Cloudflare Workers 上，不需要 Chrome、不需要浏览器容器、不需要 VM。对外说 Chrome DevTools Protocol (CDP)，因此 Puppeteer 等现有 CDP 客户端可直接连 `ws://.../devtools/browser` 使用，无迁移成本。每个页面导航启动一个独立 page isolate（Dynamic Workers），结束后即销毁，实现像素级/进程级的会话隔离。

## 行业痛点 (Why)
Agent 要「看网页」，今天唯一可靠的办法是跑无头 Chrome：一个容器 300MB–1GB、冷启动数秒、需要 VM 级隔离防恶意页面逃逸、并发几十个页面就吃掉一台机器。而 Agent 的浏览需求有个关键特征——绝大多数是「取一次 DOM / 截一张图 / 点几个按钮」，用完即弃。为了几秒钟的读取去维持一个完整浏览器的生命周期，是巨大的结构性浪费。CDP 协议是唯一成熟的自动化接口，但它被死死绑在 Chrome 这个重量级实现上。

## 旧范式 vs 新范式
- **旧做法**：Agent 浏览 = 起一个无头 Chrome 容器（Browserless / Playwright in Docker / 各家 Browser-Use 云），按容器或按分钟计费；隔离靠 VM/容器边界；CDP 是 Chrome 的私有实现，想用 CDP 就必须用 Chrome。
- **新做法**：Agent 浏览 = 一次边缘函数调用。浏览器引擎本身被编译成 WASM 部署到全球边缘网络，页面隔离由 isolate 提供而非容器，CDP 成为引擎对外暴露的标准接口而非某个实现的附属品。浏览器不再是「要运维的基础设施」，而是一个「按请求计费的无状态原语」——和 KV、R2、队列同级。

## 生产力影响 (How)
对 Agent 开发者：无需为抓取/截图链路维护容器集群与浏览器版本矩阵；冷启动从秒级降到边缘函数级；并发弹性由平台承担。对成本结构：从「常驻容器 × 时间」变为「请求 × 次数」，闲置成本归零。对安全模型：每个页面独立 isolate、导航结束即停止，把「恶意页面逃逸到宿主」的攻击面从容器边界收缩到 isolate 边界（但注意——本地开发跑在 `workerd` 上并非加固沙箱，官方明确警告勿开不可信站点）。

## 采用成本
需要 Cloudflare Workers Paid 计划（Dynamic Workers 依赖付费层）；本地构建链较重（Bazel + Rust nightly + wasm-bindgen + binaryen，首次编译久），macOS 还需 GNU tar。功能面目前是 CDP 子集——「提供的是 CDP endpoint，不是完整 Chrome 实现」，部分 DevTools 功能尚不可用。本地并发需自行加 `--expose-gc` V8 flag，否则约 300 页后 OOM。

## 核心线索
- GitHub：https://github.com/cloudflare/kitesurf
- 来源：https://blog.cloudflare.com/kitesurf-open-source/
- 发布时间：2026-11-18
