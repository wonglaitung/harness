"""治理块条件表达式：受限子集的解析与求值。

沿用 GitHub Actions 的表达式语法，但**只取安全子集**（设计稿 §6.3 规则 14-19）：

允许的运算符：``== != < <= > >= && || !``
允许的函数：``contains() startsWith() endsWith() format() join() toJSON() fromJSON()``
允许的上下文：``steps.<id>.outputs.<name>`` / ``steps.<id>.outcome`` /
``steps.<id>.conclusion`` / ``env.<name>``

**禁止**（规则 15）：``github`` / ``secrets`` / ``matrix`` / ``runner`` 上下文，
以及 ``hashFiles()``（读文件系统＝能力泄漏）。

设计约束：
- 产出（outputs）**全为字符串**，比较须写 ``== 'true'``（规则 16）。
  这是 GHA 的既有约定，不是本方案发明的——保持一致可让开发者不必改习惯。
- 整个表达式必须被 ``${{ }}`` 包裹（规则 17），否则 YAML 里的 ``!`` 会被当标签。
- 求值**无副作用、纯函数**：guard 失败不抛异常，而是返回"无法判定"，
  由调用方按 fail-closed 处理（§12.1）。
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

# 允许的函数（规则 14）
ALLOWED_FUNCTIONS = frozenset(
    {
        "contains",
        "startsWith",
        "endsWith",
        "format",
        "join",
        "toJSON",
        "fromJSON",
    }
)

# 禁止的上下文根（规则 15）
FORBIDDEN_CONTEXT_ROOTS = frozenset(
    {"github", "secrets", "matrix", "runner", "needs", "jobs", "inputs", "vars"}
)

# 允许的上下文根
ALLOWED_CONTEXT_ROOTS = frozenset({"steps", "env"})

# 表达式里禁止出现的函数（hashFiles 读文件系统＝能力泄漏）
FORBIDDEN_FUNCTIONS = frozenset({"hashFiles"})


class ExpressionError(Exception):
    """表达式语法错误或使用了被禁止的构造。"""


class ExpressionContext:
    """表达式求值上下文。

    由调用方构造，只暴露允许的上下文：`steps` 与 `env`。
    """

    def __init__(
        self,
        steps: dict[str, dict[str, Any]] | None = None,
        env: dict[str, Any] | None = None,
    ) -> None:
        # steps: {step_id: {"outputs": {...}, "outcome": str, "conclusion": str}}
        self._steps = steps or {}
        self._env = env or {}

    def lookup(self, path: str) -> Any:
        """按点路径读取上下文值；路径不存在时抛 `ExpressionError`。"""
        parts = path.split(".")
        if not parts or parts[0] not in ALLOWED_CONTEXT_ROOTS:
            raise ExpressionError(f"不允许的上下文 `{path}`")
        if parts[0] == "env":
            if len(parts) != 2:
                raise ExpressionError(f"env 路径只支持一级：{path}")
            if parts[1] not in self._env:
                raise ExpressionError(f"env 中不存在 `{parts[1]}`")
            return self._env[parts[1]]
        # steps.<id>.<attr>
        if len(parts) < 3:
            raise ExpressionError(f"steps 路径需要三级：{path}")
        step_id, attr = parts[1], parts[2]
        if step_id not in self._steps:
            raise ExpressionError(f"steps 中不存在 `{step_id}`")
        step = self._steps[step_id]
        if attr == "outcome":
            return step.get("outcome", "")
        if attr == "conclusion":
            return step.get("conclusion", "")
        if attr == "outputs":
            if len(parts) != 4:
                raise ExpressionError(f"outputs 路径需要四级：{path}")
            outputs = step.get("outputs", {})
            if parts[3] not in outputs:
                raise ExpressionError(f"step `{step_id}` 没有产出 `{parts[3]}`")
            return outputs[parts[3]]
        raise ExpressionError(f"steps 中不支持的属性 `{attr}`")


# --------------------------------------------------------------------------
# 词法
# --------------------------------------------------------------------------

_TOKEN_RE = re.compile(
    r"""
    \s*(?:
        (?P<string>'(?:[^']|'')*'|"(?:[^"]|"")*")
      | (?P<number>-?\d+(?:\.\d+)?)
      | (?P<op>==|!=|<=|>=|&&|\|\||[-+*/<>!(),.\[\]])
      | (?P<ident>[A-Za-z_][A-Za-z0-9_]*)
      | (?P<lparen>\()
      | (?P<rparen>\))
      | (?P<lbracket>\[)
      | (?P<rbracket>\])
    )
    """,
    re.VERBOSE,
)


@dataclass(frozen=True)
class Token:
    kind: str
    value: str


def _tokenize(source: str) -> list[Token]:
    tokens: list[Token] = []
    pos = 0
    while pos < len(source):
        if source[pos].isspace():
            pos += 1
            continue
        m = _TOKEN_RE.match(source, pos)
        if not m or m.end() == m.start():
            raise ExpressionError(f"无法解析的字符：{source[pos]!r}")
        kind = m.lastgroup or ""
        value = m.group(kind)
        tokens.append(Token(kind, value))
        pos = m.end()
    return tokens


# --------------------------------------------------------------------------
# 语法树
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Literal:
    value: Any


@dataclass(frozen=True)
class ContextRef:
    path: str


@dataclass(frozen=True)
class Unary:
    op: str
    operand: Any


@dataclass(frozen=True)
class Binary:
    op: str
    left: Any
    right: Any


@dataclass(frozen=True)
class Call:
    name: str
    args: tuple[Any, ...]


# --------------------------------------------------------------------------
# 解析
# --------------------------------------------------------------------------

_COMPARISON_OPS = ("==", "!=", "<=", ">=", "<", ">")
_LOGICAL_OPS = ("&&", "||")


class _Parser:
    def __init__(self, tokens: list[Token]) -> None:
        self._tokens = tokens
        self._pos = 0

    def _peek(self) -> Token | None:
        return self._tokens[self._pos] if self._pos < len(self._tokens) else None

    def _next(self) -> Token:
        token = self._peek()
        if token is None:
            raise ExpressionError("表达式意外结束")
        self._pos += 1
        return token

    def _expect(self, value: str) -> None:
        token = self._next()
        if token.value != value:
            raise ExpressionError(f"期望 `{value}`，实际是 `{token.value}`")

    def parse(self) -> Any:
        node = self._parse_or()
        if self._pos != len(self._tokens):
            raise ExpressionError("表达式尾部有多余内容")
        return node

    def _parse_or(self) -> Any:
        node = self._parse_and()
        while True:
            token = self._peek()
            if token is None or token.value != "||":
                return node
            self._next()
            node = Binary("||", node, self._parse_and())

    def _parse_and(self) -> Any:
        node = self._parse_comparison()
        while True:
            token = self._peek()
            if token is None or token.value != "&&":
                return node
            self._next()
            node = Binary("&&", node, self._parse_comparison())

    def _parse_comparison(self) -> Any:
        node = self._parse_unary()
        token = self._peek()
        if token is not None and token.value in _COMPARISON_OPS:
            self._next()
            return Binary(token.value, node, self._parse_unary())
        return node

    def _parse_unary(self) -> Any:
        token = self._peek()
        if token is not None and token.value == "!":
            self._next()
            return Unary("!", self._parse_unary())
        if token is not None and token.value == "-":
            self._next()
            operand = self._parse_unary()
            if isinstance(operand, Literal) and isinstance(operand.value, (int, float)):
                return Literal(-operand.value)
            return Unary("-", operand)
        return self._parse_primary()

    def _parse_primary(self) -> Any:
        token = self._next()
        if token.kind == "string":
            value = token.value[1:-1]
            quote = token.value[0]
            value = value.replace("''", "'") if quote == "'" else value.replace('""', '"')
            return Literal(value)
        if token.kind == "number":
            numeric = float(token.value)
            return Literal(int(numeric) if numeric.is_integer() else numeric)
        if token.kind == "lparen":
            node = self._parse_or()
            self._expect(")")
            return node
        if token.kind == "lbracket":
            items: list[Any] = []
            while True:
                nxt = self._peek()
                if nxt is not None and nxt.value == "]":
                    self._next()
                    break
                items.append(self._parse_or())
                nxt = self._peek()
                if nxt is not None and nxt.value == ",":
                    self._next()
            return Call("__list__", tuple(items))
        if token.kind == "ident":
            name = token.value
            if name in FORBIDDEN_CONTEXT_ROOTS:
                raise ExpressionError(f"禁止使用上下文 `{name}`")
            if name in FORBIDDEN_FUNCTIONS:
                raise ExpressionError(f"禁止使用函数 `{name}`")
            nxt = self._peek()
            if nxt is not None and nxt.value == "(":
                self._next()
                args: list[Any] = []
                while True:
                    after = self._peek()
                    if after is not None and after.value == ")":
                        self._next()
                        break
                    args.append(self._parse_or())
                    after = self._peek()
                    if after is not None and after.value == ",":
                        self._next()
                if name not in ALLOWED_FUNCTIONS:
                    raise ExpressionError(f"不允许的函数 `{name}`")
                return Call(name, tuple(args))
            # 上下文路径：ident ('.' ident)*
            path = [name]
            while True:
                nxt = self._peek()
                if nxt is not None and nxt.value == ".":
                    self._next()
                    part = self._next()
                    if part.kind not in ("ident", "number"):
                        raise ExpressionError(f"路径片段无效：{part.value}")
                    path.append(part.value)
                else:
                    break
            if path[0] not in ALLOWED_CONTEXT_ROOTS:
                raise ExpressionError(f"不允许的上下文 `{path[0]}`")
            return ContextRef(".".join(path))
        raise ExpressionError(f"无法解析的记号 `{token.value}`")


def _strip_wrappers(source: str) -> str:
    """剥掉 `${{ ... }}` 包裹。

    规则 17 要求整个表达式被包裹；未包裹时这里不报错，由调用方
    （validation）单独检查。
    """
    text = source.strip()
    if text.startswith("${{") and text.endswith("}}"):
        return text[3:-2].strip()
    return text


def parse_expression(source: str) -> Any:
    """解析表达式并返回语法树。

    抛 `ExpressionError` 表示语法错误或使用了被禁止的构造。
    """
    if not isinstance(source, str):
        raise ExpressionError("表达式必须是字符串")
    inner = _strip_wrappers(source)
    if not inner:
        raise ExpressionError("表达式为空")
    return _Parser(_tokenize(inner)).parse()


def is_wrapped(source: str) -> bool:
    """表达式是否被 `${{ ... }}` 完整包裹（规则 17）。"""
    text = source.strip()
    return text.startswith("${{") and text.endswith("}}")


# --------------------------------------------------------------------------
# 求值
# --------------------------------------------------------------------------


def _to_number(value: Any) -> float:
    if isinstance(value, bool):
        raise ExpressionError("布尔值不能参与数值比较")
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError as exc:
            raise ExpressionError(f"无法把 {value!r} 当作数值比较") from exc
    raise ExpressionError(f"无法把 {value!r} 当作数值比较")


def _compare(op: str, left: Any, right: Any) -> bool:
    """比较。

    ``==`` / ``!=`` 是**严格相等**（字符串产出按字符串比，不做数字转换）——
    GHA 的 ``==`` 语义如此，保持一致让开发者不必改习惯。
    顺序比较（``< <= > >=``）才做数字转换：产出全为字符串，
    数值比较必须显式转换（§6.3.3 规则 16）。
    """
    if op == "==":
        return bool(left == right)
    if op == "!=":
        return bool(left != right)
    lhs = _to_number(left)
    rhs = _to_number(right)
    if op == "<":
        return bool(lhs < rhs)
    if op == "<=":
        return bool(lhs <= rhs)
    if op == ">":
        return bool(lhs > rhs)
    return bool(lhs >= rhs)


def evaluate(node: Any, ctx: ExpressionContext) -> Any:
    """对语法树求值。抛 `ExpressionError` 表示无法判定。"""
    if isinstance(node, Literal):
        return node.value
    if isinstance(node, ContextRef):
        return ctx.lookup(node.path)
    if isinstance(node, Unary):
        value = evaluate(node.operand, ctx)
        if node.op == "!":
            if isinstance(value, str):
                # GHA 语义：非空字符串为真
                return not (value != "" and value.lower() != "false")
            return not bool(value)
        if node.op == "-":
            return -_to_number(value)
        raise ExpressionError(f"未知的一元运算 `{node.op}`")
    if isinstance(node, Binary):
        if node.op == "&&":
            return bool(evaluate(node.left, ctx)) and bool(
                evaluate(node.right, ctx)
            )
        if node.op == "||":
            return bool(evaluate(node.left, ctx)) or bool(
                evaluate(node.right, ctx)
            )
        return _compare(node.op, evaluate(node.left, ctx), evaluate(node.right, ctx))
    if isinstance(node, Call):
        name = node.name
        if name == "__list__":
            return [evaluate(a, ctx) for a in node.args]
        args = [evaluate(a, ctx) for a in node.args]
        if name == "contains":
            if len(args) != 2:
                raise ExpressionError("contains() 需要 2 个参数")
            haystack, needle = args
            if isinstance(haystack, str):
                return str(needle) in haystack
            if isinstance(haystack, list):
                return needle in haystack
            raise ExpressionError("contains() 的第一个参数必须是字符串或列表")
        if name == "startsWith":
            if len(args) != 2:
                raise ExpressionError("startsWith() 需要 2 个参数")
            return str(args[0]).startswith(str(args[1]))
        if name == "endsWith":
            if len(args) != 2:
                raise ExpressionError("endsWith() 需要 2 个参数")
            return str(args[0]).endswith(str(args[1]))
        if name == "format":
            if not args:
                raise ExpressionError("format() 至少需要 1 个参数")
            return str(args[0]).format(*args[1:])
        if name == "join":
            if len(args) != 2:
                raise ExpressionError("join() 需要 2 个参数")
            sep, items = args
            if not isinstance(items, list):
                raise ExpressionError("join() 的第二个参数必须是列表")
            return str(sep).join(str(i) for i in items)
        if name == "toJSON":
            if len(args) != 1:
                raise ExpressionError("toJSON() 需要 1 个参数")
            return json.dumps(args[0], ensure_ascii=False)
        if name == "fromJSON":
            if len(args) != 1:
                raise ExpressionError("fromJSON() 需要 1 个参数")
            try:
                return json.loads(str(args[0]))
            except (TypeError, ValueError) as exc:
                raise ExpressionError(f"无法解析 JSON：{args[0]!r}") from exc
        raise ExpressionError(f"不允许的函数 `{name}`")
    raise ExpressionError(f"未知的语法树节点 {type(node).__name__}")


def evaluate_expression(source: str, ctx: ExpressionContext) -> bool:
    """求值为布尔。

    抛 `ExpressionError` 表示**无法判定**——调用方据此按 fail-closed 处理
    （设计稿 §12.1：条件求值失败 → 视为 `if` 为假并记 `guard_unresolved`）。
    """
    result = evaluate(parse_expression(source), ctx)
    if isinstance(result, str):
        # GHA 语义：非空字符串为真
        return result != "" and result.lower() != "false"
    return bool(result)
