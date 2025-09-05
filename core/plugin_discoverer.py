import pkgutil
import logging
import os
from typing import List, Dict, Tuple
from .plugin_metadata import PluginMetadata, PluginMetadataManager


class PluginDiscoverer:
    """插件发现器，负责发现和识别可用的插件"""
    
    def __init__(self, plugins_path: str = "./plugins"):
        """
        初始化插件发现器
        
        Args:
            plugins_path: 插件目录路径
        """
        self.plugins_path = plugins_path
        self.metadata_manager = PluginMetadataManager(plugins_path)
        
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
                
            # 发现插件 - 加载符合 yoapi_plugin_xxx 命名规范的插件
            plugins = []
            for module_info in pkgutil.iter_modules([self.plugins_path]):
                if module_info.ispkg and module_info.name.startswith("yoapi_plugin_"):
                    plugins.append(module_info.name)
                        
            logging.info(f"发现 {len(plugins)} 个符合命名规范的插件: {plugins}")
            return plugins
            
        except Exception as e:
            logging.error(f"发现插件时发生错误: {e}")
            return []
            
    def discover_plugins_with_metadata(self) -> Dict[str, PluginMetadata]:
        """
        发现插件并加载其元数据
        
        Returns:
            插件名称到元数据的映射
        """
        plugins = self.discover_plugins()
        metadata_dict = {}
        
        for plugin_name in plugins:
            plugin_path = os.path.join(self.plugins_path, plugin_name)
            metadata = self.metadata_manager.load_plugin_metadata(plugin_name, plugin_path)
            
            if metadata:
                metadata_dict[plugin_name] = metadata
                
        logging.info(f"成功加载 {len(metadata_dict)}/{len(plugins)} 个插件的元数据")
        return metadata_dict
    
    def get_sorted_plugins(self) -> List[str]:
        """
        获取按依赖关系和优先级排序的插件列表
        
        Returns:
            排序后的插件名称列表
        """
        metadata_dict = self.discover_plugins_with_metadata()
        
        # 检查冲突
        conflicts = self.metadata_manager.check_conflicts(metadata_dict)
        if conflicts:
            for conflict in conflicts:
                logging.warning(conflict)
        
        # 解析依赖关系
        try:
            sorted_plugins = self.metadata_manager.resolve_dependencies(metadata_dict)
            logging.info(f"依赖解析完成，按顺序加载插件: {sorted_plugins}")
            return sorted_plugins
        except Exception as e:
            logging.warning(f"依赖解析失败，将按优先级排序: {e}")
            return self.metadata_manager.sort_by_priority(metadata_dict)
    
    def get_plugins_by_priority(self) -> List[Tuple[str, int]]:
        """
        获取插件及其优先级列表
        
        Returns:
            (插件名称, 优先级) 元组列表
        """
        metadata_dict = self.discover_plugins_with_metadata()
        plugins_with_priority = []
        
        for plugin_name, metadata in metadata_dict.items():
            if metadata.enabled:
                plugins_with_priority.append((plugin_name, metadata.priority))
        
        # 按优先级降序排序
        plugins_with_priority.sort(key=lambda x: x[1], reverse=True)
        return plugins_with_priority
            
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
    
    def has_plugin_metadata(self, plugin_name: str) -> bool:
        """
        检查插件是否有元数据文件
        
        Args:
            plugin_name: 插件名称
            
        Returns:
            是否有元数据文件
        """
        plugin_path = os.path.join(self.plugins_path, plugin_name)
        metadata_file = os.path.join(plugin_path, "plugin.json")
        return os.path.exists(metadata_file)
