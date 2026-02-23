"""
Galaxy Script 语义错误体系
===========================
收集所有语义错误，支持"继续分析模式"（报错后不立即崩溃，
尽量多检测错误）。
"""

from dataclasses import dataclass, field
from enum import Enum, auto


class ErrorSeverity(Enum):
    WARNING = auto()
    ERROR   = auto()


@dataclass
class SemanticDiag:
    """一条诊断信息"""
    severity: ErrorSeverity
    message:  str
    line:     int = -1
    column:   int = -1
    hint:     str = ''       # 可选修复提示

    def __str__(self):
        loc = f"{self.line}:{self.column}" if self.line > 0 else '?:?'
        tag = self.severity.name
        base = f"[{tag}] {loc}  {self.message}"
        if self.hint:
            base += f"\n  hint: {self.hint}"
        return base


class SemanticError(Exception):
    """单次立即抛出（仅在 fail-fast 模式使用）"""
    def __init__(self, message, line=-1, column=-1):
        super().__init__(message)
        self.line   = line
        self.column = column


class DiagnosticBag:
    """
    诊断信息收集袋。
    语义分析器将错误/警告加入此袋，
    分析结束后统一输出，而不是每遇一个错误立即中断。
    """
    def __init__(self):
        self._diags: list[SemanticDiag] = []

    # ── 添加诊断 ────────────────────────────────────────────────────────────

    def error(self, message: str, node=None, hint: str = ''):
        line, column = _loc(node)
        self._diags.append(SemanticDiag(ErrorSeverity.ERROR, message, line, column, hint))

    def warning(self, message: str, node=None, hint: str = ''):
        line, column = _loc(node)
        self._diags.append(SemanticDiag(ErrorSeverity.WARNING, message, line, column, hint))

    # ── 查询 ────────────────────────────────────────────────────────────────

    @property
    def has_errors(self) -> bool:
        return any(d.severity == ErrorSeverity.ERROR for d in self._diags)

    @property
    def count(self) -> int:
        return len(self._diags)

    @property
    def errors(self):
        return [d for d in self._diags if d.severity == ErrorSeverity.ERROR]

    @property
    def warnings(self):
        return [d for d in self._diags if d.severity == ErrorSeverity.WARNING]

    def __iter__(self):
        return iter(self._diags)

    def __len__(self):
        return len(self._diags)

    # ── 输出 ────────────────────────────────────────────────────────────────

    def report(self) -> str:
        if not self._diags:
            return "No diagnostics."
        lines = [str(d) for d in sorted(self._diags, key=lambda d: (d.line, d.column))]
        summary = (f"\n{'─'*60}\n"
                   f"{len(self.errors)} error(s), {len(self.warnings)} warning(s)")
        return '\n'.join(lines) + summary

    def raise_if_errors(self):
        if self.has_errors:
            raise SemanticError(f"{len(self.errors)} semantic error(s) found.\n" +
                                '\n'.join(str(d) for d in self.errors))


def _loc(node) -> tuple[int, int]:
    """从 Lark Tree/Token 节点提取行列信息"""
    if node is None:
        return -1, -1
    # Lark Token
    if hasattr(node, 'line') and hasattr(node, 'column'):
        return getattr(node, 'line', -1), getattr(node, 'column', -1)
    # Lark Tree with meta
    if hasattr(node, 'meta'):
        meta = node.meta
        return getattr(meta, 'line', -1), getattr(meta, 'column', -1)
    return -1, -1
