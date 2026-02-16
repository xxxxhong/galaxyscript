#!/usr/bin/env python3
"""
Galaxy Script Compiler - 完整编译器
包含词法分析、语法分析、代码生成
"""

from galaxy_lexer import Lexer, TokenType
from galaxy_parser import *
import sys

class CodeGenerator:
    """代码生成器 - 将AST转换为目标代码"""
    
    def __init__(self):
        self.output = []
        self.indent_level = 0
    
    def indent(self):
        """增加缩进"""
        self.indent_level += 1
    
    def dedent(self):
        """减少缩进"""
        self.indent_level = max(0, self.indent_level - 1)
    
    def emit(self, code: str):
        """输出代码"""
        indent_str = "    " * self.indent_level
        self.output.append(indent_str + code)
    
    def generate(self, node: ASTNode) -> str:
        """生成代码"""
        if isinstance(node, Program):
            return self.generate_program(node)
        elif isinstance(node, IncludeStatement):
            return self.generate_include(node)
        elif isinstance(node, ConstDeclaration):
            return self.generate_const(node)
        elif isinstance(node, VariableDeclaration):
            return self.generate_variable(node)
        elif isinstance(node, FunctionDeclaration):
            return self.generate_function(node)
        elif isinstance(node, StructDeclaration):
            return self.generate_struct(node)
        elif isinstance(node, BlockStatement):
            return self.generate_block(node)
        elif isinstance(node, IfStatement):
            return self.generate_if(node)
        elif isinstance(node, WhileStatement):
            return self.generate_while(node)
        elif isinstance(node, ForStatement):
            return self.generate_for(node)
        elif isinstance(node, ReturnStatement):
            return self.generate_return(node)
        elif isinstance(node, BreakStatement):
            return "break;"
        elif isinstance(node, ContinueStatement):
            return "continue;"
        elif isinstance(node, AssignmentStatement):
            return self.generate_assignment(node)
        elif isinstance(node, ExpressionStatement):
            return self.generate_expression(node.expression) + ";"
        else:
            return self.generate_expression(node)
    
    def generate_program(self, node: Program) -> str:
        """生成程序代码"""
        for stmt in node.statements:
            code = self.generate(stmt)
            if isinstance(stmt, (FunctionDeclaration, StructDeclaration)):
                self.emit(code)
                self.emit("")  # 空行
            else:
                self.emit(code)
        return "\n".join(self.output)
    
    def generate_include(self, node: IncludeStatement) -> str:
        """生成include语句"""
        return f'include "{node.path}"'
    
    def generate_const(self, node: ConstDeclaration) -> str:
        """生成常量声明"""
        value = self.generate_expression(node.value)
        return f"const {node.type} {node.name} = {value};"
    
    def generate_variable(self, node: VariableDeclaration) -> str:
        """生成变量声明"""
        prefix = "static " if node.is_static else ""
        type_str = node.type
        name = node.name
        
        if node.is_array:
            array_part = f"[{self.generate_expression(node.array_size)}]" if node.array_size else "[]"
            type_str += array_part
        
        if node.initial_value:
            value = self.generate_expression(node.initial_value)
            return f"{prefix}{type_str} {name} = {value};"
        else:
            return f"{prefix}{type_str} {name};"
    
    def generate_function(self, node: FunctionDeclaration) -> str:
        """生成函数声明"""
        if node.is_native:
            params = ", ".join([
                f"{p.type} {p.name}{'[]' if p.is_array else ''}"
                for p in node.parameters
            ])
            return f"native {node.return_type} {node.name}({params});"
        
        params = ", ".join([
            f"{p.type} {p.name}{'[]' if p.is_array else ''}"
            for p in node.parameters
        ])
        
        result = f"{node.return_type} {node.name}({params}) "
        body = self.generate_block(node.body, inline=True)
        return result + body
    
    def generate_struct(self, node: StructDeclaration) -> str:
        """生成struct声明"""
        lines = [f"struct {node.name} {{"]
        for member in node.members:
            array_part = ""
            if member.is_array:
                if member.array_size:
                    array_part = f"[{self.generate_expression(member.array_size)}]"
                else:
                    array_part = "[]"
            lines.append(f"    {member.type} {member.name}{array_part};")
        lines.append("};")
        return "\n".join(lines)
    
    def generate_block(self, node: BlockStatement, inline: bool = False) -> str:
        """生成块语句"""
        if not inline:
            lines = ["{"]
            for stmt in node.statements:
                code = self.generate(stmt)
                lines.append("    " + code)
            lines.append("}")
            return "\n".join(lines)
        else:
            if not node.statements:
                return "{ }"
            
            result = "{\n"
            self.indent()
            for stmt in node.statements:
                code = self.generate(stmt)
                result += "    " * self.indent_level + code + "\n"
            self.dedent()
            result += "    " * self.indent_level + "}"
            return result
    
    def generate_if(self, node: IfStatement) -> str:
        """生成if语句"""
        condition = self.generate_expression(node.condition)
        then_part = self.generate(node.then_branch)
        
        result = f"if ({condition})"
        
        if isinstance(node.then_branch, BlockStatement):
            result += " " + then_part
        else:
            result += "\n    " + then_part
        
        if node.else_branch:
            else_part = self.generate(node.else_branch)
            if isinstance(node.else_branch, BlockStatement):
                result += "\nelse " + else_part
            else:
                result += "\nelse\n    " + else_part
        
        return result
    
    def generate_while(self, node: WhileStatement) -> str:
        """生成while语句"""
        condition = self.generate_expression(node.condition)
        body = self.generate(node.body)
        
        result = f"while ({condition})"
        if isinstance(node.body, BlockStatement):
            result += " " + body
        else:
            result += "\n    " + body
        
        return result
    
    def generate_for(self, node: ForStatement) -> str:
        """生成for语句"""
        init = self.generate(node.init).rstrip(';') if node.init else ""
        condition = self.generate_expression(node.condition) if node.condition else ""
        update = self.generate_expression(node.update) if node.update else ""
        
        result = f"for ({init}; {condition}; {update})"
        body = self.generate(node.body)
        
        if isinstance(node.body, BlockStatement):
            result += " " + body
        else:
            result += "\n    " + body
        
        return result
    
    def generate_return(self, node: ReturnStatement) -> str:
        """生成return语句"""
        if node.value:
            value = self.generate_expression(node.value)
            return f"return {value};"
        return "return;"
    
    def generate_assignment(self, node: AssignmentStatement) -> str:
        """生成赋值语句"""
        target = self.generate_expression(node.target)
        value = self.generate_expression(node.value)
        
        op_map = {
            'ASSIGN': '=',
            'PLUS_ASSIGN': '+=',
            'MINUS_ASSIGN': '-=',
            'MULT_ASSIGN': '*=',
            'DIV_ASSIGN': '/='
        }
        operator = op_map.get(node.operator, '=')
        
        return f"{target} {operator} {value};"
    
    def generate_expression(self, node: ASTNode) -> str:
        """生成表达式"""
        if isinstance(node, IntegerLiteral):
            return str(node.value)
        elif isinstance(node, FixedLiteral):
            return str(node.value)
        elif isinstance(node, StringLiteral):
            return f'"{node.value}"'
        elif isinstance(node, BooleanLiteral):
            return "true" if node.value else "false"
        elif isinstance(node, NullLiteral):
            return "null"
        elif isinstance(node, Identifier):
            return node.name
        elif isinstance(node, BinaryOp):
            left = self.generate_expression(node.left)
            right = self.generate_expression(node.right)
            return f"({left} {node.operator} {right})"
        elif isinstance(node, UnaryOp):
            operand = self.generate_expression(node.operand)
            if node.operator in ['++', '--'] and not isinstance(node.operand, Identifier):
                # 后缀形式
                return f"{operand}{node.operator}"
            else:
                # 前缀形式
                return f"{node.operator}{operand}"
        elif isinstance(node, FunctionCall):
            args = ", ".join([self.generate_expression(arg) for arg in node.arguments])
            return f"{node.name}({args})"
        elif isinstance(node, ArrayAccess):
            array = self.generate_expression(node.array)
            index = self.generate_expression(node.index)
            return f"{array}[{index}]"
        elif isinstance(node, MemberAccess):
            obj = self.generate_expression(node.object)
            return f"{obj}.{node.member}"
        else:
            return str(node)


class GalaxyCompiler:
    """Galaxy编译器主类"""
    
    def __init__(self):
        self.lexer = None
        self.parser = None
        self.codegen = None
    
    def compile(self, source_code: str) -> str:
        """编译源代码"""
        # 词法分析
        print(">>> 词法分析中...")
        self.lexer = Lexer(source_code)
        tokens = self.lexer.tokenize()
        print(f"    生成了 {len(tokens)} 个tokens")
        
        # 语法分析
        print(">>> 语法分析中...")
        self.parser = Parser(tokens)
        ast = self.parser.parse()
        print(f"    生成了AST,包含 {len(ast.statements)} 个顶层语句")
        
        # 代码生成
        print(">>> 代码生成中...")
        self.codegen = CodeGenerator()
        output_code = self.codegen.generate(ast)
        print("    代码生成完成")
        
        return output_code
    
    def compile_file(self, input_file: str, output_file: str = None):
        """编译文件"""
        print(f"\n编译文件: {input_file}")
        print("=" * 60)
        
        # 读取源文件
        with open(input_file, 'r', encoding='utf-8') as f:
            source_code = f.read()
        
        # 编译
        try:
            output_code = self.compile(source_code)
            
            # 输出到文件
            if output_file:
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(output_code)
                print(f"\n输出已保存到: {output_file}")
            else:
                print("\n生成的代码:")
                print("=" * 60)
                print(output_code)
            
            return True
        
        except Exception as e:
            print(f"\n编译错误: {e}")
            import traceback
            traceback.print_exc()
            return False


def main():
    """主函数"""
    if len(sys.argv) < 2:
        # 演示模式
        print("Galaxy Script 编译器 v1.0")
        print("=" * 60)
        print("演示模式: 编译测试代码\n")
        
        test_code = '''
// Galaxy Script 测试程序
include "TriggerLibs/NativeLib"

const int MAX_PLAYERS = 16;
const fixed PI = 3.14159;

struct Player {
    int id;
    string name;
    bool isActive;
    fixed score;
};

int add(int a, int b) {
    return a + b;
}

int factorial(int n) {
    if (n <= 1) {
        return 1;
    }
    return n * factorial(n - 1);
}

void main() {
    int x = 10;
    int y = 20;
    int result;
    
    result = add(x, y);
    
    // 测试循环
    int i;
    for (i = 0; i < MAX_PLAYERS; i += 1) {
        result = result + i;
    }
    
    // 测试条件语句
    if (result > 100) {
        result = 100;
    } else {
        result = result * 2;
    }
    
    // 测试while循环
    while (x > 0) {
        x = x - 1;
    }
}
'''
        
        compiler = GalaxyCompiler()
        output = compiler.compile(test_code)
        
        print("\n生成的代码:")
        print("=" * 60)
        print(output)
        
    else:
        # 文件编译模式
        input_file = sys.argv[1]
        output_file = sys.argv[2] if len(sys.argv) > 2 else None
        
        compiler = GalaxyCompiler()
        success = compiler.compile_file(input_file, output_file)
        
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
