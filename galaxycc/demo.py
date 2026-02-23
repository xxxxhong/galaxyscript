#!/usr/bin/env python3
"""
GalaxyCC 使用示例
==================
展示如何将已有的 Lark grammar + 你的 900 个 .galaxy 文件
接入语义分析流水线。

假设目录结构：
  your_project/
    galaxy.lark         ← 你已有的 grammar 文件
    scripts/            ← 900+ .galaxy 脚本
    galaxycc/           ← 本项目代码
    demo.py             ← 本文件
"""

import sys
from pathlib import Path

# ── 如果 galaxycc 不在 sys.path，手动添加 ─────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent))

from galaxycc import GalaxyFrontend, COMMON_NATIVES


# ════════════════════════════════════════════════════════════════════════════
# 示例 1：分析内联字符串
# ════════════════════════════════════════════════════════════════════════════

SAMPLE_SOURCE = r"""
//==================================================================================================
include "TriggerLibs/natives"
include "TriggerLibs/AI"
include "TriggerLibs/Computer"

//--------------------------------------------------------------------------------------------------
// Globals
//--------------------------------------------------------------------------------------------------
point[17] ai0A40DCBA_defGather;
string[17] ai0A40DCBA_customData;
wave[17] ai0A40DCBA_lastWave;

//--------------------------------------------------------------------------------------------------
// Attack Wave Wrappers
//--------------------------------------------------------------------------------------------------
void ai0A40DCBA_wave_enable (int w, int p, bool val) {
}

//--------------------------------------------------------------------------------------------------
bool ai0A40DCBA_wave_isEnabled (int w, int p) {
    return false;
}
"""


def demo_inline():
    print("=" * 60)
    print("示例 1：分析内联源码")
    print("=" * 60)

    # 初始化前端（需要提供你的 .lark grammar 文件）
    # 如果 galaxy.lark 与本文件在同一目录：
    grammar_path = Path(__file__).parent / "galaxy.lark"

    if not grammar_path.exists():
        print(f"[跳过] 找不到 grammar 文件: {grammar_path}")
        print("请将你的 .lark 文件路径替换到 demo.py 中")
        demo_without_grammar()
        return

    frontend = GalaxyFrontend(grammar_file=grammar_path)

    # 加载常用内置函数（约 30 个常见 API）
    frontend.load_natives_common()


    # 可选：加载完整的 SC2 native 函数库
    # natives_path = Path("path/to/natives.galaxy")
    # count = frontend.load_natives_from_file(natives_path)
    # print(f"加载了 {count} 个 native 函数")

        # ── 加这几行调试 ──────────────────────────────
    cst = frontend.parse_only(SAMPLE_SOURCE)
    print("CST 根节点规则名:", cst.data)          # 应该是 'translation_unit'
    
    ast = frontend.transform_only(SAMPLE_SOURCE)
    print("AST 类型:", type(ast).__name__)         # 应该是 'TranslationUnit'
    # ──────────────────────────────────────────────
    
    # 分析源码
    result = frontend.process_string(SAMPLE_SOURCE, source_name="demo.galaxy")

    # 输出诊断信息
    if result.diags.count > 0:
        print(result.diags.report())
    else:
        print("✓ 分析成功，无错误/警告")

    # 输出符号表（调试用）
    if result.symbol_table:
        print("\n符号表：")
        print(result.symbol_table.dump())

    return result


def demo_without_grammar():
    """演示不依赖 grammar 的部分功能"""
    print("\n（无 grammar 模式：演示类型系统）")

    from galaxycc.semantic.type import INT, FIXED, BOOL, STRING, can_assign
    from galaxycc.semantic.type import resolve_binary_op

    cases = [
        (INT, FIXED, "int 赋值给 fixed"),
        (FIXED, INT, "fixed 赋值给 int"),
        (BOOL, INT, "int 赋值给 bool"),
        (STRING, INT, "int 赋值给 string（应为 False）"),
    ]
    print("\ncan_assign 测试：")
    for dst, src, desc in cases:
        print(f"  can_assign({dst}, {src}) = {can_assign(dst, src)}  ← {desc}")

    ops = [('+', INT, INT), ('+', INT, FIXED), ('*', FIXED, FIXED), ('+', STRING, STRING)]
    print("\nresolve_binary_op 测试：")
    for op, l, r in ops:
        result = resolve_binary_op(op, l, r)
        print(f"  {l} {op} {r} → {result}")


# ════════════════════════════════════════════════════════════════════════════
# 示例 2：批量分析 .galaxy 文件
# ════════════════════════════════════════════════════════════════════════════

def demo_batch(scripts_dir: str, grammar_path: str):
    """
    批量分析目录下所有 .galaxy 文件，汇总错误报告。

    Args:
        scripts_dir: 包含 .galaxy 文件的目录
        grammar_path: .lark grammar 文件路径
    """
    print("=" * 60)
    print("示例 2：批量分析")
    print("=" * 60)

    frontend = GalaxyFrontend(grammar_file=grammar_path, search_dirs=[r"D:\galaxyscript\SC2GameData-master\SC2GameData-master\mods\core.sc2mod\base.sc2data"])
    # frontend.load_natives_common()
    
    # 优先从真实文件加载，找不到再 fallback
    natives_path = r"D:\galaxyscript\cascviewer_galaxy_scripts\mods\core.sc2mod\base.sc2data\triggerlibs\natives.galaxy"
    if not frontend.load_natives_from_file(natives_path):
        print("[WARN] 未找到 natives.galaxy，使用内置定义（签名可能不准确）")
        frontend.load_natives_common()

    scripts = list(Path(scripts_dir).rglob("*.galaxy"))
    # scripts = list(Path(scripts_dir).rglob("*.galaxy"))[600:989]
    print(f"找到 {len(scripts)} 个 .galaxy 文件\n")

    total_errors   = 0
    total_warnings = 0
    failed_files   = []

    for script in scripts:
        result = frontend.process_file(script)
        errors   = len(result.diags.errors)
        warnings = len(result.diags.warnings)
        total_errors   += errors
        total_warnings += warnings

        if errors > 0:
            failed_files.append((script, result.diags))
            print(f"✗ {script.name}: {errors} error(s), {warnings} warning(s)")
            for d in result.diags.errors:
                print(f"  [{script.name}] {d}")
        elif warnings > 0:
            print(f"△ {script.name}: {warnings} warning(s)")
            for d in result.diags.warnings:
                print(f"  [{script.name}] {d}")
        else:
            print(f"✓ {script.name}")

    print(f"\n{'─' * 60}")
    print(f"总计: {total_errors} 错误, {total_warnings} 警告")
    print(f"失败文件: {len(failed_files)} / {len(scripts)}")

    # if failed_files:
    #     print("\n详细错误：")
    #     for path, diags in failed_files[:5]:   # 最多显示前 5 个
    #         print(f"\n  [{path.name}]")
    #         for d in diags.errors[:3]:          # 每个文件最多 3 条
    #             print(f"    {d}")
    # 另外单独打印有警告的文件
    # print("\n详细警告：")
    # for script in scripts:
    #     # result = frontend.process_file(script)
    #     # for d in result.diags.warnings:
    #     #     print(f"  [{script.name}] {d}")
    #     for d in result.diags.warnings:
    #         print(f"  [{script.name}] {d}")
# nohup python -u demo.py > output.log_semantic_errors_warnings 2>&1 &

# ════════════════════════════════════════════════════════════════════════════
# 示例 3：只做语义分析（跳过 Transformer，手动构建 AST）
# ════════════════════════════════════════════════════════════════════════════

def demo_analyzer_only():
    """
    直接使用 GalaxyAnalyzer，不经过 Lark。
    适合测试特定语义规则，或集成到其他工具链。
    """
    print("=" * 60)
    print("示例 3：直接使用 GalaxyAnalyzer")
    print("=" * 60)

    from galaxycc.semantic.analyzer import GalaxyAnalyzer
    from galaxycc.tree.transformer import (
        TranslationUnit, FuncDef, ParamDecl, CompoundStmt,
        ReturnStmt, BinaryOp, Identifier, IntLiteral,
        TypeSpecNode, VarDecl,
    )

    # 手动构建简单 AST：
    #   int add(int a, int b) { return a + b; }
    type_int = TypeSpecNode(base_name='int')

    param_a = ParamDecl(type_spec=type_int, name='a')
    param_b = ParamDecl(type_spec=type_int, name='b')

    a_id = Identifier(name='a')
    b_id = Identifier(name='b')
    add_expr = BinaryOp(op='+', left=a_id, right=b_id)
    ret_stmt = ReturnStmt(value=add_expr)

    body = CompoundStmt(items=[ret_stmt])
    func = FuncDef(type_spec=type_int, name='add', params=[param_a, param_b], body=body)

    ast = TranslationUnit(decls=[func])

    # 运行分析器
    analyzer = GalaxyAnalyzer()
    diag = analyzer.analyze(ast)

    if diag.has_errors:
        print(diag.report())
    else:
        print("✓ 手动 AST 语义分析通过")
        print(f"  add_expr.gtype = {add_expr.gtype}")
        print(f"  符号表：\n{analyzer.table.dump()}")


# ════════════════════════════════════════════════════════════════════════════
# 主入口
# ════════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    # demo_inline()
    # demo_analyzer_only()

    # 批量分析示例（按需取消注释）：
    demo_batch(
        scripts_dir="D:\galaxyscript\smallset",
        #scripts_dir="D:\galaxyscript\smallset",
        grammar_path="D:\galaxyscript\galaxycc\galaxy.lark",
    )
