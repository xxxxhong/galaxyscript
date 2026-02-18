"""
Galaxy Script 批量语法验证工具（含语义分析）
用法: python validate_galaxy.py
"""

import os
import re
import sys
from datetime import datetime
from typing import Optional
from lark import Lark, exceptions

# ── 路径配置 ──────────────────────────────────────────────────────────────────
GRAMMAR_FILE = r"D:\galaxyscript\ANSI C95_V2.lark"
SCRIPTS_DIR  = r"D:\galaxyscript\galaxy_scripts"
LOG_FILE     = r"D:\galaxyscript\validation_errors.log"
# ─────────────────────────────────────────────────────────────────────────────

# 已知内置类型，预处理时不替换这些
BUILTIN_TYPES = {
    'void', 'int', 'fixed', 'bool', 'string',
    'unitfilter', 'unitgroup', 'unit', 'point', 'timer',
    'region', 'trigger', 'wave', 'actor', 'revealer',
    'playergroup', 'text', 'sound', 'soundlink', 'color',
    'abilcmd', 'order', 'marker', 'bank', 'camerainfo',
    'actorscope', 'aifilter', 'wavetarget', 'effecthistory',
    'bitmask', 'datetime', 'doodad', 'generichandle',
    'transmissionsource', 'unitref', 'waveinfo', 'entryset',
    'boolean', 'integer',
}


# ── 语法解析相关 ──────────────────────────────────────────────────────────────

def load_grammar(grammar_path: str) -> Lark:
    """加载 lark 语法文件，返回解析器（开启行列号记录）"""
    with open(grammar_path, "r", encoding="utf-8") as f:
        grammar = f.read()
    # return Lark(grammar, parser="lalr", propagate_positions=True)
    return Lark(grammar, parser="earley", ambiguity="resolve", propagate_positions=True)


def collect_scripts(scripts_dir: str) -> list:
    """递归收集目录下所有 .galaxy 文件"""
    results = []
    for root, _, files in os.walk(scripts_dir):
        for name in files:
            if name.endswith(".galaxy"):
                results.append(os.path.join(root, name))
    return sorted(results)


def collect_all_type_names(scripts: list) -> set:
    """第一遍扫描所有文件，用正则收集用户自定义类型名。"""
    type_names = set()
    for filepath in scripts:
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                source = f.read()
        except Exception:
            continue
        for m in re.finditer(r'\bstruct\s+([a-zA-Z_][a-zA-Z0-9_]*)', source):
            type_names.add(m.group(1))
        for m in re.finditer(r'\btypedef\s+\S+\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*;', source):
            type_names.add(m.group(1))
    type_names -= BUILTIN_TYPES
    return type_names


def preprocess(source: str, type_names: set) -> str:
    """预处理：替换自定义类型名和 structref<T>"""
    if type_names:
        pattern = r'\b(' + '|'.join(
            re.escape(n) for n in sorted(type_names, key=len, reverse=True)
        ) + r')\b'
        source = re.sub(pattern, 'int', source)
    source = re.sub(r'\bstructref\s*<[^>]+>', 'int', source)
    return source


def classify_syntax_error(e: exceptions.UnexpectedToken) -> str:
    token_str = str(e.token)
    if token_str == '':
        return f"[文件截断] 文件在 line {e.line}, col {e.column} 处意外结束"
    return (
        f"UnexpectedToken '{e.token}' at line {e.line}, col {e.column}\n"
        f"  Expected: {e.expected}"
    )


# ── 语义分析相关 ──────────────────────────────────────────────────────────────

def run_semantic_analysis(tree, global_table) -> list:
    """
    在语法树上运行作用域分析，返回语义错误列表。
    导入延迟到这里，避免循环依赖。
    """
    from scope_analyzer import ScopeAnalyzer
    analyzer = ScopeAnalyzer(global_table)
    analyzer.visit(tree)
    return analyzer.errors


def build_global_symbol_table(trees: list):
    """
    对所有文件的 AST 做第一遍扫描，建立全局符号表。
    trees: [(filepath, tree), ...]
    返回 (SymbolTable, [收集时发现的错误])
    """
    from symbol_collector import SymbolCollector, SymbolTable

    # 合并所有文件的符号到一张全局表
    merged_table = SymbolTable()
    all_collector_errors = []

    for filepath, tree in trees:
        collector = SymbolCollector()
        collector.visit(tree)

        # 把收集到的符号合并进全局表
        for name, info in collector.table.symbols.items():
            existing = merged_table.declare(info)
            # 跨文件的重复只对函数定义报错，变量重复忽略（可能是头文件多次包含）

        for name, fields in collector.table.structs.items():
            merged_table.declare_struct(name, fields)

        # 收集符号收集阶段发现的错误（同文件内重复声明）
        for err in collector.errors:
            all_collector_errors.append((filepath, err))

    return merged_table, all_collector_errors


# ── 单文件验证 ────────────────────────────────────────────────────────────────

class FileResult:
    """单个文件的验证结果"""
    def __init__(self, filepath: str):
        self.filepath        = filepath
        self.syntax_error    = None    # str 或 None
        self.semantic_errors = []      # [ScopeError, ...]
        self.is_truncated    = False

    @property
    def has_error(self) -> bool:
        return self.syntax_error is not None or bool(self.semantic_errors)

    @property
    def status(self) -> str:
        if self.is_truncated:
            return "TRUNCATE"
        if self.syntax_error:
            return "SYNTAX  "
        if self.semantic_errors:
            return "SEMANTIC"
        return "OK      "


def parse_file(parser: Lark, filepath: str, type_names: set):
    """
    语法解析单个文件，返回 (tree, syntax_error_str, is_truncated)。
    tree 为 None 表示解析失败。
    """
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            source = f.read()
        source = preprocess(source, type_names)
        tree = parser.parse(source)
        return tree, None, False

    except exceptions.UnexpectedCharacters as e:
        err = (
            f"UnexpectedCharacters at line {e.line}, col {e.column}\n"
            f"  Expected: {e.expected}\n"
            f"  Context : {repr(e.char)}"
        )
        return None, err, False

    except exceptions.UnexpectedToken as e:
        err = classify_syntax_error(e)
        truncated = str(e.token) == ''
        return None, err, truncated

    except exceptions.UnexpectedEOF as e:
        return None, f"[文件截断] 文件意外结束\n  Expected: {e.expected}", True

    except Exception as e:
        return None, f"{type(e).__name__}: {e}", False


# ── 主流程 ────────────────────────────────────────────────────────────────────

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
    print(f"共找到 {len(scripts)} 个文件\n")

    # 3. 全局收集自定义类型名（预处理用）
    print("正在收集自定义类型名...")
    type_names = collect_all_type_names(scripts)
    print(f"收集到 {len(type_names)} 个自定义类型名\n")

    # 4. 第一遍：语法解析，收集所有 AST
    print("第一遍：语法解析...")
    results = {}
    valid_trees = []   # [(filepath, tree), ...]

    for i, filepath in enumerate(scripts, 1):
        rel = os.path.relpath(filepath, SCRIPTS_DIR)
        result = FileResult(filepath)
        tree, syntax_err, truncated = parse_file(parser, filepath, type_names)

        if syntax_err:
            result.syntax_error = syntax_err
            result.is_truncated = truncated
            print(f"  [{i:>4}/{len(scripts)}] {result.status} {rel}")
        else:
            valid_trees.append((filepath, tree))
            print(f"  [{i:>4}/{len(scripts)}] OK       {rel}")

        results[filepath] = result

    syntax_fail = sum(1 for r in results.values() if r.syntax_error)
    print(f"\n语法解析完成: {len(scripts) - syntax_fail} 通过 / {syntax_fail} 失败\n")

    # 5. 第二遍：建立全局符号表
    print("第二遍：建立全局符号表...")
    global_table, collector_errors = build_global_symbol_table(valid_trees)
    print(f"收集到 {len(global_table.symbols)} 个全局符号\n")

    # 把符号收集阶段的错误附加到对应文件
    for filepath, err_dict in collector_errors:
        if filepath in results:
            from scope_analyzer import ScopeError
            results[filepath].semantic_errors.append(ScopeError(
                kind=err_dict['kind'],
                message=err_dict['message'],
                line=err_dict['line'],
                col=err_dict['col'],
            ))

    # 6. 第三遍：作用域分析
    print("第三遍：作用域语义分析...")
    for i, (filepath, tree) in enumerate(valid_trees, 1):
        rel = os.path.relpath(filepath, SCRIPTS_DIR)
        try:
            semantic_errors = run_semantic_analysis(tree, global_table)
            results[filepath].semantic_errors.extend(semantic_errors)
            status = "SEMANTIC" if semantic_errors else "OK      "
            print(f"  [{i:>4}/{len(valid_trees)}] {status} {rel}"
                  + (f" ({len(semantic_errors)} 个问题)" if semantic_errors else ""))
        except Exception as e:
            print(f"  [{i:>4}/{len(valid_trees)}] ERROR    {rel} (语义分析异常: {e})")

    # 7. 汇总
    syntax_errors   = [r for r in results.values() if r.syntax_error and not r.is_truncated]
    truncated_files = [r for r in results.values() if r.is_truncated]
    semantic_errors = [r for r in results.values() if r.semantic_errors]
    ok_files        = [r for r in results.values() if not r.has_error]

    print(f"\n{'='*60}")
    print(f"验证完成: {len(scripts)} 个文件")
    print(f"  ✅ 通过:     {len(ok_files)} 个")
    print(f"  ❌ 语法错误: {len(syntax_errors)} 个")
    print(f"  ⚠️  文件截断: {len(truncated_files)} 个")
    print(f"  🔍 语义问题: {len(semantic_errors)} 个文件，"
          f"共 {sum(len(r.semantic_errors) for r in semantic_errors)} 处")
    print(f"{'='*60}\n")

    if not any(r.has_error for r in results.values()):
        print("全部通过，无错误。")
        return

    # 8. 写入 log
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "w", encoding="utf-8") as log:
        log.write("Galaxy Script 语法+语义验证报告\n")
        log.write(f"生成时间 : {timestamp}\n")
        log.write(f"语法文件 : {GRAMMAR_FILE}\n")
        log.write(f"脚本目录 : {SCRIPTS_DIR}\n")
        log.write(
            f"总计     : {len(scripts)} 个文件 / "
            f"语法错误 {len(syntax_errors)} 个 / "
            f"文件截断 {len(truncated_files)} 个 / "
            f"语义问题 {len(semantic_errors)} 个文件\n"
        )
        log.write("=" * 72 + "\n\n")

        # 语法错误
        if syntax_errors:
            log.write("【语法错误】\n")
            log.write("=" * 72 + "\n\n")
            for r in syntax_errors:
                rel = os.path.relpath(r.filepath, SCRIPTS_DIR)
                log.write(f"FILE: {rel}\n")
                log.write(f"PATH: {r.filepath}\n")
                log.write(f"{r.syntax_error}\n")
                log.write("-" * 72 + "\n\n")

        # 文件截断
        if truncated_files:
            log.write("【文件截断（内容不完整，非语法错误）】\n")
            log.write("=" * 72 + "\n\n")
            for r in truncated_files:
                rel = os.path.relpath(r.filepath, SCRIPTS_DIR)
                log.write(f"FILE: {rel}\n")
                log.write(f"PATH: {r.filepath}\n")
                log.write(f"{r.syntax_error}\n")
                log.write("-" * 72 + "\n\n")

        # 语义问题
        if semantic_errors:
            log.write("【语义问题】\n")
            log.write("=" * 72 + "\n\n")
            for r in semantic_errors:
                rel = os.path.relpath(r.filepath, SCRIPTS_DIR)
                log.write(f"FILE: {rel}\n")
                log.write(f"PATH: {r.filepath}\n")
                for err in r.semantic_errors:
                    log.write(f"  {err}\n")
                log.write("-" * 72 + "\n\n")

    print(f"错误详情已写入: {LOG_FILE}")


if __name__ == "__main__":
    main()
