"""
内存优化效果测试脚本
"""

import time
import random
from subset_sum_wrapper import SubsetSumSolver

def generate_random_numbers(count, min_val=1.0, max_val=100.0):
    """生成随机测试数据"""
    return [random.uniform(min_val, max_val) for _ in range(count)]

def test_memory_usage(size, target_ratio=0.5, max_solutions=5):
    """测试内存使用情况"""
    solver = SubsetSumSolver()
    
    # 生成测试数据
    numbers = generate_random_numbers(size)
    
    # 设置目标值为总和的一定比例
    total_sum = sum(numbers)
    target = total_sum * target_ratio
    
    print(f"\n========= 测试数据大小: {size} =========")
    print(f"目标和: {target:.2f} (总和的{target_ratio*100:.0f}%)")
    
    # 记录开始时间
    start_time = time.time()
    
    # 开始计算
    solutions = solver.find_subsets(numbers, target, max_solutions, memory_limit_mb=1024)
    
    # 计算用时
    elapsed_time = time.time() - start_time
    
    # 获取内存使用情况
    current_mem, peak_mem = solver.get_memory_usage()
    
    # 输出结果
    print(f"找到解决方案: {len(solutions)} 个")
    print(f"计算用时: {elapsed_time:.3f} 秒")
    print(f"当前内存使用: {current_mem:.2f} MB")
    print(f"峰值内存使用: {peak_mem:.2f} MB")
    
    return elapsed_time, peak_mem, len(solutions)

def run_benchmark():
    """运行多组测试，对比不同数据规模的性能"""
    print("====== 子集和求解器内存优化测试 ======")
    print(f"使用求解器版本: {SubsetSumSolver().get_version()}")
    
    results = []
    
    # 测试不同规模的数据
    for size in [20, 30, 40, 50]:
        time_used, memory_peak, solution_count = test_memory_usage(size)
        results.append((size, time_used, memory_peak, solution_count))
    
    # 汇总结果
    print("\n======= 测试结果汇总 =======")
    print("数据大小  |  耗时(秒)  |  峰值内存(MB)  |  解决方案数")
    print("---------------------------------------------")
    for size, time_used, memory_peak, solution_count in results:
        print(f"{size:^8}  |  {time_used:^9.3f}  |  {memory_peak:^13.2f}  |  {solution_count:^8}")

if __name__ == "__main__":
    run_benchmark()
