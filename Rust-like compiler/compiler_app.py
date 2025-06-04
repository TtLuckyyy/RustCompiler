import time, threading
from typing import List
from PIL import Image, ImageTk, ImageSequence
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from graphviz import Digraph
from compiler_lexer import Token, TokenType, Lexer
from compiler_parser import ParseNode, Parser
from compiler_semantic_checker import SemanticChecker
from compiler_codegenerator import Quadruple
from compiler_rust_grammar import RUST_GRAMMAR, RUST_GRAMMAR_PPT
from compiler_logger import logger

class GrammarVisualizerApp:
    """词法分析->语法分析->语义分析"""
    def __init__(self, root):
        self.root = root
        self.root.title("类RUST语法分析可视化工具")
        self.root.geometry("1200x800")

        self.chinese_font_name = "楷体"    # 中文默认使用楷体
        self.code_font_name = "Consolas"  # 代码默认使用Consolas
        self.mono_font_name = "Consolas"  # 等宽字体默认使用Consolas

        self.load_icon()         # 加载ICON     

        # 与展示分析过程相关的变量
        self.ast_tree_root = None # 语法树根节点
        self.current_step = 0
        self.analysis_details = []
        self.tree_scale = 1.0
        self.tree_offset_x = 0
        self.tree_offset_y = 0
        self.drag_data = {"x": 0, "y": 0, "item": None} 

        self.lexer = Lexer()              # 词法分析器
        self.parser = Parser()            # 语法分析器
        self.checker = SemanticChecker()  # 语义检查器(内置中间代码生成器)

        self.create_loading_screen()
        self.start_parsing_in_thread()

    def create_widgets(self):
        # 设置全局样式
        style = ttk.Style()
        style.configure('.', font=('楷体', 11))  # 设置全局默认字体为楷体

        # 主框架
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # ------------------- 左侧面板 -------------------------
        left_panel = ttk.Frame(main_frame)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # ------------------- 代码编辑器 -----------------------
        code_frame = ttk.LabelFrame(left_panel, text="源代码编辑器")
        code_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        self.code_editor = scrolledtext.ScrolledText(code_frame, wrap=tk.WORD, font=('JetBrains Mono', 11))
        self.code_editor.pack(fill=tk.BOTH, expand=True)
        RUST_EXAMPLE = (
            "请在此输入要分析的代码...\n\n"
            "示例Rust函数:\n"
            "fn max(a: i32, b: i32) -> i32 {\n"
            "    if a > b { a } else { b }  // 返回较大值\n"
            "}"
        )
        self.code_editor.insert(tk.END, RUST_EXAMPLE)
        # 添加淡灰色提示文字效果
        self.code_editor.tag_configure("prompt", foreground="gray")
        self.code_editor.tag_add("prompt", "1.0", "end")
        # 绑定事件，当用户开始输入时清除提示文字
        def clear_prompt(event):
            current_content = self.code_editor.get("1.0", "end-1c")
            if current_content == RUST_EXAMPLE:
                self.code_editor.delete("1.0", tk.END)
                self.code_editor.tag_remove("prompt", "1.0", "end")
            elif current_content.strip() == "":
                self.code_editor.insert("1.0", RUST_EXAMPLE)
                self.code_editor.tag_add("prompt", "1.0", "end")
        self.code_editor.bind("<FocusIn>", clear_prompt)
        self.code_editor.bind("<FocusOut>", clear_prompt)
        
        # ------------------- 语法展示 -----------------------
        grammar_frame = ttk.LabelFrame(left_panel, text="语法定义")
        grammar_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        # 创建 Treeview 表格
        columns = ("index", "lhs", "rhs")
        self.grammar_editor = ttk.Treeview(grammar_frame, columns=columns, show='headings', height=8)
        
        # 设置列标题
        self.grammar_editor.heading("index", text="编号")
        self.grammar_editor.heading("lhs", text="左部")
        self.grammar_editor.heading("rhs", text="右部")

        # 设置列宽度和对齐方式
        self.grammar_editor.column("index", width=50, anchor='center')
        self.grammar_editor.column("lhs", width=100, anchor='center')
        self.grammar_editor.column("rhs", width=400, anchor='w')

        # 插入语法产生式
        idx = 0
        for lhs in self.parser.productions.keys():
            for prod in self.parser.productions[lhs]:
                rhs = prod['rhs']
                rhs_str = ' '.join(rhs) if rhs else 'ε'
                tag = 'evenrow' if idx % 2 == 0 else 'oddrow'
                self.grammar_editor.insert("", tk.END, values=(idx, lhs, rhs_str), tags=(tag,))
                idx += 1

        # 设置交错背景色
        self.grammar_editor.tag_configure('evenrow', background='#f0f0ff')
        self.grammar_editor.tag_configure('oddrow', background='#ffffff')

        # 加滚动条
        scrollbar = ttk.Scrollbar(grammar_frame, orient="vertical", command=self.grammar_editor.yview)
        self.grammar_editor.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.grammar_editor.pack(fill=tk.BOTH, expand=True)
        
        # 控制按钮
        button_frame = ttk.Frame(left_panel)
        button_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(button_frame, text="分析代码", command=self.analyze_code).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="显示ACTION/GOTO表", command=self.show_tables).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="重置分析", command=self.reset_analysis).pack(side=tk.LEFT, padx=5)
        
        # ------------------- 右侧面板 -----------------------
        right_panel = ttk.Frame(main_frame)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # ------------------- 分析树显示 -----------------------
        tree_frame = ttk.LabelFrame(right_panel, text="语法分析树")
        tree_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.tree_canvas = tk.Canvas(tree_frame, bg='white')
        self.tree_canvas.pack(fill=tk.BOTH, expand=True)

        # 绑定树形图的缩放和拖动事件
        self.tree_canvas.bind("<MouseWheel>", self.zoom_tree)
        self.tree_canvas.bind("<ButtonPress-1>", self.start_drag)
        self.tree_canvas.bind("<B1-Motion>", self.on_drag)
        self.tree_canvas.bind("<ButtonRelease-1>", self.end_drag)

        # ------------- 创建可切换的显示区域 -----------------------
        self.notebook = ttk.Notebook(right_panel)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=5)

        # 分析过程标签页
        process_tab = ttk.Frame(self.notebook)
        self.notebook.add(process_tab, text="分析过程")

        # 中间代码标签页
        ir_tab = ttk.Frame(self.notebook)
        self.notebook.add(ir_tab, text="中间代码")

        # 语义错误标签页
        error_tab = ttk.Frame(self.notebook)
        self.notebook.add(error_tab, text="语义错误")

        # 分析过程内容
        self.process_text = scrolledtext.ScrolledText(process_tab, wrap=tk.WORD, height=10, state='disabled')
        self.process_text.pack(fill=tk.BOTH, expand=True)

        # 中间代码内容 - 使用Treeview展示四元式
        self.ir_frame = ttk.Frame(ir_tab)
        self.ir_frame.pack(fill=tk.BOTH, expand=True)

        # 创建中间代码表格
        columns = ("index", "op", "arg1", "arg2", "result")
        self.ir_table = ttk.Treeview(self.ir_frame, columns=columns, show='headings', height=10)

        # 设置列标题
        self.ir_table.heading("index", text="序号")
        self.ir_table.heading("op", text="操作")
        self.ir_table.heading("arg1", text="操作数1")
        self.ir_table.heading("arg2", text="操作数2")
        self.ir_table.heading("result", text="结果")

        # 设置列宽度
        self.ir_table.column("index", width=50, anchor='center')
        self.ir_table.column("op", width=100, anchor='center')
        self.ir_table.column("arg1", width=100, anchor='center')
        self.ir_table.column("arg2", width=100, anchor='center')
        self.ir_table.column("result", width=100, anchor='center')

        # 添加滚动条
        scrollbar = ttk.Scrollbar(self.ir_frame, orient="vertical", command=self.ir_table.yview)
        self.ir_table.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.ir_table.pack(fill=tk.BOTH, expand=True)

        # 语义错误内容
        self.error_text = scrolledtext.ScrolledText(error_tab, wrap=tk.WORD, height=10, foreground='red', state='disabled')
        self.error_text.pack(fill=tk.BOTH, expand=True)

        # ------------- 控制按钮区域 ------------- 
        control_frame = ttk.Frame(right_panel)
        control_frame.pack(fill=tk.X, pady=5)

        # 分析控制按钮组 - 初始隐藏
        self.process_btn_frame = ttk.Frame(control_frame)
        self.step_label = ttk.Label(self.process_btn_frame, text="步骤: 0/0")
        self.step_label.pack(side=tk.LEFT, padx=5)

        ttk.Button(self.process_btn_frame, text="上一步", command=self.prev_step).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.process_btn_frame, text="下一步", command=self.next_step).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.process_btn_frame, text="自动播放", command=self.auto_play).pack(side=tk.LEFT, padx=5)

        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)

    def analyze_code(self):
        """分析输入的代码并显示结果"""
        try:
            # 清空之前的分析结果
            self.reset_analysis()
            
            if "prompt" in self.code_editor.tag_names("1.0"):
                messagebox.showwarning("警告", "请输入要分析的代码")
                return
            
            code = self.code_editor.get("1.0", tk.END).strip()
            if not code:
                messagebox.showwarning("警告", "请输入要分析的代码")
                return
            
            tokens = self.lexer.tokenize(code)
            ast_root, self.analysis_details = self.parser.analyse(tokens=tokens, checker=self.checker)
            self.show_ast(ast_root)
            self.show_step(0)
            errors = self.checker.get_errors()
            quads = self.checker.get_quads()
            self.show_semantic_errors(errors)
            if not errors:
                self.show_quadruples(quads)
            
        except Exception as e:
            messagebox.showerror("错误", f"分析过程中出错: {str(e)}")

    def record_parsing_process(self, tokens):
        """记录语法分析的每一步过程"""
        self.analysis_details = []
        state_stack = [0]  # 状态栈
        node_stack =  []   # 节点栈
        idx = 0            # 当前token指针
        token_stream = list(tokens)

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
            action = self.parser.action_table[state].get(current_token.type.value)
            if not action:
                expected = sorted(self.parser.action_table[state].keys())
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
                prod = self.parser.prod_by_index[prod_index]
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
                self.checker.on_reduce(node=new_node)
                node_stack.append(new_node)

                # GOTO转移
                goto_state = self.parser.goto_table[state_stack[-1]].get(lhs)
                state_stack.append(goto_state)
                
            elif action[0] == 'accept':
                step_info["action"] = "接受: 分析完成"
                self.analysis_details.append(step_info)
                self.visualize_ast(node_stack[0])
                self.show_step(0)
                break
            
            self.analysis_details.append(step_info)

        errors = self.checker.get_errors()
        if errors:
            self.show_semantic_errors(errors=errors)
        else:
            self.show_quadruples(self.checker.get_quads())

    def show_quadruples(self, quadruples: List[Quadruple]):
        """更新中间代码显示"""
        # 清空现有内容
        for item in self.ir_table.get_children():
            self.ir_table.delete(item)

        # 添加新的四元式
        for idx, quad in enumerate(quadruples):
            values = (
                idx,
                quad.op,
                str(quad.arg1) if quad.arg1 is not None else "",
                str(quad.arg2) if quad.arg2 is not None else "",
                quad.result
            )
            tag = 'evenrow' if idx % 2 == 0 else 'oddrow'
            self.ir_table.insert("", tk.END, values=values, tags=(tag,))

        # 设置交替行颜色
        self.ir_table.tag_configure('evenrow', background='#f0f0ff')
        self.ir_table.tag_configure('oddrow', background='#ffffff')

    def show_semantic_errors(self, errors):
        """显示语义分析错误"""
        self.notebook.select(2)  # 自动切换到错误标签页
        self.error_text.configure(state='normal')
        self.error_text.delete(1.0, tk.END)

        if errors:
            self.error_text.insert(tk.END, "=== 语义分析错误 ===\n\n")
            for i, error in enumerate(errors, 1):
                self.error_text.insert(tk.END, f"{i}. 行 {error.line}: {error.message}\n\n", 'error')
            # 高亮第一个错误行
            if errors[0].line > 0:
                self.highlight_code_line(errors[0].line)
        else:
            self.error_text.insert(tk.END, "✓ 未发现语义错误", 'success')

        self.error_text.tag_configure('error', foreground='red')
        self.error_text.tag_configure('success', foreground='green')
        self.error_text.configure(state='disabled')

    def highlight_code_line(self, line_num):
        """高亮显示代码行"""
        self.code_editor.tag_remove("error_line", "1.0", "end")
        self.code_editor.tag_add("error_line", f"{line_num}.0", f"{line_num}.end")
        self.code_editor.tag_config("error_line", background="#ffdddd")
        self.code_editor.see(f"{line_num}.0")

    def show_step(self, step_index):
        """显示指定步骤的分析过程"""
        if step_index < 0 or step_index >= len(self.analysis_details):
            return
        
        # 更新步骤标签
        if hasattr(self, 'step_label'):
            self.step_label.config(text=f"步骤: {step_index + 1}/{len(self.analysis_details)}",
                                   font=(self.chinese_font_name, 12))
            
        self.current_step = step_index
        step = self.analysis_details[step_index]
        
        # 清空显示
        self.process_text.config(state=tk.NORMAL)
        self.process_text.delete(1.0, tk.END)
        
        # 显示分析栈
        self.process_text.insert(tk.END, "分析栈:\n", "header")
        stack_str = " ".join(f"[{state}]" for state in step["stack"])
        self.process_text.insert(tk.END, stack_str + "\n\n")
        
        # 显示节点栈
        self.process_text.insert(tk.END, "节点栈:\n", "header")
        node_str = " ".join(step["node_stack"])
        self.process_text.insert(tk.END, node_str + "\n\n")
        
        # 显示输入串
        self.process_text.insert(tk.END, "输入串:\n", "header")
        input_str = " ".join(step["input"])
        self.process_text.insert(tk.END, input_str + "\n\n")
        
        # 显示动作
        if step["action"]:
            self.process_text.insert(tk.END, "动作:\n", "header")
            self.process_text.insert(tk.END, step["action"] + "\n\n")
        
        # 显示产生式
        if step["production"]:
            self.process_text.insert(tk.END, "产生式:\n", "header")
            self.process_text.insert(tk.END, step["production"] + "\n")
        
        # 设置文本样式
        self.process_text.tag_config("header", font=(self.chinese_font_name, 10, 'bold'))
        self.process_text.config(font=(self.code_font_name, 10))
        self.process_text.config(state=tk.DISABLED)

    def show_ast(self, root):
        """使用Graphviz可视化AST"""
        try:
            # 清空画布
            self.tree_canvas.delete("all")
            
            # 创建Graphviz图
            dot = Digraph(comment='AST')
            dot.attr('node', shape='box', style='rounded')
            dot.attr('edge', arrowhead='vee')
            
            # 添加节点和边
            def add_nodes_edges(node, parent_id=None):
                node_id = str(id(node))

                # 节点标签和样式
                if node.is_terminal():  # 终结符节点
                    label = f"{node.symbol}\n{node.token.value}"
                    fill_color = "#d4edda"  # 浅绿色
                    border_color = "#155724"  # 深绿色
                    font_color = "#155724"
                else:  # 非终结符节点
                    label = node.symbol
                    fill_color = "#d1ecf1"  # 浅蓝色
                    border_color = "#0c5460"  # 深蓝色
                    font_color = "#0c5460"
                    
                    # 如果是非终结符但没有子节点，添加ε节点
                    if not node.children:
                        epsilon_id = f"{node_id}_epsilon"
                        dot.node(
                            epsilon_id,
                            label="ε",
                            fillcolor="#f8d7da",  # 浅红色
                            style='filled,rounded',
                            color="#721c24",  # 深红色
                            fontcolor="#721c24",
                            fontname="Arial",
                            penwidth="1.5"
                        )
                        dot.edge(node_id, epsilon_id, color="#6c757d", penwidth="1.2")

                # 添加节点
                dot.node(
                    node_id, 
                    label=label,
                    fillcolor=fill_color,
                    style='filled,rounded',
                    color=border_color,
                    fontcolor=font_color,
                    fontname="Arial",
                    penwidth="1.5"
                )

                # 添加边
                if parent_id is not None:
                    dot.edge(parent_id, node_id, color="#6c757d", penwidth="1.2")

                # 递归处理子节点
                for child in node.children:
                    add_nodes_edges(child, node_id)
            
            add_nodes_edges(root)
            
            # 设置图属性
            dot.attr(rankdir='TB', margin='0.2', nodesep='0.2', ranksep='0.5')

            # 渲染图像
            dot.render('temp_ast', format='png', cleanup=True)

            # 在Canvas上显示图像
            from PIL import Image, ImageTk
            img = Image.open("temp_ast.png")

            # 自适应画布大小
            canvas_width = self.tree_canvas.winfo_width() - 20
            canvas_height = self.tree_canvas.winfo_height() - 20
            img.thumbnail((canvas_width, canvas_height), Image.Resampling.LANCZOS)

            self.ast_img = ImageTk.PhotoImage(img)
            self.tree_canvas.create_image(
                10, 10, 
                anchor=tk.NW, 
                image=self.ast_img,
                tags=("ast_image",)
            )

            # 绑定鼠标悬停事件
            self.tree_canvas.tag_bind("ast_image", "<Enter>", lambda e: self.tree_canvas.config(cursor="hand2"))
            self.tree_canvas.tag_bind("ast_image", "<Leave>", lambda e: self.tree_canvas.config(cursor=""))
            
        except Exception as e:
            messagebox.showerror("错误", f"可视化AST时出错: {str(e)}")
    
    def show_tables(self):
        """显示ACTION和GOTO表"""
        try:           
            # 创建新窗口显示表格
            table_window = tk.Toplevel(self.root)
            table_window.title("ACTION/GOTO表")
            table_window.geometry("1000x600")
            
            # 使用Notebook显示多个表格
            notebook = ttk.Notebook(table_window)
            notebook.pack(fill=tk.BOTH, expand=True)
            
            # ----------------- ACTION表 -----------------
            action_frame = ttk.Frame(notebook)
            notebook.add(action_frame, text="ACTION表")

            # 创建Treeview表格
            action_tree = ttk.Treeview(action_frame)
            action_tree.pack(fill=tk.BOTH, expand=True)
        
            # 设置列
            terminals = sorted({k for state in self.parser.action_table.values() for k in state.keys()})
            action_tree["columns"] = terminals
            action_tree.column("#0", width=80, anchor="center")  # 状态列
            action_tree.heading("#0", text="状态")

            # 添加表头
            for term in terminals:
                action_tree.column(term, width=80, anchor="center")
                action_tree.heading(term, text=term)

            # 填充数据
            for state in sorted(self.parser.action_table.keys()):
                values = [self.parser.action_table[state].get(term, "") for term in terminals]
                action_tree.insert("", "end", text=str(state), values=values)

            # ----------------- GOTO表 -----------------
            goto_frame = ttk.Frame(notebook)
            notebook.add(goto_frame, text="GOTO表")

            goto_tree = ttk.Treeview(goto_frame)
            goto_tree.pack(fill=tk.BOTH, expand=True)
        
            # 设置列
            non_terminals = sorted({k for state in self.parser.goto_table.values() for k in state.keys()})
            goto_tree["columns"] = non_terminals
            goto_tree.column("#0", width=80, anchor="center")
            goto_tree.heading("#0", text="状态")

            # 添加表头
            for nt in non_terminals:
                goto_tree.column(nt, width=80, anchor="center")
                goto_tree.heading(nt, text=nt)

            # 填充数据
            for state in sorted(self.parser.goto_table.keys()):
                values = [self.parser.goto_table[state].get(nt, "") for nt in non_terminals]
                goto_tree.insert("", "end", text=str(state), values=values)

            # 添加滚动条
            for tree in [action_tree, goto_tree]:
                vsb = ttk.Scrollbar(tree, orient="vertical", command=tree.yview)
                hsb = ttk.Scrollbar(tree, orient="horizontal", command=tree.xview)
                tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
                vsb.pack(side="right", fill="y")
                hsb.pack(side="bottom", fill="x")
            
        except Exception as e:
            messagebox.showerror("错误", f"显示表格时出错: {str(e)}")
    
    def reset_analysis(self):
        """重置分析过程"""
        self.tree_canvas.delete("all")

        self.ast_tree_root = None
        self.current_step = 0
        self.analysis_details = []
        self.tree_scale = 1.0
        self.tree_offset_x = 0
        self.tree_offset_y = 0
        self.drag_data = {"x": 0, "y": 0, "item": None} 

        self.process_text.config(state=tk.NORMAL)
        self.process_text.delete(1.0, tk.END)

        if hasattr(self, 'step_label'):
            self.step_label.config(text=f"步骤: 0/0", font=(self.chinese_font_name, 12))

        # 重置语义分析器
        self.checker.reset()

        # 清除消除信息
        self.error_text.configure(state='normal')
        self.error_text.delete(1.0, tk.END)
        self.error_text.configure(state='disabled')

    # --------------- 初始化 -------------------

    def start_parsing_in_thread(self):
        """在单独的线程中启动解析器初始化"""
        def parsing_thread():
            # 执行耗时操作 -- 构建分析表
            self.parser.build_parse_table(RUST_GRAMMAR_PPT)

            # 完成后，在主线程中销毁加载界面并创建主界面
            self.root.after(0, self.finish_loading)

        # 启动线程
        thread = threading.Thread(target=parsing_thread)
        thread.daemon = True
        thread.start()

    def finish_loading(self):
        """完成加载后的创建主页面"""
        # 销毁加载界面
        if hasattr(self, 'loading_frame'):
            self.loading_frame.destroy()
    
        # 创建主界面
        self.create_widgets()

    def load_icon(self):
        try:
            img_path = './__assets__/rust_icon_1.png'
            img = Image.open(img_path)
            self.icon = ImageTk.PhotoImage(img)
            self.root.tk.call('wm', 'iconphoto', self.root._w, self.icon)
        except:
            logger.error(f"图标文件\"{img_path}\"未找到，使用默认图标")

    def create_loading_screen(self):
        """创建带有GIF动画的加载界面"""
        self.loading_frame = tk.Frame(self.root)
        self.loading_frame.place(relx=0.5, rely=0.5, anchor="center")

        try:
            gif_path = './__assets__/loading.gif'
            self.gif = Image.open(gif_path)
            self.gif_frames = []
            self.current_frame = 0

            try:
                while True:
                    frame = self.gif.copy()
                    self.gif_frames.append(ImageTk.PhotoImage(frame))
                    self.gif.seek(self.gif.tell() + 1)
            except EOFError:
                pass

            self.gif_label = tk.Label(self.loading_frame)
            self.gif_label.pack()

            self.loading_text = tk.Label(
                self.loading_frame, 
                text="正在生成语法分析表，请稍候...", 
                font=(self.chinese_font_name, 12)
            )
            self.loading_text.pack(pady=10)

            self.animate_gif(0)

        except Exception as e:
            logger.error(f"无法加载GIF动画: {str(e)}")
            self.loading_text = tk.Label(
                self.loading_frame, 
                text="正在生成语法分析表，请稍候...", 
                font=(self.chinese_font_name, 14)
            )
            self.loading_text.pack(pady=20)

    def animate_gif(self, frame_index):
        """更新GIF动画"""
        if not hasattr(self, 'loading_frame') or not self.loading_frame.winfo_exists():
            return 

        if hasattr(self, 'gif_frames') and self.gif_frames:
            next_frame = (frame_index + 1) % len(self.gif_frames)
            self.gif_label.config(image=self.gif_frames[frame_index])
            self.root.after(100, self.animate_gif, next_frame)

    # ---------------- 事件 --------------------
        
    def start_drag(self, event):
        """开始拖动语法树"""
        self.drag_data["x"] = event.x
        self.drag_data["y"] = event.y
        self.drag_data["item"] = self.tree_canvas.find_closest(event.x, event.y)[0]
    
    def on_drag(self, event):
        """拖动语法树过程中"""
        dx = event.x - self.drag_data["x"]
        dy = event.y - self.drag_data["y"]
        
        self.tree_offset_x += dx
        self.tree_offset_y += dy
        
        self.tree_canvas.move(self.drag_data["item"], dx, dy)
        self.drag_data["x"] = event.x
        self.drag_data["y"] = event.y
    
    def end_drag(self, event):
        """结束拖动语法树"""
        self.drag_data["item"] = None
     
    def zoom_tree(self, event):
        """缩放语法树"""
        scale_factor = 1.1 if event.delta > 0 else 0.9
        self.tree_scale *= scale_factor
        
        # 重新绘制树
        if hasattr(self, 'ast_img'):
            self.tree_canvas.delete("all")
            img = Image.open("temp_ast.png")
            
            # 计算新尺寸
            new_width = int(img.width * self.tree_scale)
            new_height = int(img.height * self.tree_scale)
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            self.ast_img = ImageTk.PhotoImage(img)
            self.tree_image_id = self.tree_canvas.create_image(
                self.tree_offset_x, 
                self.tree_offset_y, 
                anchor=tk.NW, 
                image=self.ast_img,
                tags=("ast_image",)
            )

    def prev_step(self):
        """显示上一步"""
        self.show_step(self.current_step - 1)
    
    def next_step(self):
        """显示下一步"""
        self.show_step(self.current_step + 1)

    def auto_play(self):
        """自动播放分析过程"""
        for i in range(len(self.analysis_details)):
            self.show_step(i)
            self.root.update()
            time.sleep(1)  # 1秒间隔

    def on_tab_changed(self, event):
        """当切换标签页时显示/隐藏控制按钮"""
        current_tab = self.notebook.tab(self.notebook.select(), "text")
        if current_tab == "分析过程":
            self.process_btn_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        else:
            self.process_btn_frame.pack_forget()
        
if __name__ == "__main__":
    root = tk.Tk()
    app = GrammarVisualizerApp(root)
    root.mainloop()