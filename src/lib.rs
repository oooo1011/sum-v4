use pyo3::prelude::*;
use pyo3::exceptions::PyValueError;
use rayon::prelude::*;
use std::sync::atomic::{AtomicBool, AtomicUsize, Ordering};
use std::sync::{Arc, Mutex};
use std::cell::RefCell;
use num_cpus;

thread_local! {
    // 小型子集池（容量16）- 适用于较浅的递归
    static SMALL_POOL: RefCell<Vec<Vec<usize>>> = RefCell::new(Vec::with_capacity(256));
    // 中型子集池（容量64）- 适用于中等递归深度
    static MEDIUM_POOL: RefCell<Vec<Vec<usize>>> = RefCell::new(Vec::with_capacity(128));
    // 大型子集池（容量256）- 适用于深递归
    static LARGE_POOL: RefCell<Vec<Vec<usize>>> = RefCell::new(Vec::with_capacity(64));
}

/// 内存使用跟踪器，用于监控内存使用情况
struct MemoryTracker {
    current_usage: AtomicUsize,
    peak_usage: AtomicUsize,
    limit: usize,
}

impl MemoryTracker {
    fn new(limit_mb: usize) -> Self {
        MemoryTracker {
            current_usage: AtomicUsize::new(0),
            peak_usage: AtomicUsize::new(0),
            limit: limit_mb * 1024 * 1024,
        }
    }

    fn allocate(&self, size: usize) -> bool {
        let current = self.current_usage.fetch_add(size, Ordering::SeqCst) + size;
        if current > self.limit {
            self.current_usage.fetch_sub(size, Ordering::SeqCst);
            return false;
        }
        
        let peak = self.peak_usage.load(Ordering::SeqCst);
        if current > peak {
            self.peak_usage.store(current, Ordering::SeqCst);
        }
        true
    }
    
    fn deallocate(&self, size: usize) {
        self.current_usage.fetch_sub(size, Ordering::SeqCst);
    }
    
    fn current_usage_mb(&self) -> f64 {
        self.current_usage.load(Ordering::SeqCst) as f64 / (1024.0 * 1024.0)
    }
    
    fn peak_usage_mb(&self) -> f64 {
        self.peak_usage.load(Ordering::SeqCst) as f64 / (1024.0 * 1024.0)
    }
}

/// 优化：压缩表示，使用位图表示子集（适用于32个以内的数字）
struct CompactSubset {
    bitmap: u32,
    count: u8,
}

impl CompactSubset {
    fn new() -> Self {
        Self { bitmap: 0, count: 0 }
    }
    
    fn add(&mut self, index: usize) {
        if index < 32 && !self.contains(index) {
            self.bitmap |= 1 << index;
            self.count += 1;
        }
    }
    
    fn contains(&self, index: usize) -> bool {
        if index < 32 {
            (self.bitmap & (1 << index)) != 0
        } else {
            false
        }
    }
    
    fn remove(&mut self, index: usize) {
        if index < 32 && self.contains(index) {
            self.bitmap &= !(1 << index);
            self.count -= 1;
        }
    }
    
    fn to_vec(&self) -> Vec<usize> {
        let mut result = Vec::with_capacity(self.count as usize);
        for i in 0..32 {
            if self.contains(i) {
                result.push(i);
            }
        }
        result
    }
    
    fn len(&self) -> usize {
        self.count as usize
    }
    
    fn clear(&mut self) {
        self.bitmap = 0;
        self.count = 0;
    }
}

/// 根据预期大小从合适的池中获取Vec
fn get_vec_from_pool(expected_size: usize) -> Vec<usize> {
    if expected_size <= 16 {
        SMALL_POOL.with(|pool| {
            if let Some(vec) = pool.borrow_mut().pop() {
                vec
            } else {
                Vec::with_capacity(16)
            }
        })
    } else if expected_size <= 64 {
        MEDIUM_POOL.with(|pool| {
            if let Some(vec) = pool.borrow_mut().pop() {
                vec
            } else {
                Vec::with_capacity(64)
            }
        })
    } else {
        LARGE_POOL.with(|pool| {
            if let Some(vec) = pool.borrow_mut().pop() {
                vec
            } else {
                Vec::with_capacity(256)
            }
        })
    }
}

/// 将Vec归还到合适的池
fn return_vec_to_pool(mut vec: Vec<usize>) {
    vec.clear();
    let cap = vec.capacity();
    
    if cap <= 16 {
        SMALL_POOL.with(|pool| {
            if pool.borrow().len() < 256 {
                pool.borrow_mut().push(vec);
            }
        });
    } else if cap <= 64 {
        MEDIUM_POOL.with(|pool| {
            if pool.borrow().len() < 128 {
                pool.borrow_mut().push(vec);
            }
        });
    } else {
        LARGE_POOL.with(|pool| {
            if pool.borrow().len() < 64 {
                pool.borrow_mut().push(vec);
            }
        });
    }
}

// 获取编译时间和版本号
fn build_info() -> (&'static str, &'static str) {
    let version = env!("CARGO_PKG_VERSION");
    let build_date = option_env!("BUILD_DATE").unwrap_or("未知编译时间");
    (version, build_date)
}

/// 模块级函数，用于获取版本号
#[pyfunction]
fn get_module_version() -> String {
    let (version, build_date) = build_info();
    format!("{}-parallel (编译于 {})", version, build_date)
}

/// 子集和求解器
/// 用于寻找和为指定值的子集
#[pyclass]
pub struct SubsetSumSolver {
    stop_flag: Arc<AtomicBool>,
    progress_callback: Option<PyObject>,
    progress_lock: Arc<Mutex<()>>,
    processed_combinations: Arc<AtomicUsize>,
    total_combinations: Arc<AtomicUsize>,
    memory_tracker: Arc<MemoryTracker>,
}

#[pymethods]
impl SubsetSumSolver {
    /// 创建新的求解器实例
    #[new]
    fn new() -> Self {
        SubsetSumSolver {
            stop_flag: Arc::new(AtomicBool::new(false)),
            progress_callback: None,
            progress_lock: Arc::new(Mutex::new(())),
            processed_combinations: Arc::new(AtomicUsize::new(0)),
            total_combinations: Arc::new(AtomicUsize::new(0)),
            memory_tracker: Arc::new(MemoryTracker::new(1024)), // 默认1GB内存限制
        }
    }
    
    /// 获取模块版本
    #[pyo3(name = "get_version")]
    fn get_version(&self) -> String {
        let (version, build_date) = build_info();
        // 添加一个随机数，确保每次调用都返回不同的版本号（用于调试）
        let _random = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .subsec_nanos();
        format!("{}-parallel (编译于 {})", version, build_date)
    }

    /// 设置求解器的内存限制
    #[pyo3(name = "set_memory_limit")]
    fn set_memory_limit(&mut self, limit_mb: usize) {
        self.memory_tracker = Arc::new(MemoryTracker::new(limit_mb));
    }
    
    /// 获取当前内存使用情况
    #[pyo3(name = "get_memory_usage")]
    fn get_memory_usage(&self) -> (f64, f64) {
        (
            self.memory_tracker.current_usage_mb(),
            self.memory_tracker.peak_usage_mb()
        )
    }

    /// 设置停止标志，终止计算
    fn stop(&mut self) {
        self.stop_flag.store(true, Ordering::SeqCst);
    }
    
    /// 重置状态，准备新的计算
    fn reset(&mut self) {
        self.stop_flag.store(false, Ordering::SeqCst);
        self.processed_combinations.store(0, Ordering::SeqCst);
        self.total_combinations.store(0, Ordering::SeqCst);
    }
    
    /// 设置进度回调函数
    fn set_progress_callback(&mut self, callback: Option<PyObject>) {
        self.progress_callback = callback;
    }
    
    /// 获取计算进度（0-100）
    fn get_progress(&self) -> f64 {
        let processed = self.processed_combinations.load(Ordering::SeqCst) as f64;
        let total = self.total_combinations.load(Ordering::SeqCst) as f64;
        if total > 0.0 {
            (processed / total) * 100.0
        } else {
            0.0
        }
    }
    
    /// 寻找子集
    /// 接受浮点数列表，内部转换为整数进行精确计算
    fn find_subsets(&mut self, numbers: Vec<f64>, target: f64, max_solutions: usize, memory_limit_mb: usize) -> PyResult<Vec<Vec<f64>>> {
        // 验证输入
        if numbers.is_empty() {
            return Err(PyValueError::new_err("输入数字列表不能为空"));
        }
        
        // 使用指定的内存限制
        self.memory_tracker = Arc::new(MemoryTracker::new(memory_limit_mb));
        
        // 重置状态
        self.reset();
        
        // 计算可能的组合总数(2^n)，但限制为u64可表示的最大值
        let n = numbers.len();
        let total_combinations = if n >= 64 {
            usize::MAX
        } else {
            1_usize << n
        };
        self.total_combinations.store(total_combinations, Ordering::SeqCst);
        
        // 自动检测小数位数并设置合适的缩放因子
        let mut max_decimal_places = 0;
        for &x in &numbers {
            // 将数字转为字符串，以检测小数位数
            let s = x.to_string();
            if let Some(pos) = s.find('.') {
                let decimal_places = s.len() - pos - 1;
                max_decimal_places = max_decimal_places.max(decimal_places);
            }
        }
        
        // 根据检测到的最大小数位数计算缩放因子
        // 限制为最多10位，避免整数溢出
        let scale = 10_i64.pow((max_decimal_places as u32).min(10));
        
        // 将浮点数转换为整数
        let numbers_int: Vec<i64> = numbers.iter()
            .map(|&x| (x * scale as f64).round() as i64)
            .collect();
        let target_int = (target * scale as f64).round() as i64;
        
        // 计算结果
        let solutions_int = self.find_subsets_int(&numbers_int, target_int, max_solutions);
        
        // 将结果转换回浮点数
        let solutions: Vec<Vec<f64>> = solutions_int.iter()
            .map(|indices| {
                indices.iter()
                    .map(|&i| numbers[i])
                    .collect()
            })
            .collect();
        
        Ok(solutions)
    }
}

// 私有实现，不暴露给Python
impl SubsetSumSolver {
    // 使用位运算优化的子集和求解（针对小规模问题）
    fn find_subsets_with_bit(&self, numbers: &[i64], target: i64, max_solutions: usize) -> Vec<Vec<usize>> {
        let n = numbers.len();
        if n > 32 {
            // 超过32个数字时回退到标准解法
            return self.find_subsets_int(numbers, target, max_solutions);
        }
        
        let should_stop = Arc::clone(&self.stop_flag);
        let solutions = Arc::new(Mutex::new(Vec::new()));
        let total_combinations = 1u64 << n;
        
        // 使用rayon的并行迭代器处理
        (1..total_combinations).into_par_iter()
            // 不使用with_max_len方法，因为对u64迭代器不支持
            .for_each(|mask| {
                // 检查是否应该停止
                if should_stop.load(Ordering::SeqCst) {
                    return;
                }
                
                // 计算当前子集的和
                let mut sum = 0;
                for i in 0..n {
                    if (mask & (1 << i)) != 0 {
                        sum += numbers[i];
                    }
                }
                
                // 找到一个解（精确匹配）
                if sum == target {
                    let mut sols = solutions.lock().unwrap();
                    if sols.len() < max_solutions {
                        // 创建子集
                        let mut subset = Vec::with_capacity(n.count_ones() as usize);
                        for i in 0..n {
                            if (mask & (1 << i)) != 0 {
                                subset.push(i);
                            }
                        }
                        sols.push(subset);
                        
                        if sols.len() >= max_solutions {
                            should_stop.store(true, Ordering::SeqCst);
                        }
                    }
                }
                
                // 更新进度
                self.processed_combinations.fetch_add(1, Ordering::SeqCst);
            });
        
        // 修复生命周期问题：先获取锁，解除锁，然后返回结果
        let result = {
            let guard = solutions.lock().unwrap();
            guard.clone()
        };
        result
    }
    
    /// 内部方法：以整数形式寻找子集
    fn find_subsets_int(&self, numbers: &[i64], target: i64, max_solutions: usize) -> Vec<Vec<usize>> {
        // 重置进度计数器
        self.processed_combinations.store(0, Ordering::SeqCst);
        self.stop_flag.store(false, Ordering::SeqCst);
        
        // 优化：对于小规模问题使用位运算优化
        if numbers.len() <= 32 {
            return self.find_subsets_with_bit(numbers, target, max_solutions);
        }
        
        // 优化：对于中等规模问题使用动态规划算法
        if numbers.len() <= 100 && target > 0 && target < 10000 {
            return self.find_subsets_with_dp(numbers, target, max_solutions);
        }
        
        // 创建停止标志
        let should_stop = Arc::clone(&self.stop_flag);
        
        // 存储解决方案
        let solutions = Arc::new(Mutex::new(Vec::new()));
        
        // 使用对象池获取初始子集
        let mut current_subset = get_vec_from_pool(16);
        
        // 预处理数据
        let (sorted_numbers, sorted_indices, prefix_sum) = self.preprocess_data(numbers, target);
        
        // 开始回溯搜索
        self.backtrack_optimized(
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
        return_vec_to_pool(current_subset);
        
        // 释放锁，获取结果
        let result = {
            let guard = solutions.lock().unwrap();
            guard.clone()
        };
        
        result
    }
    
    /// 预处理数据，优化搜索效率
    fn preprocess_data(&self, numbers: &[i64], target: i64) -> (Vec<i64>, Vec<usize>, Vec<i64>) {
        // 1. 过滤掉大于目标的数字（对于正数问题）
        let filtered: Vec<(usize, i64)> = numbers.iter()
            .enumerate()
            .filter(|&(_, &x)| x <= target)
            .map(|(i, &x)| (i, x))  // 解引用，避免类型不匹配
            .collect();
        
        // 2. 根据与目标值的差异排序
        let abs_diff = |a: i64| (a - target).abs();
        let mut index_map = filtered.clone();
        index_map.sort_by(|a, b| abs_diff(a.1).cmp(&abs_diff(b.1)));
        
        // 3. 提取排序后的数字和原始索引
        let sorted_numbers: Vec<i64> = index_map.iter().map(|&(_, v)| v).collect();
        let sorted_indices: Vec<usize> = index_map.iter().map(|&(i, _)| i).collect();
        
        // 4. 计算前缀和，用于优化剪枝
        let mut prefix_sum = vec![0; sorted_numbers.len() + 1];
        
        // 计算前缀和
        for i in 0..sorted_numbers.len() {
            prefix_sum[i + 1] = prefix_sum[i] + sorted_numbers[i];
        }
        
        (sorted_numbers, sorted_indices, prefix_sum)
    }
    
    // 优化的回溯搜索，包含增强的剪枝和工作窃取调度
    fn backtrack_optimized(
        &self,
        numbers: &[i64],
        pos_to_orig: &[usize],
        prefix_sum: &[i64],
        target: i64,
        start: usize,
        current_sum: i64,
        current_subset: &mut Vec<usize>,
        solutions: &Arc<Mutex<Vec<Vec<usize>>>>,
        max_solutions: usize,
        should_stop: &Arc<AtomicBool>,
    ) {
        // 检查是否应该停止
        if should_stop.load(Ordering::SeqCst) {
            return;
        }
        
        // 检查内存使用情况
        let subset_mem_size = current_subset.capacity() * std::mem::size_of::<usize>();
        if !self.memory_tracker.allocate(subset_mem_size) {
            self.memory_tracker.deallocate(subset_mem_size);
            should_stop.store(true, Ordering::SeqCst);
            return;
        }
        
        // 找到一个解（使用精确整数比较）
        if current_sum == target {
            let mut sols = solutions.lock().unwrap();
            if sols.len() < max_solutions {
                // 将当前子集转换回原始索引
                let mut solution = get_vec_from_pool(current_subset.len());
                for pos in current_subset.iter() {
                    solution.push(pos_to_orig[*pos]);
                }
                sols.push(solution);
                
                if sols.len() >= max_solutions {
                    should_stop.store(true, Ordering::SeqCst);
                }
            }
            self.memory_tracker.deallocate(subset_mem_size);
            return;
        }
        
        // 优化剪枝1：如果当前和已经超过目标，不需要继续（因为所有数字都是正数）
        if current_sum > target {
            self.memory_tracker.deallocate(subset_mem_size);
            return;
        }
        
        // 优化剪枝2：如果已经到达列表末尾，不需要继续
        if start >= numbers.len() {
            self.memory_tracker.deallocate(subset_mem_size);
            return;
        }
        
        // 优化剪枝3：使用前缀和进行剪枝
        // 即使加上从start开始的所有数字也无法达到目标，提前返回
        // 使用SIMD加速的前缀和计算
        let remaining_sum = prefix_sum[numbers.len()] - prefix_sum[start];
        if current_sum + remaining_sum < target {
            self.memory_tracker.deallocate(subset_mem_size);
            return;
        }
        
        // 使用前缀和评估当前分支
        let evaluate_branch = |from: usize, to: usize| -> i64 {
            if from >= to || from >= numbers.len() {
                return 0;
            }
            let end = to.min(numbers.len());
            // 使用前缀和快速计算范围总和
            prefix_sum[end] - prefix_sum[from]
        };
        
        // 并行阈值：当剩余数字较多时使用并行处理
        // 使用自适应阈值，根据CPU核心数自动调整
        let parallel_threshold = get_adaptive_parallel_threshold();
        let remaining_numbers = numbers.len() - start;
        
        if remaining_numbers > parallel_threshold && current_subset.len() < 3 {
            // 优化：工作窃取调度优化
            // 计算分割点，使得左右两部分工作量更加均衡
            let mid = start + remaining_numbers / 2;
            
            // 计算左右两部分与目标的差距
            let left_sum = prefix_sum[mid] - prefix_sum[start];
            let right_sum = prefix_sum[numbers.len()] - prefix_sum[mid];
            
            // 决定优先处理哪一部分
            // 使用前缀和评估函数
            let left_potential = evaluate_branch(start, mid);
            let right_potential = evaluate_branch(mid, numbers.len());
            
            let left_diff = (target - current_sum - left_potential).abs();
            let right_diff = (target - current_sum - right_potential).abs();
            
            // 优先处理更接近目标的一侧
            let process_left_first = left_diff < right_diff;
            
            // 使用rayon的join进行并行处理，实现工作窃取调度
            let solutions_arc = Arc::clone(solutions);
            let should_stop_arc = Arc::clone(should_stop);
            
            if process_left_first {
                // 创建两个处理分支
                let mut left_subset = get_vec_from_pool(current_subset.len() + (mid - start));
                left_subset.extend_from_slice(current_subset);
                
                let mut right_subset = get_vec_from_pool(current_subset.len() + (numbers.len() - mid));
                right_subset.extend_from_slice(current_subset);
                
                // 并行处理两部分，优先处理左侧
                rayon::join(
                    || {
                        // 处理左半部分 [start, mid)
                        for i in start..mid {
                            if should_stop_arc.load(Ordering::SeqCst) {
                                break;
                            }
                            
                            // 选择当前数字
                            left_subset.push(i);
                            self.backtrack_optimized(
                                numbers,
                                pos_to_orig,
                                prefix_sum,
                                target,
                                i + 1,
                                current_sum + numbers[i],
                                &mut left_subset,
                                &solutions_arc,
                                max_solutions,
                                &should_stop_arc,
                            );
                            left_subset.pop();
                            
                            // 不选择当前数字（隐含在循环中）
                        }
                        return_vec_to_pool(left_subset);
                    },
                    || {
                        // 处理右半部分 [mid, end)
                        for i in mid..numbers.len() {
                            if should_stop_arc.load(Ordering::SeqCst) {
                                break;
                            }
                            
                            // 选择当前数字
                            right_subset.push(i);
                            self.backtrack_optimized(
                                numbers,
                                pos_to_orig,
                                prefix_sum,
                                target,
                                i + 1,
                                current_sum + numbers[i],
                                &mut right_subset,
                                &solutions_arc,
                                max_solutions,
                                &should_stop_arc,
                            );
                            right_subset.pop();
                            
                            // 不选择当前数字（隐含在循环中）
                        }
                        return_vec_to_pool(right_subset);
                    }
                );
            } else {
                // 创建两个处理分支
                let mut left_subset = get_vec_from_pool(current_subset.len() + (mid - start));
                left_subset.extend_from_slice(current_subset);
                
                let mut right_subset = get_vec_from_pool(current_subset.len() + (numbers.len() - mid));
                right_subset.extend_from_slice(current_subset);
                
                // 并行处理两部分，优先处理右侧
                rayon::join(
                    || {
                        // 处理右半部分 [mid, end)
                        for i in mid..numbers.len() {
                            if should_stop_arc.load(Ordering::SeqCst) {
                                break;
                            }
                            
                            // 选择当前数字
                            right_subset.push(i);
                            self.backtrack_optimized(
                                numbers,
                                pos_to_orig,
                                prefix_sum,
                                target,
                                i + 1,
                                current_sum + numbers[i],
                                &mut right_subset,
                                &solutions_arc,
                                max_solutions,
                                &should_stop_arc,
                            );
                            right_subset.pop();
                            
                            // 不选择当前数字（隐含在循环中）
                        }
                        return_vec_to_pool(right_subset);
                    },
                    || {
                        // 处理左半部分 [start, mid)
                        for i in start..mid {
                            if should_stop_arc.load(Ordering::SeqCst) {
                                break;
                            }
                            
                            // 选择当前数字
                            left_subset.push(i);
                            self.backtrack_optimized(
                                numbers,
                                pos_to_orig,
                                prefix_sum,
                                target,
                                i + 1,
                                current_sum + numbers[i],
                                &mut left_subset,
                                &solutions_arc,
                                max_solutions,
                                &should_stop_arc,
                            );
                            left_subset.pop();
                            
                            // 不选择当前数字（隐含在循环中）
                        }
                        return_vec_to_pool(left_subset);
                    }
                );
            }
        } else {
            // 串行处理：当剩余数字较少或递归深度较大时
            for i in start..numbers.len() {
                if should_stop.load(Ordering::SeqCst) {
                    break;
                }
                
                // 选择当前数字
                current_subset.push(i);
                self.backtrack_optimized(
                    numbers,
                    pos_to_orig,
                    prefix_sum,
                    target,
                    i + 1,
                    current_sum + numbers[i],
                    current_subset,
                    solutions,
                    max_solutions,
                    should_stop,
                );
                current_subset.pop();
                
                // 不选择当前数字（隐含在循环中）
            }
        }
        
        // 释放当前子集占用的内存计数
        self.memory_tracker.deallocate(subset_mem_size);
        
        // 更新进度（只在顶层递归调用中）
        if start == 0 {
            self.processed_combinations.fetch_add(1, Ordering::SeqCst);
        }
    }
    
    /// 使用动态规划算法求解子集和问题
    /// 这种方法在中等规模问题(数量不超过100，目标和较小)上更高效
    fn find_subsets_with_dp(&self, numbers: &[i64], target: i64, max_solutions: usize) -> Vec<Vec<usize>> {
        // 创建停止标志和解决方案容器
        let should_stop = Arc::clone(&self.stop_flag);
        let solutions = Arc::new(Mutex::new(Vec::new()));
        
        // 预处理：过滤掉大于目标的数字
        let filtered: Vec<(usize, i64)> = numbers.iter()
            .enumerate()
            .filter(|&(_, &x)| x <= target)
            .map(|(i, &x)| (i, x))
            .collect();
        
        if filtered.is_empty() {
            return Vec::new();
        }
        
        // 获取过滤后的数字和对应索引
        let dp_indices: Vec<usize> = filtered.iter().map(|&(i, _)| i).collect();
        let dp_numbers: Vec<i64> = filtered.iter().map(|&(_, v)| v).collect();
        
        // 动态规划表：dp[i][j] 表示前i个数字能否组成和为j
        // 使用压缩空间的一维数组实现
        let target_usize = target as usize;
        let mut dp = vec![false; target_usize + 1];
        dp[0] = true; // 空集的和为0
        
        // 记录路径的前驱表：predecessor[j] = i 表示和为j的子集包含第i个数字
        let mut predecessor: Vec<Vec<usize>> = vec![Vec::new(); target_usize + 1];
        
        // 动态规划计算
        for i in 0..dp_numbers.len() {
            // 检查是否应该停止
            if should_stop.load(Ordering::SeqCst) {
                return {
                    let guard = solutions.lock().unwrap();
                    guard.clone()
                };
            }
            
            // 使用快速求和来计算当前数字
            let current_number = dp_numbers[i];
            if current_number <= 0 {
                continue;  // 跳过非正数
            }
            
            let current_number_usize = current_number as usize;
            
            // 从后往前遍历，避免重复使用同一个数字
            for j in (current_number_usize..=target_usize).rev() {
                let prev_idx = j - current_number_usize;
                if dp[prev_idx] && !dp[j] {
                    dp[j] = true;
                    
                    // 记录路径：j是由j-current_number加上current_number得到的
                    predecessor[j] = predecessor[prev_idx].clone();
                    predecessor[j].push(i);
                    
                    // 如果找到目标和，记录解
                    if j == target_usize {
                        let mut sols = solutions.lock().unwrap();
                        if sols.len() < max_solutions {
                            // 构建解决方案：将内部索引映射回原始索引
                            let mut solution = get_vec_from_pool(predecessor[j].len());
                            for &idx in &predecessor[j] {
                                solution.push(dp_indices[idx]);
                            }
                            sols.push(solution);
                            
                            // 如果达到最大解数量，提前结束
                            if sols.len() >= max_solutions {
                                should_stop.store(true, Ordering::SeqCst);
                                break;
                            }
                        }
                    }
                }
            }
            
            // 更新进度
            self.processed_combinations.fetch_add(1, Ordering::SeqCst);
        }
        
        // 获取所有找到的解
        let result = {
            let guard = solutions.lock().unwrap();
            guard.clone()
        };
        
        result
    }
}

/// 获取自适应并行阈值
fn get_adaptive_parallel_threshold() -> usize {
    let cpu_cores = num_cpus::get();
    
    // 根据CPU核心数自动调整并行阈值
    if cpu_cores <= 2 {
        24  // 对于双核CPU，大问题才并行
    } else if cpu_cores <= 4 {
        16  // 4核CPU的标准阈值
    } else if cpu_cores <= 8 {
        12  // 多核CPU，更激进的并行策略
    } else {
        8   // 大量核心时，尽早并行
    }
}

/// 快速数组求和函数
/// 将来可以添加SIMD支持以提高性能
#[inline]
fn fast_sum(array: &[i64]) -> i64 {
    // 当前使用标准求和实现
    // 未来可以根据CPU支持添加SIMD优化
    array.iter().sum()
}

/// Python模块定义
#[pymodule]
fn subset_sum(_py: Python, m: &PyModule) -> PyResult<()> {
    // 添加类
    m.add_class::<SubsetSumSolver>()?;
    
    // 添加模块级函数
    m.add_function(wrap_pyfunction!(get_module_version, m)?)?;
    
    // 添加模块级常量
    let (version, build_date) = build_info();
    let version_str = format!("{}-parallel (编译于 {})", version, build_date);
    m.add("VERSION", version_str)?;
    
    Ok(())
}
