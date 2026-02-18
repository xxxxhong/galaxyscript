from pywinauto import Application
import time

# 1. 精确连接到“脚本测试/报错”窗口
try:
    # 优先连接标题包含 "Script Test" 的窗口，这通常是报错列表所在的窗口
    app = Application(backend="win32").connect(title_re=".*Script Test.*")
    dlg = app.window(title_re=".*Script Test.*")
    print("成功连接到 Script Test 窗口")
except Exception:
    # 如果找不到，再尝试从主进程中筛选
    print("未直接找到 Script Test 窗口，尝试从编辑器主进程筛选...")
    app = Application(backend="win32").connect(title_re=".*StarCraft II Editor.*", found_index=0)
    dlg = app.window(title_re=".*Script Test.*")

if not dlg.exists():
    print("错误：依然无法定位报错窗口。")
    # 打印所有窗口标题，看看你的报错窗口到底叫什么
    print("当前所有窗口标题:", [w.window_text() for w in app.windows()])
    exit()

# 2. 尝试切换到 Files 标签并抓取
try:
    # 强制让窗口获得焦点
    dlg.set_focus()
    
    # 查找选项卡控件
    tabs = dlg.child_window(class_name="SysTabControl32")
    # 如果 select("Files") 失败，尝试用索引（通常 Files 是第二个，索引为 1）
    try:
        tabs.select("Files")
    except:
        tabs.select(1) 
    
    time.sleep(0.5)

    # 3. 提取 ListView 中的文件路径
    list_view = dlg.child_window(class_name="SysListView32")
    
    # 提取并过滤
    file_list = [item.text() for item in list_view.items() if item.text()]
    
    print(f"\n提取到 {len(file_list)} 个文件路径：")
    for path in file_list:
        print(path)

    # 保存结果
    with open("extracted_files.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(file_list))

except Exception as e:
    print(f"操作失败: {e}")
    # 打印控件树以诊断
    dlg.print_control_identifiers()

import os

# # --- 配置路径 ---
# # 提取出来的文件列表文件（每行一个路径）
# EXTRACTED_FILE = "extracted_files.txt" 
# # 本地库的根目录（即包含 ai.galaxy, natives.galaxy 的那一层）
# LOCAL_LIB_ROOT = r"E:\MARLenv\triggerlibs\mods\core.sc2mod\base.sc2data\triggerlibs"

# def compare_libs():
#     # 1. 读取编辑器提取的路径
#     with open(EXTRACTED_FILE, "r", encoding="utf-8") as f:
#         # 去掉 'TriggerLibs/' 前缀，并统一斜杠方向和大小写以便比对
#         remote_files = []
#         for line in f:
#             path = line.strip().replace("\\", "/").lower()
#             if path.startswith("triggerlibs/"):
#                 path = path[len("triggerlibs/"):]
#             if path:
#                 remote_files.append(path)

#     # 2. 扫描本地目录下的所有 galaxy 文件
#     local_files = []
#     for root, dirs, files in os.walk(LOCAL_LIB_ROOT):
#         for file in files:
#             if file.endswith(".galaxy"):
#                 # 获取相对于 LOCAL_LIB_ROOT 的路径
#                 full_path = os.path.join(root, file)
#                 rel_path = os.path.relpath(full_path, LOCAL_LIB_ROOT)
#                 local_files.append(rel_path.replace("\\", "/").lower())

#     # 3. 开始比对
#     remote_set = set(remote_files)
#     local_set = set(local_files)

#     missing_locally = remote_set - local_set
#     extra_locally = local_set - remote_set
#     matched = remote_set & local_set

#     # 4. 输出结果
#     print(f"--- 比对报告 ---")
#     print(f"编辑器引用数: {len(remote_set)}")
#     print(f"本地文件总数: {len(local_set)}")
#     print(f"完美匹配数:   {len(matched)}")
#     print(f"----------------\n")

#     if missing_locally:
#         print(f"❌ 本地缺失的文件 (编辑器有引用，但本地找不到):")
#         for f in sorted(missing_locally):
#             print(f"  - {f}")
#     else:
#         print(f"✅ 本地库包含所有编辑器引用的文件。")

#     print("\n")

#     if extra_locally:
#         print(f"⚠️  本地多余的文件 (本地有，但编辑器当前未引用):")
#         # 比如你看到的 buildai.galaxy, computer.galaxy 可能就在这里
#         for f in sorted(extra_locally):
#             print(f"  - {f}")

# if __name__ == "__main__":
#     compare_libs()