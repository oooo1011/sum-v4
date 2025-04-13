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
        solutions: 解决方案列表
        file_path: 保存路径
        
    Returns:
        是否导出成功
    """
    try:
        # 创建工作簿
        workbook = xlsxwriter.Workbook(file_path)
        
        # 添加格式
        cell_format = workbook.add_format({'border': 1})
        selected_format = workbook.add_format({'border': 1, 'bg_color': '#FFFF00'})  # 黄色背景
        number_format = workbook.add_format({'border': 1, 'num_format': '0.00'})
        selected_number_format = workbook.add_format({'border': 1, 'num_format': '0.00', 'bg_color': '#FFFF00'})
        
        # 创建工作表
        sheet = workbook.add_worksheet("Result")
        
        # 收集所有选中的数字
        selected_numbers = set()
        if solutions:
            # 使用第一个解决方案
            for num in solutions[0]:
                selected_numbers.add(num)
        
        # 写入数据 - 直接显示结果，没有标题和表格
        for i, num in enumerate(input_numbers):
            # 第一列：输入数据
            if num in selected_numbers:
                sheet.write(i, 0, num, selected_number_format)
                # 第二列：如果被选中，则在第二列也显示
                sheet.write(i, 1, num, selected_number_format)
            else:
                sheet.write(i, 0, num, number_format)
                # 第二列：如果未选中，则留空
                sheet.write(i, 1, "", cell_format)
        
        # 设置列宽
        sheet.set_column(0, 0, 15)
        sheet.set_column(1, 1, 15)
        
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
