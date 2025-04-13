# 智能子集求和计算器

## 项目概述

这是一个高性能的子集组合求和软件，用于解决从一组数字中找出和为特定目标值的子集问题。软件采用Rust实现核心算法，Python构建GUI界面，充分利用多线程CPU，追求极致性能。

## 核心功能

- 高效解决子集和问题，从一组数字中找出和为目标值的子集
- 支持处理20-300个数字，优化处理40-120个数字的场景
- 每个数字视为独立，每个数字只能使用一次（无重复选择）
- 支持最多两位小数的正数
- 提供交互式GUI界面，用户友好的控制选项
- 支持设置最大解决方案数量和内存使用限制
- 提供实时进度显示和可随时停止功能
- 多线程设计，充分利用现代CPU性能
- 内存使用控制，避免占用过多系统资源

## 技术架构

- **前端**: Python + CustomTkinter，提供现代化UI体验
- **后端**: Rust + PyO3，高性能算法实现并与Python无缝集成
- **数据可视化**: Matplotlib，展示结果图表
- **数据处理**: 支持Excel文件导入导出

## 模块化架构

项目采用模块化设计，便于维护和扩展：

- **main.py**: 主程序，整合各模块，提供完整的应用功能
- **config.py**: 配置管理模块，负责存储用户首选项和最近使用的文件
- **gui_components.py**: GUI组件模块，包含所有界面元素和对话框
- **file_operations.py**: 文件操作模块，处理文件的导入导出功能
- **calculation.py**: 计算模块，负责子集和问题的求解和可视化
- **subset_sum_wrapper.py**: Rust核心算法的Python包装器

这种模块化结构提供以下优势：
- 每个模块专注于特定功能，提高代码可读性和可维护性
- 便于添加新功能和修复问题，无需修改整个程序
- 提高代码复用性，各模块可独立测试和使用
- 清晰的项目结构，便于新开发者理解

## 最新改进

### 1. 模块化代码重构
- 将单一的大型main.py拆分为多个功能专一的模块
- 实现更清晰的代码组织和更好的关注点分离
- 改进了代码的可维护性和可扩展性

### 2. 现代UI升级
- 从tkinter升级到CustomTkinter框架
- 支持暗/亮主题模式和系统主题跟随
- 圆角组件和一致的视觉设计语言

### 3. 优化的异步处理
- 使用队列机制实现UI与计算完全分离
- 改进的进度更新，避免UI冻结
- 更平滑的用户交互体验

### 4. Excel导出格式优化
- 简化Excel导出格式，移除多余表头
- 优化为两列格式：第一列为输入数据，第二列标记选中项
- 使用黄色高亮显示选中数字

### 5. 其他优化
- 重新设计的分栏布局，更合理利用空间
- 更直观的设置面板，使用选项卡组织不同功能
- 改进的文件操作，支持从Excel导入数据

## 核心算法优化
1. **并行计算优化**:
   - 工作窃取调度：使用rayon的join方法进行并行处理
   - 智能任务分割策略：设置并行阈值，优化递归深度
   - 线程池优化：设置合适的栈大小，自动配置线程数

2. **内存优化**:
   - 内存池：减少频繁内存分配和释放
   - 压缩表示：使用更紧凑的数据结构

## 使用方法

1. 在输入区域输入要处理的数字（每行一个）
2. 设置目标和、最大解决方案数量和内存限制
3. 点击"开始计算"开始求解
4. 结果将显示在右侧面板，包括文本结果和可视化图表
5. 可随时点击"停止"中断计算
6. 计算完成后可将结果导出到Excel文件

## 系统要求

- 操作系统: Windows 10+
- Python 3.8+
- Rust 1.50+

## 安装与运行

### 方法1: 使用可执行文件（推荐）

1. 下载 `子集组合求和.exe` 文件
2. 直接双击运行，无需安装Python或其他依赖

### 方法2: 从源码运行

1. 安装Python 3.8或更高版本
2. 安装Rust（用于编译核心算法）
3. 克隆本仓库
4. 安装依赖：`pip install -r requirements.txt`
5. 构建Rust模块：`pip install -e .`
6. 运行程序：`python main.py`

## 自定义打包

如果需要自行打包程序，可以使用以下命令：

```bash
python -m PyInstaller subset_sum_app.spec
```

生成的可执行文件位于`dist`目录下。

## 版本记录

### v1.3.0 (2025-04-13)
- 代码模块化重构，提高可维护性和扩展性
- 将单一main.py文件拆分为多个专用模块
- 添加显示导入数字数量的功能
- 优化异步进度更新机制
- 改进Excel导出格式
- 完成可执行文件打包

### v1.2.0
- 升级到CustomTkinter现代UI框架
- 增加暗/亮主题支持
- 添加结果可视化功能
- 优化内存使用

### v1.1.0
- 引入并行计算优化
- 添加内存限制功能
- 改进Excel导入导出

### v1.0.0
- 初始版本发布
- 实现基本子集和求解功能
- 提供基础GUI界面

## 许可证

MIT

## 项目总结

本项目是一个高性能子集求和问题求解器，使用Python+Rust混合架构，解决从一组数字中找出和为目标值的子集问题。主要特点包括：

1. **高性能混合架构**
   - 核心算法使用Rust实现，提供极高的计算性能
   - 用户界面使用Python实现，确保良好的用户体验和快速开发迭代

2. **优化的算法实现**
   - 并行计算支持，充分利用多核处理器
   - 内存使用优化，避免占用过多系统资源
   - 可设置最大解决方案数量，避免穷举所有解

3. **现代化用户界面**
   - 使用CustomTkinter实现的现代UI
   - 支持暗/亮两种主题模式
   - 直观的交互设计和实时进度显示

4. **模块化代码结构**
   - 各模块功能明确分离，方便维护和扩展
   - 每个模块专注于单一职责，符合软件工程最佳实践
   - 清晰的代码组织，便于新开发者理解项目

5. **便捷的数据导入导出**
   - 支持从文本文件和Excel文件导入数据
   - 优化的Excel导出格式，突出显示选中的数字
   - 提供导入数字统计功能

6. **可视化结果展示**
   - 使用图表直观展示计算结果
   - 提供数据占比和详细数值分析

7. **单文件分发**
   - 打包为单一可执行文件，方便分发和使用
   - 无需安装Python或其他依赖环境

通过这个项目，我们展示了如何结合多种技术手段解决复杂的组合优化问题，并将高性能计算能力与友好的用户体验相结合。
