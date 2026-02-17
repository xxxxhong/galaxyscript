"""
Galaxy Script 批量语法验证工具
用法: python validate_galaxy.py
"""

import os
import sys
from datetime import datetime
from typing import Optional
from lark import Lark, exceptions

# ── 路径配置 ──────────────────────────────────────────────────────────────────
GRAMMAR_FILE   = r"D:\galaxyscript\ANSI C95.lark"
SCRIPTS_DIR    = r"D:\galaxyscript\galaxy_scripts"
SCRIPTS_DIR    = r"E:\SMAC_Auto-master\gen_history"
LOG_FILE       = r"D:\galaxyscript\validation_errors_6.log"
# ─────────────────────────────────────────────────────────────────────────────


def load_grammar(grammar_path: str) -> Lark:
    """加载 lark 语法文件，返回解析器"""
    with open(grammar_path, "r", encoding="utf-8") as f:
        grammar = f.read()
    return Lark(grammar, parser="lalr", propagate_positions=False)


def collect_scripts(scripts_dir: str) -> list:
    """递归收集目录下所有 .galaxy 文件"""
    results = []
    for root, _, files in os.walk(scripts_dir):
        for name in files:
            if name.endswith(".galaxy"):
                results.append(os.path.join(root, name))
    return sorted(results)


def validate_file(parser: Lark, filepath: str) -> Optional[str]:
    """
    解析单个文件。
    成功返回 None，失败返回错误描述字符串。
    """
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            source = f.read()
        parser.parse(source)
        return None
    except exceptions.UnexpectedCharacters as e:
        return (
            f"UnexpectedCharacters at line {e.line}, col {e.column}\n"
            f"  Expected: {e.expected}\n"
            f"  Context : {repr(e.char)}"
        )
    except exceptions.UnexpectedToken as e:
        return (
            f"UnexpectedToken '{e.token}' at line {e.line}, col {e.column}\n"
            f"  Expected: {e.expected}"
        )
    except exceptions.UnexpectedEOF as e:
        return (
            f"UnexpectedEOF\n"
            f"  Expected: {e.expected}"
        )
    except Exception as e:
        return f"{type(e).__name__}: {e}"


def main():
    # 1. 加载语法
    print(f"正在加载语法文件: {GRAMMAR_FILE}")
    try:
        parser = load_grammar(GRAMMAR_FILE)
    except Exception as e:
        print(f"[ERROR] 语法文件加载失败: {e}")
        sys.exit(1)
    print("语法文件加载成功\n")

    # 2. 收集脚本
    scripts = collect_scripts(SCRIPTS_DIR)
    if not scripts:
        print(f"[WARN] 未找到任何 .galaxy 文件: {SCRIPTS_DIR}")
        sys.exit(0)
    print(f"共找到 {len(scripts)} 个文件，开始验证...\n")

    # 3. 逐个验证
    errors: list = []
    for i, filepath in enumerate(scripts, 1):
        rel = os.path.relpath(filepath, SCRIPTS_DIR)
        error = validate_file(parser, filepath)
        if error is None:
            print(f"[{i:>4}/{len(scripts)}] OK       {rel}")
        else:
            print(f"[{i:>4}/{len(scripts)}] FAIL     {rel}")
            errors.append((filepath, error))

    # 4. 汇总输出
    print(f"\n验证完成: {len(scripts)} 个文件，{len(errors)} 个失败\n")

    if not errors:
        print("全部通过，无错误。")
        return

    # 5. 写入 log
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "w", encoding="utf-8") as log:
        log.write(f"Galaxy Script 语法验证报告\n")
        log.write(f"生成时间 : {timestamp}\n")
        log.write(f"语法文件 : {GRAMMAR_FILE}\n")
        log.write(f"脚本目录 : {SCRIPTS_DIR}\n")
        log.write(f"总计     : {len(scripts)} 个文件，{len(errors)} 个失败\n")
        log.write("=" * 72 + "\n\n")

        for filepath, error in errors:
            rel = os.path.relpath(filepath, SCRIPTS_DIR)
            log.write(f"FILE: {rel}\n")
            log.write(f"PATH: {filepath}\n")
            log.write(f"{error}\n")
            log.write("-" * 72 + "\n\n")

    print(f"错误详情已写入: {LOG_FILE}")


if __name__ == "__main__":
    main()
