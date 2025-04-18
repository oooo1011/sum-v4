"""
文件操作模块
负责文件的导入导出功能
"""

import os
import re
import tkinter as tk
from tkinter import messagebox, filedialog
import xlsxwriter
import openpyxl
from typing import List, Dict, Any, Tuple, Optional, Callable


def load_text_file(file_path: str) -> Tuple[str, List[float]]:
    """加载文本文件
    
    Args:
        file_path: 文件路径
        
    Returns:
        (文件内容, 有效数字列表)
    """
    with open(file_path, 'r') as f:
        content = f.read()
    
    # 计算有效数字个数
    lines = [line.strip() for line in content.split('\n') if line.strip()]
    valid_numbers = []
    for line in lines:
        try:
            num = float(line)
            if num > 0:
                valid_numbers.append(num)
        except ValueError:
            continue
    
    return content, valid_numbers


def save_text_file(content: str, file_path: str) -> bool:
    """保存文本文件
    
    Args:
        content: 文本内容
        file_path: 文件路径
        
    Returns:
        是否保存成功
    """
    try:
        with open(file_path, 'w') as f:
            f.write(content)
        return True
    except Exception as e:
        messagebox.showerror("保存错误", f"无法保存文件: {str(e)}")
        return False


def import_excel_data(workbook, sheet_name: str, column: str, start_row: str, end_row: str) -> List[float]:
    """从Excel导入数据
    
    Args:
        workbook: openpyxl工作簿对象
        sheet_name: 工作表名称
        column: 列标识
        start_row: 起始行
        end_row: 结束行
        
    Returns:
        有效数字列表
    """
    # 获取工作表
    sheet = workbook[sheet_name]
    
    # 解析参数
    try:
        start = int(start_row)
        end = int(end_row)
        if start < 1:
            start = 1
        if end < start:
            end = start
    except ValueError:
        raise ValueError("行号必须是整数")
    
    # 提取数据
    values = []
    
    for row_idx in range(start, min(end + 1, sheet.max_row + 1)):
        cell = sheet[f"{column.upper()}{row_idx}"]
        if cell.value is not None:
            try:
                value = float(cell.value)
                if value <= 0:
                    continue
                values.append(value)
            except (ValueError, TypeError):
                pass
    
    return values


def export_to_excel(input_numbers: List[float], solutions: List[List[float]], file_path: str) -> bool:
    """导出结果到Excel
    
    Args:
        input_numbers: 输入数字列表
        solutions: 解决方案列表，每个元素是一个解决方案
        file_path: 保存路径
        
    Returns:
        是否导出成功
    """
    try:
        # 创建工作簿
        workbook = xlsxwriter.Workbook(file_path)
        
        # 添加格式
        header_format = workbook.add_format({'border': 1, 'bold': True, 'align': 'center'})
        cell_format = workbook.add_format({'border': 1})
        selected_format = workbook.add_format({'border': 1, 'bg_color': '#FFFF00'})  # 黄色背景
        number_format = workbook.add_format({'border': 1, 'num_format': '0.00'})
        selected_number_format = workbook.add_format({'border': 1, 'num_format': '0.00', 'bg_color': '#FFFF00'})
        
        # 创建工作表
        sheet = workbook.add_worksheet("Result")
        
        # 写入表头
        sheet.write(0, 0, "输入数据", header_format)
        solution_count = len(solutions)
        
        # 仅预先记录表头列数，实际表头内容将在去重后写入
        
        # 为每个解决方案找到原始输入中对应的索引 - 完全重写和修复
        solution_indices = []
        
        # 预处理输入数字，建立值到索引的映射
        original_value_to_indices = {}
        for i, num in enumerate(input_numbers):
            if num not in original_value_to_indices:
                original_value_to_indices[num] = []
            original_value_to_indices[num].append(i)
        
        # 定义重新匹配函数
        def match_solution(solution):
            # 为当前解决方案收集索引
            matched_indices = []
            
            # 使用资源池匹配算法
            # 对每个元素创建一个可用图(input_numbers -> 可用索引)
            available_indices = {}
            for val, indices in original_value_to_indices.items():
                available_indices[val] = indices.copy()  # 复制确保独立
            
            # 使用贪心算法为每个解决方案元素寻找匹配项
            for val in solution:
                if val in available_indices and available_indices[val]:
                    # 使用最前面的可用索引
                    idx = available_indices[val].pop(0)  # 弹出并移除第一个可用索引
                    matched_indices.append(idx)
            
            return matched_indices
        
        # 智能去重逻辑，保证显示用户需要的解决方案数量
        
        # 首先尝试去重
        unique_solutions = []
        unique_indices = []
        unique_solution_hash = set()  # 使用哈希集合加速查找
        
        # 对每个解决方案进行规范化处理
        for i, solution in enumerate(solutions):
            # 规范化处理：排序 + 转换为不可变类型用于哈希
            sorted_solution = tuple(sorted(solution))  
            
            # 如果这个解决方案不是重复的
            if sorted_solution not in unique_solution_hash:
                unique_solution_hash.add(sorted_solution)
                unique_solutions.append(solution)  # 添加原始解决方案
                unique_indices.append(match_solution(solution))  # 匹配并保存索引
        
        # 普通情况下使用唯一解
        solution_indices = unique_indices
        
        # 智能填充：如果唯一解决方案数量少于要求的数量
        if len(unique_indices) < solution_count:
            # 如果有唯一解，就重复使用这些解填充
            if unique_indices:
                print(f"\n\n\u8b66告：找到{len(unique_indices)}个唯一解，将重复填充至{solution_count}个")
                
                # 记录唯一解的数量，以便后续标记
                unique_count = len(unique_indices)
                
                # 填充到指定数量
                while len(solution_indices) < solution_count:
                    idx = len(solution_indices) % len(unique_indices)  # 循环使用唯一解
                    solution_indices.append(unique_indices[idx])
                    
            # 如果没有唯一解，就使用原始解决方案
            else:
                for i, solution in enumerate(solutions):
                    if i >= solution_count:
                        break
                    solution_indices.append(match_solution(solution))
        
        # 如果唯一解前多于要求的数量，截取前 solution_count 个
        if len(solution_indices) > solution_count:
            solution_indices = solution_indices[:solution_count]
            
        # 更新表头 - 确保正确标记唯一和重复解
        
        # 如果有唯一解数量变量，则使用它；否则使用unique_indices的长度
        unique_count = unique_count if 'unique_count' in locals() else len(unique_indices)
        
        # 输出调试信息
        print(f"\n调试：唯一解数量={unique_count}, 总解决方案数量={len(solution_indices)}")
        
        # 逻辑更简单明确，直接基于索引位置判断
        for i in range(len(solution_indices)):
            header_text = f"解决方案 {i + 1}"
            
            # 前 unique_count 个是唯一解，后面的是重复解
            if i < unique_count:
                header_text += " (唯一)"
                header_format_with_color = workbook.add_format({
                    'border': 1, 
                    'bold': True, 
                    'align': 'center',
                    'bg_color': '#DDFFDD'  # 淡绿色背景标识唯一解
                })
            else:
                header_text += " (重复)"
                header_format_with_color = workbook.add_format({
                    'border': 1, 
                    'bold': True, 
                    'align': 'center',
                    'bg_color': '#FFDDDD'  # 淡红色背景标识重复解
                })
            
            # 写入表头
            sheet.write(0, i + 1, header_text, header_format_with_color)
        
        # 写入数据
        for i, num in enumerate(input_numbers):
            # 写入行号 (序号从1开始)
            row = i + 1  # 因为第0行是表头
            
            # 第一列：输入数据
            sheet.write(row, 0, num, number_format)
            
            # 对于每个解决方案
            for sol_idx, solution_idx in enumerate(solution_indices):
                col = sol_idx + 1  # 解决方案列从1开始
                
                # 检查当前数字是否在当前解决方案中
                if i in solution_idx:
                    sheet.write(row, col, num, selected_number_format)
                else:
                    sheet.write(row, col, "", cell_format)
        
        # 设置列宽
        sheet.set_column(0, solution_count, 15)
        
        # 关闭工作簿
        workbook.close()
        return True
    except Exception as e:
        messagebox.showerror("导出错误", f"导出过程中出错: {str(e)}")
        return False


def parse_numbers(text: str) -> List[float]:
    """解析文本中的数字
    
    Args:
        text: 要解析的文本
        
    Returns:
        解析出的数字列表
    """
    lines = text.strip().split('\n')
    numbers = []
    
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
        
        try:
            # 验证数字格式（最多两位小数的正数）
            if not re.match(r'^[0-9]+(\.[0-9]{1,2})?$', line):
                raise ValueError(f"第 {i+1} 行: '{line}' 不是有效的正数（最多两位小数）")
            
            num = float(line)
            if num <= 0:
                raise ValueError(f"第 {i+1} 行: '{line}' 不是正数")
            
            numbers.append(num)
        except ValueError as e:
            raise ValueError(str(e))
    
    return numbers
