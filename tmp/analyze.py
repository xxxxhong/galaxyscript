#!/usr/bin/env python3
"""
Galaxy Script 语法分析器
分析星际争霸II的Galaxy脚本文件,反推其文法规则
"""

import os
import re
from collections import defaultdict, Counter
from pathlib import Path

class GalaxyAnalyzer:
    def __init__(self):
        self.keywords = set()
        self.types = set()
        self.operators = set()
        self.functions = []
        self.structs = []
        self.constants = []
        self.includes = []
        self.native_funcs = []
        
    def analyze_file(self, filepath):
        """分析单个Galaxy文件"""
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # 提取include语句
        includes = re.findall(r'include\s+"([^"]+)"', content)
        self.includes.extend(includes)
        
        # 提取const常量定义
        consts = re.findall(r'const\s+(\w+)\s+(\w+)\s*=\s*([^;]+);', content)
        self.constants.extend(consts)
        
        # 提取函数定义 (返回类型 函数名 参数列表)
        funcs = re.findall(r'(\w+)\s+(\w+)\s*\(([^)]*)\)\s*{', content)
        self.functions.extend(funcs)
        
        # 提取native函数声明
        natives = re.findall(r'native\s+(\w+)\s+(\w+)\s*\(([^)]*)\);', content)
        self.native_funcs.extend(natives)
        
        # 提取struct定义
        struct_pattern = r'struct\s+(\w+)\s*{([^}]*)}'
        structs = re.findall(struct_pattern, content, re.MULTILINE | re.DOTALL)
        self.structs.extend(structs)
        
        # 提取关键字
        keywords_pattern = r'\b(if|else|while|for|return|struct|const|include|native|void|int|bool|fixed|string|static|break|continue|null|true|false)\b'
        keywords = re.findall(keywords_pattern, content)
        self.keywords.update(keywords)
        
        # 提取类型
        type_pattern = r'\b(void|int|bool|fixed|string|byte|point|unit|timer|playergroup|unitgroup|region|text|abilcmd|sound|marker|order|bank|camerainfo)\b'
        types = re.findall(type_pattern, content)
        self.types.update(types)
        
        # 提取运算符
        op_pattern = r'([+\-*/=<>!&|]{1,2})'
        ops = re.findall(op_pattern, content)
        self.operators.update(ops)
    
    def analyze_directory(self, directory):
        """分析目录中的所有Galaxy文件"""
        galaxy_files = list(Path(directory).glob('*.galaxy'))
        print(f"找到 {len(galaxy_files)} 个Galaxy文件")
        
        for idx, filepath in enumerate(galaxy_files):  # 分析前100个文件
            if idx % 10 == 0:
                print(f"已分析 {idx} 个文件...")
            self.analyze_file(filepath)
    
    def generate_report(self):
        """生成分析报告"""
        report = []
        report.append("=" * 80)
        report.append("Galaxy Script 语法分析报告")
        report.append("=" * 80)
        report.append("")
        
        report.append("1. 关键字 (Keywords)")
        report.append("-" * 40)
        report.append(f"发现 {len(self.keywords)} 个关键字:")
        report.append(", ".join(sorted(self.keywords)))
        report.append("")
        
        report.append("2. 数据类型 (Types)")
        report.append("-" * 40)
        report.append(f"发现 {len(self.types)} 个数据类型:")
        report.append(", ".join(sorted(self.types)))
        report.append("")
        
        report.append("3. 运算符 (Operators)")
        report.append("-" * 40)
        report.append(f"发现 {len(self.operators)} 个运算符:")
        report.append(", ".join(sorted(self.operators)))
        report.append("")
        
        report.append("4. Include语句示例")
        report.append("-" * 40)
        unique_includes = list(set(self.includes))[:10]
        for inc in unique_includes:
            report.append(f'  include "{inc}"')
        report.append("")
        
        report.append("5. 常量定义示例 (前20个)")
        report.append("-" * 40)
        for const in self.constants[:20]:
            report.append(f"  const {const[0]} {const[1]} = {const[2]};")
        report.append("")
        
        report.append("6. 函数定义示例 (前20个)")
        report.append("-" * 40)
        for func in self.functions[:20]:
            report.append(f"  {func[0]} {func[1]}({func[2]})")
        report.append("")
        
        report.append("7. Native函数示例 (前20个)")
        report.append("-" * 40)
        for nfunc in self.native_funcs[:20]:
            report.append(f"  native {nfunc[0]} {nfunc[1]}({nfunc[2]});")
        report.append("")
        
        report.append("8. Struct定义示例 (前5个)")
        report.append("-" * 40)
        for struct in self.structs[:5]:
            report.append(f"  struct {struct[0]} {{")
            # 简化显示
            fields = struct[1].strip().split('\n')[:5]
            for field in fields:
                if field.strip():
                    report.append(f"    {field.strip()}")
            report.append("  }")
            report.append("")
        
        report.append("=" * 80)
        report.append(f"统计:")
        report.append(f"  - Include语句: {len(self.includes)}")
        report.append(f"  - 常量定义: {len(self.constants)}")
        report.append(f"  - 函数定义: {len(self.functions)}")
        report.append(f"  - Native函数: {len(self.native_funcs)}")
        report.append(f"  - Struct定义: {len(self.structs)}")
        report.append("=" * 80)
        
        return "\n".join(report)

if __name__ == "__main__":
    analyzer = GalaxyAnalyzer()
    analyzer.analyze_directory(".\\galaxy_scripts\\")
    report = analyzer.generate_report()
    
    # 保存报告
    with open(".\\galaxy_analysis_report.txt", "w") as f:
        f.write(report)
    
    print(report)