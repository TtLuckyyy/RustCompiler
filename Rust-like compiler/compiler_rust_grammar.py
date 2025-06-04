# 新版本的语法
RUST_GRAMMAR = {
    # 终结符需要自行定义 出现在左侧的符号加入到非终结符中
    'terminals' : {
        # 关键字
        'fn', 'mut', 'return', '->', 'let', 'if', 'else', 'while', 'for', 'loop', 'break', 'continue', 'in',
        # 类型
        'i32', 
        # 标识符和字面量
        'ID', 'NUM',
        # 运算符
        '+', '-', '*', '/', '%', '&',
        '==', '!=', '<', '<=', '>', '>=',
        '||', '&&',
        # 界符
        '(', ')', '[', ']', '{', '}', ';', ',', ':', '=', '.', '..', 
    },
    # 可以通过产生式自动生成
    'non_terminals' : {
    },
    # 每一项是一个产生式 是一推一的关系
    'productions' : [
        # 0. 基础结构(Basic Construct)
        {'prod_lhs': 'Begin', 'prod_rhs': ['program']},
        {'prod_lhs': 'program', 'prod_rhs': ['declaration_list']},
        {'prod_lhs': 'declaration_list', 'prod_rhs': ['declaration', 'declaration_list']},
        {'prod_lhs': 'declaration_list', 'prod_rhs': []},
        {'prod_lhs': 'declaration', 'prod_rhs': ['function_declaration']},

        # 1. 函数声明(Function Declaration)
        {'prod_lhs': 'function_declaration', 'prod_rhs': ['function_header', 'block']},               # 块
        {'prod_lhs': 'function_declaration', 'prod_rhs': ['function_header', 'expr_block']},          # 表达式块
        {'prod_lhs': 'function_header', 'prod_rhs': ['fn', 'ID', '(', 'param_list', ')', 'return_type']},
        {'prod_lhs': 'return_type', 'prod_rhs': ['->', 'type']},
        {'prod_lhs': 'return_type', 'prod_rhs': []},
        {'prod_lhs': 'param_list', 'prod_rhs': ['param']},
        {'prod_lhs': 'param_list', 'prod_rhs': ['param', ',', 'param_list']},
        {'prod_lhs': 'param_list', 'prod_rhs': []},
        {'prod_lhs': 'param', 'prod_rhs': ['variable_declaration', ':', 'type']},

        # 2. 块(Block) & 表达式块(Expression_Block)
        {'prod_lhs': 'block', 'prod_rhs': ['{', 'statement_list', '}']},
        {'prod_lhs': 'statement_list', 'prod_rhs': []},
        {'prod_lhs': 'statement_list', 'prod_rhs': ['statement_with_semi', 'statement_list']},
        {'prod_lhs': 'expr_block', 'prod_rhs': ['{', 'statement_list_expression', '}']},
        {'prod_lhs': 'statement_list_expression', 'prod_rhs': ['bare_expression_statement']},
        {'prod_lhs': 'statement_list_expression', 'prod_rhs': ['statement_with_semi', 'statement_list_expression']},
        {'prod_lhs': 'loop_expr_block', 'prod_rhs': ['{', 'statement_list', 'break_statement_with_expr', '}']},

        # 3. 变量和类型
        {'prod_lhs': 'variable_declaration', 'prod_rhs': ['mut', 'ID']}, # 可变变量声明
        {'prod_lhs': 'variable_declaration', 'prod_rhs': ['ID']},        # 不可变变量声明 -- 需要修改
        {'prod_lhs': 'type', 'prod_rhs': ['i32']},
        {'prod_lhs': 'type', 'prod_rhs': ['[', 'type', ';', 'NUM', ']']},
        {'prod_lhs': 'type', 'prod_rhs': ['(', 'tuple_type_inner', ')']},
        {'prod_lhs': 'type', 'prod_rhs': ['&', 'mut', 'type']}, # 可变引用
        {'prod_lhs': 'type', 'prod_rhs': ['&', 'type']},        # 不可变引用

        {'prod_lhs': 'tuple_type_inner', 'prod_rhs': []},
        {'prod_lhs': 'tuple_type_inner', 'prod_rhs': ['type', ',', 'tuple_type_list']},
        {'prod_lhs': 'tuple_type_list', 'prod_rhs': []},
        {'prod_lhs': 'tuple_type_list', 'prod_rhs': ['type']},
        {'prod_lhs': 'tuple_type_list', 'prod_rhs': ['type', ',', 'tuple_type_list']},

        # 4. 语句(Statement)
        {'prod_lhs': 'statement', 'prod_rhs': ['statement_with_semi']},        # 普通语句（带分号）
        {'prod_lhs': 'statement', 'prod_rhs': ['bare_expression_statement']},  # 表达式语句（不带分号）

        {'prod_lhs': 'statement_with_semi', 'prod_rhs': ['variable_declaration_stmt']},              # 变量声明语句
        {'prod_lhs': 'statement_with_semi', 'prod_rhs': ['variable_declaration_assignment_stmt']},   # 变量声明赋值语句
        {'prod_lhs': 'statement_with_semi', 'prod_rhs': ['assignment_stmt']},                        # 赋值语句
        {'prod_lhs': 'statement_with_semi', 'prod_rhs': ['return_statement']},                       # 返回语句
        {'prod_lhs': 'statement_with_semi', 'prod_rhs': ['if_stmt']},                                # if语句
        {'prod_lhs': 'statement_with_semi', 'prod_rhs': ['loop_stmt']},                              # 循环语句
        {'prod_lhs': 'statement_with_semi', 'prod_rhs': ['break_statement']},                        # break语句
        {'prod_lhs': 'statement_with_semi', 'prod_rhs': ['continue_statement']},                     # continue语句
        {'prod_lhs': 'statement_with_semi', 'prod_rhs': [';']},                                      # 空语句（分号）

        # 4.1. 表达式语句
        {'prod_lhs': 'statement_with_semi', 'prod_rhs': ['bare_expression_statement', ';']},  # 表达式语句(有分号)
        {'prod_lhs': 'bare_expression_statement', 'prod_rhs': ['value_expr']},                # 表达式语句(无分号)
        # 4.2. 变量声明语句
        {'prod_lhs': 'variable_declaration_stmt', 'prod_rhs': ['let', 'variable_declaration', ':', 'type', ';']},
        {'prod_lhs': 'variable_declaration_stmt', 'prod_rhs': ['let', 'variable_declaration', ';']},
        {'prod_lhs': 'variable_declaration_assignment_stmt', 'prod_rhs': ['let', 'variable_declaration', '=', 'value_expr', ';']},
        {'prod_lhs': 'variable_declaration_assignment_stmt', 'prod_rhs': ['let', 'variable_declaration', ':', 'type', '=', 'value_expr', ';']},
        # 4.3. 赋值语句
        {'prod_lhs': 'assignment_stmt', 'prod_rhs': ['place_expr', '=', 'value_expr', ';']},
        # 4.4. 返回语句
        {'prod_lhs': 'return_statement', 'prod_rhs': ['return', ';']},
        {'prod_lhs': 'return_statement', 'prod_rhs': ['return', 'value_expr', ';']},
        # 4.5. if语句
        {'prod_lhs': 'if_stmt', 'prod_rhs': ['if', 'value_expr', 'block', 'else_part']},
        {'prod_lhs': 'else_part', 'prod_rhs': []},
        {'prod_lhs': 'else_part', 'prod_rhs': ['else', 'block']},
        {'prod_lhs': 'else_part', 'prod_rhs': ['else', 'if_stmt']},
        # 4.6. 循环语句
        {'prod_lhs': 'loop_stmt', 'prod_rhs': ['while', 'value_expr', 'block']},
        {'prod_lhs': 'loop_stmt', 'prod_rhs': ['for', 'variable_declaration', 'in', 'iterable_structure', 'block']},
        {'prod_lhs': 'loop_stmt', 'prod_rhs': ['loop', 'block']},
        # 4.7. break语句
        {'prod_lhs': 'break_statement', 'prod_rhs': ['break_statement_with_expr']},
        {'prod_lhs': 'break_statement', 'prod_rhs': ['break_statement_without_expr']},
        {'prod_lhs': 'break_statement_with_expr', 'prod_rhs': ['break', 'value_expr', ';']},
        {'prod_lhs': 'break_statement_without_expr', 'prod_rhs': ['break', ';']},
        # 4.8. continue语句
        {'prod_lhs': 'continue_statement', 'prod_rhs': ['continue', ';']},
        
        # 可迭代结构
        {'prod_lhs': 'iterable_structure', 'prod_rhs': ['value_expr', '..', 'value_expr']},
        {'prod_lhs': 'iterable_structure', 'prod_rhs': ['value_expr']},

        # 5. 表达式(Expression)
        # Expressions are divided into two main categories: place expressions and value expressions
        # - A place expression is an expression that represents a memory location.
        # - A value expression is an expression that represents an actual value.
        # Note: Historically, place expressions were called lvalues and value expressions were called rvalues.
        # 5.1 Place Expression (左值表达式)
        {'prod_lhs': 'place_expr', 'prod_rhs': ['place_expr_base']},
        {'prod_lhs': 'place_expr', 'prod_rhs': ['*', 'place_expr']},  # 指针解引用
        {'prod_lhs': 'place_expr_base', 'prod_rhs': ['ID']},
        {'prod_lhs': 'place_expr_base', 'prod_rhs': ['(', 'place_expr', ')']},
        {'prod_lhs': 'place_expr_base', 'prod_rhs': ['place_expr_base', '[', 'value_expr', ']']},  # 数组索引
        {'prod_lhs': 'place_expr_base', 'prod_rhs': ['place_expr_base', '.', 'NUM']},              # 字段访问      
        # 5.2 Value Expression (右值表达式)
        # 表达式层次：条件 → 逻辑或 → 逻辑与 → 关系 → 加减 → 乘除 → 一元 → 后缀 → 基本
        {'prod_lhs': 'value_expr', 'prod_rhs': ['[', 'array_element_list', ']']},   # 数组字面量
        {'prod_lhs': 'value_expr', 'prod_rhs': ['(', 'tuple_element_inner', ')']},  # 元组字面量
        {'prod_lhs': 'value_expr', 'prod_rhs': ['logical_or_expr']},
        {'prod_lhs': 'value_expr', 'prod_rhs': ['conditional_expr']},
        # 条件表达式 if condition { branch_1 } else { branch_2 }
        {'prod_lhs': 'conditional_expr', 'prod_rhs': ['logical_or_expr']},
        {'prod_lhs': 'conditional_expr', 'prod_rhs': ['if', 'logical_or_expr', 'expr_block', 'else', 'expr_block']},
        # 逻辑或
        {'prod_lhs': 'logical_or_expr', 'prod_rhs': ['logical_or_expr', 'logic_or_op', 'logical_and_expr']},
        {'prod_lhs': 'logical_or_expr', 'prod_rhs': ['logical_and_expr']},
        # 逻辑与
        {'prod_lhs': 'logical_and_expr', 'prod_rhs': ['logical_and_expr', 'logic_and_op', 'relational_expr']},
        {'prod_lhs': 'logical_and_expr', 'prod_rhs': ['relational_expr']},       
        # 关系表达式
        {'prod_lhs': 'relational_expr', 'prod_rhs': ['relational_expr', 'relational_op', 'additive_expr']},
        {'prod_lhs': 'relational_expr', 'prod_rhs': ['additive_expr']},
        # 加减表达式
        {'prod_lhs': 'additive_expr', 'prod_rhs': ['additive_expr', 'additive_op', 'multiplicative_expr']},
        {'prod_lhs': 'additive_expr', 'prod_rhs': ['multiplicative_expr']},
        # 乘除表达式
        {'prod_lhs': 'multiplicative_expr', 'prod_rhs': ['multiplicative_expr', 'multiplicative_op', 'unary_expr']},
        {'prod_lhs': 'multiplicative_expr', 'prod_rhs': ['unary_expr']},
        # 一元表达式
        {'prod_lhs': 'unary_expr', 'prod_rhs': ['unary_op', 'unary_expr']},
        {'prod_lhs': 'unary_expr', 'prod_rhs': ['postfix_expr']},
        {'prod_lhs': 'unary_expr', 'prod_rhs': ['NUM']},
        # 后缀表达式
        {'prod_lhs': 'postfix_expr', 'prod_rhs': ['postfix_expr', '(', 'argument_list', ')']},  # 函数调用
        {'prod_lhs': 'postfix_expr', 'prod_rhs': ['primary_expr']},
        # 基本表达式
        {'prod_lhs': 'primary_expr', 'prod_rhs': ['place_expr']},
        {'prod_lhs': 'primary_expr', 'prod_rhs': ['(', 'value_expr', ')']}, # 加括号()
        {'prod_lhs': 'primary_expr', 'prod_rhs': ['expr_block']},           # 表达式块{}
        # 循环表达式
        {'prod_lhs': 'primary_expr', 'prod_rhs': ['loop_expr']},
        {'prod_lhs': 'loop_expr', 'prod_rhs': ['loop', 'loop_expr_block']},

        # 数组元素列表
        {'prod_lhs': 'array_element_list', 'prod_rhs': []},
        {'prod_lhs': 'array_element_list', 'prod_rhs': ['value_expr']},
        {'prod_lhs': 'array_element_list', 'prod_rhs': ['value_expr', ',', 'array_element_list']},
        # 元组元素列表
        {'prod_lhs': 'tuple_element_inner', 'prod_rhs': []},
        {'prod_lhs': 'tuple_element_inner', 'prod_rhs': ['value_expr', ',', 'tuple_element_list']},
        {'prod_lhs': 'tuple_element_list', 'prod_rhs': []},
        {'prod_lhs': 'tuple_element_list', 'prod_rhs': ['value_expr']},
        {'prod_lhs': 'tuple_element_list', 'prod_rhs': ['value_expr', ',', 'tuple_element_list']},
        # 实参列表
        {'prod_lhs': 'argument_list', 'prod_rhs': []},
        {'prod_lhs': 'argument_list', 'prod_rhs': ['value_expr']},
        {'prod_lhs': 'argument_list', 'prod_rhs': ['value_expr', ',', 'argument_list']},
        
        # 6. 运算符
        # 6.1. 关系运算符
        {'prod_lhs': 'relational_op', 'prod_rhs': ['==']},
        {'prod_lhs': 'relational_op', 'prod_rhs': ['!=']},
        {'prod_lhs': 'relational_op', 'prod_rhs': ['<']},
        {'prod_lhs': 'relational_op', 'prod_rhs': ['<=']},
        {'prod_lhs': 'relational_op', 'prod_rhs': ['>']},
        {'prod_lhs': 'relational_op', 'prod_rhs': ['>=']},
        # 6.2. 加减运算符
        {'prod_lhs': 'additive_op', 'prod_rhs': ['+']},
        {'prod_lhs': 'additive_op', 'prod_rhs': ['-']},
        # 6.3. 乘除运算符
        {'prod_lhs': 'multiplicative_op', 'prod_rhs': ['*']}, # 乘号
        {'prod_lhs': 'multiplicative_op', 'prod_rhs': ['/']},
        {'prod_lhs': 'multiplicative_op', 'prod_rhs': ['%']},
        # 6.4. 一元运算符
        {'prod_lhs': 'unary_op', 'prod_rhs': ['&']},          # 引用
        {'prod_lhs': 'unary_op', 'prod_rhs': ['&', 'mut']},
        # 6.5. 逻辑运算符
        {'prod_lhs': 'logic_or_op', 'prod_rhs': ['||']},
        {'prod_lhs': 'logic_and_op', 'prod_rhs': ['&&']},
    ],
    'start_symbol' : 'Begin'
}
# 简单测试文法
TEST_GRAMMAR = {
    # 终结符需要自行定义 出现在左侧的符号加入到非终结符中
    # https://blog.csdn.net/qq_40147863/article/details/93253171
    'terminals' : {
        '=', '*', 'id'
    },
    # 可以通过产生式自动生成
    'non_terminals' : {
    },
    # 每一项是一个产生式 是一推一的关系
    'productions' : [
        {'prod_lhs': 'SS', 'prod_rhs': ['S']},
        {'prod_lhs': 'S', 'prod_rhs': ['L', '=', 'R']},
        {'prod_lhs': 'S', 'prod_rhs': ['R']},
        {'prod_lhs': 'L', 'prod_rhs': ['*', 'R']},
        {'prod_lhs': 'L', 'prod_rhs': ['id']},
        {'prod_lhs': 'R', 'prod_rhs': ['L']},
    ],
    'start_symbol' : 'SS'
}
# 左递归文法
LEFT_RECURSION_GRAMMAR = {
    'terminals': {'a', 'b', 'c'},
    'non_terminals': {'A', 'B'},
    'productions': [
        {'prod_lhs': 'A', 'prod_rhs': ['B', 'a']},
        {'prod_lhs': 'A', 'prod_rhs': ['c']},
        {'prod_lhs': 'A', 'prod_rhs': []},
        {'prod_lhs': 'B', 'prod_rhs': ['A', 'b']},
        {'prod_lhs': 'B', 'prod_rhs': ['d']}
    ],
    'start_symbol': 'A'
}
# 老版本的语法 -- 失败
RUST_GRAMMAR_OLD = {
    # 终结符需要自行定义 出现在左侧的符号加入到非终结符中
    'terminals' : {
        # 关键字
        'fn', 'mut', 'return', '->', 'let', 'if', 'else', 'while', 'for', 'loop', 'break', 'continue', 'in',
        # 类型
        'i32', 
        # 标识符和字面量
        'ID', 'NUM',
        # 运算符
        '+', '-', '*', '/', '%', '&',
        '==', '!=', '<', '<=', '>', '>=',
        # 界符
        '(', ')', '[', ']', '{', '}', ';', ',', ':', '=', '.', '..', 
    },
    # 可以通过产生式自动生成
    'non_terminals' : {
    },
    # 每一项是一个产生式 是一推一的关系
    'productions' : [ 
        # 0.1 变量声明内部
        {'prod_lhs': 'variable_declaration', 'prod_rhs': ['mut', 'ID']},
        # 0.2 类型’
        {'prod_lhs': 'type', 'prod_rhs': ['i32']},
        # 0.3 可赋值元素
        {'prod_lhs': 'assignable_element', 'prod_rhs': ['ID']},

        # 1.1 基础程序
        {'prod_lhs': 'Begin', 'prod_rhs': ['program']},
        {'prod_lhs': 'program', 'prod_rhs': ['declaration_list']},
        {'prod_lhs': 'declaration_list', 'prod_rhs': ['declaration', 'declaration_list']},
        {'prod_lhs': 'declaration_list', 'prod_rhs': []},
        {'prod_lhs': 'declaration', 'prod_rhs': ['function_declaration']},
        {'prod_lhs': 'function_declaration', 'prod_rhs': ['function_header', 'function_body']},
        {'prod_lhs': 'function_body', 'prod_rhs': ['{', 'block_items', '}']}, # 函数体统一使用块
        {'prod_lhs': 'block_items', 'prod_rhs': ['statement_list']}, 
        {'prod_lhs': 'function_header', 'prod_rhs': ['fn', 'ID', '(', 'param_list', ')']},
        {'prod_lhs': 'param_list', 'prod_rhs': []},
        {'prod_lhs': 'statement_block', 'prod_rhs': ['{', 'statement_list', '}']},
        {'prod_lhs': 'statement_list', 'prod_rhs': []},
        # 1.2 语句
        {'prod_lhs': 'statement_list', 'prod_rhs': ['statement', 'statement_list']},
        {'prod_lhs': 'statement', 'prod_rhs': [';']},
        # 1.3 返回语句
        {'prod_lhs': 'statement', 'prod_rhs': ['return_statement']},
        {'prod_lhs': 'return_statement', 'prod_rhs': ['return', ';']},
        # 1.4 函数输入
        {'prod_lhs': 'param_list', 'prod_rhs': ['param']},
        {'prod_lhs': 'param_list', 'prod_rhs': ['param', ',', 'param_list']},
        {'prod_lhs': 'param', 'prod_rhs': ['variable_declaration', ':', 'type']},
        # 1.5 函数输出
        {'prod_lhs': 'function_header', 'prod_rhs': ['fn', 'ID', '(', 'param_list', ')', '->', 'type']},
        {'prod_lhs': 'return_statement', 'prod_rhs': ['return', 'expression', ';']},

        # 2.1 变量声明语句
        {'prod_lhs': 'statement', 'prod_rhs': ['variable_declaration_stmt']},
        {'prod_lhs': 'variable_declaration_stmt', 'prod_rhs': ['let', 'variable_declaration', ':', 'type', ';']},
        {'prod_lhs': 'variable_declaration_stmt', 'prod_rhs': ['let', 'variable_declaration', ';']},
        # 2.2 赋值语句
        {'prod_lhs': 'statement', 'prod_rhs': ['assignment_stmt']},
        {'prod_lhs': 'assignment_stmt', 'prod_rhs': ['assignable_element', '=', 'expression', ';']},
        # 2.3 变量声明赋值语句
        {'prod_lhs': 'statement', 'prod_rhs': ['declaration_assignment_stmt']},
        {'prod_lhs': 'declaration_assignment_stmt', 'prod_rhs': ['let', 'variable_declaration', ':', 'type', '=', 'expression', ';']},
        {'prod_lhs': 'declaration_assignment_stmt', 'prod_rhs': ['let', 'variable_declaration', '=', 'expression', ';']},

        # 3.1 基本表达式
        {'prod_lhs': 'statement', 'prod_rhs': ['expression_statement']},
        {'prod_lhs': 'expression_statement', 'prod_rhs': ['expression', 'expression_statement_end']},
        {'prod_lhs': 'expression_statement_end', 'prod_rhs': [';']},  # 带分号是普通语句
        {'prod_lhs': 'expression', 'prod_rhs': ['additive_expr']},
        {'prod_lhs': 'additive_expr', 'prod_rhs': ['term']},
        {'prod_lhs': 'term', 'prod_rhs': ['factor']},
        {'prod_lhs': 'factor', 'prod_rhs': ['element']},
        {'prod_lhs': 'element', 'prod_rhs': ['NUM']},
        {'prod_lhs': 'element', 'prod_rhs': ['assignable_element']},
        {'prod_lhs': 'element', 'prod_rhs': ['(', 'expression', ')']},
        # 3.2 表达式增加计算和比较(消除左递归)
        {'prod_lhs': 'expression', 'prod_rhs': ['expression', 'comparison_op', 'additive_expr']},
        {'prod_lhs': 'additive_expr', 'prod_rhs': ['additive_expr', 'additive_op', 'term']},
        {'prod_lhs': 'term', 'prod_rhs': ['term', 'multiplicative_op', 'factor']},
        {'prod_lhs': 'comparison_op', 'prod_rhs': ['<']},
        {'prod_lhs': 'comparison_op', 'prod_rhs': ['<=']},
        {'prod_lhs': 'comparison_op', 'prod_rhs': ['>']},
        {'prod_lhs': 'comparison_op', 'prod_rhs': ['>=']},
        {'prod_lhs': 'comparison_op', 'prod_rhs': ['==']},
        {'prod_lhs': 'comparison_op', 'prod_rhs': ['!=']},
        {'prod_lhs': 'additive_op', 'prod_rhs': ['+']},
        {'prod_lhs': 'additive_op', 'prod_rhs': ['-']},
        {'prod_lhs': 'multiplicative_op', 'prod_rhs': ['*']},
        {'prod_lhs': 'multiplicative_op', 'prod_rhs': ['/']},
        # 3.3 函数调用
        {'prod_lhs': 'element', 'prod_rhs': ['ID', '(', 'argument_list', ')']},
        {'prod_lhs': 'argument_list', 'prod_rhs': []},  # 空参数
        {'prod_lhs': 'argument_list', 'prod_rhs': ['expression']},
        {'prod_lhs': 'argument_list', 'prod_rhs': ['expression', ',', 'argument_list']},

        # 4.1 选择结构
        {'prod_lhs': 'statement', 'prod_rhs': ['if_stmt']},
        {'prod_lhs': 'if_stmt', 'prod_rhs': ['if', 'expression', 'statement_block', 'else_part']},
        {'prod_lhs': 'else_part', 'prod_rhs': []},
        {'prod_lhs': 'else_part', 'prod_rhs': ['else', 'statement_block']},
        # 4.2 增加else if
        {'prod_lhs': 'else_part', 'prod_rhs': ['else', 'if', 'expression', 'statement_block', 'else_part']},

        # 5.1 while循环结构
        {'prod_lhs': 'statement', 'prod_rhs': ['loop_stmt']},
        {'prod_lhs': 'loop_stmt', 'prod_rhs': ['while_stmt']},
        {'prod_lhs': 'while_stmt', 'prod_rhs': ['while', 'expression', 'statement_block']},
        # 5.2 for循环结构
        {'prod_lhs': 'loop_stmt', 'prod_rhs': ['for_stmt']},
        {'prod_lhs': 'for_stmt', 'prod_rhs': ['for', 'variable_declaration', 'in', 'iterable_structure', 'statement_block']},
        {'prod_lhs': 'iterable_structure', 'prod_rhs': ['expression', '..', 'expression']},
        # 5.3 loop循环结构
        {'prod_lhs': 'loop_stmt', 'prod_rhs': ['loop_stmt_body']},
        {'prod_lhs': 'loop_stmt_body', 'prod_rhs': ['loop', 'statement_block']},
        # 5.4 增加break和continue
        {'prod_lhs': 'statement', 'prod_rhs': ['break', ';']},
        {'prod_lhs': 'statement', 'prod_rhs': ['continue', ';']},

        # 6.1 声明不可变变量
        {'prod_lhs': 'variable_declaration', 'prod_rhs': ['ID']},
        # 6.2 借用和引用
        {'prod_lhs': 'factor', 'prod_rhs': ['*', 'factor']},
        {'prod_lhs': 'assignable_element', 'prod_rhs': ['*', 'assignable_element']}, # 
        {'prod_lhs': 'factor', 'prod_rhs': ['&', 'mut', 'factor']},
        {'prod_lhs': 'factor', 'prod_rhs': ['&', 'factor']},
        {'prod_lhs': 'type', 'prod_rhs': ['&', 'mut', 'type']},
        {'prod_lhs': 'type', 'prod_rhs': ['&', 'type']},

        # 7.1 函数表达式块 7.2 函数表达式块作为函数体
        {'prod_lhs': 'expression', 'prod_rhs': ['{', 'block_items', '}']},
        {'prod_lhs': 'expression_statement_end', 'prod_rhs': []},     # 无分号可能是隐式返回
        # {'prod_lhs': 'function_expr_block', 'prod_rhs': ['{', 'function_expr_body', '}']},
        # {'prod_lhs': 'function_expr_body', 'prod_rhs': ['statement_list', 'expression']},
        # 7.3 选择表达式
        {'prod_lhs': 'expression', 'prod_rhs': ['selection_expression']},
        # {'prod_lhs': 'selection_expression', 'prod_rhs': ['if', 'expression', 'function_expr_block', 'else', 'function_expr_block']},
        {'prod_lhs': 'selection_expression', 'prod_rhs': ['if', 'expression', 'block_items', 'else', 'block_items']},
        # 7.4 循环表达式
        {'prod_lhs': 'expression', 'prod_rhs': ['loop_stmt_body']},
        {'prod_lhs': 'statement', 'prod_rhs': ['break', 'expression', ';']},

        # 8.1 数组类型和因子
        {'prod_lhs': 'type', 'prod_rhs': ['[', 'type', ';', 'NUM', ']']},
        {'prod_lhs': 'factor', 'prod_rhs': ['[', 'array_element_list', ']']},
        {'prod_lhs': 'array_element_list', 'prod_rhs': []},
        {'prod_lhs': 'array_element_list', 'prod_rhs': ['expression']},
        {'prod_lhs': 'array_element_list', 'prod_rhs': ['expression', ',', 'array_element_list']},
        # 8.2 数组元素
        {'prod_lhs': 'assignable_element', 'prod_rhs': ['element', '[', 'expression', ']']},
        {'prod_lhs': 'factor', 'prod_rhs': ['element', '[', 'expression', ']']},
        {'prod_lhs': 'iterable_structure', 'prod_rhs': ['element']},

        # 9.1 元组
        {'prod_lhs': 'type', 'prod_rhs': ['(', 'tuple_type_internal', ')']},
        {'prod_lhs': 'tuple_type_internal', 'prod_rhs': []},
        {'prod_lhs': 'tuple_type_internal', 'prod_rhs': ['type', ',', 'type_list']},
        {'prod_lhs': 'type_list', 'prod_rhs': []},
        {'prod_lhs': 'type_list', 'prod_rhs': ['type']},
        {'prod_lhs': 'type_list', 'prod_rhs': ['type', ',', 'type_list']},
        {'prod_lhs': 'factor', 'prod_rhs': ['(', 'tuple_assignment_internal', ')']},
        {'prod_lhs': 'tuple_assignment_internal', 'prod_rhs': []},
        {'prod_lhs': 'tuple_assignment_internal', 'prod_rhs': ['expression', ',', 'tuple_element_list']},
        {'prod_lhs': 'tuple_element_list', 'prod_rhs': []},
        {'prod_lhs': 'tuple_element_list', 'prod_rhs': ['expression']},
        {'prod_lhs': 'tuple_element_list', 'prod_rhs': ['expression', ',', 'tuple_element_list']},
        # 9.2 元组元素
        {'prod_lhs': 'assignable_element', 'prod_rhs': ['factor', '.', 'NUM']},
    ],
    'start_symbol' : 'Begin'
}
# 与PPT上命名一致的文法
RUST_GRAMMAR_PPT = {
    # 终结符需要自行定义 出现在左侧的符号加入到非终结符中
    'terminals' : {
        # 关键字
        'fn', 'mut', 'return', '->', 'let', 'if', 'else', 'while', 'for', 'loop', 'break', 'continue', 'in',
        # 类型
        'i32', 
        # 标识符和字面量
        'ID', 'NUM',
        # 运算符
        '+', '-', '*', '/', '%', '&',
        '==', '!=', '<', '<=', '>', '>=',
        # 界符
        '(', ')', '[', ']', '{', '}', ';', ',', ':', '=', '.', '..', 
    },
    # 可以通过产生式自动生成
    'non_terminals' : {
    },
    # 每一项是一个产生式 是一推一的关系
    'productions' : [
        # Program structure
        {'prod_lhs': 'Begin', 'prod_rhs': ['Program']},
        {'prod_lhs': 'JFuncStart', 'prod_rhs': []},
        {'prod_lhs': 'Program', 'prod_rhs': ['JFuncStart', 'DeclarationString']},
        {'prod_lhs': 'DeclarationString', 'prod_rhs': ['Declaration', 'DeclarationString']},
        {'prod_lhs': 'DeclarationString', 'prod_rhs': ['Declaration']},
        {'prod_lhs': 'Declaration', 'prod_rhs': ['FunctionDeclaration']},

        # Function declarations
        {'prod_lhs': 'FunctionDeclaration', 'prod_rhs': ['FunctionHeaderDeclaration', 'FunctionExpressionBlock']}, # 函数表达式块
        {'prod_lhs': 'FunctionDeclaration', 'prod_rhs': ['FunctionHeaderDeclaration', 'Block']},                   # 函数体
        {'prod_lhs': 'FunctionHeaderDeclaration', 'prod_rhs': ['fn', 'ID', '(', 'Parameters', ')']},
        {'prod_lhs': 'FunctionHeaderDeclaration', 'prod_rhs': ['fn', 'ID', '(', ')']},
        {'prod_lhs': 'FunctionHeaderDeclaration', 'prod_rhs': ['fn', 'ID', '(', 'Parameters', ')', '->', 'Type']},
        {'prod_lhs': 'FunctionHeaderDeclaration', 'prod_rhs': ['fn', 'ID', '(', ')', '->', 'Type']},

        # Blocks and parameters
        {'prod_lhs': 'FunctionExpressionBlock', 'prod_rhs': ['{', 'FunctionExpressionString', '}']},
        {'prod_lhs': 'FunctionExpressionString', 'prod_rhs': ['Expression']},
        {'prod_lhs': 'FunctionExpressionString', 'prod_rhs': ['Statement', 'FunctionExpressionString']},
        {'prod_lhs': 'Block', 'prod_rhs': ['{', 'StatementString', '}']},
        {'prod_lhs': 'Block', 'prod_rhs': ['{', '}']},
        {'prod_lhs': 'StatementString', 'prod_rhs': ['Statement']},
        {'prod_lhs': 'StatementString', 'prod_rhs': ['StatementString', 'BeginMarker', 'Statement']},
        
        {'prod_lhs': 'Parameters', 'prod_rhs': ['ParamVar']},
        {'prod_lhs': 'Parameters', 'prod_rhs': ['ParamVar', ',']},
        {'prod_lhs': 'Parameters', 'prod_rhs': ['ParamVar', ',', 'Parameters']},
        {'prod_lhs': 'ParamVar', 'prod_rhs': ['VarDeclaration', ':', 'Type']},

        # Variable declarations
        {'prod_lhs': 'VarDeclaration', 'prod_rhs': ['mut', 'ID']},
        {'prod_lhs': 'VarDeclaration', 'prod_rhs': ['ID']},

        # Types
        {'prod_lhs': 'Type', 'prod_rhs': ['i32']},
        {'prod_lhs': 'Type', 'prod_rhs': ['[', 'Type', ';', 'NUM', ']']},
        {'prod_lhs': 'Type', 'prod_rhs': ['(', 'TupleTypeInner', ')']},
        {'prod_lhs': 'Type', 'prod_rhs': ['(', ')']},
        {'prod_lhs': 'Type', 'prod_rhs': ['&', 'mut', 'Type']},
        {'prod_lhs': 'Type', 'prod_rhs': ['&', 'Type']},
        {'prod_lhs': 'TupleTypeInner', 'prod_rhs': ['Type', ',', 'TypeList']},
        {'prod_lhs': 'TupleTypeInner', 'prod_rhs': ['Type', ',']},
        {'prod_lhs': 'TypeList', 'prod_rhs': ['Type']},
        {'prod_lhs': 'TypeList', 'prod_rhs': ['Type', ',']},
        {'prod_lhs': 'TypeList', 'prod_rhs': ['Type', ',', 'TypeList']},

        # Statements
        {'prod_lhs': 'Statement', 'prod_rhs': [';']},
        {'prod_lhs': 'Statement', 'prod_rhs': ['ReturnStatement']},
        {'prod_lhs': 'Statement', 'prod_rhs': ['VarDeclarationStatement']},
        {'prod_lhs': 'Statement', 'prod_rhs': ['AssignStatement']},
        {'prod_lhs': 'Statement', 'prod_rhs': ['Expression', ';']},
        {'prod_lhs': 'Statement', 'prod_rhs': ['IfStatement']},
        {'prod_lhs': 'Statement', 'prod_rhs': ['CirculateStatement']},
        {'prod_lhs': 'Statement', 'prod_rhs': ['VarDeclarationAssignStatement']},
        {'prod_lhs': 'Statement', 'prod_rhs': ['BreakStatement']},
        {'prod_lhs': 'Statement', 'prod_rhs': ['ContinueStatement']},

        {'prod_lhs': 'BreakStatement', 'prod_rhs': ['break', ';']},
        {'prod_lhs': 'BreakStatement', 'prod_rhs': ['break', 'Expression', ';']},
        {'prod_lhs': 'ContinueStatement', 'prod_rhs': ['continue', ';']},

        {'prod_lhs': 'ReturnStatement', 'prod_rhs': ['return', 'Expression', ';']},
        {'prod_lhs': 'ReturnStatement', 'prod_rhs': ['return', ';']},

        {'prod_lhs': 'VarDeclarationStatement', 'prod_rhs': ['let', 'VarDeclaration', ':', 'Type', ';']},
        {'prod_lhs': 'VarDeclarationStatement', 'prod_rhs': ['let', 'VarDeclaration', ';']},

        {'prod_lhs': 'AssignStatement', 'prod_rhs': ['Assignableidentifier', '=', 'Expression', ';']},

        {'prod_lhs': 'VarDeclarationAssignStatement', 'prod_rhs': ['let', 'VarDeclaration', ':', 'Type', '=', 'Expression', ';']},
        {'prod_lhs': 'VarDeclarationAssignStatement', 'prod_rhs': ['let', 'VarDeclaration', '=', 'Expression', ';']},

        # Control flow
        # 控制流标记 用于指导条件表达式中间代码的生成
        {'prod_lhs': 'ControlFLowMarker', 'prod_rhs': []},
        {'prod_lhs': 'LoopMarker', 'prod_rhs': []},
        {'prod_lhs': 'ReDoMarker', 'prod_rhs': []},
        {'prod_lhs': 'BeginMarker', 'prod_rhs': []},
        {'prod_lhs': 'EndMarker', 'prod_rhs': []},

        # 修改条件控制语句至三条产生式
        {'prod_lhs': 'IfStatement', 'prod_rhs': ['if', 'Expression', 'ControlFLowMarker', 'BeginMarker', 'Block']},
        {'prod_lhs': 'IfStatement', 'prod_rhs': ['if', 'Expression', 'ControlFLowMarker', 'BeginMarker', 'Block', 'EndMarker', 'else', 'BeginMarker', 'Block']},
        {'prod_lhs': 'IfStatement', 'prod_rhs': ['if', 'Expression', 'ControlFLowMarker', 'BeginMarker', 'Block', 'EndMarker', 'else', 'BeginMarker', 'IfStatement']},
        # 修改循环控制语句
        {'prod_lhs': 'CirculateStatement', 'prod_rhs': ['LoopMarker', 'WhileStatement']},
        {'prod_lhs': 'CirculateStatement', 'prod_rhs': ['LoopMarker', 'ForStatement']},
        {'prod_lhs': 'CirculateStatement', 'prod_rhs': ['LoopMarker', 'LoopStatement']},
        {'prod_lhs': 'WhileStatement', 'prod_rhs': ['while', 'ReDoMarker', 'Expression', 'ControlFLowMarker', 'BeginMarker', 'Block']},
        {'prod_lhs': 'ForExpression', 'prod_rhs': ['VarDeclaration', 'in', 'IterableStructure']},
        {'prod_lhs': 'ForStatement', 'prod_rhs': ['for', 'ForExpression', 'BeginMarker', 'Block']},
        {'prod_lhs': 'ForStatement', 'prod_rhs': ['for', 'VarDeclaration', 'in', 'IterableStructure', 'BeginMarker', 'Block']},
        {'prod_lhs': 'LoopStatement', 'prod_rhs': ['loop', 'Block']},

        {'prod_lhs': 'IterableStructure', 'prod_rhs': ['Expression', '..', 'Expression']},
        {'prod_lhs': 'IterableStructure', 'prod_rhs': ['Element']},

        # Expressions
        {'prod_lhs': 'Expression', 'prod_rhs': ['AddExpression']},
        {'prod_lhs': 'Expression', 'prod_rhs': ['Expression', 'Relop', 'AddExpression']},
        {'prod_lhs': 'Expression', 'prod_rhs': ['FunctionExpressionBlock']},
        {'prod_lhs': 'Expression', 'prod_rhs': ['SelectExpression']},
        {'prod_lhs': 'Expression', 'prod_rhs': ['LoopStatement']},

        {'prod_lhs': 'SelectExpression', 'prod_rhs': ['if', 'Expression', 'ControlFLowMarker', 'FunctionExpressionBlock', 'else', 'FunctionExpressionBlock']},

        {'prod_lhs': 'AddExpression', 'prod_rhs': ['Item']},
        {'prod_lhs': 'AddExpression', 'prod_rhs': ['AddExpression', 'AddOp', 'Item']},

        {'prod_lhs': 'Item', 'prod_rhs': ['Factor']},
        {'prod_lhs': 'Item', 'prod_rhs': ['Item', 'MulOp', 'Factor']},

        {'prod_lhs': 'Factor', 'prod_rhs': ['Element']},
        {'prod_lhs': 'Factor', 'prod_rhs': ['[', 'ArrayElementList', ']']},
        {'prod_lhs': 'Factor', 'prod_rhs': ['[', ']']},
        {'prod_lhs': 'Factor', 'prod_rhs': ['(', 'TupleAssignInner', ')']},
        {'prod_lhs': 'Factor', 'prod_rhs': ['(', ')']},
        {'prod_lhs': 'Factor', 'prod_rhs': ['*', 'Factor']},
        {'prod_lhs': 'Factor', 'prod_rhs': ['&', 'mut', 'Factor']},
        {'prod_lhs': 'Factor', 'prod_rhs': ['&', 'Factor']},

        {'prod_lhs': 'ArrayElementList', 'prod_rhs': ['Expression']},
        {'prod_lhs': 'ArrayElementList', 'prod_rhs': ['Expression', ',']},
        {'prod_lhs': 'ArrayElementList', 'prod_rhs': ['Expression', ',', 'ArrayElementList']},

        {'prod_lhs': 'TupleAssignInner', 'prod_rhs': ['Expression', ',', 'TupleElementList']},
        {'prod_lhs': 'TupleAssignInner', 'prod_rhs': ['Expression', ',']},

        {'prod_lhs': 'TupleElementList', 'prod_rhs': ['Expression']},
        {'prod_lhs': 'TupleElementList', 'prod_rhs': ['Expression', ',']},
        {'prod_lhs': 'TupleElementList', 'prod_rhs': ['Expression', ',', 'TupleElementList']},

        {'prod_lhs': 'Assignableidentifier', 'prod_rhs': ['*', 'Assignableidentifier']},
        {'prod_lhs': 'Assignableidentifier', 'prod_rhs': ['AssignableidentifierInner']},

        {'prod_lhs': 'AssignableidentifierInner', 'prod_rhs': ['Element', '[', 'Expression', ']']},
        {'prod_lhs': 'AssignableidentifierInner', 'prod_rhs': ['Element', '.', 'NUM']},
        {'prod_lhs': 'AssignableidentifierInner', 'prod_rhs': ['ID']},

        {'prod_lhs': 'Element', 'prod_rhs': ['NUM']},
        {'prod_lhs': 'Element', 'prod_rhs': ['Assignableidentifier']},
        {'prod_lhs': 'Element', 'prod_rhs': ['(', 'Expression', ')']},
        {'prod_lhs': 'Element', 'prod_rhs': ['ID', '(', 'Arguments', ')']},
        {'prod_lhs': 'Element', 'prod_rhs': ['ID', '(', ')']},

        {'prod_lhs': 'Arguments', 'prod_rhs': ['Expression']},
        {'prod_lhs': 'Arguments', 'prod_rhs': ['Expression', ',']},
        {'prod_lhs': 'Arguments', 'prod_rhs': ['Expression', ',', 'Arguments']},

        # Operators
        {'prod_lhs': 'Relop', 'prod_rhs': ['<']},
        {'prod_lhs': 'Relop', 'prod_rhs': ['<=']},
        {'prod_lhs': 'Relop', 'prod_rhs': ['>']},
        {'prod_lhs': 'Relop', 'prod_rhs': ['>=']},
        {'prod_lhs': 'Relop', 'prod_rhs': ['==']},
        {'prod_lhs': 'Relop', 'prod_rhs': ['!=']},

        {'prod_lhs': 'AddOp', 'prod_rhs': ['+']},
        {'prod_lhs': 'AddOp', 'prod_rhs': ['-']},

        {'prod_lhs': 'MulOp', 'prod_rhs': ['*']},
        {'prod_lhs': 'MulOp', 'prod_rhs': ['/']}
    ],
    'start_symbol' : 'Begin'
}