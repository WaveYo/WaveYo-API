import pkgutil
import logging
import os
from typing import List


class PluginDiscoverer:
    """插件发现器，负责发现和识别可用的插件"""
    
    def __init__(self, plugins_path: str = "./plugins"):
        """
        初始化插件发现器
        
        Args:
            plugins_path: 插件目录路径
        """
        self.plugins_path = plugins_path
        
    def discover_plugins(self) -> List[str]:
        """
        发现可用的插件

        Returns:
            插件名称列表
        """
        try:
            # 检查插件目录是否存在
            if not os.path.exists(self.plugins_path) or not os.path.isdir(self.plugins_path):
                logging.warning(f"插件目录不存在: {self.plugins_path}")
                return []
                
            # 发现插件 - 只加载符合 yoapi-plugin-xxx 命名规范的插件
            plugins = []
            for module_info in pkgutil.iter_modules([self.plugins_path]):
                if module_info.ispkg and module_info.name.startswith("yoapi-plugin-"):  # 只处理符合命名规范的包类型插件
                    plugins.append(module_info.name)
                    
            logging.info(f"发现 {len(plugins)} 个符合命名规范的插件: {plugins}")
            return plugins
            
        except Exception as e:
            logging.error(f"发现插件时发生错误: {e}")
            return []
            
    def validate_plugin_structure(self, plugin_name: str) -> bool:
        """
        验证插件目录结构是否完整
        
        Args:
            plugin_name: 插件名称
            
        Returns:
            是否具有有效的插件结构
        """
        plugin_path = os.path.join(self.plugins_path, plugin_name)
        
        # 检查插件目录是否存在
        if not os.path.exists(plugin_path) or not os.path.isdir(plugin_path):
            return False
            
        # 检查是否有 __init__.py 文件（基本要求）
        init_file = os.path.join(plugin_path, "__init__.py")
        if not os.path.exists(init_file):
            logging.warning(f"插件 {plugin_name} 缺少 __init__.py 文件")
            return False
            
        return True
