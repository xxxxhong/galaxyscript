"""
Galaxy Script AST Transformer
==============================
将 Lark 生成的 CST（具体语法树）转换为更易于分析的 AST 节点树。

使用 Lark 的 Transformer 机制：每个方法对应 grammar 中一条规则，
接收已转换的子节点，返回 AST 节点对象。

使用方式：
    transformer = GalaxyTransformer()
    ast = transformer.transform(lark_tree)
"""

from dataclasses import dataclass, field
from typing import Any, List, Optional

from lark import Transformer, Token, Tree, v_args


# ──────────────────────────────────────────────────────────────────────────────
# AST 节点基类
# ──────────────────────────────────────────────────────────────────────────────

class ASTNode:
    """
    所有 AST 节点的公共基类。

    Attributes:
        line, col: 源码位置（由 Transformer 从 meta 填入）
        gtype:     语义分析后填写的类型（GType 实例）
        symbol:    语义分析后填写的符号引用（Symbol 实例）
    """
    line: int = -1
    col:  int = -1
    gtype = None
    symbol = None

    def _pos(self):
        return f"{self.line}:{self.col}"

    def __repr__(self):
        return f"{self.__class__.__name__}@{self._pos()}"


def _meta_pos(meta) -> tuple[int, int]:
    if meta is None:
        return -1, -1
    return getattr(meta, 'line', -1), getattr(meta, 'column', -1)


# ──────────────────────────────────────────────────────────────────────────────
# 顶层 & 声明节点
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class TranslationUnit(ASTNode):
    """整个翻译单元（一个 .galaxy 文件）"""
    decls: List[ASTNode] = field(default_factory=list)


@dataclass
class IncludeDirective(ASTNode):
    path: str = ''


@dataclass
class TypeSpecNode(ASTNode):
    """类型说明：可能是 `int`, `string`, `MyStruct`, 或带数组维度的 `int[10]`"""
    base_name: str = ''           # 基础类型名
    dimensions: List[Any] = field(default_factory=list)   # 每个维度的 size expr


@dataclass
class VarDecl(ASTNode):
    """变量/常量声明（可含初始值）"""
    type_spec:  TypeSpecNode = None
    name:       str = ''
    init:       Optional[ASTNode] = None
    is_static:  bool = False
    is_const:   bool = False


@dataclass
class FuncDecl(ASTNode):
    """函数前向声明或 native 声明（无函数体）"""
    type_spec:  TypeSpecNode = None
    name:       str = ''
    params:     List['ParamDecl'] = field(default_factory=list)
    is_native:  bool = False
    is_static:  bool = False


@dataclass
class FuncDef(ASTNode):
    """函数定义（有函数体）"""
    type_spec:  TypeSpecNode = None
    name:       str = ''
    params:     List['ParamDecl'] = field(default_factory=list)
    body:       'CompoundStmt' = None
    is_static:  bool = False


@dataclass
class ParamDecl(ASTNode):
    type_spec: TypeSpecNode = None
    name:      str = ''
    is_const:  bool = False


@dataclass
class StructDef(ASTNode):
    name:    str = ''
    members: List['StructMember'] = field(default_factory=list)


@dataclass
class StructMember(ASTNode):
    type_spec: TypeSpecNode = None
    names:     List[str] = field(default_factory=list)


@dataclass
class TypedefDecl(ASTNode):
    type_spec: TypeSpecNode = None
    alias:     str = ''


# ──────────────────────────────────────────────────────────────────────────────
# 语句节点
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class CompoundStmt(ASTNode):
    items: List[ASTNode] = field(default_factory=list)   # decl 或 stmt 混合


@dataclass
class ExprStmt(ASTNode):
    expr: Optional[ASTNode] = None


@dataclass
class IfStmt(ASTNode):
    cond:     ASTNode = None
    then_br:  ASTNode = None
    else_br:  Optional[ASTNode] = None


@dataclass
class WhileStmt(ASTNode):
    cond: ASTNode = None
    body: ASTNode = None


@dataclass
class DoWhileStmt(ASTNode):
    body: ASTNode = None
    cond: ASTNode = None


@dataclass
class ForStmt(ASTNode):
    init:  Optional[ASTNode] = None   # expression_statement（可为 None）
    cond:  Optional[ASTNode] = None   # expression_statement（可为 None）
    post:  Optional[ASTNode] = None   # expression（可为 None）
    body:  ASTNode = None


@dataclass
class ReturnStmt(ASTNode):
    value: Optional[ASTNode] = None


@dataclass
class BreakStmt(ASTNode):
    pass


@dataclass
class ContinueStmt(ASTNode):
    pass


@dataclass
class BreakpointStmt(ASTNode):
    pass


# ──────────────────────────────────────────────────────────────────────────────
# 表达式节点
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class Identifier(ASTNode):
    name: str = ''

    def __repr__(self):
        return f"Id({self.name})"


@dataclass
class IntLiteral(ASTNode):
    raw: str = ''

    @property
    def value(self) -> int:
        return int(self.raw, 0)


@dataclass
class FixedLiteral(ASTNode):
    """Galaxy Script 的定点数字面量（fixed 类型）"""
    raw: str = ''

    @property
    def value(self) -> float:
        return float(self.raw)


@dataclass
class BoolLiteral(ASTNode):
    value: bool = False


@dataclass
class NullLiteral(ASTNode):
    pass


@dataclass
class StringLiteral(ASTNode):
    raw: str = ''   # 含引号的原始字符串

    @property
    def value(self) -> str:
        return self.raw[1:-1]   # 去掉引号


@dataclass
class BinaryOp(ASTNode):
    op:    str = ''
    left:  ASTNode = None
    right: ASTNode = None

    def __repr__(self):
        return f"BinOp({self.op})"


@dataclass
class UnaryOp(ASTNode):
    op:      str = ''
    operand: ASTNode = None


@dataclass
class TernaryOp(ASTNode):
    """condition ? then_expr : else_expr"""
    cond:      ASTNode = None
    then_expr: ASTNode = None
    else_expr: ASTNode = None


@dataclass
class AssignOp(ASTNode):
    op:    str = ''     # '=', '+=', '-=', etc.
    left:  ASTNode = None
    right: ASTNode = None


@dataclass
class CastExpr(ASTNode):
    target_type: TypeSpecNode = None
    expr:        ASTNode = None


@dataclass
class FuncCall(ASTNode):
    callee: ASTNode = None
    args:   List[ASTNode] = field(default_factory=list)


@dataclass
class ArrayAccess(ASTNode):
    array: ASTNode = None
    index: ASTNode = None


@dataclass
class MemberAccess(ASTNode):
    obj:    ASTNode = None
    member: str = ''


@dataclass
class CommaExpr(ASTNode):
    """逗号表达式 (expr1, expr2, ...)"""
    exprs: List[ASTNode] = field(default_factory=list)


@dataclass
class Initializer(ASTNode):
    """花括号初始化列表 { a, b, c }"""
    items: List[ASTNode] = field(default_factory=list)


# ──────────────────────────────────────────────────────────────────────────────
# Transformer
# ──────────────────────────────────────────────────────────────────────────────

def _str(tok) -> str:
    """Token → str"""
    return str(tok)


def _is_tok(tok, *types) -> bool:
    return isinstance(tok, Token) and str(tok.type) in types


class GalaxyTransformer(Transformer):
    """
    将 Lark CST 转换为 Galaxy Script AST。
    规则名与 grammar 中的产生式名保持一致。

    使用 @v_args(meta=True) 来获取源码位置。
    """

    # ── 辅助 ────────────────────────────────────────────────────────────────

    @staticmethod
    def _set_pos(node: ASTNode, meta) -> ASTNode:
        if meta:
            node.line = getattr(meta, 'line', -1)
            node.col  = getattr(meta, 'column', -1)
        return node

    # ── 顶层 ────────────────────────────────────────────────────────────────

    def start(self, items):
        node = TranslationUnit(decls=[i for i in items if i is not None])
        return node
    # @v_args(meta=True)
    # def translation_unit(self, meta, items):
    #     node = TranslationUnit(decls=[i for i in items if i is not None])
    #     return self._set_pos(node, meta)
    
    def translation_unit(self, items):
        node = TranslationUnit(decls=[i for i in items if i is not None])
        return node

    @v_args(meta=True)
    def include_directive(self, meta, items):
        path_tok = items[1] if len(items) > 1 else items[0]
        node = IncludeDirective(path=_str(path_tok))
        return self._set_pos(node, meta)

    # ── 类型说明 ─────────────────────────────────────────────────────────────

    @v_args(meta=True)
    def type_specifier(self, meta, items):
        # items[0] = base_type_specifier / base Token
        # items[1:] = array_dimensions（可选）
        base = items[0]
        dims = []
        if len(items) > 1:
            # array_dimensions 已被转换为列表
            dims = items[1] if isinstance(items[1], list) else [items[1]]
        if isinstance(base, str):
            base_name = base
        elif isinstance(base, Token):
            base_name = _str(base)
        else:
            base_name = _str(base)
        node = TypeSpecNode(base_name=base_name, dimensions=dims)
        return self._set_pos(node, meta)

    @v_args(meta=True)
    def base_type_specifier(self, meta, items):
        # 可能是关键字 Token，或者是 struct_or_union_specifier
        tok = items[0]
        if isinstance(tok, ASTNode):
            return tok          # struct_or_union_specifier
        return _str(tok)        # 关键字

    @v_args(meta=True)
    def array_dimensions(self, meta, items):
        # 每个维度：[ expr ]，去掉括号 Token
        exprs = [i for i in items if not _is_tok(i, 'LSQB', 'RSQB')]
        return exprs

    # ── struct ──────────────────────────────────────────────────────────────

    @v_args(meta=True)
    def struct_or_union_specifier(self, meta, items):
        # struct NAME { members }  |  struct NAME  |  struct { members }
        name = ''
        members = []
        for item in items:
            if isinstance(item, Token) and item.type == 'IDENTIFIER':
                name = _str(item)
            elif isinstance(item, list):
                members = item
        node = StructDef(name=name, members=members)
        return self._set_pos(node, meta)

    @v_args(meta=True)
    def struct_declaration_list(self, meta, items):
        return [i for i in items if isinstance(i, StructMember)]

    @v_args(meta=True)
    def struct_declaration(self, meta, items):
        # specifier_qualifier_list struct_declarator_list ";"
        type_spec = items[0] if items else None
        names = []
        for item in items[1:]:
            if isinstance(item, str):
                names.append(item)
            elif isinstance(item, list):
                names.extend(item)
        node = StructMember(type_spec=type_spec, names=names)
        return self._set_pos(node, meta)

    def struct_declarator_list(self, items):
        return [_str(i) for i in items if isinstance(i, Token) and i.type == 'IDENTIFIER']

    # ── 外部声明 ─────────────────────────────────────────────────────────────

    # @v_args(meta=True)
    # def external_declaration(self, meta, items):
    #     return items[0] if items else None
    
    def external_declaration(self, items):
        return items[0] if items else None

    @v_args(meta=True)
    def native_declaration(self, meta, items):
        # NATIVE declaration_specifiers declarator ";"
        type_spec, name, params, is_static, is_const = self._parse_decl_spec_declarator(items[1:])
        node = FuncDecl(type_spec=type_spec, name=name, params=params,
                        is_native=True, is_static=is_static)
        return self._set_pos(node, meta)

    @v_args(meta=True)
    def function_definition(self, meta, items):
        # declaration_specifiers declarator compound_statement
        # （参数声明列表的情况 Galaxy Script 基本不用，暂时忽略）
        type_spec, name, params, is_static, is_const = self._parse_decl_spec_declarator(items[:-1])
        body = items[-1]
        node = FuncDef(type_spec=type_spec, name=name, params=params,
                       body=body, is_static=is_static)
        return self._set_pos(node, meta)

    @v_args(meta=True)
    def declaration(self, meta, items):
        """
        处理 declaration 规则：
          - typedef → TypedefDecl
          - 函数型 declarator → FuncDecl（前向声明）
          - 其他 → VarDecl 列表
        """
        # 从 items 中提取 declaration_specifiers 和 init_declarator_list
        spec_items = []
        decl_items = []
        reached_declarator = False
        # for item in items:
        #     if isinstance(item, (TypeSpecNode, StructDef)):
        #         spec_items.append(item)
        #         reached_declarator = True
        #     elif isinstance(item, list):
        #         decl_items = item   # init_declarator_list
        #     elif isinstance(item, Token):
        #         spec_items.append(item)
        
        for item in items:
            if isinstance(item, list):
                # 判断是 declaration_specifiers 的透传列表还是 init_declarator_list
                if item and isinstance(item[0], tuple):
                    # init_declarator_list：元素是 (name, suffix, init) 元组
                    decl_items = item
                else:
                    # declaration_specifiers 的透传列表
                    spec_items.extend(item)
            elif isinstance(item, (TypeSpecNode, StructDef)):
                spec_items.append(item)
            elif isinstance(item, Token):
                spec_items.append(item)

        # 提取 storage_class_specifier 和 type_qualifier
        is_typedef = any(_is_tok(t, 'TYPEDEF') for t in spec_items)
        is_static  = any(_is_tok(t, 'STATIC') for t in spec_items)
        is_const   = any(_is_tok(t, 'CONST') for t in spec_items)
        type_spec  = next((i for i in spec_items if isinstance(i, (TypeSpecNode, StructDef))), None)

        results = []
        for decl_name, decl_suffix, decl_init in decl_items:
            if is_typedef:
                alias = decl_name
                node = TypedefDecl(type_spec=type_spec, alias=alias)
                self._set_pos(node, meta)
                results.append(node)
            elif decl_suffix:  # 函数前向声明
                params = decl_suffix
                node = FuncDecl(type_spec=type_spec, name=decl_name,
                                params=params, is_static=is_static)
                self._set_pos(node, meta)
                results.append(node)
            else:
                node = VarDecl(type_spec=type_spec, name=decl_name,
                               init=decl_init, is_static=is_static, is_const=is_const)
                self._set_pos(node, meta)
                results.append(node)

        if len(results) == 1:
            return results[0]
        return results if results else None

    # ── 声明辅助 ─────────────────────────────────────────────────────────────

    def _parse_decl_spec_declarator(self, items):
        """
        从 [declaration_specifiers..., declarator] 中提取：
        (TypeSpecNode, func_name, params, is_static, is_const)
        """
        type_spec  = None
        name       = ''
        params     = []
        is_static  = False
        is_const   = False

        for item in items:
            if isinstance(item, (TypeSpecNode, StructDef)):
                type_spec = item
            elif _is_tok(item, 'STATIC'):
                is_static = True
            elif _is_tok(item, 'CONST'):
                is_const = True
            elif isinstance(item, tuple):
                # declarator → (name, params_or_none, init_or_none)
                name   = item[0]
                params = item[1] or []
        return type_spec, name, params, is_static, is_const

    @v_args(meta=True)
    def init_declarator_list(self, meta, items):
        return [i for i in items if isinstance(i, tuple)]

    @v_args(meta=True)
    def init_declarator(self, meta, items):
        # (name, suffix, init)
        name, suffix = None, None
        init = None
        for item in items:
            if isinstance(item, tuple) and len(item) == 2:
                name, suffix = item
            else:
                init = item
        return (name, suffix, init)

    @v_args(meta=True)
    def declarator(self, meta, items):
        return items[0]     # → direct_declarator

    # @v_args(meta=True)
    # def direct_declarator(self, meta, items):
    #     # IDENTIFIER | direct_declarator "(" params ")" | direct_declarator "(" ")"
    #     if isinstance(items[0], Token) and items[0].type == 'IDENTIFIER':
    #         name = _str(items[0])
    #         suffix = None
    #         if len(items) > 1:
    #             suffix = items[1] if not isinstance(items[1], Token) else []
    #         return (name, suffix)
    #     # 带后缀
    #     inner_name, inner_suffix = items[0]
    #     if len(items) > 1:
    #         suffix = items[1] if not isinstance(items[1], Token) else []
    #         return (inner_name, suffix)
    #     return (inner_name, inner_suffix)
    
    @v_args(meta=True)
    def direct_declarator(self, meta, items):
        first = items[0]
        # 现在 items[0] 是原始 Token（因为删掉了 IDENTIFIER 方法）
        if isinstance(first, Token) and first.type == 'IDENTIFIER':
            name = str(first)
            suffix = None
            if len(items) > 1 and not isinstance(items[1], Token):
                suffix = items[1]
            return (name, suffix)
        # 带后缀的情况（递归）
        inner_name, inner_suffix = first
        suffix = items[1] if len(items) > 1 and not isinstance(items[1], Token) else inner_suffix
        return (inner_name, suffix)

    @v_args(meta=True)
    def parameter_type_list(self, meta, items):
        return items[0] if items else []

    @v_args(meta=True)
    def parameter_list(self, meta, items):
        return [i for i in items if isinstance(i, ParamDecl)]

    @v_args(meta=True)
    def parameter_declaration(self, meta, items):
        type_spec  = None
        name       = ''
        is_const   = False
        for item in items:
            if isinstance(item, (TypeSpecNode, StructDef)):
                type_spec = item
            elif _is_tok(item, 'CONST'):
                is_const = True
            elif isinstance(item, tuple):
                name = item[0]
        node = ParamDecl(type_spec=type_spec, name=name, is_const=is_const)
        return self._set_pos(node, meta)

    @v_args(meta=True)
    def declaration_specifiers(self, meta, items):
        return items   # 透传，由上层组装

    @v_args(meta=True)
    def specifier_qualifier_list(self, meta, items):
        return items

    # ── 语句 ────────────────────────────────────────────────────────────────

    @v_args(meta=True)
    def compound_statement(self, meta, items):
        node = CompoundStmt(items=[i for i in items if i is not None])
        return self._set_pos(node, meta)

    @v_args(meta=True)
    def declaration_list(self, meta, items):
        result = []
        for item in items:
            if isinstance(item, list):
                result.extend(item)
            elif item is not None:
                result.append(item)
        return result

    @v_args(meta=True)
    def statement_list(self, meta, items):
        return [i for i in items if i is not None]

    @v_args(meta=True)
    def expression_statement(self, meta, items):
        expr = items[0] if items and not _is_tok(items[0], 'SEMICOLON') else None
        node = ExprStmt(expr=expr)
        return self._set_pos(node, meta)

    @v_args(meta=True)
    def selection_statement(self, meta, items):
        # IF "(" expr ")" stmt [ELSE stmt]
        cond    = items[1]
        then_br = items[2]
        else_br = items[3] if len(items) > 3 else None
        node = IfStmt(cond=cond, then_br=then_br, else_br=else_br)
        return self._set_pos(node, meta)

    @v_args(meta=True)
    def iteration_statement(self, meta, items):
        kw = _str(items[0])
        if kw == 'while':
            node = WhileStmt(cond=items[1], body=items[2])
        elif kw == 'do':
            node = DoWhileStmt(body=items[1], cond=items[2])
        else:  # for
            # FOR "(" init_stmt cond_stmt [post_expr] ")" body
            init = items[1]
            cond = items[2]
            if len(items) == 4:
                post, body = None, items[3]
            else:
                post, body = items[3], items[4]
            node = ForStmt(init=init, cond=cond, post=post, body=body)
        return self._set_pos(node, meta)

    @v_args(meta=True)
    def jump_statement(self, meta, items):
        kw = _str(items[0])
        if kw == 'return':
            val = items[1] if len(items) > 1 and not _is_tok(items[1], 'SEMICOLON') else None
            node = ReturnStmt(value=val)
        elif kw == 'break':
            node = BreakStmt()
        elif kw == 'continue':
            node = ContinueStmt()
        else:  # breakpoint
            node = BreakpointStmt()
        return self._set_pos(node, meta)

    # ── 表达式（从简单到复杂，递归折叠） ───────────────────────────────────

    @v_args(meta=True)
    def expression(self, meta, items):
        if len(items) == 1:
            return items[0]
        node = CommaExpr(exprs=items)
        return self._set_pos(node, meta)

    @v_args(meta=True)
    def assignment_expression(self, meta, items):
        if len(items) == 1:
            return items[0]
        left, op_tok, right = items[0], items[1], items[2]
        node = AssignOp(op=_str(op_tok), left=left, right=right)
        return self._set_pos(node, meta)

    @v_args(meta=True)
    def conditional_expression(self, meta, items):
        if len(items) == 1:
            return items[0]
        cond, then_expr, else_expr = items[0], items[1], items[2]
        node = TernaryOp(cond=cond, then_expr=then_expr, else_expr=else_expr)
        return self._set_pos(node, meta)

    # 以下二元运算规则统一处理（左结合，多个运算符）
    def _fold_binary(self, meta, items):
        result = items[0]
        i = 1
        while i < len(items):
            op  = _str(items[i]); i += 1
            rhs = items[i];       i += 1
            node = BinaryOp(op=op, left=result, right=rhs)
            self._set_pos(node, meta)
            result = node
        return result

    @v_args(meta=True)
    def logical_or_expression(self, meta, items):
        return self._fold_binary(meta, items)

    @v_args(meta=True)
    def logical_and_expression(self, meta, items):
        return self._fold_binary(meta, items)

    # @v_args(meta=True)
    # def inclusive_or_expression(self, meta, items):
    #     return self._fold_binary(meta, items)
    
    @v_args(meta=True)
    def inclusive_or_expression(self, meta, items):
        # grammar: and_expression ("|" and_expression)*
        # Lark 过滤了字符串字面量 "|"，items 只有操作数
        if len(items) == 1:
            return items[0]
        result = items[0]
        for rhs in items[1:]:
            node = BinaryOp(op='|', left=result, right=rhs)
            self._set_pos(node, meta)
            result = node
        return result

    # @v_args(meta=True)
    # def exclusive_or_expression(self, meta, items):
    #     return self._fold_binary(meta, items)

    @v_args(meta=True)
    def and_expression(self, meta, items):
        if len(items) == 1:
            return items[0]
        result = items[0]
        for rhs in items[1:]:
            node = BinaryOp(op='&', left=result, right=rhs)
            self._set_pos(node, meta)
            result = node
        return result

    @v_args(meta=True)
    def exclusive_or_expression(self, meta, items):
        if len(items) == 1:
            return items[0]
        result = items[0]
        for rhs in items[1:]:
            node = BinaryOp(op='^', left=result, right=rhs)
            self._set_pos(node, meta)
            result = node
        return result

    # @v_args(meta=True)
    # def and_expression(self, meta, items):
    #     return self._fold_binary(meta, items)

    @v_args(meta=True)
    def equality_expression(self, meta, items):
        return self._fold_binary(meta, items)

    @v_args(meta=True)
    def relational_expression(self, meta, items):
        return self._fold_binary(meta, items)

    @v_args(meta=True)
    def shift_expression(self, meta, items):
        return self._fold_binary(meta, items)

    @v_args(meta=True)
    def additive_expression(self, meta, items):
        return self._fold_binary(meta, items)

    @v_args(meta=True)
    def multiplicative_expression(self, meta, items):
        return self._fold_binary(meta, items)

    @v_args(meta=True)
    def cast_expression(self, meta, items):
        if len(items) == 1:
            return items[0]
        # "(" type_name ")" cast_expression
        target_type = items[0]
        expr        = items[1]
        node = CastExpr(target_type=target_type, expr=expr)
        return self._set_pos(node, meta)

    @v_args(meta=True)
    def unary_expression(self, meta, items):
        if len(items) == 1:
            return items[0]
        op      = _str(items[0])
        operand = items[1]
        node = UnaryOp(op=op, operand=operand)
        return self._set_pos(node, meta)

    @v_args(meta=True)
    def postfix_expression(self, meta, items):
        result = items[0]
        for suffix in items[1:]:
            if isinstance(suffix, tuple):
                kind = suffix[0]
                if kind == 'index':
                    node = ArrayAccess(array=result, index=suffix[1])
                elif kind == 'call':
                    node = FuncCall(callee=result, args=suffix[1])
                elif kind == 'member':
                    node = MemberAccess(obj=result, member=suffix[1])
                else:
                    node = result
                self._set_pos(node, meta)
                result = node
        return result

    # @v_args(meta=True)
    # def postfix_suffix(self, meta, items):
    #     # "[" expr "]"  | "(" args ")"  | "." IDENTIFIER
    #     first = items[0]
    #     if _is_tok(first, 'LSQB'):
    #         return ('index', items[1])
    #     if _is_tok(first, 'LPAR'):
    #         args = items[1] if len(items) > 2 else []
    #         return ('call', args if isinstance(args, list) else [args])
    #     if _is_tok(first, 'DOT'):
    #         return ('member', _str(items[1]))
    #     return ('unknown', None)
    
    def postfix_suffix(self, items):
        if not items:
            # "()" 空参数调用
            return ('call', [])
        
        first = items[0]
        
        # "[" expr "]" → 数组访问
        if isinstance(first, Token) and first.type == 'LSQB':
            return ('index', items[1])
        
        # "." IDENTIFIER → 成员访问
        if isinstance(first, Token) and first.type == 'DOT':
            return ('member', str(items[1]))
        
        # "(" args ")" → 函数调用（有参数）
        # items[0] 就是 argument_expression_list 的结果（已是列表）
        if isinstance(first, list):
            return ('call', first)
        
        # 单个表达式作为参数
        return ('call', [first])

    @v_args(meta=True)
    def argument_expression_list(self, meta, items):
        return list(items)

    # ── 主表达式 ─────────────────────────────────────────────────────────────

    # @v_args(meta=True)
    # def primary_expression(self, meta, items):
    #     return items[0]     # 直接透传

    @v_args(meta=True)
    def primary_expression(self, meta, items):
        tok = items[0]
        # IDENTIFIER token → Identifier 节点（只在表达式位置转换）
        if isinstance(tok, Token) and tok.type == 'IDENTIFIER':
            node = Identifier(name=str(tok))
            node.line = getattr(tok, 'line', -1)
            node.col  = getattr(tok, 'column', -1)
            return node
        # 其他情况（常量、字符串、括号表达式）直接透传
        return tok
    
    # @v_args(meta=True)
    # def IDENTIFIER(self, tok):
    #     node = Identifier(name=_str(tok))
    #     node.line = getattr(tok, 'line', -1)
    #     node.col  = getattr(tok, 'column', -1)
    #     return node
    
    

    @v_args(meta=True)
    def CONSTANT(self, tok):
        raw = _str(tok)
        # 判断是整数还是浮点
        if '.' in raw or ('e' in raw.lower() and not raw.startswith('0x')):
            node = FixedLiteral(raw=raw)
        else:
            node = IntLiteral(raw=raw)
        node.line = getattr(tok, 'line', -1)
        node.col  = getattr(tok, 'column', -1)
        return node

    @v_args(meta=True)
    def STRING_LITERAL(self, tok):
        node = StringLiteral(raw=_str(tok))
        node.line = getattr(tok, 'line', -1)
        node.col  = getattr(tok, 'column', -1)
        return node

    @v_args(meta=True)
    def TRUE(self, tok):
        node = BoolLiteral(value=True)
        node.line = getattr(tok, 'line', -1)
        return node

    @v_args(meta=True)
    def FALSE(self, tok):
        node = BoolLiteral(value=False)
        node.line = getattr(tok, 'line', -1)
        return node

    @v_args(meta=True)
    def NULL(self, tok):
        node = NullLiteral()
        node.line = getattr(tok, 'line', -1)
        return node

    # ── 初始化列表 ───────────────────────────────────────────────────────────

    @v_args(meta=True)
    def initializer(self, meta, items):
        if len(items) == 1 and not isinstance(items[0], list):
            return items[0]   # 单个赋值表达式
        inner = [i for i in items if not _is_tok(i, 'LBRACE', 'RBRACE', 'COMMA')]
        node = Initializer(items=inner)
        return self._set_pos(node, meta)

    @v_args(meta=True)
    def initializer_list(self, meta, items):
        return [i for i in items if not _is_tok(i, 'COMMA')]

    # ── 赋值运算符 ───────────────────────────────────────────────────────────

    def assignment_operator(self, items):
        return items[0]   # 透传 Token

    # ── 透传规则（不需要特别处理的） ─────────────────────────────────────────

    def statement(self, items):
        return items[0]

    def external_declaration(self, items):
        return items[0]

    def type_name(self, items):
        return items[0]   # specifier_qualifier_list

    def specifier_qualifier_list(self, items):
        return next((i for i in items if isinstance(i, (TypeSpecNode, StructDef))), None)

    def constant_expression(self, items):
        return items[0]
