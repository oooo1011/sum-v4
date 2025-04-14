"""
测试SIMD优化的性能
"""

import subset_sum
import time
import random
import config

def generate_random_numbers(count, min_val=1, max_val=1000):
    """生成随机数列表"""
    return [random.randint(min_val, max_val) for _ in range(count)]

def test_performance(numbers, target, max_solutions=10):
    """测试性能"""
    solver = subset_sum.SubsetSumSolver()
    
    start_time = time.time()
    solutions = solver.find_subsets(numbers, target, max_solutions)
    end_time = time.time()
    
    return solutions, end_time - start_time

def main():
    print("子集和求解器SIMD优化性能测试")
    print(f"使用版本: {config.APP_VERSION}")
    
    # 测试中等规模问题
    print("\n测试1: 中等规模问题")
    numbers = generate_random_numbers(30, 1, 100)
    target = sum(numbers) // 3
    solutions, duration = test_performance(numbers, target)
    print(f"找到 {len(solutions)} 个解")
    print(f"耗时: {duration:.6f} 秒")
    
    # 测试大规模问题
    print("\n测试2: 大规模问题")
    numbers = generate_random_numbers(40, 1, 1000)
    target = sum(numbers) // 4
    solutions, duration = test_performance(numbers, target)
    print(f"找到 {len(solutions)} 个解")
    print(f"耗时: {duration:.6f} 秒")

if __name__ == "__main__":
    main()
