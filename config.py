"""
配置管理模块
负责应用程序配置的加载、保存和管理
"""

import os
import json
from typing import Any, Dict, List, Optional, Union

# 应用程序配置
APP_NAME = "子集组合求和"
APP_VERSION = "1.6.0-UI"  # 混合算法策略优化版本
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app_config.json")
DEFAULT_THEME = "dark"  # 默认主题模式

# 可用的主题列表
AVAILABLE_THEMES = [
    "dark", "light", "system"
]


class AppConfig:
    """应用程序配置管理类"""
    
    def __init__(self, config_file: str):
        """初始化配置管理"""
        self.config_file = config_file
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        default_config = {
            "window_geometry": "1200x800",
            "theme": DEFAULT_THEME,
            "show_visualization": True,
            "auto_save_results": False,
            "default_memory_limit": 500,  # 默认内存限制(MB)
            "default_max_solutions": 1,  # 默认最大解决方案数量
            "recent_files": [],  # 最近使用的文件
            "last_export_dir": ""  # 上次导出目录
        }
        
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    # 合并配置，确保所有默认值都存在
                    for key, value in default_config.items():
                        if key not in loaded_config:
                            loaded_config[key] = value
                    return loaded_config
            
            return default_config
        except Exception as e:
            print(f"加载配置文件出错: {str(e)}, 使用默认配置")
            return default_config
    
    def save_config(self) -> bool:
        """保存配置到文件"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=4)
            return True
        except Exception as e:
            print(f"保存配置文件出错: {str(e)}")
            return False
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值"""
        return self.config.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """设置配置值"""
        self.config[key] = value
    
    def add_recent_file(self, file_path: str) -> None:
        """添加最近使用的文件"""
        recent_files = self.get("recent_files", [])
        # 如果文件已存在，先移除它
        if file_path in recent_files:
            recent_files.remove(file_path)
        # 添加到列表前面
        recent_files.insert(0, file_path)
        # 保留最近的10个文件
        self.set("recent_files", recent_files[:10])
    
    def clear_recent_files(self) -> None:
        """清除最近使用的文件列表"""
        self.set("recent_files", [])
