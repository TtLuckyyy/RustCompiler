"""
词法分析器
1. 保留字(关键词)
2. 标识符
3. 常量
4. 运算符
5. 界符
6. 注释

输入内容：源程序字符串
输出内容：词法单元列表
"""
from enum import Enum
from compiler_logger import logger

class TokenType(Enum):
    """
    词法单元类型枚举
    按功能分组：
    - 关键词：语言保留字（fn/let等）
    - 标识符：变量/函数名
    - 常量：数字/字符串等字面量
    - 运算符：算术/逻辑/位运算
    - 界符：括号/分号等语法符号
    """
    # 关键词
    FN = 'fn'               # 函数
    LET = 'let'             # 变量声明
    MUT = 'mut'             # 可变声明
    IF = 'if'               # 条件语句
    ELSE = 'else'           # 条件语句（否则）
    WHILE = 'while'         # 循环
    RETURN = 'return'       # 返回
    FOR = 'for'             # for 循环
    IN = 'in'               # for-in 语句中的 in
    LOOP = 'loop'           # 无限循环
    BREAK = 'break'         # 跳出循环
    CONTINUE = 'continue'   # 跳过当前循环
    I32 = 'i32'             # 类型：32位整数

    # 标识符
    IDENTIFIER = 'ID'

    # 常量
    INTEGER = 'NUM' # 整数
    FLOAT = 'NUM' # 浮点数
    STRING = 'STRING' # 字符串
    CHAR = 'CHAR' # 字符
    BOOL = 'BOOL' # 布尔值

    # 基础算术运算符
    PLUS = '+'           # +
    MINUS = '-'          # -
    MULTIPLY = '*'       # *
    DIVIDE = '/'         # /
    MOD = '%'            # %
    # 比较运算符
    EQUAL = '=='         # ==  
    NOT_EQUAL = '!='     # !=
    LESS = '<'           # <
    GREATER = '>'        # >
    LESS_EQUAL = '<='    # <=
    GREATER_EQUAL = '>=' # >=
    # 逻辑运算符
    AND = '&&'           # &&
    OR = '||'            # ||
    NOT = '!'            # !
    # 位运算符
    BIT_AND = '&'        # &
    BIT_OR = '|'         # |
    BIT_XOR = '^'        # ^
    BIT_NOT = '~'        # ~
    SHIFT_LEFT = '<<'    # <<
    SHIFT_RIGHT = '>>'   # >>
    # 赋值运算符
    ASSIGN = '='         # =
    ADD_ASSIGN = '+='    # +=
    SUB_ASSIGN = '-='    # -=
    MUL_ASSIGN = '*='    # *=
    DIV_ASSIGN = '/='    # /=
    MOD_ASSIGN = '%='    # %=
    AND_ASSIGN = '&='    # &=
    OR_ASSIGN = '|='     # |=
    XOR_ASSIGN = '^='    # ^=
    SHIFT_LEFT_ASSIGN = '<<='  # <<=
    SHIFT_RIGHT_ASSIGN = '>>=' # >>=
    # 自增/自减
    INCREMENT = '++'     # ++
    DECREMENT = '--'     # --

    # 单字符界符和分隔符
    SEMICOLON = ';' # ;
    COMMA = ','     # ,
    DOT = '.'       # .
    COLON = ':'     # :
    LPAREN = '('    # (
    RPAREN = ')'    # )
    LBRACE = '{'    # {
    RBRACE = '}'    # }
    LBRACKET = '['  # [
    RBRACKET = ']'  # ]
    QUESTION = '?'  # ?

    # 双字符界符和分隔符
    DOUBLE_COLON = '::'  # ::
    ARROW  = '->'        # ->
    DOTDOT = '..'        # ..

    # 结束符
    EOF = '$'

class Token:
    """
    Token数据结构
    属性：
    - type: TokenType枚举值
    - value: 原始词素值(存储的均是相应的文本)
    - line: 所在行号(1-based)
    - column: 所在列号(1-based)
    """
    def __init__(self, type_: TokenType, value=None, line=None, column=None):
        self.type = type_
        self.value = value # 存储的就是相应的文本 # !!TokenValue
        self.line = line
        self.column = column
    
    def __str__(self):
        # 统一格式：[Type:value]
        value_part = f":{self.value}" if self.value is not None else ""
        return f"[{self.type.name}{value_part}]"
    
    def __repr__(self):
        return f"Token({self.type}, {self.value}, line={self.line}, column={self.column})"

class Lexer:
    """
    核心词法分析器类
    工作流程：
    1. 初始化：设置源代码文本和指针
    2. next_token(): 逐个提取Token
    3. tokenize(): 批量处理整个文本

    设计要点：
    - 使用peek()实现单字符前瞻
    - 各_handle_*方法处理特定词法单元
    - 严格的位置跟踪（行列计数）
    """
    def __init__(self, text=None):
        """
        词法分析器初始化

        :param text: 要分析的源代码字符串
        """
        self.text = text or ""
        self.pos = 0
        self.line = 1
        self.column = 1
        self.current_char = self.text[0] if self.text else None

    def error(self, message):
        """抛出异常"""
        full_msg = f"Lexer error at line {self.line}, column {self.column}: {message}"
        logger.error(full_msg)
        raise Exception(full_msg)
    
    def warn(self, message):
        """记录警告信息"""
        full_msg = f"Lexer warning at line {self.line}, column {self.column}: {message}"
        logger.warning(full_msg)
    
    def advance(self):
        """移动到下一个字符"""
        if self.current_char == '\n':
            self.line += 1
            self.column = 0

        self.pos += 1
        self.column += 1

        if self.pos < len(self.text):
            self.current_char = self.text[self.pos]
        else:
            self.current_char = None

    def peek(self):
        """查看下一个字符"""
        peek_pos = self.pos + 1

        if peek_pos < len(self.text):
            return self.text[peek_pos]
        else:
            return None
        
    def _skip_whitespace(self):
        """跳过空格"""
        while self.current_char is not None and self.current_char.isspace():
            self.advance()

    def _skip_comment(self):
        """跳过注释"""
        # 单行注释
        if self.current_char == '/' and self.peek() == '/':
            while self.current_char is not None and self.current_char != '\n':
                self.advance()

        # 多行注释（支持嵌套）
        if self.current_char == '/' and self.peek() == '*':
            nest_level = 1  # 初始化嵌套层级
            self.advance()  # 跳过/
            self.advance()  # 跳过*
            
            while nest_level > 0 and self.current_char:
                # 遇到注释开始标记
                if self.current_char == '/' and self.peek() == '*':
                    nest_level += 1
                    self.advance()
                    self.advance()
                # 遇到注释结束标记    
                elif self.current_char == '*' and self.peek() == '/':
                    nest_level -= 1
                    self.advance()
                    self.advance()
                # 普通字符处理
                else:
                    if self.current_char == '\n':
                        self.line += 1
                        self.column = 0
                    self.advance()
            
            if nest_level > 0:
                self.error("Unterminated nested comment")

    def _handle_number(self):
        """处理数字"""
        num_str = ''
        is_float = False
        start_pos = (self.line, self.column)

        # 整数部分
        while self.current_char is not None and self.current_char.isdigit():
            num_str += self.current_char
            self.advance()
        
        # 小数部分(需要保证小数点后面是数字)
        if self.current_char == '.' and self.peek().isdigit():
            is_float = True
            num_str += self.current_char
            self.advance()

            while self.current_char is not None and self.current_char.isdigit():
                num_str += self.current_char
                self.advance()

        try:
            # 数字字面量存在value
            value = float(num_str) if is_float else int(num_str)
            return Token(TokenType.FLOAT if is_float else TokenType.INTEGER, value, *start_pos)
        except ValueError:
            self.error(f"Invalid numeric literal: {num_str}")

    def _handle_string(self):
        """处理字符串"""
        buffer = []
        start_pos = (self.line, self.column)
        self.advance() # 跳过开始的引号

        # 转移符
        escape_map = {
            'n': '\n',
            't': '\t',
            'r': '\r',
            '\\': '\\',
            '"': '"',
            "'": "'",
            '0': '\0'
        }

        while self.current_char and self.current_char != '"':
            if self.current_char == '\\':
                self.advance()
                if not self.current_char:
                    break
                buffer.append(escape_map.get(self.current_char, f"\\{self.current_char}"))  # 未知转义保持原样
            else:
                buffer.append(self.current_char)
            self.advance()

        if self.current_char is None:
            self.error("Unterminated string literal")
        self.advance() # 跳过结束的引号

        # 字符串字面量存在value
        return Token(TokenType.STRING, ''.join(buffer), *start_pos)
    
    def _handle_identifier(self):
        """处理标识符"""
        identifier = []
        start_pos = (self.line, self.column)

        while self.current_char and (self.current_char.isalnum() or self.current_char == '_'):
            identifier.append(self.current_char)
            self.advance()

        ident_str = ''.join(identifier)

        # 保留字
        keyword_map = {
            'fn': TokenType.FN,
            'let': TokenType.LET,
            'mut': TokenType.MUT,
            'if': TokenType.IF,
            'else': TokenType.ELSE,
            'while': TokenType.WHILE,
            'return': TokenType.RETURN,
            'for': TokenType.FOR,
            'in': TokenType.IN,
            'loop': TokenType.LOOP,
            'break': TokenType.BREAK,
            'continue': TokenType.CONTINUE,
            'i32': TokenType.I32
        }

        token_type = keyword_map.get(ident_str, TokenType.IDENTIFIER)

        return Token(token_type, ident_str, *start_pos)
    
    def _handle_operator(self):
        """处理运算符"""
        operator_map = {
            # 单字符运算符
            '+': TokenType.PLUS,
            '-': TokenType.MINUS,
            '*': TokenType.MULTIPLY,
            '/': TokenType.DIVIDE,
            '%': TokenType.MOD,
            '=': TokenType.ASSIGN,
            '!': TokenType.NOT,
            '<': TokenType.LESS,
            '>': TokenType.GREATER,
            '&': TokenType.BIT_AND,
            '|': TokenType.BIT_OR,
            '^': TokenType.BIT_XOR,
            '~': TokenType.BIT_NOT,
            # 双字符运算符
            '++': TokenType.INCREMENT,
            '--': TokenType.DECREMENT,
            '+=': TokenType.ADD_ASSIGN,
            '-=': TokenType.SUB_ASSIGN,
            '*=': TokenType.MUL_ASSIGN,
            '/=': TokenType.DIV_ASSIGN,
            '%=': TokenType.MOD_ASSIGN,
            '==': TokenType.EQUAL,
            '!=': TokenType.NOT_EQUAL,
            '<=': TokenType.LESS_EQUAL,
            '>=': TokenType.GREATER_EQUAL,
            '<<': TokenType.SHIFT_LEFT,
            '>>': TokenType.SHIFT_RIGHT,
            '&&': TokenType.AND,
            '||': TokenType.OR,
            '=>': TokenType.ARROW,
        }
        double_delimiter_map = {
            '->': TokenType.ARROW,
        }

        if self.current_char and self.peek():
            double_op = self.current_char + self.peek()
            if double_op in operator_map:
                start_line, start_col = self.line, self.column
                self.advance()
                self.advance()
                return Token(operator_map[double_op], double_op, start_line, start_col)
            if double_op in double_delimiter_map:
                return None
            
        if self.current_char in operator_map:
            op = self.current_char
            start_line, start_col = self.line, self.column
            self.advance()
            return Token(operator_map[op], op, start_line, start_col)
        
        return None

    def _handle_delimiters(self):
        """处理所有界符字符，返回对应的Token"""
        delimiter_map = {
            # 单字符界符
            ';': TokenType.SEMICOLON,
            ',': TokenType.COMMA,
            '.': TokenType.DOT,
            ':': TokenType.COLON,
            '(': TokenType.LPAREN,
            ')': TokenType.RPAREN,
            '{': TokenType.LBRACE,
            '}': TokenType.RBRACE,
            '[': TokenType.LBRACKET,
            ']': TokenType.RBRACKET,
            '?': TokenType.QUESTION,
            # 双字符界符
            '::': TokenType.DOUBLE_COLON,
            '->': TokenType.ARROW,
            '..': TokenType.DOTDOT
        }

        # 双字符界符检查
        if self.current_char and self.peek():
            double_char = self.current_char + self.peek()
            if double_char in delimiter_map:
                start_line, start_col = self.line, self.column
                self.advance()
                self.advance()
                return Token(delimiter_map[double_char], double_char, start_line, start_col)
        
        # 单字符界符检查
        if self.current_char in delimiter_map:
            char = self.current_char
            start_line, start_col = self.line, self.column
            self.advance()
            return Token(delimiter_map[char], char, start_line, start_col)
        
        return None

    def next_token(self):
        while self.current_char is not None:
            # 跳过空格
            if self.current_char.isspace():
                self._skip_whitespace()
                continue
            # 注释
            if self.current_char == '/' and (self.peek() == '/' or self.peek() == '*'):
                self._skip_comment()
                continue
            # 数字
            if self.current_char.isdigit():
                return self._handle_number()
            # 字符串
            if self.current_char == '"':
                return self._handle_string()
            # 标识符和关键字
            if self.current_char.isalpha() or self.current_char == '_':
                return self._handle_identifier()
            # 运算符
            if operator_token := self._handle_operator():
                return operator_token
            # 界符和分隔符
            if delimiter_token := self._handle_delimiters():
                return delimiter_token

            # 其他字符
            self.error(f"Unknown character: {self.current_char}")
        
        return Token(TokenType.EOF, None, self.line, self.column)
    
    def reset(self, text):
        """初始化"""
        self.text = text or ""
        self.pos = 0
        self.line = 1
        self.column = 1
        self.current_char = self.text[0] if self.text else None

    def tokenize(self, text):
        """词法分析"""
        self.reset(text) # 先初始化
        tokens = []
        while((token := self.next_token()).type != TokenType.EOF):
            tokens.append(token)
        tokens.append(token)  # 加入EOF
        self._log_lexer_result(tokens)
        return tokens
    
    def _log_lexer_result(self, tokens):
        """输出词法分析器分析结果"""
        from collections import defaultdict
        lines = defaultdict(list)
        for token in tokens:
            lines[token.line].append(token)

        logger.info("====== LEXER RESULT START ======")
        for line_num, code_line in enumerate(self.text.split('\n'), 1):
            logger.info(f"{line_num:4d} | {code_line}")
            if line_num in lines:
                indent = " " * 6
                token_strs = [str(token) for token in lines[line_num]]
                logger.info(f"{indent}-> {' '.join(token_strs)}")
        logger.info("======= LEXER RESULT END =======")
