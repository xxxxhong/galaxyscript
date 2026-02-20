import os
import difflib
from pathlib import Path
from lark import Lark

# ==================== 配置 ====================
GALAXY_DIR = r"D:\galaxyscript\galaxy_scripts"
OUTPUT_DIR = r"D:\galaxyscript\parse_output_WITHOUT_TYPE_NAME"
GRAMMAR_FILE = r"D:\galaxyscript\ANSI C95_V2.lark"  # 改成你的语法文件路径

MODE_A_DIR = os.path.join(OUTPUT_DIR, "mode_a_earley")
MODE_B_DIR = os.path.join(OUTPUT_DIR, "mode_b_lalr")
DIFF_DIR   = os.path.join(OUTPUT_DIR, "diffs")
SUMMARY    = os.path.join(OUTPUT_DIR, "summary.txt")
# ==============================================

def get_parser_a(grammar):
    """Earley 模式"""
    return Lark(grammar, parser="earley", lexer="standard", ambiguity="resolve", propagate_positions=True)

def get_parser_b(grammar):
    """LALR 模式"""
    return Lark(grammar, parser="lalr", propagate_positions=True)

def parse_to_pretty(parser, source_code):
    """解析并返回 pretty 字符串，失败返回错误信息"""
    try:
        tree = parser.parse(source_code)
        return tree.pretty(), None
    except Exception as e:
        return None, str(e)

def process_all():
    # 创建输出目录
    for d in [MODE_A_DIR, MODE_B_DIR, DIFF_DIR]:
        os.makedirs(d, exist_ok=True)

    # 读取语法
    with open(GRAMMAR_FILE, "r", encoding="utf-8") as f:
        grammar = f.read()

    parser_a = get_parser_a(grammar)
    parser_b = get_parser_b(grammar)

    galaxy_files = list(Path(GALAXY_DIR).rglob("*.galaxy"))
    total = len(galaxy_files)
    print(f"共找到 {total} 个 .galaxy 文件")

    same_count    = 0
    diff_count    = 0
    error_count   = 0
    error_files   = []
    diff_files    = []

    with open(SUMMARY, "w", encoding="utf-8") as summary_f:
        summary_f.write(f"共 {total} 个文件\n")
        summary_f.write("=" * 60 + "\n\n")

        for i, filepath in enumerate(galaxy_files, 1):
            rel_path = filepath.relative_to(GALAXY_DIR)
            # 用相对路径作为输出文件名（替换路径分隔符避免嵌套）
            safe_name = str(rel_path).replace(os.sep, "__") + ".txt"

            print(f"[{i}/{total}] 处理: {rel_path}")

            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                source = f.read()

            pretty_a, err_a = parse_to_pretty(parser_a, source)
            pretty_b, err_b = parse_to_pretty(parser_b, source)

            # —— 写入各自输出 ——
            out_a = os.path.join(MODE_A_DIR, safe_name)
            out_b = os.path.join(MODE_B_DIR, safe_name)

            with open(out_a, "w", encoding="utf-8") as f:
                f.write(pretty_a if pretty_a else f"[ERROR]\n{err_a}")

            with open(out_b, "w", encoding="utf-8") as f:
                f.write(pretty_b if pretty_b else f"[ERROR]\n{err_b}")

            # —— 判断状态 ——
            if err_a or err_b:
                status = "ERROR"
                error_count += 1
                error_files.append(str(rel_path))
                detail = ""
                if err_a:
                    detail += f"  [Earley 报错] {err_a}\n"
                if err_b:
                    detail += f"  [LALR   报错] {err_b}\n"
                summary_f.write(f"[ERROR] {rel_path}\n{detail}\n")

            elif pretty_a == pretty_b:
                status = "SAME"
                same_count += 1
                # 相同的不写 diff 文件，summary 也可以选择不记录
                # summary_f.write(f"[SAME]  {rel_path}\n")

            else:
                status = "DIFF"
                diff_count += 1
                diff_files.append(str(rel_path))

                # 生成 unified diff
                diff = difflib.unified_diff(
                    (pretty_b or "").splitlines(keepends=True),
                    (pretty_a or "").splitlines(keepends=True),
                    fromfile=f"LALR:   {rel_path}",
                    tofile=  f"Earley: {rel_path}",
                    lineterm=""
                )
                diff_text = "".join(diff)

                diff_path = os.path.join(DIFF_DIR, safe_name)
                with open(diff_path, "w", encoding="utf-8") as f:
                    f.write(diff_text)

                summary_f.write(f"[DIFF]  {rel_path}\n")

            print(f"        -> {status}")

        # —— 写汇总 ——
        summary_f.write("\n" + "=" * 60 + "\n")
        summary_f.write(f"结果汇总:\n")
        summary_f.write(f"  相同 (SAME):  {same_count}\n")
        summary_f.write(f"  有差异(DIFF): {diff_count}\n")
        summary_f.write(f"  报错 (ERROR): {error_count}\n\n")

        if diff_files:
            summary_f.write("有差异的文件:\n")
            for p in diff_files:
                summary_f.write(f"  {p}\n")

        if error_files:
            summary_f.write("\n报错的文件:\n")
            for p in error_files:
                summary_f.write(f"  {p}\n")

    print(f"\n完成! 相同:{same_count} 差异:{diff_count} 报错:{error_count}")
    print(f"结果在: {OUTPUT_DIR}")

if __name__ == "__main__":
    process_all()