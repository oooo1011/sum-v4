"""
子集和求解器性能测试脚本
测试不同规模的数据集和不同算法的性能差异
"""

import time
import random
import pandas as pd
import matplotlib.pyplot as plt
from subset_sum import SubsetSumSolver

def generate_test_data(size, min_val=1, max_val=1000, decimal_places=2):
    """生成指定大小的测试数据"""
    return [round(random.uniform(min_val, max_val), decimal_places) for _ in range(size)]

def run_performance_test(data_sizes=[20, 50, 80, 100, 150], repeat=3):
    """运行性能测试，比较不同规模和不同算法的性能"""
    results = []
    solver = SubsetSumSolver()  # 使用默认配置
    
    for size in data_sizes:
        print(f"\n==== 测试数据大小: {size} ====")
        
        # 从测试文件加载数据，如果存在的话
        try:
            if size <= 30:
                with open("test_small.txt", "r") as f:
                    numbers = [float(line.strip()) for line in f][:size]
            elif size <= 80:
                with open("test_medium.txt", "r") as f:
                    numbers = [float(line.strip()) for line in f][:size]
            else:
                with open("test_large.txt", "r") as f:
                    numbers = [float(line.strip()) for line in f][:size]
        except:
            # 如果文件不存在，生成随机数据
            numbers = generate_test_data(size)
            
        # 计算一个合理的目标和（约为总和的30%）
        total_sum = sum(numbers)
        target = total_sum * 0.3
        
        # 测试位运算算法 (<=32)
        if size <= 32:
            times = []
            for i in range(repeat):
                start_time = time.time()
                solutions = solver.find_subsets(numbers, target, 1)
                end_time = time.time()
                times.append(end_time - start_time)
                print(f"  位运算算法 (run {i+1}): {times[-1]:.4f}秒, 找到 {len(solutions)} 个解")
            
            avg_time = sum(times) / len(times)
            results.append({
                'size': size, 
                'algorithm': '位运算', 
                'time': avg_time,
                'solutions': len(solutions)
            })
        
        # 测试动态规划算法 (<=100 & 目标和较小)
        if size <= 100 and target < 10000:
            times = []
            for i in range(repeat):
                start_time = time.time()
                solutions = solver.find_subsets(numbers, target, 1)
                end_time = time.time()
                times.append(end_time - start_time)
                print(f"  动态规划算法 (run {i+1}): {times[-1]:.4f}秒, 找到 {len(solutions)} 个解")
            
            avg_time = sum(times) / len(times)
            results.append({
                'size': size, 
                'algorithm': '动态规划', 
                'time': avg_time,
                'solutions': len(solutions)
            })
        
        # 测试回溯算法 (所有大小)
        times = []
        for i in range(repeat):
            start_time = time.time()
            solutions = solver.find_subsets(numbers, target, 1)
            end_time = time.time()
            times.append(end_time - start_time)
            print(f"  回溯算法 (run {i+1}): {times[-1]:.4f}秒, 找到 {len(solutions)} 个解")
        
        avg_time = sum(times) / len(times)
        results.append({
            'size': size, 
            'algorithm': '回溯', 
            'time': avg_time,
            'solutions': len(solutions)
        })
    
    return results

def plot_results(results):
    """绘制性能测试结果图表"""
    df = pd.DataFrame(results)
    
    plt.figure(figsize=(12, 6))
    pivot_table = df.pivot(index='size', columns='algorithm', values='time')
    pivot_table.plot(marker='o', linewidth=2)
    
    plt.title('子集和算法性能对比')
    plt.xlabel('数据集大小')
    plt.ylabel('执行时间(秒)')
    plt.grid(True)
    plt.legend(title='算法')
    plt.savefig('performance_comparison.png', dpi=300, bbox_inches='tight')
    plt.show()
    
    return df

if __name__ == "__main__":
    # 测试不同大小的数据集
    data_sizes = [20, 40, 60, 80, 100]
    results = run_performance_test(data_sizes, repeat=2)
    
    # 输出结果表格
    df = pd.DataFrame(results)
    print("\n==== 性能测试结果 ====")
    print(df.to_string(index=False))
    
    # 保存结果到CSV
    df.to_csv('performance_results.csv', index=False)
    print("\n结果已保存到 performance_results.csv")
    
    # 绘制图表
    try:
        plot_results(results)
        print("性能对比图已保存到 performance_comparison.png")
    except Exception as e:
        print(f"绘图出错: {e}")
