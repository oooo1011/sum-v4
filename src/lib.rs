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
}

#[pymethods]
impl SubsetSumSolver {
    /// 创建新的求解器实例
    #[new]
    fn new() -> Self {
        SubsetSumSolver {
            progress: Arc::new(AtomicU64::new(0)),
            should_stop: Arc::new(AtomicBool::new(false)),
        }
    }

    /// 重置求解器状态
    fn reset(&mut self) {
        self.progress.store(0, Ordering::SeqCst);
        self.should_stop.store(false, Ordering::SeqCst);
    }

    /// 停止计算
    fn stop(&mut self) {
        self.should_stop.store(true, Ordering::SeqCst);
    }

    /// 获取当前进度（百分比）
    fn get_progress(&self) -> f64 {
        self.progress.load(Ordering::SeqCst) as f64 / 100.0
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
        
        if max_solutions == 0 {
            return Err(PyValueError::new_err("最大解决方案数量必须大于0"));
        }
        
        // 重置状态
        self.reset();
        
        // 排序可以提高剪枝效率
        let mut sorted_numbers = numbers.clone();
        sorted_numbers.sort_by(|a, b| a.partial_cmp(b).unwrap_or(CmpOrdering::Equal));
        
        // 共享状态
        let solutions = Arc::new(Mutex::new(Vec::<Vec<usize>>::new()));
        let should_stop = self.should_stop.clone();
        let progress = self.progress.clone();
        
        // 计算分块大小
        let num_threads = num_cpus::get();
        let chunk_size = std::cmp::max(1, sorted_numbers.len() / num_threads);
        
        // 并行处理
        sorted_numbers.par_chunks(chunk_size)
            .enumerate()
            .for_each(|(chunk_id, chunk)| {
                if should_stop.load(Ordering::SeqCst) {
                    return;
                }
                
                let chunk_start_idx = chunk_id * chunk_size;
                
                for (i, &num) in chunk.iter().enumerate() {
                    let idx = chunk_start_idx + i;
                    
                    if should_stop.load(Ordering::SeqCst) {
                        break;
                    }
                    
                    // 单个数字就是解
                    if (num - target).abs() < 1e-6 {
                        let mut sols = solutions.lock().unwrap();
                        if sols.len() < max_solutions {
                            sols.push(vec![idx]);
                            if sols.len() >= max_solutions {
                                should_stop.store(true, Ordering::SeqCst);
                                break;
                            }
                        }
                    }
                    
                    // 回溯查找
                    let mut current_subset = vec![idx];
                    let mut current_sum = num;
                    
                    self.backtrack(
                        &sorted_numbers, 
                        target, 
                        idx + 1, 
                        current_sum, 
                        &mut current_subset, 
                        &solutions, 
                        max_solutions, 
                        &should_stop,
                        memory_limit_mb,
                    );
                    
                    // 更新进度
                    let chunk_progress = (i as u64 * 100) / chunk.len() as u64;
                    let total_progress = (chunk_id as u64 * 100) / num_threads as u64 + chunk_progress / num_threads as u64;
                    progress.store(total_progress, Ordering::SeqCst);
                    
                    // 检查是否已找到足够解
                    let sols_len = solutions.lock().unwrap().len();
                    if sols_len >= max_solutions {
                        should_stop.store(true, Ordering::SeqCst);
                        break;
                    }
                }
            });
        
        // 转换索引为实际数字
        let final_solutions = solutions.lock().unwrap();
        let mut result = Vec::new();
        
        for solution in final_solutions.iter() {
            let subset: Vec<f64> = solution.iter()
                .map(|&idx| sorted_numbers[idx])
                .collect();
            result.push(subset);
        }
        
        Ok(result)
    }
}

impl SubsetSumSolver {
    /// 回溯算法核心实现
    fn backtrack(
        &self,
        numbers: &[f64],
        target: f64,
        start: usize,
        current_sum: f64,
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
        
        // 找到一个解
        if (current_sum - target).abs() < 1e-6 {
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
        self.backtrack(
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
        self.backtrack(
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
    }
}

/// Python模块定义
#[pymodule]
fn subset_sum(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<SubsetSumSolver>()?;
    Ok(())
}
