"""
Galaxy Script Native 函数加载器
================================
Galaxy Script 的标准库（SC2 Editor 的 native 函数）数量庞大（数千个）。
本模块提供两种加载方式：

  1. 从 .galaxy 文件（native 声明文件）解析，这是最准确的方式
  2. 从手工维护的字典加载（用于快速原型开发）

典型的 native 声明文件就是星际争霸II安装目录下的：
  Mods/Core.SC2Mod/Base.SC2Data/TriggerLibs/natives.galaxy

用法示例：
    loader = NativeLoader()
    loader.load_from_file("path/to/natives.galaxy")
    builtins = loader.get_builtins()   # dict[str, FunctionType]

    analyzer = GalaxyAnalyzer(native_builtins=builtins)
"""

from __future__ import annotations
import re
from pathlib import Path

from .type import (
    GType, FunctionType, ArrayType,
    VOID, INT, FIXED, BOOL, STRING, TEXT, ERROR_T,
    BUILTIN_TYPES, HANDLE_TYPES,
)


# 解析 native 声明行的简单正则
# native void TriggerExecute(trigger t, bool immediate, bool wait);
_NATIVE_RE = re.compile(
    r'native\s+'
    r'(?P<ret>\w+)(?:\[[\d\s]*\])?\s+'       # 返回类型（可带数组维度）
    r'(?P<name>[a-zA-Z_]\w*)\s*'              # 函数名
    r'\((?P<params>[^)]*)\)\s*;'              # 参数列表
)

_PARAM_RE = re.compile(
    r'(?:const\s+)?(?P<type>\w+)(?:\[[\d\s]*\])?\s+(?P<name>[a-zA-Z_]\w*)'
)


def _parse_type_str(type_str: str, array_suffix: str = '') -> GType:
    """将类型字符串解析为 GType（仅处理 native 文件中出现的简单类型）"""
    name = type_str.strip()
    # 类型别名统一
    if name in ('integer', 'int'):
        gtype = INT
    elif name in ('boolean', 'bool'):
        gtype = BOOL
    elif name == 'fixed':
        gtype = FIXED
    elif name == 'string':
        gtype = STRING
    elif name == 'text':
        gtype = TEXT
    elif name == 'void':
        gtype = VOID
    elif name in HANDLE_TYPES:
        gtype = HANDLE_TYPES[name]
    else:
        gtype = BUILTIN_TYPES.get(name, ERROR_T)

    # 处理数组维度（简化：只支持一维）
    if array_suffix and '[' in array_suffix:
        gtype = ArrayType(gtype)

    return gtype


class NativeLoader:
    """
    加载 native 函数声明。
    """
    def __init__(self):
        self._funcs: dict[str, FunctionType] = {}
        self._load_errors: list[str] = []

    def load_from_file(self, path: str | Path) -> int:
        """
        从 .galaxy 文件加载 native 函数。
        返回成功加载的函数数量。
        """
        path = Path(path)
        if not path.exists():
            self._load_errors.append(f"文件不存在: {path}")
            return 0

        count = 0
        with open(path, encoding='utf-8', errors='replace') as f:
            for line in f:
                line = line.strip()
                m = _NATIVE_RE.match(line)
                if not m:
                    continue

                ret_str  = m.group('ret')
                func_name = m.group('name')
                params_str = m.group('params').strip()

                ret_type = _parse_type_str(ret_str)
                param_types = self._parse_params(params_str)

                self._funcs[func_name] = FunctionType(ret_type, param_types)
                count += 1

        return count

    def load_from_dict(self, definitions: dict[str, tuple]):
        """
        从手工维护的字典加载（快速原型）。

        definitions 格式：
          {
            'func_name': ('return_type_str', ['param_type_str', ...]),
            ...
          }
        """
        for name, (ret_str, param_strs) in definitions.items():
            ret_type    = _parse_type_str(ret_str)
            param_types = [_parse_type_str(p) for p in param_strs]
            self._funcs[name] = FunctionType(ret_type, param_types)

    def get_builtins(self) -> dict[str, FunctionType]:
        """返回已加载的函数类型字典"""
        return dict(self._funcs)

    @property
    def load_errors(self):
        return list(self._load_errors)

    def _parse_params(self, params_str: str) -> list[GType]:
        if not params_str or params_str.lower() == 'void':
            return []
        types = []
        for part in params_str.split(','):
            part = part.strip()
            if not part:
                continue
            m = _PARAM_RE.search(part)
            if m:
                types.append(_parse_type_str(m.group('type')))
            else:
                # 回退：取第一个词
                first_word = part.split()[0] if part.split() else ''
                if first_word:
                    types.append(_parse_type_str(first_word))
        return types


# ─── 内置常用函数的手工定义（用于不依赖 natives.galaxy 的快速测试）─────────────

COMMON_NATIVES = {
    # 调试 / 控制台
    'TriggerDebugOutput': ('void',  ['int', 'text', 'bool']),
    'TriggerDebugWindowShow': ('void', ['bool']),

    # 单位操作
    'UnitCreate':  ('unit',  ['int', 'string', 'int', 'int', 'point', 'fixed']),
    'UnitKill':    ('void',  ['unit']),
    'UnitRemove':  ('void',  ['unit']),
    'UnitSetPosition': ('void', ['unit', 'point', 'bool']),
    'UnitGetPosition': ('point', ['unit']),
    'UnitGetOwner': ('int',  ['unit']),
    'UnitIsAlive':  ('bool', ['unit']),
    'UnitOrder':    ('void', ['unit', 'order']),
    'UnitGroupCount': ('int', ['unitgroup', 'int']),

    # 玩家操作
    'PlayerSetResource': ('void', ['int', 'string', 'int']),
    'PlayerGetResource': ('int',  ['int', 'string']),

    # 坐标 / 点
    'Point':        ('point', ['fixed', 'fixed']),
    'PointX':       ('fixed', ['point']),
    'PointY':       ('fixed', ['point']),
    'PointFromUnit': ('point', ['unit']),
    'DistanceBetweenPoints': ('fixed', ['point', 'point']),

    # 触发器
    'TriggerCreate': ('trigger', ['string']),
    'TriggerEnable': ('void', ['trigger', 'bool']),
    'TriggerDestroy': ('void', ['trigger']),
    'TriggerExecute': ('void', ['trigger', 'bool', 'bool']),

    # 计时器
    'TimerCreate':  ('timer', []),
    'TimerStart':   ('void', ['timer', 'fixed', 'bool']),
    'TimerStop':    ('void', ['timer']),
    'TimerGetElapsed': ('fixed', ['timer']),
    'TimerGetRemaining': ('fixed', ['timer']),

    # 字符串 / 文本
    'StringLength': ('int', ['string']),
    'StringSub':    ('string', ['string', 'int', 'int']),
    'StringCase':   ('string', ['string', 'bool']),
    'IntToString':  ('string', ['int']),
    'FixedToString': ('string', ['fixed', 'int']),
    'StringToInt':  ('int', ['string']),
    'StringToFixed': ('fixed', ['string']),

    # 数学
    'Abs':   ('fixed', ['fixed']),
    'Cos':   ('fixed', ['fixed']),
    'Sin':   ('fixed', ['fixed']),
    'Sqrt':  ('fixed', ['fixed']),
    'Pow':   ('fixed', ['fixed', 'fixed']),
    'MinI':  ('int',   ['int', 'int']),
    'MaxI':  ('int',   ['int', 'int']),
    'MinF':  ('fixed', ['fixed', 'fixed']),
    'MaxF':  ('fixed', ['fixed', 'fixed']),

    # 随机
    'RandomInt':   ('int',   ['int', 'int']),
    'RandomFixed': ('fixed', ['fixed', 'fixed']),
}
