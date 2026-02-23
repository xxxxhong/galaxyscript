"""
GalaxyCC - Galaxy Script 编译器前端
=====================================
模块结构：
  galaxycc/
    __init__.py          本文件：公共 API
    error.py             诊断信息系统
    tree/
      transformer.py     CST → AST 转换器 & AST 节点定义
    semantic/
      type.py            类型系统
      symbol.py          符号表
      analyzer.py        语义分析器
      natives.py         Native 函数加载器

快速使用示例：

    from galaxycc import GalaxyFrontend

    frontend = GalaxyFrontend()
    frontend.load_natives_from_dict(COMMON_NATIVES)   # 可选

    result = frontend.process_string(source_code)
    if result.diags.has_errors:
        print(result.diags.report())
    else:
        print("分析成功，符号表：")
        print(result.symbol_table.dump())
"""

from .pipeline import GalaxyFrontend, FrontendResult
from .error import DiagnosticBag, SemanticError
from .semantic.type import (
    VOID, INT, FIXED, BOOL, STRING, TEXT,
    GType, BasicType, HandleType, ArrayType, FunctionType, StructType,
)
from .semantic.natives import COMMON_NATIVES

__all__ = [
    'GalaxyFrontend', 'FrontendResult',
    'DiagnosticBag', 'SemanticError',
    'VOID', 'INT', 'FIXED', 'BOOL', 'STRING', 'TEXT',
    'GType', 'BasicType', 'HandleType', 'ArrayType', 'FunctionType', 'StructType',
    'COMMON_NATIVES',
]
