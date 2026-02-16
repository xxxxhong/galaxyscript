# Galaxy Script 编译器

基于对星际争霸II游戏数据中Galaxy脚本文件的逆向分析,构建的完整编译器实现。

## 项目概述

本项目通过分析星际争霸II的游戏数据文件,反推出Galaxy脚本语言的完整文法规则,并实现了一个功能完整的编译器,包括:

1. **词法分析器 (Lexer)** - 将源代码转换为token流
2. **语法分析器 (Parser)** - 将token流转换为抽象语法树(AST)
3. **代码生成器 (Code Generator)** - 将AST转换回源代码
4. **BNF文法定义** - 完整的语法规则文档

## 项目结构

```
.
├── galaxy_lexer.py              # 词法分析器
├── galaxy_parser.py             # 语法分析器和AST定义
├── galaxy_compiler.py           # 完整编译器主程序
├── galaxy_bnf_grammar.txt       # BNF文法定义
├── galaxy_analysis_report.txt  # 语法分析报告
├── analyze_galaxy_syntax.py    # 语法分析脚本
└── README.md                    # 本文件
```

## Galaxy语言特性

### 1. 基本类型

```galaxy
// 基本类型
void, int, bool, fixed, string, byte

// 复杂类型
point, unit, timer, playergroup, unitgroup, region, text
abilcmd, sound, marker, order, bank, camerainfo
```

### 2. 关键字

```
if, else, while, for, return, break, continue
struct, const, static, native, include
true, false, null
```

### 3. 运算符

**算术运算符**: `+`, `-`, `*`, `/`
**赋值运算符**: `=`, `+=`, `-=`, `*=`, `/=`
**比较运算符**: `==`, `!=`, `<`, `>`, `<=`, `>=`
**逻辑运算符**: `&&`, `||`, `!`
**自增/自减**: `++`, `--`

### 4. 语法示例

#### 常量声明
```galaxy
const int MAX_PLAYERS = 16;
const fixed PI = 3.14159;
const string GAME_NAME = "StarCraft";
```

#### 变量声明
```galaxy
int health = 100;
fixed speed = 5.5;
bool isAlive = true;
int scores[MAX_PLAYERS];
static int globalCounter;
```

#### 函数声明
```galaxy
int add(int a, int b) {
    return a + b;
}

void processUnit(unit u, int damage) {
    // 函数体
}
```

#### Native函数声明
```galaxy
native int UnitGetHealth(unit u);
native void UnitSetHealth(unit u, int value);
```

#### 结构体
```galaxy
struct Player {
    int id;
    string name;
    bool isActive;
    fixed score;
    int inventory[10];
};
```

#### 控制流
```galaxy
// if-else
if (x > 10) {
    x = 10;
} else {
    x += 1;
}

// while循环
while (count > 0) {
    count -= 1;
}

// for循环
for (i = 0; i < MAX_PLAYERS; i += 1) {
    ProcessPlayer(i);
}
```

#### Include语句
```galaxy
include "TriggerLibs/NativeLib"
include "TriggerLibs/GameLib"
```

## 使用方法

### 1. 词法分析

```python
from galaxy_lexer import Lexer

source_code = '''
const int MAX_VALUE = 100;
int add(int a, int b) {
    return a + b;
}
'''

lexer = Lexer(source_code)
tokens = lexer.tokenize()

for token in tokens:
    print(token)
```

### 2. 语法分析

```python
from galaxy_lexer import Lexer
from galaxy_parser import Parser

source_code = '...'  # Galaxy源代码

lexer = Lexer(source_code)
tokens = lexer.tokenize()

parser = Parser(tokens)
ast = parser.parse()

# 遍历AST
for statement in ast.statements:
    print(statement)
```

### 3. 完整编译

```bash
# 命令行模式
python3 galaxy_compiler.py input.galaxy output.galaxy

# 演示模式(使用内置测试代码)
python3 galaxy_compiler.py
```

### 4. Python API

```python
from galaxy_compiler import GalaxyCompiler

compiler = GalaxyCompiler()

# 编译字符串
source_code = '''
int factorial(int n) {
    if (n <= 1) {
        return 1;
    }
    return n * factorial(n - 1);
}
'''

output = compiler.compile(source_code)
print(output)

# 编译文件
compiler.compile_file('input.galaxy', 'output.galaxy')
```

## 语法分析报告

项目包含对989个Galaxy文件的自动分析,提取了:

- **19个关键字**
- **17种数据类型**
- **25个运算符**
- **1230个常量定义**
- **5281个函数定义**
- **19个结构体定义**

详见 `galaxy_analysis_report.txt`

## BNF文法规则

完整的巴科斯范式(BNF)文法定义见 `galaxy_bnf_grammar.txt`,包括:

- 程序结构
- 表达式语法
- 语句语法
- 类型系统
- 运算符优先级

## 编译器架构

### 词法分析器 (Lexer)

- 输入:源代码字符串
- 输出:Token流
- 功能:
  - 识别关键字、标识符、字面量
  - 处理运算符和分隔符
  - 跳过注释和空白
  - 行号/列号追踪

### 语法分析器 (Parser)

- 输入:Token流
- 输出:抽象语法树(AST)
- 方法:递归下降解析
- 支持:
  - 表达式解析(支持运算符优先级)
  - 语句解析
  - 类型检查
  - 错误报告(行号/列号)

### 代码生成器 (CodeGenerator)

- 输入:AST
- 输出:格式化的源代码
- 功能:
  - 代码美化
  - 缩进管理
  - 注释保留

## 测试示例

### 示例1:基本函数

输入:
```galaxy
int add(int a, int b) {
    return a + b;
}
```

输出:
```galaxy
int add(int a, int b) {
    return (a + b);
}
```

### 示例2:完整程序

见 `test_simple.galaxy`

## 扩展功能

编译器可以扩展为:

1. **语义分析器** - 类型检查、作用域分析
2. **优化器** - 代码优化、死代码消除
3. **解释器** - 直接执行Galaxy脚本
4. **字节码生成** - 生成中间表示或字节码
5. **IDE集成** - 语法高亮、自动补全、错误检查

## 局限性

当前实现的局限:

1. 不支持预处理器指令(除include外)
2. 有限的错误恢复能力
3. 不进行语义分析(类型检查)
4. 不支持某些高级语法特性

## 技术栈

- Python 3.12+
- dataclasses (用于AST节点定义)
- enum (用于Token类型)
- 递归下降解析算法

## 贡献

欢迎贡献!可以改进的方向:

- 增强错误报告
- 添加更多语法特性
- 优化解析性能
- 增加测试用例
- 改进代码生成

## 许可

本项目用于学习和研究目的。

## 致谢

基于星际争霸II游戏数据文件进行的逆向工程分析。

---

**作者**: Claude (Anthropic)
**创建日期**: 2026-02-14
**版本**: 1.0.0
