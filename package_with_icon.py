"""
专用打包脚本，确保图标正确应用
"""
import os
import sys
import subprocess
import shutil
from pathlib import Path

# 图标文件路径
ICON_FILE = "windows_app_icon.ico"
ICON_PATH = os.path.abspath(ICON_FILE)

# 检查图标文件是否存在
if not os.path.exists(ICON_PATH):
    print(f"错误: 找不到图标文件 {ICON_PATH}")
    sys.exit(1)

print(f"使用图标: {ICON_PATH}")

# 创建.spec文件内容
SPEC_CONTENT = f'''# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('version_info.txt', '.'), ('{ICON_FILE}', '.')],
    hiddenimports=['xlsxwriter', 'openpyxl', 'matplotlib', 'customtkinter', 
                   'config', 'gui_components', 'file_operations', 'calculation', 
                   'subset_sum_wrapper'],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='子集组合求和',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=r'{ICON_PATH}',
)
'''

# 写入自定义spec文件
SPEC_FILE = "custom_icon_app.spec"
with open(SPEC_FILE, "w", encoding="utf-8") as f:
    f.write(SPEC_CONTENT)

print(f"已创建自定义spec文件: {SPEC_FILE}")

# 清理旧的构建文件
print("清理旧的构建文件...")
build_dir = Path("build")
dist_dir = Path("dist")
if build_dir.exists():
    try:
        shutil.rmtree(build_dir)
        print("- 已删除build目录")
    except Exception as e:
        print(f"- 无法删除build目录: {e}")

if dist_dir.exists():
    try:
        shutil.rmtree(dist_dir)
        print("- 已删除dist目录")
    except Exception as e:
        print(f"- 无法删除dist目录: {e}")

# 运行PyInstaller
print("\n开始打包...")
cmd = ["python", "-m", "PyInstaller", SPEC_FILE, "--clean"]
print(f"执行命令: {' '.join(cmd)}")

try:
    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    print("打包成功!")
    
    # 检查可执行文件是否存在
    exe_path = os.path.join("dist", "子集组合求和.exe")
    if os.path.exists(exe_path):
        print(f"可执行文件已创建: {os.path.abspath(exe_path)}")
    else:
        print(f"警告: 找不到生成的可执行文件 {exe_path}")
    
except subprocess.CalledProcessError as e:
    print(f"打包失败: {e}")
    print("\n错误输出:")
    print(e.stderr)
    
print("\n提示: 如果图标仍然不显示，可能是Windows图标缓存的问题。")
print("可以尝试运行以下命令刷新图标缓存: ie4uinit.exe -show")
