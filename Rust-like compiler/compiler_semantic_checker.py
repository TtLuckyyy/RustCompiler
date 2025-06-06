"""语义检查器"""
from typing import Dict, List
from compiler_parser_node import ParseNode, ExprResult
from compiler_logger import logger
from compiler_semantic_symbol import VariableSymbol, ParameterSymbol, FunctionSymbol, SymbolTable, Scope
from compiler_semantic_symbol import Type, BaseType, ArrayType, TupleType, ReferenceType, OperatorType, UnitType, UninitializedType, RangeType
from compiler_semantic_symbol import type_to_string
from compiler_codegenerator import IntermediateCodeGenerator

class SemanticError:
    """简化的语义错误类"""
    def __init__(self, message: str, line: int = None, column: int = None):
        self.message = message
        self.line = line
        self.column = column

    def __str__(self) -> str:
        location = ""
        if self.line is not None:
            location = f" 位于行 {self.line}"
            if self.column is not None:
                location += f" 列 {self.column}"
        return f"{self.message}{location}"

class SemanticChecker:
    """语义检查器"""
    def __init__(self):
        self.symbolTable = SymbolTable()                        
        self.pending_type_inference: Dict[str, ParseNode] = {} 
        self.errors = []                                    
        self.current_function = None                       
        self.loop_stack = []                             
        self.code_generator = IntermediateCodeGenerator()     
        self.reference_tracker = {}                           
        
    def reset(self):
        """重置"""
        self.symbolTable = SymbolTable()                      
        self.pending_type_inference: Dict[str, ParseNode] = {}  
        self.errors = []                                      
        self.current_function = None                         
        self.reference_tracker = {}                          
        self.code_generator.reset()

    def check(self, node: ParseNode):
        """后序遍历语法树进行语义检查"""
        for child in node.children:
            self.check(child)
        method_name = f"_handle_{node.symbol}"
        action = getattr(self, method_name, self.no_action)
        action(node)

    def on_reduce(self, node: ParseNode):
        """处理非终结符节点"""
        method_name = f"_handle_{node.symbol}"
        action = getattr(self, method_name, self.no_action)
        self._update_position(node=node)
        logger.info(f"✏️  当前处理: {method_name}")
        action(node)
            
    def no_action(self, node: ParseNode):
        """默认处理规则"""
        logger.info(f"❌  此处未定义处理规则: {node.symbol}")
        pass

    # ---------- 具体节点检查方法 ----------

    def _handle_JFuncStart(self, node: ParseNode):
        """处理开始跳转到main函数"""
        node.attributes.next_list = [self.code_generator.next_quad]
        self.code_generator.emit('j', None, None, None)
        
    def _handle_Program(self, node: ParseNode):

        # 检查是否有待类型推断的符号
        if self.pending_type_inference:
            for var_name, var_node in self.pending_type_inference.items():
                self._report_error(f"无法推断变量 '{var_name}' 的类型，请显式指定类型或赋初值", var_node)
        
        funcStartSymbol = self.symbolTable.lookup('main')
        if not funcStartSymbol:
            self._report_error("程序必须包含一个 'main' 函数作为入口点", node)
            return 

        self.code_generator.backpatch(node.children[0].attributes.next_list, funcStartSymbol.quad_index)
            
    def _handle_Declaration(self, node: ParseNode):
        pass

    def _handle_DeclarationString(self, node: ParseNode):
        pass

    def _handle_Type(self, node: ParseNode):
        first_child = node.children[0]

        
        if first_child.value == 'i32': # 基础类型 (i32)
            node.type_obj = BaseType("i32")

        elif first_child.value == '[':  # 数组类型 [Type; NUM]
            element_type_node = node.children[1]  # 数组元素类型节点
            size_node = node.children[3]          # 数组大小节点

            # 检查数组大小是否为正整数
            try:
                size = int(size_node.value)
                if size <= 0:
                    self._report_error(f"数组大小必须为正整数，实际为 {size}", size_node)
                    size = 1  # 设置默认值以继续分析
            except ValueError:
                self._report_error(f"无效的数组大小：{size_node.value}", size_node)
                size = 1  # 设置默认值以继续分析

            node.type_obj = ArrayType(
                element_type=element_type_node.type_obj,
                size=size
            )

        elif first_child.value == '(':
            if len(node.children) == 2:  # 空元组
                node.type_obj = TupleType([])
            else:
                node.type_obj = TupleType(node.children[1].member_types)

        elif first_child.value == '&':  # 引用类型 &mut T 或 &T
            is_mut = len(node.children) > 2 and node.children[1].value == 'mut' # 是否为可变引用
            target_type_node = node.children[-1]                                # 目标类型对象
            
            node.type_obj = ReferenceType(
                target_type=target_type_node.type_obj,
                is_mutable=is_mut
            )

    def _handle_TupleTypeInner(self, node: ParseNode):
        member_types = []
        for child in node.children:
            if child.symbol == "Type":
                member_types.append(child.type_obj)
            elif child.symbol == "TypeList":
                member_types.extend(child.member_types)
        
        node.member_types = member_types

    def _handle_TypeList(self, node: ParseNode):
        member_types = []
        for child in node.children:
            if child.symbol == "Type":
                member_types.append(child.type_obj)
            elif child.symbol == "TypeList":
                member_types.extend(child.member_types)

        node.member_types = member_types

    def _handle_VarDeclaration(self, node: ParseNode):

        if node.children[0].value == 'mut':
            node.var_name = node.children[1].value
            node.is_mutable = True
        else:
            node.var_name = node.children[0].value
            node.is_mutable = False  
            
    def _handle_VarDeclarationStatement(self, node: ParseNode):

        # 从VarDeclaration获取变量名和是否可变
        var_decl_node = node.children[1]

        var_name = var_decl_node.var_name
        is_mutable = var_decl_node.is_mutable
        
        if node.children[-2].symbol == "Type":
            inner_type = node.children[-2].type_obj
            if var_name in self.pending_type_inference:
                del self.pending_type_inference[var_name] # 重影覆盖之前需要类型推断的变量
        else:
            inner_type = None
            self.pending_type_inference[var_name] = node # 插入待推断字典

        # 未初始化类型
        var_type = UninitializedType(
            inner_type=inner_type,
            is_mutable=is_mutable
        )
            
        # 创建并插入符号
        var_symbol = VariableSymbol(
            name=var_name,
            type_obj=var_type,
        )
        self.symbolTable.insert(var_symbol)
        
    def _handle_VarDeclarationAssignStatement(self, node: ParseNode):

        # 获取变量名和类型
        var_decl_node = node.children[1]    # VarDeclaration 节点
        expr_node = node.children[-2]       # Expression 节点
        type_node = node.children[3]        # 声明类型节点

        var_name = var_decl_node.var_name
        is_mutable = var_decl_node.is_mutable

        declared_type = type_node.type_obj        # 声明类型
        expr_type = expr_node.expr_res.type_obj   # 表达式类型

        if isinstance(expr_type, UninitializedType):
            self._report_error("该变量未初始化，不能作为右值使用", expr_node)
            return
        
        elif isinstance(expr_type, UnitType):
            self._report_error("右值表达式没有类型(unit 类型)，不能作为右值使用", expr_node)
            return

        # 类型兼容检查
        if len(node.children) > 5 and not self._is_type_compatible(expr_type, declared_type):
            self._report_error(f"类型不匹配: 不能将 {expr_type} 赋值给 {declared_type}", expr_node)
            var_type = declared_type
        else:
            var_type = expr_type

        # 创建符号并插入符号表
        var_type.is_mutable = is_mutable
        var_symbol = VariableSymbol(name=var_name, type_obj=var_type,)
        self.symbolTable.insert(var_symbol)

        # 中间代码生成
        expr_attrs = node.children[-2].attributes
        self.code_generator.emit('=', expr_attrs.place, None, var_name)

# ------------------ 函数定义 -----------------------

    def _handle_ParamVar(self, node: ParseNode):

        # 提取变量声明和类型节点
        var_decl_node = node.children[0]  # VarDeclaration
        type_node = node.children[2]      # Type

        type_node.type_obj.is_mutable = var_decl_node.is_mutable
        param_symbol = ParameterSymbol(
            name=var_decl_node.var_name,
            type_obj=type_node.type_obj
        )

        node.parameters = [param_symbol]

    def _handle_Parameters(self, node: ParseNode):

        # 初始化参数列表
        parameters = []
        position_counter = 0
        param_names = set()

        # 遍历所有子节点, 收集参数
        for child in node.children:
            if child.symbol in {"ParamVar", "Parameters"}:
                for param in child.parameters:
                    if param.name in param_names:
                        self._report_error(f"重复的参数名: {param.name}", node)
                        continue
                    param.position = position_counter
                    position_counter += 1
                    parameters.append(param)
                    param_names.add(param.name)                 

        node.parameters = parameters

                
    def _handle_FunctionHeaderDeclaration(self, node: ParseNode):

        # 提取函数名
        func_name_node = node.children[1]  # ID节点
        node.func_name = func_name_node.value

        # Begin:进入该函数的作用域
        self.symbolTable.enter_scope(node.func_name)

        # 检查是否有返回类型声明 Return
        if node.children[-2].value == '->':
            type_node = node.children[-1]
            node.return_type = type_node.type_obj
        else:
            node.return_type = UnitType()

        # 处理参数 Param
        if node.children[2].symbol == '(' and node.children[3].symbol == ')':
            node.parameters = []
        else:
            parameters_node = node.children[3]
            node.parameters = parameters_node.parameters

            # 将函数参数加入到该作用域中
            for param in node.parameters:
                self.symbolTable.insert(param)

        # 将函数信息临时存储起来
        self.current_function = FunctionSymbol(
            quad_index=self.code_generator.next_quad,
            name=node.func_name,
            return_type_obj=node.return_type,
            parameters=node.parameters
        )
            
        # 调试输出完整函数头信息
        param_str = ", ".join([f"{param.name}: {param.type_obj}" for param in node.parameters])
        return_str = f" -> {node.return_type}" if node.return_type is not None else "void"

    def _handle_FunctionDeclaration(self, node: ParseNode):

        header_node = node.children[0]   # FunctionHeaderDeclaration
        body_node = node.children[-1]    # FunctionExpressionBlock/Block
        declared_return_type = header_node.return_type   # 函数声明返回值类型
    
        # 处理函数表达式块
        if body_node.symbol == "FunctionExpressionBlock":
            actual_return_type = body_node.expr_res.type_obj # 表达式块计算值的类型

            if not self._is_type_compatible(actual_return_type, declared_return_type):
                self._report_error(f"返回值类型不匹配: 声明返回 {declared_return_type}, 实际返回 {actual_return_type}", node)

            # TODO: 函数表达式块的返回值 将最后一个表达式的计算结果放在$ret_reg中返回
            self.code_generator

        else:
            if not node.children[-1].last_return and not isinstance(self.current_function.return_type_obj, UnitType):
                # 函数声明的最后一句不是返回值并且返回值类型不是无类型 -> 缺少返回语句
                self._report_error(f"非Unit类型函数 '{self.current_function.name}' 缺少返回语句，预期返回类型: {self.current_function.return_type_obj}", node.children[0])
            else:
                # 隐式添加返回语句
                self.code_generator.emit('RETURN', None, None, "$ret_reg")

            # 回填
            self.code_generator.backpatch(node.children[-1].attributes.next_list, self.code_generator.next_quad - 1);

        # 将临时存储的函数符号加入到全局作用域中
        self.symbolTable.exit_scope()
        self.symbolTable.insert(self.current_function)
        self.current_function = None

# ------------------ 表达式 -------------------------

    def _handle_Expression(self, node: ParseNode):

        if len(node.children) == 1:
            node.expr_res = node.children[0].expr_res
            node.attributes = node.children[0].attributes
            
        elif len(node.children) == 3 and node.children[1].symbol == 'Relop':
            # 布尔表达式计算
            left, op, right = node.children
            left_type = left.expr_res.type_obj
            right_type = right.expr_res.type_obj

            if not self._is_binop_compatible(op.value, left_type, right_type):
                self._report_error(f"操作符 {op.value} 不支持操作类型 {left_type} 和 {right_type}", op)
                node.expr_res = ExprResult(type_obj=UnitType(), is_rvalue=True)
                return
              
            node.expr_res = ExprResult(type_obj=BaseType('bool'), is_rvalue=True)

            # 生成中间代码
            expr_attrs = node.children[0].attributes
            rel_op = node.children[1].value
            add_expr_attrs = node.children[2].attributes

            temp = self.code_generator.new_temp()
            self.code_generator.emit(rel_op, expr_attrs.place, add_expr_attrs.place, temp)
            node.attributes.place = temp

    def _handle_FunctionExpressionBlock(self, node: ParseNode):

        node.expr_res = node.children[1].expr_res
        node.attributes.place = node.children[1].attributes.place

    def _handle_FunctionExpressionString(self, node: ParseNode):

        node.expr_res = node.children[-1].expr_res
        node.attributes.place = node.children[-1].attributes.place

    def _handle_SelectExpression(self, node: ParseNode):

        cond, if_block, else_block = node.children[1], node.children[3], node.children[5]

        # 检查条件类型必须是bool
        cond_type = cond.expr_res.type_obj

        if not isinstance(cond_type, BaseType) or cond_type.name != "bool":
            self._report_error("条件表达式必须是bool类型", cond)
            node.expr_res = ExprResult(type_obj=UnitType(), is_lvalue=True)
            return

        # 检查两个分支类型兼容
        if_block_type = if_block.expr_res.type_obj
        else_block_type = else_block.expr_res.type_obj
        if not self._is_type_compatible(if_block_type, else_block_type):
            self._report_error(f"if-else分支类型不匹配: {if_block.type_obj} vs {else_block.type_obj}", node)
            node.expr_res = ExprResult(type_obj=UnitType(), is_lvalue=True)
            return
        
        # 加入'ControlFLowMarker'将关系表达式求值运算更改为跳转
        C = node.children[2].attributes
        E1 = node.children[3].attributes
        E2 = node.children[5].attributes
        temp = self.code_generator.new_temp() # 存储表达式结果的位置
        self.code_generator.backpatch(C.true_list, self.code_generator.next_quad)
        self.code_generator.backpatch(C.false_list, self.code_generator.next_quad + 1)
        self.code_generator.emit('=', E1.place, None, temp)
        self.code_generator.emit('=', E2.place, None, temp)
        node.expr_res = ExprResult(type_obj=if_block_type, is_rvalue=True)
        node.attributes.place = temp

    def _handle_AddExpression(self, node: ParseNode):

        if len(node.children) == 1: # Itenm
            node.expr_res = node.children[0].expr_res
            node.attributes = node.children[0].attributes
            
        else: # 加减运算
            left, op, right = node.children
            left_type = left.expr_res.type_obj
            right_type = right.expr_res.type_obj

            if not self._is_binop_compatible(op.value, left_type, right_type):
                self._report_error(f"操作符 {op.value} 不支持操作类型 {left_type} 和 {right_type}", op)
                node.expr_res = ExprResult(type_obj=UnitType(), is_rvalue=True)
                return
            
            node.expr_res = ExprResult(type_obj=left_type, is_rvalue=True)

            # 生成中间代码
            add_expr_attrs = node.children[0].attributes
            add_op = node.children[1].value
            item_attrs = node.children[2].attributes

            temp = self.code_generator.new_temp()
            self.code_generator.emit(add_op, add_expr_attrs.place, item_attrs.place, temp)
            node.attributes.place = temp

    def _handle_Item(self, node: ParseNode):

        if len(node.children) == 1: # Factor
            node.expr_res = node.children[0].expr_res
            node.attributes = node.children[0].attributes

        else: # 乘除运算
            left, op, right = node.children
            left_type = left.expr_res.type_obj
            right_type = right.expr_res.type_obj

            if not self._is_binop_compatible(op.value, left_type, right_type):
                self._report_error(f"操作符 {op.value} 不支持操作类型 {left_type} 和 {right_type}", op)
                node.expr_res = ExprResult(type_obj=UnitType(), is_rvalue=True)
                return
            

            node.expr_res = ExprResult(type_obj=left_type, is_rvalue=True)

            # Item -> Item MulOp Factor
            item_attrs = node.children[0].attributes
            mul_op = node.children[1].value
            factor_attrs = node.children[2].attributes

            temp = self.code_generator.new_temp()
            self.code_generator.emit(mul_op, item_attrs.place, factor_attrs.place, temp)

            node.attributes.place = temp

    def _handle_Factor(self, node: ParseNode):


        first = node.children[0]

        if len(node.children) == 1: # Element
            node.expr_res = node.children[0].expr_res
            node.attributes = node.children[0].attributes

        if first.value == '[':    # 数组
            if len(node.children) == 2:  # 空数组
                node.expr_res = ExprResult(
                    type_obj=ArrayType(element_type=UnitType, size=0),
                    is_rvalue=True
                )
            else:
                element_exprs = node.children[1].expressions
                common_type = self._get_common_type(element_exprs)

                node.expr_res = ExprResult(
                    type_obj=ArrayType(element_type=common_type, size=len(element_exprs)),
                    is_rvalue=True
                )

        elif first.value == '(':  # 元组
            if len(node.children) == 2:  # 空元组
                node.expr_res = ExprResult(
                    type_obj=TupleType([]),
                    is_rvalue=True
                )
            else:
                tuple_members_type = [expr_res.type_obj for expr_res in node.children[1].expressions]
                node.expr_res = ExprResult(
                    type_obj=TupleType(tuple_members_type),
                    is_rvalue=True
                )

        elif first.value == '*':  # 解引用
            target_type = node.children[1].expr_res.type_obj
            if not isinstance(target_type, ReferenceType):
                self._report_error("只能解引用引用类型", node)
                node.expr_res = ExprResult(
                    type_obj=UnitType(),
                    is_rvalue=True
                )
                return
            
            deref_type = target_type.target_type
            node.expr_res = ExprResult(
                type_obj=deref_type,
                is_rvalue=True,
            )

        elif first.value == '&':  # 引用
            factor_node = node.children[-1]
            is_mut_ref = len(node.children) > 2 and node.children[1].value == 'mut'

            def _check_ref_avaliable(target_node: ParseNode, is_mut_ref: bool) -> bool:
                """检查引用是否有效"""
                var_name = target_node.expr_res.var_name
                var_state = self.reference_tracker.get(var_name) # 获取引用追踪状态

                if var_state:
                    # 规则1: 可变引用必须来自可变变量
                    if is_mut_ref and not var_state['is_mutable']:
                        self._report_error(f"不能从不可变变量'{var_name}'创建可变引用", target_node)
                        return False
                    # 规则2: 可变引用不能与其他引用共存
                    if is_mut_ref and (var_state['immutable_refs'] > 0 or var_state['mutable_ref']):
                        self._report_error(f"变量'{var_name}'已存在其他引用，无法创建可变引用", target_node)
                        return False
                    # 规则3: 不可变引用不能与可变引用共存
                    if not is_mut_ref and var_state['mutable_ref']:
                        self._report_error(f"变量'{var_name}'已存在可变引用，无法创建不可变引用", target_node)
                        return False

                    if is_mut_ref:
                        var_state['mutable_ref'] = True
                    else:
                        var_state['immutable_refs'] += 1
                else:
                    symbol = self.symbolTable.lookup(var_name)
                    if not symbol:
                        return False
                    
                    if is_mut_ref and symbol.type_obj.is_mutable == False:
                        self._report_error(f"不能从不可变变量'{var_name}'创建可变引用", node)
                        return False
                    self.reference_tracker[var_name] = {
                        'is_mutable': symbol.type_obj.is_mutable, 
                        'immutable_refs': 0 if is_mut_ref else 1, 
                        'mutable_ref': True if is_mut_ref else False
                    }

                return True
            
            if _check_ref_avaliable(factor_node, is_mut_ref):
                node.expr_res = ExprResult(
                    type_obj=ReferenceType(factor_node.expr_res.type_obj, is_mut_ref),
                    is_rvalue=True
                )
            else:
                node.expr_res = ExprResult(
                    type_obj=UnitType(),
                    is_rvalue=True
                )

    def _handle_ArrayElementList(self, node: ParseNode):

        # 收集所有表达式节点
        expressions = []
        for child in node.children:
            if child.symbol == "Expression":
                expressions.append(child.expr_res)
            elif child.symbol == "ArrayElementList":
                expressions.extend(child.expressions)

        node.expressions = expressions

    def _handle_TupleAssignInner(self, node: ParseNode):

        expressions = [node.children[0].expr_res]  # 第一个表达式类型

        if len(node.children) > 2 and node.children[2].symbol == "TupleElementList":
            expressions.extend(node.children[2].expressions)

        node.expressions = expressions

    def _handle_TupleElementList(self, node: ParseNode):

        expressions = []
        for child in node.children:
            if child.symbol == "Expression":
                expressions.append(child.expr_res)
            elif child.symbol == "TupleElementList":
                expressions.extend(child.expressions)

        node.expressions = expressions

    def _handle_Element(self, node: ParseNode):

        first_child = node.children[0]

        if first_child.symbol == "NUM": # 数字字面量 (NUM)
            node.expr_res = ExprResult(type_obj=BaseType('i32'), value=int(first_child.value), is_rvalue=True)
            node.attributes.place = node.children[0].value
        
        elif first_child.symbol == "Assignableidentifier": # 可赋值标识符 (变量/成员访问等)
            node.expr_res = first_child.expr_res
            node.expr_res.is_lvalue = False
            node.expr_res.is_rvalue = True
            node.attributes.place = node.children[0].attributes.place
        
        elif first_child.value == '(': # 括号表达式 (Expression)
            node.expr_res = node.children[1].expr_res
            node.attributes.place = node.children[1].attributes.place

        elif first_child.symbol == "ID" and node.children[1].value == "(" and node.children[-1].value == ")": # 函数调用 (ID + Arguments)

            func_name = node.children[0].value
            args_node = node.children[2] if node.children[2].symbol == "Arguments" else None

            # 查找函数符号
            func_symbol = self.symbolTable.lookup(func_name)
            if not func_symbol or not isinstance(func_symbol, FunctionSymbol):
                self._report_error(f"未定义的函数: {func_name}", first_child)
                node.expr_res = ExprResult(var_name=func_name, type_obj=UnitType(), is_rvalue=True)
                return
            
            # 检查参数匹配
            expected_params = func_symbol.parameters
            actual_args = args_node.arguments if args_node else []

            # 参数数量检查
            if len(actual_args) != len(expected_params):
                self._report_error(f"参数数量不匹配: 需要 {len(expected_params)} 个参数，得到 {len(actual_args)} 个", node)
                node.expr_res = ExprResult(var_name=func_name, type_obj=UnitType(), is_rvalue=True)
                return
            else:
                # 参数类型检查
                for i, (arg, param) in enumerate(zip(actual_args, expected_params)):
                    if not self._is_type_compatible(arg[i].type_obj, param.type_obj):
                        self._report_error(f"参数 {i+1} 类型不匹配: 需要 {param.type_obj}，得到 {arg[i].type_obj}", node)
                        node.expr_res = ExprResult(var_name=func_name, type_obj=UnitType(), is_rvalue=True)
                        return           

            # 函数调用中间代码生成
            for arg in actual_args:
                self.code_generator.emit('param', arg[1], None, f"param_{i}") # 生成param四元式
            self.code_generator.emit('call', func_name, len(actual_args), None)

            # 规定去特定的寄存器中取返回值
            return_type = func_symbol.return_type_obj
            temp = self.code_generator.new_temp()
            self.code_generator.emit('=', "$ret_reg", None, temp) # 从寄存器读取返回值
            node.expr_res = ExprResult(var_name=func_name, type_obj=return_type, is_rvalue=True)
            node.attributes.place = temp

    def _handle_Arguments(self, node: ParseNode):

        # 初始化参数列表
        arguments = []

        for child in node.children:
            if child.symbol == "Expression":
                arguments.append(
                    (child.expr_res, child.attributes.place)
                )
            
            elif child.symbol == "Arguments":
                arguments.extend(child.arguments)

        node.arguments = arguments

    def _handle_Assignableidentifier(self, node: ParseNode):

        if node.children[0].value == '*':  # 指针解引用
            target = node.children[1]

            # 检查目标是否为指针类型
            if not isinstance(target.type_obj, ReferenceType):
                self._report_error("只能解引用指针类型", node.children[0])
                node.expr_res = ExprResult(type_obj=UnitType(), is_lvalue=True)
                return
            
            node.expr_res = ExprResult(type_obj=target.type_obj.target_type, is_lvalue=True)

        else:  # 基础左值
            node.expr_res = node.children[0].expr_res  
            node.attributes = node.children[0].attributes
    
    def _handle_AssignableidentifierInner(self, node: ParseNode):

        if len(node.children) == 4:  # 数组索引
            array = node.children[0]
            index = node.children[2]

            array_type = array.expr_res.type_obj
            index_type = index.expr_res.type_obj
            
            # 检查是否为数组类型
            if not isinstance(array_type, ArrayType):
                self._report_error(f"非数组类型不能索引: {array_type}", node.children[1])
                node.expr_res = ExprResult(
                    type_obj=UnitType(),
                    is_lvalue=True
                )
                return
            
            # 检查索引是否为整数
            if not isinstance(index_type, BaseType) or index_type.name not in ("i32"):
                self._report_error("数组索引必须是整数类型", index)
                node.expr_res = ExprResult(
                    type_obj=UnitType(),
                    is_lvalue=True
                )
                return           
            # 检查索引是否在范围内
            index_value=node.children[2].expr_res.value
            if index_value:
                if isinstance(index_value, int):
                    if(index_value<0 or index_value >= array_type.size):
                        self._report_error(f"数组索引越界: 最大 {array_type.size-1}，实际 {index_value}", node.children[2])
                    else:
                        self._report_error(f"数组索引必须是整数，实际:{index_value}", node.children[2])

            # 传递数组信息
            type_obj = array_type.element_type
            type_obj.is_mutable = array_type.is_mutable
            node.expr_res = ExprResult(
                type_obj=type_obj,
                is_lvalue=True,
                index_expr=index.expr_res
            )

        elif len(node.children) == 3:  # 元组成员
            struct = node.children[0]                   # 
            member_index = int(node.children[2].value)  # 访问索引

            # 检查是否为元组类型
            if not isinstance(struct.expr_res.type_obj, TupleType):
                self._report_error(f"非复合类型不能访问成员: {struct.expr_res.type_obj}", node)
                node.expr_res = ExprResult(
                    type_obj=UnitType(),
                    is_lvalue=True
                )
                return
            
            # 检查成员索引有效性
            if member_index >= len(struct.expr_res.type_obj.members):
                self._report_error(f"成员索引越界: 最大 {len(struct.expr_res.type_obj.members)-1}，实际 {member_index}", node.children[2])
                node.expr_res = ExprResult(
                    type_obj=UnitType(),
                    is_lvalue=True
                )
                return

            type_obj = struct.expr_res.type_obj.members[member_index]
            type_obj.is_mutable = struct.expr_res.type_obj.is_mutable
            node.expr_res = ExprResult(
                var_name=f"{struct.expr_res.var_name}[{member_index}]",
                type_obj=type_obj,
                is_lvalue=True,
                member_index=member_index
            )

        else:  # 普通标识符    
            # 检查变量是否已经声明
            if not (symbol := self.symbolTable.lookup((id_node := node.children[0]).value)):
                self._report_error(f"未声明的变量: {id_node.value}", id_node)
                node.expr_res = ExprResult(var_name=id_node.value, type_obj=UnitType(), is_lvalue=True)
                return
            
            node.expr_res = ExprResult(var_name=id_node.value, type_obj=symbol.type_obj, is_lvalue=True)
            node.attributes.place = node.children[0].value # 标识符名称
                
    def _handle_Relop(self, node: ParseNode):

        node.value = node.children[0].value

    def _handle_AddOp(self, node: ParseNode):

        node.value = node.children[0].value
        
    def _handle_MulOp(self, node: ParseNode):
    
        node.value = node.children[0].value

# -------------------- 语句块 -------------------------

    def _handle_Block(self, node: ParseNode):
 
        if len(node.children) == 3:
            node.attributes.next_list = node.children[1].attributes.next_list
            node.last_return = node.children[1].last_return

    def _handle_StatementString(self, node: ParseNode):
 
        if len(node.children) == 3:
            L1 = node.children[0].attributes
            M = node.children[1].attributes
            S = node.children[2].attributes
            self.code_generator.backpatch(L1.next_list, M.quad_index)
            node.attributes.next_list = S.next_list
            node.last_return = node.children[-1]
        else:
            S = node.children[0].attributes
            node.attributes.next_list = S.next_list
            node.last_return = node.children[-1]

    def _handle_Statement(self, node: ParseNode):
       
        node.attributes = node.children[0].attributes
        if node.children[0].symbol == 'ReturnStatement':
            node.last_return = True

    def _handle_ReturnStatement(self, node: ParseNode):
   
        declared_return_type = self.current_function.return_type_obj
        actual_return_type = node.children[1].expr_res.type_obj if len(node.children) == 3 else UnitType()

        if not self._is_type_compatible(actual_return_type, declared_return_type):
            self._report_error(f"返回值类型不匹配: 声明返回 {declared_return_type}, 实际返回 {actual_return_type}", node)

        if len(node.children) == 3:
            result_place = node.children[1].attributes.place
            self.code_generator.emit('RETURN', result_place, None, "$ret_reg") # 将计算结果写在寄存器中
        else:
            self.code_generator.emit('RETURN', None, None, "$ret_reg")

    def _handle_AssignStatement(self, node: ParseNode):
        
        lvalue_node, rvalue_node = node.children[0], node.children[2]

        lvalue_type = lvalue_node.expr_res.type_obj
        rvalue_type = rvalue_node.expr_res.type_obj

        if isinstance(lvalue_type, UnitType):
            return

        lvalue_name = lvalue_node.expr_res.var_name
        is_mutable = lvalue_node.expr_res.type_obj.is_mutable        

        # 检查左值是否为可赋值
        if is_mutable == False:
            self._report_error(f"不能给不可变变量赋值: {lvalue_name}", lvalue_node)
            return
        
        # 检查右值是否可以赋值
        if isinstance(rvalue_type, UninitializedType):
            self._report_error("该变量未初始化，不能作为右值使用", rvalue_node)
            return
        
        elif isinstance(rvalue_type, UnitType):
            self._report_error("右值表达式没有类型(unit 类型)，不能作为右值使用", rvalue_node)
            return

        if lvalue_name in self.pending_type_inference:
            symbol = self.symbolTable.lookup(lvalue_name)
            symbol.type_obj = rvalue_type
            del self.pending_type_inference[lvalue_name]
        else:
            if not self._is_type_compatible(lvalue_type, rvalue_type):
                self._report_error(f"类型不匹配: 不能将 {rvalue_type} 赋值给 {lvalue_type}", node)
                return
            
        lvalue = node.children[0].attributes.place
        expr_attrs = node.children[2].attributes
        self.code_generator.emit('=', expr_attrs.place, None, lvalue)

# ------------------- 控制流 ----------------------

    def _handle_ControlFLowMarker(self, node: ParseNode):
        expr_res_place = f"t{self.code_generator.temp_counter - 1}"
        node.attributes.true_list = [self.code_generator.next_quad]
        node.attributes.false_list = [self.code_generator.next_quad + 1]
        self.code_generator.emit("jnz", expr_res_place, None, None) # 为真跳转
        self.code_generator.emit("j", None, None, None)             # 为假跳转
        
    def _handle_LoopMarker(self, node: ParseNode):
        """处理循环标志"""
        # TODO: Loop语句还要规定一个break返回值存放的位置
        loop_info = {
            "begin_quad" : self.code_generator.next_quad, # 记录起始位置
            "break_list": [],                             # 用于回填
        }
        self.loop_stack.append(loop_info)
        self.symbolTable.enter_scope(f"Loop_{len(self.loop_stack)}")

    def _handle_ReDoMarker(self, node: ParseNode):
        node.attributes.quad_index = self.code_generator.next_quad

    def _handle_BeginMarker(self, node: ParseNode):
        node.attributes.quad_index = self.code_generator.next_quad

    def _handle_EndMarker(self, node: ParseNode):
        node.attributes.next_list = [self.code_generator.next_quad]
        self.code_generator.emit('j', None, None, None)
    
    def _handle_IfStatement(self, node: ParseNode):
        cond_expr = node.children[1].expr_res   # 条件表达式
        has_else = len(node.children) > 5       # 是否有else分支

        # 检查条件表达式
        cond_type = cond_expr.type_obj
        if not isinstance(cond_type, BaseType) or cond_type.name != "bool":
            self._report_error("if条件必须是bool类型", node.children[1])
            return
        
        # 中间代码生成
        C = node.children[2].attributes  # 控制流布尔运算标记
        M1 = node.children[3].attributes # Begin标记
        block1_attrs = node.children[4].attributes

        if has_else:
            N = node.children[5].attributes  # End标记
            M2 = node.children[7].attributes # Begin标记
            block2_attrs = node.children[8].attributes
            self.code_generator.backpatch(C.true_list, M1.quad_index)
            self.code_generator.backpatch(C.false_list, M2.quad_index)
            node.attributes.next_list = self.code_generator.merge_lists(block1_attrs.next_list, N.next_list, block2_attrs.next_list)
        else:
            self.code_generator.backpatch(C.true_list, M1.quad_index)
            node.attributes.next_list = self.code_generator.merge_lists(C.false_list, block1_attrs.next_list)

    def _handle_CirculateStatement(self, node: ParseNode):
        node.attributes = node.children[1].attributes
        self.symbolTable.exit_scope()

    def _handle_WhileStatement(self, node: ParseNode):
        cond_expr_res = node.children[2].expr_res
    
        # 检查条件表达式
        cond_expr_type = cond_expr_res.type_obj
        if not isinstance(cond_expr_type, BaseType) or cond_expr_type.name != "bool":
            self._report_error("while条件必须是bool类型", node.children[2])
            return
        
        # 中间代码生成
        M1 = node.children[1].attributes
        C = node.children[3].attributes
        M2 = node.children[4].attributes
        S1 = node.children[5].attributes
        self.code_generator.backpatch(S1.next_list, M1.quad_index)
        self.code_generator.backpatch(C.true_list, M2.quad_index)
        loop_info = self.loop_stack.pop()
        node.attributes.next_list = self.code_generator.merge_lists(C.false_list, loop_info['break_list'])
        self.code_generator.emit('j', None, None, M1.quad_index)

    def _handle_IterableStructure(self, node: ParseNode):
        if len(node.children) == 3: # 范围表达式 `a..b`
            start_expr = node.children[0].expr_res
            end_expr = node.children[2].expr_res
            # 检查两个表达式是否为整数类型
            if not (isinstance(start_expr.type_obj, BaseType) and isinstance(end_expr.type_obj, BaseType) and
                    start_expr.type_obj.name == 'i32' and end_expr.type_obj.name == 'i32'):
                self._report_error("范围表达式必须使用整数", node)
                
            # 创建 RangeType
            type_obj = RangeType(
                element_type=start_expr.type_obj,
                start=node.children[0].attributes.place,
                end=node.children[2].attributes.place,
            )
            node.expr_res = ExprResult(type_obj=type_obj)
        else:
            element = node.children[0].expr_res
            if not isinstance(element.type_obj, ArrayType):
                self._report_error("不可迭代的类型", node)
            node.expr_res = ExprResult(type_obj=element.type_obj)

    def _handle_ForExpression(self, node: ParseNode):
        # 确保可迭代结构已被正确处理
        iterable = node.children[2].expr_res
        if not hasattr(iterable, 'type_obj'):
            self._report_error("无效的可迭代结构", node.children[3])
            return
        
        # 检查可迭代对象是否为范围或数组类型
        if not (isinstance(iterable.type_obj, (ArrayType, RangeType))):
            self._report_error("for循环只能迭代数组或范围", node.children[3])
            return
        
        # 添加变量
        var_decl_node = node.children[0]
        var_symbol = VariableSymbol(name=var_decl_node.var_name, type_obj=iterable.type_obj.element_type)
        self.symbolTable.insert(var_symbol)
        
        # 初始化迭代器临时变量
        temp_iterator = self.code_generator.new_temp()
        if isinstance(iterable.type_obj, RangeType):
            self.code_generator.emit('=', iterable.type_obj.start, None, temp_iterator)
        elif isinstance(iterable.type_obj, ArrayType):
            self.code_generator.emit('=', 0, None, temp_iterator)

        # 循环开始位置
        node.attributes.quad_index = self.code_generator.next_quad
        node.attributes.true_list = [self.code_generator.next_quad]
        node.attributes.false_list = [self.code_generator.next_quad + 1]

        # 条件检查
        end_condition = (
            iterable.type_obj.end if isinstance(iterable.type_obj, RangeType)
            else iterable.type_obj.size
        )
        self.code_generator.emit('<', temp_iterator, end_condition, None) # 小于是True分支
        self.code_generator.emit('j', None, None, None)                   # 大于等于是False分支

        # 赋值循环变量
        self.code_generator.emit('=', temp_iterator, None, var_decl_node.var_name)

        # 迭代器步进
        step = iterable.type_obj.step if isinstance(iterable.type_obj, RangeType) else 1
        self.code_generator.emit('+', temp_iterator, step, temp_iterator)

    def _handle_ForStatement(self, node: ParseNode):
        C = node.children[1].attributes
        M1 = node.children[2].attributes
        S1 = node.children[3].attributes

        self.code_generator.backpatch(C.true_list, M1.quad_index)
        loop_info = self.loop_stack.pop()
        node.attributes.next_list = self.code_generator.merge_lists(C.false_list, S1.next_list, loop_info['break_list'])
        self.code_generator.emit('j', None, None, C.quad_index) # 跳转到开始

    def _handle_LoopStatement(self, node: ParseNode):
        S = node.children[1].attributes
        loop_info = self.loop_stack.pop()
        self.code_generator.backpatch(S.next_list, loop_info['begin_quad'])
        self.code_generator.emit('j', None, None, loop_info['begin_quad']) # 无条件跳转

        node.attributes.next_list = loop_info['break_list']                # 记录待回填四元式

    def _handle_BreakStatement(self, node: ParseNode):
        if not self.loop_stack:
            self._report_error("break语句必须在循环内使用", node)
            return

        # TODO: Loop循环中还要判断所有的break表达式类型是否一致
        if len(node.children) > 2:  # break带返回值
            # TODO: break后面的表达式必须可以求值
            expr = node.children[1]
            node.return_type = expr.type_obj

        quad_index = self.code_generator.emit('j', None, None, None)

        current_loop = self.loop_stack[-1]
        current_loop["break_list"].append(quad_index)

    def _handle_ContinueStatement(self, node: ParseNode):
        if not hasattr(self, 'loop_stack') or not self.loop_stack:
            self._report_error("continue语句必须在循环内使用", node)
            return

        current_loop = self.loop_stack[-1]
        self.code_generator.emit('j', None, None, current_loop['begin_quad'])
        

    # ---------- 辅助检查工具方法 ----------
    def _report_error(self, message: str, node: ParseNode):
        """记录错误信息"""
        error = SemanticError(message=message, line=node.line, column=node.column)
        self.errors.append(error)
        logger.error(error)

    def _update_position(self, node: ParseNode):
        """更新节点的位置 用于错误信息输出"""
        if len(node.children) != 0:
            first_child = node.children[0]
            node.line = first_child.line
            node.column = first_child.column

    def _get_common_type(self, expressions: List[ExprResult]) -> Type:
        """获取表达式列表的共同类型"""
        if not expressions:
            return UnitType()

        first_type = expressions[0].type_obj
        for expr in expressions[1:]:
            if expr.type_obj != first_type:
                self._report_error(
                    f"数组元素类型不一致: {first_type} 和 {expr.type_obj}",
                    expr.line, expr.column
                )
        return first_type

    def _is_type_compatible(self, actual: Type, expected: Type) -> bool:
        # 1. 未初始化类型
        if isinstance(actual, UninitializedType):
            logger.info(f"❌  未初始化类型 {actual.inner_type} {expected}")
            return self._is_type_compatible(actual.inner_type, expected)
        
        if isinstance(expected, UninitializedType):
            return self._is_type_compatible(actual, expected.inner_type)
        
        # 2. 完全同类匹配（引用对象同类型）
        if type(actual) != type(expected):
            return False
        
        # 3. Unit 类型
        if isinstance(actual, UnitType) and isinstance(expected, UnitType):
            return True
        
        # 4. 基础类型（i32, bool, void 等）
        if isinstance(actual, BaseType) and isinstance(expected, BaseType):
            return actual.name == expected.name
        
        # 5. 数组类型：元素类型兼容且长度相同
        if isinstance(actual, ArrayType) and isinstance(expected, ArrayType):
            return (actual.size == expected.size and
                    self._is_type_compatible(actual.element_type, expected.element_type))
        
        # 6. 元组类型：成员数量相同且对应成员类型兼容
        if isinstance(actual, TupleType) and isinstance(expected, TupleType):
            if len(actual.members) != len(expected.members):
                return False
            return all(self._is_type_compatible(a, e) for a, e in zip(actual.members, expected.members))
        
        # 7. 引用类型：目标类型相同即可
        if isinstance(actual, ReferenceType) and isinstance(expected, ReferenceType):
            return self._is_type_compatible(actual.target_type, expected.target_type)
        
        return False
        
    def _is_binop_compatible(self, op: str, left_type: Type, right_type: Type) -> bool:
        """检查二元运算的操作数类型是否兼容"""
        # 1. 处理未初始化类型
        if isinstance(left_type, UninitializedType):
            left_type = left_type.inner_type
        if isinstance(right_type, UninitializedType):
            right_type = right_type.inner_type

        # 2. 根据运算符分类处理
        if op in {'+', '-', '*', '/', '%'}:  # 算术运算
            return (isinstance(left_type, BaseType) and isinstance(right_type, BaseType) and
                    left_type.name in {'i32'} and left_type.name == right_type.name)
        
        elif op in {'<', '>', '<=', '>=', '==', '!='}:  # 比较运算
            # 允许数值比较，或同类型比较（如结构体判等）
            return (self._is_type_compatible(left_type, right_type) and
                    (isinstance(left_type, BaseType) or  # 数值/布尔比较
                     isinstance(left_type, ReferenceType)))  # 引用判等
        
        elif op in {'&&', '||'}:  # 逻辑运算
            # 要求两边都是布尔类型
            return (isinstance(left_type, BaseType) and 
                    isinstance(right_type, BaseType) and
                    left_type.name == 'bool' and
                    right_type.name == 'bool')
        
        return False

    def get_errors(self):
        return self.errors
    
    def get_quads(self):
        return self.code_generator.quads
    