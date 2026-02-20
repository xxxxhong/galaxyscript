import os
from pathlib import Path
from lark import Lark

# ==================== 配置 ====================
GALAXY_DIR = r"D:\galaxyscript\galaxy_scripts"
OUTPUT_DIR = r"D:\galaxyscript\parse_output_earley_dynamic"
GRAMMAR_FILE = r"D:\galaxyscript\ANSI C95_V3.lark"

SUMMARY = os.path.join(OUTPUT_DIR, "summary.txt")
RESULT_DIR = os.path.join(OUTPUT_DIR, "trees")
# ==============================================

def get_parser(grammar):
    return Lark(grammar, parser="earley", ambiguity="resolve", propagate_positions=True)

def parse_to_pretty(parser, source_code):
    try:
        tree = parser.parse(source_code)
        return tree.pretty(), None
    except Exception as e:
        return None, str(e)

def process_all():
    os.makedirs(RESULT_DIR, exist_ok=True)

    with open(GRAMMAR_FILE, "r", encoding="utf-8") as f:
        grammar = f.read()

    parser = get_parser(grammar)

    galaxy_files = list(Path(GALAXY_DIR).rglob("*.galaxy"))
    total = len(galaxy_files)
    print(f"共找到 {total} 个 .galaxy 文件")

    ok_count = 0
    error_count = 0
    error_files = []

    with open(SUMMARY, "w", encoding="utf-8") as summary_f:
        summary_f.write(f"共 {total} 个文件\n")
        summary_f.write("=" * 60 + "\n\n")

        for i, filepath in enumerate(galaxy_files, 1):
            rel_path = filepath.relative_to(GALAXY_DIR)
            safe_name = str(rel_path).replace(os.sep, "__") + ".txt"

            print(f"[{i}/{total}] 处理: {rel_path}")

            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                source = f.read()

            pretty, err = parse_to_pretty(parser, source)

            out_path = os.path.join(RESULT_DIR, safe_name)
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(pretty if pretty else f"[ERROR]\n{err}")

            if err:
                status = "ERROR"
                error_count += 1
                error_files.append(str(rel_path))
                summary_f.write(f"[ERROR] {rel_path}\n  {err}\n\n")
            else:
                status = "OK"
                ok_count += 1

            print(f"        -> {status}")

        summary_f.write("\n" + "=" * 60 + "\n")
        summary_f.write(f"结果汇总:\n")
        summary_f.write(f"  成功 (OK):    {ok_count}\n")
        summary_f.write(f"  报错 (ERROR): {error_count}\n\n")

        if error_files:
            summary_f.write("报错的文件:\n")
            for p in error_files:
                summary_f.write(f"  {p}\n")

    print(f"\n完成! 成功:{ok_count} 报错:{error_count}")
    print(f"结果在: {OUTPUT_DIR}")

if __name__ == "__main__":
    process_all()