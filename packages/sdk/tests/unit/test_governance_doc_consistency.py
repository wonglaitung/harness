"""治理设计稿（21-hkma-agentic-governance.md）自洽性检查。

设计稿是代码改造的唯一规格来源。稿内任何"字段 / 规则 / 信号 / 事件 / 状态"
之间的矛盾，都会在实现时分叉成不同行为。本测试把可机器判定的自洽条件固化为
断言，避免靠人工通读发现。

检查项：
1. 结构：标题层级、代码围栏、表格列数
2. 引用：所有 §N / 第 N 节 引用指向真实章节
3. 代码块：YAML / JSON 可解析
4. 声明对账：
   - §5.2 示例的字段 ↔ §5.3 校验规则
   - §8.2 信号 ↔ §5.2 `limits.signal_thresholds`
   - §10.1 事件类型 ↔ 全文引用（每种事件须有产出方）
   - §5.3 规则编号连续
   - §12 工作项编号连续
5. 事实核对：文档声称"已有/现状"的机制，其符号须真实存在于 SDK 源码
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
import yaml

SDK_ROOT = Path(__file__).resolve().parents[2]
DOC_PATH = SDK_ROOT / "docs" / "21-hkma-agentic-governance.md"
SRC_ROOT = SDK_ROOT / "src" / "harness"

# 文档里出现但不属于 SDK 符号的词（散文、字面量、枚举值、示例工具名等）
NON_SYMBOL_WORDS = {
    "yaml", "json", "python", "bash", "mermaid", "markdown", "agent_id", "run_id",
    "step_id", "args_hash", "strict", "workflow", "steps", "tools", "id", "if",
    "outputs", "outcome", "conclusion", "env", "github", "secrets", "matrix",
    "runner", "needs", "jobs", "inputs", "vars", "continue-on-error",
    "timeout-minutes", "shared_tools", "approved_by", "material", "limits",
    "approval_required_for", "intervention", "kill_switch", "fallback",
    "capability", "complete", "idempotent", "from", "path", "name", "type",
    "value", "op", "policy", "sdk", "api", "ui", "cli", "jsonl", "sha256", "uuid",
    "hmac", "cors", "dns", "url", "http", "https", "localhost", "git", "npm",
    "node", "pip", "python3", "read_only", "search", "run", "draft", "post",
    "read", "write", "edit", "bash",
    # 占位符字面量（治理块里是"被拒绝的值"，不是代码符号）
    "TODO", "TBD", "FIXME", "XXX",
}

# 本设计稿新引入、SDK 源码中尚不存在的符号（P0 待实现）。
# 任何**不在**此清单中的 CamelCase 符号，都必须在 SDK 源码中存在——
# 否则文档里的一个类名/常量名是笔误或幻觉，实现时会找不到。
DESIGN_NEW_SYMBOLS = {
    "PolicySnapshot",   # P0-1 编译产物
    "INCOMPLETE",       # P0-3 新增 LoopState
    "AppSettings",      # 客户端设置类（存在于 packages/client，非 SDK）
}


@pytest.fixture(scope="module")
def doc_text() -> str:
    return DOC_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def doc_lines(doc_text: str) -> list[str]:
    return doc_text.split("\n")


@pytest.fixture(scope="module")
def sdk_source() -> str:
    parts = []
    for path in SRC_ROOT.rglob("*.py"):
        parts.append(path.read_text(encoding="utf-8"))
    return "\n".join(parts)


def _section(lines: list[str], start_pat: str, end_pat: str) -> str:
    start = end = None
    for i, line in enumerate(lines):
        if start is None and re.match(start_pat, line):
            start = i
        elif start is not None and re.match(end_pat, line):
            end = i
            break
    if start is None:
        return ""
    return "\n".join(lines[start:end if end is not None else len(lines)])


def _section_by_title(doc_lines: list[str], title_kw: str) -> str:
    """按**标题文字**定位小节内容（而非章节编号）。

    章节编号会随结构调整而变，硬编码编号会让检查在每次重构后失效。
    这里按标题里的关键词定位，语义稳定。
    """
    start = end = None
    level = None
    for i, line in enumerate(doc_lines):
        m = re.match(r"^(#{2,4}) (.+)$", line)
        if not m:
            continue
        if start is None:
            if title_kw in m.group(2):
                start, level = i, len(m.group(1))
        elif len(m.group(1)) <= level:
            end = i
            break
    if start is None:
        return ""
    return "\n".join(doc_lines[start: end if end is not None else len(doc_lines)])


def _governance_block(doc_text: str) -> dict:
    """取 §5.2 的治理块示例（YAML frontmatter 形态）。"""
    blocks = re.findall(r"```yaml\n(.*?)```", doc_text, re.S)
    for block in blocks:
        if block.startswith("---\n"):
            body = block[len("---\n"): block.rstrip().rfind("---")]
            data = yaml.safe_load(body)
            if isinstance(data, dict) and "governance" in data:
                return data["governance"]
    raise AssertionError("未找到 §5.2 治理块示例")


# --------------------------------------------------------------------------
# 1. 结构
# --------------------------------------------------------------------------

def test_heading_levels_never_jump(doc_lines: list[str]) -> None:
    prev = 0
    for i, line in enumerate(doc_lines, 1):
        if line.startswith("#"):
            level = len(line) - len(line.lstrip("#"))
            assert level <= prev + 1, f"L{i}: 标题层级跳跃：{line[:40]}"
            prev = level


def test_code_fences_balanced(doc_lines: list[str]) -> None:
    fences = [i for i, line in enumerate(doc_lines, 1) if line.startswith("```")]
    assert len(fences) % 2 == 0, f"代码围栏不配对：{fences}"


def test_table_column_counts_consistent(doc_lines: list[str]) -> None:
    def cols(line: str) -> int:
        return line.replace("\\|", "").count("|")

    i = 0
    while i < len(doc_lines):
        line = doc_lines[i]
        if (
            line.startswith("|")
            and i + 1 < len(doc_lines)
            and re.match(r"^\|[\s:\-|]+\|$", doc_lines[i + 1])
        ):
            width = cols(line)
            j = i + 2
            while j < len(doc_lines) and doc_lines[j].startswith("|"):
                assert cols(doc_lines[j]) == width, (
                    f"L{j + 1}: 表格列数不一致（期望 {width}，实际 {cols(doc_lines[j])}）"
                )
                j += 1
            i = j
        else:
            i += 1


# --------------------------------------------------------------------------
# 2. 引用完整性
# --------------------------------------------------------------------------

def test_section_references_resolve(doc_lines: list[str]) -> None:
    sections = set()
    for line in doc_lines:
        m = re.match(r"^(#{2,4})\s+(\d+(?:\.\d+)*)(?:\.\s|\s|$)", line)
        if m:
            sections.add(m.group(2))

    for i, line in enumerate(doc_lines, 1):
        for m in re.finditer(r"§\s*(\d+(?:\.\d+)*)", line):
            assert m.group(1) in sections, f"L{i}: 悬空引用 §{m.group(1)}"
        for m in re.finditer(r"见\s*(\d+(?:\.\d+)*)\s*节", line):
            assert m.group(1) in sections, f"L{i}: 悬空引用 第{m.group(1)}节"


def test_bare_section_numbers_resolve(doc_lines: list[str]) -> None:
    """**不带 § 的裸编号**引用（如"见 6.4"）也必须指向真实章节。

    这类引用藏在代码块里（流水线示意），章节重排后不会被带 § 的
    重写逻辑覆盖——曾导致 7 处引用在重构后全部失效。单独加检查守住。
    """
    sections = set()
    for line in doc_lines:
        m = re.match(r"^(#{2,4})\s+(\d+(?:\.\d+)*)(?:\.\s|\s|$)", line)
        if m:
            sections.add(m.group(2))

    pattern = re.compile(r"(?<!§)(?<!第 )\b(\d+\.\d+)\b")
    for i, line in enumerate(doc_lines, 1):
        # 先去掉带 § 的引用，剩下的才是"裸编号"
        stripped = re.sub(r"§\s*\d+(?:\.\d+)*", "", line)
        for m in pattern.finditer(stripped):
            num = m.group(1)
            if num in sections:
                continue
            before = stripped[max(0, m.start() - 16): m.start()]
            after = stripped[m.end(): m.end() + 6]
            # 排除非章节号：版本号 / 编码名 / URL / 纯小数
            if re.search(r"(sha|utf|ascii|https?|v\d)\s*$", before, re.I):
                continue
            if re.match(r"^\s*\d*\.?\d*\s*$", after) and not re.search(r"[§（(]\s*$", before):
                # 后面不是章节语境（如 "sha256:9f2c"、小数）→ 排除
                if not re.search(r"见|参见|依据|按|据|第|§|节", before):
                    continue
            assert num in sections, (
                f"L{i}: 裸编号引用 {num} 不指向任何章节（上下文："
                f"{(before + num + after).strip()!r}）"
            )


# --------------------------------------------------------------------------
# 3. 代码块可解析
# --------------------------------------------------------------------------

def test_yaml_blocks_parse(doc_text: str) -> None:
    for i, block in enumerate(re.findall(r"```yaml\n(.*?)```", doc_text, re.S), 1):
        if block.startswith("---\n"):
            body = block[len("---\n"): block.rstrip().rfind("---")]
            yaml.safe_load(body)
        else:
            yaml.safe_load(block)


def test_json_blocks_parse(doc_text: str) -> None:
    for i, block in enumerate(re.findall(r"```json\n(.*?)```", doc_text, re.S), 1):
        json.loads(block)


# --------------------------------------------------------------------------
# 4. 声明对账
# --------------------------------------------------------------------------

def test_rule_numbering_is_contiguous(doc_lines: list[str]) -> None:
    # 锚到"校验规则"整节——它包含全部子节共 25 条；
    # 若只锚到"通用"子节，只会看到前 7 条，后续断裂查不出来。
    section = _section_by_title(doc_lines, "校验规则")
    numbers = [
        int(m.group(1))
        for line in section.split("\n")
        for m in [re.match(r"^(\d+)\. ", line)]
        if m
    ]
    assert numbers, "§5.3 未找到编号规则"
    assert numbers == list(range(1, len(numbers) + 1)), f"§5.3 规则编号不连续：{numbers}"


def test_implementation_plan_numbering_is_contiguous(doc_lines: list[str]) -> None:
    section = _section_by_title(doc_lines, "实施计划")
    numbers = [
        int(m.group(1))
        for line in section.split("\n")
        for m in [re.match(r"^(\d+)\. ", line)]
        if m
    ]
    assert numbers, "§12 未找到编号工作项"
    assert numbers == list(range(1, len(numbers) + 1)), f"§12 工作项编号不连续：{numbers}"


def test_signals_have_threshold_fields(doc_text: str, doc_lines: list[str]) -> None:
    """§8.2 定义的每个信号，要么有阈值字段，要么明确声明不受治理块覆盖。"""
    governance = _governance_block(doc_text)
    thresholds = set(governance.get("limits", {}).get("signal_thresholds", {}))

    section = _section_by_title(doc_lines, "行为信号")
    signal_rows = re.findall(r"^\| `([a-z_]+)` \|(.+)$", section, re.M)

    assert signal_rows, "§8.2 未找到信号表"
    for name, rest in signal_rows:
        if name in thresholds:
            continue
        # 未列入阈值表者，必须在行内声明其阈值由别处决定
        assert "不受治理块覆盖" in rest or "既有" in rest, (
            f"信号 `{name}` 既无 `limits.signal_thresholds` 字段，"
            f"也未声明阈值来源——开发者将无法覆盖它（§5.3.1 规则 6 未知字段拒绝）"
        )


def test_every_event_type_has_a_producer(doc_lines: list[str]) -> None:
    """§10.1 的事件清单必须与"产出方表"逐项一致。

    双向校验：
    - 正文声明要写的事件 → 必须在产出方表中有行（否则不知何时写）
    - 产出方表中的行 → 必须在正文被提及（否则是孤立的僵尸事件）

    孤立行会让"实现了但没人引用"或"引用了但表里没有"两类漂移无法被发现。
    """
    section = _section_by_title(doc_lines, "事件模型")
    table_match = re.search(
        r"事件类型与\*\*产出方\*\*.*?\n\n(.*?)\n\n", section, re.S
    )
    assert table_match, "§10.1 缺少事件类型产出方表"

    declared = set(re.findall(r"^\| `([a-z_]+)` \|", table_match.group(1), re.M))
    assert declared, "§10.1 产出方表为空"

    # 正文声明要写的事件：行内出现「事件」且含反引号标识符即为候选。
    # （不能用单一正则：`**`code`** 事件` 这类加粗写法会让模式匹配漏掉。）
    # 排除：仅"与事件无关的枚举值恰好在同一行"的情况——要求该标识符在行内
    # 处于「动词 + 标识符 + 事件」或「标识符 + 事件」的邻近关系。
    mentioned: set[str] = set()
    event_adjacent = re.compile(
        r"(?:写|记|产生|产出|触发|携带)[^`\n]{0,12}`([a-z_]+)`[^`\n]{0,20}事件"
        r"|`([a-z_]+)`[^`\n]{0,4}事件"
    )
    for sec in (
        _section_by_title(doc_lines, "失败语义"),
        _section_by_title(doc_lines, "运行期审批机制"),
        _section_by_title(doc_lines, "条件与事实"),
        _section_by_title(doc_lines, "游标判定"),
        _section_by_title(doc_lines, "行为信号"),
        _section_by_title(doc_lines, "状态与存储"),
        _section_by_title(doc_lines, "模式开关"),
    ):
        for line in sec.split("\n"):
            if "事件" not in line:
                continue
            for m in event_adjacent.finditer(line):
                mentioned.add(m.group(1) or m.group(2))

    known_non_events = {"tool_call", "gate_verdict", "approval"}
    for event in sorted(mentioned - known_non_events - declared):
        assert event in declared, (
            f"正文声明要写 `{event}` 事件，但 §10.1 产出方表无对应行——"
            f"实现时无从判断在哪个阶段写它"
        )

    # 产出方表中的行必须在正文（表外）被提及，否则是孤立事件
    body = "\n".join(doc_lines)
    outside_table = body.replace(table_match.group(0), "")
    for event in sorted(declared):
        assert re.search(rf"`{event}`", outside_table), (
            f"§10.1 产出方表列出 `{event}`，但正文别处从未提及——"
            f"僵尸事件：实现了没人用，或该表行已过期"
        )


def test_governance_example_fields_are_validated(doc_lines: list[str]) -> None:
    """§5.2 示例的每个顶层字段，须在 §5.3 至少被提及一次（否则无校验规则）。"""
    governance = _governance_block("\n".join(doc_lines))
    section = _section_by_title(doc_lines, "校验规则")

    for field in governance:
        assert field in section, (
            f"治理块顶层字段 `{field}` 在 §5.3 无任何校验规则提及——"
            f"未知字段拒绝规则下它可能被误拒，也可能无人校验"
        )


def test_step_fields_are_validated(doc_lines: list[str]) -> None:
    """§5.2 示例的每个 step 字段，须在 §5.3 至少被提及一次。"""
    governance = _governance_block("\n".join(doc_lines))
    section = _section_by_title(doc_lines, "校验规则")

    step_fields: set[str] = set()
    for step in governance.get("workflow", {}).get("steps", []):
        step_fields |= set(step)

    for field in step_fields:
        assert field in section, (
            f"step 字段 `{field}` 在 §5.3 无任何校验规则提及"
        )


def test_authoring_section_covers_all_nine_steps(doc_lines: list[str]) -> None:
    """§5.5「如何准备治理块」必须给出完整推导路径与工具化入口。

    设计稿若只给示例与校验规则（而不给"怎么写出来"），开发同事只能照抄
    示例猜——这是设计稿与可实施规格之间的缺口。
    """
    section = _section_by_title(doc_lines, "如何准备治理块")
    assert section, "缺少 §5.5「如何准备治理块」"

    # 九步推导路径：①..⑨ 必须在**推导表**中各出现且不重复
    # （只数推导表的行首列——样例表（§5.5.5）里也有 ①..⑨，不能混进来）
    derivation = _section_by_title(doc_lines, "推导路径")
    step_rows = re.findall(r"^\|\s*([①②③④⑤⑥⑦⑧⑨])\s*\|", derivation, re.M)
    assert sorted(step_rows) == sorted("①②③④⑤⑥⑦⑧⑨"), (
        f"§5.5.1 推导路径步骤不全或重复：{step_rows}"
    )

    # 机器兜什么 / 人兜什么
    assert "机器" in section and "人" in section, "§5.5 缺少人机分工说明"

    # 工具化入口
    assert "harness governance init" in section, "§5.5 缺少骨架生成命令"
    assert "harness governance check" in section, "§5.5 缺少校验命令"

    # 必须诚实说明"过了检查不等于合规"
    assert re.search(r"不等于合规|≠ *合规", section), (
        "§5.5 未声明'机器兜形式、人兜内容'——"
        "会让读者误以为通过校验即合规"
    )


def test_cli_commands_are_in_implementation_plan(doc_lines: list[str]) -> None:
    """§5.5 承诺的 CLI 命令必须在 §12 实施计划中有对应工作项。"""
    plan = _section_by_title(doc_lines, "实施计划")
    for cmd in ("harness governance init", "harness governance check"):
        assert cmd in plan, f"§12 实施计划缺少 `{cmd}` 工作项"


def test_authoring_sample_matches_governance_example(doc_lines: list[str]) -> None:
    """§5.5.5 样例的推导结果必须与 §5.2 的治理块一致。

    §5.5.5 声称"最终产物即 §5.2 的治理块"。若两者漂移（如 §5.2 加了
    一个步骤而样例没提），开发按样例推导出来的块与示例对不上——
    同一份稿子里出现两个"标准答案"。
    """
    governance = _governance_block("\n".join(doc_lines))
    example_steps = [s["id"] for s in governance.get("workflow", {}).get("steps", [])]
    example_tools = [t["name"] for t in governance.get("tools", [])]

    sample = _section_by_title(doc_lines, "完整样例")
    assert sample, "缺少 §5.5.5 完整样例"

    # 推导表的**结论列**（最后一列）须逐项点名 §5.2 的每个 step / tool。
    # 只看结论列——推导列与其它段落里也会出现这些名字，不能混进来。
    conclusion_col: list[str] = []
    for line in sample.split("\n"):
        if not line.startswith("| ") or "---" in line:
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 3:
            conclusion_col.append(cells[-1])
    conclusions = "\n".join(conclusion_col)

    for step_id in example_steps:
        assert step_id in conclusions, (
            f"§5.5.5 推导表的结论列未点名 §5.2 的步骤 `{step_id}`——"
            f"推导过程与最终示例漂移"
        )

    for tool in example_tools:
        assert tool in conclusions, (
            f"§5.5.5 推导表的结论列未点名 §5.2 的工具 `{tool}`——"
            f"推导过程与最终示例漂移"
        )


def test_rule_count_claims_match_actual(doc_text: str, doc_lines: list[str]) -> None:
    """文中"§N.M 的 K 条"这类计数声明，须与实际规则条数一致。"""
    section = _section_by_title(doc_lines, "校验规则")
    actual = len(
        [
            line
            for line in section.split("\n")
            if re.match(r"^\d+\. ", line)
        ]
    )
    for m in re.finditer(r"§\d+(?:\.\d+)? 的 (\d+) 条", doc_text):
        assert int(m.group(1)) == actual, (
            f"文中声明校验规则有 {m.group(1)} 条，实际 {actual} 条"
        )
    for m in re.finditer(r"§\d+(?:\.\d+)? 全部 (\d+) 条", doc_text):
        assert int(m.group(1)) == actual, (
            f"文中声明校验规则全部 {m.group(1)} 条，实际 {actual} 条"
        )


# --------------------------------------------------------------------------
# 5. 事实核对：文档声称已有的机制须真实存在
# --------------------------------------------------------------------------

def test_claimed_existing_symbols_exist(doc_lines: list[str], sdk_source: str) -> None:
    """文档称"已有 / 现状 / 原样保留"的代码符号，须真实存在于 SDK 源码。

    这一项直接捕获过一类真实缺陷：文档把 `HARNESS_REQUIRE_STRICT=1` 描述为
    "环境变量强制开启"，而实现是 fail-fast 断言（strict 未开则启动失败）。
    """
    claim = re.compile(r"已有|现状|原样保留|现有|沿用现有|直接复用")
    newly_added = re.compile(r"需新增|新增|P0 |治理侧|本方案|待实现")
    symbol = re.compile(r"`([A-Z][A-Za-z0-9]*(?:\.[a-z_]+)?)`|`(mcp_[a-z_]+)`")

    checked = 0
    for i, line in enumerate(doc_lines, 1):
        if not claim.search(line) or newly_added.search(line):
            continue
        for m in symbol.finditer(line):
            name = m.group(1) or m.group(2)
            root = name.split(".")[0]
            if root in NON_SYMBOL_WORDS:
                continue
            checked += 1
            assert root in sdk_source, (
                f"L{i}: 文档称 `{name}` 已有，但 SDK 源码中不存在该符号"
            )
    assert checked > 0, "未检查到任何'已有机制'声明——检查规则可能失效"


def test_all_class_like_symbols_resolve(doc_lines: list[str], sdk_source: str) -> None:
    """文档中所有 CamelCase 符号，要么存在于 SDK 源码，要么是本设计新引入的。

    比上一项更严：覆盖**没有**"已有/现状"措辞的行。设计稿里写错一个类名
    （如 `ToolGateHokX`），实现时会直接找不到——这类笔误必须在稿内拦下。

    新引入的符号必须登记在 `DESIGN_NEW_SYMBOLS`，让"哪些是待实现的"显式化。
    """
    symbol = re.compile(r"`([A-Z][A-Za-z0-9]+)`")
    for i, line in enumerate(doc_lines, 1):
        for m in symbol.finditer(line):
            name = m.group(1)
            if name in DESIGN_NEW_SYMBOLS:
                continue
            if name in NON_SYMBOL_WORDS:
                continue
            assert name in sdk_source, (
                f"L{i}: 符号 `{name}` 在 SDK 源码中不存在，"
                f"也未登记为本设计新引入（DESIGN_NEW_SYMBOLS）——"
                f"疑为笔误，或需先登记为待实现符号"
            )


def test_env_var_claims_match_source(doc_lines: list[str], sdk_source: str) -> None:
    """文档提到的 HARNESS_* 环境变量：要么源码存在，要么明确标注为需新增。

    "需新增"的标注允许出现在**同一章节**内（而非相邻几行）——同一节里
    先声明"该环境变量需新增"、后文再提到它，是正常写法。
    """
    # 计算每行所属的二级章节（`## N. 标题`）
    section_of: list[int] = []
    current = -1
    for line in doc_lines:
        if re.match(r"^## \d+\. ", line):
            current += 1
        section_of.append(current)

    for i, line in enumerate(doc_lines, 1):
        for env in re.findall(r"HARNESS_[A-Z_]+", line):
            if env in sdk_source:
                continue
            sec = section_of[i - 1]
            window = "\n".join(
                doc_lines[j]
                for j in range(len(doc_lines))
                if section_of[j] == sec
            )
            assert re.search(r"新增|增加", window), (
                f"L{i}: 环境变量 `{env}` 在源码中不存在，且其所在章节未标注为需新增——"
                f"开发者照文档配置会静默失效"
            )


def test_new_env_var_names_are_consistent(doc_lines: list[str], sdk_source: str) -> None:
    """待新增的环境变量名，在各处必须一致（§4.3 的说明与 §12 的实施项）。

    这类缺陷只在"名字写错"时出现：§4.3 写 `HARNESS_STRICT`，§12 写成
    `HARNESS_STRIC`，开发者照 §4.3 配置后 §12 实现出来的是另一个名字，
    环境变量静默失效。
    """
    new_envs = {
        env
        for env in re.findall(r"HARNESS_[A-Z_]+", "\n".join(doc_lines))
        if env not in sdk_source
    }
    assert new_envs, "未发现待新增的环境变量——检查规则可能失效"

    for env in sorted(new_envs):
        # 必须用词边界匹配：`HARNESS_STRIC` 是 `HARNESS_STRICT` 的前缀，
        # 子串匹配会让"名字写错"这类缺陷漏检。
        pattern = rf"`?{re.escape(env)}\b"
        occurrences = [
            i for i, line in enumerate(doc_lines, 1)
            if re.search(pattern, line)
        ]
        assert len(occurrences) >= 2, (
            f"待新增环境变量 `{env}` 只出现 1 次（L{occurrences}）——"
            f"须在 §4.3（用法）与 §12（实施项）两处保持一致，避免名字写错"
        )


def test_file_line_references_point_to_real_lines(doc_lines: list[str]) -> None:
    """`file.py:NNN` 形式的引用，行号须在文件范围内。"""
    for i, line in enumerate(doc_lines, 1):
        for m in re.finditer(r"([a-z_/]+\.py):(\d+)(?:-(\d+))?", line):
            path, start, end = m.group(1), int(m.group(2)), m.group(3)
            candidates = [
                p for p in SRC_ROOT.rglob(Path(path).name) if p.name == Path(path).name
            ]
            assert candidates, f"L{i}: 引用的文件不存在：{path}"
            total = len(candidates[0].read_text(encoding="utf-8").split("\n"))
            assert start <= total, f"L{i}: {path}:{start} 超出文件行数 {total}"
            if end:
                assert int(end) <= total, f"L{i}: {path}:{end} 超出文件行数 {total}"


# --------------------------------------------------------------------------
# 6. 机制行为一致性：文档对既有机制的描述须与实现相符
# --------------------------------------------------------------------------

def test_require_strict_env_var_behaviour(doc_lines: list[str]) -> None:
    """`HARNESS_REQUIRE_STRICT=1` 的行为描述须与实现一致。

    实现（`src/harness/sdk/harness.py::_require_strict_if_env`）是
    **fail-fast 断言**：strict 未开时直接抛 `RuntimeError` 拒绝启动。
    它**不是**"强制开启 strict"——单独设置该环境变量会让进程起不来。

    这是一类已发生过的真实缺陷（文档写成"环境变量强制开启"），故单列断言。
    """
    harness_src = (SRC_ROOT / "sdk" / "harness.py").read_text(encoding="utf-8")
    assert "HARNESS_REQUIRE_STRICT" in harness_src
    # 实现是 raise，不是设置 strict=True
    assert "raise RuntimeError" in harness_src, "实现已变，文档描述须同步更新"

    text = "\n".join(doc_lines)
    section = _section_by_title(doc_lines, "模式开关")
    assert re.search(
        r"断言", section
    ), "§4.3 未把 `HARNESS_REQUIRE_STRICT=1` 描述为断言（fail-fast）"

    # 不得出现"该环境变量强制开启治理"这类描述（§4.3 内的每一处提及）
    for i, line in enumerate(doc_lines, 1):
        if "HARNESS_REQUIRE_STRICT" not in line:
            continue
        assert not re.search(r"强制开启|强制打开|强制生效", line), (
            f"L{i}: 文档把 `HARNESS_REQUIRE_STRICT=1` 描述为强制开启——"
            f"实现是 fail-fast 断言（strict 未开则启动失败），"
            f"照此配置会让进程起不来"
        )


def test_traceability_matrix_covers_every_rule(doc_lines: list[str]) -> None:
    """§16.1 可追溯性矩阵必须与 §6.3 的规则**逐条一一对应**。

    没有这张矩阵时，"§6.3 全部 N 条都被测到"只是一句不可验证的声称。
    矩阵存在后，可机器判定：
      - 每条规则在矩阵中恰好出现一次（不漏、不少、不重复）
      - 矩阵引用的 §15 实施项号与 §17 测试组名都真实存在
    """
    matrix = _section_by_title(doc_lines, "可追溯性矩阵")
    assert matrix, "缺少 §16.1 可追溯性矩阵"

    # §6.3 的实际规则号
    rules_sec = _section_by_title(doc_lines, "校验规则")
    rule_nums = [
        int(m.group(1))
        for line in rules_sec.split("\n")
        for m in [re.match(r"^(\d+)\. ", line)]
        if m
    ]
    assert rule_nums, "§6.3 未找到编号规则"

    # 矩阵**主表**：位于"校验归属与测试组"小节之下、第一列为纯数字的行。
    # 后续的"实施项承担的规则"表首列也是数字，必须排除——按小节切片。
    main_part = matrix.split("#### §15 实施项承担的规则")[0]
    matrix_rows = [
        line for line in main_part.split("\n")
        if re.match(r"^\|\s*\d+\s*\|", line)
    ]
    assert matrix_rows, "可追溯性矩阵未找到规则行"

    mapped = []
    for line in matrix_rows:
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        mapped.append(int(cells[0]))

    assert sorted(mapped) == rule_nums, (
        f"矩阵规则号与 §6.3 不一致：缺 {sorted(set(rule_nums) - set(mapped))}，"
        f"多 {sorted(set(mapped) - set(rule_nums))}"
    )
    assert len(mapped) == len(set(mapped)), "矩阵中规则号重复"

    # 矩阵引用的 §15 实施项号必须存在
    plan = _section_by_title(doc_lines, "实施计划")
    plan_nums = {
        int(m.group(1))
        for line in plan.split("\n")
        for m in [re.match(r"^(\d+)\. ", line)]
        if m
    }
    assert plan_nums, "§15 未找到编号实施项"

    test_sec = _section_by_title(doc_lines, "测试策略")
    test_groups = set(re.findall(r"\*\*(.+?)\*\*", test_sec))

    for line in matrix_rows:
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        rule_no, impl_field, test_group = cells[0], cells[3], cells[4]
        for n in re.findall(r"\d+", impl_field):
            assert int(n) in plan_nums, (
                f"规则 {rule_no} 引用了不存在的 §15 实施项 {n}"
            )
        assert test_group in test_groups, (
            f"规则 {rule_no} 引用了不存在的 §17 测试组『{test_group}』"
        )


def test_failure_summary_covers_every_rule_class(doc_lines: list[str]) -> None:
    """§12 失败语义总表必须覆盖 §6.3 的全部规则类别。

    §12 是跨章汇总——若某类编译期失败没进汇总表，实施者只看汇总表会漏掉它。
    """
    summary = _section_by_title(doc_lines, "失败语义总表")
    assert summary, "缺少 §12 失败语义总表"

    rules = _section_by_title(doc_lines, "校验规则")
    rule_nums = [
        int(m.group(1))
        for line in rules.split("\n")
        for m in [re.match(r"^(\d+)\. ", line)]
        if m
    ]
    assert rule_nums, "§6.3 未找到编号规则"

    # 汇总表用区间引用（如"规则 1-13、20-27"），须覆盖全部规则号
    covered: set[int] = set()
    # "规则 1-13、20-27"：区间 + 顿号分隔的多个区间
    for chunk in re.findall(r"规则 ([0-9、\-]+)", summary):
        for part in chunk.split("、"):
            m = re.match(r"^(\d+)-(\d+)$", part)
            if m:
                covered |= set(range(int(m.group(1)), int(m.group(2)) + 1))
            elif part.isdigit():
                covered.add(int(part))
    # "规则 24/25"：并列单条
    for m in re.finditer(r"规则 (\d+)/(\d+)", summary):
        covered.add(int(m.group(1)))
        covered.add(int(m.group(2)))

    missing = sorted(set(rule_nums) - covered)
    assert not missing, (
        f"§12 失败语义总表未覆盖规则 {missing}——汇总表是实施者的唯一入口，不能漏"
    )


def test_failure_summary_points_to_single_definitions(doc_lines: list[str]) -> None:
    """§12 汇总表的"定义处"列必须指向真实章节，且不得指向自身。"""
    summary = _section_by_title(doc_lines, "失败语义总表")
    sections = set()
    for line in doc_lines:
        m = re.match(r"^(#{2,4})\s+(\d+(?:\.\d+)*)(?:\.\s|\s|$)", line)
        if m:
            sections.add(m.group(2))

    for m in re.finditer(r"\| §(\d+(?:\.\d+)?)(?: 步骤 \d+)? \|", summary):
        num = m.group(1)
        assert num in sections, f"§12 汇总表指向不存在的章节 §{num}"
