"""Parser for Rust-like Language (重构版)"""
from collections import namedtuple, defaultdict
from compiler_lexer import Token
from compiler_parser_node import ParseNode
from compiler_rust_grammar import RUST_GRAMMAR, TEST_GRAMMAR, LEFT_RECURSION_GRAMMAR
from compiler_semantic_checker import SemanticChecker
from compiler_logger import logger
from enum import Enum

# 定义LR1项目
LR1Entry = namedtuple('LR1Entry', ['lhs', 'rhs', 'dot', 'la'])

class SyntaxParser:
    def __init__(self):
        self._first_cache = dict()

    def _setup_grammar(self):
        """Grammar preprocessing and index building"""
        self.terminal_set = set(self.grammar.get('terminals', []))
        self.nonterminal_set = set(self.grammar.get('non_terminals', []))
        self.prod_map = defaultdict(list)
        self.prod_idx_map = dict()
        self.start = self.grammar['start_symbol']

        for idx, prod in enumerate(self.grammar['productions']):
            left = prod['prod_lhs']
            right = prod['prod_rhs']
            self.nonterminal_set.add(left)
            self.prod_map[left].append({'rhs': right, 'idx': idx})
            self.prod_idx_map[idx] = {'lhs': left, 'rhs': right}

        self._print_grammar()

    def remove_left_recursion(self, grammar):
        """Remove direct and indirect left recursion (for reference)"""
        logger.info("Removing left recursion...")
        prod_dict = defaultdict(list)
        for prod in grammar['productions']:
            prod_dict[prod['prod_lhs']].append(prod['prod_rhs'])
        nonterms = list(prod_dict.keys())
        new_prods = []
        for i, Ai in enumerate(nonterms):
            for j in range(i):
                Aj = nonterms[j]
                updated = []
                for rhs in prod_dict[Ai]:
                    if rhs and rhs[0] == Aj:
                        for gamma in prod_dict[Aj]:
                            updated.append(gamma + rhs[1:])
                    else:
                        updated.append(rhs)
                prod_dict[Ai] = updated
            lefts, rights = [], []
            for rhs in prod_dict[Ai]:
                if rhs and rhs[0] == Ai:
                    lefts.append(rhs[1:])
                else:
                    rights.append(rhs)
            if lefts:
                Ai_ = Ai + "_tail"
                for beta in rights:
                    new_prods.append({'prod_lhs': Ai, 'prod_rhs': beta + [Ai_]})
                for alpha in lefts:
                    new_prods.append({'prod_lhs': Ai_, 'prod_rhs': alpha + [Ai_]})
                new_prods.append({'prod_lhs': Ai_, 'prod_rhs': []})
            else:
                for rhs in prod_dict[Ai]:
                    new_prods.append({'prod_lhs': Ai, 'prod_rhs': rhs})
        grammar['productions'] = new_prods
        logger.info(f"Left recursion removed. New count: {len(new_prods)}")
        return grammar

    def closure_set(self, entries):
        """Compute closure of a set of LR1 entries"""
        closure = set()
        for entry in entries:
            closure.add(self._to_lr1entry(entry) if isinstance(entry, dict) else entry)
        changed = True
        while changed:
            changed = False
            for entry in list(closure):
                if entry.dot < len(entry.rhs):
                    B = entry.rhs[entry.dot]
                    if B in self.nonterminal_set:
                        beta = entry.rhs[entry.dot+1:]
                        lookaheads = self.first_set(beta + (entry.la,)) if beta else {entry.la}
                        for prod in self.prod_map[B]:
                            for la in lookaheads:
                                new_entry = LR1Entry(
                                    lhs=B,
                                    rhs=tuple(prod['rhs']),
                                    dot=0,
                                    la=la
                                )
                                if new_entry not in closure:
                                    closure.add(new_entry)
                                    changed = True
        return tuple(sorted(closure, key=lambda x: (x.lhs, x.rhs, x.dot, x.la)))

    def goto_set(self, entries, symbol):
        """LR(1) goto function"""
        next_entries = set()
        for entry in entries:
            curr = self._to_lr1entry(entry) if isinstance(entry, dict) else entry
            if curr.dot < len(curr.rhs) and curr.rhs[curr.dot] == symbol:
                next_entries.add(LR1Entry(
                    lhs=curr.lhs,
                    rhs=curr.rhs,
                    dot=curr.dot + 1,
                    la=curr.la
                ))
        return self.closure_set(next_entries) if next_entries else None

    def first_set(self, symbols, visited=None):
        """Compute FIRST set for a sequence of symbols"""
        if visited is None:
            visited = set()
        cache_key = tuple(symbols)
        if cache_key in self._first_cache:
            return set(self._first_cache[cache_key])
        if cache_key in visited:
            return set()
        visited.add(cache_key)
        result = set()
        if not symbols:
            result.add('')
            return result
        for sym in symbols:
            if sym in self.terminal_set or sym == '$':
                result.add(sym)
                result.discard('')
                break
            elif sym in self.nonterminal_set:
                has_epsilon = False
                for prod in self.prod_map.get(sym, []):
                    if not prod['rhs']:
                        result.add('')
                        has_epsilon = True
                        continue
                    sub_first = self.first_set(prod['rhs'], visited.copy())
                    result |= (sub_first - {''})
                    if '' in sub_first:
                        has_epsilon = True
                if not has_epsilon:
                    result.discard('')
                    break
            else:
                raise ValueError(f"Unknown symbol: {sym}")
        self._first_cache[cache_key] = set(result)
        return result

    def build_table(self, grammar):
        """Build LR(1) parsing table"""
        self.grammar = grammar
        self._setup_grammar()
        logger.debug("Building LR(1) parsing table...")
        self.action_tbl = defaultdict(dict)
        self.goto_tbl = defaultdict(dict)
        self.state_list = []
        start_prod = self.prod_map[self.start][0]
        init_entry = LR1Entry(
            lhs=self.start,
            rhs=tuple(start_prod['rhs']),
            dot=0,
            la='$'
        )
        init_state = self.closure_set([init_entry])
        self.state_list = [init_state]
        queue = [init_state]
        state_ids = {init_state: 0}
        self._print_state(0, init_state)
        while queue:
            curr_state = queue.pop(0)
            curr_id = state_ids[curr_state]
            symbols = self.terminal_set | self.nonterminal_set
            for symbol in symbols:
                next_state = self.goto_set(curr_state, symbol)
                if next_state and len(next_state) > 0:
                    if next_state not in state_ids:
                        new_id = len(self.state_list)
                        state_ids[next_state] = new_id
                        self.state_list.append(next_state)
                        queue.append(next_state)
                        self._print_state(new_id, next_state)
                    new_id = state_ids[next_state]
                    if symbol in self.terminal_set:
                        self.action_tbl[curr_id][symbol] = ('shift', new_id)
                    else:
                        self.goto_tbl[curr_id][symbol] = new_id
            for entry in curr_state:
                if entry.dot == len(entry.rhs):
                    if entry.lhs == self.start and entry.la == '$':
                        self.action_tbl[curr_id]['$'] = ('accept',)
                    else:
                        for prod in self.prod_map[entry.lhs]:
                            if tuple(prod['rhs']) == entry.rhs:
                                self.action_tbl[curr_id][entry.la] = ('reduce', prod['idx'])
                                break
        logger.debug(f"Parsing table built ({len(self.state_list)} states)")
        return self.action_tbl, self.goto_tbl

    def parse(self, tokens, checker: SemanticChecker = None):
        """Run LR(1) parsing process"""
        trace = []
        state_stack = [0]
        node_stack = []
        idx = 0
        token_list = list(tokens)
        while True:
            curr_state = state_stack[-1]
            curr_token = token_list[idx]
            step = {
                "state_stack": list(state_stack),
                "node_stack": [str(n) for n in node_stack],
                "input": [str(t) for t in token_list[idx:]],
                "action": "",
                "prod": ""
            }
            action = self.action_tbl[curr_state].get(curr_token.type.value)
            if not action:
                expected = sorted(self.action_tbl[curr_state].keys())
                context = token_list[max(0, idx-2):idx+1]
                raise SyntaxError(
                    f"Syntax error at line {curr_token.line}, col {curr_token.column}\n"
                    f"Unexpected: {curr_token}\n"
                    f"Expected: {expected}\n"
                    f"Context: {context}"
                )
            if action[0] == 'shift':
                step["action"] = f"SHIFT: {curr_token} -> state {action[1]}"
                node_stack.append(ParseNode(symbol=curr_token.type.value, children=None, token=curr_token))
                idx += 1
                state_stack.append(action[1])
            elif action[0] == 'reduce':
                prod_idx = action[1]
                prod = self.prod_idx_map[prod_idx]
                lhs = prod['lhs']
                rhs_len = len(prod['rhs'])
                step["prod"] = f"{lhs} → {' '.join(prod['rhs']) if prod['rhs'] else 'ε'}"
                step["action"] = f"REDUCE: by production {prod_idx}"
                children = []
                if rhs_len > 0:
                    state_stack = state_stack[:-rhs_len]
                    children = node_stack[-rhs_len:]
                    node_stack = node_stack[:-rhs_len]
                new_node = ParseNode(symbol=lhs, children=children)
                if checker:
                    checker.on_reduce(node=new_node)
                node_stack.append(new_node)
                goto_state = self.goto_tbl[state_stack[-1]].get(lhs)
                if goto_state is None:
                    raise SyntaxError(f"Invalid GOTO: state {state_stack[-1]} with {lhs}")
                state_stack.append(goto_state)
            elif action[0] == 'accept':
                step["action"] = "ACCEPT: parsing finished"
                break
            else:
                raise SyntaxError(f"Unknown action: {action}")
            trace.append(step)
        return node_stack[0], trace

    @staticmethod
    def _to_lr1entry(item_dict):
        """Convert dict to LR1Entry"""
        prod = item_dict['production']
        return LR1Entry(
            lhs=prod['lhs'],
            rhs=tuple(prod['rhs']),
            dot=item_dict['dot_pos'],
            la=item_dict['lookahead']
        )

    def _print_grammar(self):
        logger.debug("=== Grammar Info ===")
        logger.debug(f"Start symbol: {self.start}")
        logger.debug(f"Terminals({len(self.terminal_set)}): {', '.join(sorted(self.terminal_set))}")
        logger.debug(f"Non-terminals({len(self.nonterminal_set)}): {', '.join(sorted(self.nonterminal_set))}")
        logger.debug("Productions:")
        maxlen = max((len(lhs) for lhs in self.prod_map), default=0)
        for lhs in sorted(self.prod_map.keys()):
            for prod in self.prod_map[lhs]:
                rhs_str = ' '.join(prod['rhs']) if prod['rhs'] else "ε"
                logger.debug(f"  {lhs.ljust(maxlen)} → {rhs_str} # {prod['idx']}")

    def _print_state(self, state_id, state):
        logger.debug(f"--- State {state_id} ---")
        for entry in sorted(state, key=lambda x: (x.lhs, x.rhs, x.dot)):
            rhs = list(entry.rhs)
            rhs.insert(entry.dot, '•')
            prod_str = f"{entry.lhs} → {' '.join(rhs) if rhs else 'ε'}"
            logger.debug(f"  {prod_str.ljust(40)} , {entry.la}")

if __name__ == "__main__":
    class DummyTokenType(Enum):
        ID = 'id'
        EQUAL = '='
        END = '$'
    tokens = [
        Token(DummyTokenType.ID, value="x", line=1, column=1),
        Token(DummyTokenType.EQUAL, value="=", line=1, column=3),
        Token(DummyTokenType.ID, value="y", line=1, column=5),
        Token(DummyTokenType.END)
    ]
    parser = SyntaxParser()
    parser.build_table(TEST_GRAMMAR)
    parser.parse(tokens)
    # parser.remove_left_recursion(LEFT_RECURSION_GRAMMAR)