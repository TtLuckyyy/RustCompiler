"""语法分析器"""
from collections import namedtuple, defaultdict
from compiler_lexer import Token
from compiler_parser_node import ParseNode
from compiler_rust_grammar import RUST_GRAMMAR, TEST_GRAMMAR, LEFT_RECURSION_GRAMMAR
from compiler_semantic_checker import SemanticChecker
from compiler_logger import logger
from enum import Enum

# 元组形式的项目元素 Hashable
LR1Item = namedtuple('LR1Item', ['prod_lhs', 'prod_rhs', 'dot_pos', 'lookahead'])

class Parser:
    def __init__(self):
        self._first_cache = {} # first集缓存
        
    def _initialize_grammar(self):
        """初始化语法"""
        self.terminals = set(self.grammar.get('terminals', []))         # 终结符
        self.non_terminals = set(self.grammar.get('non_terminals', [])) # 非终结符
        self.productions = defaultdict(list)                            # 通过LHS查询产生式
        self.prod_by_index = {}                                         # 通过索引查找产生式
        self.start_symbol = self.grammar['start_symbol']                # 起始符号

        # 预处理产生式
        for idx, prod in enumerate(self.grammar['productions']):
            lhs = prod['prod_lhs']  # 产生式左侧
            rhs = prod['prod_rhs']  # 产生式右侧
            self.non_terminals.add(lhs)
            self.productions[lhs].append({
                'rhs': rhs,
                'index':idx
            })
            self.prod_by_index[idx] = {
                'lhs': lhs,
                'rhs': rhs
            }
        
        # 输出调试信息：处理后的语法
        self._log_grammar_info()

    def eliminate_left_recursion(self, grammar):
        """
        消除文法的直接和间接左递归
        注: 已经不再需要这个函数
        """
        logger.info("Starting left recursion elimination...")
        original_count = len(grammar['productions'])
        logger.info(f"Original production count: {original_count}")

        prod_dict = defaultdict(list)
        for prod in grammar['productions']:
            prod_dict[prod['prod_lhs']].append(prod['prod_rhs'])
        
        non_terminals = list(prod_dict.keys())
        new_productions = []

        for i in range(len(non_terminals)):
            Ai = non_terminals[i]
            for j in range(i):
                Aj = non_terminals[j]
                update_rules = []
                for rhs in prod_dict[Ai]:
                    if len(rhs) == 0:
                        update_rules.append(rhs)
                    elif rhs[0] == Aj:
                        # Ai -> Aj γ, 替换Aj的产生式
                        for gamma in prod_dict[Aj]:
                            update_rules.append(gamma + rhs[1:])
                    else:
                        update_rules.append(rhs)
                prod_dict[Ai] = update_rules

            # 消除直接左递归
            direct_left = []
            non_left = []

            for rhs in prod_dict[Ai]:
                if len(rhs) == 0:
                    non_left.append(rhs)
                elif rhs[0] == Ai:
                    direct_left.append(rhs[1:])
                else:
                    non_left.append(rhs)
            
            if direct_left:
                Ai_prime = Ai + "_tail"
                for beta in non_left:
                    new_productions.append({
                        'prod_lhs': Ai,
                        'prod_rhs': beta + [Ai_prime]
                    })
                for alpha in direct_left:
                    new_productions.append({
                        'prod_lhs': Ai_prime,
                        'prod_rhs': alpha + [Ai_prime]
                    })
                new_productions.append({
                    'prod_lhs': Ai_prime,
                    'prod_rhs': []
                })
            else:
                for rhs in prod_dict[Ai]:
                    new_productions.append({
                        'prod_lhs': Ai,
                        'prod_rhs': rhs
                    })

        grammar['productions'] = new_productions
        new_count = len(grammar['productions'])
        logger.info(f"Left recursion elimination completed.")
        logger.info(f"New production count: {new_count}")
        return grammar

    def closure(self, items):
        """
        计算项目集的闭包(扩展当前项目集)
        核心思想：将所有可能通过 非终结符转移 触发的子项目纳入当前状态。
        :param items: 项目集 [{'production': 产生式, 'dot_pos': 位置, 'lookahead': 向前看符号}]
        :return: 闭包后的项目集 (LR1Item)
        """
        # 将项目闭包转换为集合以便于快速查看生成的新项目是否已经存在
        closure_set = set()
        
        for item in items:
            if isinstance(item, dict):
                closure_set.add(self._dict_to_lr1_item(item))
            else:
                closure_set.add(item)

        changed = True

        while changed:
            changed = False
            for item in list(closure_set):
                # [A -> α.Bβ, a]
                # 如果点在产生式的右侧，且点后还有符号
                if item.dot_pos < len(item.prod_rhs):
                    B = item.prod_rhs[item.dot_pos]
                    # 对于每个产生式B -> γ，添加到闭包中
                    if B in self.non_terminals:
                        beta = item.prod_rhs[item.dot_pos+1:] # β
                        # 计算 FIRST(βa)
                        lookaheads = self.first(beta + (item.lookahead,)) if beta else {item.lookahead}
                        # 添加新项目
                        for prod in self.productions[B]:
                            for la in lookaheads:
                                new_item = LR1Item(
                                    prod_lhs=B,
                                    prod_rhs=tuple(prod['rhs']),
                                    dot_pos=0,
                                    lookahead=la
                                )
                                if new_item not in closure_set:
                                    closure_set.add(new_item)
                                    changed = True

        # 排序逻辑：按 prod_lhs → prod_rhs → dot_pos → lookahead 的优先级
        sorted_items = sorted(
            closure_set,
            key=lambda x: (x.prod_lhs, x.prod_rhs, x.dot_pos, x.lookahead)
        )
        return tuple(sorted_items)
    
    def go(self, items, symbol):
        """
        状态转移函数
        :param items: 项目集
        :param symbol: 符号
        :return: 计算转移后的项目集(状态)
        """
        new_items = set()

        for item in items:
            # 当前的项目Item
            current  =self._dict_to_lr1_item(item) if isinstance(item, dict) else item
            if current.dot_pos < len(current.prod_rhs) and current.prod_rhs[current.dot_pos] == symbol:
                new_item = LR1Item(
                    prod_lhs=current.prod_lhs,
                    prod_rhs=current.prod_rhs,
                    dot_pos=current.dot_pos + 1,  # 移动点位置
                    lookahead=current.lookahead
                )
                new_items.add(new_item)

        return self.closure(new_items) if new_items else None
    
    def first(self, symbols, visited=None):
        """
        计算符号串的FIRST集合
        :param symbols: 符号串
        :return: FIRST集合
        """
        if visited is None:
            visited = set()

        cache_key = tuple(symbols)
        if cache_key in self._first_cache:
            return self._first_cache[cache_key].copy()
        
        # 检测循环依赖
        if cache_key in visited:
            return set()
        visited.add(cache_key)

        first_set = set()

        # 处理空串''
        if not symbols:
            first_set.add('')
            return first_set
        
        for symbol in symbols:
            # 处理终结符
            if symbol in self.terminals or symbol == '$':
                first_set.add(symbol)
                first_set.discard('') # 终结符会阻塞ε传播
                break
            
            # 处理非终结符
            elif symbol in self.non_terminals:
                # ['A']
                has_epsilon = False # 假设FIRST(A)不存在ε 用于拦截ε
                for prod in self.productions.get(symbol, []):
                    # A -> ε
                    if not prod['rhs']:
                        first_set.add('')
                        has_epsilon = True
                        continue
                    
                    # 递归计算产生式右部的FIRST集
                    # A -> B C D
                    sub_first = self.first(prod['rhs'], visited.copy())
                    first_set.update(sub_first - {''})

                    if '' in sub_first:
                        has_epsilon = True       
                                
                # 若FIRST(A)的不包含ε 需要将ε移除并且需要跳出循环
                if not has_epsilon:
                    first_set.discard('')
                    break    
            
            # 未知类型
            else :
                raise ValueError(f"未知符号类型: {symbol}")
            
        self._first_cache[cache_key] = first_set
        return first_set
    
    def build_parse_table(self, grammar):
        """
        构建LR(1)分析表(ACTION表和GOTO表)
        :return: 分析表
        """
        self.grammar = grammar
        self._initialize_grammar()

        logger.debug("🛠️ 开始构建LR(1)分析表...")

        # 初始化分析表
        self.action_table = defaultdict(dict)
        self.goto_table = defaultdict(dict)
        self.states = []

        # 生成初始项目集闭包
        start_prod = self.productions[self.start_symbol][0]
        initial_item = LR1Item(
            prod_lhs=self.start_symbol,
            prod_rhs=tuple(start_prod['rhs']),
            dot_pos=0,
            lookahead='$'
        )
        
        # 状态
        initial_state = self.closure([initial_item]) # tuple(LR1Item)
        self.states = [initial_state]
        queue = [initial_state]
        state_ids = {initial_state: 0}

        # 记录初始状态
        self._log_state_items(0, initial_state)

        while queue:
            current_state = queue.pop(0)
            current_id = state_ids[current_state] # 获取状态编号
            logger.debug(f"当前处理状态ID:{current_id}")

            # 遍历所有符号
            symbols = self.terminals.union(self.non_terminals)
            for idx, symbol in enumerate(symbols):
                new_state = self.go(current_state, symbol)
                if new_state and len(new_state) > 0:
                    if new_state not in state_ids:
                        new_state_id = len(self.states)
                        state_ids[new_state] = new_state_id
                        self.states.append(new_state)
                        queue.append(new_state)

                        # 记录新状态的项目集
                        self._log_state_items(new_state_id, new_state)

                    # 记录转移动作
                    new_state_id = state_ids[new_state]
                    if symbol in self.terminals:
                        # 终结符 ACTION表
                        self.action_table[current_id][symbol] = ('shift', new_state_id)
                    else:
                        # 非终结符 GOTO表
                        self.goto_table[current_id][symbol] = new_state_id
            
            # 检查规约项
            for item in current_state:
                if item.dot_pos == len(item.prod_rhs):
                    if item.prod_lhs == self.start_symbol and item.lookahead == '$':
                        # 接受
                        self.action_table[current_id]['$'] = ('accept',)
                    else:
                        # 规约
                        for prod in self.productions[item.prod_lhs]:
                            if tuple(prod['rhs']) == item.prod_rhs:
                                self.action_table[current_id][item.lookahead] = ('reduce', prod['index'])
                                break

        logger.debug("✅ 分析表构建完成（共%d个状态）" % len(self.states))
        return self.action_table, self.goto_table

    def analyse(self, tokens, checker: SemanticChecker = None):
        """
        执行LR(1)语法分析
        :param tokens: Token对象列表
        :param checker: 语义检查器(是否在语法分析过程中进行语义分析)

        :return: (语法分析树根节点, 分析过程信息)
        """
        analysis_details = []         # 分析过程信息
        state_stack = [0]             # 状态栈，初始状态为0
        node_stack = []               # 节点栈
        idx = 0                       # 当前token指针
        token_stream = list(tokens)   # token流
        
        while True:
            state = state_stack[-1]
            current_token = token_stream[idx]

            # 记录当前状态
            step_info = {
                "stack": list(state_stack),
                "node_stack": [str(n) for n in node_stack],
                "input": [str(t) for t in token_stream[idx:]],
                "action": "",
                "production": ""
            }
            
            # 查ACTION表
            action = self.action_table[state].get(current_token.type.value)
            if not action:
                expected = sorted(self.action_table[state].keys())
                context = token_stream[max(0, idx-2):idx+1]
                raise SyntaxError(
                    f"语法错误（第{current_token.line}行, 第{current_token.column}列）\n"
                    f"意外Token: {current_token}\n"
                    f"期望: {expected}\n"
                    f"上下文: {context}"
                )
            
            # 执行动作
            if action[0] == 'shift':
                step_info["action"] = f"移入: {current_token} -> 状态{action[1]}"

                # 创建终结符节点
                new_node = ParseNode(symbol=current_token.type.value, children=None, token=current_token)
                node_stack.append(new_node)
                idx += 1

                # ACTION转移
                action_state = action[1]
                state_stack.append(action_state)

            elif action[0] == 'reduce':
                prod_index = action[1]
                prod = self.prod_by_index[prod_index]
                lhs = prod['lhs']
                rhs_len = len(prod['rhs'])
                
                step_info["production"] = f"{lhs} → {' '.join(prod['rhs']) if prod['rhs'] else 'ε' }" 
                step_info["action"] = f"规约: 应用产生式 {prod_index}"
                
                children = []
                if rhs_len > 0:
                    state_stack = state_stack[:-rhs_len]
                    children = node_stack[-rhs_len:]
                    node_stack = node_stack[:-rhs_len]
                
                # 创建非终结符节点
                new_node = ParseNode(symbol=lhs, children=children)
                if checker:
                    checker.on_reduce(node=new_node)
                node_stack.append(new_node)

                # GOTO转移
                goto_state = self.goto_table[state_stack[-1]].get(lhs)
                if goto_state is None:
                    raise SyntaxError(f"无效GOTO：状态{state_stack[-1]}遇到{lhs}")
                state_stack.append(goto_state)

            elif action[0] == 'accept':
                step_info["action"] = "接受: 分析完成"
                break
            
            else:
                raise SyntaxError(f"无效动作: {action}") 

            analysis_details.append(step_info)
            
        return node_stack[0], analysis_details
    
    def _dict_to_lr1_item(item_dict: dict) -> LR1Item:
        """
            将字典形式的项目转换为 LR1Item 对象
        Args:
            item_dict: 必须包含键 'production'（含 'lhs' 和 'rhs'）、'dot_pos' 和 'lookahead'。
        Returns:
            LR1Item: 转换后的命名元组对象。
        """
        # 提取并验证字段
        production = item_dict['production']
        lhs = production['lhs']
        rhs = tuple(production['rhs'])  # 转换为元组保证可哈希
        dot_pos = item_dict['dot_pos']
        lookahead = item_dict['lookahead']

        return LR1Item(prod_lhs=lhs, prod_rhs=rhs, dot_pos=dot_pos, lookahead=lookahead)

    def _log_grammar_info(self):
        """记录语法分析详细信息"""
        logger.debug("🔍 语法规则分析结果")
        logger.debug(f"起始符号: \033[1m{self.start_symbol}\033[0m")

        # 符号统计
        logger.debug(f"终结符({len(self.terminals)}): {', '.join(sorted(self.terminals))}")
        logger.debug(f"非终结符({len(self.non_terminals)}): {', '.join(sorted(self.non_terminals))}")

        # 产生式表格输出
        logger.debug("📜 产生式规则:")
        max_lhs_len = max(len(lhs) for lhs in self.productions) if self.productions else 0
        for lhs in sorted(self.productions.keys()):
            for prod in self.productions[lhs]:
                rhs_str = ' '.join(prod['rhs']) if prod['rhs'] else "ε"
                logger.debug(f"  {lhs.ljust(max_lhs_len)} → {rhs_str} \033[90m# {prod['index']}\033[0m")

    def _log_state_items(self, state_id, state):
        """记录状态中的项目集"""
        logger.debug(f"🔍 状态 {state_id} 项目集:")
        for item in sorted(state, key=lambda x: (x.prod_lhs, x.prod_rhs, x.dot_pos)):
            # 构建带点的产生式表示
            rhs = list(item.prod_rhs)
            rhs.insert(item.dot_pos, '•')
            production = f"{item.prod_lhs} → {' '.join(rhs) if rhs else 'ε'}"

            # 格式化输出
            logger.debug(f"  {production.ljust(40)} , {item.lookahead}")

if __name__ == "__main__":
    class TestTokenType(Enum):
        ID = 'id'
        EQUAL = '='
        END = '$'
    
    tokens = [
        Token(TestTokenType.ID, value="x", line=1, column=1),
        Token(TestTokenType.EQUAL, value="=", line=1, column=3),
        Token(TestTokenType.ID, value="y", line=1, column=5),
        Token(TestTokenType.END)
    ]
    parser_test = Parser(TEST_GRAMMAR)
    parser_test.parse(tokens)
    # 消除左递归测试
    parser_left_recursion = Parser(LEFT_RECURSION_GRAMMAR)
    pass


