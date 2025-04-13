use pyo3::prelude::*;
use pyo3::exceptions::PyValueError;
use rayon::prelude::*;
use std::sync::{Arc, Mutex, atomic::{AtomicBool, Ordering}};
use std::sync::atomic::AtomicU64;
use std::cmp::Ordering as CmpOrdering;

/// 子集和求解器
#[pyclass]
pub struct SubsetSumSolver {
    progress: Arc<AtomicU64>,
    should_stop: Arc<AtomicBool>,
    total_combinations: Arc<AtomicU64>,
    processed_combinations: Arc<AtomicU64>,
}

#[pymethods]
impl SubsetSumSolver {
    /// 创建新的求解器实例
    #[new]
    fn new() -> Self {
        SubsetSumSolver {
            progress: Arc::new(AtomicU64::new(0)),
            should_stop: Arc::new(AtomicBool::new(false)),
            total_combinations: Arc::new(AtomicU64::new(0)),
            processed_combinations: Arc::new(AtomicU64::new(0)),
        }
    }

    /// 重置求解器状态
    fn reset(&mut self) {
        self.progress.store(0, Ordering::SeqCst);
        self.should_stop.store(false, Ordering::SeqCst);
        self.total_combinations.store(0, Ordering::SeqCst);
        self.processed_combinations.store(0, Ordering::SeqCst);
    }

    /// 停止计算
    fn stop(&mut self) {
        self.should_stop.store(true, Ordering::SeqCst);
    }

    /// 获取当前进度（百分比）
    fn get_progress(&self) -> f64 {
        let total_combinations = self.total_combinations.load(Ordering::SeqCst);
        let processed_combinations = self.processed_combinations.load(Ordering::SeqCst);
        (processed_combinations as f64 / total_combinations as f64) * 100.0
    }

    /// 查找和为目标值的子集
    /// 
    /// Args:
    ///     numbers: 输入数字列表
    ///     target: 目标和
    ///     max_solutions: 最大解决方案数量
    ///     memory_limit_mb: 内存限制（MB）
    /// 
    /// Returns:
    ///     找到的子集列表
    #[pyo3(signature = (numbers, target, max_solutions=1, memory_limit_mb=1000))]
    fn find_subsets(
        &mut self, 
        numbers: Vec<f64>, 
        target: f64, 
        max_solutions: usize,
        memory_limit_mb: usize,
    ) -> PyResult<Vec<Vec<f64>>> {
        // 验证输入
        if numbers.is_empty() {
            return Err(PyValueError::new_err("输入数字列表不能为空"));
        }

        // 重置状态
        self.reset();
        
        // 将浮点数乘以100并转换为整数，以避免浮点数精度问题
        let int_numbers: Vec<i64> = numbers.iter().map(|&x| (x * 100.0).round() as i64).collect();
        let int_target = (target * 100.0).round() as i64;
        
        // 排序数字（从大到小，有助于更快找到解）
        let mut sorted_numbers = int_numbers.clone();
        sorted_numbers.sort_by(|a, b| b.cmp(a));
        
        // 创建共享数据结构
        let solutions = Arc::new(Mutex::new(Vec::new()));
        let should_stop = Arc::clone(&self.should_stop);
        
        // 设置进度计算
        let total_combinations = 2_u64.pow(sorted_numbers.len().min(30) as u32);
        self.total_combinations.store(total_combinations, Ordering::SeqCst);
        self.processed_combinations.store(0, Ordering::SeqCst);
        
        // 创建线程池
        let pool = rayon::ThreadPoolBuilder::new()
            .num_threads(num_cpus::get())
            .build()
            .unwrap();
        
        // 并行执行回溯算法
        pool.install(|| {
            // 创建初始子集
            let mut current_subset = Vec::new();
            
            // 执行回溯
            self.backtrack_int(
                &sorted_numbers,
                int_target,
                0,
                0,
                &mut current_subset,
                &solutions,
                max_solutions,
                &should_stop,
                memory_limit_mb,
            );
        });
        
        // 获取结果并转换回原始索引
        let index_solutions = solutions.lock().unwrap();
        
        // 将索引解转换为实际数字解
        let mut result = Vec::new();
        for indices in index_solutions.iter() {
            let mut solution = Vec::new();
            for &idx in indices {
                solution.push(numbers[idx]);
            }
            result.push(solution);
        }
        
        Ok(result)
    }
}

impl SubsetSumSolver {
    /// 回溯算法核心实现（整数版本）
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
        memory_limit_mb: usize,
    ) {
        // 检查是否应该停止
        if should_stop.load(Ordering::SeqCst) {
            return;
        }
        
        // 简单内存限制检查（粗略估计）
        if current_subset.len() * std::mem::size_of::<usize>() > memory_limit_mb * 1024 * 1024 / 2 {
            return;
        }
        
        // 找到一个解（使用精确整数比较）
        if current_sum == target {
            let mut sols = solutions.lock().unwrap();
            if sols.len() < max_solutions {
                sols.push(current_subset.clone());
                if sols.len() >= max_solutions {
                    should_stop.store(true, Ordering::SeqCst);
                }
            }
            return;
        }
        
        // 剪枝：如果当前和已经超过目标，不需要继续（因为所有数字都是正数）
        if current_sum > target {
            return;
        }
        
        // 剪枝：如果已经到达列表末尾，不需要继续
        if start >= numbers.len() {
            return;
        }
        
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
            memory_limit_mb,
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
            memory_limit_mb,
        );
        
        // 更新进度（只在顶层递归调用中）
        if start == 0 {
            self.processed_combinations.fetch_add(1, Ordering::SeqCst);
        }
    }
}

/// Python模块定义
#[pymodule]
fn subset_sum(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<SubsetSumSolver>()?;
    Ok(())
}
