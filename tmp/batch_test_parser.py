#!/usr/bin/env python3
"""
批量测试Galaxy解析器
====================

扫描指定目录下的所有.galaxy文件并测试解析器
"""

import os
import sys
import time
from pathlib import Path
from lark import Lark
from lark.exceptions import LarkError

# 你的语法定义（从0214_v2.py复制过来）
GALAXY_GRAMMAR = r"""
start: translation_unit

translation_unit: external_declaration+

external_declaration: function_definition
                    | declaration
                    | native_declaration
                    | struct_declaration
                    | include_statement

include_statement: "include" STRING

declaration: declaration_specifiers ";"
           | declaration_specifiers init_declarator_list ";"

declaration_specifiers: storage_class_specifier* type_specifier

storage_class_specifier: "const" | "static"

type_specifier: primitive_type | game_type | struct_specifier | type_name

type_name: IDENTIFIER

primitive_type: "void" | "int" | "bool" | "fixed" | "string" | "byte"

game_type: "unit" | "point" | "timer" | "region" | "trigger" | "wave" | "actor"
         | "revealer" | "playergroup" | "unitgroup" | "text" | "sound"
         | "soundlink" | "color" | "abilcmd" | "order" | "marker" | "bank"
         | "camerainfo" | "actorscope" | "aifilter" | "unitfilter"
         | "wavetarget" | "effecthistory"

init_declarator_list: init_declarator ("," init_declarator)*

init_declarator: declarator ("=" initializer)?

declarator: IDENTIFIER array_suffix*

array_suffix: "[" constant_expression? "]"
            | "[" constant_expression "+" constant_expression "]"

initializer: assignment_expression
           | "{" initializer_list ","? "}"

initializer_list: initializer ("," initializer)*

struct_declaration: struct_specifier ";"

struct_specifier: "struct" IDENTIFIER "{" struct_member+ "}"
                | "struct" "{" struct_member+ "}"
                | "struct" IDENTIFIER

struct_member: type_specifier struct_declarator ("," struct_declarator)* ";"

struct_declarator: declarator

function_definition: type_specifier IDENTIFIER "(" parameter_list? ")" compound_statement

parameter_list: parameter_declaration ("," parameter_declaration)*

parameter_declaration: type_specifier IDENTIFIER array_suffix?

native_declaration: "native" type_specifier IDENTIFIER "(" native_parameter_list? ")" ";"

native_parameter_list: native_parameter_declaration ("," native_parameter_declaration)*

native_parameter_declaration: type_specifier IDENTIFIER array_suffix?

statement: compound_statement
         | expression_statement
         | selection_statement
         | iteration_statement
         | jump_statement

compound_statement: "{" block_item* "}"

block_item: declaration | statement

expression_statement: expression? ";"

selection_statement: "if" "(" expression ")" statement ("else" statement)?

iteration_statement: "while" "(" expression ")" statement
                   | "for" "(" for_init ";" for_condition ";" for_update ")" statement

for_init: expression? | declaration_specifiers init_declarator_list

for_condition: expression?

for_update: expression?

jump_statement: "continue" ";"
              | "break" ";"
              | "return" expression? ";"

?expression: assignment_expression

constant_expression: logical_or_expression

assignment_expression: logical_or_expression
                     | unary_expression assignment_operator assignment_expression

assignment_operator: "=" | "*=" | "/=" | "+=" | "-="

logical_or_expression: logical_and_expression ("||" logical_and_expression)*

logical_and_expression: equality_expression ("&&" equality_expression)*

equality_expression: relational_expression (("==" | "!=") relational_expression)*

relational_expression: shift_expression (("<" | ">" | "<=" | ">=" | "><" | ">+" | "/>" | "</") shift_expression)*

shift_expression: additive_expression ("<<" additive_expression)*

additive_expression: multiplicative_expression (("+" | "-" | "+/") multiplicative_expression)*

multiplicative_expression: unary_expression (("*" | "/" | "**" | "*-") unary_expression)*

unary_expression: postfix_expression
                | ("++" | "--") unary_expression
                | ("+" | "-" | "!") unary_expression

postfix_expression: primary_expression
                  | postfix_expression "[" expression "]"
                  | postfix_expression "(" argument_list? ")"
                  | postfix_expression "." IDENTIFIER
                  | postfix_expression ("++" | "--")

argument_list: assignment_expression ("," assignment_expression)*

primary_expression: IDENTIFIER
                  | INTEGER
                  | FIXED
                  | STRING
                  | "true"
                  | "false"
                  | "null"
                  | "(" expression ")"

IDENTIFIER: /[a-zA-Z_][a-zA-Z0-9_]*/
INTEGER: /\d+/
FIXED: /\d+\.\d+/
STRING: /"([^"\\]|\\.)*"/

COMMENT: "//" /[^\n]*/
       | "/*" /(.|\n)*?/ "*/"

%import common.WS
%ignore WS
%ignore COMMENT
"""

def count_nodes(tree, node_type):
    """统计特定类型的节点数量"""
    from lark import Tree
    count = 0
    if isinstance(tree, Tree):
        if tree.data == node_type:
            count += 1
        for child in tree.children:
            count += count_nodes(child, node_type)
    return count

def test_single_file(parser, filepath):
    """测试单个文件"""
    try:
        # 读取文件
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # 跳过空文件
        if not content.strip():
            return {
                'status': 'skipped',
                'reason': 'empty file'
            }
        
        # 计时
        start_time = time.time()
        
        # 解析
        tree = parser.parse(content)
        
        # 计算耗时
        parse_time = time.time() - start_time
        
        # 统计
        stats = {
            'status': 'success',
            'parse_time': parse_time,
            'functions': count_nodes(tree, 'function_definition'),
            'natives': count_nodes(tree, 'native_declaration'),
            'structs': count_nodes(tree, 'struct_declaration'),
            'declarations': count_nodes(tree, 'declaration'),
            'lines': len(content.split('\n'))
        }
        
        return stats
        
    except LarkError as e:
        return {
            'status': 'parse_error',
            'error': str(e)[:200]  # 限制错误信息长度
        }
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e)[:200]
        }

def batch_test(directory, max_files=None, verbose=False):
    """批量测试目录下的所有Galaxy文件"""
    
    print("=" * 80)
    print("Galaxy Parser 批量测试")
    print("=" * 80)
    print()
    
    # 创建解析器
    print("创建解析器...")
    parser = Lark(GALAXY_GRAMMAR, start='start', parser='earley')
    print("✅ 解析器创建成功")
    print()
    
    # 查找所有.galaxy文件
    print(f"扫描目录: {directory}")
    galaxy_files = list(Path(directory).glob('**/*.galaxy'))
    
    if max_files:
        galaxy_files = galaxy_files[:max_files]
    
    total = len(galaxy_files)
    print(f"找到 {total} 个.galaxy文件")
    print()
    
    # 统计
    results = {
        'success': [],
        'parse_error': [],
        'error': [],
        'skipped': []
    }
    
    total_parse_time = 0
    
    # 测试每个文件
    print("开始测试...")
    print("-" * 80)
    
    for idx, filepath in enumerate(galaxy_files, 1):
        # 进度
        if idx % 10 == 0 or verbose:
            print(f"[{idx}/{total}] {filepath.name}", end='')
        
        # 测试
        result = test_single_file(parser, filepath)
        result['file'] = filepath.name
        result['path'] = str(filepath)
        
        # 记录
        status = result['status']
        results[status].append(result)
        
        if status == 'success':
            total_parse_time += result['parse_time']
            if idx % 10 == 0 or verbose:
                print(f" ✅ ({result['parse_time']*1000:.1f}ms)")
        elif verbose:
            print(f" ❌ {status}")
        elif idx % 10 == 0:
            print()
    
    print()
    print("-" * 80)
    
    # 输出结果
    print()
    print("=" * 80)
    print("测试结果")
    print("=" * 80)
    print()
    
    success_count = len(results['success'])
    error_count = len(results['parse_error']) + len(results['error'])
    skipped_count = len(results['skipped'])
    
    print(f"总文件数:     {total}")
    print(f"成功:         {success_count} ({success_count/total*100:.1f}%)")
    print(f"解析错误:     {len(results['parse_error'])}")
    print(f"其他错误:     {len(results['error'])}")
    print(f"跳过:         {skipped_count}")
    print()
    
    if success_count > 0:
        avg_time = total_parse_time / success_count
        print(f"平均解析时间: {avg_time*1000:.1f}ms")
        
        # 统计代码规模
        total_lines = sum(r['lines'] for r in results['success'])
        total_functions = sum(r['functions'] for r in results['success'])
        total_natives = sum(r['natives'] for r in results['success'])
        total_structs = sum(r['structs'] for r in results['success'])
        
        print(f"总代码行数:   {total_lines:,}")
        print(f"总函数数:     {total_functions:,}")
        print(f"总Native函数: {total_natives:,}")
        print(f"总Struct:     {total_structs:,}")
        print()
    
    # 显示错误
    if results['parse_error']:
        print("=" * 80)
        print("解析错误 (前10个):")
        print("=" * 80)
        for result in results['parse_error'][:10]:
            print(f"\n文件: {result['file']}")
            print(f"错误: {result['error']}")
    
    if results['error']:
        print("=" * 80)
        print("其他错误 (前10个):")
        print("=" * 80)
        for result in results['error'][:10]:
            print(f"\n文件: {result['file']}")
            print(f"错误: {result['error']}")
    
    # 最慢的文件
    if success_count > 5:
        print()
        print("=" * 80)
        print("解析最慢的5个文件:")
        print("=" * 80)
        slowest = sorted(results['success'], key=lambda x: x['parse_time'], reverse=True)[:5]
        for i, r in enumerate(slowest, 1):
            print(f"{i}. {r['file']:40s} {r['parse_time']*1000:6.1f}ms ({r['lines']:5d} 行)")
    
    # 最大的文件
    if success_count > 5:
        print()
        print("=" * 80)
        print("代码量最大的5个文件:")
        print("=" * 80)
        largest = sorted(results['success'], key=lambda x: x['lines'], reverse=True)[:5]
        for i, r in enumerate(largest, 1):
            print(f"{i}. {r['file']:40s} {r['lines']:5d} 行 ({r['functions']} 函数)")
    
    return results

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='批量测试Galaxy解析器')
    parser.add_argument('directory', 
                       nargs='?',
                       default=r'C:\Users\hyg19\Desktop\files\galaxy_scripts',
                       help='Galaxy文件目录')
    parser.add_argument('--max', type=int, help='最多测试多少个文件')
    parser.add_argument('-v', '--verbose', action='store_true', help='显示详细信息')
    
    args = parser.parse_args()
    
    # 检查目录
    if not os.path.exists(args.directory):
        print(f"❌ 错误: 目录不存在: {args.directory}")
        return 1
    
    # 批量测试
    results = batch_test(args.directory, max_files=args.max, verbose=args.verbose)
    
    # 返回码
    if len(results['parse_error']) + len(results['error']) > 0:
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())