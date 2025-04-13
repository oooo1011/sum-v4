"""
使用PyInstaller打包应用程序，并确保正确应用图标
"""
import os
import subprocess
import shutil

# 确保图标文件存在
icon_path = "app_icon.ico"
if not os.path.exists(icon_path):
    print(f"错误: 图标文件 {icon_path} 不存在")
    exit(1)

# 获取图标的绝对路径
abs_icon_path = os.path.abspath(icon_path)
print(f"使用图标: {abs_icon_path}")

# 构建PyInstaller命令
cmd = [
    "python", "-m", "PyInstaller",
    "--name=子集组合求和",
    f"--icon={abs_icon_path}",
    "--windowed",
    "--onefile",
    "--clean",
    "--add-data", "version_info.txt;.",
    "--hidden-import=xlsxwriter",
    "--hidden-import=openpyxl",
    "--hidden-import=matplotlib",
    "--hidden-import=customtkinter",
    "--hidden-import=config",
    "--hidden-import=gui_components",
    "--hidden-import=file_operations",
    "--hidden-import=calculation",
    "--hidden-import=subset_sum_wrapper",
    "main.py"
]

# 执行命令
print("开始打包...")
print(" ".join(cmd))
result = subprocess.run(cmd, capture_output=True, text=True)

# 输出结果
print("\n--- 打包输出 ---")
print(result.stdout)

if result.stderr:
    print("\n--- 错误信息 ---")
    print(result.stderr)

# 检查是否成功
if result.returncode == 0:
    print("\n打包成功！")
    print(f"可执行文件位于: {os.path.abspath('dist/子集组合求和.exe')}")
    
    # 复制图标到dist目录，以便在运行时也能找到
    try:
        shutil.copy(icon_path, "dist/")
        print(f"已复制图标到dist目录")
    except Exception as e:
        print(f"复制图标时出错: {str(e)}")
else:
    print("\n打包失败！")
