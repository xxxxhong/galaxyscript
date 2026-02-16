%token IDENTIFIER CONSTANT STRING_LITERAL SIZEOF
%token PTR_OP INC_OP DEC_OP LEFT_OP RIGHT_OP LE_OP GE_OP EQ_OP NE_OP
%token AND_OP OR_OP MUL_ASSIGN DIV_ASSIGN MOD_ASSIGN ADD_ASSIGN
%token SUB_ASSIGN LEFT_ASSIGN RIGHT_ASSIGN AND_ASSIGN
%token XOR_ASSIGN OR_ASSIGN TYPE_NAME

%token TYPEDEF EXTERN STATIC AUTO REGISTER
%token CHAR SHORT INT LONG SIGNED UNSIGNED FLOAT DOUBLE CONST VOLATILE VOID
%token STRUCT UNION ENUM ELLIPSIS

%token CASE DEFAULT IF ELSE SWITCH WHILE DO FOR GOTO CONTINUE BREAK RETURN

%start translation_unit
%%

/* 
初级表达式
	: 标识符				|含义：指代变量名、函数名或常量名。它是一个名字，指向内存中的某个值。     |例子：x  user_age  calculate_sum  PI
	| 常量					|含义：直接写死的数值，通常包括整数、浮点数、枚举常量等。              	|例子：42 3.14159  0xFF
	| 字符串字面量			|含义：用双引号括起来的一串字符。                                     	|例子："Hello, World!" "12345"  ""
	| '(' 表达式 ')'		|含义：这是一个递归定义。它允许你把一个复杂的表达式用括号包起来，使其在逻辑上变成一个“初级表达式”。这也就是为什么在数学中括号能改变运算优先级。 |例子：(a + b)  ((10 * x) / y)
	;
*/
primary_expression	
	: IDENTIFIER
	| CONSTANT
	| STRING_LITERAL
	| '(' expression ')'
	;

/*
后缀表达式
	: 初级表达式           				 |含义：这是递归的出口。所有的后缀操作必须建立在标识符、常量或括号表达式之上。  |例子：x, 42, (a + b)
	| 后缀表达式 '[' 表达式 ']'			 |含义：数组访问。数组下标     											   |例子：arr[5]  arr[0], data[i + 1]
	| 后缀表达式 '(' ')'				 |含义：调用一个不带参数的函数。函数调用，参数为空。							 |例子：func()  getchar(), init()
	| 后缀表达式 '(' 参数表达式列表 ')'	  | 含义：函数调用，带参数。											   	|例子：func(x, y + 2)  printf("Hello"), add(a, b)
	| 后缀表达式 '.' 标识符				  |含义：结构体成员访问。													|例子：point.x
	| 后缀表达式 PTR_OP 标识符			  |含义：结构体指针成员访问。												|例子：ptr->x
	| 后缀表达式 INC_OP					 |含义：后置递增。														|例子：i++
	| 后缀表达式 DEC_OP					 |含义：后置递减。														|例子：i--
	;
*/
postfix_expression
	: primary_expression
	| postfix_expression '[' expression ']'
	| postfix_expression '(' ')'
	| postfix_expression '(' argument_expression_list ')'
	| postfix_expression '.' IDENTIFIER
	| postfix_expression PTR_OP IDENTIFIER
	| postfix_expression INC_OP
	| postfix_expression DEC_OP
	;

/*
参数表达式列表:
	: 赋值表达式				|含义：起始项。列表可以只包含一个表达式。这是递归的出口。所有的参数表达式必须建立在赋值表达式之上。  |例子：func(42) 这里的 42 就是一个表达式。func(a = 10) —— 这里的 a = 10 也是一个有效的参数。
	| 参数表达式列表 ',' 赋值表达式	|含义：递归扩展项。允许通过逗号 , 不断追加更多的表达式。											   |例子：func(a, b)  func(1, 2, 3 + x, "hello")
	;
*/
argument_expression_list
	: assignment_expression
	| argument_expression_list ',' assignment_expression
	;

/*
一元表达式
	: 后缀表达式						|含义：基础项。所有的后缀表达式（如变量名、数组访问、函数调用）都可以直接作为一个一元表达式。这是递归的出口。			|例子：x, arr[0], func()
	| INC_OP 一元表达式					|含义：前置自增。在变量使用之前先加 1（通常对应 ++i）。										|例子：++count, ++++i（虽然连用在 C 语言中不合法，但语法结构支持这种嵌套）。
	| DEC_OP 一元表达式					|含义：前置自减。递在变量使用之前先减 1（通常对应 --i）。									|例子：--i  --x --index
	| 一元运算符 强制类型转换表达式		|含义：一元运算符操作。包括取地址 & (取地址)、* (解引用)、+ (正号)、- (负号)、~ (按位取反) 和 ! (逻辑非)。  |例子：* &x (取 x 的地址)  *ptr (获取指针指向的值)  -5 (负 5)     !is_valid (逻辑非)
	| SIZEOF 一元表达式					|含义：sizeof 操作符返回一个对象或类型所占的字节数。它可以用来计算表达式大小。					|例子：sizeof x, sizeof (a + b)。
	| SIZEOF '(' 类型名称 ')'			|含义：sizeof 操作符也可以直接作用于一个类型名称，用于计算类型大小。												|例子：sizeof(int), sizeof(double)。
	;
*/
unary_expression
	: postfix_expression
	| INC_OP unary_expression
	| DEC_OP unary_expression
	| unary_operator cast_expression
	| SIZEOF unary_expression
	| SIZEOF '(' type_name ')'
	;


/*
一元运算符
	: '&'  (取地址)
	| '*'  (解引用)
	| '+'  (正号)
	| '-'  (负号)
	| '~'  (按位取反)
	| '!'  (逻辑非)
	;
	由于这些都是 一元运算符，它们的结合性是 从右向左 (Right-to-Left) 的。这意味着如果你写出：
		*&x
		首先执行右边的 &x (取地址)。
		然后对结果执行左边的 * (解引用)。
		最终结果依然是 x 本身。
*/
unary_operator
	: '&'
	| '*'
	| '+'
	| '-'
	| '~'
	| '!'
	;

/*
强制类型转换表达式
	: 一元表达式						|含义：基础项。所有的“一元表达式”（比如变量 x、指针 *ptr、负数 -5 等）本身都可以直接作为一个类型转换表达式。这是递归的出口，意味着如果不进行转换，它就是一个普通的值。			|例子：count, -10, !flag
	| '(' 类型名称 ')' 强制类型转换表达式	|含义：转换项。这是递归定义。它允许你在一个表达式前面加上括号包围的“类型名”，将其转换成该类型。 |例子：(float)i ：将整数 i 转换为浮点数。  (int*)ptr ：将一个通用指针转换为整型指针。  (double)(int)x ：先将 x 转为 int，再转为 double（连续转换）。
	;

	为什么右边是 cast_expression 而不是 unary_expression？这是一个非常精妙的递归设计。请看下面这个例子：
		(double) -x
		-x 是一个 unary_expression。
		根据规则 1，它也是一个 cast_expression。
		根据规则 2，(double) 作用于这个 cast_expression，整体依然是一个 cast_expression。
		如果规则 2 的右边写的是 unary_expression，那么你就无法写出类似 (int)(float)x 这样连续转换的代码了。
*/
cast_expression
	: unary_expression
	| '(' type_name ')' cast_expression
	;

/*
乘法类表达式
	: 强制类型转换表达式				   |含义：基础项。这是一个递归出口。一个单独的变量、常量或经过强制转换的值（如 (int)2.5）本身就可以看作是一个乘法表达式。			|例子：x, 10, (float)i
	| 乘法类表达式 '*' 强制类型转换表达式	|含义：乘法运算。将两个值相乘。																								|例子：a * b, 5 * 10
	| 乘法类表达式 '/' 强制类型转换表达式	|含义：除法运算。将左侧表达式除以右侧表达式。在 C 语言中，如果两边都是整数，结果会向下取整（丢弃小数部分）。				|例子：total / count, 10 / 3 (结果为 3)。
	| 乘法类表达式 '%' 强制类型转换表达式	|含义：取模运算。计算除法后的余数。通常只用于整数。											|例子：10 % 3 (结果为 1)。
	;	
	核心机制：左结合性与优先级
	这里的定义方式暗示了两个编译器处理逻辑：
	A. 为什么是左递归？（左结合性）
		定义的结构是 multiplicative_expression op cast_expression。这意味着当你写 a * b / c 时，编译器会这样分组：
		((a * b) / c)
		它会先处理最左边的运算。这保证了在执行 10 / 2 * 5 时，结果是 25 而不是 1。
	B. 优先级层级
		在整个语法树中，multiplicative_expression 位于 additive_expression（加法表达式）之上。
		高优先级： cast_expression（如 (int)3.14）
		中优先级： *, /, %
		低优先级： +, -
		这就是为什么在 a + b * c 中，编译器会优先识别出 b * c 是一个完整的乘法表达式。
*/
multiplicative_expression
	: cast_expression
	| multiplicative_expression '*' cast_expression
	| multiplicative_expression '/' cast_expression
	| multiplicative_expression '%' cast_expression
	;

/*
加法类表达式
	: 乘法类表达式						|含义：基础项。递归的出口。这意味着如果一个表达式中没有加减号，它就被视为一个乘法表达式（或者是更基础的单元）。			|例子：x, 10 * 2, (int)5.5
	| 加法类表达式 '+' 乘法类表达式		|含义：加法运算。将左边的结果与右边的乘法表达式相加。																|例子：a + b, x * y + z
	| 加法类表达式 '-' 乘法类表达式		|含义：减法运算。从左边的结果中减去右边的乘法表达式。										   						|例子：total - 10, a - b - c
	;
	核心机制：结合性与优先级
	A. 左结合性（Left Associativity）
		由于定义是 additive_expression op multiplicative_expression，当遇到 10 - 5 + 2 时，编译器的处理顺序是：
		先计算 10 - 5 = 5。
		再计算 5 + 2 = 7。
		注意： 如果是右结合，结果就会变成 10 - (5 + 2) = 3，这显然不符合数学常规。
	B. 优先级的体现
		观察这个层级结构：
		primary_expression (最高：变量、常量)
		unary_expression (高：-x, ++i)
		multiplicative_expression (中：*, /)
		additive_expression (低：+, -)
		当编译器处理 a + b * c 时：
		它会发现 b * c 匹配 multiplicative_expression。
		然后整个 b * c 的结果作为右操作数，与 a 匹配 additive_expression。
		这就保证了“先乘后加”。
*/
additive_expression
	: multiplicative_expression
	| additive_expression '+' multiplicative_expression
	| additive_expression '-' multiplicative_expression
	;

/*
移位表达式
	: 加法类表达式						|含义：基础项。递归出口。如果表达式中没有移位符号，它就被视为一个加法类表达式。			|例子：x, a + b, 100
	| 移位表达式 LEFT_OP 加法类表达式	|含义：左移运算。将左侧数值的二进制位向左移动指定的位数。在 C 语言中，LEFT_OP 通常对应 <<。			 |例子：x << 2
	| 移位表达式 RIGHT_OP 加法类表达式	|含义：右移运算。将左侧数值的二进制位向右移动。在 C 语言中，RIGHT_OP 通常对应 >>。					|例子：16 >> 3
	;
	为什么它在 additive_expression 之后？	这是初学者最容易写错的地方。
	移位运算的优先级低于加减法，所以：
		代码： x << 1 + 2
		编译器的实际处理： x << (1 + 2)  即 x << 3
		如果你原本的意图是 (x << 1) + 2，你必须加括号。这种语法定义保证了编译器会先去寻找 additive_expression（加法），把加法处理完后，再把它当作移位运算的操作数。
	结合性分析
		由于定义是 shift_expression op additive_expression，它同样是 左结合 的。
		例子： a << b >> c
		处理顺序： (a << b) >> c
*/
shift_expression
	: additive_expression
	| shift_expression LEFT_OP additive_expression
	| shift_expression RIGHT_OP additive_expression
	;

/*
关系表达式
	: 移位表达式					|含义：基础项。递归出口。如果没有比较符号，它就是一个移位表达式（或更高级别的算术表达式）。			|例子：x, a + b, n << 2
	| 关系表达式 '<' 移位表达式		|含义：小于运算。判断左边是否小于右边。					|例子：count < 10
	| 关系表达式 '>' 移位表达式		|含义：大于运算。判断左边是否大于右边。					|例子：speed > max_speed
	| 关系表达式 LE_OP 移位表达式	|含义：小于等于。LE_OP 通常代表 <= (Less than or Equal)。		|例子：i <= 100
	| 关系表达式 GE_OP 移位表达式	|含义：大于等于。GE_OP 通常代表 >= (Greater than or Equal)。	|例子：age >= 18
	;
	为什么这样设计？
	A. 优先级逻辑
		关系运算的优先级低于算术运算。这符合人类直觉：我们通常是先算出一个结果，再去比大小。
		代码： a + b < c * d
		编译器理解： (a + b) < (c * d)
		结果： 比较两个算术结果，返回真（1）或假（0）。
	B. 左结合性及其“陷阱”
		由于是左递归定义，a < b < c 在语法上是合法的，但它的含义可能让你大吃一惊：
		先计算 a < b。结果要么是 1（真），要么是 0（假）。
		然后用这个 1 或 0 去和 c 比较。
		结论： 在 C 语言中，1 < 2 < 3 的结果是真（1 < 2 得到 1，1 < 3 得到真），而 3 < 2 < 1 的结果也是真（3 < 2 得到 0，0 < 1 得到真）。这与数学上的连等式完全不同！
*/
relational_expression
	: shift_expression
	| relational_expression '<' shift_expression
	| relational_expression '>' shift_expression
	| relational_expression LE_OP shift_expression
	| relational_expression GE_OP shift_expression
	;

/*
相等类表达式
	: 关系表达式					|含义：基础项。递归出口。递归出口。如果表达式中没有 == 或 !=，它就被视为一个关系表达式。			|例子：a < b, x >= 10, count
	| 相等类表达式 EQ_OP 关系表达式	|含义：EQ_OP 代表 == (Equal operator)。用于判断两侧是否相等。					|例子：status == 200, (a > b) == (c > d)
	| 相等类表达式 NE_OP 关系表达式	|含义：NE_OP 代表 != (Not Equal operator)。用于判断两侧是否不相等。				|例子：ptr != NULL, score != 0
	;

	为什么要区分“大小比较”和“相等比较”？为什么它在 relational_expression 之后？这是优先级设计的一部分。	相等比较的优先级低于关系比较，这符合人类的思维习惯：我们通常是先算出一个结果，再去判断它是否等于另一个结果。
	在 C 语言语法中，把它们分开是为了确立优先级差异：
	relational ( <, >, <=, >= ) > equality ( ==, != )

	优先级示例：
		代码： a < b == c < d
		解析顺序： (a < b) == (c < d)
		编译器会先判断 a < b 的真假，再判断 c < d 的真假，最后比较这两个结果（0 或 1）是否相同。如果它们在同一级，这种逻辑就会变得混乱。
	结合性与常见陷阱
	1. 左结合性
		a == b == c 的执行顺序是 (a == b) == c。
		如果 a, b, c 都是 5：
		5 == 5 得到 1 (真)。
		1 == 5 得到 0 (假)。
		结论： 即使三个数相等，这个表达式的结果也是“假”。这再次证明了 C 语言不支持数学上的连等写法。
	2. 经典错误：= vs ==
		在这个语法阶段，我们处理的是 ==。而单号的 = 属于后面会讲到的 assignment_expression（赋值表达式），它的优先级极低。
		if (x = 5)：这是把 5 赋给 x，然后判断 5 是否为真（永远为真）。
		if (x == 5)：这才是判断 x 是否等于 5。
*/
equality_expression
	: relational_expression
	| equality_expression EQ_OP relational_expression
	| equality_expression NE_OP relational_expression
	;

/*
按位与表达式
	: 相等类表达式	| 含义：基础项。递归出口。如果没有 & 符号，它就是一个相等判断表达式（或者更高级别的表达式）。			|例子：a == b, x != 0, 100
	| 按位与表达式 '&' 相等类表达式	| 含义：按位与运算。对两个操作数的二进制位进行逐位“与”运算（只有两个对应位都是 1，结果位才为 1）。	|例子：flags & 0x01
	;
	优先级陷阱：一个非常经典的 Bug 来源在 C 语言语法中，& 的优先级低于 ==。
	这在逻辑上其实有点反直觉，经常导致开发者写出错误的逻辑。
	代码场景： 你想判断变量 status 的最低位是不是 1。	
	错误写法： if (status & 1 == 1) 
	编译器的实际处理： status & (1 == 1) $\rightarrow$ status & 1	
	虽然在这个特定例子中结果可能歪打正着，
	但如果你写 if (status & 3 == 3)，	编译器会先算 3 == 3 得到 1，最后变成 status & 1，这显然不是你想要的。
	正确的做法必须加括号： if ((status & 3) == 3)
	
	结合性与用途
	1. 左结合性
		a & b & c 处理顺序为 (a & b) & c。
	2. 常见用途掩码检查 (Masking)： 
		检查某个特定的位是否被设置（如上面的例子）。
		清零特定位： x & 0xFE 可以把最低位强行变为 0。
	
*/
and_expression
	: equality_expression
	| and_expression '&' equality_expression
	;

/*
按位异或表达式
	: 按位与表达式	| 含义：基础项。递归出口。如果表达式中没有 ^ 符号，它就被视为一个按位与表达式（或者更高级别的表达式）。			|例子：a & b, x == 1, 42
	| 按位异或表达式 '^' 按位与表达式 | 含义：按位异或运算。对两个操作数的二进制位进行逐位“异或”运算。	|例子：a ^ b
	;

	在 C 语言的位运算“三兄弟”中，优先级顺序如下：
	& (AND)  >  ^ (XOR)  >  | (OR)

	这意味着如果你写：
	代码： a ^ b & c
	编译器理解： a ^ (b & c)
	编译器会先处理按位与，再处理异或。
*/
exclusive_or_expression
	: and_expression
	| exclusive_or_expression '^' and_expression
	;

/*
按位或表达式
	: 按位异或表达式	| 含义：基础项。递归出口。如果表达式中没有 | 符号，它就被视为一个按位异或表达式（或者更高级别的表达式）。			|例子：a ^ b, x & y, status == 0
	| 按位或表达式 '|' 按位异或表达式 | 含义：按位或运算。对两个操作数的二进制位进行逐位“或”运算。	|例子：flags | 0x02 a | b
	;
*/
inclusive_or_expression
	: exclusive_or_expression
	| inclusive_or_expression '|' exclusive_or_expression
	;

/*
逻辑与表达式
	: 按位或表达式					| 含义：基础项。递归出口。如果没有 && 符号，它就是一个按位或表达式（或更高级别的表达式）。			|例子：a | b, x == 5, 1
	| 逻辑与表达式 AND_OP 按位或表达式 | 含义：逻辑与运算。判断左右两个表达式是否同时为真（非 0 即为真）。	|例子：age > 18 && age < 60  只有当 age > 18 为真 且 age < 60 为真时，整个结果才为 1（真）。
	;
	运算符	符号	语义	优先级	特性
	Logical AND	&&	逻辑与	低于 |	短路求值
*/
logical_and_expression
	: inclusive_or_expression
	| logical_and_expression AND_OP inclusive_or_expression
	;

/*
逻辑或表达式
	: 逻辑与表达式					| 含义：基础项。递归出口。递归出口。如果没有 || 符号，它就是一个逻辑与表达式（或更高级别的表达式）。			|例子：a && b, status == 0, x > 10
	| 逻辑或表达式 OR_OP 逻辑与表达式 | 含义：逻辑或运算。判断左右两个表达式是否至少有一个为真。	|例子：is_admin || has_permission
	;
	逻辑运算符的优先级顺序是：
	! (一元非) > && (逻辑与) > || (逻辑或)
*/
logical_or_expression
	: logical_and_expression
	| logical_or_expression OR_OP logical_and_expression
	;

/*
条件表达式
	: 逻辑或表达式						| 含义：基础项。递归出口。如果表达式中没有 ?，它就是一个逻辑或表达式（或更高级别的算术/逻辑表达式）。			|例子：a || b, x + y, 10
	| 逻辑或表达式 '?' 表达式 ':' 条件表达式 | 含义：三元运算。1.  首先计算 ? 左边的 logical_or_expression。2.  如果为真（非 0），则计算并返回中间 expression 的值。3.  如果为假（0），则计算并返回右边 conditional_expression 的值。	|例子：max = (a > b) ? a : b;
	;
	这里的定义藏着两个关键设计：
	A. 结合性：右结合（Right Associativity）
		注意右侧的项是 conditional_expression（它自己），而左侧是 logical_or_expression。这意味着多个三元运算符连用时，是从右往左结合的。
		代码： a ? b : c ? d : e
		编译器理解： a ? b : (c ? d : e)
		这非常符合逻辑：如果 a 是假，那么我们再去判断 c 的情况。
	B. 中间和右侧的区别
		中间： 用的是 expression。这意味着在 ? 和 : 之间，你可以写任何合法的表达式，甚至是带逗号的列表。
		右侧： 用的是 conditional_expression。这保证了优先级层级的严格控制。
	核心特性：条件执行（Lazy Evaluation）
		三元运算符不仅是一个计算公式，它还有“选择性执行”的特性。
		在 condition ? func_A() : func_B() 中：
		如果条件为真，只有 func_A() 会被调用。
		func_B() 会被完全跳过，其副作用（比如修改全局变量）不会发生。
*/
conditional_expression
	: logical_or_expression
	| logical_or_expression '?' expression ':' conditional_expression
	;

/*
赋值表达式
	: 条件表达式						|含义：基础项。递归出口。如果表达式中没有赋值符号，它就是一个条件表达式（或更高级别的算术/逻辑表达式）。			|例子：a > b ? a : b, x + 5
	| 一元表达式 赋值运算符 赋值表达式	|含义：赋值操作。左侧必须是 unary_expression： 赋值的左边必须是一个可以被写入的“容器”（左值，L-value）。例如变量 x、数组元素 arr[i] 或指针解引用 *ptr。	右侧又是 assignment_expression： 这意味着赋值运算是**右结合（Right Associativity）**的，支持连续赋值。 |例子：x = 10     x += 5 (相当于 x = x + 5)    a = b = c = 0 (连续赋值)
	;
	左边必须是 unary_expression？你可能会问，为什么不写成 expression = expression？ 因为赋值需要一个确定的内存地址。
*/
assignment_expression
	: conditional_expression
	| unary_expression assignment_operator assignment_expression
	;

/*
赋值运算符
	: '='	| 含义：= (基本赋值)  |例子： x = 5
	| 算术复合赋值。这类操作符先进行算术运算，再将结果存回左侧。
		MUL_ASSIGN (*=): x *= 2 等价于 x = x * 2
		DIV_ASSIGN (/=): x /= 2 等价于 x = x / 2
		MOD_ASSIGN (%=): x %= 2 等价于 x = x % 2
		ADD_ASSIGN (+=): x += 2 等价于 x = x + 2
		SUB_ASSIGN (-=): x -= 2 等价于 x = x - 2
	| 位运算复合赋值 这类操作符通常用于底层开发或标志位处理。
		LEFT_ASSIGN (<<=): 左移并赋值。flags <<= 1
		RIGHT_ASSIGN (>>=): 右移并赋值。flags >>= 1
		AND_ASSIGN (&=): 按位与并赋值。常用作“清零某些位”：mask &= 0xFE
		XOR_ASSIGN (^=): 按位异或并赋值。常用作“翻转某些位”：status ^= 1
		OR_ASSIGN (|=): 按位或并赋值。常用作“开启某些位”：status |= 0x80
	;
	表达式的终点：expression  所有的赋值表达式，最终都会汇聚到最后一个生成式：expression。
*/
assignment_operator
	: '='
	| MUL_ASSIGN
	| DIV_ASSIGN
	| MOD_ASSIGN
	| ADD_ASSIGN
	| SUB_ASSIGN
	| LEFT_ASSIGN
	| RIGHT_ASSIGN
	| AND_ASSIGN
	| XOR_ASSIGN
	| OR_ASSIGN
	;

/*
表达式
	: 赋值表达式 | 含义： 基础项。递归出口。绝大多数情况下，我们写的一个算式或一个赋值语句就是一个完整的表达式。 |例子：x = 5 或 a + b
	| 表达式 ',' 赋值表达式  | 含义：逗号表达式。这是一个左递归定义。它允许用逗号连接任意数量的赋值表达式。 |例子：x = 1, y = 2, z = x + y
	;
	逗号运算符的优先级是全 C 语言最低的，甚至比赋值运算符还要低。
		for (i = 0, j = 10; i < j; i++, j--)
		这里的 i = 0, j = 10 就是一个 expression。
		这里的 i++, j-- 也是一个 expression。
*/
expression
	: assignment_expression
	| expression ',' assignment_expression
	;


/*
常量表达式
	: 条件表达式 | 含义：基础项。递归出口。常量表达式在形式上可以是一个完整的三元运算、逻辑运算或算术运算，但它的核心要求是：结果必须在编译时就能确定。常量必须是“只读”的计算结果。 |例子：42, sizeof(int), 3 + 5, (1 << 4)
	;
*/
constant_expression
	: conditional_expression
	;

/*
声明
	: 声明说明符 ';' | 含义：这种形式只包含“说明符”，没有具体的变量名。它通常用于定义结构体、联合体或枚举类型，或者仅仅是声明某种类型的存在。 |例子： struct Point { int x; int y; }; —— 定义了一个结构体类型。enum Color { RED, GREEN }; —— 定义了一个枚举类型。int; —— 语法上合法但没有意义（编译器通常会报警告，因为它没创建任何变量）。
	| 声明说明符 初始化声明符列表 ';' | 含义：这是我们最常用的方式：指定类型（specifiers），然后列出一个或多个变量名及其初始值（init_declarator_list）。| 例子：int a; —— int 是说明符，a 是声明列表。static float x = 1.0, y = 2.0; —— static float 是说明符，后面跟着两个带初始化的变量。
*/
declaration
	: declaration_specifiers ';'
	| declaration_specifiers init_declarator_list ';'
	;

/*
声明说明符
	: 存储类说明符 | 含义：决定变量存在哪（内存、寄存器）以及它的生命周期（生命起点和终点）。 | 例子：typedef, extern, static, auto, register。
	| 存储类说明符 声明说明符 | 含义：“存储类说明符”后面可以再接其他的声明说明符。 | 例子：static (storage) 后面接 int (属于 declaration_specifiers)。组合成：static int。
	| 类型说明符  |含义：声明可以只由一个“类型说明符”组成。	|例子： int, char, float, struct Node。
	| 类型说明符 声明说明符 |含义：“类型说明符”后面可以再接其他的声明说明符。 |例子：unsigned (type) 后面接 int (属于 declaration_specifiers)。组合成：unsigned int。
	| 类型限定符  |含义：声明可以只由一个“类型限定符”组成。 |例子： const, volatile。
	| 类型限定符 声明说明符 | 含义：“类型限定符”后面可以再接其他的声明说明符。 |例子：const (qualifier) 后面接 static int (属于 declaration_specifiers)。组合成：const static int。
	;
*/
declaration_specifiers
	: storage_class_specifier
	| storage_class_specifier declaration_specifiers
	| type_specifier
	| type_specifier declaration_specifiers
	| type_qualifier
	| type_qualifier declaration_specifiers
	;

/*
初始化声明符列表
	: 初始化声明符	| 含义：起始项。列表可以只包含一个变量定义。这是递归的出口。 | 例子：int a = 10; 中的 a = 10。
	| 初始化声明符列表 ',' 初始化声明符 |含义：递归扩展项。允许你在已经存在的变量列表后面，通过逗号 , 增加更多的变量。 | 例子：int a, b;     int a = 1, b, *p = &a;
	;
*/
init_declarator_list
	: init_declarator
	| init_declarator_list ',' init_declarator
	;

/*
初始化声明符
	: 声明符						| 含义：基础项。递归出口。只定义变量的名号、类型形状（指针/数组），但不给它指定初始值。此时变量的值通常取决于它的存储位置（全局变量默认为 0，局部变量为随机值）。|例子：int a;（a 是 declarator）    int *p;（*p 是 declarator）     int arr[10];（arr[10] 是 declarator）
	| 声明符 '=' 初始化器			| 含义：带初始化的声明。定义变量的同时，使用等号 = 将一个初始值赋给它。 |例子：int a = 10;（a 是 declarator，10 是 initializer）      char *str = "Hello";（*str 是 declarator，"Hello" 是 initializer）      int vals[2] = {1, 2};（vals[2] 是 declarator，{1, 2} 是 initializer）
	;
	不要简单地把它等同于“变量名”。在 C 语言中，声明符决定了变量的**“形状”**：
		它是普通的标识符吗？（如 x）
		它是指针吗？（如 *ptr）
		它是数组吗？（如 buffer[256]）
		它是函数吗？（如 func(int a)）
*/
init_declarator
	: declarator
	| declarator '=' initializer
	;

/*
存储类说明符
	: TYPEDEF	| 含义：typedef 说明符。用于为现有的类型创建一个新的名字（别名）。| 例子：typedef int Age;  此后，Age 就可以像 int 一样用来定义变量：Age my_age = 25;。
	| EXTERN	| 含义：extern 说明符。声明变量或函数是在其他地方（通常是另一个文件）定义的。它不会分配新内存，只是告诉编译器“去别处找这个名字”。 | 例子：extern int global_score; 这通常放在头文件中，以便多个 .c 文件共享同一个变量。
	| STATIC	| 含义：static 说明符。 在函数外： 限制变量只能在当前文件内访问（内部链接）。在函数内： 使变量在函数结束后不销毁，下次进入函数时保留原值（静态局部变量）。| 例子：例如： static int counter = 0; 定义了一个静态局部变量 counter，它在每次函数调用之间保持其值。
	| AUTO		| 含义：auto 说明符。自动变量。C 语言默认的存储类。函数内的局部变量默认就是 auto。 | 例子：auto int x = 10; 在现代 C 编程中，这个关键字几乎没人写，因为不写也是默认 auto。
	| REGISTER	| 含义：register 说明符。寄存器变量。建议编译器将变量存储在 CPU 的寄存器中，而不是内存（RAM）里，以提高访问速度。 | 例子：register int i; 限制： 你不能对 register 变量使用取地址符 &，因为寄存器没有内存地址。现代编译器通常会自动优化，这个关键字现在多用于嵌入式底层开发。
	;
	语法上的“唯一性”规则
		虽然之前的 declaration_specifiers 是递归定义的，但在语义上有一个严格限制：在同一个声明中，通常只能出现一个存储类说明符。
		错误示例： static extern int x; (编译器会报错，因为一个变量不能既是本地静态的又是外部声明的)
		正确示例： static const int x = 10; (这里只有一个 static 存储类，const 是类型限定符，int 是类型说明符)
*/
storage_class_specifier
	: TYPEDEF
	| EXTERN
	| STATIC
	| AUTO
	| REGISTER
	;

/*
类型说明符
	基础内置类型
	: VOID	| 含义：代表“无类型”。常用于函数返回类型（表示不返回值）或 void * 指针（表示通用指针）。
	| CHAR	| 含义：CHAR, SHORT, INT, LONG: 整数家族。按存储空间从小到大排列。
	| SHORT
	| INT
	| LONG
	| FLOAT	|含义：FLOAT, DOUBLE: 浮点数家族。用于表示带有小数点的实数。
	| DOUBLE
	符号限定符
	| SIGNED	|含义：有符号数（默认）。最高位作为符号位，可以表示负数。
	| UNSIGNED	|含义：无符号数。所有位都用来表示数值，只能表示非负数（0 和正数）。
	| struct_or_union_specifier 自定义复合类型 	|含义：struct_or_union_specifier: 结构体（struct）或联合体（union）。|例子：struct { int x; int y; } point;
	| enum_specifier  			枚举类型。		|含义：用于定义一组有名字的整型常量。			| 例子：enum Color { RED, BLUE };
	| TYPE_NAME	 				类型别名  		|含义：这是指通过 typedef 定义出来的名字。		| 例子：typedef int int32;，那么这里的 int32 就是一个 TYPE_NAME。
	;
*/
type_specifier
	: VOID
	| CHAR
	| SHORT
	| INT
	| LONG
	| FLOAT
	| DOUBLE
	| SIGNED
	| UNSIGNED
	| struct_or_union_specifier
	| enum_specifier
	| TYPE_NAME
	;

/*
结构体或联合体说明符
	:结构体或联合体 标识符 '{' 结构体声明列表 '}'	| 含义：定义一个新的结构体或联合体类型。标识符是这个类型的名字，结构体声明列表定义了这个类型包含哪些成员。 |例子： struct Point { int x; int y; }; 这里的 Point 是标识符，{ int x; int y; } 是结构体声明列表。
	|结构体或联合体 '{' 结构体声明列表 '}'			| 含义：匿名结构体或联合体定义。没有标识符，这种类型只能通过包含它的变量来使用。 |例子： struct { int x; int y; } point; 这里没有给结构体类型命名，它只能通过变量 point 来使用。
	|结构体或联合体 标识符						| 含义：前向声明（Forward Declaration）。仅声明一个结构体或联合体类型的名字，但不定义它的内容。这通常用于处理递归数据结构或在多个文件之间共享类型定义。 |例子： struct Node; 这只是告诉编译器存在一个名为 Node 的结构体类型，但它的成员还没有定义。
	;
*/

struct_or_union_specifier
	: struct_or_union IDENTIFIER '{' struct_declaration_list '}'
	| struct_or_union '{' struct_declaration_list '}'
	| struct_or_union IDENTIFIER
	;


/*
结构体或联合体
	: STRUCT	| 含义：结构体（struct）。定义一个包含多个成员的复合数据类型，每个成员占用独立的内存空间。成员按声明顺序依次存储（考虑内存对齐）。 | 例子：struct Person { char name[50]; int age; float height; };  所有成员都有独立的存储空间，可以同时访问。
	| UNION		| 含义：联合体（union）。定义一个可以存储不同类型数据的复合类型，但所有成员共享同一块内存空间。同一时间只能使用其中一个成员。联合体的大小等于最大成员的大小。 | 例子：union Value { int i; float f; char c; };  三个成员共享内存，修改一个会影响其他成员的值。常用于节省内存或实现类型转换。
	;
	
	使用场景对比：
	struct 使用场景：
	- 需要同时存储多个不同类型的数据
	- 表示具有多个属性的实体（如：学生、坐标点）
	- 数据成员之间相互独立
	
	union 使用场景：
	- 同一内存空间需要存储不同类型的数据，但不同时使用
	- 节省内存空间（嵌入式系统）
	- 实现类型转换或查看数据的不同表示方式
	- 实现变体类型（variant type）
	
	示例对比：
	struct Example {
		int i;     // 4 字节
		float f;   // 4 字节
		char c;    // 1 字节
	};  // 总大小约 12 字节（考虑对齐）
	
	union Example {
		int i;     // 4 字节
		float f;   // 4 字节
		char c;    // 1 字节
	};  // 总大小 4 字节（最大成员的大小）
*/
struct_or_union
	: STRUCT
	| UNION
	;


/*
结构体声明列表
	: 结构体声明								| 含义：基础项。递归出口。列表至少包含一个成员声明。 | 例子：struct Point { int x; };  只有一个成员 x。
	| 结构体声明列表 结构体声明					| 含义：递归扩展项。允许在现有成员列表后继续添加新成员。通过这种左递归定义，可以定义任意数量的成员。 | 例子：struct Point { int x; int y; };  有两个成员 x 和 y。  struct Person { char name[50]; int age; float height; };  有三个成员。
	;
	
	注意事项：
	1. 每个结构体声明必须以分号结尾
	2. 成员按声明顺序在内存中排列（考虑对齐规则）
	3. 结构体内可以包含其他结构体或联合体
	4. 结构体内可以包含位域（bit-field）成员
*/
struct_declaration_list
	: struct_declaration
	| struct_declaration_list struct_declaration
	;


/*
结构体声明
	: 说明符限定符列表 结构体声明符列表 ';'	| 含义：定义结构体或联合体的一个或多个成员。说明符限定符列表指定成员的类型（和可选的限定符如 const），结构体声明符列表指定成员的名字（可以包含多个成员，用逗号分隔）。必须以分号结尾。 | 例子：int x, y;  定义两个 int 类型的成员 x 和 y。  const float radius;  定义一个只读的 float 成员。  unsigned int flags : 8;  定义一个 8 位的位域成员。
	;
	
	说明符限定符列表
	（specifier_qualifier_list）：
	- 只能包含类型说明符（type_specifier）和类型限定符（type_qualifier）
	- 不能包含存储类说明符（storage_class_specifier），因为结构体成员不需要 static、extern 等
	- 可以是：int, const int, unsigned long, volatile char, struct Node 等
	
	结构体声明符列表（struct_declarator_list）：
	- 可以是普通成员：int x;
	- 可以是位域：unsigned int flag : 1;
	- 可以声明多个成员：int x, y, z;
	
	示例：
	struct Example {		int a;                      // 普通成员		const float b;              // 带 const 限定符的成员		unsigned int flags : 8;     // 位域成员		int x, y, z;                // 一次声明多个成员	struct Point {			int px, py;		} point;                    // 嵌套结构体	};
*/
struct_declaration
	: specifier_qualifier_list struct_declarator_list ';'
	;


/*
说明符限定符列表
	: 类型说明符 说明符限定符列表		| 含义：类型说明符后面可以继续跟其他说明符或限定符。这是递归定义，允许组合多个类型说明符。 | 例子：unsigned long  先是 unsigned，然后是 long。  struct Node *  先是 struct Node，然后可能跟指针声明符。
	| 类型说明符						| 含义：基础项。递归出口之一。列表可以只包含一个类型说明符。 | 例子：int, char, float, struct Point, enum Color
	| 类型限定符 说明符限定符列表		| 含义：类型限定符后面可以继续跟其他说明符或限定符。 | 例子：const int  先是 const，然后是 int。  volatile unsigned  先是 volatile，然后是 unsigned。
	| 类型限定符						| 含义：基础项。递归出口之一。列表可以只包含一个类型限定符。 | 例子：const, volatile
	;
	
	与 declaration_specifiers 的区别：
	- declaration_specifiers 可以包含存储类说明符（typedef, extern, static, auto, register）
	- specifier_qualifier_list 只能包含类型说明符和类型限定符，用于结构体成员、类型转换等不需要存储类的场景
	
	常见组合：
	- int                           // 单个类型说明符
	- const int                     // 限定符 + 类型说明符
	- unsigned long                 // 多个类型说明符
	- volatile unsigned int         // 限定符 + 多个类型说明符
	- const volatile char           // 多个限定符 + 类型说明符
	- struct Point                  // 结构体类型说明符
	
	应用场景：
	1. 结构体成员声明：struct { const int x; } s;
	2. 类型转换：(unsigned long)value
	3. 抽象声明符：sizeof(const int *)
*/
specifier_qualifier_list
	: type_specifier specifier_qualifier_list
	| type_specifier
	| type_qualifier specifier_qualifier_list
	| type_qualifier
	;


/*
结构体声明符列表
	: 结构体声明符							| 含义：基础项。递归出口。列表可以只包含一个成员声明。 | 例子：int x;  只声明一个成员。  unsigned int flags : 8;  只声明一个位域成员。
	| 结构体声明符列表 ',' 结构体声明符		| 含义：递归扩展项。允许在一个声明语句中用逗号分隔声明多个成员。所有成员共享同一个类型说明符。 | 例子：int x, y, z;  一次声明三个 int 类型成员。  unsigned int a : 4, b : 4;  声明两个位域成员。
	;
	
	这种设计允许：
	1. 简化代码：一次声明多个相同类型的成员
	2. 提高可读性：相关的成员可以放在一起声明
	3. 支持混合声明：普通成员和位域可以混合声明
	
	示例：
	struct Example {
		int a, b, c;                    // 三个普通成员
		int *p, **pp;                   // 指针成员
		int arr[10], matrix[3][4];      // 数组成员
		unsigned int flag1 : 1, flag2 : 1, flag3 : 6;  // 位域成员
	};
*/
struct_declarator_list
	: struct_declarator
	| struct_declarator_list ',' struct_declarator
	;

/*
结构体声明符
	: 声明符								| 含义：普通成员声明。定义一个普通的结构体或联合体成员，可以是变量、数组或指针等。 | 例子：int x;  普通整型成员。  char name[50];  字符数组成员。  struct Node *next;  指针成员。
	| ':' 常量表达式						| 含义：无名位域（Unnamed bit-field）。只指定位域的宽度，不给它命名。通常用作填充（padding）或对齐。 | 例子：unsigned int : 3;  占用 3 位但无法访问，用于跳过某些位。  unsigned int : 0;  特殊用法：强制下一个位域从新的存储单元开始。
	| 声明符 ':' 常量表达式				| 含义：命名位域（Named bit-field）。定义一个具有指定位宽的成员。位域用于节省内存，可以让多个成员共享同一个存储单元。 | 例子：unsigned int flag : 1;  定义一个 1 位的标志位（只能存储 0 或 1）。  unsigned int color : 8;  定义一个 8 位的颜色值（0-255）。  int status : 2;  定义一个 2 位的有符号整数（-2 到 1）。
	;
	
	位域（Bit-field）详解：
	
	1. 基本语法：
		type member_name : width;
		- type: 必须是整型（int, unsigned int, signed int）或枚举类型
		- width: 位数，必须是常量表达式，范围 0 到类型的位数
	
	2. 位域的限制：
		- 不能取地址：&bf 是非法的，因为位域可能不在字节边界
		- 不能定义位域数组
		- 位域不能是 static
		- 指针不能指向位域
	
	3. 位域的对齐和打包：
		- 位域在同一存储单元内紧密打包
		- 如果下一个位域放不下，会从新的存储单元开始
		- 使用 : 0 可以强制下一个位域从新单元开始
	
	4. 应用场景：
		- 标志位集合：节省空间存储多个布尔值
		- 硬件寄存器映射：精确控制硬件寄存器的位
		- 网络协议：表示数据包的各个字段
		- 嵌入式系统：内存受限的环境
	
	示例：
	struct Flags {
		unsigned int is_valid : 1;      // 1 位：有效标志
		unsigned int is_ready : 1;      // 1 位：就绪标志
		unsigned int priority : 3;      // 3 位：优先级 (0-7)
		unsigned int : 3;               // 3 位：填充/保留
		unsigned int color : 8;         // 8 位：颜色值 (0-255)
		unsigned int : 0;               // 强制下一个位域从新字节开始
		unsigned int status : 4;        // 4 位：状态码
	};
	
	注意事项：
	1. 位域的存储顺序是实现定义的（编译器相关）
	2. 跨平台代码应谨慎使用位域
	3. 位域的符号位行为可能因编译器而异
	4. 读写位域可能比普通成员慢（需要位操作）
*/
struct_declarator
	: declarator
	| ':' constant_expression
	| declarator ':' constant_expression
	;


/*
枚举说明符
	: ENUM '{' 枚举符列表 '}'					| 含义：匿名枚举定义。定义一组命名的整型常量，但不给枚举类型本身命名。枚举常量会被注入到当前作用域。 | 例子：enum { RED, GREEN, BLUE };  定义三个常量：RED=0, GREEN=1, BLUE=2。  enum { MON=1, TUE, WED };  MON=1, TUE=2, WED=3。
	| ENUM IDENTIFIER '{' 枚举符列表 '}'		| 含义：命名枚举定义。定义一个具有名字的枚举类型和一组枚举常量。以后可以用这个枚举名来声明变量。 | 例子：enum Color { RED, GREEN, BLUE };  定义枚举类型 Color。  enum Color c = RED;  声明一个 Color 类型的变量。
	| ENUM IDENTIFIER							| 含义：枚举类型引用或前向声明。引用一个已经定义的枚举类型，或者声明一个枚举类型（C 标准中枚举不支持真正的前向声明，但某些编译器扩展支持）。 | 例子：enum Color c;  使用之前定义的 Color 枚举类型。
	;
	
	枚举（Enumeration）详解：
	
	1. 基本特性：
		- 枚举常量本质上是整型常量（int 类型）
		- 默认从 0 开始自动递增
		- 可以显式指定任意整数值
		- 后续常量在前一个基础上 +1
	
	2. 枚举常量的作用域：
		- 枚举常量具有文件作用域或块作用域
		- 即使是命名枚举，其常量也直接可见（不需要通过枚举名访问）
		- 这与 C++ 不同（C++ 可以用 enum class 创建作用域枚举）
	
	3. 值的指定：
		enum Example {
			A,          // 0
			B,          // 1
			C = 10,     // 10（显式指定）
			D,          // 11（在上一个基础上 +1）
			E = 5,      // 5（可以指定为更小的值）
			F           // 6
		};
	
	4. 应用场景：
		- 定义一组相关的命名常量（状态、选项、错误码等）
		- 提高代码可读性（用名字代替魔法数字）
		- 类型安全（虽然 C 中枚举类型检查较弱）
		- 便于维护（添加新常量时自动分配值）
	
	示例：
	
	// 星期枚举
	enum Weekday {
		MONDAY = 1,    // 从 1 开始
		TUESDAY,       // 2
		WEDNESDAY,     // 3
		THURSDAY,      // 4
		FRIDAY,        // 5
		SATURDAY,      // 6
		SUNDAY         // 7
	};
	
	// 错误码枚举
	enum ErrorCode {
		SUCCESS = 0,
		ERR_FILE_NOT_FOUND = -1,
		ERR_PERMISSION_DENIED = -2,
		ERR_INVALID_ARGUMENT = -3
	};
	
	// 状态机状态
	enum State {
		STATE_IDLE,
		STATE_RUNNING,
		STATE_PAUSED,
		STATE_STOPPED
	};
	
	使用方式：
	enum Color { RED, GREEN, BLUE };
	enum Color c = RED;              // 声明并初始化
	
	if (c == GREEN) {                // 比较
		// ...
	}
	
	switch (c) {                     // 可用于 switch
		case RED:
			// ...
			break;
		case GREEN:
			// ...
			break;
	}
	
	注意事项：
	1. C 语言中枚举类型检查很弱，可以赋任意整数值
		enum Color c = 100;  // 合法但不推荐
	2. 不同枚举的常量可能重名，后定义的会覆盖先定义的
	3. 枚举常量是编译时常量，可用于数组大小等需要常量表达式的地方
	4. 枚举不占用额外内存，只是符号常量的集合
*/
enum_specifier
	: ENUM '{' enumerator_list '}'
	| ENUM IDENTIFIER '{' enumerator_list '}'
	| ENUM IDENTIFIER
	;

/*
枚举符列表
	: 枚举符							| 含义：基础项。递归出口。列表至少包含一个枚举常量。 | 例子：enum { RED };  只有一个枚举常量 RED，值为 0。
	| 枚举符列表 ',' 枚举符			| 含义：递归扩展项。允许用逗号分隔定义多个枚举常量。每个常量可以有自己的值，或者自动递增。 | 例子：enum { RED, GREEN, BLUE };  定义三个常量。  enum { A=1, B, C=10, D };  A=1, B=2, C=10, D=11。
	;
	
	语法特点：
	1. 枚举列表中的常量用逗号分隔
	2. 最后一个枚举常量后面可以有逗号（C99 特性，便于代码生成和维护）
		enum { RED, GREEN, BLUE, };  // 末尾逗号是合法的
	3. 枚举常量可以有相同的值
		enum { A=1, B=1, C };  // A=1, B=1, C=2
	
	示例：
	enum Color {
		RED,         // 0
		GREEN,       // 1
		BLUE         // 2
	};
	
	enum Status {
		OK = 200,
		CREATED = 201,
		BAD_REQUEST = 400,
		NOT_FOUND = 404,
		SERVER_ERROR = 500
	};
	
	enum Flags {
		FLAG_NONE   = 0,
		FLAG_READ   = 1 << 0,  // 1  (位运算常量表达式)
		FLAG_WRITE  = 1 << 1,  // 2
		FLAG_EXEC   = 1 << 2,  // 4
		FLAG_ALL    = FLAG_READ | FLAG_WRITE | FLAG_EXEC  // 7
	};
*/
enumerator_list
	: enumerator
	| enumerator_list ',' enumerator
	;


/*
枚举符
	: IDENTIFIER							| 含义：简单枚举常量。定义一个枚举常量，其值为前一个常量的值加 1（如果是第一个常量，则为 0）。 | 例子：RED  如果是第一个，值为 0；否则为前一个常量值 +1。
	| IDENTIFIER '=' 常量表达式			| 含义：显式赋值的枚举常量。为枚举常量指定一个具体的整数值。这个值必须是常量表达式（编译时可求值）。 | 例子：RED = 5  将 RED 的值显式设置为 5。  MAX_SIZE = 1024  设置为 1024。  FLAG = 1 << 3  使用位运算表达式，值为 8。
	;
	
	枚举常量的值：
	1. 自动赋值规则：
		- 第一个枚举常量：如果没有显式赋值，默认为 0
		- 后续枚举常量：如果没有显式赋值，值为前一个常量 +1
	
	2. 显式赋值：
		- 可以为任何枚举常量显式指定值
		- 值必须是常量表达式（编译时求值）
		- 可以使用算术运算、位运算等
		- 值可以是负数
		- 值可以重复（不同常量可以有相同值）
	
	3. 常量表达式（constant_expression）可以包含：
		- 整数字面量：0, 100, 0xFF
		- 之前定义的枚举常量：RED + 1
		- sizeof 表达式：sizeof(int)
		- 算术运算：10 * 2, 1 << 3
		- 逻辑运算：!(0)
		- 其他编译时可求值的表达式
	
	示例：
	
	// 基本用法
	enum Basic {
		FIRST,          // 0（默认）
		SECOND,         // 1（FIRST + 1）
		THIRD           // 2（SECOND + 1）
	};
	
	// 显式赋值
	enum Explicit {
		A = 10,         // 10（显式）
		B,              // 11（A + 1）
		C = 20,         // 20（显式）
		D               // 21（C + 1）
	};
	
	// 使用表达式
	enum WithExpr {
		BIT0 = 1 << 0,  // 1
		BIT1 = 1 << 1,  // 2
		BIT2 = 1 << 2,  // 4
		BIT3 = 1 << 3,  // 8
		ALL = BIT0 | BIT1 | BIT2 | BIT3  // 15（使用前面定义的常量）
	};
	
	// 负数和重复值
	enum Special {
		NEG = -1,       // -1
		ZERO = 0,       // 0
		POS = 1,        // 1
		DUP = 0         // 0（重复值，合法）
	};
	
	// HTTP 状态码示例
	enum HttpStatus {
		HTTP_OK = 200,
		HTTP_CREATED = 201,
		HTTP_NO_CONTENT = 204,
		HTTP_BAD_REQUEST = 400,
		HTTP_UNAUTHORIZED = 401,
		HTTP_FORBIDDEN = 403,
		HTTP_NOT_FOUND = 404,
		HTTP_SERVER_ERROR = 500
	};
	
	常见用途：
	1. 位标志（Bit Flags）：
		enum Permissions {
			PERM_READ  = 1 << 0,  // 0x01
			PERM_WRITE = 1 << 1,  // 0x02
			PERM_EXEC  = 1 << 2   // 0x04
		};
		unsigned int perms = PERM_READ | PERM_WRITE;
	
	2. 错误码：
		enum Error {
			ERR_SUCCESS = 0,
			ERR_GENERIC = -1,
			ERR_NOMEM = -2,
			ERR_IO = -3
		};
	
	3. 状态值：
		enum State {
			STATE_INIT = 0,
			STATE_READY,
			STATE_RUNNING,
			STATE_DONE
		};
*/
enumerator
	: IDENTIFIER
	| IDENTIFIER '=' constant_expression
	;

/*
类型限定符
	: CONST		| 含义：const 限定符。声明一个常量或只读变量。表示该对象在初始化后不能被修改。编译器会检查并阻止对 const 对象的赋值操作。 | 例子：const int MAX = 100;  定义一个整型常量。  const char *str = "Hello";  指向常量字符的指针（字符不可修改，指针可修改）。  char * const ptr = arr;  常量指针（指针不可修改，指向的内容可修改）。  const char * const p = "Hi";  指针和内容都不可修改。
	| VOLATILE	| 含义：volatile 限定符。告诉编译器该变量的值可能被程序外部因素改变（如硬件、中断、其他线程），不要对其进行优化。每次访问都必须从内存读取，不能缓存在寄存器中。 | 例子：volatile int flag;  可能被中断服务程序修改的标志。  volatile unsigned int *port = (unsigned int *)0x40000000;  映射到硬件寄存器的指针。  volatile sig_atomic_t signal_received;  信号处理中使用的变量。
	;
	
	const 详解：
	
	1. 基本用法：
		const int x = 10;          // x 是常量
		int const y = 20;          // 等价于上面（const 位置可交换）
	
	2. 与指针结合（从右往左读）：
		const int *p;              // 指向常量整数的指针（内容不可变，指针可变）
		                           // *p = 10; 错误
		                           // p = &x;  正确
		
		int * const p;             // 常量指针（指针不可变，内容可变）
		                           // *p = 10; 正确
		                           // p = &x;  错误
		
		const int * const p;       // 指向常量的常量指针（都不可变）
		                           // *p = 10; 错误
		                           // p = &x;  错误
	
	3. 函数参数中的 const：
		void func(const int *p);   // 承诺不修改 p 指向的内容
		void func(const char *str);// 字符串字面量可以传入
	
	4. 返回值中的 const：
		const int* getPtr();       // 返回指向常量的指针
	
	5. 优点：
		- 防止意外修改
		- 提高代码可读性（表明设计意图）
		- 允许编译器优化
		- 可以接受字符串字面量等常量
	
	volatile 详解：
	
	1. 使用场景：
		a) 内存映射的硬件寄存器：
			volatile unsigned int *gpio = (unsigned int *)0x40020000;
			*gpio = 0x01;  // 每次都真实写入硬件
		
		b) 中断服务程序（ISR）修改的变量：
			volatile int timer_ticks = 0;
			
			void timer_ISR() {
				timer_ticks++;  // 在中断中修改
			}
			
			void main() {
				while (timer_ticks < 100) {  // 主程序读取
					// 等待
				}
			}
		
		c) 多线程共享变量（注意：volatile 不保证原子性，通常需要配合其他同步机制）：
			volatile int shared_flag = 0;
		
		d) setjmp/longjmp 中的局部变量：
			volatile int x = 0;  // 避免被优化掉
	
	2. 防止的优化：
		// 不使用 volatile
		int flag = 0;
		while (flag == 0) {
			// 编译器可能优化为无限循环，因为它看不到 flag 在哪里被修改
		}
		
		// 使用 volatile
		volatile int flag = 0;
		while (flag == 0) {
			// 编译器不会优化，每次循环都会从内存读取 flag
		}
	
	3. volatile 不是原子操作保证：
		volatile int counter = 0;
		counter++;  // 这不是原子操作！
		           // 仍然分为：读取、加1、写回三个步骤
		           // 多线程下需要使用互斥锁或原子操作
	
	const 和 volatile 结合使用：
	
	const volatile int *status_reg = (int *)0x40000004;
	// const: 程序不应该修改它
	// volatile: 硬件可能会改变它的值
	// 典型用例：只读的硬件状态寄存器
	
	int value = *status_reg;  // 正确：读取硬件状态
	*status_reg = 0;          // 错误：const 禁止写入
	
	总结：
	- const：编译时语义，防止程序修改，允许编译器优化
	- volatile：运行时语义，防止编译器优化，保证每次访问都读写内存
	- 两者可以同时使用，分别控制不同的语义
*/
type_qualifier
	: CONST
	| VOLATILE
	;


/*
声明符
	: 指针 直接声明符			| 含义：带指针的声明符。定义一个指针类型的变量、数组或函数。指针部分指定了间接层级（*的数量），直接声明符指定了名字和其他修饰（数组、函数）。 | 例子：int *p;  指向 int 的指针。  int **pp;  指向指针的指针（二级指针）。  int *arr[10];  指针数组（10 个指向 int 的指针）。  int *func();  返回 int 指针的函数。
	| 直接声明符				| 含义：不带指针的声明符。定义一个普通变量、数组或函数。 | 例子：int x;  普通变量。  int arr[10];  数组。  int func();  函数。
	;
	
	声明符（Declarator）是 C 语言语法中最复杂的部分之一。它的作用是描述标识符的"形状"——即标识符是什么类型的对象。
	
	核心概念：
	1. 声明符 = 指针部分（可选）+ 直接声明符
	2. 直接声明符包含：
		- 标识符（变量名）
		- 数组维度 []
		- 函数参数 ()
		- 括号分组 ( declarator )
	
	从右往左，从里往外的阅读规则：
	
	1. 找到标识符（变量名）
	2. 向右看：
		- [] 表示"数组"
		- () 表示"函数"
	3. 向左看：
		- * 表示"指针"
	4. 遇到括号时，跳到对应的右括号，继续上述过程
	
	复杂声明示例：
*/
declarator
	: pointer direct_declarator
	| direct_declarator
	;


/*
直接声明符
	: IDENTIFIER								| 含义：基础项。最简单的声明符，就是一个标识符（变量名、函数名）。这是递归的出口。 | 例子：x, count, buffer, calculate
	| '(' 声明符 ')'							| 含义：括号分组。用括号包围一个声明符，改变优先级。这是处理复杂声明的关键。 | 例子：(*p)  将 p 包围，使其先与 * 结合。  (*func)  将 func 包围，使其先成为指针再成为函数。
	| 直接声明符 '[' 常量表达式 ']'				| 含义：数组声明符。声明一个固定大小的数组。常量表达式指定数组的元素个数，必须在编译时可求值。 | 例子：arr[10]  包含 10 个元素的数组。  matrix[3][4]  3x4 的二维数组。  buffer[SIZE]  大小由常量 SIZE 确定的数组。
	| 直接声明符 '[' ']'						| 含义：不定长数组声明符。声明一个大小未指定的数组。通常用于：1) 函数参数（等价于指针）；2) extern 数组声明；3) 不完整类型。 | 例子：void func(int arr[]);  函数参数，等价于 int *arr。  extern int data[];  外部数组声明，大小在定义处指定。  int matrix[][10];  多维数组的第一维可以不指定。
	| 直接声明符 '(' 参数类型列表 ')'			| 含义：函数声明符（带参数）。声明一个函数，指定参数类型列表。这是现代 C 的函数原型声明方式（ANSI C）。 | 例子：func(int x, float y)  接受 int 和 float 参数的函数。  process(const char *str)  接受字符串参数。  operate(int a, ...)  接受可变参数。
	| 直接声明符 '(' 标识符列表 ')'				| 含义：旧式函数声明符（K&R C 风格）。只列出参数名，不指定类型。参数类型在函数定义中另行声明。这是 K&R C 的遗留语法，不推荐使用。 | 例子：func(x, y)  旧式声明，参数类型需要另外指定。  int func(a, b) int a; float b; { ... }  完整的旧式定义。
	| 直接声明符 '(' ')'						| 含义：无参数函数声明符。声明一个不接受参数的函数。注意：在 C 语言中，() 表示参数未指定（不同于 C++），应该用 (void) 来明确表示无参数。 | 例子：func()  参数未指定（不推荐）。  func(void)  明确表示无参数（推荐）。
	;
	
	直接声明符是构建复杂声明的核心。通过递归定义，可以组合出任意复杂的类型。
*/
direct_declarator
	: IDENTIFIER
	| '(' declarator ')'
	| direct_declarator '[' constant_expression ']'
	| direct_declarator '[' ']'
	| direct_declarator '(' parameter_type_list ')'
	| direct_declarator '(' identifier_list ')'
	| direct_declarator '(' ')'
	;

/*
指针
	: '*'									| 含义：单级指针。定义一个指向某类型的指针。 | 例子：int *p;  p 是指向 int 的指针。
	| '*' 类型限定符列表					| 含义：带限定符的单级指针。指针本身可以被 const 或 volatile 限定。 | 例子：int * const p;  p 是常量指针（指针本身不可修改，但指向的内容可修改）。  int * volatile p;  p 是 volatile 指针（可能被外部修改）。  int * const volatile p;  同时具有两种限定符。
	| '*' 指针								| 含义：多级指针。递归定义，允许创建多级间接引用。 | 例子：int **pp;  pp 是指向指针的指针（二级指针）。  int ***ppp;  三级指针。
	| '*' 类型限定符列表 指针				| 含义：带限定符的多级指针。在多级指针中，每一级都可以有自己的限定符。 | 例子：int * const *p;  p 是指向常量指针的指针。  int ** const p;  p 是常量指针，指向指向 int 的指针。
	;
	
	指针详解：
	
	1. 基本概念：
		- 指针存储另一个变量的内存地址
		- * 表示"指向"的关系
		- 每增加一个 *，增加一级间接引用
	
	2. 指针层级：
		int x = 10;
		int *p = &x;          // p 是一级指针，存储 x 的地址
		int **pp = &p;        // pp 是二级指针，存储 p 的地址
		int ***ppp = &pp;     // ppp 是三级指针，存储 pp 的地址
		
		访问方式：
		x                     // 直接访问
		*p                    // 通过一级指针访问
		**pp                  // 通过二级指针访问
		***ppp                // 通过三级指针访问
*/
pointer
	: '*'
	| '*' type_qualifier_list
	| '*' pointer
	| '*' type_qualifier_list pointer
	;

/*
类型限定符列表
	: 类型限定符						| 含义：基础项。递归出口。列表至少包含一个类型限定符。 | 例子：const, volatile
	| 类型限定符列表 类型限定符		| 含义：递归扩展项。允许组合多个类型限定符。注意：重复的限定符是合法的（虽然没有意义）。 | 例子：const volatile  同时具有 const 和 volatile 性质。  const const  合法但冗余（仅一个 const 有效）。
	;
	
	类型限定符列表详解：
	
	1. 可用的类型限定符（C89/C90）：
		- const: 表示常量性
		- volatile: 表示易变性
*/
type_qualifier_list
	: type_qualifier
	| type_qualifier_list type_qualifier
	;

/*
参数类型列表
	: 参数列表							| 含义：固定参数列表。函数接受固定数量和类型的参数。这是最常见的函数声明方式。 | 例子：int add(int a, int b)  接受两个 int 参数。  void print(const char *str)  接受一个字符串参数。  double compute(int x, float y, double z)  接受三个不同类型的参数。
	| 参数列表 ',' ELLIPSIS				| 含义：可变参数列表。函数可以接受可变数量的参数。ELLIPSIS 对应 ...（三个点），表示"可变参数"。必须至少有一个固定参数。 | 例子：int printf(const char *format, ...)  接受格式字符串加可变参数。  int sum(int count, ...)  接受数量参数加可变个整数。  void log(int level, const char *msg, ...)  日志函数with可变参数。
	;
	
	可变参数（Variadic Functions）详解：
	
	1. 基本语法：
		return_type func_name(fixed_params, ...);
*/
parameter_type_list
	: parameter_list
	| parameter_list ',' ELLIPSIS
	;

/*
参数列表
	: 参数声明						| 含义：基础项。至少有一个参数声明。 | 例子：int x
	| 参数列表 ',' 参数声明			| 含义：递归扩展。用逗号分隔多个参数。 | 例子：int x, float y, char *z
	;
*/
parameter_list
	: parameter_declaration
	| parameter_list ',' parameter_declaration
	;

/*
参数声明
	: 声明说明符 声明符				| 含义：完整参数声明，包含类型和参数名。 | 例子：int x, int *ptr, const char *str
	| 声明说明符 抽象声明符			| 含义：带类型修饰但无参数名。 | 例子：int *, int [], int (*)(int)
	| 声明说明符					| 含义：仅类型说明符，无参数名。 | 例子：int, char, void*
	;
*/
parameter_declaration
	: declaration_specifiers declarator
	| declaration_specifiers abstract_declarator
	| declaration_specifiers
	;

/*
标识符列表
	: IDENTIFIER 标识符					| 含义：基础项。单个参数名（K&R C 旧式语法）。 | 例子：x
	| 标识符列表 ',' IDENTIFIER	标识符	| 含义：递归扩展。多个参数名，用逗号分隔。注意这里只有名字，没有类型。 | 例子：x, y, z
	;
	说明：这是 K&R C 的旧式函数定义语法，现代 C 不推荐使用。
	旧式：int add(a, b) int a; int b; { return a+b; }
	现代：int add(int a, int b) { return a+b; }
*/
identifier_list
	: IDENTIFIER
	| identifier_list ',' IDENTIFIER
	;


/*
类型名称
	: 说明符限定符列表						| 含义：仅类型，无声明符。 | 例子：int, const char, struct Point
	| 说明符限定符列表 抽象声明符			| 含义：类型加抽象修饰符（指针、数组、函数）。 | 例子：int *, int [10], int (*)(int)
	;
	说明：类型名称用于类型转换 (int)x、sizeof(int*) 等不需要变量名的场景。
*/
type_name
	: specifier_qualifier_list
	| specifier_qualifier_list abstract_declarator
	;

/*
抽象声明符
	: 指针								| 含义：仅指针修饰。 | 例子：*, **, ***
	| 直接抽象声明符					| 含义：数组、函数等直接修饰符。 | 例子：[], (), [10]
	| 指针 直接抽象声明符				| 含义：指针加直接修饰符的组合。 | 例子：*[], (*)[10], (*)(int)
	;
	说明：抽象声明符是没有标识符名字的声明符，用于类型转换、sizeof、参数声明等。
*/
abstract_declarator
	: pointer
	| direct_abstract_declarator
	| pointer direct_abstract_declarator
	;

/*
直接抽象声明符
	: '(' 抽象声明符 ')'									| 含义：括号分组，改变优先级。 | 例子：(*) 表示指针
	| '[' ']'											| 含义：不定长数组。 | 例子：sizeof(int [])
	| '[' 常量表达式 ']'								| 含义：固定大小数组。 | 例子：sizeof(int [10])
	| 直接抽象声明符 '[' ']'							| 含义：递归的不定长数组。 | 例子：[][10] 表示二维数组第一维不定
	| 直接抽象声明符 '[' 常量表达式 ']'				| 含义：递归的固定大小数组，支持多维。 | 例子：[3][4] 表示 3x4 数组
	| '(' ')'											| 含义：无参数函数。 | 例子：sizeof(int (*)(void))
	| '(' 参数类型列表 ')'								| 含义：带参数的函数。 | 例子：(int, float) 表示接受 int 和 float 的函数
	| 直接抽象声明符 '(' ')'							| 含义：递归的无参函数，如函数指针。 | 例子：(*)(void) 表示指向无参函数的指针
	| 直接抽象声明符 '(' 参数类型列表 ')'				| 含义：递归的带参函数。 | 例子：(*)(int) 表示指向接受 int 的函数的指针
	;
	说明：通过递归定义可以构建复杂类型，如 int (*)[10] 指向数组的指针，int (*)(int) 函数指针。
*/
direct_abstract_declarator
	: '(' abstract_declarator ')'
	| '[' ']'
	| '[' constant_expression ']'
	| direct_abstract_declarator '[' ']'
	| direct_abstract_declarator '[' constant_expression ']'
	| '(' ')'
	| '(' parameter_type_list ')'
	| direct_abstract_declarator '(' ')'
	| direct_abstract_declarator '(' parameter_type_list ')'
	;

/*
初始化器
	: 赋值表达式						| 含义：简单初始化，用单个表达式。 | 例子：int x = 10;  char c = 'A';
	| '{' 初始化器列表 '}'				| 含义：聚合初始化，用花括号包围的列表。 | 例子：int arr[] = {1, 2, 3};  struct Point p = {10, 20};
	| '{' 初始化器列表 ',' '}'			| 含义：带尾随逗号的聚合初始化（C99 特性）。 | 例子：int arr[] = {1, 2, 3,};
	;
	说明：聚合初始化用于数组、结构体、联合体。支持嵌套初始化如 int matrix[2][2] = {{1,2},{3,4}};
*/
initializer
	: assignment_expression
	| '{' initializer_list '}'
	| '{' initializer_list ',' '}'
	;

/*
初始化器列表
	: 初始化器						| 含义：基础项。单个初始化器。 | 例子：{10}
	| 初始化器列表 ',' 初始化器		| 含义：递归扩展。多个初始化器用逗号分隔。 | 例子：{1, 2, 3}  {1, {2, 3}}（嵌套）
	;
*/
initializer_list
	: initializer
	| initializer_list ',' initializer
	;

/*
语句
	: 标号语句		| 含义：带标签的语句，用于 goto、case、default。 | 例子：label: x = 10;  case 1: break;
	| 复合语句		| 含义：用花括号包围的语句块。 | 例子：{ int x = 10; printf("%d", x); }
	| 表达式语句	| 含义：以分号结束的表达式。 | 例子：x = 10;  printf("hello");
	| 选择语句		| 含义：条件分支语句（if、switch）。 | 例子：if (x > 0) y = 1;  switch(x) { ... }
	| 迭代语句		| 含义：循环语句（while、do-while、for）。 | 例子：while (x < 10) x++;  for (i=0; i<10; i++)
	| 跳转语句		| 含义：改变控制流（goto、continue、break、return）。 | 例子：return 0;  break;  goto end;
	;
*/
statement
	: labeled_statement
	| compound_statement
	| expression_statement
	| selection_statement
	| iteration_statement
	| jump_statement
	;

/*
标号语句
	: IDENTIFIER ':' statement				| 含义：标签语句，用于 goto 跳转的目标。 | 例子：error: printf("Error"); return -1;
	| CASE 常量表达式 ':' statement			| 含义：switch 的 case 分支。 | 例子：case 1: x = 10; break;
	| DEFAULT ':' statement					| 含义：switch 的默认分支。 | 例子：default: printf("Unknown"); break;
	;
*/
labeled_statement
	: IDENTIFIER ':' statement
	| CASE constant_expression ':' statement
	| DEFAULT ':' statement
	;

/*
复合语句
	: '{' '}'									| 含义：空语句块。 | 例子：if (x) { }
	| '{' statement_list '}'					| 含义：只包含语句的块。 | 例子：{ x = 10; y = 20; }
	| '{' declaration_list '}'					| 含义：只包含声明的块。 | 例子：{ int x; float y; }
	| '{' declaration_list statement_list '}'	| 含义：包含声明和语句的块（声明必须在前）。 | 例子：{ int x = 10; printf("%d", x); }
	;
	说明：在 C89 中，所有声明必须在语句之前。C99 允许混合声明和语句。
*/
compound_statement
	: '{' '}'
	| '{' statement_list '}'
	| '{' declaration_list '}'
	| '{' declaration_list statement_list '}'
	;

/*
声明列表
	: 声明					| 含义：基础项。单个声明。 | 例子：int x;
	| 声明列表 声明			| 含义：递归扩展。多个声明。 | 例子：int x; float y; char *z;
	;
*/
declaration_list
	: declaration
	| declaration_list declaration
	;


/*
语句列表
	: 语句					| 含义：基础项。单个语句。 | 例子：x = 10;
	| 语句列表 语句			| 含义：递归扩展。多个语句。 | 例子：x = 10; y = 20; printf("%d", x);
	;
*/
statement_list
	: statement
	| statement_list statement
	;

/*
表达式语句
	: ';'				| 含义：空语句（只有分号）。 | 例子：;  用于 for 循环等需要占位的地方
	| expression ';'	| 含义：表达式后跟分号。 | 例子：x = 10;  printf("hello");  i++;
	;
*/
expression_statement
	: ';'
	| expression ';'
	;

/*
选择语句
	: IF '(' expression ')' statement						| 含义：if 语句，无 else。 | 例子：if (x > 0) y = 1;
	| IF '(' expression ')' statement ELSE statement		| 含义：if-else 语句。 | 例子：if (x > 0) y = 1; else y = -1;
	| SWITCH '(' expression ')' statement					| 含义：switch 语句。 | 例子：switch(x) { case 1: break; default: break; }
	;
	说明：嵌套的 if-else 遵循"悬挂 else"问题，else 总是与最近的 if 匹配。
*/
selection_statement
	: IF '(' expression ')' statement
	| IF '(' expression ')' statement ELSE statement
	| SWITCH '(' expression ')' statement
	;

/*
迭代语句
	: WHILE '(' expression ')' statement								| 含义：while 循环，先判断后执行。 | 例子：while (x < 10) x++;
	| DO statement WHILE '(' expression ')' ';'							| 含义：do-while 循环，先执行后判断，至少执行一次。 | 例子：do { x++; } while (x < 10);
	| FOR '(' expression_statement expression_statement ')' statement	| 含义：for 循环，无第三部分（递增表达式）。 | 例子：for (i=0; i<10; ) i++;
	| FOR '(' expression_statement expression_statement expression ')' statement	| 含义：完整的 for 循环。 | 例子：for (i=0; i<10; i++) sum += i;
	;
	说明：for 循环的三部分：初始化、条件、递增。任何部分都可以省略。
*/
iteration_statement
	: WHILE '(' expression ')' statement
	| DO statement WHILE '(' expression ')' ';'
	| FOR '(' expression_statement expression_statement ')' statement
	| FOR '(' expression_statement expression_statement expression ')' statement
	;

/*
跳转语句
	: GOTO IDENTIFIER ';'	| 含义：无条件跳转到标签。 | 例子：goto error;  跳转到 error: 标签处
	| CONTINUE ';'			| 含义：跳过本次循环，继续下一次迭代。 | 例子：for (i=0; i<10; i++) { if (i==5) continue; }
	| BREAK ';'				| 含义：跳出当前循环或 switch。 | 例子：while (1) { if (done) break; }
	| RETURN ';'			| 含义：从函数返回，无返回值（void 函数）。 | 例子：void func() { return; }
	| RETURN expression ';'	| 含义：从函数返回，带返回值。 | 例子：int add(int a, int b) { return a + b; }
	;
*/
jump_statement
	: GOTO IDENTIFIER ';'
	| CONTINUE ';'
	| BREAK ';'
	| RETURN ';'
	| RETURN expression ';'
	;

/*
翻译单元（编译单元）
	: 外部声明						| 含义：基础项。程序至少包含一个外部声明。 | 例子：int x;  或  int main() { }
	| 翻译单元 外部声明				| 含义：递归扩展。程序由多个外部声明组成。 | 例子：int x; void func(); int main() { }
	;
	说明：翻译单元是 C 程序的顶层结构，一个 .c 文件就是一个翻译单元。
*/
translation_unit
	: external_declaration
	| translation_unit external_declaration
	;

/*
外部声明
	: 函数定义		| 含义：函数的完整定义（带函数体）。 | 例子：int add(int a, int b) { return a + b; }
	| 声明			| 含义：全局变量声明、函数原型声明、类型定义等。 | 例子：int x;  void func(int);  typedef int INT;
	;
*/
external_declaration
	: function_definition
	| declaration
	;

/*
函数定义
	: 声明说明符 声明符 声明列表 复合语句		| 含义：带类型和旧式参数声明的函数定义（K&R C）。 | 例子：int add(a, b) int a; int b; { return a+b; }
	| 声明说明符 声明符 复合语句				| 含义：现代函数定义（ANSI C），最常用。 | 例子：int add(int a, int b) { return a+b; }
	| 声明符 声明列表 复合语句					| 含义：无类型说明符的旧式定义（默认返回 int）。 | 例子：add(a, b) int a; int b; { return a+b; }
	| 声明符 复合语句							| 含义：无类型说明符和参数类型的定义（默认 int）。 | 例子：add(a, b) { return a+b; }（不推荐）
	;
	说明：
	- 第1、3、4种是旧式 K&R C 语法，不推荐使用
	- 第2种是现代 ANSI C 标准语法，推荐使用
	- 没有类型说明符时默认返回类型为 int（C89），C99 后不再允许
*/
function_definition
	: declaration_specifiers declarator declaration_list compound_statement
	| declaration_specifiers declarator compound_statement
	| declarator declaration_list compound_statement
	| declarator compound_statement
	;
