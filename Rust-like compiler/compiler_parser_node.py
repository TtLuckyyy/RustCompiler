"""语法分析树节点"""
from dataclasses import dataclass, field
from typing import Optional, List, Any
from compiler_lexer import Tokenize,LexicalElement

@dataclass
class ExprResult:
    """表达式结果封装类,用于在语法分析树节点之间传递表达式计算信息"""
    var_name: Optional[str] = None       # 变量名称
    type_obj: Any = None                 # 类型对象
    is_mutable: bool = False             # 是否可变
    value: Optional[Any] = None          # 可能的值
    is_lvalue: bool = False              # 是否可以作为左值
    is_rvalue: bool = False              # 是否可以作为右值
    index_expr: Optional[Any] = None     # 用于数组索引
    member_index: Optional[Any] = None   # 用于元组成员访问
    

@dataclass
class SynthesizedAttributes:
    """综合属性"""
    place: Optional[str] = None                           # 值存储位置(常量值或变量名称)
    quad_index: Optional[int] = None                      # 记录下一条未生成四元式的位置  
       
    true_list: List[int] = field(default_factory=list)    # 为真跳转目标
    false_list: List[int] = field(default_factory=list)   # 为假跳转目标
    next_list: List[int] = field(default_factory=list)    # 下一跳转目标
    break_list: List[int] = field(default_factory=list)

class ParseNode:
    def __init__(
            self, 
            symbol: str, 
            children: Optional[List["ParseNode"]] = None, 
            token: Optional[LexicalElement] = None
            ):
        """
        语法分析树节点
        
        :param symbol: 节点符号(String)
        :param children: 子节点列表
        :param token: 关联的词法单元(对终结符节点)
        """
        self.symbol = symbol
        self.children = children if children is not None else []
        self.token = token

        # 终结符相关属性
        self.value = getattr(token, "value", None)
        self.line = getattr(token, "line", -1)
        self.column = getattr(token, "column", -1)

        # 语义分析属性
        self.expr_res: Optional[ExprResult] = None # 表达式结果信息
        self.var_name: Optional[str] = None        # 变量声明用
        self.type_obj: Optional[type] = None       # 变量声明用
        self.is_mutable: Optional[bool] = None     # 变量声明用
        self.expressions = None                    # 数组和元组用
        self.member_types = None                   # 数组和元组用

        # 函数/方法相关属性
        self.return_type = None     # 返回值类型(函数节点)
        self.last_return = False    # 判断最后一个语句是不是返回语句
        self.parameters = None      # 参数列表(函数节点)
        self.arguments = None       # 函数调用参数

        # 综合属性
        self.attributes: Optional[SynthesizedAttributes] = SynthesizedAttributes()
        
    def is_terminal(self):
        """判断是否为终结符节点"""
        return self.token is not None
    
    def add_child(self, child):
        """添加子节点"""
        self.children.append(child)
        return self

    def __str__(self):
        if self.token:
            return f"{self.symbol}({self.token.value})"
        return f"{self.symbol}[{len(self.children)}]"
    
    def __repr__(self):
        return f"<ParseNode {self.__str__()}>"
