"""
子集和求解器的Python包装器
提供与Rust核心算法的接口
"""

import os
import sys
import time
import threading
from typing import List, Optional, Tuple

# 读取版本信息文件
def read_version_info():
    """读取版本信息文件"""
    try:
        # 尝试从可能的位置读取版本信息文件
        possible_paths = [
            os.path.join(os.path.dirname(__file__), "version_info.txt"),
            os.path.join(os.path.dirname(__file__), "target", "release", "version_info.txt"),
            os.path.join(os.path.dirname(__file__), "target", "debug", "version_info.txt"),
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                print(f"找到版本信息文件: {path}")
                with open(path, "r", encoding="utf-8") as f:
                    version = f.read().strip()
                    print(f"读取到版本信息: {version}")
                    return version
        
        print("未找到版本信息文件")
    except Exception as e:
        print(f"读取版本信息时出错: {e}")
    
    return "1.0.0-python"  # 默认版本号

# 获取版本信息
RUST_VERSION = read_version_info()

# 尝试导入Rust模块
RUST_AVAILABLE = False
try:
    # 从编译好的Rust模块导入
    import subset_sum
    RustSubsetSumSolver = subset_sum.SubsetSumSolver
    RUST_AVAILABLE = True
    
    print(f"成功导入Rust模块，版本: {RUST_VERSION}，将使用高性能实现")
except Exception as e:
    print(f"警告: 导入Rust模块时出错: {e}，将使用纯Python实现（性能较低）")
    RUST_AVAILABLE = False

# 纯Python实现（作为备用）
class PySubsetSumSolver:
    """子集和求解器的纯Python实现"""
    
    def __init__(self):
        """初始化求解器"""
        self.should_stop = False
        self.progress_callback = None
        self.progress = 0
        self.processed_combinations = 0
        self.total_combinations = 0
        # 内存监控（Python版本只提供模拟数据）
        self.memory_usage = 0
        self.peak_memory = 0
    
    def find_subsets(self, numbers: List[float], target: float, max_solutions: int = 1, memory_limit_mb: int = 1000) -> List[List[float]]:
        """查找和为目标值的子集"""
        if not numbers:
            raise ValueError("输入数字列表不能为空")
        
        # 重置状态
        self.should_stop = False
        self.progress = 0
        self.processed_combinations = 0
        
        # 计算可能的组合总数(2^n)，但注意避免溢出
        n = len(numbers)
        self.total_combinations = min(2 ** n, 2 ** 63 - 1)
        
        # 存储解决方案
        solutions = []
        current_subset = []
        
        # 开始回溯搜索
        self._backtrack(numbers, target, 0, 0, current_subset, solutions, max_solutions)
        
        return solutions
    
    def _backtrack(self, numbers, target, start, current_sum, current_subset, solutions, max_solutions):
        """回溯搜索算法"""
        # 检查是否应该停止
        if self.should_stop or len(solutions) >= max_solutions:
            return
        
        # 找到一个解
        if abs(current_sum - target) < 1e-6:  # 使用小阈值处理浮点数精度问题
            solutions.append(current_subset.copy())
            if len(solutions) >= max_solutions:
                self.should_stop = True
            return
        
        # 剪枝：如果当前和已经超过目标，不需要继续（假设所有数字都是正数）
        if current_sum > target:
            return
        
        # 继续搜索
        for i in range(start, len(numbers)):
            # 选择当前数字
            current_subset.append(numbers[i])
            current_sum += numbers[i]
            
            # 继续递归
            self._backtrack(numbers, target, i + 1, current_sum, current_subset, solutions, max_solutions)
            
            # 回溯，撤销选择
            current_subset.pop()
            current_sum -= numbers[i]
            
            # 检查是否应该停止
            if self.should_stop:
                break
        
        # 更新进度（只在顶层递归调用中）
        if start == 0:
            self.processed_combinations += 1
            self.progress = self.processed_combinations / self.total_combinations * 100
            if self.progress_callback:
                self.progress_callback(self.progress)
    
    def stop(self):
        """停止计算"""
        self.should_stop = True
    
    def get_progress(self):
        """获取计算进度（百分比）"""
        return self.progress
    
    def set_progress_callback(self, callback):
        """设置进度回调函数"""
        self.progress_callback = callback
        
    def get_version(self):
        """获取版本号"""
        return "1.0.0-python"
        
    def get_memory_usage(self):
        """获取内存使用情况（Python版本只返回模拟数据）"""
        # 简单模拟内存使用情况，对于纯Python版本只是估计值
        self.memory_usage = len(sys.modules) * 0.5  # 粗略估计
        self.peak_memory = self.memory_usage * 1.2
        return (self.memory_usage, self.peak_memory)
        
    def set_memory_limit(self, limit_mb):
        """设置内存限制（Python版本为空操作）"""
        # Python版本不支持真正的内存限制
        pass

# 统一接口，自动选择Rust或Python实现
class SubsetSumSolver:
    """子集和求解器统一接口"""
    
    def __init__(self):
        """初始化求解器，自动选择实现"""
        if RUST_AVAILABLE:
            self._solver = RustSubsetSumSolver()
        else:
            self._solver = PySubsetSumSolver()
    
    def find_subsets(self, numbers: List[float], target: float, max_solutions: int = 1, memory_limit_mb: int = 1000) -> List[List[float]]:
        """查找和为目标值的子集"""
        return self._solver.find_subsets(numbers, target, max_solutions, memory_limit_mb)
    
    def stop(self):
        """停止计算"""
        self._solver.stop()
    
    def get_progress(self):
        """获取计算进度"""
        return self._solver.get_progress()
    
    def get_version(self):
        """获取版本号"""
        return RUST_VERSION
    
    def set_progress_callback(self, callback):
        """设置进度回调函数"""
        if hasattr(self._solver, 'set_progress_callback'):
            self._solver.set_progress_callback(callback)
        # 如果Rust模块不支持进度回调，在Python端处理
        elif isinstance(self._solver, PySubsetSumSolver):
            self._solver.progress_callback = callback
        # 其他情况下静默失败，不影响程序运行
    
    def get_memory_usage(self):
        """获取内存使用情况"""
        if hasattr(self._solver, 'get_memory_usage'):
            return self._solver.get_memory_usage()
        return (0.0, 0.0)  # 默认返回
        
    def set_memory_limit(self, limit_mb):
        """设置内存限制"""
        if hasattr(self._solver, 'set_memory_limit'):
            self._solver.set_memory_limit(limit_mb)
