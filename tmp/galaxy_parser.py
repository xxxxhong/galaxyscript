#!/usr/bin/env python3
"""
Galaxy Script Parser (语法分析器)
将token流转换为抽象语法树(AST)
"""

from dataclasses import dataclass
from typing import List, Optional, Union
from galaxy_lexer import Token, TokenType, Lexer

# AST节点定义

@dataclass
class ASTNode:
    """AST基类"""
    pass

# 表达式节点

@dataclass
class IntegerLiteral(ASTNode):
    value: int
    line: int = 0
    column: int = 0

@dataclass
class FixedLiteral(ASTNode):
    value: float
    line: int = 0
    column: int = 0

@dataclass
class StringLiteral(ASTNode):
    value: str
    line: int = 0
    column: int = 0

@dataclass
class BooleanLiteral(ASTNode):
    value: bool
    line: int = 0
    column: int = 0

@dataclass
class NullLiteral(ASTNode):
    line: int = 0
    column: int = 0

@dataclass
class Identifier(ASTNode):
    name: str
    line: int = 0
    column: int = 0

@dataclass
class BinaryOp(ASTNode):
    operator: str
    left: ASTNode
    right: ASTNode
    line: int = 0
    column: int = 0

@dataclass
class UnaryOp(ASTNode):
    operator: str
    operand: ASTNode
    line: int = 0
    column: int = 0

@dataclass
class FunctionCall(ASTNode):
    name: str
    arguments: List[ASTNode]
    line: int = 0
    column: int = 0

@dataclass
class ArrayAccess(ASTNode):
    array: ASTNode
    index: ASTNode
    line: int = 0
    column: int = 0

@dataclass
class MemberAccess(ASTNode):
    object: ASTNode
    member: str
    line: int = 0
    column: int = 0

# 语句节点

@dataclass
class IncludeStatement(ASTNode):
    path: str
    line: int = 0
    column: int = 0

@dataclass
class ConstDeclaration(ASTNode):
    type: str
    name: str
    value: ASTNode
    line: int = 0
    column: int = 0

@dataclass
class VariableDeclaration(ASTNode):
    type: str
    name: str
    is_array: bool = False
    array_size: Optional[ASTNode] = None
    initial_value: Optional[ASTNode] = None
    is_static: bool = False
    line: int = 0
    column: int = 0

@dataclass
class Parameter(ASTNode):
    type: str
    name: str
    is_array: bool = False
    line: int = 0
    column: int = 0

@dataclass
class FunctionDeclaration(ASTNode):
    return_type: str
    name: str
    parameters: List[Parameter]
    body: 'BlockStatement'
    is_native: bool = False
    line: int = 0
    column: int = 0

@dataclass
class StructMember(ASTNode):
    type: str
    name: str
    is_array: bool = False
    array_size: Optional[ASTNode] = None
    line: int = 0
    column: int = 0

@dataclass
class StructDeclaration(ASTNode):
    name: str
    members: List[StructMember]
    line: int = 0
    column: int = 0

@dataclass
class BlockStatement(ASTNode):
    statements: List[ASTNode]
    line: int = 0
    column: int = 0

@dataclass
class IfStatement(ASTNode):
    condition: ASTNode
    then_branch: ASTNode
    else_branch: Optional[ASTNode] = None
    line: int = 0
    column: int = 0

@dataclass
class WhileStatement(ASTNode):
    condition: ASTNode
    body: ASTNode
    line: int = 0
    column: int = 0

@dataclass
class ForStatement(ASTNode):
    init: Optional[ASTNode]
    condition: Optional[ASTNode]
    update: Optional[ASTNode]
    body: ASTNode
    line: int = 0
    column: int = 0

@dataclass
class ReturnStatement(ASTNode):
    value: Optional[ASTNode] = None
    line: int = 0
    column: int = 0

@dataclass
class BreakStatement(ASTNode):
    line: int = 0
    column: int = 0

@dataclass
class ContinueStatement(ASTNode):
    line: int = 0
    column: int = 0

@dataclass
class AssignmentStatement(ASTNode):
    target: ASTNode
    operator: str
    value: ASTNode
    line: int = 0
    column: int = 0

@dataclass
class ExpressionStatement(ASTNode):
    expression: ASTNode
    line: int = 0
    column: int = 0

@dataclass
class Program(ASTNode):
    statements: List[ASTNode]
    line: int = 0
    column: int = 0


class Parser:
    """Galaxy语法分析器"""
    
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0
    
    def current_token(self) -> Token:
        """获取当前token"""
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return self.tokens[-1]  # EOF
    
    def peek_token(self, offset: int = 1) -> Token:
        """向前查看token"""
        pos = self.pos + offset
        if pos < len(self.tokens):
            return self.tokens[pos]
        return self.tokens[-1]  # EOF
    
    def advance(self):
        """前进一个token"""
        if self.pos < len(self.tokens) - 1:
            self.pos += 1
    
    def expect(self, token_type: TokenType) -> Token:
        """期望特定类型的token"""
        token = self.current_token()
        if token.type != token_type:
            raise SyntaxError(
                f"Expected {token_type.name}, got {token.type.name} "
                f"at {token.line}:{token.column}"
            )
        self.advance()
        return token
    
    def is_type(self, token: Token) -> bool:
        """检查token是否为类型"""
        return token.type in [
            TokenType.VOID, TokenType.INT, TokenType.BOOL, TokenType.FIXED,
            TokenType.STRING, TokenType.BYTE, TokenType.POINT, TokenType.UNIT,
            TokenType.TIMER, TokenType.PLAYERGROUP, TokenType.UNITGROUP,
            TokenType.REGION, TokenType.TEXT, TokenType.ABILCMD, TokenType.SOUND,
            TokenType.MARKER, TokenType.ORDER, TokenType.BANK, TokenType.CAMERAINFO,
            TokenType.IDENTIFIER  # 用户定义的struct类型
        ]
    
    def parse(self) -> Program:
        """解析程序"""
        statements = []
        while self.current_token().type != TokenType.EOF:
            stmt = self.parse_statement()
            if stmt:
                statements.append(stmt)
        return Program(statements=statements)
    
    def parse_statement(self) -> Optional[ASTNode]:
        """解析语句"""
        token = self.current_token()
        
        if token.type == TokenType.INCLUDE:
            return self.parse_include()
        elif token.type == TokenType.CONST:
            return self.parse_const_declaration()
        elif token.type == TokenType.STATIC:
            return self.parse_variable_declaration(is_static=True)
        elif token.type == TokenType.STRUCT:
            return self.parse_struct_declaration()
        elif token.type == TokenType.NATIVE:
            return self.parse_native_declaration()
        elif self.is_type(token):
            # 可能是函数声明或变量声明
            return self.parse_type_statement()
        elif token.type == TokenType.IF:
            return self.parse_if_statement()
        elif token.type == TokenType.WHILE:
            return self.parse_while_statement()
        elif token.type == TokenType.FOR:
            return self.parse_for_statement()
        elif token.type == TokenType.RETURN:
            return self.parse_return_statement()
        elif token.type == TokenType.BREAK:
            return self.parse_break_statement()
        elif token.type == TokenType.CONTINUE:
            return self.parse_continue_statement()
        elif token.type == TokenType.LBRACE:
            return self.parse_block_statement()
        else:
            # 尝试解析表达式语句或赋值语句
            return self.parse_expression_or_assignment()
    
    def parse_include(self) -> IncludeStatement:
        """解析include语句"""
        line = self.current_token().line
        col = self.current_token().column
        self.expect(TokenType.INCLUDE)
        path_token = self.expect(TokenType.STRING_LITERAL)
        return IncludeStatement(path=path_token.value, line=line, column=col)
    
    def parse_const_declaration(self) -> ConstDeclaration:
        """解析const声明"""
        line = self.current_token().line
        col = self.current_token().column
        self.expect(TokenType.CONST)
        
        type_token = self.current_token()
        type_name = type_token.type.name.lower() if type_token.type != TokenType.IDENTIFIER else type_token.value
        self.advance()
        
        name_token = self.expect(TokenType.IDENTIFIER)
        self.expect(TokenType.ASSIGN)
        value = self.parse_expression()
        self.expect(TokenType.SEMICOLON)
        
        return ConstDeclaration(
            type=type_name,
            name=name_token.value,
            value=value,
            line=line,
            column=col
        )
    
    def parse_variable_declaration(self, is_static: bool = False) -> VariableDeclaration:
        """解析变量声明"""
        line = self.current_token().line
        col = self.current_token().column
        
        if is_static:
            self.expect(TokenType.STATIC)
        
        type_token = self.current_token()
        type_name = type_token.type.name.lower() if type_token.type != TokenType.IDENTIFIER else type_token.value
        self.advance()
        
        name_token = self.expect(TokenType.IDENTIFIER)
        
        is_array = False
        array_size = None
        initial_value = None
        
        # 检查是否为数组
        if self.current_token().type == TokenType.LBRACKET:
            is_array = True
            self.advance()
            if self.current_token().type != TokenType.RBRACKET:
                array_size = self.parse_expression()
            self.expect(TokenType.RBRACKET)
        
        # 检查初始值
        if self.current_token().type == TokenType.ASSIGN:
            self.advance()
            initial_value = self.parse_expression()
        
        self.expect(TokenType.SEMICOLON)
        
        return VariableDeclaration(
            type=type_name,
            name=name_token.value,
            is_array=is_array,
            array_size=array_size,
            initial_value=initial_value,
            is_static=is_static,
            line=line,
            column=col
        )
    
    def parse_type_statement(self) -> Union[FunctionDeclaration, VariableDeclaration]:
        """解析以类型开头的语句(函数或变量声明)"""
        # 保存当前位置
        saved_pos = self.pos
        
        type_token = self.current_token()
        
        # 如果type_token是IDENTIFIER但不是已知类型,可能是赋值语句
        if type_token.type == TokenType.IDENTIFIER:
            # 需要检查后续token来判断
            self.advance()
            next_token = self.current_token()
            
            # 恢复位置
            self.pos = saved_pos
            
            # 如果下一个token是赋值运算符,这是赋值语句
            if next_token.type in [TokenType.ASSIGN, TokenType.PLUS_ASSIGN, 
                                   TokenType.MINUS_ASSIGN, TokenType.MULT_ASSIGN,
                                   TokenType.DIV_ASSIGN, TokenType.LBRACKET, TokenType.DOT]:
                return self.parse_expression_or_assignment()
        
        # 现在解析类型声明
        self.advance()  # 跳过类型token
        name_token = self.current_token()
        self.advance()  # 跳过名称token
        
        # 检查是否为函数声明
        if self.current_token().type == TokenType.LPAREN:
            # 恢复位置并解析函数
            self.pos = saved_pos
            return self.parse_function_declaration()
        else:
            # 恢复位置并解析变量
            self.pos = saved_pos
            return self.parse_variable_declaration()
    
    def parse_function_declaration(self) -> FunctionDeclaration:
        """解析函数声明"""
        line = self.current_token().line
        col = self.current_token().column
        
        type_token = self.current_token()
        return_type = type_token.type.name.lower() if type_token.type != TokenType.IDENTIFIER else type_token.value
        self.advance()
        
        name_token = self.expect(TokenType.IDENTIFIER)
        self.expect(TokenType.LPAREN)
        
        parameters = []
        if self.current_token().type != TokenType.RPAREN:
            parameters = self.parse_parameter_list()
        
        self.expect(TokenType.RPAREN)
        body = self.parse_block_statement()
        
        return FunctionDeclaration(
            return_type=return_type,
            name=name_token.value,
            parameters=parameters,
            body=body,
            line=line,
            column=col
        )
    
    def parse_native_declaration(self) -> FunctionDeclaration:
        """解析native函数声明"""
        line = self.current_token().line
        col = self.current_token().column
        
        self.expect(TokenType.NATIVE)
        
        type_token = self.current_token()
        return_type = type_token.type.name.lower() if type_token.type != TokenType.IDENTIFIER else type_token.value
        self.advance()
        
        name_token = self.expect(TokenType.IDENTIFIER)
        self.expect(TokenType.LPAREN)
        
        parameters = []
        if self.current_token().type != TokenType.RPAREN:
            parameters = self.parse_parameter_list()
        
        self.expect(TokenType.RPAREN)
        self.expect(TokenType.SEMICOLON)
        
        return FunctionDeclaration(
            return_type=return_type,
            name=name_token.value,
            parameters=parameters,
            body=BlockStatement(statements=[]),
            is_native=True,
            line=line,
            column=col
        )
    
    def parse_parameter_list(self) -> List[Parameter]:
        """解析参数列表"""
        parameters = []
        
        while True:
            param_type = self.current_token()
            param_type_name = param_type.type.name.lower() if param_type.type != TokenType.IDENTIFIER else param_type.value
            self.advance()
            
            param_name = self.expect(TokenType.IDENTIFIER)
            
            is_array = False
            if self.current_token().type == TokenType.LBRACKET:
                is_array = True
                self.advance()
                self.expect(TokenType.RBRACKET)
            
            parameters.append(Parameter(
                type=param_type_name,
                name=param_name.value,
                is_array=is_array
            ))
            
            if self.current_token().type != TokenType.COMMA:
                break
            self.advance()
        
        return parameters
    
    def parse_struct_declaration(self) -> StructDeclaration:
        """解析struct声明"""
        line = self.current_token().line
        col = self.current_token().column
        
        self.expect(TokenType.STRUCT)
        name_token = self.expect(TokenType.IDENTIFIER)
        self.expect(TokenType.LBRACE)
        
        members = []
        while self.current_token().type != TokenType.RBRACE:
            member_type = self.current_token()
            member_type_name = member_type.type.name.lower() if member_type.type != TokenType.IDENTIFIER else member_type.value
            self.advance()
            
            member_name = self.expect(TokenType.IDENTIFIER)
            
            is_array = False
            array_size = None
            if self.current_token().type == TokenType.LBRACKET:
                is_array = True
                self.advance()
                if self.current_token().type != TokenType.RBRACKET:
                    array_size = self.parse_expression()
                self.expect(TokenType.RBRACKET)
            
            self.expect(TokenType.SEMICOLON)
            
            members.append(StructMember(
                type=member_type_name,
                name=member_name.value,
                is_array=is_array,
                array_size=array_size
            ))
        
        self.expect(TokenType.RBRACE)
        self.expect(TokenType.SEMICOLON)
        
        return StructDeclaration(name=name_token.value, members=members, line=line, column=col)
    
    def parse_block_statement(self) -> BlockStatement:
        """解析块语句"""
        line = self.current_token().line
        col = self.current_token().column
        
        self.expect(TokenType.LBRACE)
        statements = []
        
        while self.current_token().type != TokenType.RBRACE:
            stmt = self.parse_statement()
            if stmt:
                statements.append(stmt)
        
        self.expect(TokenType.RBRACE)
        return BlockStatement(statements=statements, line=line, column=col)
    
    def parse_if_statement(self) -> IfStatement:
        """解析if语句"""
        line = self.current_token().line
        col = self.current_token().column
        
        self.expect(TokenType.IF)
        self.expect(TokenType.LPAREN)
        condition = self.parse_expression()
        self.expect(TokenType.RPAREN)
        
        then_branch = self.parse_statement()
        
        else_branch = None
        if self.current_token().type == TokenType.ELSE:
            self.advance()
            else_branch = self.parse_statement()
        
        return IfStatement(
            condition=condition,
            then_branch=then_branch,
            else_branch=else_branch,
            line=line,
            column=col
        )
    
    def parse_while_statement(self) -> WhileStatement:
        """解析while语句"""
        line = self.current_token().line
        col = self.current_token().column
        
        self.expect(TokenType.WHILE)
        self.expect(TokenType.LPAREN)
        condition = self.parse_expression()
        self.expect(TokenType.RPAREN)
        body = self.parse_statement()
        
        return WhileStatement(condition=condition, body=body, line=line, column=col)
    
    def parse_for_statement(self) -> ForStatement:
        """解析for语句"""
        line = self.current_token().line
        col = self.current_token().column
        
        self.expect(TokenType.FOR)
        self.expect(TokenType.LPAREN)
        
        # 解析初始化部分
        init = None
        if self.current_token().type != TokenType.SEMICOLON:
            # 检查是否为变量声明 - 必须是已知类型token开头
            if self.is_type(self.current_token()) and self.current_token().type != TokenType.IDENTIFIER:
                # 确定是类型关键字开头的变量声明
                init = self.parse_variable_declaration()
            else:
                # 可能是赋值或表达式
                init = self.parse_expression()
                self.expect(TokenType.SEMICOLON)
        else:
            self.advance()  # 跳过分号
        
        # 解析条件部分
        condition = None
        if self.current_token().type != TokenType.SEMICOLON:
            condition = self.parse_expression()
        self.expect(TokenType.SEMICOLON)
        
        # 解析更新部分
        update = None
        if self.current_token().type != TokenType.RPAREN:
            update = self.parse_expression()
        self.expect(TokenType.RPAREN)
        
        body = self.parse_statement()
        
        return ForStatement(
            init=init,
            condition=condition,
            update=update,
            body=body,
            line=line,
            column=col
        )
    
    def parse_return_statement(self) -> ReturnStatement:
        """解析return语句"""
        line = self.current_token().line
        col = self.current_token().column
        
        self.expect(TokenType.RETURN)
        
        value = None
        if self.current_token().type != TokenType.SEMICOLON:
            value = self.parse_expression()
        
        self.expect(TokenType.SEMICOLON)
        return ReturnStatement(value=value, line=line, column=col)
    
    def parse_break_statement(self) -> BreakStatement:
        """解析break语句"""
        line = self.current_token().line
        col = self.current_token().column
        self.expect(TokenType.BREAK)
        self.expect(TokenType.SEMICOLON)
        return BreakStatement(line=line, column=col)
    
    def parse_continue_statement(self) -> ContinueStatement:
        """解析continue语句"""
        line = self.current_token().line
        col = self.current_token().column
        self.expect(TokenType.CONTINUE)
        self.expect(TokenType.SEMICOLON)
        return ContinueStatement(line=line, column=col)
    
    def parse_expression_or_assignment(self) -> Union[ExpressionStatement, AssignmentStatement]:
        """解析表达式或赋值语句"""
        expr = self.parse_expression()
        
        # 检查是否为赋值
        if self.current_token().type in [TokenType.ASSIGN, TokenType.PLUS_ASSIGN,
                                         TokenType.MINUS_ASSIGN, TokenType.MULT_ASSIGN,
                                         TokenType.DIV_ASSIGN]:
            operator = self.current_token().type.name
            self.advance()
            value = self.parse_expression()
            self.expect(TokenType.SEMICOLON)
            return AssignmentStatement(target=expr, operator=operator, value=value)
        else:
            self.expect(TokenType.SEMICOLON)
            return ExpressionStatement(expression=expr)
    
    def parse_expression(self) -> ASTNode:
        """解析表达式"""
        return self.parse_logical_or()
    
    def parse_logical_or(self) -> ASTNode:
        """解析逻辑或"""
        left = self.parse_logical_and()
        
        while self.current_token().type == TokenType.OR:
            self.advance()
            right = self.parse_logical_and()
            left = BinaryOp(operator='||', left=left, right=right)
        
        return left
    
    def parse_logical_and(self) -> ASTNode:
        """解析逻辑与"""
        left = self.parse_equality()
        
        while self.current_token().type == TokenType.AND:
            self.advance()
            right = self.parse_equality()
            left = BinaryOp(operator='&&', left=left, right=right)
        
        return left
    
    def parse_equality(self) -> ASTNode:
        """解析相等性"""
        left = self.parse_relational()
        
        while self.current_token().type in [TokenType.EQ, TokenType.NE]:
            op = '==' if self.current_token().type == TokenType.EQ else '!='
            self.advance()
            right = self.parse_relational()
            left = BinaryOp(operator=op, left=left, right=right)
        
        return left
    
    def parse_relational(self) -> ASTNode:
        """解析关系运算"""
        left = self.parse_additive()
        
        while self.current_token().type in [TokenType.LT, TokenType.GT, TokenType.LE, TokenType.GE]:
            op_map = {
                TokenType.LT: '<',
                TokenType.GT: '>',
                TokenType.LE: '<=',
                TokenType.GE: '>='
            }
            op = op_map[self.current_token().type]
            self.advance()
            right = self.parse_additive()
            left = BinaryOp(operator=op, left=left, right=right)
        
        return left
    
    def parse_additive(self) -> ASTNode:
        """解析加减运算"""
        left = self.parse_multiplicative()
        
        while self.current_token().type in [TokenType.PLUS, TokenType.MINUS]:
            op = '+' if self.current_token().type == TokenType.PLUS else '-'
            self.advance()
            right = self.parse_multiplicative()
            left = BinaryOp(operator=op, left=left, right=right)
        
        return left
    
    def parse_multiplicative(self) -> ASTNode:
        """解析乘除运算"""
        left = self.parse_unary()
        
        while self.current_token().type in [TokenType.MULTIPLY, TokenType.DIVIDE]:
            op = '*' if self.current_token().type == TokenType.MULTIPLY else '/'
            self.advance()
            right = self.parse_unary()
            left = BinaryOp(operator=op, left=left, right=right)
        
        return left
    
    def parse_unary(self) -> ASTNode:
        """解析一元运算"""
        if self.current_token().type in [TokenType.NOT, TokenType.MINUS, TokenType.INCREMENT, TokenType.DECREMENT]:
            op_map = {
                TokenType.NOT: '!',
                TokenType.MINUS: '-',
                TokenType.INCREMENT: '++',
                TokenType.DECREMENT: '--'
            }
            op = op_map[self.current_token().type]
            self.advance()
            operand = self.parse_unary()
            return UnaryOp(operator=op, operand=operand)
        
        return self.parse_postfix()
    
    def parse_postfix(self) -> ASTNode:
        """解析后缀表达式"""
        expr = self.parse_primary()
        
        while True:
            if self.current_token().type == TokenType.LPAREN:
                # 函数调用
                self.advance()
                args = []
                if self.current_token().type != TokenType.RPAREN:
                    args.append(self.parse_expression())
                    while self.current_token().type == TokenType.COMMA:
                        self.advance()
                        args.append(self.parse_expression())
                self.expect(TokenType.RPAREN)
                
                if isinstance(expr, Identifier):
                    expr = FunctionCall(name=expr.name, arguments=args)
            
            elif self.current_token().type == TokenType.LBRACKET:
                # 数组访问
                self.advance()
                index = self.parse_expression()
                self.expect(TokenType.RBRACKET)
                expr = ArrayAccess(array=expr, index=index)
            
            elif self.current_token().type == TokenType.DOT:
                # 成员访问
                self.advance()
                member = self.expect(TokenType.IDENTIFIER)
                expr = MemberAccess(object=expr, member=member.value)
            
            elif self.current_token().type in [TokenType.INCREMENT, TokenType.DECREMENT]:
                # 后缀++/--
                op = '++' if self.current_token().type == TokenType.INCREMENT else '--'
                self.advance()
                expr = UnaryOp(operator=op, operand=expr)
            
            else:
                break
        
        return expr
    
    def parse_primary(self) -> ASTNode:
        """解析基本表达式"""
        token = self.current_token()
        
        if token.type == TokenType.INTEGER_LITERAL:
            self.advance()
            return IntegerLiteral(value=token.value)
        
        elif token.type == TokenType.FIXED_LITERAL:
            self.advance()
            return FixedLiteral(value=token.value)
        
        elif token.type == TokenType.STRING_LITERAL:
            self.advance()
            return StringLiteral(value=token.value)
        
        elif token.type == TokenType.TRUE:
            self.advance()
            return BooleanLiteral(value=True)
        
        elif token.type == TokenType.FALSE:
            self.advance()
            return BooleanLiteral(value=False)
        
        elif token.type == TokenType.NULL:
            self.advance()
            return NullLiteral()
        
        elif token.type == TokenType.IDENTIFIER:
            self.advance()
            return Identifier(name=token.value)
        
        elif token.type == TokenType.LPAREN:
            self.advance()
            expr = self.parse_expression()
            self.expect(TokenType.RPAREN)
            return expr
        
        else:
            raise SyntaxError(
                f"Unexpected token {token.type.name} at {token.line}:{token.column}"
            )


# 测试代码
if __name__ == "__main__":
    test_code = '''
    const int MAX_PLAYERS = 16;
    
    int add(int a, int b) {
        return a + b;
    }
    
    void main() {
        int x = 10;
        x = add(x, 5);
    }
    '''
    
    lexer = Lexer(test_code)
    tokens = lexer.tokenize()
    
    parser = Parser(tokens)
    ast = parser.parse()
    
    print("AST:")
    for stmt in ast.statements:
        print(stmt)
