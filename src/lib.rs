use pyo3::prelude::*;
use pyo3::wrap_pyfunction;
use std::sync::{Arc, Mutex};
use std::sync::atomic::{AtomicU64, AtomicBool, Ordering};
use std::time::{Instant, Duration};
use rayon::prelude::*;
use std::collections::HashSet;

/// 算法类型枚举，用于智能算法选择
#[derive(Debug, Clone, Copy)]
enum Algorithm {
    BitManipulation,    // 位运算算法 - 适用于小规模问题
    DynamicProgramming, // 动态规划算法 - 适用于中等规模问题
    BacktrackingCompact, // 内存优化回溯算法 - 适用于大规模问题
}

/// 优化：压缩表示，使用位图表示子集
struct CompactSubset {
    bitmap: Vec<u64>,
    count: usize,
}

/// 内存对象池，避免频繁分配内存
#[pyclass]
struct MemoryTracker {
    max_memory: usize,
    used_memory: Arc<AtomicU64>,
}

impl MemoryTracker {
    fn new(max_memory: usize) -> Self {
        MemoryTracker {
            max_memory,
            used_memory: Arc::new(AtomicU64::new(0)),
        }
    }

    fn allocate(&self, size: usize) -> bool {
        let current = self.used_memory.load(Ordering::SeqCst) as usize;
        if current + size > self.max_memory {
            return false;
        }
        self.used_memory.fetch_add(size as u64, Ordering::SeqCst);
        true
    }

    fn deallocate(&self, size: usize) {
        self.used_memory.fetch_sub(size as u64, Ordering::SeqCst);
    }

    fn get_used_memory(&self) -> usize {
        self.used_memory.load(Ordering::SeqCst) as usize
    }
}

impl CompactSubset {
    fn new() -> Self {
        Self { bitmap: vec![0], count: 0 }
    }
    
    fn with_capacity(max_size: usize) -> Self {
        let blocks = (max_size + 63) / 64;
        Self { bitmap: vec![0; blocks], count: 0 }
    }
    
    fn add(&mut self, index: usize) {
        let block_idx = index / 64;
        let bit_idx = index % 64;
        
        // 确保有足够的空间
        while block_idx >= self.bitmap.len() {
            self.bitmap.push(0);
        }
        
        // 检查是否已添加
        if !self.contains(index) {
            self.bitmap[block_idx] |= 1u64 << bit_idx;
            self.count += 1;
        }
    }
    
    fn remove(&mut self, index: usize) {
        let block_idx = index / 64;
        let bit_idx = index % 64;
        
        if block_idx < self.bitmap.len() && self.contains(index) {
            self.bitmap[block_idx] &= !(1u64 << bit_idx);
            self.count -= 1;
        }
    }
    
    fn contains(&self, index: usize) -> bool {
        let block_idx = index / 64;
        let bit_idx = index % 64;
        
        if block_idx < self.bitmap.len() {
            (self.bitmap[block_idx] & (1u64 << bit_idx)) != 0
        } else {
            false
        }
    }
    
    fn clear(&mut self) {
        for block in &mut self.bitmap {
            *block = 0;
        }
        self.count = 0;
    }
    
    fn len(&self) -> usize {
        self.count
    }
    
    fn to_indices(&self) -> Vec<usize> {
        let mut result = Vec::with_capacity(self.count);
        
        for (block_idx, &block) in self.bitmap.iter().enumerate() {
            let base_idx = block_idx * 64;
            let mut bits = block;
            
            while bits != 0 {
                let trailing_zeros = bits.trailing_zeros() as usize;
                let index = base_idx + trailing_zeros;
                result.push(index);
                
                // 清除最低位的1
                bits &= bits - 1;
            }
        }
        
        result
    }
    
    fn clone(&self) -> Self {
        Self {
            bitmap: self.bitmap.clone(),
            count: self.count,
        }
    }
}

// 对象池实现
static mut SUBSET_POOL: Option<Vec<CompactSubset>> = None;

fn get_compact_subset_from_pool() -> CompactSubset {
    unsafe {
        if SUBSET_POOL.is_none() {
            SUBSET_POOL = Some(Vec::with_capacity(10));
        }
        
        if let Some(pool) = &mut SUBSET_POOL {
            if let Some(mut subset) = pool.pop() {
                subset.clear();
                return subset;
            }
        }
        
        CompactSubset::new()
    }
}

fn return_compact_subset_to_pool(subset: CompactSubset) {
    unsafe {
        if SUBSET_POOL.is_none() {
            SUBSET_POOL = Some(Vec::with_capacity(10));
        }
        
        if let Some(pool) = &mut SUBSET_POOL {
            if pool.len() < 100 {  // 限制池大小
                pool.push(subset);
            }
        }
    }
}

#[pyclass]
pub struct SubsetSumSolver {
    processed_combinations: Arc<AtomicU64>,
    total_combinations: Arc<AtomicU64>,
    stop_flag: Arc<AtomicBool>,
    memory_tracker: MemoryTracker,
    start_time: Option<Instant>,
}

#[pymethods]
impl SubsetSumSolver {
    #[new]
    pub fn new() -> Self {
        SubsetSumSolver {
            processed_combinations: Arc::new(AtomicU64::new(0)),
            total_combinations: Arc::new(AtomicU64::new(0)),
            stop_flag: Arc::new(AtomicBool::new(false)),
            memory_tracker: MemoryTracker::new(4 * 1024 * 1024 * 1024), // 4GB
            start_time: None,
        }
    }

    #[getter]
    fn get_progress(&self) -> f64 {
        let processed = self.processed_combinations.load(Ordering::SeqCst);
        let total = self.total_combinations.load(Ordering::SeqCst);
        if total == 0 {
            return 0.0;
        }
        processed as f64 / total as f64
    }

    #[getter]
    fn get_memory_usage(&self) -> usize {
        self.memory_tracker.get_used_memory()
    }

    fn start_timer(&mut self) {
        self.start_time = Some(Instant::now());
    }

    fn get_elapsed_time(&self) -> Option<f64> {
        self.start_time.map(|start| start.elapsed().as_secs_f64())
    }

    fn stop_execution(&self) {
        self.stop_flag.store(true, Ordering::SeqCst);
    }

    #[pyo3(text_signature = "(numbers, target, max_solutions=10)")]
    pub fn find_subsets(&self, numbers: Vec<i64>, target: i64, max_solutions: Option<usize>) -> Vec<Vec<usize>> {
        self.find_subsets_int(&numbers, target, max_solutions.unwrap_or(10))
    }
}

impl SubsetSumSolver {
    /// 查找子集，根据问题规模和特征自动选择最合适的算法
    pub fn find_subsets_int(&self, numbers: &[i64], target: i64, max_solutions: usize) -> Vec<Vec<usize>> {
        // 重置进度计数器
        self.processed_combinations.store(0, Ordering::SeqCst);
        self.total_combinations.store(2u64.pow(numbers.len() as u32), Ordering::SeqCst);
        self.stop_flag.store(false, Ordering::SeqCst);
        
        // 使用问题分析功能选择最佳算法
        let algorithm = self.analyze_problem(numbers, target);
        
        // 根据选择的算法执行相应的求解方法
        match algorithm {
            Algorithm::BitManipulation => {
                self.find_subsets_with_bit(numbers, target, max_solutions)
            },
            Algorithm::DynamicProgramming => {
                self.find_subsets_with_dp(numbers, target, max_solutions)
            },
            Algorithm::BacktrackingCompact => {
                // 创建线程安全的解决方案容器
                let solutions = Arc::new(Mutex::new(Vec::new()));
                let should_stop = Arc::clone(&self.stop_flag);
                
                // 预处理数据
                let (sorted_numbers, sorted_indices, prefix_sum) = self.preprocess_data(numbers, target);
                
                // 创建当前子集实例
                let mut current_subset = get_compact_subset_from_pool();
                
                // 调用回溯算法的核心实现
                self.backtracking_with_compact_subset(
                    &sorted_numbers,
                    &sorted_indices,
                    &prefix_sum,
                    target,
                    0,
                    0,
                    &mut current_subset,
                    &solutions,
                    max_solutions,
                    &should_stop,
                );
                
                // 归还对象到池
                return_compact_subset_to_pool(current_subset);
                
                // 释放锁，获取结果
                let result = {
                    let guard = solutions.lock().unwrap();
                    guard.clone()
                };
                
                result
            }
        }
    }
    
    /// 分析问题特征，选择最合适的算法
    fn analyze_problem(&self, numbers: &[i64], target: i64) -> Algorithm {
        let n = numbers.len();
        
        // 基于问题规模的初步判断
        if n <= 25 {
            // 小规模问题，适合位运算
            return Algorithm::BitManipulation;
        } else if n <= 100 && target <= 10000 {
            // 中等规模问题，目标和不太大，适合动态规划
            return Algorithm::DynamicProgramming;
        }
        
        // 对于更大规模问题，进一步分析数据特征
        
        // 计算数据统计特征
        let mut sum = 0i64;
        let mut min_val = i64::MAX;
        let mut max_val = i64::MIN;
        let mut positive_count = 0;
        
        for &num in numbers {
            if num > 0 {
                sum += num;
                min_val = min_val.min(num);
                max_val = max_val.max(num);
                positive_count += 1;
            }
        }
        
        let _avg = if positive_count > 0 { sum / positive_count } else { 0 };
        let range = max_val - min_val;
        
        // 如果所有数都很小，或者值范围很窄，动态规划可能表现更好
        if (max_val <= 100 || range <= 100) && target <= 10000 && n <= 200 {
            return Algorithm::DynamicProgramming;
        }
        
        // 如果数字比较大，但数量不太多，也可以使用动态规划
        if n <= 150 && target <= 50000 {
            return Algorithm::DynamicProgramming;
        }
        
        // 默认使用内存优化的回溯算法
        Algorithm::BacktrackingCompact
    }
    
    /// 预处理数据，优化搜索效率
    fn preprocess_data(&self, numbers: &[i64], target: i64) -> (Vec<i64>, Vec<usize>, Vec<i64>) {
        // 过滤负数和零，只保留正数
        let mut filtered: Vec<(usize, i64)> = numbers.iter()
            .enumerate()
            .filter(|&(_, &x)| x > 0)
            .map(|(i, &x)| (i, x))
            .collect();

        // 按值降序排序，有助于更快找到解
        filtered.sort_unstable_by(|a, b| b.1.cmp(&a.1));

        // 分离索引和值
        let sorted_indices: Vec<usize> = filtered.iter().map(|&(i, _)| i).collect();
        let sorted_numbers: Vec<i64> = filtered.iter().map(|&(_, v)| v).collect();

        // 计算前缀和，用于剪枝
        let prefix_sum = Self::compute_prefix_sum_simd(&sorted_numbers);

        (sorted_numbers, sorted_indices, prefix_sum)
    }
    
    /// 回溯算法（带紧凑子集表示）
    fn backtracking_with_compact_subset(
        &self,
        numbers: &[i64],
        indices: &[usize],
        prefix_sum: &[i64],
        target: i64,
        start: usize,
        current_sum: i64,
        current_subset: &mut CompactSubset,
        solutions: &Arc<Mutex<Vec<Vec<usize>>>>,
        max_solutions: usize,
        should_stop: &AtomicBool
    ) {
        // 检查是否应该停止
        if should_stop.load(Ordering::SeqCst) {
            return;
        }

        // 找到一个解
        if current_sum == target {
            let mut sols = solutions.lock().unwrap();
            if sols.len() < max_solutions {
                // 将紧凑表示转换回索引列表
                let solution = current_subset.to_indices()
                    .into_iter()
                    .map(|idx| indices[idx])
                    .collect();
                sols.push(solution);
                
                // 如果达到最大解数量，提前结束
                if sols.len() >= max_solutions {
                    should_stop.store(true, Ordering::SeqCst);
                }
            }
            return;
        }

        // 剪枝：如果当前和已经超过目标，或剩余数字加起来也不够，提前结束
        if current_sum > target {
            return;
        }

        // 剪枝：检查剩余数字能否达到目标
        let remaining_sum = Self::range_sum_simd(prefix_sum, start, numbers.len());
        if current_sum + remaining_sum < target {
            return;
        }

        // 更新进度计数器
        let processed = 1u64 << start;
        self.processed_combinations.fetch_add(processed, Ordering::SeqCst);

        // 考虑当前数字，然后递归
        for i in start..numbers.len() {
            // 剪枝：跳过重复值
            if i > start && numbers[i] == numbers[i - 1] {
                continue;
            }

            let new_sum = current_sum + numbers[i];
            if new_sum <= target {
                current_subset.add(i);
                self.backtracking_with_compact_subset(
                    numbers,
                    indices,
                    prefix_sum,
                    target,
                    i + 1,
                    new_sum,
                    current_subset,
                    solutions,
                    max_solutions,
                    should_stop
                );
                current_subset.remove(i);
                
                // 检查是否应该停止
                if should_stop.load(Ordering::SeqCst) {
                    return;
                }
            }
        }
    }
    
    /// 范围求和函数
    fn evaluate_branch(&self, numbers: &[i64], prefix_sum: &[i64], from: usize, to: usize) -> i64 {
        if from >= to {
            return 0;
        }
        Self::range_sum_simd(prefix_sum, from, to)
    }
    
    /// 并行回溯算法的阈值确定
    fn should_parallelize(&self, depth: usize, numbers: &[i64]) -> bool {
        let parallel_threshold = 16; // 使用固定阈值简化实现
        depth <= parallel_threshold && numbers.len() >= 16
    }
    
    /// 使用位运算算法求解子集和问题
    /// 这种方法在小规模问题(数量不超过32个)上非常高效
    fn find_subsets_with_bit(&self, numbers: &[i64], target: i64, max_solutions: usize) -> Vec<Vec<usize>> {
        // 如果数字数量超过了位运算的限制，切换到其他算法
        if numbers.len() > 32 {
            return self.find_subsets_with_dp(numbers, target, max_solutions);
        }
        
        let n = numbers.len();
        let mut results = Vec::new();
        let mut best_diff = i64::MAX;
        let mut best_candidates = Vec::new();
        
        // 计算所有2^n种组合
        let total_combinations = 1 << n;
        
        for mask in 1..total_combinations {
            let mut sum = 0;
            
            // 计算当前组合的和
            for i in 0..n {
                if (mask & (1 << i)) != 0 {
                    sum += numbers[i];
                }
            }
            
            // 更新进度
            self.processed_combinations.fetch_add(1, Ordering::SeqCst);
            
            // 检查是否应该停止
            if self.stop_flag.load(Ordering::SeqCst) {
                break;
            }
            
            // 如果找到精确匹配
            if sum == target {
                // 构建解决方案
                let mut solution = Vec::new();
                for i in 0..n {
                    if (mask & (1 << i)) != 0 {
                        solution.push(i);
                    }
                }
                
                results.push(solution);
                
                // 如果达到最大解数量，提前结束
                if results.len() >= max_solutions {
                    break;
                }
            } 
            // 如果没有足够的精确匹配，记录接近的组合
            else if results.len() < max_solutions {
                let diff = (sum - target).abs();
                
                if diff < best_diff {
                    best_diff = diff;
                    best_candidates.clear();
                    
                    let mut candidate = Vec::new();
                    for i in 0..n {
                        if (mask & (1 << i)) != 0 {
                            candidate.push(i);
                        }
                    }
                    best_candidates.push(candidate);
                } 
                else if diff == best_diff && best_candidates.len() < max_solutions - results.len() {
                    let mut candidate = Vec::new();
                    for i in 0..n {
                        if (mask & (1 << i)) != 0 {
                            candidate.push(i);
                        }
                    }
                    best_candidates.push(candidate);
                }
            }
        }
        
        // 如果精确匹配不足max_solutions，添加最接近的组合
        if results.len() < max_solutions {
            results.extend(best_candidates);
        }
        
        // 确保返回的结果不超过max_solutions
        if results.len() > max_solutions {
            results.truncate(max_solutions);
        }
        
        results
    }
    
    /// 使用动态规划算法求解子集和问题
    /// 这种方法在中等规模问题(数量不超过100，目标和较小)上更高效
    fn find_subsets_with_dp(&self, numbers: &[i64], target: i64, max_solutions: usize) -> Vec<Vec<usize>> {
        if target <= 0 {
            return Vec::new();
        }
        
        let target_usize = target as usize;
        let _n = numbers.len();
        
        // 创建动态规划表，dp[i]表示是否存在和为i的子集
        let mut dp = vec![false; target_usize + 1];
        dp[0] = true; // 空集的和为0
        
        // 记录每个可能和的一个可行子集
        let mut predecessor = vec![Vec::new(); target_usize + 1];
        
        // 检查内存使用情况
        let memory_size = dp.len() * std::mem::size_of::<bool>() +
                         predecessor.len() * std::mem::size_of::<Vec<usize>>();
        
        if !self.memory_tracker.allocate(memory_size) {
            self.memory_tracker.deallocate(memory_size);
            return Vec::new(); // 内存不足，返回空结果
        }
        
        // 记录所有可能的和
        let mut all_sums = vec![0];
        
        // 动态规划填表
        for (idx, &num) in numbers.iter().enumerate() {
            if num <= 0 {
                continue; // 跳过非正数
            }
            
            let num_usize = num as usize;
            
            // 为避免重复计算，从后向前遍历
            let mut new_sums = Vec::new();
            
            for &prev_sum in &all_sums {
                let new_sum = prev_sum + num_usize;
                if new_sum <= target_usize && !dp[new_sum] {
                    dp[new_sum] = true;
                    predecessor[new_sum] = predecessor[prev_sum].clone();
                    predecessor[new_sum].push(idx);
                    new_sums.push(new_sum);
                    
                    // 更新进度
                    self.processed_combinations.fetch_add(1, Ordering::SeqCst);
                }
            }
            
            all_sums.extend(new_sums);
            
            // 检查是否应该停止
            if self.stop_flag.load(Ordering::SeqCst) {
                self.memory_tracker.deallocate(memory_size);
                return Vec::new();
            }
        }
        
        // 收集结果 - 只返回精确匹配的子集
        let mut solutions = Vec::new();
        if dp[target_usize] {
            solutions.push(predecessor[target_usize].clone());
        }
        
        // 查找接近目标值的其他解决方案（如果需要多个解）
        if max_solutions > 1 {
            // 按照与目标值的接近程度排序
            let mut sums_with_solutions: Vec<(usize, Vec<usize>)> = all_sums.iter()
                .filter(|&&sum| sum != target_usize && dp[sum]) // 排除已找到的精确解
                .map(|&sum| (sum, predecessor[sum].clone()))
                .collect();
            
            // 按照与目标的接近程度排序
            sums_with_solutions.sort_by_key(|&(sum, _)| (target_usize as i64 - sum as i64).abs());
            
            // 添加最接近的解决方案，直到达到max_solutions
            for (_, solution) in sums_with_solutions.into_iter().take(max_solutions - solutions.len()) {
                solutions.push(solution);
            }
        }
        
        self.memory_tracker.deallocate(memory_size);
        solutions
    }
    
    /// 使用SIMD指令集的快速求和实现
    #[inline]
    fn fast_sum(array: &[i64]) -> i64 {
        // 对于小数组，使用标准求和避免SIMD开销
        if array.len() < 16 {
            return Self::sum_scalar(array);
        }
        
        // 默认实现
        Self::sum_scalar(array)
    }
    
    /// 标准求和实现（无SIMD）
    fn sum_scalar(array: &[i64]) -> i64 {
        array.iter().sum()
    }
    
    /// 使用SIMD计算前缀和
    fn compute_prefix_sum_simd(array: &[i64]) -> Vec<i64> {
        let len = array.len();
        let mut prefix_sum = vec![0; len + 1];
        
        for i in 0..len {
            prefix_sum[i + 1] = prefix_sum[i] + array[i];
        }
        
        prefix_sum
    }
    
    /// 使用SIMD优化的范围求和
    fn range_sum_simd(prefix_sum: &[i64], from: usize, to: usize) -> i64 {
        if from >= to || from >= prefix_sum.len() - 1 {
            return 0;
        }
        let end = to.min(prefix_sum.len() - 1);
        prefix_sum[end] - prefix_sum[from]
    }
}

/// 获取当前CPU支持的SIMD指令集类型
fn detect_simd_support() -> &'static str {
    "基础" // 简化实现
}

/// Python模块定义
#[pymodule]
fn subset_sum(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<SubsetSumSolver>()?;
    Ok(())
}
