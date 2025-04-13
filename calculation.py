"""
计算模块
负责子集和问题的求解和可视化
"""

import threading
import time
import traceback
import queue
import tkinter as tk
from tkinter import messagebox
from typing import List, Dict, Any, Tuple, Optional, Callable
import matplotlib
matplotlib.use('TkAgg')  # 使用TkAgg后端
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np

# 从subset_sum_wrapper导入需要的内容
from subset_sum_wrapper import SubsetSumSolver


class CalculationManager:
    """计算管理类"""
    
    def __init__(self, 
                 on_progress_update: Callable[[float], None], 
                 on_result: Callable[[List[List[float]], float], None],
                 on_error: Callable[[str], None]):
        """初始化计算管理器
        
        Args:
            on_progress_update: 进度更新回调函数
            on_result: 结果回调函数
            on_error: 错误回调函数
        """
        self.solver = SubsetSumSolver()
        self.calculation_thread = None
        self.result_queue = queue.Queue()
        self.on_progress_update = on_progress_update
        self.on_result = on_result
        self.on_error = on_error
        
        # 设置进度回调
        try:
            if hasattr(self.solver, 'set_progress_callback'):
                self.solver.set_progress_callback(
                    lambda p: self.on_progress_update(p)
                )
        except Exception as e:
            print(f"设置进度回调失败: {str(e)}")
    
    def start_calculation(self, numbers: List[float], target: float, max_solutions: int, memory_limit: int):
        """开始计算
        
        Args:
            numbers: 输入数字列表
            target: 目标和
            max_solutions: 最大解决方案数量
            memory_limit: 内存限制(MB)
        """
        # 创建结果队列
        self.result_queue = queue.Queue()
        
        # 启动计算线程
        self.calculation_thread = threading.Thread(
            target=self._calculation_worker,
            args=(numbers, target, max_solutions, memory_limit)
        )
        self.calculation_thread.daemon = True
        self.calculation_thread.start()
    
    def _calculation_worker(self, numbers: List[float], target: float, max_solutions: int, memory_limit: int):
        """计算工作线程
        
        Args:
            numbers: 输入数字列表
            target: 目标和
            max_solutions: 最大解决方案数量
            memory_limit: 内存限制(MB)
        """
        start_time = time.time()
        
        try:
            # 调用求解器
            solutions = self.solver.find_subsets(numbers, target, max_solutions, memory_limit)
            
            # 计算用时
            elapsed_time = time.time() - start_time
            
            # 使用消息队列将结果发送
            self.result_queue.put(("success", solutions, elapsed_time))
            
        except Exception as e:
            # 使用消息队列发送错误
            error_msg = f"计算出错: {str(e)}\n{traceback.format_exc()}"
            self.result_queue.put(("error", error_msg, 0))
    
    def check_queue(self):
        """检查结果队列，返回是否有结果
        
        Returns:
            是否有结果
        """
        try:
            # 非阻塞方式检查队列
            result = self.result_queue.get_nowait()
            
            if result[0] == "success":
                solutions, elapsed_time = result[1], result[2]
                self.on_result(solutions, elapsed_time)
                return True
            elif result[0] == "error":
                self.on_error(result[1])
                return True
            
        except queue.Empty:
            # 队列为空，检查是否已经计算完毕但线程还活着
            if self.calculation_thread and not self.calculation_thread.is_alive():
                # 线程已结束但队列为空，可能是完成了但没有输出结果
                return True
            # 队列为空，继续等待
            return False
        
        return False
        
    def start_calculation_with_progress(self, numbers: List[float], target: float, max_solutions: int, memory_limit: int, root_window):
        """开始计算并设置进度更新（带UI刷新）
        
        Args:
            numbers: 输入数字列表
            target: 目标和
            max_solutions: 最大解决方案数量
            memory_limit: 内存限制(MB)
            root_window: 根窗口，用于刷新UI
        """
        # 创建结果队列
        self.result_queue = queue.Queue()
        
        # 设置进度回调（包含UI刷新）
        if hasattr(self.solver, 'set_progress_callback'):
            def progress_callback(progress):
                # 更新进度
                if self.on_progress_update:
                    self.on_progress_update(progress)
                # 刷新界面
                if root_window and root_window.winfo_exists():
                    try:
                        root_window.update()
                    except:
                        pass
            
            try:
                self.solver.set_progress_callback(progress_callback)
            except Exception as e:
                print(f"设置进度回调失败: {str(e)}")
        
        # 启动计算线程
        self.calculation_thread = threading.Thread(
            target=self._calculation_worker,
            args=(numbers, target, max_solutions, memory_limit)
        )
        self.calculation_thread.daemon = True
        self.calculation_thread.start()
    
    def stop_calculation(self):
        """停止计算"""
        if self.solver:
            self.solver.stop()


class Visualizer:
    """可视化管理类"""
    
    @staticmethod
    def create_visualization(canvas_frame, input_numbers: List[float], solution: List[float]):
        """创建可视化图表
        
        Args:
            canvas_frame: 画布框架
            input_numbers: 输入数字列表
            solution: 选中的解决方案
        """
        # 清空现有图表
        for widget in canvas_frame.winfo_children():
            widget.destroy()
        
        if not solution:
            return
        
        # 创建图表
        fig = Figure(figsize=(5, 4), dpi=100)
        
        # 创建子图1: 饼图 - 选中与未选中数字的比例
        ax1 = fig.add_subplot(121)
        selected_sum = sum(solution)
        total_sum = sum(input_numbers)
        not_selected_sum = total_sum - selected_sum
        
        ax1.pie(
            [selected_sum, not_selected_sum],
            labels=['选中', '未选中'],
            autopct='%1.1f%%',
            colors=['#4CAF50', '#F44336']
        )
        ax1.set_title('选中数字占比')
        
        # 创建子图2: 条形图 - 选中的数字
        ax2 = fig.add_subplot(122)
        indices = [str(i+1) for i in range(len(solution))]
        ax2.bar(indices, solution, color='#2196F3')
        ax2.set_title('选中的数字')
        ax2.set_xlabel('数字序号')
        ax2.set_ylabel('数值')
        
        # 调整布局
        fig.tight_layout()
        
        # 将图表添加到界面
        canvas = FigureCanvasTkAgg(fig, master=canvas_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
