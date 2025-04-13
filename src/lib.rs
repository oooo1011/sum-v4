use pyo3::prelude::*;
use pyo3::exceptions::PyValueError;
use rayon::prelude::*;
use std::sync::atomic::{AtomicBool, AtomicUsize, Ordering};
use std::sync::{Arc, Mutex};
use std::cell::RefCell;

thread_local! {
    // 线程局部存储的对象池，避免线程间竞争
    static SUBSET_POOL: RefCell<Vec<Vec<usize>>> = RefCell::new(Vec::with_capacity(64));
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

/// 从线程本地对象池获取Vec
fn get_vec_from_pool<T: Clone>() -> Vec<T> {
    let mut result = Vec::new();
    SUBSET_POOL.with(|pool| {
        if let Some(vec) = pool.borrow_mut().pop() {
            // 类型转换，使其可用于任何T类型
            let capacity = vec.capacity();
            drop(vec);
            result = Vec::with_capacity(capacity);
        }
    });
    result
}

/// 将Vec归还给线程本地对象池
fn return_vec_to_pool(mut vec: Vec<usize>) {
    vec.clear();
    SUBSET_POOL.with(|pool| {
        // 限制池大小，避免过度缓存
        if pool.borrow().len() < 128 {
            pool.borrow_mut().push(vec);
        }
    });
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
            (1_usize << n)
        };
        self.total_combinations.store(total_combinations, Ordering::SeqCst);
        
        // 将浮点数转换为整数（乘以100后四舍五入）
        // 这避免了浮点数精度问题
        let scale = 100;
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
    // 内部方法：以整数形式寻找子集
    fn find_subsets_int(&self, numbers: &[i64], target: i64, max_solutions: usize) -> Vec<Vec<usize>> {
        // 创建停止标志
        let should_stop = Arc::clone(&self.stop_flag);
        
        // 存储解决方案
        let solutions = Arc::new(Mutex::new(Vec::new()));
        
        // 使用对象池获取初始子集
        let mut current_subset = get_vec_from_pool();
        
        // 开始回溯搜索
        self.backtrack_int(
            numbers,
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
        let result = solutions.lock().unwrap().clone();
        
        result
    }
    
    // 回溯搜索核心算法
    fn backtrack_int(
        &self,
        numbers: &[i64],
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
                // 使用对象池获取新的Vec来存储解决方案
                let mut solution = get_vec_from_pool();
                solution.extend_from_slice(current_subset);
                sols.push(solution);
                
                if sols.len() >= max_solutions {
                    should_stop.store(true, Ordering::SeqCst);
                }
            }
            self.memory_tracker.deallocate(subset_mem_size);
            return;
        }
        
        // 剪枝：如果当前和已经超过目标，不需要继续（因为所有数字都是正数）
        if current_sum > target {
            self.memory_tracker.deallocate(subset_mem_size);
            return;
        }
        
        // 剪枝：如果已经到达列表末尾，不需要继续
        if start >= numbers.len() {
            self.memory_tracker.deallocate(subset_mem_size);
            return;
        }

        // 并行阈值：当剩余数字较多时使用并行处理
        // 这个阈值可以根据实际性能测试进行调整
        let parallel_threshold = 16;
        let remaining_numbers = numbers.len() - start;

        if remaining_numbers > parallel_threshold && current_subset.len() < 3 {
            // 使用rayon的join进行并行处理，实现工作窃取调度
            // 创建两个分支：选择当前数字和不选择当前数字
            let solutions_arc = Arc::clone(solutions);
            let should_stop_arc = Arc::clone(should_stop);
            
            // 使用对象池获取子集副本，避免频繁分配内存
            let mut subset_with_current = get_vec_from_pool();
            subset_with_current.extend_from_slice(current_subset);
            subset_with_current.push(start);
            
            rayon::join(
                // 分支1：选择当前数字
                || {
                    if !should_stop_arc.load(Ordering::SeqCst) {
                        self.backtrack_int(
                            numbers,
                            target,
                            start + 1,
                            current_sum + numbers[start],
                            &mut subset_with_current,
                            &solutions_arc,
                            max_solutions,
                            &should_stop_arc,
                        );
                    }
                    // 记得将Vec归还到对象池
                    return_vec_to_pool(subset_with_current);
                },
                // 分支2：不选择当前数字
                || {
                    if !should_stop_arc.load(Ordering::SeqCst) {
                        // 使用对象池获取另一个子集副本
                        let mut subset_without_current = get_vec_from_pool();
                        subset_without_current.extend_from_slice(current_subset);
                        
                        self.backtrack_int(
                            numbers,
                            target,
                            start + 1,
                            current_sum,
                            &mut subset_without_current,
                            &solutions_arc,
                            max_solutions,
                            &should_stop_arc,
                        );
                        
                        // 归还到对象池
                        return_vec_to_pool(subset_without_current);
                    }
                },
            );
        } else {
            // 串行处理：当剩余数字较少或递归深度较大时
            // 选择当前数字
            current_subset.push(start);
            self.backtrack_int(
                numbers, 
                target, 
                start + 1, 
                current_sum + numbers[start], 
                current_subset, 
                solutions, 
                max_solutions, 
                should_stop,
            );
            current_subset.pop();
            
            // 不选择当前数字
            self.backtrack_int(
                numbers,
                target,
                start + 1,
                current_sum,
                current_subset,
                solutions,
                max_solutions,
                should_stop,
            );
        }
        
        // 释放当前子集占用的内存计数
        self.memory_tracker.deallocate(subset_mem_size);
        
        // 更新进度（只在顶层递归调用中）
        if start == 0 {
            self.processed_combinations.fetch_add(1, Ordering::SeqCst);
        }
    }
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
