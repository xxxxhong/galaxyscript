"""
GalaxyCC 分析流水线
====================
将词法分析 → 语法分析 → AST 转换 → 语义分析串联为一个高层接口。
"""

from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from lark import Lark, exceptions as lark_exc

from .tree.transformer import GalaxyTransformer, TranslationUnit
from .semantic.analyzer import GalaxyAnalyzer
from .semantic.natives import NativeLoader, COMMON_NATIVES
from .semantic.symbol import SymbolTable
from galaxycc.error import DiagnosticBag, SemanticError


# ─── 结果对象 ──────────────────────────────────────────────────────────────────

@dataclass
class FrontendResult:
    """分析流水线的输出"""
    ast:          Optional[TranslationUnit]   # None 表示语法分析失败
    diags:        DiagnosticBag
    symbol_table: Optional[SymbolTable]       # None 表示未进入语义分析

    @property
    def success(self) -> bool:
        return self.ast is not None and not self.diags.has_errors


# ─── 主流水线 ─────────────────────────────────────────────────────────────────

class GalaxyFrontend:
    """
    Galaxy Script 编译器前端。

    主要流程：
      1. Lark 解析（词法 + 语法）→ CST
      2. GalaxyTransformer   → AST
      3. GalaxyAnalyzer      → 类型注解 + 符号表

    用法::

        frontend = GalaxyFrontend(grammar_file="galaxy.lark")
        frontend.load_natives_common()      # 加载常用内置函数
        result = frontend.process_file("mymap.galaxy")
        print(result.diags.report())
    """

    def __init__(self, grammar_file: str | Path = None, grammar_text: str = None):
        """
        Args:
            grammar_file: .lark 文件路径（与 grammar_text 二选一）
            grammar_text: 直接传入 grammar 字符串
        """
        if grammar_file is None and grammar_text is None:
            raise ValueError("必须提供 grammar_file 或 grammar_text")

        self._parser = Lark.open(
            str(grammar_file),
            parser='earley',          # 或 'lalr'（需要 grammar 无歧义）
            # propagate_positions=True,
            ambiguity='resolve',
        ) if grammar_file else Lark(
            grammar_text,
            parser='earley',
            # propagate_positions=True,
            ambiguity='resolve',
        )

        self._transformer = GalaxyTransformer()
        self._native_loader = NativeLoader()

    # ── 加载 native 函数 ───────────────────────────────────────────────────

    def load_natives_common(self):
        """加载内置的常用 native 函数定义（无需外部文件）"""
        self._native_loader.load_from_dict(COMMON_NATIVES)

    def load_natives_from_file(self, path: str | Path) -> int:
        """从 .galaxy native 声明文件加载，返回加载的函数数量"""
        return self._native_loader.load_from_file(path)

    def load_natives_from_dict(self, definitions: dict):
        """从手工字典加载（格式见 NativeLoader.load_from_dict）"""
        self._native_loader.load_from_dict(definitions)

    # ── 分析入口 ───────────────────────────────────────────────────────────

    def process_file(self, path: str | Path) -> FrontendResult:
        """分析单个 .galaxy 文件"""
        path = Path(path)
        if not path.exists():
            diag = DiagnosticBag()
            diag.error(f"文件不存在: {path}")
            return FrontendResult(ast=None, diags=diag, symbol_table=None)
        source = path.read_text(encoding='utf-8', errors='replace')
        return self.process_string(source, source_name=str(path))

    def process_string(self, source: str, source_name: str = '<input>') -> FrontendResult:
        """
        分析源码字符串，返回 FrontendResult。
        即使有错误也尽量完成分析（错误恢复模式）。
        """
        diag = DiagnosticBag()

        # ── Step 1: 词法 + 语法分析 ─────────────────────────────────────
        try:
            cst = self._parser.parse(source)
        except lark_exc.UnexpectedCharacters as e:
            diag.error(
                f"词法错误：意外字符 '{e.char}' at {e.line}:{e.column}",
                hint=f"期望：{e.allowed}")
            return FrontendResult(ast=None, diags=diag, symbol_table=None)
        except lark_exc.UnexpectedToken as e:
            diag.error(
                f"语法错误：意外 token '{e.token}' (类型 {e.token.type}) "
                f"at {e.line}:{e.column}",
                hint=f"期望：{e.expected}")
            return FrontendResult(ast=None, diags=diag, symbol_table=None)
        except lark_exc.ParseError as e:
            diag.error(f"语法分析失败: {e}")
            return FrontendResult(ast=None, diags=diag, symbol_table=None)

        # ── Step 2: CST → AST ───────────────────────────────────────────
        try:
            ast = self._transformer.transform(cst)
        except Exception as e:
            diag.error(f"AST 转换失败（可能是 Transformer 未完整覆盖某规则）: {e}")
            return FrontendResult(ast=None, diags=diag, symbol_table=None)

        if not isinstance(ast, TranslationUnit):
            diag.error(f"AST 根节点类型错误：{type(ast).__name__}")
            return FrontendResult(ast=None, diags=diag, symbol_table=None)

        # ── Step 3: 语义分析 ─────────────────────────────────────────────
        try:
            analyzer = GalaxyAnalyzer(
                native_builtins=self._native_loader.get_builtins()
            )
            sem_diag = analyzer.analyze(ast)
            # 合并诊断
            for d in sem_diag:
                diag._diags.append(d)
        except SemanticError as e:
            diag.error(f"语义分析内部错误（请报告 bug）: {e}")
            return FrontendResult(ast=ast, diags=diag, symbol_table=None)
        except Exception as e:
            diag.error(f"语义分析崩溃（请报告 bug）: {type(e).__name__}: {e}")
            return FrontendResult(ast=ast, diags=diag, symbol_table=None)

        return FrontendResult(
            ast=ast,
            diags=diag,
            symbol_table=analyzer.table,
        )

    # ── 调试工具 ───────────────────────────────────────────────────────────

    def parse_only(self, source: str):
        """仅做语法分析，返回 Lark Tree（调试用）"""
        return self._parser.parse(source)

    def transform_only(self, source: str):
        """语法分析 + AST 转换，不做语义分析（调试用）"""
        cst = self._parser.parse(source)
        return self._transformer.transform(cst)
