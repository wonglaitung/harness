"""
SharedStateStore 黑板通信示例 — 多 Agent 通过黑板协作（非 P2P）。

本示例演示：
1. BlackboardItem 的创建、写入、读取
2. additive vs authoritative 写分层
3. CAS 乐观并发控制
4. 冲突检测
5. provenance 溯源（A4）

运行方式：
    python examples/multi_agent_blackboard.py

所有示例使用内存 store，无需外部依赖。
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from harness.state import (
    ConflictSet,
    ItemStatus,
    WriteKind,
    create_state_store,
)


# ── 示例 1: 基础读写 ────────────────────────────────────────────────────────


async def demo_basic_read_write():
    """基础读写：agent 写入观测/决策 → 从黑板读取回来。"""
    print("\n" + "=" * 60)
    print("示例 1: 基础读写")
    print("=" * 60)

    store = create_state_store("memory")

    # Agent A 写入一条观测（additive：任意 Agent 可写）
    item_a = await store.put_additive(
        type="observation",
        content={"modules": ["auth", "api", "db"]},
        source_agent="analyzer",
        writer_id="agent-a",
    )
    print(f"[Agent A] 写入观测: {item_a.id}")

    # Agent B 写入一条决策（authoritative：需 provenance）
    item_b = await store.put_authoritative(
        type="decision",
        content={"approved": True, "score": 85},
        source_agent="reviewer",
        writer_id="agent-b",
        provenance="file:report.pdf:page=3",  # A4: 溯源
    )
    print(f"[Agent B] 写入决策: {item_b.id} (provenance={item_b.provenance})")

    # 读取
    got_a = await store.get(item_a.id)
    got_b = await store.get(item_b.id)
    print(f"\n[读取] Agent A 的观测: {got_a.content}")
    print(f"[读取] Agent B 的决策: {got_b.content} (provenance={got_b.provenance})")


# ── 示例 2: additive vs authoritative 写分层 ──────────────────────────────────


async def demo_write_layers():
    """
    写分层：
    - additive：任意 Agent 可写（观测/提议）
    - authoritative：仅控制层可写（决策落定），必带 provenance
    """
    print("\n" + "=" * 60)
    print("示例 2: additive vs authoritative 写分层")
    print("=" * 60)

    store = create_state_store("memory")

    # additive 写入：任意 Agent
    item_additive = await store.put_additive(
        type="proposal",
        content={"suggestion": "增加单元测试覆盖"},
        source_agent="junior-dev",
    )
    print(f"[additive] junior-dev 提议: {item_additive.content} (kind={item_additive.kind.value})")

    # authoritative 写入：需 provenance
    item_auth = await store.put_authoritative(
        type="decision",
        content={"action": "approve"},
        source_agent="tech-lead",
        writer_id="harness",
        provenance="meeting:2024-01-15:decision-1",  # A4: 必填
    )
    print(f"[authoritative] tech-lead 决策: {item_auth.content} (provenance={item_auth.provenance})")

    # 列出所有 items
    all_items = await store.list_items()
    print(f"\n黑板中共 {len(all_items)} 条记录:")
    for item in all_items:
        print(f"  [{item.kind.value}] {item.source_agent}: {item.content}")


# ── 示例 3: CAS 乐观并发控制 ─────────────────────────────────────────────────


async def demo_cas_concurrency():
    """
    CAS（Compare-And-Swap）：并发写入时，版本不匹配则拒绝。
    防止 Agent B 覆盖 Agent A 的写入（防幻觉覆写）。
    """
    print("\n" + "=" * 60)
    print("示例 3: CAS 乐观并发控制")
    print("=" * 60)

    store = create_state_store("memory")

    # Agent A 写入初始版本（base_version=0 创建）
    ok, item = await store.write_if_version(
        "counter", {"value": 100}, base_version=0,
        type="metric", source_agent="agent-a",
    )
    print(f"[Agent A] 写入初始版本: value={item.content['value']}, version={item.version}")

    # Agent B 尝试基于旧版本覆盖 → 失败
    ok, current = await store.write_if_version(
        "counter", {"value": 200}, base_version=0  # 旧版本
    )
    print(f"[Agent B] CAS 写入 (base_version=0): {'成功' if ok else '失败'}")
    if not ok:
        print(f"  当前版本: {current.version}，Agent B 的 base_version=0 已过期")

    # Agent C 基于正确版本写入 → 成功
    base_c = current.version  # 捕获当前版本（避免后续写操作修改同一对象引用）
    ok, updated = await store.write_if_version(
        "counter", {"value": 200}, base_version=base_c  # 当前版本
    )
    print(f"[Agent C] CAS 写入 (base_version={base_c}): {'成功' if ok else '失败'}")
    if ok:
        print(f"  新版本: value={updated.content['value']}, version={updated.version}")


# ── 示例 4: 冲突检测 ────────────────────────────────────────────────────────


async def demo_conflict_detection():
    """
    冲突检测：两个 Agent 对同一 type 写入不同内容 → 冲突集显性化。
    """
    print("\n" + "=" * 60)
    print("示例 4: 冲突检测")
    print("=" * 60)

    store = create_state_store("memory")

    # Agent A 写入决策
    await store.put_authoritative(
        type="architecture",
        content={"database": "PostgreSQL"},
        source_agent="agent-a",
        writer_id="harness",
        provenance="meeting:2024-01-15",
    )
    print("[Agent A] 决策: database=PostgreSQL")

    # Agent B 写入冲突决策
    await store.put_authoritative(
        type="architecture",
        content={"database": "MongoDB"},  # ← 与 A 冲突！
        source_agent="agent-b",
        writer_id="harness",
        provenance="meeting:2024-01-16",
    )
    print("[Agent B] 决策: database=MongoDB")

    # 检测冲突
    conflicts = await store.get_conflicts()
    print(f"\n冲突数: {len(conflicts)}")
    for cs in conflicts:
        print(f"  冲突类型: {cs.key}")
        print(f"  冲突项: {cs.item_ids}")
        print(f"  检测时间: {cs.detected_at}")


# ── 示例 5: 真实场景 — 多 Agent 代码审查 ────────────────────────────────────


async def demo_real_scenario():
    """
    真实场景：多个 Agent 通过黑板协作完成代码审查。

    流程：
    1. analyzer 写入分析结果（additive）
    2. linter 写入 lint 结果（additive）
    3. reviewer 基于黑板数据给出审查意见（additive）
    4. tech-lead 做最终决策（authoritative）
    """
    print("\n" + "=" * 60)
    print("示例 5: 真实场景 — 多 Agent 代码审查")
    print("=" * 60)

    store = create_state_store("memory")

    # 1. Analyzer 写入分析结果
    await store.put_additive(
        type="analysis",
        content={"modules": ["auth", "api", "db"], "complexity": "medium", "test_coverage": 0.72},
        source_agent="analyzer",
        writer_id="harness",
    )
    print("[1] analyzer: 分析完成 → 写入黑板")

    # 2. Linter 写入 lint 结果
    await store.put_additive(
        type="lint_result",
        content={"errors": 0, "warnings": 3, "issues": ["unused-import", "line-too-long", "missing-docstring"]},
        source_agent="linter",
        writer_id="harness",
    )
    print("[2] linter: 检查完成 → 写入黑板")

    # 3. Reviewer 从黑板读取数据，给出审查意见
    analysis_items = await store.list_items(type="analysis")
    lint_items = await store.list_items(type="lint_result")

    analysis = analysis_items[0].content if analysis_items else {}
    lint = lint_items[0].content if lint_items else {}

    review_score = 100 - (lint["errors"] * 10) - (lint["warnings"] * 2)
    await store.put_additive(
        type="review",
        content={
            "score": review_score,
            "verdict": "approve" if review_score >= 80 else "revise",
            "summary": f"模块划分清晰，覆盖率{analysis['test_coverage'] * 100:.0f}%，{lint['warnings']}个warning",
        },
        source_agent="reviewer",
        writer_id="harness",
    )
    print(f"[3] reviewer: 审查完成 (score={review_score}) → 写入黑板")

    # 4. Tech-lead 做最终决策（authoritative）
    review_items = await store.list_items(type="review")
    review = review_items[0].content if review_items else {}
    await store.put_authoritative(
        type="decision",
        content={"action": review["verdict"], "reason": review["summary"]},
        source_agent="tech-lead",
        writer_id="harness",
        provenance="review:2024-01-15:final",
    )
    print(f"[4] tech-lead: 最终决策 → {review['verdict']} (authoritative)")

    # 查看完整黑板
    all_items = await store.list_items()
    print(f"\n黑板完整状态 ({len(all_items)} 条):")
    for item in all_items:
        kind = "AUTH" if item.kind == WriteKind.AUTHORITATIVE else "ADD"
        prov = f" [prov={item.provenance}]" if item.provenance else ""
        print(f"  [{kind}] {item.source_agent}/{item.type}: {item.content}{prov}")


# ── 主函数 ────────────────────────────────────────────────────────────────────


async def main():
    """运行所有示例。"""
    print("SharedStateStore 黑板通信示例")
    print("所有示例使用内存 store，无需外部依赖")

    await demo_basic_read_write()
    await demo_write_layers()
    await demo_cas_concurrency()
    await demo_conflict_detection()
    await demo_real_scenario()

    print("\n" + "=" * 60)
    print("所有示例运行完成")


if __name__ == "__main__":
    asyncio.run(main())
