# GalaxyCC 项目设计文档

> Galaxy Script（星际争霸II编辑器脚本语言）编译器前端，参考 AnanasCC 架构。

---

## 一、整体架构

```
源码字符串 / .galaxy 文件
        │
        ▼
┌───────────────────┐
│   Lark Parser     │  词法 + 语法分析（你已完成的 grammar）
│   (galaxy.lark)   │
└────────┬──────────┘
         │  Lark Tree（CST，具体语法树）
         ▼
┌───────────────────┐
│ GalaxyTransformer │  CST → AST 转换（tree/transformer.py）
└────────┬──────────┘
         │  TranslationUnit（AST 根节点）
         ▼
┌───────────────────┐
│ GalaxyAnalyzer    │  语义分析（semantic/analyzer.py）
│   · 符号表构建    │
│   · 类型推导      │
│   · 错误检测      │
└────────┬──────────┘
         │  DiagnosticBag + 带类型注解的 AST
         ▼
     FrontendResult
```

---

## 二、与 AnanasCC 的对应关系

| AnanasCC 模块 | GalaxyCC 对应模块 | 主要差异 |
|---|---|---|
| `lexer/lexer.py` + `lexer/lexicon.lark` | 你的 `galaxy.lark` | Galaxy 有大量内置句柄类型 |
| `parser/parser.py` + `parser/syntax.lark` | 你的 `galaxy.lark`（合并） | 同上 |
| `tree/transformer.py` | `galaxycc/tree/transformer.py` | Galaxy 无指针，有 native |
| `tree/tree.py` | `galaxycc/tree/transformer.py`（合并）| 用 dataclass 代替手写类 |
| `semantic/type.py` | `galaxycc/semantic/type.py` | 新增 fixed、HandleType、NullType |
| `semantic/symbol.py` | `galaxycc/semantic/symbol.py` | 新增 is_native、is_static |
| `semantic/analyzer.py` | `galaxycc/semantic/analyzer.py` | 两遍扫描处理前向引用 |
| — | `galaxycc/semantic/natives.py` | Galaxy 独有：native API 加载 |
| `compiler/compiler.py` | `galaxycc/pipeline.py` | 流水线封装 |

---

## 三、模块详解

### 3.1 类型系统（`semantic/type.py`）

Galaxy Script 的类型系统比 C 简单，但有自己的特色：

```
GType（所有类型基类）
├── BasicType      void / int / fixed / bool / string / text
├── HandleType     unit / unitgroup / trigger / timer / region …（30+ 个）
├── ArrayType      可多维，尺寸在编译期确定
├── FunctionType   返回类型 + 参数类型列表
├── StructType     Galaxy struct（不支持 union）
├── TypedefType    typedef 别名（透明穿透）
├── NullType       null 字面量（可赋给任何 HandleType）
└── ErrorType      错误恢复哨兵（与一切类型"兼容"，阻止级联报错）
```

**关键规则：**
- `int` ↔ `fixed` 可隐式转换（Galaxy 编辑器行为）
- `bool` 可接受任何数值（非零为真）
- `null` 只能赋给句柄类型
- 句柄类型之间**不能**互相赋值（unit ≠ trigger）

### 3.2 符号表（`semantic/symbol.py`）

三层作用域：
```
global scope
  └── function scope（进入函数时建立）
        └── block scope（每个 { } 建立一层）
```

每个 `Symbol` 携带：
- `gtype`：类型
- `kind`：VAR / CONST / FUNC / TYPE / PARAM
- `is_native`：native 函数标记
- `is_static`：static 局部变量（在全局初始化，但只在函数内可见）
- `is_const`：const 修饰

### 3.3 语义分析器（`semantic/analyzer.py`）

采用**两遍扫描**解决前向引用问题：

```
第一遍（顶层扫描）：
  ├── 注册所有 struct 定义
  ├── 注册所有 typedef
  ├── 注册所有函数签名（含 native）
  └── 注册所有全局变量并检查初始值

第二遍（函数体分析）：
  └── 对每个 FuncDef，分析函数体
       ├── 注册形参
       ├── 逐条语句分析
       └── 维护 loop_depth、curr_func 状态
```

**错误恢复策略：**
- 使用 `ErrorType` 作为"中毒"类型
- 子表达式出错时，父节点拿到 `ErrorType` 不再报错
- 分析尽量继续，以便一次发现更多错误

### 3.4 Native 函数加载器（`semantic/natives.py`）

Galaxy Script 的标准库有数千个 native 函数。加载方式：

**方式 A（推荐）：从 SC2 安装目录加载**
```python
frontend.load_natives_from_file(
    "StarCraft II/Mods/Core.SC2Mod/Base.SC2Data/TriggerLibs/natives.galaxy"
)
```

**方式 B：使用内置的常用函数集**
```python
frontend.load_natives_common()   # 约 30 个最常用函数
```

**方式 C：手工定义**
```python
frontend.load_natives_from_dict({
    'MyCustomFunc': ('int', ['unit', 'fixed']),
})
```

---

## 四、接入已有项目的步骤

### 步骤 1：将 `galaxycc/` 目录放到你的项目中

```
your_project/
  galaxy.lark          ← 你的 grammar
  galaxycc/            ← 本项目
  main.py
```

### 步骤 2：修改 `pipeline.py` 中的 Lark 解析器参数

根据你的 grammar 特点选择 parser：
```python
# 如果 grammar 有歧义（大多数 Galaxy grammar 有），用 earley
self._parser = Lark.open(grammar_file, parser='earley', ...)

# 如果无歧义（通常 LALR 更快），用 lalr
self._parser = Lark.open(grammar_file, parser='lalr', ...)
```

### 步骤 3：完善 GalaxyTransformer

`tree/transformer.py` 中的 Transformer 需要与你的 grammar 规则名完全对应。

**对照表（你的 grammar → Transformer 方法）：**

| grammar 规则 | Transformer 方法 |
|---|---|
| `translation_unit` | `translation_unit` |
| `function_definition` | `function_definition` |
| `declaration` | `declaration` |
| `selection_statement` | `selection_statement` |
| `iteration_statement` | `iteration_statement` |
| `jump_statement` | `jump_statement` |
| `assignment_expression` | `assignment_expression` |
| `postfix_expression` | `postfix_expression` |
| … | … |

**调试技巧：**先用 `frontend.parse_only(src)` 看 CST 结构，
再对应补全 Transformer。

### 步骤 4：测试已有的 900 个脚本

```python
from galaxycc import GalaxyFrontend

frontend = GalaxyFrontend(grammar_file="galaxy.lark")
frontend.load_natives_common()

import glob
files = glob.glob("your_scripts/**/*.galaxy", recursive=True)
for f in files:
    result = frontend.process_file(f)
    if result.diags.has_errors:
        print(f"FAIL {f}")
        print(result.diags.report())
```

---

## 五、扩展方向

### 5.1 下一步：IR 生成

参考 AnanasCC 的 `ir/generator.py`，遍历已标注类型的 AST，
生成三地址码或其他中间表示。

Galaxy Script 的目标不是生成机器码，而是可能：
- 生成优化后的 Galaxy Script（minify / refactor）
- 生成文档（函数签名提取）
- 进行静态分析（死代码检测、未初始化变量等）

### 5.2 增量分析

对 900 个文件，可以把符号表序列化缓存，
只重新分析修改过的文件。

### 5.3 LSP（语言服务器）

有了符号表和类型信息，可以实现：
- 代码补全
- 悬停提示（显示类型）
- 跳转到定义
- 查找引用

---

## 六、已知限制与 TODO

- [ ] Transformer 覆盖尚不完整，部分边缘规则需根据你的 grammar 补充
- [ ] `const` 变量的编译期求值还较弱（只支持整数字面量）
- [ ] struct 成员不支持嵌套初始化列表检查
- [ ] 多文件（`include` 指令）的跨文件符号解析未实现
- [ ] `static` 局部变量的语义（全局生命期）未在 IR 层处理
