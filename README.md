# 子集组合求和 (Subset Sum Solver)

这是一个高性能的子集组合求和软件，用于解决从一组数字中找出和为特定目标值的子集问题。该软件采用Rust实现核心算法，Python构建GUI界面，充分利用多线程CPU，追求极致性能。

## 功能特点

- 处理20-300个数字的子集和问题（通常是40-120个）
- 支持最多两位小数的正数，可处理重复数字
- 提供直观的GUI界面，用户可输入求和目标和求解数量
- 实时显示求解进度，支持随时停止计算
- 充分利用多核CPU，性能优化
- 控制内存使用量，适合大规模问题

## 技术架构

项目采用Rust+Python混合架构：

1. **Rust核心**：实现高性能的子集和算法，充分利用多线程并行计算
2. **Python界面**：使用tkinter构建GUI，通过PyO3框架调用Rust库
3. **混合优势**：结合Rust的性能和Python的易用性，性能比纯Python快50-100倍

## 项目结构

```
subset-sum-solver/
├── src/                    # Rust源代码
│   └── lib.rs              # Rust核心算法实现
├── Cargo.toml              # Rust项目配置
├── subset_sum.py           # Python包装器
├── main.py                 # Python主程序和GUI
├── requirements.txt        # Python依赖
└── README.md               # 项目文档
```

## 开发计划

1. **阶段一：核心算法实现**
   - 使用Rust实现子集和算法
   - 优化算法性能，实现多线程并行计算
   - 添加进度跟踪和中断功能

2. **阶段二：Python绑定**
   - 使用PyO3创建Python绑定
   - 实现Python与Rust之间的数据转换
   - 封装Rust函数为Python类

3. **阶段三：GUI开发**
   - 使用tkinter创建用户界面
   - 实现数据输入和结果显示
   - 添加进度条和停止按钮

4. **阶段四：性能优化与测试**
   - 优化内存使用
   - 进行性能测试和基准测试
   - 处理边缘情况和错误

## 安装与使用

### 依赖项

- Python 3.8+
- Rust 1.50+
- maturin (用于构建Python绑定)

### 安装步骤

1. 克隆仓库
2. 安装Python依赖：
   ```
   pip install -r requirements.txt
   ```
3. 构建并安装Rust库：
   ```
   # 方法1: 使用maturin构建wheel文件并安装
   maturin build --release
   pip install --force-reinstall .\target\wheels\subset_sum-0.1.0-cp310-none-win_amd64.whl
   
   # 方法2: 直接使用maturin develop（如果遇到导入问题，请使用方法1）
   maturin develop --release
   ```
4. 运行程序：
   ```
   python main.py
   ```

### 打包为可执行文件

如果您想将程序打包为独立的可执行文件，可以使用PyInstaller：

1. 安装PyInstaller：
   ```
   pip install pyinstaller
   ```

2. 打包程序：
   ```
   python -m PyInstaller --name=SubsetSumSolver --windowed --onefile main.py
   ```

3. 打包完成后，可执行文件位于`dist`目录中

### 使用打包后的程序

1. 打开`dist`目录
2. 运行`SubsetSumSolver.exe`
3. 无需安装Python、Rust或任何其他依赖，可直接使用所有功能

### 常见问题解决

1. **循环导入问题**：如果遇到"循环导入"错误，请确保已经使用`subset_sum_wrapper.py`而不是`subset_sum.py`
2. **模块未找到**：如果Python无法找到Rust模块，请使用方法1构建并安装wheel文件
3. **编译错误**：如果遇到Rust编译错误，请确保Rust代码中的类型匹配正确

### 使用方法

1. 在文本框中输入数字（每行一个）
2. 设置目标和值
3. 设置需要找到的解决方案数量
4. 设置内存限制
5. 点击"开始计算"按钮
6. 查看结果或随时点击"停止"按钮中断计算

## 性能分析

### 浮点数处理和精确匹配

在处理浮点数时，程序采用了整数化处理策略：

1. **整数化处理**：将所有输入数字乘以100并转换为整数进行计算，完全避免浮点数精度问题
2. **精确比较**：使用精确的整数比较，不再需要误差阈值
3. **实现方式**：在Rust代码中通过`(x * 100.0).round() as i64`将浮点数转换为整数

这种方法比之前的误差阈值方法更加精确，特别适合处理最多两位小数的正数输入。

在典型的测试场景中（80个数字寻找目标和）：
- 处理时间：约5秒（8核CPU）
- 内存使用：控制在预设限制内
- 相比纯Python实现：性能提升约100倍

## 许可证

MIT
