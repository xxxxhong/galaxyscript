#!/usr/bin/env python3
"""
Galaxy Script Parser using Lark
================================

This module demonstrates how to parse Galaxy Script using the Lark parsing library.

Installation:
    pip install lark

Usage:
    python galaxy_parser_lark.py [file.galaxy]
"""

from lark import Lark, Tree, Token
from lark.visitors import Transformer, Interpreter
from pathlib import Path
import sys

# ============================================================================
# GRAMMAR (Can also be loaded from galaxy.lark file)
# ============================================================================

GALAXY_GRAMMAR = r"""
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

struct_specifier: "struct" IDENTIFIER "{" struct_member_list "}"
                | "struct" "{" struct_member_list "}"
                | "struct" IDENTIFIER

struct_member_list: struct_member+

struct_member: type_specifier struct_declarator_list ";"

struct_declarator_list: struct_declarator ("," struct_declarator)*

struct_declarator: declarator

function_definition: type_specifier IDENTIFIER "(" parameter_list? ")" compound_statement

parameter_list: parameter_declaration ("," parameter_declaration)*

parameter_declaration: type_specifier IDENTIFIER ("[" constant_expression? "]")?

native_declaration: "native" type_specifier IDENTIFIER "(" native_parameter_list? ")" ";"

native_parameter_list: native_parameter_declaration ("," native_parameter_declaration)*

native_parameter_declaration: type_specifier IDENTIFIER ("[" "]")?

statement: compound_statement
         | expression_statement
         | selection_statement
         | iteration_statement
         | jump_statement

compound_statement: "{" (declaration | statement)* "}"

expression_statement: expression? ";"

selection_statement: "if" "(" expression ")" statement ("else" statement)?

iteration_statement: "while" "(" expression ")" statement
                   | "for" "(" for_init_clause ";" for_condition_clause ";" for_iteration_clause ")" statement

for_init_clause: (expression | declaration_specifiers init_declarator_list)?

for_condition_clause: expression?

for_iteration_clause: expression?

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
                | unary_operator unary_expression

unary_operator: "+" | "-" | "!"

postfix_expression: primary_expression
                  | postfix_expression "[" expression "]"
                  | postfix_expression "(" argument_expression_list? ")"
                  | postfix_expression "." IDENTIFIER
                  | postfix_expression ("++" | "--")

argument_expression_list: assignment_expression ("," assignment_expression)*

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

# ============================================================================
# AST TRANSFORMER
# ============================================================================

class GalaxyTransformer(Transformer):
    """
    Transforms the parse tree into a more usable AST.
    
    Example transformations:
    - Flatten lists
    - Extract values from tokens
    - Create meaningful node types
    """
    
    def IDENTIFIER(self, token):
        return str(token)
    
    def INTEGER(self, token):
        return int(token)
    
    def FIXED(self, token):
        return float(token)
    
    def STRING(self, token):
        # Remove quotes
        return str(token)[1:-1]
    
    def primitive_type(self, args):
        return ('primitive_type', args[0])
    
    def game_type(self, args):
        return ('game_type', args[0])

# ============================================================================
# AST VISITOR (for code generation, analysis, etc.)
# ============================================================================

class GalaxyVisitor:
    """
    Visits AST nodes and performs operations.
    Can be used for:
    - Code generation
    - Semantic analysis
    - Pretty printing
    - Optimization
    """
    
    def __init__(self):
        self.indent_level = 0
        self.output = []
    
    def visit(self, tree):
        """Visit a tree node"""
        method_name = f'visit_{tree.data}'
        method = getattr(self, method_name, self.generic_visit)
        return method(tree)
    
    def generic_visit(self, tree):
        """Default visit method"""
        for child in tree.children:
            if isinstance(child, Tree):
                self.visit(child)
    
    def visit_function_definition(self, tree):
        """Visit a function definition"""
        # Example: extract function name and parameters
        type_spec = tree.children[0]
        name = tree.children[1]
        params = tree.children[2] if len(tree.children) > 2 else None
        
        self.output.append(f"Function: {name}")
        return tree
    
    def get_output(self):
        return '\n'.join(self.output)

# ============================================================================
# PARSER CLASS
# ============================================================================

class GalaxyParser:
    """
    Main parser class for Galaxy Script
    """
    
    def __init__(self, grammar_file=None):
        """
        Initialize the parser
        
        Args:
            grammar_file: Path to .lark file (optional, uses embedded grammar if None)
        """
        if grammar_file:
            with open(grammar_file, 'r') as f:
                grammar = f.read()
        else:
            grammar = GALAXY_GRAMMAR
        
        # Create Lark parser
        # parser='lalr' is faster, parser='earley' handles all grammars
        self.parser = Lark(
            grammar,
            start='translation_unit',
            parser='earley',  # Use LALR for speed
            # transformer=GalaxyTransformer(),  # Optionally apply transformer
        )
    
    def parse(self, source_code):
        """
        Parse Galaxy source code
        
        Args:
            source_code: Galaxy script as string
            
        Returns:
            Parse tree
        """
        return self.parser.parse(source_code)
    
    def parse_file(self, filepath):
        """
        Parse a Galaxy file
        
        Args:
            filepath: Path to .galaxy file
            
        Returns:
            Parse tree
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            source_code = f.read()
        return self.parse(source_code)
    
    def pretty_print(self, tree, indent=0):
        """
        Pretty print the parse tree
        
        Args:
            tree: Parse tree
            indent: Current indentation level
        """
        if isinstance(tree, Tree):
            print('  ' * indent + tree.data)
            for child in tree.children:
                self.pretty_print(child, indent + 1)
        else:
            print('  ' * indent + repr(tree))

# ============================================================================
# EXAMPLE USAGE
# ============================================================================

def main():
    """Main function demonstrating parser usage"""
    
    # Example Galaxy code
    example_code = """
    include "TriggerLibs/NativeLib"
    
    const int c_maxPlayers = 16;
    const fixed c_gravity = 9.8;
    
    struct PlayerData {
        int id;
        string name;
        bool isActive;
    };
    
    static PlayerData gv_player;
    
    native void UnitSetHealth(unit inUnit, int value);
    
    int add(int a, int b) {
        return a + b;
    }
    
    void initialize() {
        int i;
        for (i = 0; i < c_maxPlayers; i += 1) {
            gv_player.id = i;
        }
    }
    """
    
    print("Galaxy Script Parser Demo")
    print("=" * 80)
    
    # Create parser
    parser = GalaxyParser()
    
    # Parse the code
    try:
        tree = parser.parse(example_code)
        
        print("\n✅ Parsing successful!")
        print("\nParse Tree:")
        print("-" * 80)
        parser.pretty_print(tree)
        
        # Get statistics
        print("\n" + "=" * 80)
        print("Statistics:")
        print("-" * 80)
        
        def count_nodes(tree, node_type):
            """Count nodes of a specific type"""
            count = 0
            if isinstance(tree, Tree):
                if tree.data == node_type:
                    count += 1
                for child in tree.children:
                    count += count_nodes(child, node_type)
            return count
        
        print(f"Include statements:  {count_nodes(tree, 'include_statement')}")
        print(f"Function definitions: {count_nodes(tree, 'function_definition')}")
        print(f"Native declarations:  {count_nodes(tree, 'native_declaration')}")
        print(f"Struct declarations:  {count_nodes(tree, 'struct_declaration')}")
        print(f"Declarations:        {count_nodes(tree, 'declaration')}")
        
    except Exception as e:
        print(f"\n❌ Parsing failed!")
        print(f"Error: {e}")
        return 1
    
    # If a file was provided as argument, parse it
    if len(sys.argv) > 1:
        filepath = sys.argv[1]
        print(f"\n" + "=" * 80)
        print(f"Parsing file: {filepath}")
        print("=" * 80)
        
        try:
            tree = parser.parse_file(filepath)
            print("\n✅ File parsed successfully!")
            
            # Show summary
            print("\nFile Statistics:")
            print(f"Functions: {count_nodes(tree, 'function_definition')}")
            print(f"Natives:   {count_nodes(tree, 'native_declaration')}")
            print(f"Structs:   {count_nodes(tree, 'struct_declaration')}")
            
        except FileNotFoundError:
            print(f"\n❌ File not found: {filepath}")
            return 1
        except Exception as e:
            print(f"\n❌ Parsing failed!")
            print(f"Error: {e}")
            return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())