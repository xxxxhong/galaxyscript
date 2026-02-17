"""
symbol_collector.py
====================
第一遍遍历：从 AST 中收集所有符号声明，建立符号表。

收集内容：
- 全局变量声明
- 函数定义（含参数列表和返回类型）
- native 函数声明
- 前向声明
- struct 类型定义
"""

# from lark import Interpreter, Token, Tree
from lark.visitors import Interpreter
from lark import Token, Tree
from typing import Optional


# ── 数据结构 ──────────────────────────────────────────────────────────────────

class SymbolInfo:
    """单个符号的信息"""
    def __init__(self, name: str, kind: str, type_: str,
                 line: int, col: int, params: Optional[list] = None):
        self.name    = name      # 符号名
        self.kind    = kind      # 'variable' | 'function' | 'native' | 'struct' | 'param'
        self.type_   = type_     # 类型名（字符串）
        self.line    = line      # 声明行号
        self.col     = col       # 声明列号
        self.params  = params    # 函数参数列表 [SymbolInfo, ...]，非函数为 None

    def __repr__(self):
        if self.params is not None:
            param_str = ", ".join(f"{p.type_} {p.name}" for p in self.params)
            return f"{self.kind} {self.type_} {self.name}({param_str}) @{self.line}"
        return f"{self.kind} {self.type_} {self.name} @{self.line}"


class SymbolTable:
    """符号表：全局作用域的所有声明"""
    def __init__(self):
        self.symbols: dict[str, SymbolInfo] = {}   # name → SymbolInfo
        self.structs: dict[str, list] = {}         # struct name → [field SymbolInfo]

    def declare(self, info: SymbolInfo) -> Optional[SymbolInfo]:
        """
        尝试注册符号。
        如果已存在同名符号，返回已有的 SymbolInfo（用于报告重复声明）。
        否则注册并返回 None。
        """
        existing = self.symbols.get(info.name)
        # forward_declaration 和 function_definition 允许共存（前向声明后再定义）
        if existing:
            if existing.kind == 'forward' and info.kind == 'function':
                self.symbols[info.name] = info   # 用函数定义覆盖前向声明
                return None
            if existing.kind == 'function' and info.kind == 'forward':
                return None   # 已有定义，忽略前向声明
        if not existing:
            self.symbols[info.name] = info
            return None
        return existing

    def lookup(self, name: str) -> Optional[SymbolInfo]:
        return self.symbols.get(name)

    def declare_struct(self, name: str, fields: list):
        self.structs[name] = fields


# ── 辅助函数 ──────────────────────────────────────────────────────────────────

def _get_token_line_col(token) -> tuple:
    """安全获取 token 的行列号"""
    if isinstance(token, Token):
        return (token.line or 0, token.column or 0)
    return (0, 0)


def _extract_type_str(type_specifier_tree) -> str:
    """
    从 type_specifier 或 declaration_specifiers 子树中提取类型名字符串。
    """
    if isinstance(type_specifier_tree, Token):
        return str(type_specifier_tree)

    if not isinstance(type_specifier_tree, Tree):
        return "unknown"

    # 递归找第一个有意义的 token
    for child in type_specifier_tree.children:
        if isinstance(child, Token):
            # 跳过 storage class 和 qualifier
            if child.type in ('CONST', 'STATIC', 'TYPEDEF'):
                continue
            return str(child)
        if isinstance(child, Tree):
            result = _extract_type_str(child)
            if result != "unknown":
                return result
    return "unknown"


def _extract_name_from_declarator(declarator_tree) -> Optional[tuple]:
    """
    从 declarator / direct_declarator 子树中提取变量名 token。
    返回 (name_str, line, col) 或 None。
    """
    if not isinstance(declarator_tree, Tree):
        return None

    for child in declarator_tree.children:
        if isinstance(child, Token) and child.type == 'IDENTIFIER':
            return (str(child), child.line or 0, child.column or 0)
        if isinstance(child, Tree):
            result = _extract_name_from_declarator(child)
            if result:
                return result
    return None


def _extract_params(parameter_type_list_tree) -> list:
    """
    从 parameter_type_list 子树中提取参数列表。
    返回 [SymbolInfo, ...]
    """
    params = []
    if not isinstance(parameter_type_list_tree, Tree):
        return params

    for node in parameter_type_list_tree.iter_subtrees():
        if node.data == 'parameter_declaration':
            type_str = "unknown"
            name_str = "?"
            line, col = 0, 0

            for child in node.children:
                if isinstance(child, Tree):
                    if child.data == 'declaration_specifiers':
                        type_str = _extract_type_str(child)
                    elif child.data in ('declarator', 'direct_declarator'):
                        result = _extract_name_from_declarator(child)
                        if result:
                            name_str, line, col = result
                elif isinstance(child, Token):
                    type_str = str(child)

            params.append(SymbolInfo(
                name=name_str, kind='param',
                type_=type_str, line=line, col=col
            ))
    return params


# ── 收集器 ────────────────────────────────────────────────────────────────────

class SymbolCollector(Interpreter):
    """
    第一遍遍历：只关注顶层声明，建立全局符号表。
    不进入函数体内部（函数体内的局部变量由 ScopeAnalyzer 处理）。
    """

    def __init__(self):
        self.table = SymbolTable()
        self.errors: list[dict] = []   # 收集重复声明错误

    # ── 全局变量声明 ──────────────────────────────────────────────────────────

    def declaration(self, tree):
        """
        处理全局变量声明。
        只在顶层调用，不递归进入函数体。
        """
        type_str = "unknown"
        for child in tree.children:
            if isinstance(child, Tree) and child.data == 'declaration_specifiers':
                type_str = _extract_type_str(child)
                break

        # 遍历 init_declarator_list 提取所有变量名
        for node in tree.iter_subtrees():
            if node.data == 'init_declarator':
                for child in node.children:
                    if isinstance(child, Tree) and child.data == 'declarator':
                        result = _extract_name_from_declarator(child)
                        if result:
                            name, line, col = result
                            info = SymbolInfo(name=name, kind='variable',
                                              type_=type_str, line=line, col=col)
                            existing = self.table.declare(info)
                            if existing:
                                self.errors.append({
                                    'kind': 'duplicate_declaration',
                                    'name': name,
                                    'line': line,
                                    'col': col,
                                    'prev_line': existing.line,
                                    'message': (
                                        f"变量 '{name}' 重复声明（第{line}行），"
                                        f"已在第{existing.line}行声明过"
                                    )
                                })

    # ── 函数定义 ──────────────────────────────────────────────────────────────

    def function_definition(self, tree):
        """收集函数定义的签名，不进入函数体。"""
        type_str = "unknown"
        name, line, col = "?", 0, 0
        params = []

        for child in tree.children:
            if isinstance(child, Tree):
                if child.data == 'declaration_specifiers':
                    type_str = _extract_type_str(child)
                elif child.data == 'declarator':
                    result = _extract_name_from_declarator(child)
                    if result:
                        name, line, col = result
                    # 提取参数
                    for node in child.iter_subtrees():
                        if node.data == 'parameter_type_list':
                            params = _extract_params(node)
                            break

        info = SymbolInfo(name=name, kind='function',
                          type_=type_str, line=line, col=col, params=params)
        existing = self.table.declare(info)
        if existing and existing.kind not in ('forward', 'function'):
            self.errors.append({
                'kind': 'duplicate_declaration',
                'name': name,
                'line': line,
                'col': col,
                'prev_line': existing.line,
                'message': (
                    f"函数 '{name}' 与已有符号重名（第{line}行），"
                    f"已在第{existing.line}行声明过"
                )
            })

        # 不递归进入函数体（compound_statement）
        # Interpreter 不会自动递归，无需显式阻止

    # ── native 函数声明 ───────────────────────────────────────────────────────

    def native_declaration(self, tree):
        type_str = "unknown"
        name, line, col = "?", 0, 0
        params = []

        for child in tree.children:
            if isinstance(child, Tree):
                if child.data == 'declaration_specifiers':
                    type_str = _extract_type_str(child)
                elif child.data == 'declarator':
                    result = _extract_name_from_declarator(child)
                    if result:
                        name, line, col = result
                    for node in child.iter_subtrees():
                        if node.data == 'parameter_type_list':
                            params = _extract_params(node)
                            break

        info = SymbolInfo(name=name, kind='native',
                          type_=type_str, line=line, col=col, params=params)
        self.table.declare(info)   # native 函数不报重复（可能多文件声明）

    # ── 前向声明 ──────────────────────────────────────────────────────────────

    def forward_declaration(self, tree):
        type_str = "unknown"
        name, line, col = "?", 0, 0
        params = []

        for child in tree.children:
            if isinstance(child, Tree):
                if child.data == 'declaration_specifiers':
                    type_str = _extract_type_str(child)
                elif child.data == 'declarator':
                    result = _extract_name_from_declarator(child)
                    if result:
                        name, line, col = result
                    for node in child.iter_subtrees():
                        if node.data == 'parameter_type_list':
                            params = _extract_params(node)
                            break

        info = SymbolInfo(name=name, kind='forward',
                          type_=type_str, line=line, col=col, params=params)
        self.table.declare(info)

    # ── struct 定义 ───────────────────────────────────────────────────────────

    def struct_or_union_specifier(self, tree):
        name = None
        fields = []

        for child in tree.children:
            if isinstance(child, Token) and child.type == 'IDENTIFIER':
                name = str(child)
            elif isinstance(child, Tree) and child.data == 'struct_declaration_list':
                for node in child.iter_subtrees():
                    if node.data == 'struct_declaration':
                        type_str = "unknown"
                        for sub in node.children:
                            if isinstance(sub, Tree) and sub.data == 'specifier_qualifier_list':
                                type_str = _extract_type_str(sub)
                                break
                        for sub in node.iter_subtrees():
                            if sub.data == 'declarator':
                                result = _extract_name_from_declarator(sub)
                                if result:
                                    fname, fline, fcol = result
                                    fields.append(SymbolInfo(
                                        name=fname, kind='field',
                                        type_=type_str, line=fline, col=fcol
                                    ))

        if name:
            self.table.declare_struct(name, fields)
            info = SymbolInfo(name=name, kind='struct',
                              type_='struct', line=0, col=0)
            self.table.declare(info)

    # ── include / translation_unit：正常递归 ──────────────────────────────────

    def translation_unit(self, tree):
        self.visit_children(tree)

    def external_declaration(self, tree):
        self.visit_children(tree)

    def include_directive(self, tree):
        pass   # 不处理 include
