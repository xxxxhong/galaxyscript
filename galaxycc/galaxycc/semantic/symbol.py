"""
Galaxy Script 符号表
====================
实现作用域嵌套的符号表，支持全局 / 函数 / 块级作用域。

Galaxy Script 特性：
  - 支持 static（静态局部变量，在函数外部初始化但作用域在函数内）
  - 支持 const 修饰符
  - 支持 typedef 别名
  - 支持 native 函数声明（外部函数，无函数体）
"""

from enum import Enum, auto
from .type import GType


class SymbolKind(Enum):
    VAR      = auto()   # 普通变量
    CONST    = auto()   # const 常量
    FUNC     = auto()   # 函数（含 native）
    TYPE     = auto()   # typedef / struct 类型名
    PARAM    = auto()   # 函数形参（用于区分局部变量）


class Symbol:
    """
    符号表条目。

    Attributes:
        name:     符号名
        gtype:    Galaxy 类型（GType 实例）
        kind:     SymbolKind
        is_static:  static 局部变量
        is_native:  native 函数（无函数体）
        is_const:   const 修饰
        defined:  函数是否已有函数体（用于检测重定义）
        node:     对应的 Lark Tree 节点（用于报错定位）
    """
    def __init__(self, name: str, gtype: GType, kind: SymbolKind, *,
                 is_static=False, is_native=False, is_const=False,
                 defined=True, node=None):
        self.name      = name
        self.gtype     = gtype
        self.kind      = kind
        self.is_static = is_static
        self.is_native = is_native
        self.is_const  = is_const
        self.defined   = defined
        self.node      = node

    def __repr__(self):
        flags = []
        if self.is_static: flags.append('static')
        if self.is_native: flags.append('native')
        if self.is_const:  flags.append('const')
        flag_str = ' '.join(flags)
        return f"Symbol({self.kind.name} {flag_str} {self.gtype} {self.name!r})"


class Scope:
    """单个作用域（一个哈希表）"""
    def __init__(self, name: str = ''):
        self.name    = name
        self._table: dict[str, Symbol] = {}

    def define(self, sym: Symbol) -> bool:
        if sym.name in self._table:
            return False
        self._table[sym.name] = sym
        return True

    def lookup_local(self, name: str):
        return self._table.get(name)

    def symbols(self):
        return self._table.values()


class SymbolTable:
    """
    嵌套作用域符号表。

    作用域层次：
      global → function-param → block → block …
    """
    def __init__(self):
        self._scopes: list[Scope] = []
        self._enter('global')

    # ── 作用域管理 ──────────────────────────────────────────────────────────

    def _enter(self, name: str = ''):
        self._scopes.append(Scope(name))

    def enter_global(self):
        """已在 __init__ 中建立，外部一般不需调用"""
        pass

    def enter_function(self, func_name: str):
        self._enter(f'func:{func_name}')

    def enter_block(self):
        self._enter('block')

    def leave_scope(self):
        if len(self._scopes) > 1:
            self._scopes.pop()

    @property
    def current_scope(self) -> Scope:
        return self._scopes[-1]

    @property
    def is_global(self) -> bool:
        return len(self._scopes) == 1

    # ── 符号操作 ────────────────────────────────────────────────────────────

    def define(self, sym: Symbol) -> bool:
        """在当前作用域定义符号，重复定义返回 False"""
        return self.current_scope.define(sym)

    def lookup(self, name: str) -> Symbol | None:
        """从最内层作用域向外查找"""
        for scope in reversed(self._scopes):
            sym = scope.lookup_local(name)
            if sym is not None:
                return sym
        return None

    def lookup_local(self, name: str) -> Symbol | None:
        """仅在当前作用域查找（用于检测同层重定义）"""
        return self.current_scope.lookup_local(name)

    def lookup_global(self, name: str) -> Symbol | None:
        """仅查全局作用域"""
        return self._scopes[0].lookup_local(name)

    # ── 调试辅助 ────────────────────────────────────────────────────────────

    def dump(self) -> str:
        lines = []
        for i, scope in enumerate(self._scopes):
            indent = '  ' * i
            lines.append(f"{indent}[{scope.name}]")
            for sym in scope.symbols():
                lines.append(f"{indent}  {sym}")
        return '\n'.join(lines)
