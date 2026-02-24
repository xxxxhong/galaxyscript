"""
Galaxy Script 类型系统
======================
对应 Galaxy Script 支持的所有内置类型和复合类型。

Galaxy Script 是星际争霸II编辑器的脚本语言，类似于C语言，
但有一套专属的内置"句柄"类型（如 unit、trigger、region 等）。
"""


class GType:
    """所有类型的基类"""
    def __eq__(self, other):
        return isinstance(other, self.__class__)

    def __hash__(self):
        return hash(repr(self))

    def __repr__(self):
        return self.__class__.__name__


# ──────────────────────────────────────────────────────────────────────────────
# 基础标量类型
# ──────────────────────────────────────────────────────────────────────────────

class BasicType(GType):
    """基础标量类型（int、fixed、bool、string、void …）"""
    def __init__(self, name: str):
        self.name = name

    def __eq__(self, other):
        return isinstance(other, BasicType) and self.name == other.name

    def __hash__(self):
        return hash(self.name)

    def __repr__(self):
        return self.name


class HandleType(GType):
    """
    Galaxy Script 的句柄类型（unit、trigger、region 等）。
    句柄类型在语义上是不透明的引用，不能做算术，只能比较和传参。
    """
    def __init__(self, name: str):
        self.name = name

    def __eq__(self, other):
        return isinstance(other, HandleType) and self.name == other.name

    def __hash__(self):
        return hash(('handle', self.name))

    def __repr__(self):
        return self.name


# ──────────────────────────────────────────────────────────────────────────────
# 复合类型
# ──────────────────────────────────────────────────────────────────────────────

class ArrayType(GType):
    """数组类型，支持多维（Galaxy Script 用 int[8][8] 语法）"""
    def __init__(self, element_type: GType, size=None):
        self.element_type = element_type
        self.size = size          # None 表示在初始化时推断

    def __eq__(self, other):
        return isinstance(other, ArrayType) and self.element_type == other.element_type

    def __hash__(self):
        return hash(('array', self.element_type))

    def __repr__(self):
        size_str = str(self.size) if self.size is not None else ''
        return f"{self.element_type}[{size_str}]"


class FunctionType(GType):
    """函数类型（返回类型 + 参数类型列表）"""
    def __init__(self, return_type: GType, param_types: list):
        self.return_type = return_type
        self.param_types = param_types or []

    def __eq__(self, other):
        return (isinstance(other, FunctionType) and
                self.return_type == other.return_type and
                self.param_types == other.param_types)

    def __hash__(self):
        return hash(('func', self.return_type, tuple(self.param_types)))

    def __repr__(self):
        params = ', '.join(map(str, self.param_types))
        return f"{self.return_type}({params})"


class StructType(GType):
    """结构体类型"""
    def __init__(self, name: str, members: dict = None):
        self.name = name
        self.members = members  # {field_name: GType}，None 表示前向声明未完成

    def __eq__(self, other):
        return isinstance(other, StructType) and self.name == other.name

    def __hash__(self):
        return hash(('struct', self.name))

    def __repr__(self):
        return f"struct {self.name}"


class TypedefType(GType):
    """typedef 别名类型"""
    def __init__(self, name: str, underlying: GType):
        self.name = name
        self.underlying = underlying

    def resolve(self) -> GType:
        """递归解析到最终类型"""
        t = self.underlying
        while isinstance(t, TypedefType):
            t = t.underlying
        return t

    def __eq__(self, other):
        if isinstance(other, TypedefType):
            return self.name == other.name
        return self.resolve() == other

    def __hash__(self):
        return hash(('typedef', self.name))

    def __repr__(self):
        return self.name


# ──────────────────────────────────────────────────────────────────────────────
# 特殊哨兵类型（用于错误恢复，不对外暴露）
# ──────────────────────────────────────────────────────────────────────────────

class NullType(GType):
    """null 字面量的类型，可赋给任何句柄类型"""
    def __repr__(self):
        return 'null'


class ErrorType(GType):
    """
    语义错误恢复类型。
    当子表达式已经报过错时，父节点使用 ErrorType，
    避免产生大量级联错误。
    """
    def __repr__(self):
        return '<error>'

    def __eq__(self, other):
        return True   # ErrorType 与一切类型"兼容"，阻断级联错误

    def __hash__(self):
        return hash('error')


# ──────────────────────────────────────────────────────────────────────────────
# 预定义类型常量
# ──────────────────────────────────────────────────────────────────────────────

VOID    = BasicType('void')
INT     = BasicType('int')
FIXED   = BasicType('fixed')   # Galaxy Script 的定点小数
BOOL    = BasicType('bool')
STRING  = BasicType('string')
TEXT    = BasicType('text')     # 本地化文本，≠ string
NULL_T  = NullType()
ERROR_T = ErrorType()

# Galaxy Script 全部内置句柄类型
_HANDLE_NAMES = [
    'unit', 'unitgroup', 'unitfilter', 'unitref',
    'point', 'region', 'trigger', 'timer',
    'actor', 'actorscope',
    'wave', 'wavetarget', 'waveinfo',
    'sound', 'soundlink',
    'revealer', 'playergroup',
    'shuffler', 'color', 'abilcmd',
    'order', 'marker', 'bank', 'camerainfo',
    'aifilter', 'effecthistory', 'bitmask',
    'datetime', 'doodad', 'generichandle',
    'transmissionsource',
]

# 构建句柄类型字典，方便按名称查找
HANDLE_TYPES: dict[str, HandleType] = {n: HandleType(n) for n in _HANDLE_NAMES}

# 所有内置基础类型（用于初始化符号表）
BUILTIN_TYPES: dict[str, GType] = {
    'void': VOID, 'int': INT, 'integer': INT,   # integer 是 int 的别名
    'fixed': FIXED, 'bool': BOOL, 'boolean': BOOL,
    'string': STRING, 'text': TEXT,
    'byte': INT,   # 加这一行
    **HANDLE_TYPES,
}


# ──────────────────────────────────────────────────────────────────────────────
# 类型工具函数
# ──────────────────────────────────────────────────────────────────────────────

def is_numeric(t: GType) -> bool:
    """整数或定点数"""
    return t in (INT, FIXED)

def is_arithmetic(t: GType) -> bool:
    """可以做算术（+−*/）的类型"""
    return t in (INT, FIXED)

def is_comparable(t: GType) -> bool:
    """可以用 == / != 比较"""
    return isinstance(t, (BasicType, HandleType, NullType, ErrorType))

def is_orderable(t: GType) -> bool:
    """可以用 < > <= >= 比较"""
    return is_numeric(t) or t == STRING

def can_assign(dst: GType, src: GType) -> bool:
    """
    判断 src 能否赋值给 dst（隐式类型转换规则）。

    Galaxy Script 的转换规则远比 C 严格：
    - int  ↔ fixed 可以相互赋值（隐式转换）
    - bool ← int/fixed（非零为真）
    - null 可赋给任何句柄类型
    - ErrorType 与一切兼容（错误恢复）
    """
    if isinstance(dst, ErrorType) or isinstance(src, ErrorType):
        return True
    if dst == src:
        return True
    # int <-> fixed 互转
    if dst in (INT, FIXED) and src in (INT, FIXED):
        return True
    # bool 可以接受任何数值
    if dst == BOOL and is_numeric(src):
        return True
    # # null 可以赋给句柄
    # if isinstance(dst, HandleType) and isinstance(src, NullType):
    #     return True
    # null 可以赋给句柄
    if isinstance(dst, HandleType) and isinstance(src, NullType):
        return True
    # null 也可以赋给 string
    if dst == STRING and isinstance(src, NullType):
        return True
    # null 也可以赋给 text
    if dst == TEXT and isinstance(src, NullType):
        return True
    # typedef 透明穿透
    if isinstance(dst, TypedefType):
        return can_assign(dst.resolve(), src)
    if isinstance(src, TypedefType):
        return can_assign(dst, src.resolve())
    return False

def resolve_binary_op(op: str, ltype: GType, rtype: GType):
    """
    给定二元运算符和两个操作数类型，返回结果类型。
    无法推导时返回 None。
    """
    if isinstance(ltype, ErrorType) or isinstance(rtype, ErrorType):
        return ERROR_T

    # 算术：int op int → int；任一为 fixed → fixed
    if op in ('+', '-', '*', '/', '%'):
        if is_arithmetic(ltype) and is_arithmetic(rtype):
            return FIXED if FIXED in (ltype, rtype) else INT
        if op == '+' and ltype == STRING and rtype == STRING:
            return STRING   # 字符串拼接（Galaxy Script 支持）
        return None

    # 移位
    if op in ('<<', '>>'):
        if ltype == INT and rtype == INT:
            return INT
        return None

    # 位运算
    if op in ('&', '|', '^'):
        if ltype == INT and rtype == INT:
            return INT
        return None

    # 关系
    if op in ('<', '>', '<=', '>='):
        if is_orderable(ltype) and ltype == rtype:
            return BOOL
        if is_numeric(ltype) and is_numeric(rtype):
            return BOOL
        return None

    # 相等
    if op in ('==', '!='):
        # null 可以和任何非基础类型比较
        if ltype == NULL_T or rtype == NULL_T:
            return BOOL
        if is_comparable(ltype) and is_comparable(rtype):
            if can_assign(ltype, rtype) or can_assign(rtype, ltype):
                return BOOL
        return None

    # 逻辑
    if op in ('&&', '||'):
        if can_assign(BOOL, ltype) and can_assign(BOOL, rtype):
            return BOOL
        return None

    return None
