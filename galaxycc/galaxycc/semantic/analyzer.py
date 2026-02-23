"""
Galaxy Script 语义分析器
=========================
使用访问者模式遍历 AST，完成：
  1. 符号表构建（变量、函数、struct、typedef）
  2. 类型推导与类型检查
  3. 作用域分析
  4. 控制流合法性检查（break/continue 只能在循环内）
  5. 返回值检查

设计原则：
  - 遇到错误后继续分析（使用 ErrorType 作为错误恢复类型）
  - 所有错误写入 DiagnosticBag，不抛异常（除非致命错误）
  - 分析完成后，AST 节点的 .gtype 属性被填写
"""

from __future__ import annotations
from typing import Optional

from galaxycc.error import DiagnosticBag, _loc
from .type import (
    GType, BasicType, HandleType, ArrayType, FunctionType,
    StructType, TypedefType, NullType, ErrorType,
    VOID, INT, FIXED, BOOL, STRING, TEXT, NULL_T, ERROR_T,
    BUILTIN_TYPES, HANDLE_TYPES,
    is_numeric, is_arithmetic, is_comparable, is_orderable,
    can_assign, resolve_binary_op,
)
from .symbol import Symbol, SymbolKind, SymbolTable

# 导入 AST 节点（从 transformer 模块）
from ..tree.transformer import (
    ASTNode, TranslationUnit, IncludeDirective,
    TypeSpecNode, StructDef,
    VarDecl, FuncDecl, FuncDef, ParamDecl, TypedefDecl,
    StructMember,
    CompoundStmt, ExprStmt,
    IfStmt, WhileStmt, DoWhileStmt, ForStmt,
    ReturnStmt, BreakStmt, ContinueStmt, BreakpointStmt,
    Identifier, IntLiteral, FixedLiteral, BoolLiteral,
    NullLiteral, StringLiteral,
    BinaryOp, UnaryOp, TernaryOp, AssignOp, CastExpr,
    FuncCall, ArrayAccess, MemberAccess,
    CommaExpr, Initializer,
)


class GalaxyAnalyzer:
    """
    Galaxy Script 语义分析器。

    用法：
        analyzer = GalaxyAnalyzer()
        diags = analyzer.analyze(ast_root)
        if diags.has_errors:
            print(diags.report())
    """

    def __init__(self, native_builtins: dict = None, file_loader=None, parser=None):
        """
        Args:
            native_builtins: 预定义的 native 函数字典
                             { func_name: FunctionType }
                             通常由外部加载 Galaxy API 定义后传入
        """
        self._file_loader = file_loader
        self._parser = parser
        self._curr_file = '<main>'
        self._included = set()
        self.diag  = DiagnosticBag()
        self.table = SymbolTable()

        # 分析器状态
        self._curr_func: Optional[FunctionType] = None   # 当前所在函数类型
        self._curr_func_name: str = ''
        self._loop_depth: int = 0                        # 嵌套循环深度

        # 注册内置类型
        for name, gtype in BUILTIN_TYPES.items():
            sym = Symbol(name, gtype, SymbolKind.TYPE)
            self.table.define(sym)

        # 注册用户提供的 native 函数
        if native_builtins:
            for fname, ftype in native_builtins.items():
                sym = Symbol(fname, ftype, SymbolKind.FUNC, is_native=True)
                self.table.define(sym)

    # ══════════════════════════════════════════════════════════════════════
    # 入口
    # ══════════════════════════════════════════════════════════════════════

    def analyze(self, root: TranslationUnit, source_name='<main>') -> DiagnosticBag:
        """
        分析整个翻译单元，返回诊断信息袋。
        分析后每个 AST 节点的 .gtype 会被填写。
        """
        self._curr_file = source_name
        self._visit(root)
        return self.diag

    # ══════════════════════════════════════════════════════════════════════
    # 分发器
    # ══════════════════════════════════════════════════════════════════════

    def _visit(self, node: ASTNode) -> GType:
        """
        分发到对应的 visit_* 方法。
        返回节点的类型（对表达式有意义）。
        """
        if node is None:
            return VOID
        method = '_visit_' + type(node).__name__
        handler = getattr(self, method, self._visit_default)
        result = handler(node)
        return result if result is not None else VOID

    def _visit_default(self, node: ASTNode):
        """未注册的节点：递归处理子节点"""
        for child in getattr(node, '__dict__', {}).values():
            if isinstance(child, ASTNode):
                self._visit(child)
            elif isinstance(child, list):
                for item in child:
                    if isinstance(item, ASTNode):
                        self._visit(item)

    # def _process_include(self, node: IncludeDirective):
    #     if self._file_loader is None or node.path in self._included:
    #         return
    #     self._included.add(node.path)
    #     try:
    #         source = self._file_loader(node.path)
    #         included_ast = parse(source)
    #         self._visit_TranslationUnit(included_ast)
    #     except FileNotFoundError:
    #         self.diag.warning(f"找不到 include 文件 '{node.path}'", node)
    
    # def _process_include(self, node: IncludeDirective):
    #     if self._file_loader is None or self._parser is None:
    #         return
    #     if node.path in self._included:
    #         return
    #     self._included.add(node.path)
    #     try:
    #         source = self._file_loader(node.path)
    #         included_ast = self._parser(source)
    #         self._visit_TranslationUnit(included_ast)
    #     except FileNotFoundError:
    #         self.diag.warning(f"找不到 include 文件 '{node.path}'", node)
            
    def _process_include(self, node: IncludeDirective):
        if self._file_loader is None or self._parser is None:
            return
        if node.path in self._included:
            return
        self._included.add(node.path)
        try:
            source = self._file_loader(node.path)
            included_ast = self._parser(source)
            self._curr_file = node.path  # 新增
            self._visit_TranslationUnit(included_ast)
        except FileNotFoundError:
            self.diag.warning(f"找不到 include 文件 '{node.path}'", node)
    
    def _register_type_forward(self, node):
        if isinstance(node, StructDef):
            sym = Symbol(node.name, StructType(node.name, members=None), SymbolKind.TYPE)
            self.table.define(sym)
        elif isinstance(node, TypedefDecl):
            sym = Symbol(node.alias, VOID, SymbolKind.TYPE)  # 临时占位
            self.table.define(sym)
    
    # ══════════════════════════════════════════════════════════════════════
    # 顶层
    # ══════════════════════════════════════════════════════════════════════

    # def _visit_TranslationUnit(self, node: TranslationUnit):
    #     # 两遍扫描：先收集所有顶层函数/类型声明（处理前向引用），再分析函数体
    #     # 第一遍：注册 struct、typedef、函数签名（不分析函数体）
    #     for decl in node.decls:
    #         if isinstance(decl, (StructDef, TypedefDecl)):
    #             self._register_type(decl)
    #         elif isinstance(decl, (FuncDecl, FuncDef)):
    #             self._register_func(decl)
    #         elif isinstance(decl, VarDecl):
    #             self._register_global_var(decl)

    #     # 第二遍：分析函数体
    #     for decl in node.decls:
    #         if isinstance(decl, FuncDef):
    #             self._visit_FuncDef(decl, body_only=True)
          
    def _visit_TranslationUnit(self, node: TranslationUnit):
        # Step 1: 处理 include
        for decl in node.decls:
            if isinstance(decl, IncludeDirective):
                self._process_include(decl)
        
        # 调试：看 include 之后 const 变量有没有被加载进来
        # print(f"[DEBUG] include 后符号表中的 const 变量:")
        print(f"[DEBUG] [{self._curr_file}] include 后符号表中的 const 变量:")
        for name, sym in self.table._scopes[0]._table.items():
            if sym.is_const:
                print(f"  {name} = {sym.const_value}")
        
        # Step 2a: 先注册 const 变量（struct 成员数组维度可能依赖它们）
        for decl in node.decls:
            if isinstance(decl, VarDecl) and decl.is_const:
                self._register_global_var(decl)

        
        # 看 Step 2a 处理了多少 const 变量
        const_decls = [d for d in node.decls if isinstance(d, VarDecl) and d.is_const]
        all_vars = [d for d in node.decls if isinstance(d, VarDecl)]
        print(f"[DEBUG] [{self._curr_file}] VarDecl 总数={len(all_vars)}, is_const=True 的数量={len(const_decls)}")
        if all_vars:
            # 打印前3个变量看看
            for v in all_vars[:3]:
                print(f"  name={v.name}, is_const={v.is_const}")
        # # Step 2b: 注册类型和函数签名
        # for decl in node.decls:
        #     if isinstance(decl, (StructDef, TypedefDecl)):
        #         self._register_type(decl)
        #     elif isinstance(decl, (FuncDecl, FuncDef)):
        #         self._register_func(decl)
                
        # Step 2b-1: 先注册所有 struct/typedef 的名字（空壳，不解析成员）
        for decl in node.decls:
            if isinstance(decl, (StructDef, TypedefDecl)):
                self._register_type_forward(decl)

        # Step 2b-2: 再填充成员
        for decl in node.decls:
            if isinstance(decl, (StructDef, TypedefDecl)):
                self._register_type(decl)

        # Step 3: 注册其余全局变量
        for decl in node.decls:
            if isinstance(decl, VarDecl) and not decl.is_const:
                self._register_global_var(decl)

        # Step 4: 分析函数体
        for decl in node.decls:
            if isinstance(decl, FuncDef):
                self._visit_FuncDef(decl, body_only=True)

    def _visit_IncludeDirective(self, node: IncludeDirective):
        pass   # 词法层面已展开，此处无需处理

    # ══════════════════════════════════════════════════════════════════════
    # 类型注册（第一遍）
    # ══════════════════════════════════════════════════════════════════════

    def _register_type(self, node):
        if isinstance(node, StructDef):
            self._register_struct(node)
        elif isinstance(node, TypedefDecl):
            self._register_typedef(node)

    def _register_struct(self, node: StructDef):
        if not node.name:
            return   # 匿名 struct，在变量声明时处理
        existing = self.table.lookup_local(node.name)
        if existing and existing.kind == SymbolKind.TYPE:
            if isinstance(existing.gtype, StructType) and existing.gtype.members is None:
                # 完成前向声明
                existing.gtype.members = self._build_struct_members(node)
                return
            else:
                self.diag.error(f"类型 '{node.name}' 重复定义", node)
                return
        struct_type = StructType(node.name, None)   # 先占位
        sym = Symbol(node.name, struct_type, SymbolKind.TYPE, node=node)
        self.table.define(sym)
        struct_type.members = self._build_struct_members(node)

    def _build_struct_members(self, node: StructDef) -> dict:
        members = {}
        for member in node.members:
            mtype = self._resolve_type_spec(member.type_spec)
            for name in member.names:
                if name in members:
                    self.diag.error(f"结构体成员 '{name}' 重复定义", member)
                else:
                    members[name] = mtype
        return members

    def _register_typedef(self, node: TypedefDecl):
        underlying = self._resolve_type_spec(node.type_spec)
        td_type = TypedefType(node.alias, underlying)
        sym = Symbol(node.alias, td_type, SymbolKind.TYPE, node=node)
        if not self.table.define(sym):
            self.diag.error(f"类型 '{node.alias}' 重复定义", node)

    def _register_func(self, node):
        """注册函数签名（FuncDecl 或 FuncDef 的签名部分）"""
        return_type = self._resolve_type_spec(node.type_spec)
        func_name   = node.name
        param_types = [self._resolve_type_spec(p.type_spec) for p in node.params]
        func_type   = FunctionType(return_type, param_types)

        existing = self.table.lookup(func_name)
        is_native = getattr(node, 'is_native', False)

        if existing:
            if existing.kind != SymbolKind.FUNC:
                self.diag.error(f"'{func_name}' 已被定义为非函数类型", node)
                return
            if existing.gtype != func_type:
                self.diag.error(
                    f"函数 '{func_name}' 的重声明与原声明类型不一致\n"
                    f"  原声明: {existing.gtype}\n"
                    f"  新声明: {func_type}", node)
                return
            if isinstance(node, FuncDef) and existing.defined:
                self.diag.error(f"函数 '{func_name}' 重复定义", node)
                return
            if isinstance(node, FuncDef):
                existing.defined = True
            return

        sym = Symbol(func_name, func_type, SymbolKind.FUNC,
                     is_native=is_native,
                     defined=isinstance(node, FuncDef),
                     node=node)
        self.table.define(sym)
        node.symbol = sym

    # def _register_global_var(self, node: VarDecl):
    #     gtype = self._resolve_type_spec(node.type_spec)
    #     sym = Symbol(node.name, gtype, SymbolKind.VAR,
    #                  is_static=node.is_static,
    #                  is_const=node.is_const,
    #                  node=node)
    #     if not self.table.define(sym):
    #         self.diag.error(f"全局变量 '{node.name}' 重复定义", node)
    #         return
    
    def _register_global_var(self, node: VarDecl):
        gtype = self._resolve_type_spec(node.type_spec)
        sym = Symbol(node.name, gtype, SymbolKind.VAR,
                    is_static=node.is_static,
                    is_const=node.is_const,
                    node=node)
        
        # # 记录 const int 的编译期值
        # if node.is_const and gtype == INT and node.init:
        #     val = self._eval_const_int(node.init)
        #     if val is not None:
        #         sym.const_value = val
        
        if node.is_const and node.init:
            if gtype == INT:
                val = self._eval_const_int(node.init)
                if val is not None:
                    sym.const_value = val
            elif gtype == STRING:
                if isinstance(node.init, StringLiteral):
                    sym.const_value = node.init.value  # 存去掉引号的字符串
            elif gtype == BOOL:
                if isinstance(node.init, BoolLiteral):
                    sym.const_value = node.init.value  # 存 True/False
            elif gtype == FIXED:
                if isinstance(node.init, FixedLiteral):
                    sym.const_value = node.init.value  # 存 float
        
        if not self.table.define(sym):
            self.diag.error(f"全局变量 '{node.name}' 重复定义", node)
            return

        if node.init:
            init_type = self._visit(node.init)
            if not can_assign(gtype, init_type):
                self.diag.error(
                    f"全局变量 '{node.name}' 的初始值类型 '{init_type}' "
                    f"无法赋值给 '{gtype}'", node.init)

    # ══════════════════════════════════════════════════════════════════════
    # 函数体分析（第二遍）
    # ══════════════════════════════════════════════════════════════════════

    def _visit_FuncDef(self, node: FuncDef, body_only=False):
        func_sym = self.table.lookup(node.name)
        if func_sym is None:
            return   # 第一遍应该已经注册，这里保险

        func_type = func_sym.gtype
        self._curr_func      = func_type
        self._curr_func_name = node.name
        self._loop_depth = 0

        self.table.enter_function(node.name)

        # 注册形参
        for param in node.params:
            ptype = self._resolve_type_spec(param.type_spec)
            psym  = Symbol(param.name, ptype, SymbolKind.PARAM,
                           is_const=param.is_const, node=param)
            if not self.table.define(psym):
                self.diag.error(f"形参 '{param.name}' 重复定义", param)

        self._visit_CompoundStmt(node.body)

        self.table.leave_scope()
        self._curr_func      = None
        self._curr_func_name = ''

    # ══════════════════════════════════════════════════════════════════════
    # 语句 visit
    # ══════════════════════════════════════════════════════════════════════

    def _visit_CompoundStmt(self, node: CompoundStmt):
        self.table.enter_block()
        for item in node.items:
            if isinstance(item, list):
                for sub in item:
                    self._visit(sub)
            else:
                self._visit(item)
        self.table.leave_scope()

    def _visit_VarDecl(self, node: VarDecl):
        gtype = self._resolve_type_spec(node.type_spec)
        if gtype == VOID:
            self.diag.error(f"变量 '{node.name}' 不能声明为 void 类型", node)
            gtype = ERROR_T

        sym = Symbol(node.name, gtype, SymbolKind.VAR,
                     is_static=node.is_static, is_const=node.is_const, node=node)
        if not self.table.define(sym):
            self.diag.error(f"变量 '{node.name}' 重复定义", node)

        if node.init:
            init_type = self._visit(node.init)
            if not isinstance(gtype, ErrorType) and not can_assign(gtype, init_type):
                self.diag.error(
                    f"变量 '{node.name}' 的初始值类型 '{init_type}' "
                    f"无法赋值给 '{gtype}'", node.init)

        node.gtype = gtype

    def _visit_ExprStmt(self, node: ExprStmt):
        if node.expr:
            self._visit(node.expr)

    def _visit_IfStmt(self, node: IfStmt):
        cond_type = self._visit(node.cond)
        if not can_assign(BOOL, cond_type):
            self.diag.error(
                f"if 条件表达式类型 '{cond_type}' 无法转换为 bool", node.cond)
        self._visit(node.then_br)
        if node.else_br:
            self._visit(node.else_br)

    def _visit_WhileStmt(self, node: WhileStmt):
        cond_type = self._visit(node.cond)
        if not can_assign(BOOL, cond_type):
            self.diag.error(
                f"while 条件表达式类型 '{cond_type}' 无法转换为 bool", node.cond)
        self._loop_depth += 1
        self._visit(node.body)
        self._loop_depth -= 1

    def _visit_DoWhileStmt(self, node: DoWhileStmt):
        self._loop_depth += 1
        self._visit(node.body)
        self._loop_depth -= 1
        cond_type = self._visit(node.cond)
        if not can_assign(BOOL, cond_type):
            self.diag.error(
                f"do-while 条件表达式类型 '{cond_type}' 无法转换为 bool", node.cond)

    # def _visit_ForStmt(self, node: ForStmt):
    #     self.table.enter_block()   # for 自己的作用域（存放 init 中声明的变量）
    #     if node.init:
    #         self._visit(node.init)
    #     if node.cond:
    #         cond_type = self._visit(node.cond)
    #         if not can_assign(BOOL, cond_type):
    #             self.diag.error(
    #                 f"for 条件表达式类型 '{cond_type}' 无法转换为 bool", node.cond)
    #     if node.post:
    #         self._visit(node.post)
    #     self._loop_depth += 1
    #     self._visit(node.body)
    #     self._loop_depth -= 1
    #     self.table.leave_scope()
    
    def _visit_ForStmt(self, node: ForStmt):
        self.table.enter_block()
        if node.init:
            self._visit(node.init)
        if node.cond:
            cond_node = node.cond.expr if isinstance(node.cond, ExprStmt) else node.cond
            if cond_node is not None:  # 空条件（for(;;)）直接跳过检查
                cond_type = self._visit(cond_node)
                if not can_assign(BOOL, cond_type):
                    self.diag.error(
                        f"for 条件表达式类型 '{cond_type}' 无法转换为 bool", node.cond)
        if node.post:
            self._visit(node.post)
        self._loop_depth += 1
        self._visit(node.body)
        self._loop_depth -= 1
        self.table.leave_scope()

    def _visit_ReturnStmt(self, node: ReturnStmt):
        if self._curr_func is None:
            self.diag.error("return 语句只能出现在函数内部", node)
            return

        expected = self._curr_func.return_type
        if node.value:
            actual = self._visit(node.value)
            if expected == VOID:
                self.diag.error(
                    f"void 函数 '{self._curr_func_name}' 不能有返回值", node)
            elif not can_assign(expected, actual):
                self.diag.error(
                    f"函数 '{self._curr_func_name}' 期望返回 '{expected}'，"
                    f"实际返回 '{actual}'", node.value)
        else:
            if expected != VOID:
                self.diag.error(
                    f"函数 '{self._curr_func_name}' 必须返回 '{expected}'", node)

    def _visit_BreakStmt(self, node: BreakStmt):
        if self._loop_depth == 0:
            self.diag.error("break 语句只能出现在循环内部", node)

    def _visit_ContinueStmt(self, node: ContinueStmt):
        if self._loop_depth == 0:
            self.diag.error("continue 语句只能出现在循环内部", node)

    def _visit_BreakpointStmt(self, node: BreakpointStmt):
        pass   # breakpoint 始终合法

    # ══════════════════════════════════════════════════════════════════════
    # 表达式 visit（所有方法都返回 GType）
    # ══════════════════════════════════════════════════════════════════════

    # def _visit_Identifier(self, node: Identifier) -> GType:
    #     sym = self.table.lookup(node.name)
    #     if sym is None:
    #         self.diag.error(f"未声明的标识符 '{node.name}'", node)
    #         node.gtype = ERROR_T
    #         return ERROR_T
    #     node.gtype  = sym.gtype
    #     node.symbol = sym
    #     return sym.gtype
    
    def _visit_Identifier(self, node: Identifier) -> GType:
        sym = self.table.lookup(node.name)
        if sym is None:
            # 跨文件符号暂时降级为 warning，不阻断分析
            self.diag.warning(f"未声明的标识符 '{node.name}'（可能来自 include 文件）", node)
            node.gtype = ERROR_T
            return ERROR_T
        node.gtype  = sym.gtype
        node.symbol = sym
        return sym.gtype

    def _visit_IntLiteral(self, node: IntLiteral) -> GType:
        node.gtype = INT
        return INT

    def _visit_FixedLiteral(self, node: FixedLiteral) -> GType:
        node.gtype = FIXED
        return FIXED

    def _visit_BoolLiteral(self, node: BoolLiteral) -> GType:
        node.gtype = BOOL
        return BOOL

    def _visit_NullLiteral(self, node: NullLiteral) -> GType:
        node.gtype = NULL_T
        return NULL_T

    def _visit_StringLiteral(self, node: StringLiteral) -> GType:
        node.gtype = STRING
        return STRING

    def _visit_BinaryOp(self, node: BinaryOp) -> GType:
        ltype = self._visit(node.left)
        rtype = self._visit(node.right)
        result = resolve_binary_op(node.op, ltype, rtype)
        if result is None:
            self.diag.error(
                f"运算符 '{node.op}' 不支持操作数类型 '{ltype}' 和 '{rtype}'", node)
            result = ERROR_T
        node.gtype = result
        return result

    def _visit_UnaryOp(self, node: UnaryOp) -> GType:
        operand_type = self._visit(node.operand)
        op = node.op

        if isinstance(operand_type, ErrorType):
            node.gtype = ERROR_T
            return ERROR_T

        if op in ('+', '-'):
            if not is_arithmetic(operand_type):
                self.diag.error(
                    f"一元运算符 '{op}' 要求数值类型，实际为 '{operand_type}'", node.operand)
                node.gtype = ERROR_T
                return ERROR_T
            node.gtype = operand_type
            return operand_type

        if op == '!':
            if not can_assign(BOOL, operand_type):
                self.diag.error(
                    f"逻辑非 '!' 要求可转换为 bool 的类型，实际为 '{operand_type}'", node.operand)
                node.gtype = ERROR_T
                return ERROR_T
            node.gtype = BOOL
            return BOOL

        if op == '~':
            if operand_type != INT:
                self.diag.error(
                    f"按位取反 '~' 要求 int 类型，实际为 '{operand_type}'", node.operand)
                node.gtype = ERROR_T
                return ERROR_T
            node.gtype = INT
            return INT

        self.diag.error(f"未知一元运算符 '{op}'", node)
        node.gtype = ERROR_T
        return ERROR_T

    def _visit_TernaryOp(self, node: TernaryOp) -> GType:
        cond_type = self._visit(node.cond)
        if not can_assign(BOOL, cond_type):
            self.diag.error(
                f"三元运算符条件类型 '{cond_type}' 无法转换为 bool", node.cond)

        then_type = self._visit(node.then_expr)
        else_type = self._visit(node.else_expr)

        # 结果类型：两分支类型兼容则取"更宽"的那个
        if then_type == else_type:
            result = then_type
        elif can_assign(then_type, else_type):
            result = then_type
        elif can_assign(else_type, then_type):
            result = else_type
        else:
            self.diag.error(
                f"三元运算符的两个分支类型不兼容：'{then_type}' vs '{else_type}'", node)
            result = ERROR_T

        node.gtype = result
        return result

    def _visit_AssignOp(self, node: AssignOp) -> GType:
        ltype = self._visit(node.left)
        rtype = self._visit(node.right)

        # 检查左值
        if not self._is_lvalue(node.left):
            self.diag.error("赋值运算符的左侧必须是可修改的左值", node.left)
        elif isinstance(node.left, Identifier):
            sym = node.left.symbol
            if sym and sym.is_const:
                self.diag.error(f"不能修改 const 变量 '{sym.name}'", node.left)

        if node.op == '=':
            if not can_assign(ltype, rtype):
                self.diag.error(
                    f"无法将 '{rtype}' 赋值给 '{ltype}'", node)
        else:
            # 复合赋值 +=, -=, *=, /=
            op = node.op[:-1]   # 去掉 '='
            result = resolve_binary_op(op, ltype, rtype)
            if result is None:
                self.diag.error(
                    f"复合赋值运算符 '{node.op}' 不支持操作数类型 '{ltype}' 和 '{rtype}'", node)
            elif not can_assign(ltype, result):
                self.diag.error(
                    f"复合赋值 '{node.op}' 的结果类型 '{result}' "
                    f"无法赋值给 '{ltype}'", node)

        node.gtype = ltype
        return ltype

    def _visit_CastExpr(self, node: CastExpr) -> GType:
        src_type    = self._visit(node.expr)
        target_type = self._resolve_type_spec(node.target_type)

        # Galaxy Script 允许的显式转换：
        #   int  ↔ fixed, int/fixed → bool
        #   其他强转视为警告（与 SC2 Editor 行为一致）
        if not can_assign(target_type, src_type):
            self.diag.warning(
                f"强制类型转换 '{src_type}' → '{target_type}' 可能不安全", node)

        node.gtype = target_type
        return target_type

    def _visit_FuncCall(self, node: FuncCall) -> GType:
        callee_type = self._visit(node.callee)
        arg_types   = [self._visit(arg) for arg in node.args]

        if isinstance(callee_type, ErrorType):
            node.gtype = ERROR_T
            return ERROR_T

        if not isinstance(callee_type, FunctionType):
            self.diag.error(
                f"'{self._expr_name(node.callee)}' 不是可调用的函数类型", node.callee)
            node.gtype = ERROR_T
            return ERROR_T

        expected_params = callee_type.param_types
        if len(arg_types) != len(expected_params):
            self.diag.error(
                f"函数调用参数数量错误：期望 {len(expected_params)} 个，"
                f"实际传入 {len(arg_types)} 个", node)
        else:
            for i, (expected, actual) in enumerate(zip(expected_params, arg_types)):
                if not can_assign(expected, actual):
                    self.diag.error(
                        f"第 {i+1} 个参数类型不匹配：期望 '{expected}'，实际 '{actual}'",
                        node.args[i])

        ret_type = callee_type.return_type
        node.gtype = ret_type
        return ret_type

    def _visit_ArrayAccess(self, node: ArrayAccess) -> GType:
        array_type = self._visit(node.array)
        index_type = self._visit(node.index)

        if index_type != INT and not isinstance(index_type, ErrorType):
            self.diag.error(
                f"数组下标必须是 int 类型，实际为 '{index_type}'", node.index)

        if isinstance(array_type, ArrayType):
            elem_type = array_type.element_type
            node.gtype = elem_type
            return elem_type
        elif isinstance(array_type, ErrorType):
            node.gtype = ERROR_T
            return ERROR_T
        else:
            self.diag.error(
                f"下标运算符 '[]' 只能用于数组类型，实际为 '{array_type}'", node.array)
            node.gtype = ERROR_T
            return ERROR_T

    def _visit_MemberAccess(self, node: MemberAccess) -> GType:
        obj_type = self._visit(node.obj)

        # 解包 typedef
        actual_type = obj_type
        if isinstance(actual_type, TypedefType):
            actual_type = actual_type.resolve()

        if isinstance(actual_type, ErrorType):
            node.gtype = ERROR_T
            return ERROR_T

        if not isinstance(actual_type, StructType):
            self.diag.error(
                f"成员访问 '.' 只能用于 struct 类型，实际为 '{obj_type}'", node.obj)
            node.gtype = ERROR_T
            return ERROR_T

        if actual_type.members is None:
            self.diag.error(
                f"struct '{actual_type.name}' 尚未完整定义", node)
            node.gtype = ERROR_T
            return ERROR_T

        if node.member not in actual_type.members:
            self.diag.error(
                f"struct '{actual_type.name}' 中没有成员 '{node.member}'", node)
            node.gtype = ERROR_T
            return ERROR_T

        member_type = actual_type.members[node.member]
        node.gtype = member_type
        return member_type

    def _visit_CommaExpr(self, node: CommaExpr) -> GType:
        last_type = VOID
        for expr in node.exprs:
            last_type = self._visit(expr)
        node.gtype = last_type
        return last_type

    def _visit_Initializer(self, node: Initializer) -> GType:
        # 裸初始化列表的类型由上层 VarDecl 决定，这里只递归检查各项
        for item in node.items:
            self._visit(item)
        node.gtype = ERROR_T   # 占位，实际类型由上下文决定
        return ERROR_T

    # ══════════════════════════════════════════════════════════════════════
    # 辅助方法
    # ══════════════════════════════════════════════════════════════════════

    def _resolve_type_spec(self, node) -> GType:
        """
        将 TypeSpecNode 或 StructDef 解析为 GType。
        处理数组维度、struct、typedef 等情况。
        """
        if node is None:
            return ERROR_T

        if isinstance(node, StructDef):
            # 匿名 struct 或引用已有 struct
            if node.name:
                sym = self.table.lookup(node.name)
                if sym and sym.kind == SymbolKind.TYPE:
                    return sym.gtype
                # struct 前向声明
                st = StructType(node.name, None)
                new_sym = Symbol(node.name, st, SymbolKind.TYPE, node=node)
                self.table.define(new_sym)
                return st
            else:
                # 匿名 struct：直接构建
                return StructType('', self._build_struct_members(node))

        if not isinstance(node, TypeSpecNode):
            return ERROR_T

        # 查找基础类型
        sym = self.table.lookup(node.base_name)
        if sym is None or sym.kind != SymbolKind.TYPE:
            self.diag.error(f"未知类型 '{node.base_name}'", node)
            return ERROR_T

        base_type = sym.gtype

        # 处理数组维度（从最后一维向外包装）
        if node.dimensions:
            result = base_type
            for dim_expr in reversed(node.dimensions):
                size = None
                if dim_expr is not None:
                    # 尝试静态求值数组大小
                    size = self._eval_const_int(dim_expr)
                    if size is None:
                        self.diag.error("数组大小必须是编译期常量整数表达式", dim_expr)
                result = ArrayType(result, size)
            return result

        return base_type

    def _eval_const_int(self, node) -> Optional[int]:
        """
        尝试在编译期对整数常量表达式求值。
        支持：整数字面量、const 变量、基本算术。
        返回 None 表示无法静态求值。
        """
        if isinstance(node, IntLiteral):
            return node.value
        # if isinstance(node, Identifier):
        #     sym = self.table.lookup(node.name)
        #     if sym and sym.is_const and isinstance(sym.gtype, BasicType):
        #         return None   # 暂时不跟踪 const 变量的值（可扩展）
        
        if isinstance(node, Identifier):
            sym = self.table.lookup(node.name)
            if sym and sym.is_const and sym.const_value is not None:
                return sym.const_value   # 改这里
            return None
        
        if isinstance(node, BinaryOp):
            l = self._eval_const_int(node.left)
            r = self._eval_const_int(node.right)
            if l is None or r is None:
                return None
            ops = {'+': l+r, '-': l-r, '*': l*r, '/': l//r if r else None, '%': l%r if r else None}
            return ops.get(node.op)
        if isinstance(node, UnaryOp) and node.op == '-':
            v = self._eval_const_int(node.operand)
            return -v if v is not None else None
        return None

    def _is_lvalue(self, node: ASTNode) -> bool:
        """判断节点是否是可赋值的左值"""
        if isinstance(node, Identifier):
            sym = self.table.lookup(node.name)
            if sym and sym.kind in (SymbolKind.FUNC, SymbolKind.TYPE):
                return False
            return True
        if isinstance(node, (ArrayAccess, MemberAccess)):
            return True
        return False

    @staticmethod
    def _expr_name(node: ASTNode) -> str:
        """提取表达式的简短名称（用于错误消息）"""
        if isinstance(node, Identifier):
            return node.name
        return str(type(node).__name__)
