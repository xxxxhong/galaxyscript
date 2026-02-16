#!/usr/bin/env python3
"""
Galaxy Script 增强版语法分析器
提供更深入的统计分析和洞察
"""

import os
import re
from collections import defaultdict, Counter
from pathlib import Path
import json

class EnhancedGalaxyAnalyzer:
    def __init__(self):
        self.keywords = set()
        self.types = set()
        self.operators = set()
        self.functions = []
        self.structs = []
        self.constants = []
        self.includes = []
        self.native_funcs = []
        
        # 增强统计
        self.file_sizes = []
        self.file_lines = []
        self.function_params = []
        self.struct_members = []
        self.constant_types = defaultdict(int)
        self.function_prefixes = defaultdict(int)
        self.native_categories = defaultdict(list)
        
    def analyze_file(self, filepath):
        """分析单个Galaxy文件"""
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                lines = content.split('\n')
            
            # 文件统计
            file_size = os.path.getsize(filepath)
            self.file_sizes.append((filepath.name, file_size))
            self.file_lines.append((filepath.name, len(lines)))
            
            # 提取include语句
            includes = re.findall(r'include\s+"([^"]+)"', content)
            self.includes.extend(includes)
            
            # 提取const常量定义
            consts = re.findall(r'const\s+(\w+)\s+(\w+)\s*=\s*([^;]+);', content)
            for const in consts:
                self.constants.append(const)
                self.constant_types[const[0]] += 1
            
            # 提取函数定义 (返回类型 函数名 参数列表)
            funcs = re.findall(r'(\w+)\s+(\w+)\s*\(([^)]*)\)\s*{', content)
            for func in funcs:
                self.functions.append(func)
                # 统计函数前缀
                prefix = func[1].split('_')[0] if '_' in func[1] else func[1][:3]
                self.function_prefixes[prefix] += 1
                # 统计参数数量
                params = [p.strip() for p in func[2].split(',') if p.strip()]
                self.function_params.append(len(params))
            
            # 提取native函数声明
            natives = re.findall(r'native\s+(\w+)\s+(\w+)\s*\(([^)]*)\);', content, re.DOTALL)
            for native in natives:
                self.native_funcs.append(native)
                # 按功能分类native函数：提取函数名的第一个单词
                match = re.match(r'^([A-Z][a-z]+)', native[1])
                category = match.group(1) if match else 'Other'
                self.native_categories[category].append(native[1])
            
            # 提取struct定义
            struct_pattern = r'struct\s+(\w+)\s*{([^}]*)}'
            structs = re.findall(struct_pattern, content, re.MULTILINE | re.DOTALL)
            for struct in structs:
                self.structs.append(struct)
                # 统计struct成员数量
                members = [m for m in struct[1].split(';') if m.strip()]
                self.struct_members.append(len(members))
            
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
            
        except Exception as e:
            print(f"Error analyzing {filepath}: {e}")
    
    def analyze_directory(self, directory):
        """分析目录中的所有Galaxy文件"""
        galaxy_files = list(Path(directory).glob('*.galaxy'))
        total = len(galaxy_files)
        print(f"找到 {total} 个Galaxy文件")
        print("=" * 80)
        
        for idx, filepath in enumerate(galaxy_files, 1):
            if idx % 50 == 0:
                progress = (idx / total) * 100
                print(f"进度: {idx}/{total} ({progress:.1f}%)")
            self.analyze_file(filepath)
        
        print(f"分析完成: {total}/{total} (100.0%)")
        print("=" * 80)
    
    def generate_enhanced_report(self):
        """生成增强版分析报告"""
        report = []
        
        report.append("=" * 80)
        report.append("Galaxy Script 增强版语法分析报告")
        report.append("=" * 80)
        report.append("")
        
        # ============ 基础统计 ============
        report.append("【一、基础语法元素】")
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
        
        # ============ 代码规模分析 ============
        report.append("【二、代码规模分析】")
        report.append("=" * 80)
        report.append("")
        
        if self.file_sizes:
            total_size = sum(size for _, size in self.file_sizes)
            avg_size = total_size / len(self.file_sizes)
            max_file = max(self.file_sizes, key=lambda x: x[1])
            min_file = min(self.file_sizes, key=lambda x: x[1])
            
            report.append("文件大小统计:")
            report.append(f"  - 文件总数: {len(self.file_sizes)} 个")
            report.append(f"  - 总大小: {total_size / 1024 / 1024:.2f} MB")
            report.append(f"  - 平均大小: {avg_size / 1024:.2f} KB")
            report.append(f"  - 最大文件: {max_file[0]} ({max_file[1] / 1024:.2f} KB)")
            report.append(f"  - 最小文件: {min_file[0]} ({min_file[1]} bytes)")
            report.append("")
        
        if self.file_lines:
            total_lines = sum(lines for _, lines in self.file_lines)
            avg_lines = total_lines / len(self.file_lines)
            max_file = max(self.file_lines, key=lambda x: x[1])
            min_file = min(self.file_lines, key=lambda x: x[1])
            
            report.append("代码行数统计:")
            report.append(f"  - 总行数: {total_lines:,} 行")
            report.append(f"  - 平均行数: {avg_lines:.0f} 行/文件")
            report.append(f"  - 最多: {max_file[0]} ({max_file[1]:,} 行)")
            report.append(f"  - 最少: {min_file[0]} ({min_file[1]} 行)")
            report.append("")
        
        # ============ 函数分析 ============
        report.append("【三、函数分析】")
        report.append("=" * 80)
        report.append("")
        
        report.append(f"函数定义总数: {len(self.functions)}")
        report.append("")
        
        # 函数参数分布
        if self.function_params:
            param_dist = Counter(self.function_params)
            avg_params = sum(self.function_params) / len(self.function_params)
            max_params = max(self.function_params)
            
            report.append("参数数量分布:")
            report.append(f"  - 平均参数: {avg_params:.2f} 个")
            report.append(f"  - 最多参数: {max_params} 个")
            report.append("")
            report.append("  参数数量分布 (前10):")
            for count, freq in sorted(param_dist.items())[:10]:
                percentage = (freq / len(self.function_params)) * 100
                bar = "█" * int(percentage / 2)
                report.append(f"    {count}个参数: {freq:5d} 次 ({percentage:5.2f}%) {bar}")
            report.append("")
        
        # 函数前缀分析
        if self.function_prefixes:
            report.append("函数命名前缀分析 (Top 20):")
            for prefix, count in sorted(self.function_prefixes.items(), key=lambda x: x[1], reverse=True)[:20]:
                percentage = (count / len(self.functions)) * 100
                report.append(f"  {prefix:15s}: {count:5d} ({percentage:5.2f}%)")
            report.append("")
        
        # ============ Native函数分析 ============
        report.append("【四、Native函数分析】")
        report.append("=" * 80)
        report.append("")
        
        report.append(f"Native函数总数: {len(self.native_funcs)}")
        report.append("")
        
        if self.native_categories:
            report.append("Native函数分类 (Top 20):")
            for category, funcs in sorted(self.native_categories.items(), 
                                         key=lambda x: len(x[1]), reverse=True)[:20]:
                report.append(f"  {category:15s}: {len(funcs):4d} 个函数")
            report.append("")
            
            # 显示每个类别的示例
            report.append("各类别Native函数示例:")
            for category, funcs in sorted(self.native_categories.items(), 
                                         key=lambda x: len(x[1]), reverse=True)[:10]:
                report.append(f"\n  [{category}] 类别:")
                for func in funcs[:5]:
                    report.append(f"    - {func}")
            report.append("")
        
        # ============ 常量分析 ============
        report.append("【五、常量分析】")
        report.append("=" * 80)
        report.append("")
        
        report.append(f"常量定义总数: {len(self.constants)}")
        report.append("")
        
        if self.constant_types:
            report.append("常量类型分布:")
            total_consts = sum(self.constant_types.values())
            for ctype, count in sorted(self.constant_types.items(), key=lambda x: x[1], reverse=True):
                percentage = (count / total_consts) * 100
                bar = "█" * int(percentage / 2)
                report.append(f"  {ctype:12s}: {count:6d} ({percentage:5.2f}%) {bar}")
            report.append("")
        
        # 常量命名模式
        const_prefixes = defaultdict(int)
        for _, name, _ in self.constants:
            prefix = name.split('_')[0] if '_' in name else name[:2]
            const_prefixes[prefix] += 1
        
        if const_prefixes:
            report.append("常量命名前缀 (Top 15):")
            for prefix, count in sorted(const_prefixes.items(), key=lambda x: x[1], reverse=True)[:15]:
                report.append(f"  {prefix:20s}: {count:5d}")
            report.append("")
        
        # ============ Struct分析 ============
        report.append("【六、结构体分析】")
        report.append("=" * 80)
        report.append("")
        
        report.append(f"Struct定义总数: {len(self.structs)}")
        report.append("")
        
        if self.struct_members:
            avg_members = sum(self.struct_members) / len(self.struct_members)
            max_members = max(self.struct_members)
            min_members = min(self.struct_members)
            
            report.append("Struct成员数量统计:")
            report.append(f"  - 平均成员: {avg_members:.2f} 个")
            report.append(f"  - 最多成员: {max_members} 个")
            report.append(f"  - 最少成员: {min_members} 个")
            report.append("")
            
            # 成员数量分布
            member_dist = Counter(self.struct_members)
            report.append("  成员数量分布:")
            for count, freq in sorted(member_dist.items())[:15]:
                percentage = (freq / len(self.struct_members)) * 100
                bar = "█" * int(percentage)
                report.append(f"    {count:2d}个成员: {freq:3d} 个struct ({percentage:5.2f}%) {bar}")
            report.append("")
        
        # 最复杂的Struct
        if self.structs:
            complex_structs = sorted(zip(self.structs, self.struct_members), 
                                   key=lambda x: x[1], reverse=True)[:10]
            report.append("最复杂的Struct (Top 10):")
            for (struct, _), member_count in complex_structs:
                report.append(f"  {struct[0]:40s}: {member_count} 个成员")
            report.append("")
        
        # ============ Include依赖分析 ============
        report.append("【七、Include依赖分析】")
        report.append("=" * 80)
        report.append("")
        
        report.append(f"Include语句总数: {len(self.includes)}")
        unique_includes = set(self.includes)
        report.append(f"唯一Include路径: {len(unique_includes)} 个")
        report.append("")
        
        # 最常被引用的库
        include_freq = Counter(self.includes)
        report.append("最常被引用的库 (Top 20):")
        for inc, count in include_freq.most_common(20):
            report.append(f"  {inc:50s}: {count:4d} 次")
        report.append("")
        
        # Include路径分类
        triggerlibs = [inc for inc in self.includes if 'TriggerLibs' in inc]
        game_data = [inc for inc in self.includes if 'GameData' in inc]
        lib_files = [inc for inc in self.includes if inc.startswith('Lib') and '_h' in inc]
        
        report.append("Include分类:")
        report.append(f"  - TriggerLibs库: {len(triggerlibs)} 次引用")
        report.append(f"  - GameData库: {len(game_data)} 次引用")
        report.append(f"  - Lib头文件: {len(lib_files)} 次引用")
        report.append(f"  - 其他: {len(self.includes) - len(triggerlibs) - len(game_data) - len(lib_files)} 次引用")
        report.append("")
        
        # ============ 总体统计 ============
        report.append("【八、总体统计摘要】")
        report.append("=" * 80)
        report.append("")
        
        report.append(f"关键字数量:        {len(self.keywords):6d}")
        report.append(f"数据类型:          {len(self.types):6d}")
        report.append(f"运算符:            {len(self.operators):6d}")
        report.append(f"Include语句:       {len(self.includes):6d}")
        report.append(f"常量定义:          {len(self.constants):6d}")
        report.append(f"函数定义:          {len(self.functions):6d}")
        report.append(f"Native函数:        {len(self.native_funcs):6d}")
        report.append(f"Struct定义:        {len(self.structs):6d}")
        if self.file_lines:
            report.append(f"总代码行数:        {sum(lines for _, lines in self.file_lines):6d}")
        report.append("")
        
        report.append("=" * 80)
        report.append("分析完成!")
        report.append("=" * 80)
        
        return "\n".join(report)
    
    def export_to_json(self, filename):
        """导出详细数据为JSON格式"""
        data = {
            "summary": {
                "keywords": len(self.keywords),
                "types": len(self.types),
                "operators": len(self.operators),
                "includes": len(self.includes),
                "constants": len(self.constants),
                "functions": len(self.functions),
                "native_functions": len(self.native_funcs),
                "structs": len(self.structs),
            },
            "keywords": sorted(list(self.keywords)),
            "types": sorted(list(self.types)),
            "operators": sorted(list(self.operators)),
            "function_prefixes": dict(sorted(self.function_prefixes.items(), 
                                           key=lambda x: x[1], reverse=True)[:50]),
            "constant_types": dict(self.constant_types),
            "native_categories": {k: len(v) for k, v in self.native_categories.items()},
            "include_frequency": dict(Counter(self.includes).most_common(50)),
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"JSON数据已导出到: {filename}")


def main():
    """主函数"""
    import sys
    
    # 确定要分析的目录
    if len(sys.argv) > 1:
        directory = sys.argv[1]
    else:
        directory = "..\\galaxy_scripts\\"
    
    print("Galaxy Script 增强版语法分析器")
    print("=" * 80)
    print(f"分析目录: {directory}")
    print()
    
    # 创建分析器
    analyzer = EnhancedGalaxyAnalyzer()
    
    # 分析目录
    analyzer.analyze_directory(directory)
    
    # 生成报告
    print("\n生成增强版分析报告...")
    report = analyzer.generate_enhanced_report()
    
    # 保存报告
    output_file = "galaxy_enhanced_analysis.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\n报告已保存到: {output_file}")
    
    # 导出JSON
    json_file = "galaxy_analysis_data.json"
    analyzer.export_to_json(json_file)
    
    # 打印报告
    print("\n" + "=" * 80)
    print(report)


if __name__ == "__main__":
    main()