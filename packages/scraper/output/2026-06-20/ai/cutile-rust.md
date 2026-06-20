# cuTile Rust

## 技术定义 (What)
cuTile Rust 是 NVIDIA Labs 开发的 GPU 内核编程框架，将 Rust 的所有权系统扩展到 GPU 编程边界。通过 tensor 分区和类型系统保证，实现内存安全、无数据竞争的 GPU 内核开发，支持同步启动、异步管道和 CUDA 图重放。

## 行业痛点 (Why)
传统 GPU 编程（CUDA C++）存在内存安全问题和数据竞争风险，调试困难。即使是 Rust 等安全语言，在 GPU 启动边界也会失去安全保证。cuTile Rust 通过 tile-based 分区模型，在 GPU 端保持 Rust 的安全语义。

## 旧范式 vs 新范式
- **旧做法**：使用 CUDA C++ 或 unsafe Rust 编写 GPU 内核，需要手动管理内存同步、避免数据竞争，依赖运行时检测或事后调试发现问题。
- **新做法**：通过 Rust 所有权和类型系统在编译期保证 GPU 内核安全。Mutable tensor 在启动前分区为不重叠片段，immutable tensor 共享，生成的启动器在 GPU 执行期间保持所有权。JIT 编译 Rust AST 到 CUDA Tile IR 再到 GPU cubin。

## 生产力影响 (How)
在 NVIDIA B200 上达到 7 TB/s 内存带宽和 2 PFlop/s GEMM 性能，与 cuBLAS 竞争。Hugging Face 已用于 Grout 推理引擎（Qwen3 解码 171 tokens/s）。安全开销可忽略不计。

## 采用成本
需要 NVIDIA sm_80+ GPU 和 CUDA 13.3。学习 Rust 所有权系统和 tile-based GPU 编程模型。当前为早期研究项目，API 可能变化。

## 核心线索
- GitHub：https://github.com/nvlabs/cutile-rs
- 来源：https://github.com/nvlabs/cutile-rs
- 发布时间：2026-06-20
