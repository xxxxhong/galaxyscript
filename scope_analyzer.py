"""
scope_analyzer.py
==================
第二遍遍历：在每个函数体内做作用域分析。

检测内容：
- 未声明就使用的变量
- 函数体内变量重复声明
- 调用未声明的函数
- 函数参数个数不匹配
"""

# from lark import Interpreter, Token, Tree
from lark.visitors import Interpreter
from lark import Token, Tree
from symbol_collector import (
    SymbolTable, SymbolInfo,
    _extract_type_str, _extract_name_from_declarator, _extract_params
)
from typing import Optional


class ScopeError:
    """单个语义错误"""
    def __init__(self, kind: str, message: str, line: int, col: int,
                 context: str = ""):
        self.kind    = kind       # 错误类型标识
        self.message = message    # 人类可读的错误描述
        self.line    = line
        self.col     = col
        self.context = context    # 所在函数名，用于定位

    def to_dict(self) -> dict:
        return {
            'kind':    self.kind,
            'message': self.message,
            'line':    self.line,
            'col':     self.col,
            'context': self.context,
        }

    def __str__(self):
        ctx = f" (in {self.context})" if self.context else ""
        return f"[语义错误] line {self.line}, col {self.col}{ctx}: {self.message}"


# ── 作用域栈 ──────────────────────────────────────────────────────────────────

class ScopeStack:
    """
    维护当前函数内的作用域栈。
    每层是一个 dict: name → SymbolInfo
    """
    def __init__(self, global_table: SymbolTable):
        self.global_table = global_table
        self._stack: list[dict] = []

    def push(self):
        self._stack.append({})

    def pop(self):
        if self._stack:
            self._stack.pop()

    def declare_local(self, info: SymbolInfo) -> Optional[SymbolInfo]:
        """在当前作用域注册局部变量，返回冲突的已有符号或 None"""
        current = self._stack[-1] if self._stack else {}
        existing = current.get(info.name)
        if existing:
            return existing
        if self._stack:
            self._stack[-1][info.name] = info
        return None

    def lookup(self, name: str) -> Optional[SymbolInfo]:
        """从内到外查找，最后查全局符号表"""
        for scope in reversed(self._stack):
            if name in scope:
                return scope[name]
        return self.global_table.lookup(name)

    @property
    def depth(self) -> int:
        return len(self._stack)


# ── 分析器 ────────────────────────────────────────────────────────────────────

class ScopeAnalyzer(Interpreter):
    """
    第二遍遍历：进入每个函数体，做作用域和调用检查。
    """

    def __init__(self, global_table: SymbolTable):
        self.global_table  = global_table
        self.scope         = ScopeStack(global_table)
        self.errors: list[ScopeError] = []
        self._current_func = ""   # 当前所在函数名，用于错误上下文

    # ── 顶层路由 ──────────────────────────────────────────────────────────────

    def translation_unit(self, tree):
        self.visit_children(tree)

    def external_declaration(self, tree):
        self.visit_children(tree)

    def include_directive(self, tree):
        pass

    def native_declaration(self, tree):
        pass   # 已由 SymbolCollector 处理

    def forward_declaration(self, tree):
        pass   # 已由 SymbolCollector 处理

    def declaration(self, tree):
        """
        顶层全局声明：不做作用域检查（已由 SymbolCollector 处理）。
        如果在函数体内被调用，由 _handle_local_declaration 处理。
        """
        pass

    # ── 函数定义：进入函数作用域 ──────────────────────────────────────────────

    def function_definition(self, tree):
        """进入函数：推入新作用域，注册参数，遍历函数体，退出时弹栈。"""
        func_name = "?"
        params = []

        # 提取函数名和参数
        for child in tree.children:
            if isinstance(child, Tree):
                if child.data == 'declarator':
                    result = _extract_name_from_declarator(child)
                    if result:
                        func_name = result[0]
                    for node in child.iter_subtrees():
                        if node.data == 'parameter_type_list':
                            params = _extract_params(node)
                            break

        self._current_func = func_name
        self.scope.push()

        # 把参数注册到函数作用域
        for param in params:
            self.scope.declare_local(param)

        # 进入函数体
        for child in tree.children:
            if isinstance(child, Tree) and child.data == 'compound_statement':
                self._visit_compound(child)

        self.scope.pop()
        self._current_func = ""

    # ── 复合语句（块）：推入新作用域 ─────────────────────────────────────────

    def _visit_compound(self, tree):
        """手动处理 compound_statement，确保正确推栈/弹栈。"""
        self.scope.push()
        for child in tree.children:
            if isinstance(child, Tree):
                self._visit_block_item(child)
        self.scope.pop()

    def _visit_block_item(self, tree):
        """分发函数体内的各种语句和声明。"""
        if not isinstance(tree, Tree):
            return

        if tree.data == 'declaration':
            self._handle_local_declaration(tree)
        elif tree.data == 'declaration_list':
            for child in tree.children:
                if isinstance(child, Tree):
                    self._visit_block_item(child)
        elif tree.data == 'statement_list':
            for child in tree.children:
                if isinstance(child, Tree):
                    self._visit_block_item(child)
        elif tree.data == 'statement':
            self._visit_statement(tree)
        elif tree.data == 'compound_statement':
            self._visit_compound(tree)
        else:
            # 其他情况直接递归
            for child in tree.children:
                if isinstance(child, Tree):
                    self._visit_block_item(child)

    def _visit_statement(self, tree):
        """处理各种语句，重点是含表达式的部分。"""
        if not isinstance(tree, Tree):
            return

        for child in tree.children:
            if isinstance(child, Tree):
                if child.data == 'compound_statement':
                    self._visit_compound(child)
                elif child.data in ('expression_statement', 'expression',
                                    'assignment_expression', 'selection_statement',
                                    'iteration_statement', 'jump_statement'):
                    self._visit_statement(child)
                else:
                    self._check_expression(child)

    # ── 局部变量声明 ──────────────────────────────────────────────────────────

    def _handle_local_declaration(self, tree):
        """处理函数体内的局部变量声明。"""
        type_str = "unknown"
        for child in tree.children:
            if isinstance(child, Tree) and child.data == 'declaration_specifiers':
                type_str = _extract_type_str(child)
                break

        for node in tree.iter_subtrees():
            if node.data == 'init_declarator':
                # 先检查初始化表达式中的引用
                for child in node.children:
                    if isinstance(child, Tree) and child.data == 'initializer':
                        self._check_expression(child)

                # 再注册变量名
                for child in node.children:
                    if isinstance(child, Tree) and child.data == 'declarator':
                        result = _extract_name_from_declarator(child)
                        if result:
                            name, line, col = result
                            info = SymbolInfo(name=name, kind='variable',
                                              type_=type_str, line=line, col=col)
                            existing = self.scope.declare_local(info)
                            if existing:
                                self.errors.append(ScopeError(
                                    kind='duplicate_local',
                                    message=(
                                        f"局部变量 '{name}' 重复声明，"
                                        f"已在第 {existing.line} 行声明过"
                                    ),
                                    line=line, col=col,
                                    context=self._current_func
                                ))

    # ── 表达式检查：变量引用 + 函数调用 ──────────────────────────────────────

    def _check_expression(self, tree):
        """递归检查表达式树中的 IDENTIFIER 引用和函数调用。"""
        if not isinstance(tree, Tree):
            return

        # 函数调用：postfix_expression "(" args ")"
        if tree.data == 'postfix_expression' and len(tree.children) >= 2:
            first = tree.children[0]
            # 检查是否是函数调用形式
            has_arg_list = any(
                isinstance(c, Tree) and c.data == 'argument_expression_list'
                for c in tree.children
            )
            is_empty_call = (
                len(tree.children) == 1 and
                isinstance(first, Tree) and
                first.data == 'primary_expression'
            )
            # 判断有括号的调用
            children_types = [
                c.type if isinstance(c, Token) else (c.data if isinstance(c, Tree) else '')
                for c in tree.children
            ]

            if has_arg_list or 'LPAR' in str(tree):
                self._check_function_call(tree)
                return

        # primary_expression 中的 IDENTIFIER：变量引用
        if tree.data == 'primary_expression':
            for child in tree.children:
                if isinstance(child, Token) and child.type == 'IDENTIFIER':
                    self._check_identifier(child)
            return

        # 递归检查子节点
        for child in tree.children:
            if isinstance(child, Tree):
                self._check_expression(child)

    def _check_identifier(self, token: Token):
        """检查标识符是否已声明。"""
        name = str(token)
        line = token.line or 0
        col  = token.column or 0

        # 跳过已知的内置常量前缀（c_ 开头的常量是 Galaxy 内置的）
        if name.startswith('c_'):
            return

        if not self.scope.lookup(name):
            self.errors.append(ScopeError(
                kind='undeclared',
                message=f"标识符 '{name}' 未声明就使用",
                line=line, col=col,
                context=self._current_func
            ))

    def _check_function_call(self, tree):
        """
        检查函数调用：
        - 函数是否存在
        - 参数个数是否匹配
        """
        # 提取被调用的函数名
        func_name = None
        func_token = None
        arg_count = 0

        for child in tree.children:
            if isinstance(child, Tree):
                if child.data == 'primary_expression':
                    for sub in child.children:
                        if isinstance(sub, Token) and sub.type == 'IDENTIFIER':
                            func_name = str(sub)
                            func_token = sub
                elif child.data == 'argument_expression_list':
                    arg_count = self._count_args(child)
            elif isinstance(child, Tree) and child.data == 'postfix_expression':
                # 递归情况，先检查子调用
                self._check_expression(child)

        if not func_name or not func_token:
            return

        line = func_token.line or 0
        col  = func_token.column or 0

        # 跳过 c_ 开头的常量（不是函数）
        if func_name.startswith('c_'):
            return

        symbol = self.scope.lookup(func_name)
        if symbol is None:
            self.errors.append(ScopeError(
                kind='undeclared_function',
                message=f"调用了未声明的函数 '{func_name}'",
                line=line, col=col,
                context=self._current_func
            ))
            return

        # 检查参数个数（只对有 params 信息的符号检查）
        if symbol.params is not None and symbol.kind in ('function', 'native', 'forward'):
            expected = len(symbol.params)
            if arg_count != expected:
                self.errors.append(ScopeError(
                    kind='arg_count_mismatch',
                    message=(
                        f"函数 '{func_name}' 期望 {expected} 个参数，"
                        f"实际传入 {arg_count} 个"
                    ),
                    line=line, col=col,
                    context=self._current_func
                ))

    def _count_args(self, arg_list_tree) -> int:
        """统计 argument_expression_list 中的参数个数。"""
        if not isinstance(arg_list_tree, Tree):
            return 0
        count = 0
        for node in arg_list_tree.iter_subtrees():
            if node.data == 'assignment_expression':
                # 只计算直接子级的 assignment_expression
                parent_data = getattr(node, '_parent_data', None)
                count += 1
        # 更简单的方法：数逗号数+1
        # argument_expression_list 的左递归结构意味着层数 = 参数数
        return self._count_args_recursive(arg_list_tree)

    def _count_args_recursive(self, tree) -> int:
        """通过左递归结构计算参数个数。"""
        if not isinstance(tree, Tree) or tree.data != 'argument_expression_list':
            return 0
        count = 1  # 当前节点代表一个参数
        for child in tree.children:
            if isinstance(child, Tree) and child.data == 'argument_expression_list':
                count += self._count_args_recursive(child)
                break
        return count
