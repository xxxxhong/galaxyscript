"""
类型推导最小完整示例
====================

演示语言支持：
    - 4种基本类型：int, float, bool, string
    - 变量声明与初始化
    - 二元运算（算术、比较）
    - 函数定义与调用
    - if 语句

整体流程：
    源码
     │
     ▼
    Lark 解析 → AST
     │
     ▼
    Pass 1: SymbolCollector   收集函数签名（解决前向引用）
     │
     ▼
    Pass 2: TypeInferencer    遍历 AST，对每个表达式推导类型，报告类型错误

运行：
    pip install lark
    python type_inference_demo.py
"""

from lark import Lark, Token, Tree
from lark.visitors import Interpreter
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum, auto


# ═══════════════════════════════════════════════════════════════════════════════
# 第一部分：类型系统
# 类型是推导的基本单元，必须先设计清楚
# ═══════════════════════════════════════════════════════════════════════════════

class BaseType(Enum):
    INT    = "int"
    FLOAT  = "float"
    BOOL   = "bool"
    STRING = "string"
    VOID   = "void"


@dataclass(frozen=True)
class Type:
    """
    类型对象。frozen=True 使它可以作为 dict key，也方便比较。

    用 dataclass 而不是普通类，是因为推导结果需要大量比较（== 操作）。
    """
    base: BaseType
    # 如果以后要支持数组：dimensions: tuple = ()
    # 如果以后要支持结构体：struct_name: str = ""

    def __str__(self):
        return self.base.value

    @property
    def is_numeric(self):
        return self.base in (BaseType.INT, BaseType.FLOAT)

    @property
    def is_unknown(self):
        return self is T_UNKNOWN


# 类型单例，整个程序共用，方便用 is 比较
T_INT    = Type(BaseType.INT)
T_FLOAT  = Type(BaseType.FLOAT)
T_BOOL   = Type(BaseType.BOOL)
T_STRING = Type(BaseType.STRING)
T_VOID   = Type(BaseType.VOID)


# ── 特殊类型：Unknown ─────────────────────────────────────────────────────────
# Unknown 是推导失败时的占位类型。
# 关键性质：Unknown 具有"传染性"——任何涉及 Unknown 的运算结果仍是 Unknown。
# 这样做的好处是：第一个错误报告后，后续依赖它的表达式不会产生虚假的级联错误。

class _UnknownType:
    """Unknown 类型的单例，与 Type 类分开定义避免混入正常类型比较"""
    def __str__(self):
        return "<unknown>"
    def __repr__(self):
        return "<unknown>"
    @property
    def is_unknown(self):
        return True

T_UNKNOWN = _UnknownType()


def is_unknown(t) -> bool:
    return isinstance(t, _UnknownType)


# ── 类型兼容性规则 ────────────────────────────────────────────────────────────
# 这里集中定义所有类型规则，修改时只改这一个地方

# 二元运算结果类型表
# key: (operator_category, left_type, right_type)
# value: result_type
#
# 设计思路：先按"运算符类别"分组，比按具体符号分组更简洁
# 算术运算：+  -  *  /
# 比较运算：== != < > <= >=

def result_type_of_binary(op: str, left, right):
    """
    推导二元运算的结果类型。
    返回 Type 对象，或 T_UNKNOWN（表示非法运算）。

    这个函数是类型系统的核心规则表，所有类型检查逻辑集中在这里。
    """
    # Unknown 传染：有一个操作数未知，直接返回 Unknown，不报新错误
    if is_unknown(left) or is_unknown(right):
        return T_UNKNOWN

    # ── 算术运算 ──────────────────────────────────────────────────────────────
    if op in ('+', '-', '*', '/'):
        if left == T_INT   and right == T_INT:   return T_INT
        if left == T_FLOAT and right == T_FLOAT: return T_FLOAT
        if left == T_FLOAT and right == T_INT:   return T_FLOAT  # 隐式提升
        if left == T_INT   and right == T_FLOAT: return T_FLOAT  # 隐式提升

        # string 只允许 + 拼接
        if op == '+' and left == T_STRING and right == T_STRING: return T_STRING

        # 其他组合非法，返回 None 表示需要报错
        return None

    # ── 比较运算，结果一定是 bool ─────────────────────────────────────────────
    if op in ('==', '!='):
        # 相同类型可以比较
        if left == right: return T_BOOL
        # 数值类型之间可以比较
        if left.is_numeric and right.is_numeric: return T_BOOL
        return None

    if op in ('<', '>', '<=', '>='):
        # 只有数值类型可以做大小比较
        if left.is_numeric and right.is_numeric: return T_BOOL
        return None

    return None  # 未知运算符


def can_assign(target_type, value_type) -> bool:
    """
    判断 value_type 的值能否赋给 target_type 的变量。
    """
    if is_unknown(target_type) or is_unknown(value_type):
        return True  # Unknown 传染，不产生额外报错
    if target_type == value_type:
        return True
    # int 可以赋给 float（隐式提升）
    if target_type == T_FLOAT and value_type == T_INT:
        return True
    return False


# ═══════════════════════════════════════════════════════════════════════════════
# 第二部分：符号表
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class Symbol:
    """符号表中的一个条目"""
    name:        str
    type_:       object          # Type 或 T_UNKNOWN
    kind:        str             # 'variable' | 'function' | 'param'
    line:        int = 0
    col:         int = 0
    param_types: list = field(default_factory=list)   # 函数参数类型列表
    return_type: object = None                         # 函数返回类型


class ScopeStack:
    """
    作用域栈，维护从内到外的变量可见性。

    每进入一个块（函数体、if块）就 push 一个新字典，
    退出时 pop，外层的变量自动恢复可见。

    查找时从栈顶（最内层）向栈底（最外层）搜索。
    """

    def __init__(self):
        # 全局作用域始终在栈底
        self._stack: list[dict[str, Symbol]] = [{}]

    def push(self):
        """进入新的作用域（如函数体、if块）"""
        self._stack.append({})

    def pop(self):
        """退出当前作用域"""
        if len(self._stack) > 1:  # 保留全局作用域
            self._stack.pop()

    def declare(self, sym: Symbol) -> Optional[Symbol]:
        """
        在当前作用域声明符号。
        如果当前作用域已有同名符号，返回已有的（调用方报错）。
        """
        current = self._stack[-1]
        if sym.name in current:
            return current[sym.name]  # 重复声明
        current[sym.name] = sym
        return None

    def lookup(self, name: str) -> Optional[Symbol]:
        """从内到外查找，找不到返回 None"""
        for scope in reversed(self._stack):
            if name in scope:
                return scope[name]
        return None

    @property
    def is_global(self) -> bool:
        return len(self._stack) == 1


# ═══════════════════════════════════════════════════════════════════════════════
# 第三部分：错误收集
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class TypeError_:
    """一个类型错误"""
    message:  str
    line:     int
    col:      int
    context:  str = ""   # 所在函数名

    def __str__(self):
        ctx = f" (in {self.context})" if self.context else ""
        return f"  [line {self.line:>3}, col {self.col:>3}]{ctx}  {self.message}"


# ═══════════════════════════════════════════════════════════════════════════════
# 第四部分：工具函数
# ═══════════════════════════════════════════════════════════════════════════════

def token_pos(token: Token) -> tuple:
    return (token.line or 0, token.column or 0)


def parse_type_node(tree: Tree) -> object:
    """
    把语法树中的 type 节点转换为 Type 对象。
    语法中 type 节点的 data 是 t_int / t_float / t_bool / t_string。
    """
    mapping = {
        't_int':    T_INT,
        't_float':  T_FLOAT,
        't_bool':   T_BOOL,
        't_string': T_STRING,
    }
    return mapping.get(tree.data, T_UNKNOWN)


# ═══════════════════════════════════════════════════════════════════════════════
# 第五部分：Pass 1 —— 收集函数签名
#
# 为什么需要 Pass 1？
# 考虑这种情况：
#     int main() {
#         int r = add(1, 2);   // add 在下面才定义
#     }
#     int add(int a, int b) { return a + b; }
#
# 如果只做一遍，分析 main 时还不知道 add 的签名，无法检查调用。
# Pass 1 先扫描所有函数定义，把签名存入全局符号表，
# Pass 2 再做详细的类型推导。
# ═══════════════════════════════════════════════════════════════════════════════

class SignatureCollector(Interpreter):
    """
    Pass 1：只收集函数签名，不进入函数体。
    """

    def __init__(self, scope: ScopeStack):
        self.scope = scope
        self.errors: list[TypeError_] = []

    def start(self, tree):
        self.visit_children(tree)

    def func_def(self, tree):
        """
        语法：type IDENTIFIER "(" param_list? ")" "{" statement* "}"
        children 的结构：[type_node, IDENTIFIER, param?, ..., statements...]
        """
        children = tree.children
        ret_type = parse_type_node(children[0])
        name_tok = children[1]  # Token
        func_name = str(name_tok)
        line, col = token_pos(name_tok)

        # 收集参数类型
        param_types = []
        for child in children[2:]:
            if isinstance(child, Tree) and child.data == 'param_list':
                for param in child.children:
                    if isinstance(param, Tree) and param.data == 'param':
                        param_types.append(parse_type_node(param.children[0]))

        sym = Symbol(
            name=func_name,
            type_=ret_type,
            kind='function',
            line=line, col=col,
            param_types=param_types,
            return_type=ret_type
        )
        existing = self.scope.declare(sym)
        if existing:
            self.errors.append(TypeError_(
                f"函数 '{func_name}' 重复定义（先前在第 {existing.line} 行）",
                line, col
            ))

        # 不访问函数体，直接返回
        # Interpreter 不会自动递归，这里什么都不做就等于不进入函数体


# ═══════════════════════════════════════════════════════════════════════════════
# 第六部分：Pass 2 —— 类型推导
#
# 核心思路：后序遍历（Post-order traversal）
#   先递归推导子表达式的类型，再根据子类型推导父节点的类型。
#   对每个表达式节点，_infer 函数既返回该表达式的类型，
#   也作为副作用报告类型错误。
# ═══════════════════════════════════════════════════════════════════════════════

class TypeInferencer(Interpreter):
    """
    Pass 2：类型推导主体。

    关键设计：_infer(node) 是核心函数，对任意表达式节点返回其类型。
    所有类型检查都通过调用 _infer 完成，错误收集在 self.errors。
    """

    def __init__(self, scope: ScopeStack):
        self.scope   = scope
        self.errors: list[TypeError_] = []
        self._current_func = ""        # 当前所在函数，用于错误上下文
        self._expected_return = None   # 当前函数的期望返回类型

    # ── 顶层入口 ──────────────────────────────────────────────────────────────

    def start(self, tree):
        self.visit_children(tree)

    # ── 语句处理 ──────────────────────────────────────────────────────────────

    def var_decl(self, tree):
        """
        变量声明：type IDENTIFIER ("=" expr)?

        处理顺序：
          1. 解析声明的类型
          2. 如果有初始化表达式，推导其类型并检查兼容性
          3. 把变量注册到当前作用域
        """
        children = tree.children
        decl_type = parse_type_node(children[0])
        name_tok  = children[1]
        var_name  = str(name_tok)
        line, col = token_pos(name_tok)

        # 有初始化表达式
        if len(children) > 2:
            init_expr = children[2]
            init_type = self._infer(init_expr)   # ← 推导右侧表达式类型

            # 检查赋值兼容性
            if not is_unknown(init_type) and not can_assign(decl_type, init_type):
                self._error(
                    f"类型不匹配：声明为 {decl_type}，初始化值类型为 {init_type}",
                    line, col
                )

        # 注册变量
        sym = Symbol(name=var_name, type_=decl_type, kind='variable',
                     line=line, col=col)
        existing = self.scope.declare(sym)
        if existing:
            self._error(
                f"变量 '{var_name}' 重复声明（先前在第 {existing.line} 行）",
                line, col
            )

    def assign_stmt(self, tree):
        """
        赋值语句：IDENTIFIER "=" expr

        处理顺序：
          1. 查找左侧变量的类型
          2. 推导右侧表达式类型
          3. 检查兼容性
        """
        name_tok  = tree.children[0]
        var_name  = str(name_tok)
        line, col = token_pos(name_tok)
        expr_node = tree.children[1]

        target_sym = self.scope.lookup(var_name)
        if target_sym is None:
            self._error(f"变量 '{var_name}' 未声明", line, col)
            self._infer(expr_node)  # 还是要推导右侧，避免漏报
            return

        value_type = self._infer(expr_node)  # ← 推导右侧

        if not can_assign(target_sym.type_, value_type):
            self._error(
                f"类型不匹配：变量 '{var_name}' 类型为 {target_sym.type_}，"
                f"赋值表达式类型为 {value_type}",
                line, col
            )

    def expr_stmt(self, tree):
        """纯表达式语句，推导但不使用结果（主要是触发函数调用检查）"""
        self._infer(tree.children[0])

    def if_stmt(self, tree):
        """
        if 语句：检查条件必须是 bool，然后进入新作用域分析 body
        """
        children = tree.children
        cond_expr = children[0]

        # 检查条件类型
        cond_type = self._infer(cond_expr)
        if not is_unknown(cond_type) and cond_type != T_BOOL:
            tok = self._first_token(cond_expr)
            line, col = token_pos(tok) if tok else (0, 0)
            self._error(
                f"if 条件必须是 bool，得到 {cond_type}",
                line, col
            )

        # 进入新作用域分析 body（if 块内声明的变量不影响外部）
        self.scope.push()
        for stmt in children[1:]:
            if isinstance(stmt, Tree):
                self.visit(stmt)
        self.scope.pop()

    def func_def(self, tree):
        """
        函数定义：进入函数作用域，注册参数，分析函数体
        """
        children  = tree.children
        ret_type  = parse_type_node(children[0])
        name_tok  = children[1]
        func_name = str(name_tok)

        old_func   = self._current_func
        old_return = self._expected_return
        self._current_func    = func_name
        self._expected_return = ret_type

        # 推入函数作用域
        self.scope.push()

        # 注册参数
        for child in children[2:]:
            if isinstance(child, Tree) and child.data == 'param_list':
                for param in child.children:
                    if isinstance(param, Tree) and param.data == 'param':
                        p_type = parse_type_node(param.children[0])
                        p_tok  = param.children[1]
                        p_name = str(p_tok)
                        p_line, p_col = token_pos(p_tok)
                        self.scope.declare(Symbol(
                            name=p_name, type_=p_type,
                            kind='param', line=p_line, col=p_col
                        ))

        # 分析函数体（跳过类型节点、名字token和参数列表）
        for child in children[2:]:
            if isinstance(child, Tree) and child.data not in ('param_list',):
                self.visit(child)

        self.scope.pop()
        self._current_func    = old_func
        self._expected_return = old_return

    def return_stmt(self, tree):
        """
        return 语句：检查返回类型与函数声明是否匹配
        """
        if not tree.children:
            # return;
            if self._expected_return and self._expected_return != T_VOID:
                self._error(
                    f"函数 '{self._current_func}' 应返回 {self._expected_return}，"
                    f"但 return 没有值",
                    0, 0
                )
            return

        ret_expr = tree.children[0]
        ret_type = self._infer(ret_expr)

        if (self._expected_return
                and not is_unknown(ret_type)
                and not can_assign(self._expected_return, ret_type)):
            tok = self._first_token(ret_expr)
            line, col = token_pos(tok) if tok else (0, 0)
            self._error(
                f"函数 '{self._current_func}' 返回类型为 "
                f"{self._expected_return}，但 return 的值类型为 {ret_type}",
                line, col
            )

    # ── 核心：表达式类型推导 ───────────────────────────────────────────────────
    #
    # _infer(node) 是整个推导系统的核心。
    # 它接受任意表达式节点，返回该表达式的类型。
    #
    # 设计模式：结构化递归（Structural Recursion）
    # 根据节点类型分发到不同的处理函数，每个处理函数：
    #   1. 先递归推导子节点类型（bottom-up）
    #   2. 根据子类型和当前节点的操作，推导当前节点类型
    #   3. 如发现类型错误，记录到 self.errors
    #   4. 返回当前节点的类型

    def _infer(self, node) -> object:
        """
        表达式类型推导入口，根据节点类型分发。
        """
        if isinstance(node, Token):
            return self._infer_token(node)

        if not isinstance(node, Tree):
            return T_UNKNOWN

        # 根据节点的 data（rule 名称）分发
        dispatch = {
            'expr':            self._infer_pass_through,
            'compare_expr':    self._infer_binary,
            'add_expr':        self._infer_binary,
            'mul_expr':        self._infer_binary,
            'unary_neg':       self._infer_unary_neg,
            'unary_not':       self._infer_unary_not,
            'var_ref':         self._infer_var_ref,
            'number_lit':      self._infer_number_lit,
            'float_lit':       self._infer_float_lit,
            'string_lit':      self._infer_string_lit,
            'bool_true':       lambda n: T_BOOL,
            'bool_false':      lambda n: T_BOOL,
            'call_expr':       self._infer_call,
            'call_expr_noarg': self._infer_call_noarg,
            'paren_expr':      self._infer_pass_through,
            'primary_expr':    self._infer_pass_through,
            'unary_expr':      self._infer_pass_through,
        }

        handler = dispatch.get(node.data)
        if handler:
            return handler(node)

        # 兜底：递归子节点，返回最后一个子节点的类型
        result = T_UNKNOWN
        for child in node.children:
            if isinstance(child, Tree):
                result = self._infer(child)
        return result

    # ── 字面量推导 ────────────────────────────────────────────────────────────

    def _infer_token(self, token: Token) -> object:
        """Token 级别的类型推导（通常是字面量）"""
        if token.type == 'NUMBER':   return T_INT
        if token.type == 'FLOAT_NUM': return T_FLOAT
        if token.type == 'STRING_LIT': return T_STRING
        return T_UNKNOWN

    def _infer_number_lit(self, node) -> object:
        return T_INT

    def _infer_float_lit(self, node) -> object:
        return T_FLOAT

    def _infer_string_lit(self, node) -> object:
        return T_STRING

    def _infer_pass_through(self, node) -> object:
        """透传节点：直接推导唯一子节点的类型"""
        for child in node.children:
            if isinstance(child, Tree):
                return self._infer(child)
        return T_UNKNOWN

    # ── 变量引用 ──────────────────────────────────────────────────────────────

    def _infer_var_ref(self, node) -> object:
        """
        变量引用：查符号表，返回变量类型
        这里同时做"未声明变量"的检查
        """
        tok  = node.children[0]
        name = str(tok)
        line, col = token_pos(tok)

        sym = self.scope.lookup(name)
        if sym is None:
            self._error(f"变量 '{name}' 未声明", line, col)
            return T_UNKNOWN  # 返回 Unknown，阻止级联错误

        return sym.type_

    # ── 一元运算 ──────────────────────────────────────────────────────────────

    def _infer_unary_neg(self, node) -> object:
        """
        负号：-expr
        只有数值类型可以取负
        """
        operand_type = self._infer(node.children[0])
        if is_unknown(operand_type):
            return T_UNKNOWN
        if not operand_type.is_numeric:
            tok = self._first_token(node.children[0])
            line, col = token_pos(tok) if tok else (0, 0)
            self._error(f"一元负号不能用于 {operand_type} 类型", line, col)
            return T_UNKNOWN
        return operand_type

    def _infer_unary_not(self, node) -> object:
        """
        逻辑非：!expr
        只有 bool 类型可以取非
        """
        operand_type = self._infer(node.children[0])
        if is_unknown(operand_type):
            return T_UNKNOWN
        if operand_type != T_BOOL:
            tok = self._first_token(node.children[0])
            line, col = token_pos(tok) if tok else (0, 0)
            self._error(f"逻辑非 '!' 不能用于 {operand_type} 类型", line, col)
            return T_UNKNOWN
        return T_BOOL

    # ── 二元运算 ──────────────────────────────────────────────────────────────

    def _infer_binary(self, node) -> object:
        """
        二元运算：left op right（可能有多个，左结合）
        语法生成的是平铺结构：[left, op, right, op, right, ...]

        处理方式：从左到右依次处理每对 (op, operand)，
        结果类型随着运算逐步更新。
        """
        children = node.children

        # 交替收集：操作数(Tree)和运算符(Token)
        # 顺序是固定的：operand0, op0, operand1, op1, operand2, ...
        operands  = []
        op_tokens = []
        for child in children:
            if isinstance(child, Tree):
                operands.append(self._infer(child))
            elif isinstance(child, Token):
                # 具名运算符 terminal：CMP_OP / ADD_OP / MUL_OP
                # token.type 是 terminal 名称，str(token) 是实际符号
                op_tokens.append(child)

        if not operands:
            return T_UNKNOWN

        if not op_tokens:
            return operands[0]

        result = operands[0]
        for i, op_tok in enumerate(op_tokens):
            op    = str(op_tok)   # 实际符号，如 "+" "==" "<="
            right = operands[i + 1] if i + 1 < len(operands) else T_UNKNOWN
            new_result = result_type_of_binary(op, result, right)

            if new_result is None:
                line, col = token_pos(op_tok)
                self._error(
                    f"运算符 '{op}' 不支持操作数类型 {result} 和 {right}",
                    line, col
                )
                result = T_UNKNOWN
            else:
                result = new_result

        return result

    # ── 函数调用 ──────────────────────────────────────────────────────────────

    def _infer_call(self, node) -> object:
        """
        函数调用：IDENTIFIER "(" arg_list ")"
        检查：① 函数是否存在  ② 参数个数  ③ 参数类型
        返回：函数的返回类型
        """
        tok       = node.children[0]
        func_name = str(tok)
        line, col = token_pos(tok)

        # 推导所有参数的类型（无论函数是否存在，都要推导以报告参数内部的错误）
        arg_types = []
        for child in node.children[1:]:
            if isinstance(child, Tree) and child.data == 'arg_list':
                for arg in child.children:
                    if isinstance(arg, Tree):
                        arg_types.append(self._infer(arg))   # ← 递归推导每个参数

        # 查符号表
        sym = self.scope.lookup(func_name)
        if sym is None:
            self._error(f"函数 '{func_name}' 未声明", line, col)
            return T_UNKNOWN

        if sym.kind not in ('function',):
            self._error(f"'{func_name}' 不是函数，无法调用", line, col)
            return T_UNKNOWN

        # 检查参数个数
        expected_count = len(sym.param_types)
        actual_count   = len(arg_types)
        if expected_count != actual_count:
            self._error(
                f"函数 '{func_name}' 期望 {expected_count} 个参数，"
                f"实际传入 {actual_count} 个",
                line, col
            )
            return sym.return_type  # 个数错了，不再检查类型

        # 逐个检查参数类型
        for i, (expected, actual) in enumerate(zip(sym.param_types, arg_types)):
            if not is_unknown(actual) and not can_assign(expected, actual):
                self._error(
                    f"函数 '{func_name}' 第 {i+1} 个参数期望 {expected}，"
                    f"实际传入 {actual}",
                    line, col
                )

        return sym.return_type

    def _infer_call_noarg(self, node) -> object:
        """无参数函数调用：IDENTIFIER "()" """
        tok       = node.children[0]
        func_name = str(tok)
        line, col = token_pos(tok)

        sym = self.scope.lookup(func_name)
        if sym is None:
            self._error(f"函数 '{func_name}' 未声明", line, col)
            return T_UNKNOWN

        if sym.param_types:
            self._error(
                f"函数 '{func_name}' 期望 {len(sym.param_types)} 个参数，"
                f"实际传入 0 个",
                line, col
            )

        return sym.return_type if sym.return_type else T_VOID

    # ── 辅助 ──────────────────────────────────────────────────────────────────

    def _error(self, message: str, line: int, col: int):
        self.errors.append(TypeError_(
            message=message,
            line=line, col=col,
            context=self._current_func
        ))

    def _first_token(self, node) -> Optional[Token]:
        """从节点中找到第一个 Token，用于获取位置信息"""
        if isinstance(node, Token):
            return node
        if isinstance(node, Tree):
            for child in node.children:
                tok = self._first_token(child)
                if tok:
                    return tok
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# 第七部分：组装完整的分析流程
# ═══════════════════════════════════════════════════════════════════════════════

GRAMMAR = r"""
start: statement*

statement: var_decl
         | assign_stmt
         | expr_stmt
         | if_stmt
         | func_def
         | return_stmt

var_decl: type IDENTIFIER "=" expr ";"
        | type IDENTIFIER ";"

assign_stmt: IDENTIFIER "=" expr ";"
expr_stmt: expr ";"
if_stmt: "if" "(" expr ")" "{" statement* "}"

func_def: type IDENTIFIER "(" param_list ")" "{" statement* "}"
        | type IDENTIFIER "(" ")" "{" statement* "}"

param_list: param ("," param)*
param: type IDENTIFIER

return_stmt: "return" expr ";"
           | "return" ";"

expr: compare_expr

compare_expr: add_expr (CMP_OP add_expr)*

add_expr: mul_expr (ADD_OP mul_expr)*

mul_expr: unary_expr (MUL_OP unary_expr)*

unary_expr: "-" primary_expr    -> unary_neg
          | "!" primary_expr    -> unary_not
          | primary_expr

primary_expr: IDENTIFIER "(" arg_list ")"   -> call_expr
            | IDENTIFIER "(" ")"            -> call_expr_noarg
            | IDENTIFIER                    -> var_ref
            | FLOAT_NUM                     -> float_lit
            | NUMBER                        -> number_lit
            | STRING_LIT                    -> string_lit
            | "true"                        -> bool_true
            | "false"                       -> bool_false
            | "(" expr ")"                  -> paren_expr

arg_list: expr ("," expr)*

type: "int"    -> t_int
    | "float"  -> t_float
    | "bool"   -> t_bool
    | "string" -> t_string

CMP_OP: "==" | "!=" | "<=" | ">=" | "<" | ">"
ADD_OP: "+" | "-"
MUL_OP: "*" | "/"

IDENTIFIER: /[a-zA-Z_][a-zA-Z0-9_]*/
FLOAT_NUM:  /[0-9]+\.[0-9]+/
NUMBER:     /[0-9]+/
STRING_LIT: /\"[^\"]*\"/

%import common.WS
%ignore WS
%ignore /\/\/[^\n]*/
"""

_parser = Lark(GRAMMAR, parser='lalr', propagate_positions=True)


def analyze(source: str) -> tuple[list, list]:
    """
    对源码做完整的类型分析。
    返回 (syntax_errors, type_errors)
    """
    # 语法解析
    try:
        tree = _parser.parse(source)
    except Exception as e:
        return [str(e)], []

    # 建立共享的作用域栈
    scope = ScopeStack()

    # Pass 1：收集函数签名
    collector = SignatureCollector(scope)
    collector.visit(tree)

    # Pass 2：类型推导
    inferencer = TypeInferencer(scope)
    inferencer.visit(tree)

    all_errors = collector.errors + inferencer.errors
    all_errors.sort(key=lambda e: (e.line, e.col))

    return [], all_errors


def run_test(name: str, source: str, expect_errors: bool = False):
    """运行一个测试用例并打印结果"""
    print(f"\n{'─'*60}")
    print(f"【{name}】")
    print("源码:")
    for i, line in enumerate(source.strip().split('\n'), 1):
        print(f"  {i:>2} │ {line}")

    _, errors = analyze(source)

    if errors:
        print(f"\n发现 {len(errors)} 个类型错误:")
        for e in errors:
            print(e)
    else:
        print("\n✅ 类型检查通过")

    if expect_errors and not errors:
        print("⚠️  预期有错误但未检测到")
    elif not expect_errors and errors:
        print("⚠️  预期无错误但检测到了错误")


# ═══════════════════════════════════════════════════════════════════════════════
# 测试用例
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("类型推导演示")
    print("=" * 60)

    # ── 测试 1：正常代码 ──────────────────────────────────────────────────────
    run_test("正常代码", """
int x = 1 + 2;
float y = 3.14;
bool flag = true;
string s = "hello";
""", expect_errors=False)

    # ── 测试 2：基本类型不匹配 ────────────────────────────────────────────────
    run_test("赋值类型不匹配", """
int x = "hello";
bool b = 42;
string s = 3.14;
""", expect_errors=True)

    # ── 测试 3：运算符类型错误 ────────────────────────────────────────────────
    run_test("运算符类型错误", """
int x = 1;
string s = "hello";
int bad = x + s;
bool also_bad = x - true;
""", expect_errors=True)

    # ── 测试 4：Unknown 传染性（只报一个错，不级联）──────────────────────────
    run_test("Unknown传染性（只报根源错误）", """
int result = undefined_var + 1;
int another = result * 2;
""", expect_errors=True)
    # 注意：undefined_var 未声明，报一个错
    # result 的类型变成 Unknown
    # another = result * 2 因为 result 是 Unknown，不额外报错

    # ── 测试 5：函数定义与调用 ────────────────────────────────────────────────
    run_test("正常函数调用", """
int add(int a, int b) {
    return a + b;
}
int result = add(1, 2);
""", expect_errors=False)

    # ── 测试 6：函数参数错误 ──────────────────────────────────────────────────
    run_test("函数参数类型不匹配", """
int multiply(int a, int b) {
    return a * b;
}
int r1 = multiply(1, 2);
int r2 = multiply("x", 2);
int r3 = multiply(1, 2, 3);
""", expect_errors=True)

    # ── 测试 7：前向引用（Pass 1 的必要性）────────────────────────────────────
    run_test("前向引用（调用在定义之前）", """
int main_calc() {
    return helper(10);
}
int helper(int n) {
    return n * 2;
}
""", expect_errors=False)

    # ── 测试 8：返回类型检查 ──────────────────────────────────────────────────
    run_test("返回类型错误", """
int get_value() {
    return "not an int";
}
bool get_flag() {
    return 42;
}
""", expect_errors=True)

    # ── 测试 9：if 条件类型检查 ───────────────────────────────────────────────
    run_test("if 条件：int 直接作条件报错", """
int x = 1;
if (x) {
    int y = 2;
}
""", expect_errors=True)

    run_test("if 条件：比较表达式返回 bool，合法", """
int x = 1;
if (x == 1) {
    int z = 3;
}
""", expect_errors=False)

    # ── 测试 10：作用域 ───────────────────────────────────────────────────────
    run_test("作用域隔离", """
int x = 10;
int outer_fn(int a) {
    int local = a + x;
    return local;
}
""", expect_errors=False)

    # ── 测试 11：float 和 int 的隐式提升 ─────────────────────────────────────
    run_test("int → float 隐式提升", """
float f = 3.14;
int i = 2;
float result = f + i;
float result2 = i * f;
""", expect_errors=False)

    print(f"\n{'='*60}")
    print("演示完成")
