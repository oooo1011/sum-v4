"""
子集组合求和 - 主程序和GUI界面
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import threading
import time
import os
import sys
import platform
import traceback
from typing import List, Optional, Tuple
import re
import xlsxwriter

from subset_sum_wrapper import SubsetSumSolver

class SubsetSumApp:
    """子集组合求和应用程序"""
    
    def __init__(self, root):
        """初始化应用程序"""
        self.root = root
        self.root.title("子集组合求和")
        self.root.geometry("800x600")
        self.root.minsize(800, 600)
        
        # 创建求解器
        self.solver = SubsetSumSolver()
        self.calculation_thread = None
        
        # 存储数据和结果，用于导出
        self.input_numbers = []
        self.current_solutions = []
        
        # 创建UI
        self._create_ui()
        
        # 设置进度回调
        self.solver.set_progress_callback(self._update_progress)
    
    def _create_ui(self):
        """创建用户界面"""
        # 创建主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建左右分栏
        left_frame = ttk.Frame(main_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        right_frame = ttk.Frame(main_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(10, 0))
        
        # === 左侧：输入区域 ===
        input_frame = ttk.LabelFrame(left_frame, text="输入数据", padding="10")
        input_frame.pack(fill=tk.BOTH, expand=True)
        
        # 数字输入区
        ttk.Label(input_frame, text="输入数字（每行一个，支持最多两位小数的正数）:").pack(anchor=tk.W)
        
        # 数字输入文本框和滚动条
        numbers_frame = ttk.Frame(input_frame)
        numbers_frame.pack(fill=tk.BOTH, expand=True, pady=(5, 10))
        
        self.numbers_text = scrolledtext.ScrolledText(numbers_frame, wrap=tk.WORD, height=10)
        self.numbers_text.pack(fill=tk.BOTH, expand=True)
        
        # 文件操作按钮
        file_frame = ttk.Frame(input_frame)
        file_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Button(file_frame, text="从文件加载", command=self._load_from_file).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(file_frame, text="保存到文件", command=self._save_to_file).pack(side=tk.LEFT)
        
        # 目标和输入
        target_frame = ttk.Frame(input_frame)
        target_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(target_frame, text="目标和:").pack(side=tk.LEFT)
        self.target_entry = ttk.Entry(target_frame)
        self.target_entry.pack(side=tk.LEFT, padx=(5, 0), fill=tk.X, expand=True)
        
        # 解决方案数量
        solutions_frame = ttk.Frame(input_frame)
        solutions_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(solutions_frame, text="解决方案数量:").pack(side=tk.LEFT)
        self.solutions_var = tk.StringVar(value="1")
        self.solutions_entry = ttk.Spinbox(solutions_frame, from_=1, to=100, textvariable=self.solutions_var)
        self.solutions_entry.pack(side=tk.LEFT, padx=(5, 0), fill=tk.X, expand=True)
        
        # 内存限制
        memory_frame = ttk.Frame(input_frame)
        memory_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(memory_frame, text="内存限制 (MB):").pack(side=tk.LEFT)
        self.memory_var = tk.StringVar(value="1000")
        self.memory_entry = ttk.Spinbox(memory_frame, from_=100, to=10000, textvariable=self.memory_var)
        self.memory_entry.pack(side=tk.LEFT, padx=(5, 0), fill=tk.X, expand=True)
        
        # 操作按钮
        button_frame = ttk.Frame(input_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.start_button = ttk.Button(button_frame, text="开始计算", command=self._start_calculation)
        self.start_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.stop_button = ttk.Button(button_frame, text="停止", command=self._stop_calculation, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT)
        
        # === 右侧：结果和进度区域 ===
        result_frame = ttk.LabelFrame(right_frame, text="计算结果", padding="10")
        result_frame.pack(fill=tk.BOTH, expand=True)
        
        # 进度条
        progress_frame = ttk.Frame(result_frame)
        progress_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(progress_frame, text="计算进度:").pack(anchor=tk.W)
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill=tk.X, pady=(5, 0))
        
        # 进度文本
        self.progress_label = ttk.Label(progress_frame, text="0.0%")
        self.progress_label.pack(anchor=tk.E, pady=(5, 0))
        
        # 结果文本区
        result_header_frame = ttk.Frame(result_frame)
        result_header_frame.pack(fill=tk.X, pady=(10, 5))
        
        ttk.Label(result_header_frame, text="找到的子集:").pack(side=tk.LEFT)
        
        # 导出结果按钮
        self.export_button = ttk.Button(result_header_frame, text="导出结果", command=self._export_results, state=tk.DISABLED)
        self.export_button.pack(side=tk.RIGHT)
        
        self.result_text = scrolledtext.ScrolledText(result_frame, wrap=tk.WORD, height=15)
        self.result_text.pack(fill=tk.BOTH, expand=True)
        self.result_text.config(state=tk.DISABLED)
        
        # 状态栏
        self.status_var = tk.StringVar(value="就绪")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X, pady=(10, 0))
    
    def _load_from_file(self):
        """从文件加载数字"""
        file_path = filedialog.askopenfilename(
            title="选择数字文件",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
        )
        
        if not file_path:
            return
        
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            self.numbers_text.delete(1.0, tk.END)
            self.numbers_text.insert(tk.END, content)
            self.status_var.set(f"从文件加载了数据: {os.path.basename(file_path)}")
        except Exception as e:
            messagebox.showerror("加载错误", f"无法加载文件: {str(e)}")
    
    def _save_to_file(self):
        """保存数字到文件"""
        file_path = filedialog.asksaveasfilename(
            title="保存数字文件",
            defaultextension=".txt",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
        )
        
        if not file_path:
            return
        
        try:
            content = self.numbers_text.get(1.0, tk.END)
            with open(file_path, 'w') as f:
                f.write(content)
            self.status_var.set(f"数据已保存到文件: {os.path.basename(file_path)}")
        except Exception as e:
            messagebox.showerror("保存错误", f"无法保存文件: {str(e)}")
    
    def _parse_numbers(self) -> List[float]:
        """解析输入的数字"""
        text = self.numbers_text.get(1.0, tk.END).strip()
        lines = text.split('\n')
        numbers = []
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
            
            try:
                # 验证数字格式（最多两位小数的正数）
                if not re.match(r'^[0-9]+(\.[0-9]{1,2})?$', line):
                    raise ValueError(f"第 {i+1} 行: '{line}' 不是有效的正数（最多两位小数）")
                
                num = float(line)
                if num <= 0:
                    raise ValueError(f"第 {i+1} 行: '{line}' 不是正数")
                
                numbers.append(num)
            except ValueError as e:
                raise ValueError(str(e))
        
        return numbers
    
    def _parse_target(self) -> float:
        """解析目标和"""
        target_str = self.target_entry.get().strip()
        if not target_str:
            raise ValueError("请输入目标和")
        
        try:
            target = float(target_str)
            if target <= 0:
                raise ValueError("目标和必须是正数")
            return target
        except ValueError:
            raise ValueError("目标和必须是有效的数字")
    
    def _parse_max_solutions(self) -> int:
        """解析最大解决方案数量"""
        try:
            max_solutions = int(self.solutions_var.get())
            if max_solutions <= 0:
                raise ValueError("解决方案数量必须大于0")
            return max_solutions
        except ValueError:
            raise ValueError("解决方案数量必须是有效的整数")
    
    def _parse_memory_limit(self) -> int:
        """解析内存限制"""
        try:
            memory_limit = int(self.memory_var.get())
            if memory_limit < 100:
                raise ValueError("内存限制不能小于100MB")
            return memory_limit
        except ValueError:
            raise ValueError("内存限制必须是有效的整数")
    
    def _update_progress(self, progress: float):
        """更新进度条和标签"""
        if not self.root:
            return
        
        self.progress_var.set(progress)
        self.progress_label.config(text=f"{progress:.1f}%")
        
        # 如果计算完成，启用开始按钮
        if progress >= 100:
            self._enable_ui()
    
    def _enable_ui(self):
        """启用UI控件"""
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.numbers_text.config(state=tk.NORMAL)
        self.target_entry.config(state=tk.NORMAL)
        self.solutions_entry.config(state=tk.NORMAL)
        self.memory_entry.config(state=tk.NORMAL)
        self.export_button.config(state=tk.NORMAL)
    
    def _disable_ui(self):
        """禁用UI控件"""
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.numbers_text.config(state=tk.DISABLED)
        self.target_entry.config(state=tk.DISABLED)
        self.solutions_entry.config(state=tk.DISABLED)
        self.memory_entry.config(state=tk.DISABLED)
        self.export_button.config(state=tk.DISABLED)
    
    def _start_calculation(self):
        """开始计算"""
        # 清除之前的结果
        self.result_text.config(state=tk.NORMAL)
        self.result_text.delete(1.0, tk.END)
        self.result_text.config(state=tk.DISABLED)
        
        # 解析输入
        try:
            numbers = self._parse_numbers()
            target = self._parse_target()
            max_solutions = self._parse_max_solutions()
            memory_limit = self._parse_memory_limit()
        except ValueError as e:
            messagebox.showerror("输入错误", str(e))
            return
        
        # 验证输入数量
        if len(numbers) < 2:
            messagebox.showerror("输入错误", "请至少输入2个数字")
            return
        
        if len(numbers) > 300:
            messagebox.showerror("输入错误", "数字数量不能超过300个")
            return
        
        # 存储原始数据
        self.input_numbers = numbers
        
        # 禁用UI
        self._disable_ui()
        
        # 重置进度
        self.progress_var.set(0)
        self.progress_label.config(text="0.0%")
        self.status_var.set("计算中...")
        
        # 启动计算线程
        self.calculation_thread = threading.Thread(
            target=self._calculation_worker,
            args=(numbers, target, max_solutions, memory_limit)
        )
        self.calculation_thread.daemon = True
        self.calculation_thread.start()
    
    def _calculation_worker(self, numbers: List[float], target: float, max_solutions: int, memory_limit: int):
        """计算工作线程"""
        start_time = time.time()
        
        try:
            # 调用求解器
            solutions = self.solver.find_subsets(numbers, target, max_solutions, memory_limit)
            
            # 计算用时
            elapsed_time = time.time() - start_time
            
            # 存储计算结果
            self.current_solutions = solutions
            
            # 显示结果
            self.root.after(0, lambda: self._display_results(solutions, elapsed_time))
            
        except Exception as e:
            # 显示错误
            error_msg = f"计算出错: {str(e)}\n{traceback.format_exc()}"
            self.root.after(0, lambda: self._display_error(error_msg))
    
    def _display_results(self, solutions: List[List[float]], elapsed_time: float):
        """显示计算结果"""
        self.result_text.config(state=tk.NORMAL)
        self.result_text.delete(1.0, tk.END)
        
        if not solutions:
            self.result_text.insert(tk.END, "未找到符合条件的子集")
        else:
            for i, subset in enumerate(solutions):
                self.result_text.insert(tk.END, f"解决方案 {i+1}:\n")
                self.result_text.insert(tk.END, f"子集: {[round(x, 2) for x in subset]}\n")
                self.result_text.insert(tk.END, f"和: {round(sum(subset), 2)}\n")
                self.result_text.insert(tk.END, f"元素个数: {len(subset)}\n")
                if i < len(solutions) - 1:
                    self.result_text.insert(tk.END, "\n" + "-" * 40 + "\n\n")
        
        self.result_text.config(state=tk.DISABLED)
        self.status_var.set(f"计算完成，用时: {elapsed_time:.2f} 秒")
        self._enable_ui()
    
    def _display_error(self, error_msg: str):
        """显示错误信息"""
        self.result_text.config(state=tk.NORMAL)
        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, error_msg)
        self.result_text.config(state=tk.DISABLED)
        self.status_var.set("计算出错")
        self._enable_ui()
    
    def _stop_calculation(self):
        """停止计算"""
        if self.solver:
            self.solver.stop()
            self.status_var.set("计算已停止")
    
    def _export_results(self):
        """导出结果到Excel文件"""
        if not self.input_numbers or not self.current_solutions:
            messagebox.showerror("导出错误", "没有可导出的结果，请先计算")
            return
            
        file_path = filedialog.asksaveasfilename(
            title="保存结果文件",
            defaultextension=".xlsx",
            filetypes=[("Excel文件", "*.xlsx"), ("所有文件", "*.*")]
        )
        
        if not file_path:
            return
        
        try:
            workbook = xlsxwriter.Workbook(file_path)
            worksheet = workbook.add_worksheet()
            
            # 定义单元格格式
            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#D9D9D9',
                'border': 1
            })
            
            highlight_format = workbook.add_format({
                'bg_color': 'yellow',
                'border': 1
            })
            
            normal_format = workbook.add_format({
                'border': 1
            })
            
            # 写入标题
            worksheet.write(0, 0, "输入数字", header_format)
            worksheet.write(0, 1, "是否选中", header_format)
            
            # 设置列宽
            worksheet.set_column(0, 0, 12)
            worksheet.set_column(1, 1, 12)
            
            # 获取所有选中的数字（所有解决方案中的所有数字）
            selected_numbers = set()
            for solution in self.current_solutions:
                for num in solution:
                    selected_numbers.add(num)
            
            # 写入数据
            for i, num in enumerate(self.input_numbers):
                # 第一列：输入数字
                worksheet.write(i + 1, 0, round(num, 2), normal_format)
                
                # 第二列：是否选中
                if num in selected_numbers:
                    worksheet.write(i + 1, 1, "是", highlight_format)
                else:
                    worksheet.write(i + 1, 1, "否", normal_format)
            
            workbook.close()
            self.status_var.set(f"结果已导出到Excel文件: {os.path.basename(file_path)}")
            
            # 尝试打开导出的文件
            try:
                os.startfile(file_path)
            except:
                pass  # 如果无法打开文件，静默失败
                
        except Exception as e:
            messagebox.showerror("导出错误", f"无法导出文件: {str(e)}")

def main():
    """主函数"""
    root = tk.Tk()
    app = SubsetSumApp(root)
    
    # 设置窗口图标和主题
    if platform.system() == "Windows":
        root.iconbitmap(default="")
    
    # 启动应用
    root.mainloop()

if __name__ == "__main__":
    main()
