"""
子集和求解器的Python包装器
提供与Rust核心算法的接口
"""

import os
import sys
import time
import threading
from typing import List, Optional, Tuple

# 尝试导入Rust模块
RUST_AVAILABLE = False
try:
    # 从编译好的Rust模块导入
    import subset_sum
    RustSubsetSumSolver = subset_sum.SubsetSumSolver
    RUST_AVAILABLE = True
    print("成功导入Rust模块，将使用高性能实现")
except Exception as e:
    print(f"警告: 导入Rust模块时出错: {e}，将使用纯Python实现（性能较低）")
    RUST_AVAILABLE = False

# 纯Python实现（作为备用）
class PySubsetSumSolver:
    """纯Python实现的子集和求解器（作为备用）"""
    
    def __init__(self):
        """初始化求解器"""
        self._progress = 0.0
        self._should_stop = False
        self._lock = threading.Lock()
    
    def reset(self):
        """重置求解器状态"""
        self._progress = 0.0
        self._should_stop = False
    
    def stop(self):
        """停止计算"""
        self._should_stop = True
    
    def get_progress(self) -> float:
        """获取当前进度百分比"""
        return self._progress
    
    def find_subsets(self, numbers: List[float], target: float, 
                    max_solutions: int = 1, memory_limit_mb: int = 1000) -> List[List[float]]:
        """
        查找和为目标值的子集
        
        Args:
            numbers: 输入数字列表
            target: 目标和
            max_solutions: 最大解决方案数量
            memory_limit_mb: 内存限制（MB）
        
        Returns:
            找到的子集列表
        """
        self.reset()
        
        # 排序可以提高剪枝效率
        sorted_numbers = sorted(numbers)
        solutions = []
        
        def backtrack(start: int, current_sum: float, current_subset: List[int]):
            # 检查是否应该停止
            if self._should_stop:
                return
            
            # 更新进度
            self._progress = min(99.9, (start / len(sorted_numbers)) * 100)
            
            # 找到一个解
            if abs(current_sum - target) < 1e-6:
                with self._lock:
                    if len(solutions) < max_solutions:
                        solutions.append([sorted_numbers[i] for i in current_subset])
                        if len(solutions) >= max_solutions:
                            self._should_stop = True
                            return
            
            # 剪枝
            if current_sum > target or start >= len(sorted_numbers):
                return
            
            # 选择当前数字
            current_subset.append(start)
            backtrack(start + 1, current_sum + sorted_numbers[start], current_subset)
            current_subset.pop()
            
            # 不选择当前数字
            backtrack(start + 1, current_sum, current_subset)
        
        # 尝试每个起始位置
        for i in range(len(sorted_numbers)):
            if self._should_stop:
                break
                
            # 单个数字就是解
            if abs(sorted_numbers[i] - target) < 1e-6:
                solutions.append([sorted_numbers[i]])
                if len(solutions) >= max_solutions:
                    break
            
            # 从当前数字开始回溯
            backtrack(i + 1, sorted_numbers[i], [i])
        
        self._progress = 100.0
        return solutions[:max_solutions]

# 统一接口
class SubsetSumSolver:
    """子集和求解器统一接口"""
    
    def __init__(self):
        """初始化求解器"""
        if RUST_AVAILABLE:
            self._solver = RustSubsetSumSolver()
        else:
            self._solver = PySubsetSumSolver()
        self._running = False
        self._progress_thread = None
        self._callback = None
    
    def reset(self):
        """重置求解器状态"""
        self._solver.reset()
        self._running = False
        if self._progress_thread and self._progress_thread.is_alive():
            self._progress_thread.join()
        self._progress_thread = None
    
    def stop(self):
        """停止计算"""
        if self._running:
            self._solver.stop()
            self._running = False
    
    def get_progress(self) -> float:
        """获取当前进度百分比"""
        return self._solver.get_progress()
    
    def set_progress_callback(self, callback):
        """设置进度回调函数"""
        self._callback = callback
    
    def _progress_monitor(self):
        """进度监控线程"""
        last_progress = 0
        while self._running:
            current_progress = self.get_progress()
            if self._callback and abs(current_progress - last_progress) >= 0.5:
                self._callback(current_progress)
                last_progress = current_progress
            time.sleep(0.1)
    
    def find_subsets(self, numbers: List[float], target: float, 
                    max_solutions: int = 1, memory_limit_mb: int = 1000) -> List[List[float]]:
        """
        查找和为目标值的子集
        
        Args:
            numbers: 输入数字列表
            target: 目标和
            max_solutions: 最大解决方案数量
            memory_limit_mb: 内存限制（MB）
        
        Returns:
            找到的子集列表
        """
        self.reset()
        self._running = True
        
        # 启动进度监控线程
        if self._callback:
            self._progress_thread = threading.Thread(target=self._progress_monitor)
            self._progress_thread.daemon = True
            self._progress_thread.start()
        
        try:
            result = self._solver.find_subsets(numbers, target, max_solutions, memory_limit_mb)
        finally:
            self._running = False
            if self._callback:
                self._callback(100.0)
        
        return result
