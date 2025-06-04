from dataclasses import dataclass, field
from typing import Optional, List, Dict, Union
from compiler_logger import logger

# -------------------- 类型系统 --------------------
@dataclass
class UnitType:
    """表示没有实际值的类型,用于无返回值的函数调用等场景"""
    @property
    def name(self) -> str:
        return "unit"
    
    def __eq__(self, other):
        return isinstance(other, UnitType)
    
@dataclass
class UninitializedType:
    """未初始化的类型 其类型可能已经确定"""
    inner_type: "Type" 
    is_mutable: bool = field(default=False)

@dataclass
class BaseType:
    name: str  # "i32", "bool", "void"等基础类型
    is_mutable: bool = field(default=False)

@dataclass
class ArrayType:
    element_type: 'Type'
    size: int  # 数组长度
    is_mutable: bool = field(default=False)

@dataclass
class RangeType:
    element_type: 'Type'                        # 范围元素的类型（通常是整数类型）
    start: Optional[int] = field(default=None)  # 起始值（可选）
    end: Optional[int] = field(default=None)    # 结束值（可选）
    step: int = field(default=1)                # 步长（默认为1）

@dataclass
class TupleType:
    members: List['Type']
    is_mutable: bool = field(default=False)

@dataclass
class ReferenceType:
    target_type: 'Type'
    is_mutable: bool

@dataclass
class OperatorType:
    category: str  # "relop" / "addop" / "mulop"
    op: str        # 如 "+", "-", "*", "=="

    @property
    def name(self) -> str:
        return f"operator_{self.op}"

    def __eq__(self, other):
        return isinstance(other, OperatorType) and self.op == other.op

    def __str__(self):
        return self.name

Type = Union[UnitType, UninitializedType, BaseType, ArrayType, TupleType, ReferenceType, OperatorType, RangeType]

def type_to_string(t: Type) -> str:
    """类型对象序列化为字符串"""
    if isinstance(t, UnitType):
        return t.name
    elif isinstance(t, UninitializedType):
        return f"<uninitialized {type_to_string(t.inner_type)}>"
    elif isinstance(t, BaseType):
        return t.name
    elif isinstance(t, ArrayType):
        return f"[{type_to_string(t.element_type)}; {t.size}]"
    elif isinstance(t, TupleType):
        members = ', '.join(type_to_string(m) for m in t.members)
        return f"({members})"
    elif isinstance(t, ReferenceType):
        mut = "mut " if t.is_mutable else ""
        return f"&{mut}{type_to_string(t.target_type)}"
    elif isinstance(t, OperatorType):
        return str(t)      

# -------------------- 符号系统 --------------------
class Symbol:
    """符号"""
    def __init__(self, name: str):
        self.name = name
        self.type_str: str = ""  # 类型字符串表示（用于错误消息）

    def set_type_obj(self, type_obj: Type):
        """设置类型对象并自动生成类型字符串"""
        self.type_obj = type_obj
        self.type_str = type_to_string(type_obj)

    def __repr__(self):
        return f"<{self.__class__.__name__} {self.name} {self.type_str}>"

class VariableSymbol(Symbol):
    """变量符号"""
    def __init__(
            self, 
            name: str, 
            type_obj: Optional[Type] = None,
        ):
        super().__init__(name)
        if type_obj:
            self.set_type_obj(type_obj)

    def __repr__(self):
        mut = "mut " if self.type_obj.is_mutable else ""
        init = " (initialized)" if isinstance(self.type_obj, UninitializedType) else ""
        return f"<Var {mut}{self.name}: {getattr(self, 'type_str', '<?>')}{init}>"

class ParameterSymbol(Symbol):
    """函数参数符号"""
    def __init__(
            self, 
            name, 
            type_obj, 
            position=0
        ):
        super().__init__(name)
        self.type_obj = type_obj
        self.position = position      # 参数位置
        
    def __repr__(self):
        mut = "mut " if self.type_obj.is_mutable else ""
        return f"<Param {mut}{self.name}: {self.type_str} @{self.position}>"

class FunctionSymbol(Symbol):
    """函数符号"""
    def __init__(
            self, 
            quad_index: int, 
            name: str, 
            return_type_obj: Optional[Type] = None,
            parameters: Optional[List[VariableSymbol]] = None
        ):
        super().__init__(name)
        self.quad_index = quad_index # 记录函数开始执行的位置
        self.return_type_obj = return_type_obj or UnitType()
        self.parameters = parameters or []
        self.set_type_obj(self._make_func_type())

    def _make_func_type(self) -> Type:
        """构造函数类型（用于重载检查）"""
        param_types = TupleType([p.type_obj for p in self.parameters])
        return TupleType([param_types, self.return_type_obj])
    
    def __repr__(self):
        params = ", ".join([f"{p}" for p in self.parameters])
        return f"<Fn {self.name}({params}) -> {self.type_str}>"

# -------------------- 作用域管理 --------------------
class Scope:
    """作用域"""
    def __init__(self, name: str, parent: Optional['Scope'] = None):
        self.name = name
        self.parent = parent
        self.symbols: Dict[str, Symbol] = {}

    def insert(self, symbol: Symbol) -> bool:
        """添加符号(允许覆盖 以支持重影)"""
        self.symbols[symbol.name] = symbol  # 覆盖旧符号
        return True
    
    def lookup(self, name: str, current_scope_only=False) -> Optional[Symbol]:
        """查找符号（可选是否仅当前作用域）"""
        if name in self.symbols:
            return self.symbols[name]
        if not current_scope_only and self.parent:
            return self.parent.lookup(name)
        return None

# -------------------- 符号表 --------------------
class SymbolTable:
    """符号表"""
    def __init__(self):
        self.global_scope = Scope("global")    # 全局作用域
        self.current_scope = self.global_scope # 当前位于的作用域
        self._type_registry: Dict[str, Type] = {
            "i32": BaseType("i32"),
            "bool": BaseType("bool")
        } # 类型注册表

    def enter_scope(self, name: str):
        self.current_scope = Scope(name, self.current_scope)
        logger.info(f"进入作用域 {self.current_scope.name}")

    def exit_scope(self):
        if self.current_scope.parent:
            self.current_scope = self.current_scope.parent
            logger.info(f"退出作用域至 {self.current_scope.name}")

    def register_type(self, name: str, type_obj: Type) -> bool:
        """注册新类型"""
        if name in self._type_registry:
            logger.warning(f"类型 {name} 已存在，注册失败")
            return False
        self._type_registry[name] = type_obj
        logger.info(f"注册新类型: {name} -> {type_obj}")
        return True

    def lookup_type(self, name: str) -> Optional[Type]:
        """查找类型"""
        return self._type_registry.get(name)
    
    def insert(self, symbol: Symbol) -> bool:
        """插入符号到当前作用域(覆盖之前的)"""
        logger.info(f"符号表插入: {symbol} (作用域: {self.current_scope.name})")
        return self.current_scope.insert(symbol)

    def lookup(self, name: str, current_scope_only=False) -> Optional[Symbol]:
        """查找符号"""
        symbol = self.current_scope.lookup(name, current_scope_only)
        logger.info(f"符号查找: {name} => {symbol} (当前作用域: {self.current_scope.name})")
        return symbol
    
    def lookup_current_scope(self, name: str) -> Optional[Symbol]:
        """只在当前作用域查找符号"""
        return self.lookup(name, current_scope_only=True)
    
    def get_function(self, name: str) -> Optional[FunctionSymbol]:
        """专门查找函数符号（始终从全局作用域开始）"""
        symbol = self.global_scope.lookup(name)
        if isinstance(symbol, FunctionSymbol):
            return symbol
        return None
