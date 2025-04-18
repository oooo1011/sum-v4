"""
智能子集求和 - 主程序
模块化版本 (1.3.0)
"""

import customtkinter as ctk
import os
import platform
import tkinter as tk

# 导入自定义模块
from config import AppConfig, APP_NAME, APP_VERSION, CONFIG_FILE
from gui_components import AboutDialog, SettingsDialog, ThemeSwitcher, ExcelImportDialog
from file_operations import load_text_file, save_text_file, export_to_excel, parse_numbers
from calculation import CalculationManager, Visualizer


class SubsetSumApp:
    """子集组合求和应用"""
    
    def __init__(self, root):
        """初始化应用"""
        self.root = root
        self.root.title(f"{APP_NAME} - {APP_VERSION}")
        self.root.geometry("1200x800")
        self.root.minsize(800, 600)
        
        # 设置图标（如果有）
        icon_path = "app_icon.ico"
        if os.path.exists(icon_path):
            try:
                self.root.iconbitmap(icon_path)
                print(f"成功加载图标: {os.path.abspath(icon_path)}")
            except Exception as e:
                print(f"加载图标失败: {str(e)}")
        
        # 初始化配置
        self.config = AppConfig(CONFIG_FILE)
        
        # 初始化变量
        self.current_solutions = []
        self.input_numbers = []
        self.status_var = tk.StringVar(value="就绪")
        self.progress_var = tk.DoubleVar(value=0)
        
        # 设置主题
        ThemeSwitcher.apply_theme(self.config.get("theme", "system"))
        
        # 设置字体
        self._setup_fonts()
        
        # 读取Rust版本信息
        try:
            from subset_sum_wrapper import read_version_info
            self.version = read_version_info()
            self.status_var.set(f"已加载 {APP_NAME} {APP_VERSION} (核心: {self.version})")
        except:
            self.version = "未知"
            self.status_var.set(f"已加载 {APP_NAME} {APP_VERSION}")
        
        # 创建UI
        self._create_ui()
        
        # 初始化计算管理器
        self.calculation_manager = CalculationManager(
            on_progress_update=self._update_progress,
            on_result=self._display_results,
            on_error=self._display_error
        )
        
        # 注册关闭窗口事件
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
        
        # 自动加载上次的位置和尺寸
        last_geometry = self.config.get("window_geometry")
        if last_geometry:
            try:
                self.root.geometry(last_geometry)
            except:
                pass
        
        # UI创建方法
    def _create_input_area(self, parent_frame):
        """创建输入区域"""
        from gui_components import create_input_area
        self.numbers_text, self.load_button, self.save_button, self.target_entry, \
        self.solutions_var, self.solutions_spinbox, self.memory_var, self.memory_spinbox, \
        self.start_button, self.stop_button = create_input_area(
            parent_frame, 
            self.subtitle_font, 
            self.config, 
            self._load_from_file, 
            self._save_to_file, 
            self._start_calculation, 
            self._stop_calculation
        )
    
    def _create_result_area(self, parent_frame):
        """创建结果区域"""
        from gui_components import create_result_area
        self.progress_bar, self.progress_label, self.result_text, \
        self.export_button, self.canvas_frame = create_result_area(
            parent_frame, 
            self.subtitle_font, 
            self._export_results
        )
    
    def _setup_menu(self):
        """设置菜单"""
        from gui_components import setup_menu
        setup_menu(
            self.root, 
            self._load_from_file, 
            self._save_to_file, 
            self._copy, 
            self._paste,
            self._switch_theme, 
            self._open_settings, 
            self._about
        )
    
    def _setup_fonts(self):
        """设置字体"""
        self.default_font = ctk.CTkFont(family="Arial", size=10)
        self.title_font = ctk.CTkFont(family="Arial", size=16, weight="bold")
        self.subtitle_font = ctk.CTkFont(family="Arial", size=12, weight="bold")
    
    def _create_ui(self):
        """创建用户界面"""
        # 创建主框架
        main_frame = ctk.CTkFrame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 顶部标题和版本信息
        title_frame = ctk.CTkFrame(main_frame)
        title_frame.pack(fill=tk.X, pady=(0, 10))
        
        title_label = ctk.CTkLabel(title_frame, text="智能子集求和", font=self.title_font)
        title_label.pack(side=tk.LEFT)
        
        version_label = ctk.CTkLabel(title_frame, text=f"版本: {self.version}")
        version_label.pack(side=tk.RIGHT)
        
        # 创建左右分栏
        content_frame = ctk.CTkFrame(main_frame)
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        left_frame = ctk.CTkFrame(content_frame)
        right_frame = ctk.CTkFrame(content_frame)
        
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        # === 左侧：输入区域 ===
        self._create_input_area(left_frame)
        
        # === 右侧：结果和进度区域 ===
        self._create_result_area(right_frame)
        
        # 状态栏
        status_bar = ctk.CTkLabel(main_frame, textvariable=self.status_var, anchor="w", height=25)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X, pady=(10, 0))
        
        # 设置菜单
        self._setup_menu()
        
    # 界面行为方法
    def _on_closing(self):
        """窗口关闭时的处理"""
        # 保存窗口位置和大小
        self.config.set("window_geometry", self.root.geometry())
        
        # 保存配置
        self.config.save_config()
        
        # 停止计算
        if hasattr(self, 'calculation_manager') and self.calculation_manager.calculation_thread and self.calculation_manager.calculation_thread.is_alive():
            self.calculation_manager.stop_calculation()
            self.status_var.set("正在停止计算...")
            # 给计算线程一点时间来停止
            self.root.after(500, self.root.destroy)
        else:
            self.root.destroy()
    
    def _copy(self):
        """复制选中文本"""
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(self.numbers_text.selection_get())
        except:
            pass
    
    def _paste(self):
        """粘贴文本"""
        try:
            text = self.root.clipboard_get()
            self.numbers_text.insert("insert", text)
        except:
            pass
    
    def _switch_theme(self):
        """切换主题"""
        current_theme = self.config.get("theme", "system")
        new_theme = ThemeSwitcher.toggle_theme(current_theme)
        self.config.set("theme", new_theme)
        self.status_var.set(f"已切换到{new_theme}主题")
    
    def _about(self):
        """显示关于对话框"""
        AboutDialog(self.root, APP_NAME, APP_VERSION, self.version, self.title_font)
    
    def _open_settings(self):
        """打开设置对话框"""
        SettingsDialog(self.root, self.config, self._save_settings)
    
    def _save_settings(self, show_viz, auto_save, memory_limit, max_solutions, theme, dialog):
        """保存设置"""
        try:
            # 验证数字设置
            try:
                memory = int(memory_limit)
                if memory < 100:
                    raise ValueError("内存限制不能小于100MB")
                
                solutions = int(max_solutions)
                if solutions < 1:
                    raise ValueError("解决方案数量必须大于0")
                
            except ValueError as e:
                tk.messagebox.showerror("参数错误", str(e))
                return
            
            # 保存设置
            self.config.set("show_visualization", show_viz)
            self.config.set("auto_save_results", auto_save)
            self.config.set("default_memory_limit", memory)
            self.config.set("default_max_solutions", solutions)
            
            # 如果主题发生变化，应用新主题
            current_theme = self.config.get("theme", "system")
            if theme != current_theme:
                ThemeSwitcher.apply_theme(theme)
                self.config.set("theme", theme)
            
            # 保存配置
            self.config.save_config()
            
            # 更新界面状态
            self.memory_var.set(str(memory))
            self.solutions_var.set(str(solutions))
            
            self.status_var.set("设置已保存")
            
            # 关闭对话框
            if dialog:
                dialog.destroy()
                
        except Exception as e:
            tk.messagebox.showerror("保存设置错误", f"保存设置时出错: {str(e)}")
    
    # 文件操作方法
    def _load_from_file(self):
        """从文件加载数字"""
        from gui_components import handle_file_load
        handle_file_load(
            self.root, 
            self.numbers_text, 
            self.status_var, 
            self.config, 
            self._load_from_excel
        )
    
    def _load_from_excel(self, file_path):
        """从Excel文件加载数字"""
        try:
            # 显示Excel导入对话框
            ExcelImportDialog(self.root, file_path, self._import_excel_data)
        except Exception as e:
            tk.messagebox.showerror("Excel加载错误", f"无法加载Excel文件: {str(e)}")
    
    def _import_excel_data(self, workbook, sheet_name, column, start_row, end_row, dialog):
        """从Excel导入数据到文本框"""
        from file_operations import import_excel_data
        try:
            # 提取数据
            values = import_excel_data(workbook, sheet_name, column, start_row, end_row)
            
            # 更新文本框
            if values:
                self.numbers_text.delete(1.0, tk.END)
                for value in values:
                    self.numbers_text.insert(tk.END, f"{value:.2f}\n")
                
                self.status_var.set(f"从Excel导入了 {len(values)} 个数字")
                dialog.destroy()
            else:
                tk.messagebox.showwarning("导入警告", "没有找到有效的数字")
                
        except Exception as e:
            tk.messagebox.showerror("导入错误", f"导入过程中出错: {str(e)}")
    
    def _save_to_file(self):
        """保存数字到文件"""
        from gui_components import handle_file_save
        handle_file_save(
            self.root, 
            self.numbers_text, 
            self.status_var, 
            self.config
        )
    
    # 计算相关方法
    def _parse_target(self):
        """解析目标和"""
        target_str = self.target_entry.get().strip()
        if not target_str:
            raise ValueError("请输入目标和")
        
        try:
            target = float(target_str)
            if target <= 0:
                raise ValueError("目标和必须是正数")
            return target
        except ValueError:
            raise ValueError("目标和必须是有效的数字")
    
    def _parse_max_solutions(self):
        """解析最大解决方案数量"""
        try:
            value = int(self.solutions_var.get())
            if value < 1:
                raise ValueError("解决方案数量必须大于0")
            return value
        except ValueError:
            raise ValueError("解决方案数量必须是正整数")
    
    def _parse_memory_limit(self):
        """解析内存限制"""
        try:
            value = int(self.memory_var.get())
            if value < 100:
                raise ValueError("内存限制不能小于100MB")
            return value
        except ValueError:
            raise ValueError("内存限制必须是正整数")
    
    def _update_progress(self, progress):
        """更新进度条 - 不再使用，保留为兼容性"""
        # 仅在计算完成时启用UI
        if progress >= 100:
            self._enable_ui()
    
    def _start_calculation(self):
        """开始计算"""
        # 清除之前的结果
        self.result_text.delete(1.0, tk.END)
        
        # 解析输入
        try:
            numbers_text = self.numbers_text.get(1.0, tk.END)
            numbers = parse_numbers(numbers_text)
            target = self._parse_target()
            max_solutions = self._parse_max_solutions()
            memory_limit = self._parse_memory_limit()
        except ValueError as e:
            tk.messagebox.showerror("输入错误", str(e))
            return
        
        # 验证输入数量
        if len(numbers) < 2:
            tk.messagebox.showerror("输入错误", "请至少输入2个数字")
            return
        
        if len(numbers) > 300:
            tk.messagebox.showerror("输入错误", "数字数量不能超过300个")
            return
        
        # 存储原始数据
        self.input_numbers = numbers
        
        # 禁用UI
        self._disable_ui()
        
        # 清除之前的结果显示
        if hasattr(self, 'result_text'):
            self.result_text.configure(state="normal")
            self.result_text.delete(1.0, tk.END)
            self.result_text.insert(tk.END, "计算中，请稍候...\n")
            self.result_text.configure(state="disabled")
        
        # 状态提示（不再显示进度百分比）
        self.status_var.set(f"计算中... ({len(numbers)} 个数字, 目标和: {target})")
        
        # 强制更新界面，确保状态信息立即显示
        self.root.update()
        
        # 使用新的启动方法，传递root窗口用于UI刷新
        if hasattr(self.calculation_manager, 'start_calculation_with_progress'):
            self.calculation_manager.start_calculation_with_progress(
                numbers, target, max_solutions, memory_limit, self.root
            )
        else:
            # 兼容旧方法
            self.calculation_manager.start_calculation(numbers, target, max_solutions, memory_limit)
        
        # 启动队列检查
        self._check_calculation_queue()
    
    def _check_calculation_queue(self):
        """检查计算队列"""
        # 强制刷新界面，处理所有积压的GUI事件
        self.root.update()
        
        # 检查计算队列是否有结果
        has_result = self.calculation_manager.check_queue()
        
        # 如果计算仍在进行
        if not has_result and hasattr(self, 'calculation_manager') and self.calculation_manager.calculation_thread and self.calculation_manager.calculation_thread.is_alive():
            # 添加动态状态更新以显示程序正在运行
            current_status = self.status_var.get()
            if "计算中" in current_status and not current_status.endswith("..."):
                dots = current_status.count(".")
                if dots >= 3:
                    new_status = current_status.replace("...", "")
                else:
                    new_status = current_status + "."
                self.status_var.set(new_status)
            
            # 使用更短的时间间隔来更新UI
            self.root.after(10, self._check_calculation_queue)
    
    def _stop_calculation(self):
        """停止计算"""
        if hasattr(self, 'calculation_manager'):
            self.calculation_manager.stop_calculation()
            self.status_var.set("计算已停止")
            self._enable_ui()
    
    def _display_results(self, solutions, elapsed_time):
        """显示计算结果"""
        self.result_text.configure(state="normal")
        self.result_text.delete(1.0, tk.END)
        
        # 显示计算用时
        self.result_text.insert(tk.END, f"计算用时: {elapsed_time:.3f} 秒\n\n")
        
        if not solutions:
            self.result_text.insert(tk.END, "未找到解决方案")
            self.result_text.configure(state="disabled")
            self.status_var.set("计算完成，未找到解决方案")
            # 恢复UI状态
            self._enable_ui()
            return
        
        self.current_solutions = solutions
        
        # 解决方案导航部分
        if len(solutions) > 1:
            self.result_text.insert(tk.END, f"共找到 {len(solutions)} 个解决方案 (以下显示第1个解决方案的详细信息)\n")
            self.result_text.insert(tk.END, "要查看其他解决方案，请导出到Excel查看完整结果\n\n")
        
        # 为第一个解决方案找到原始输入中对应的索引 - 完全重写和修复
        
        # 预处理输入数字，建立值到索引的映射
        original_value_to_indices = {}
        for i, num in enumerate(self.input_numbers):
            if num not in original_value_to_indices:
                original_value_to_indices[num] = []
            original_value_to_indices[num].append(i)
        
        # 只处理第一个解决方案用于详细显示
        first_solution = solutions[0]
        
        # 定义解决方案匹配函数
        def match_solution(solution):
            # 为这个解决方案创建一个独立的可用索引集
            available_indices = {}
            for val, indices in original_value_to_indices.items():
                available_indices[val] = indices.copy()  # 复制确保独立
            
            # 收集匹配的索引
            matched_indices = []
            
            # 为每个元素找到匹配项
            for val in solution:
                if val in available_indices and available_indices[val]:
                    # 使用最前面的可用索引
                    idx = available_indices[val].pop(0)  # 弹出并移除第一个可用索引
                    matched_indices.append(idx)
            
            return matched_indices
        
        # 应用匹配函数找到第一个解决方案的索引
        first_solution_idx = match_solution(first_solution)
            
        # 创建表格形式的显示 - 第一个解决方案
        self.result_text.insert(tk.END, "输入数字列表              选中子集\n")
        self.result_text.insert(tk.END, "----------------------------------------\n")
        
        # 显示所有输入数字，并根据索引高亮选中项
        # first_solution_idx已在上面定义
        
        # 遍历所有输入数字
        for i, num in enumerate(self.input_numbers):
            is_selected = i in first_solution_idx
            # 使用制表符对齐
            if is_selected:
                self.result_text.insert(tk.END, f"{num:<20.2f} {num:>15.2f} ←\n")
            else:
                self.result_text.insert(tk.END, f"{num:<20.2f}\n")
        
        # 显示子集和
        self.result_text.insert(tk.END, "\n----------------------------------------\n")
        subset_sum = sum(solutions[0])
        self.result_text.insert(tk.END, f"子集和: {subset_sum:.2f}\n\n")
        
        # 如果有多个解决方案，显示其他解决方案的简要信息
        if len(solutions) > 1:
            self.result_text.insert(tk.END, f"其他解决方案简要信息:\n")
            for i, solution in enumerate(solutions[1:], 2):
                self.result_text.insert(tk.END, f"方案 {i}: 子集和 = {sum(solution):.2f}, 元素数 = {len(solution)}\n")
        
        self.result_text.configure(state="disabled")
        self.export_button.configure(state="normal")
        self.status_var.set(f"计算完成，找到 {len(solutions)} 个解决方案，用时 {elapsed_time:.3f} 秒")
        
        # 恢复UI状态
        self._enable_ui()
    
    def _display_error(self, error_msg):
        """显示错误信息"""
        self.result_text.configure(state="normal")
        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, error_msg)
        self.result_text.configure(state="disabled")
        self.status_var.set("计算出错")
        self._enable_ui()
    
    def _enable_ui(self):
        """启用UI控件"""
        self.start_button.configure(state="normal")
        self.stop_button.configure(state="disabled")
        self.numbers_text.configure(state="normal")
        self.target_entry.configure(state="normal")
        self.solutions_spinbox.configure(state="normal")
        self.memory_spinbox.configure(state="normal")
        if hasattr(self, 'current_solutions') and self.current_solutions:
            self.export_button.configure(state="normal")
    
    def _disable_ui(self):
        """禁用UI控件"""
        self.start_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        self.numbers_text.configure(state="disabled")
        self.target_entry.configure(state="disabled")
        self.solutions_spinbox.configure(state="disabled")
        self.memory_spinbox.configure(state="disabled")
        self.export_button.configure(state="disabled")
    
    def _export_results(self):
        """导出结果到Excel文件"""
        if not self.current_solutions:
            tk.messagebox.showinfo("导出提示", "没有结果可导出")
            return
        
        # 获取上次导出目录
        last_export_dir = self.config.get("last_export_dir")
        initial_dir = last_export_dir if last_export_dir and os.path.exists(last_export_dir) else os.path.dirname(os.path.abspath(__file__))
        
        file_path = tk.filedialog.asksaveasfilename(
            title="导出结果",
            initialdir=initial_dir,
            defaultextension=".xlsx",
            filetypes=[("Excel文件", "*.xlsx"), ("所有文件", "*.*")]
        )
        
        if not file_path:
            return
        
        # 保存导出目录
        self.config.set("last_export_dir", os.path.dirname(file_path))
        self.config.save_config()
        
        # 导出数据
        if export_to_excel(self.input_numbers, self.current_solutions, file_path):
            self.status_var.set(f"结果已导出至: {os.path.basename(file_path)}")
            
            # 询问用户是否打开文件
            if tk.messagebox.askyesno("导出成功", f"结果已成功导出到{os.path.basename(file_path)}。\n\n是否打开文件？"):
                try:
                    # 使用系统默认程序打开文件
                    import subprocess
                    if platform.system() == 'Windows':
                        os.startfile(file_path)
                    elif platform.system() == 'Darwin':  # macOS
                        subprocess.call(('open', file_path))
                    else:  # Linux或其他系统
                        subprocess.call(('xdg-open', file_path))
                except Exception as e:
                    tk.messagebox.showerror("打开文件错误", f"无法打开文件: {str(e)}")


def main():
    """主函数"""
    root = ctk.CTk()
    app = SubsetSumApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
