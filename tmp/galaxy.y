/*
 * Galaxy Script Grammar (Yacc/Bison Style)
 * Based on ANSI C Yacc grammar style
 * 
 * Designed for: StarCraft II Galaxy scripting language
 * Data Source: Analysis of 990 Galaxy files (655,866 lines of code)
 * Created: 2026-02-14
 * 
 * This grammar defines the complete syntax for Galaxy Script,
 * a game-specific scripting language derived from C but with
 * significant modifications for safety and game domain specificity.
 */

/* ===================================================================
 * TOKEN DEFINITIONS
 * =================================================================== */

/* Identifiers and literals */
%token IDENTIFIER
%token INTEGER_CONSTANT FIXED_CONSTANT STRING_LITERAL
%token TRUE FALSE NULL

/* Keywords - Control Flow */
%token IF ELSE WHILE FOR RETURN BREAK CONTINUE

/* Keywords - Declarations */
%token CONST STATIC NATIVE STRUCT INCLUDE

/* Keywords - Basic Types */
%token VOID INT BOOL FIXED STRING BYTE

/* Keywords - Game Types */
%token UNIT POINT TIMER REGION TRIGGER WAVE ACTOR REVEALER
%token PLAYERGROUP UNITGROUP
%token TEXT SOUND SOUNDLINK COLOR
%token ABILCMD ORDER MARKER BANK CAMERAINFO
%token ACTORSCOPE AIFILTER UNITFILTER WAVETARGET EFFECTHISTORY

/* Operators - Arithmetic */
%token INC_OP DEC_OP         /* ++ -- */

/* Operators - Relational */
%token LE_OP GE_OP EQ_OP NE_OP   /* <= >= == != */

/* Operators - Logical */
%token AND_OP OR_OP              /* && || */

/* Operators - Assignment */
%token MUL_ASSIGN DIV_ASSIGN ADD_ASSIGN SUB_ASSIGN  /* *= /= += -= */

/* Operators - Special (Galaxy-specific) */
%token ARROW_RIGHT ARROW_LEFT    /* -> <- */
%token DIV_GT LT_DIV             /* /> </ */
%token GT_LT GT_PLUS             /* >< >+ */
%token LSHIFT                    /* << */
%token DOUBLE_NOT                /* !! */
%token DOUBLE_DIV                /* // (not comment) */
%token PLUS_DIV                  /* +/ */
%token MULT_MINUS                /* *- */
%token DOUBLE_MULT               /* ** */

/* Entry point */
%start translation_unit

%%

/* ===================================================================
 * PRIMARY EXPRESSIONS
 * =================================================================== */

primary_expression
	: IDENTIFIER
	| INTEGER_CONSTANT
	| FIXED_CONSTANT
	| STRING_LITERAL
	| TRUE
	| FALSE
	| NULL
	| '(' expression ')'
	;

/* ===================================================================
 * POSTFIX EXPRESSIONS
 * =================================================================== */

postfix_expression
	: primary_expression
	| postfix_expression '[' expression ']'
	| postfix_expression '(' ')'
	| postfix_expression '(' argument_expression_list ')'
	| postfix_expression '.' IDENTIFIER
	| postfix_expression INC_OP
	| postfix_expression DEC_OP
	;

argument_expression_list
	: assignment_expression
	| argument_expression_list ',' assignment_expression
	;

/* ===================================================================
 * UNARY EXPRESSIONS
 * =================================================================== */

unary_expression
	: postfix_expression
	| INC_OP unary_expression
	| DEC_OP unary_expression
	| unary_operator unary_expression
	;

unary_operator
	: '+'
	| '-'
	| '!'
	;

/* Note: Galaxy does NOT support:
 * - '&' (address-of)
 * - '*' (dereference) 
 * - '~' (bitwise NOT)
 * as it has no pointer support
 */

/* ===================================================================
 * MULTIPLICATIVE EXPRESSIONS
 * =================================================================== */

multiplicative_expression
	: unary_expression
	| multiplicative_expression '*' unary_expression
	| multiplicative_expression '/' unary_expression
	| multiplicative_expression DOUBLE_MULT unary_expression     /* ** power */
	| multiplicative_expression MULT_MINUS unary_expression      /* *- */
	;

/* ===================================================================
 * ADDITIVE EXPRESSIONS
 * =================================================================== */

additive_expression
	: multiplicative_expression
	| additive_expression '+' multiplicative_expression
	| additive_expression '-' multiplicative_expression
	| additive_expression PLUS_DIV multiplicative_expression     /* +/ */
	;

/* ===================================================================
 * SHIFT EXPRESSIONS (Limited in Galaxy)
 * =================================================================== */

shift_expression
	: additive_expression
	| shift_expression LSHIFT additive_expression                /* << */
	;

/* Note: Galaxy only supports << (left shift)
 * No >> (right shift) support
 */

/* ===================================================================
 * RELATIONAL EXPRESSIONS
 * =================================================================== */

relational_expression
	: shift_expression
	| relational_expression '<' shift_expression
	| relational_expression '>' shift_expression
	| relational_expression LE_OP shift_expression
	| relational_expression GE_OP shift_expression
	| relational_expression GT_LT shift_expression               /* >< */
	| relational_expression GT_PLUS shift_expression             /* >+ */
	| relational_expression DIV_GT shift_expression              /* /> */
	| relational_expression LT_DIV shift_expression              /* </ */
	;

/* ===================================================================
 * EQUALITY EXPRESSIONS
 * =================================================================== */

equality_expression
	: relational_expression
	| equality_expression EQ_OP relational_expression
	| equality_expression NE_OP relational_expression
	;

/* Note: Galaxy does NOT support bitwise AND, OR, XOR
 * No: and_expression, exclusive_or_expression, inclusive_or_expression
 */

/* ===================================================================
 * LOGICAL EXPRESSIONS
 * =================================================================== */

logical_and_expression
	: equality_expression
	| logical_and_expression AND_OP equality_expression
	;

logical_or_expression
	: logical_and_expression
	| logical_or_expression OR_OP logical_and_expression
	;

/* ===================================================================
 * ASSIGNMENT EXPRESSIONS
 * =================================================================== */

assignment_expression
	: logical_or_expression
	| unary_expression assignment_operator assignment_expression
	;

assignment_operator
	: '='
	| MUL_ASSIGN
	| DIV_ASSIGN
	| ADD_ASSIGN
	| SUB_ASSIGN
	;

/* Note: Galaxy does NOT support:
 * - Conditional operator (? :)
 * - Bitwise assignment operators (&=, |=, ^=)
 * - Shift assignment operators (<<=, >>=)
 * - Modulo assignment (%=)
 */

/* ===================================================================
 * EXPRESSIONS
 * =================================================================== */

expression
	: assignment_expression
	;

/* Note: Galaxy does NOT support comma operator
 * No: expression ',' assignment_expression
 */

constant_expression
	: logical_or_expression
	;

/* ===================================================================
 * DECLARATIONS
 * =================================================================== */

declaration
	: declaration_specifiers ';'
	| declaration_specifiers init_declarator_list ';'
	;

declaration_specifiers
	: storage_class_specifier
	| storage_class_specifier declaration_specifiers
	| type_specifier
	| type_specifier declaration_specifiers
	;

init_declarator_list
	: init_declarator
	| init_declarator_list ',' init_declarator
	;

init_declarator
	: declarator
	| declarator '=' initializer
	;

/* ===================================================================
 * STORAGE CLASS SPECIFIERS
 * =================================================================== */

storage_class_specifier
	: CONST
	| STATIC
	;

/* Note: Galaxy does NOT support:
 * - TYPEDEF
 * - EXTERN
 * - AUTO
 * - REGISTER
 */

/* ===================================================================
 * TYPE SPECIFIERS
 * =================================================================== */

type_specifier
	: primitive_type_specifier
	| game_type_specifier
	| struct_specifier
	| IDENTIFIER                    /* User-defined type (struct name) */
	;

primitive_type_specifier
	: VOID
	| INT
	| BOOL
	| FIXED
	| STRING
	| BYTE
	;

game_type_specifier
	: UNIT
	| POINT
	| TIMER
	| REGION
	| TRIGGER
	| WAVE
	| ACTOR
	| REVEALER
	| PLAYERGROUP
	| UNITGROUP
	| TEXT
	| SOUND
	| SOUNDLINK
	| COLOR
	| ABILCMD
	| ORDER
	| MARKER
	| BANK
	| CAMERAINFO
	| ACTORSCOPE
	| AIFILTER
	| UNITFILTER
	| WAVETARGET
	| EFFECTHISTORY
	;

/* Note: Galaxy does NOT support:
 * - Type modifiers (signed, unsigned, short, long)
 * - CHAR, FLOAT, DOUBLE (uses INT, FIXED instead)
 * - ENUM
 * - UNION
 * - Type qualifiers (volatile)
 */

/* ===================================================================
 * STRUCT SPECIFIER
 * =================================================================== */

struct_specifier
	: STRUCT IDENTIFIER '{' struct_declaration_list '}'
	| STRUCT '{' struct_declaration_list '}'
	| STRUCT IDENTIFIER
	;

struct_declaration_list
	: struct_declaration
	| struct_declaration_list struct_declaration
	;

struct_declaration
	: type_specifier struct_declarator_list ';'
	;

struct_declarator_list
	: struct_declarator
	| struct_declarator_list ',' struct_declarator
	;

struct_declarator
	: declarator
	;

/* Note: Galaxy does NOT support:
 * - Bit fields (: constant_expression)
 * - UNION
 * - Anonymous structs
 */

/* ===================================================================
 * DECLARATORS
 * =================================================================== */

declarator
	: direct_declarator
	;

/* Note: Galaxy does NOT support pointers
 * No: pointer direct_declarator
 */

direct_declarator
	: IDENTIFIER
	| direct_declarator '[' constant_expression ']'
	| direct_declarator '[' ']'
	| direct_declarator '[' constant_expression '+' constant_expression ']'
	;

/* Note: Galaxy arrays:
 * - Maximum 2 dimensions (no 3D+ arrays)
 * - Size must be compile-time constant
 * - Supports expressions like [MAX + 1]
 * 
 * Galaxy does NOT support:
 * - Function declarators in general declarations (only in function_definition)
 * - Pointer declarators
 */

/* ===================================================================
 * INITIALIZERS
 * =================================================================== */

initializer
	: assignment_expression
	| '{' initializer_list '}'
	| '{' initializer_list ',' '}'
	;

initializer_list
	: initializer
	| initializer_list ',' initializer
	;

/* ===================================================================
 * STATEMENTS
 * =================================================================== */

statement
	: compound_statement
	| expression_statement
	| selection_statement
	| iteration_statement
	| jump_statement
	;

/* Note: Galaxy does NOT support:
 * - Labeled statements (IDENTIFIER ':' statement)
 * - Case labels (no switch/case)
 */

compound_statement
	: '{' '}'
	| '{' statement_list '}'
	| '{' declaration_list '}'
	| '{' declaration_list statement_list '}'
	;

declaration_list
	: declaration
	| declaration_list declaration
	;

statement_list
	: statement
	| statement_list statement
	;

expression_statement
	: ';'
	| expression ';'
	;

/* ===================================================================
 * SELECTION STATEMENTS
 * =================================================================== */

selection_statement
	: IF '(' expression ')' statement
	| IF '(' expression ')' statement ELSE statement
	;

/* Note: Galaxy does NOT support:
 * - SWITCH/CASE/DEFAULT
 */

/* ===================================================================
 * ITERATION STATEMENTS
 * =================================================================== */

iteration_statement
	: WHILE '(' expression ')' statement
	| FOR '(' for_init_clause ';' for_condition_clause ';' for_iteration_clause ')' statement
	;

for_init_clause
	: /* empty */
	| expression
	| declaration_specifiers init_declarator_list
	;

for_condition_clause
	: /* empty */
	| expression
	;

for_iteration_clause
	: /* empty */
	| expression
	;

/* Note: Galaxy does NOT support:
 * - DO-WHILE loops
 */

/* ===================================================================
 * JUMP STATEMENTS
 * =================================================================== */

jump_statement
	: CONTINUE ';'
	| BREAK ';'
	| RETURN ';'
	| RETURN expression ';'
	;

/* Note: Galaxy does NOT support:
 * - GOTO
 */

/* ===================================================================
 * TRANSLATION UNIT (Top Level)
 * =================================================================== */

translation_unit
	: external_declaration
	| translation_unit external_declaration
	;

external_declaration
	: function_definition
	| declaration
	| native_declaration
	| struct_declaration
	| include_statement
	;

/* ===================================================================
 * INCLUDE STATEMENTS
 * =================================================================== */

include_statement
	: INCLUDE STRING_LITERAL
	;

/* Note: Galaxy's include is NOT a preprocessor directive
 * It's a first-class language construct
 */

/* ===================================================================
 * FUNCTION DEFINITIONS
 * =================================================================== */

function_definition
	: type_specifier IDENTIFIER '(' parameter_list ')' compound_statement
	| type_specifier IDENTIFIER '(' ')' compound_statement
	;

parameter_list
	: parameter_declaration
	| parameter_list ',' parameter_declaration
	;

parameter_declaration
	: type_specifier IDENTIFIER
	| type_specifier IDENTIFIER '[' ']'
	| type_specifier IDENTIFIER '[' constant_expression ']'
	;

/* Note: Galaxy function definitions:
 * - Simple, single style (no K&R style)
 * - No variadic functions (...)
 * - No abstract declarators in parameters
 * - No function pointers
 */

/* ===================================================================
 * NATIVE DECLARATIONS (Galaxy-specific)
 * =================================================================== */

native_declaration
	: NATIVE type_specifier IDENTIFIER '(' native_parameter_list ')' ';'
	| NATIVE type_specifier IDENTIFIER '(' ')' ';'
	;

native_parameter_list
	: native_parameter_declaration
	| native_parameter_list ',' native_parameter_declaration
	;

native_parameter_declaration
	: type_specifier IDENTIFIER
	| type_specifier IDENTIFIER '[' ']'
	;

/* Note: Native declarations may include documentation comments
 * in the form of /// comments, but these are handled by the lexer
 */

%%

/* ===================================================================
 * GRAMMAR NOTES AND CONVENTIONS
 * =================================================================== */

/*
 * OPERATOR PRECEDENCE (Lowest to Highest):
 * 
 * 1.  =, +=, -=, *=, /=           (Assignment)
 * 2.  ||                           (Logical OR)
 * 3.  &&                           (Logical AND)
 * 4.  ==, !=                       (Equality)
 * 5.  <, >, <=, >=, ><, >+, />, </ (Relational)
 * 6.  <<                           (Shift)
 * 7.  +, -, +/                     (Additive)
 * 8.  *, /, **, *-                 (Multiplicative)
 * 9.  !, +, - (unary)              (Unary)
 * 10. ++, -- (postfix)             (Postfix)
 * 11. (), [], .                    (Postfix access)
 *
 * ASSOCIATIVITY:
 * - Most operators: left-to-right
 * - Assignment operators: right-to-left
 * - Unary operators: right-to-left
 */

/*
 * KEY DIFFERENCES FROM ANSI C:
 *
 * REMOVED FEATURES:
 * - Pointers (* and & operators, -> is repurposed)
 * - Preprocessor (#define, #ifdef, etc.)
 * - Enumerations (enum)
 * - Type definitions (typedef)
 * - Unions
 * - Bitwise operators (&, |, ^, ~, except <<)
 * - Conditional operator (? :)
 * - Comma operator
 * - Sizeof operator
 * - Type casting ((type)expression)
 * - Goto and labels
 * - Switch/case/default
 * - Do-while loops
 * - Function pointers
 * - Variadic functions (...)
 * - Type qualifiers (volatile)
 * - Storage classes (extern, auto, register, typedef)
 * - Type modifiers (signed, unsigned, short, long)
 * - Bit fields in structs
 *
 * ADDED FEATURES:
 * - 30 game-specific types (unit, trigger, wave, etc.)
 * - Native function declarations
 * - Include as language construct (not preprocessor)
 * - Special operators (+/, *-, **, ><, >+, />, </, !!, //)
 * - Array size expressions ([SIZE + 1])
 *
 * SIMPLIFIED FEATURES:
 * - Single function definition style
 * - No complex declarators
 * - Implicit type conversions only (no casts)
 * - Simple struct declarations
 */

/*
 * COMMON USAGE PATTERNS:
 *
 * 1. Variable Declaration:
 *    int count = 0;
 *    bool isActive = true;
 *    unit myUnit;
 *
 * 2. Constant Declaration:
 *    const int MAX_PLAYERS = 16;
 *    const fixed GRAVITY = 9.8;
 *
 * 3. Array Declaration:
 *    int array[10];
 *    int array[MAX_SIZE + 1];
 *    unit units[libCore_gv_bALMaxPlayers];
 *
 * 4. Function Definition:
 *    int add(int a, int b) {
 *        return a + b;
 *    }
 *
 * 5. Native Declaration:
 *    native void UnitAbilityAdd(unit inUnit, string ability);
 *
 * 6. Struct Definition:
 *    struct PlayerData {
 *        int id;
 *        string name;
 *        bool isActive;
 *    };
 *
 * 7. Include Statement:
 *    include "TriggerLibs/NativeLib"
 *
 * 8. For Loop (Most common pattern):
 *    int i;
 *    for (i = 0; i < MAX; i += 1) {
 *        // loop body
 *    }
 */

/*
 * STATISTICS (Based on 990 Galaxy files):
 * - Total lines of code: 655,866
 * - Total functions: 40,246
 * - Total constants: 14,146
 * - Total native functions: 274
 * - Total structs: 266
 * - Keywords: 20
 * - Data types: 30
 * - Operators: 33
 */

/* End of Galaxy Script Grammar */
