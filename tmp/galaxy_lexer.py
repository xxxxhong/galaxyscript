#!/usr/bin/env python3
"""
Galaxy Script Lexer (词法分析器)
将Galaxy源代码转换为token流
"""

import re
from enum import Enum, auto
from dataclasses import dataclass
from typing import List, Optional

class TokenType(Enum):
    """Token类型枚举"""
    # 关键字
    IF = auto()
    ELSE = auto()
    WHILE = auto()
    FOR = auto()
    RETURN = auto()
    BREAK = auto()
    CONTINUE = auto()
    STRUCT = auto()
    CONST = auto()
    STATIC = auto()
    NATIVE = auto()
    INCLUDE = auto()
    
    # 类型
    VOID = auto()
    INT = auto()
    BOOL = auto()
    FIXED = auto()
    STRING = auto()
    BYTE = auto()
    POINT = auto()
    UNIT = auto()
    TIMER = auto()
    PLAYERGROUP = auto()
    UNITGROUP = auto()
    REGION = auto()
    TEXT = auto()
    ABILCMD = auto()
    SOUND = auto()
    MARKER = auto()
    ORDER = auto()
    BANK = auto()
    CAMERAINFO = auto()
    
    # 字面量
    INTEGER_LITERAL = auto()
    FIXED_LITERAL = auto()
    STRING_LITERAL = auto()
    TRUE = auto()
    FALSE = auto()
    NULL = auto()
    
    # 标识符
    IDENTIFIER = auto()
    
    # 运算符
    PLUS = auto()           # +
    MINUS = auto()          # -
    MULTIPLY = auto()       # *
    DIVIDE = auto()         # /
    ASSIGN = auto()         # =
    PLUS_ASSIGN = auto()    # +=
    MINUS_ASSIGN = auto()   # -=
    MULT_ASSIGN = auto()    # *=
    DIV_ASSIGN = auto()     # /=
    EQ = auto()             # ==
    NE = auto()             # !=
    LT = auto()             # <
    GT = auto()             # >
    LE = auto()             # <=
    GE = auto()             # >=
    AND = auto()            # &&
    OR = auto()             # ||
    NOT = auto()            # !
    INCREMENT = auto()      # ++
    DECREMENT = auto()      # --
    
    # 分隔符
    LPAREN = auto()         # (
    RPAREN = auto()         # )
    LBRACE = auto()         # {
    RBRACE = auto()         # }
    LBRACKET = auto()       # [
    RBRACKET = auto()       # ]
    SEMICOLON = auto()      # ;
    COMMA = auto()          # ,
    DOT = auto()            # .
    
    # 特殊
    EOF = auto()
    COMMENT = auto()

@dataclass
class Token:
    """Token数据类"""
    type: TokenType
    value: any
    line: int
    column: int
    
    def __repr__(self):
        return f"Token({self.type.name}, {repr(self.value)}, {self.line}:{self.column})"

class Lexer:
    """Galaxy语言词法分析器"""
    
    # 关键字映射
    KEYWORDS = {
        'if': TokenType.IF,
        'else': TokenType.ELSE,
        'while': TokenType.WHILE,
        'for': TokenType.FOR,
        'return': TokenType.RETURN,
        'break': TokenType.BREAK,
        'continue': TokenType.CONTINUE,
        'struct': TokenType.STRUCT,
        'const': TokenType.CONST,
        'static': TokenType.STATIC,
        'native': TokenType.NATIVE,
        'include': TokenType.INCLUDE,
        'void': TokenType.VOID,
        'int': TokenType.INT,
        'bool': TokenType.BOOL,
        'fixed': TokenType.FIXED,
        'string': TokenType.STRING,
        'byte': TokenType.BYTE,
        'point': TokenType.POINT,
        'unit': TokenType.UNIT,
        'timer': TokenType.TIMER,
        'playergroup': TokenType.PLAYERGROUP,
        'unitgroup': TokenType.UNITGROUP,
        'region': TokenType.REGION,
        'text': TokenType.TEXT,
        'abilcmd': TokenType.ABILCMD,
        'sound': TokenType.SOUND,
        'marker': TokenType.MARKER,
        'order': TokenType.ORDER,
        'bank': TokenType.BANK,
        'camerainfo': TokenType.CAMERAINFO,
        'true': TokenType.TRUE,
        'false': TokenType.FALSE,
        'null': TokenType.NULL,
    }
    
    def __init__(self, source: str):
        self.source = source
        self.pos = 0
        self.line = 1
        self.column = 1
        self.tokens: List[Token] = []
    
    def current_char(self) -> Optional[str]:
        """获取当前字符"""
        if self.pos >= len(self.source):
            return None
        return self.source[self.pos]
    
    def peek_char(self, offset: int = 1) -> Optional[str]:
        """向前查看字符"""
        pos = self.pos + offset
        if pos >= len(self.source):
            return None
        return self.source[pos]
    
    def advance(self):
        """前进一个字符"""
        if self.pos < len(self.source):
            if self.source[self.pos] == '\n':
                self.line += 1
                self.column = 1
            else:
                self.column += 1
            self.pos += 1
    
    def skip_whitespace(self):
        """跳过空白字符"""
        while self.current_char() and self.current_char() in ' \t\n\r':
            self.advance()
    
    def skip_comment(self):
        """跳过注释"""
        if self.current_char() == '/' and self.peek_char() == '/':
            # 单行注释
            while self.current_char() and self.current_char() != '\n':
                self.advance()
            return True
        elif self.current_char() == '/' and self.peek_char() == '*':
            # 多行注释
            self.advance()  # /
            self.advance()  # *
            while self.current_char():
                if self.current_char() == '*' and self.peek_char() == '/':
                    self.advance()  # *
                    self.advance()  # /
                    return True
                self.advance()
            return True
        return False
    
    def read_number(self) -> Token:
        """读取数字字面量"""
        start_line = self.line
        start_col = self.column
        num_str = ''
        
        while self.current_char() and (self.current_char().isdigit() or self.current_char() == '.'):
            num_str += self.current_char()
            self.advance()
        
        if '.' in num_str:
            return Token(TokenType.FIXED_LITERAL, float(num_str), start_line, start_col)
        else:
            return Token(TokenType.INTEGER_LITERAL, int(num_str), start_line, start_col)
    
    def read_string(self) -> Token:
        """读取字符串字面量"""
        start_line = self.line
        start_col = self.column
        self.advance()  # 跳过开始的引号
        
        string_val = ''
        while self.current_char() and self.current_char() != '"':
            if self.current_char() == '\\':
                self.advance()
                # 处理转义字符
                if self.current_char() in 'nrt"\\':
                    escape_chars = {'n': '\n', 'r': '\r', 't': '\t', '"': '"', '\\': '\\'}
                    string_val += escape_chars.get(self.current_char(), self.current_char())
                    self.advance()
            else:
                string_val += self.current_char()
                self.advance()
        
        self.advance()  # 跳过结束的引号
        return Token(TokenType.STRING_LITERAL, string_val, start_line, start_col)
    
    def read_identifier(self) -> Token:
        """读取标识符或关键字"""
        start_line = self.line
        start_col = self.column
        identifier = ''
        
        while self.current_char() and (self.current_char().isalnum() or self.current_char() == '_'):
            identifier += self.current_char()
            self.advance()
        
        # 检查是否为关键字
        token_type = self.KEYWORDS.get(identifier, TokenType.IDENTIFIER)
        value = identifier if token_type == TokenType.IDENTIFIER else None
        
        return Token(token_type, value, start_line, start_col)
    
    def tokenize(self) -> List[Token]:
        """执行词法分析,返回token列表"""
        while self.current_char():
            self.skip_whitespace()
            
            if not self.current_char():
                break
            
            # 跳过注释
            if self.skip_comment():
                continue
            
            start_line = self.line
            start_col = self.column
            char = self.current_char()
            
            # 数字
            if char.isdigit():
                self.tokens.append(self.read_number())
            
            # 字符串
            elif char == '"':
                self.tokens.append(self.read_string())
            
            # 标识符或关键字
            elif char.isalpha() or char == '_':
                self.tokens.append(self.read_identifier())
            
            # 运算符和分隔符
            elif char == '+':
                self.advance()
                if self.current_char() == '+':
                    self.tokens.append(Token(TokenType.INCREMENT, None, start_line, start_col))
                    self.advance()
                elif self.current_char() == '=':
                    self.tokens.append(Token(TokenType.PLUS_ASSIGN, None, start_line, start_col))
                    self.advance()
                else:
                    self.tokens.append(Token(TokenType.PLUS, None, start_line, start_col))
            
            elif char == '-':
                self.advance()
                if self.current_char() == '-':
                    self.tokens.append(Token(TokenType.DECREMENT, None, start_line, start_col))
                    self.advance()
                elif self.current_char() == '=':
                    self.tokens.append(Token(TokenType.MINUS_ASSIGN, None, start_line, start_col))
                    self.advance()
                else:
                    self.tokens.append(Token(TokenType.MINUS, None, start_line, start_col))
            
            elif char == '*':
                self.advance()
                if self.current_char() == '=':
                    self.tokens.append(Token(TokenType.MULT_ASSIGN, None, start_line, start_col))
                    self.advance()
                else:
                    self.tokens.append(Token(TokenType.MULTIPLY, None, start_line, start_col))
            
            elif char == '/':
                self.advance()
                if self.current_char() == '=':
                    self.tokens.append(Token(TokenType.DIV_ASSIGN, None, start_line, start_col))
                    self.advance()
                else:
                    self.tokens.append(Token(TokenType.DIVIDE, None, start_line, start_col))
            
            elif char == '=':
                self.advance()
                if self.current_char() == '=':
                    self.tokens.append(Token(TokenType.EQ, None, start_line, start_col))
                    self.advance()
                else:
                    self.tokens.append(Token(TokenType.ASSIGN, None, start_line, start_col))
            
            elif char == '!':
                self.advance()
                if self.current_char() == '=':
                    self.tokens.append(Token(TokenType.NE, None, start_line, start_col))
                    self.advance()
                else:
                    self.tokens.append(Token(TokenType.NOT, None, start_line, start_col))
            
            elif char == '<':
                self.advance()
                if self.current_char() == '=':
                    self.tokens.append(Token(TokenType.LE, None, start_line, start_col))
                    self.advance()
                else:
                    self.tokens.append(Token(TokenType.LT, None, start_line, start_col))
            
            elif char == '>':
                self.advance()
                if self.current_char() == '=':
                    self.tokens.append(Token(TokenType.GE, None, start_line, start_col))
                    self.advance()
                else:
                    self.tokens.append(Token(TokenType.GT, None, start_line, start_col))
            
            elif char == '&':
                self.advance()
                if self.current_char() == '&':
                    self.tokens.append(Token(TokenType.AND, None, start_line, start_col))
                    self.advance()
            
            elif char == '|':
                self.advance()
                if self.current_char() == '|':
                    self.tokens.append(Token(TokenType.OR, None, start_line, start_col))
                    self.advance()
            
            elif char == '(':
                self.tokens.append(Token(TokenType.LPAREN, None, start_line, start_col))
                self.advance()
            
            elif char == ')':
                self.tokens.append(Token(TokenType.RPAREN, None, start_line, start_col))
                self.advance()
            
            elif char == '{':
                self.tokens.append(Token(TokenType.LBRACE, None, start_line, start_col))
                self.advance()
            
            elif char == '}':
                self.tokens.append(Token(TokenType.RBRACE, None, start_line, start_col))
                self.advance()
            
            elif char == '[':
                self.tokens.append(Token(TokenType.LBRACKET, None, start_line, start_col))
                self.advance()
            
            elif char == ']':
                self.tokens.append(Token(TokenType.RBRACKET, None, start_line, start_col))
                self.advance()
            
            elif char == ';':
                self.tokens.append(Token(TokenType.SEMICOLON, None, start_line, start_col))
                self.advance()
            
            elif char == ',':
                self.tokens.append(Token(TokenType.COMMA, None, start_line, start_col))
                self.advance()
            
            elif char == '.':
                self.advance()
                if self.current_char() and self.current_char().isdigit():
                    # 这是一个小数
                    num_str = '0.'
                    while self.current_char() and self.current_char().isdigit():
                        num_str += self.current_char()
                        self.advance()
                    self.tokens.append(Token(TokenType.FIXED_LITERAL, float(num_str), start_line, start_col))
                else:
                    self.tokens.append(Token(TokenType.DOT, None, start_line, start_col))
            
            else:
                raise SyntaxError(f"Unexpected character '{char}' at {start_line}:{start_col}")
        
        # 添加EOF token
        self.tokens.append(Token(TokenType.EOF, None, self.line, self.column))
        return self.tokens

# 测试代码
if __name__ == "__main__":
    # 测试示例
    test_code = '''
    const int c_maxValue = 100;
    
    // 这是一个注释
    int add(int a, int b) {
        return a + b;
    }
    
    /* 多行注释
       测试 */
    void main() {
        int x = 10;
        fixed y = 3.14;
        string name = "Galaxy";
        bool flag = true;
        
        if (x > 5) {
            x += 1;
        }
    }
    '''
    
    lexer = Lexer(test_code)
    tokens = lexer.tokenize()
    
    print("Token列表:")
    for token in tokens:
        print(token)
