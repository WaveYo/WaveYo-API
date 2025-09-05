import importlib
import logging
import os
from typing import Dict, List, Any, Optional
from fastapi import FastAPI
from .plugin_discoverer import PluginDiscoverer
from .env_manager import EnvManager
from .dependency_manager import DependencyManager
from .isolated_executor import IsolatedPluginExecutor
from .shared_dependency_registry import SharedDependencyRegistry
from .env_validator import get_env_validator
from .plugin_metadata import PluginMetadata, PluginMetadataManager


class PluginManager:
    """插件管理器，负责协调各个模块完成插件的发现、加载和注册"""
    
    def __init__(self, app: FastAPI, plugins_path: str = "./plugins"):
        """
        初始化插件管理器
        
        Args:
            app: FastAPI应用实例
            plugins_path: 插件目录路径
        """
        self.app = app
        self.plugins_path = plugins_path
        self.loaded_plugins: Dict[str, Any] = {}
        
        # 初始化各个功能模块
        self.plugin_discoverer = PluginDiscoverer(plugins_path)
        self.env_manager = EnvManager()
        self.dependency_manager = DependencyManager(plugins_path)
        self.isolated_executor = IsolatedPluginExecutor(plugins_path)
        self.shared_dependency_registry = SharedDependencyRegistry()
        self.metadata_manager = PluginMetadataManager(plugins_path)
        
    def register_shared_dependency(self, name: str, dependency: Any) -> None:
        """
        注册共享依赖
        
        Args:
            name: 依赖名称
            dependency: 依赖对象
        """
        self.shared_dependency_registry.register_shared_dependency(name, dependency)
        
    def discover_plugins(self) -> List[str]:
        """
        发现可用的插件

        Returns:
            插件名称列表
        """
        return self.plugin_discoverer.discover_plugins()
    
    def discover_plugins_with_metadata(self) -> Dict[str, PluginMetadata]:
        """
        发现插件并加载其元数据
        
        Returns:
            插件名称到元数据的映射
        """
        return self.plugin_discoverer.discover_plugins_with_metadata()
    
    def get_sorted_plugins(self) -> List[str]:
        """
        获取按依赖关系和优先级排序的插件列表
        
        Returns:
            排序后的插件名称列表
        """
        return self.plugin_discoverer.get_sorted_plugins()
            
    def _load_plugin_env_vars(self, plugin_name: str) -> bool:
        """
        加载插件的环境变量
        
        Args:
            plugin_name: 插件名称
                        
        Returns:
            是否成功加载环境变量
        """
        return self.env_manager.load_plugin_env_vars(plugin_name, self.plugins_path)
            
            
    def load_and_register_plugin(self, plugin_name: str) -> bool:
        """
        加载并注册单个插件
        
        Args:
            plugin_name: 插件名称
            
        Returns:
            是否成功加载
        """
        try:
            # 先加载插件的环境变量
            self._load_plugin_env_vars(plugin_name)
            
            # 检查是否在隔离环境中安装了依赖
            module = None
            if plugin_name in self.isolated_executor.isolated_environments:
                # 从隔离环境中加载插件
                module = self._load_plugin_from_isolated_env(plugin_name)
            else:
                # 正常加载插件
                module = importlib.import_module(f"plugins.{plugin_name}")
            
            if module is None:
                logging.error(f"无法加载插件 {plugin_name} 的模块")
                return False
                
            # 检查插件是否包含register函数
            if not hasattr(module, 'register'):
                logging.warning(f"插件 {plugin_name} 缺少 register 函数")
                return False
                
            # 调用插件的register函数，传递共享依赖
            shared_deps = self.shared_dependency_registry.get_all_shared_dependencies()
            module.register(self.app, **shared_deps)
            
            # 记录已加载的插件
            self.loaded_plugins[plugin_name] = {
                'module': module,
                'status': 'loaded',
                'environment': 'isolated' if plugin_name in self.isolated_executor.isolated_environments else 'main'
            }
            
            logging.info(f"成功加载插件: {plugin_name} (环境: {self.loaded_plugins[plugin_name]['environment']})")
            return True
            
        except ImportError as e:
            logging.error(f"导入插件 {plugin_name} 失败: {e}")
            return False
        except Exception as e:
            logging.error(f"加载插件 {plugin_name} 时发生错误: {e}")
            return False
            
    def load_all_plugins(self) -> None:
        """
        加载所有发现的插件
        """
        plugins = self.discover_plugins()
        for plugin_name in plugins:
            self.load_and_register_plugin(plugin_name)
            
        logging.info(f"总共加载了 {len(self.loaded_plugins)}/{len(plugins)} 个插件")
        
    def get_loaded_plugins(self) -> Dict[str, Any]:
        """
        获取已加载的插件信息
        
        Returns:
            已加载插件的信息字典
        """
        return self.loaded_plugins
        
    def get_shared_dependency(self, name: str) -> Optional[Any]:
        """
        获取共享依赖
        
        Args:
            name: 依赖名称
            
        Returns:
            依赖对象，如果不存在则返回None
        """
        return self.shared_dependency_registry.get_shared_dependency(name)
        
    def _install_plugin_dependencies(self, plugin_name: str) -> bool:
        """
        安装插件的依赖项（包含智能冲突处理）
        
        Args:
            plugin_name: 插件名称
            
        Returns:
            是否成功安装依赖
        """
        # 先检查依赖冲突
        conflicts = self.dependency_manager.check_dependency_conflicts(plugin_name)
        
        if conflicts:
            logging.warning(f"插件 {plugin_name} 存在依赖冲突，尝试在隔离环境中安装...")
            
            # 创建隔离环境
            if not self.isolated_executor.create_isolated_environment(plugin_name):
                logging.error(f"无法为插件 {plugin_name} 创建隔离环境")
                return False
                
            # 在隔离环境中安装依赖
            if not self.isolated_executor.install_dependencies_in_isolated_env(plugin_name):
                logging.error(f"无法在隔离环境中安装插件 {plugin_name} 的依赖")
                return False
                
            logging.info(f"插件 {plugin_name} 的依赖已在隔离环境中成功安装")
            return True
            
        # 如果没有冲突，正常安装
        return self.dependency_manager.install_plugin_dependencies(plugin_name)
        
    def _load_plugin_from_isolated_env(self, plugin_name: str) -> Optional[Any]:
        """
        从隔离环境中加载插件模块
        
        Args:
            plugin_name: 插件名称
            
        Returns:
            插件模块，如果加载失败则返回None
        """
        return self.isolated_executor.load_plugin_from_isolated_env(plugin_name)
            
    def load_and_register_plugin_with_deps(self, plugin_name: str) -> bool:
        """
        加载并注册插件（包含依赖安装）
        
        Args:
            plugin_name: 插件名称
            
        Returns:
            是否成功加载
        """
        # 先安装依赖
        if not self._install_plugin_dependencies(plugin_name):
            logging.warning(f"插件 {plugin_name} 依赖安装失败，跳过加载")
            return False
            
        # 然后加载插件
        return self.load_and_register_plugin(plugin_name)
        
    def load_all_plugins_with_deps(self) -> None:
        """
        加载所有发现的插件（包含依赖安装）
        """
        plugins = self.discover_plugins()
        success_count = 0
        
        for plugin_name in plugins:
            if self.load_and_register_plugin_with_deps(plugin_name):
                success_count += 1
                
        logging.info(f"总共成功加载了 {success_count}/{len(plugins)} 个插件（包含依赖安装）")
        
    def load_all_plugins_with_priority(self) -> None:
        """
        按优先级加载所有插件（优先级高的先加载）
        """
        sorted_plugins = self.get_sorted_plugins()
        success_count = 0
        
        for plugin_name in sorted_plugins:
            if self.load_and_register_plugin_with_deps(plugin_name):
                success_count += 1
                
        logging.info(f"按优先级成功加载了 {success_count}/{len(sorted_plugins)} 个插件")
        
    def load_plugins_by_dependencies(self) -> None:
        """
        按依赖关系加载插件（先加载被依赖的插件）
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
            
            success_count = 0
            for plugin_name in sorted_plugins:
                if self.load_and_register_plugin_with_deps(plugin_name):
                    success_count += 1
                    
            logging.info(f"按依赖关系成功加载了 {success_count}/{len(sorted_plugins)} 个插件")
            
        except Exception as e:
            logging.warning(f"依赖解析失败，将按优先级排序: {e}")
            self.load_all_plugins_with_priority()
            
    def get_plugin_metadata(self, plugin_name: str) -> Optional[PluginMetadata]:
        """
        获取插件的元数据
        
        Args:
            plugin_name: 插件名称
            
        Returns:
            插件元数据，如果不存在则返回None
        """
        plugin_path = os.path.join(self.plugins_path, plugin_name)
        return self.metadata_manager.load_plugin_metadata(plugin_name, plugin_path)
        
    def validate_plugin_metadata(self, plugin_name: str) -> List[str]:
        """
        验证插件元数据的有效性
        
        Args:
            plugin_name: 插件名称
            
        Returns:
            错误消息列表，如果验证通过则返回空列表
        """
        metadata = self.get_plugin_metadata(plugin_name)
        if metadata:
            return metadata.validate()
        return ["无法加载插件元数据"]
        
    def create_plugin_metadata(self, plugin_name: str) -> bool:
        """
        为插件创建默认的元数据文件
        
        Args:
            plugin_name: 插件名称
            
        Returns:
            是否成功创建
        """
        plugin_path = os.path.join(self.plugins_path, plugin_name)
        metadata = PluginMetadata.create_default(plugin_name, plugin_path)
        return metadata.save()
        
    def get_plugins_status(self) -> Dict[str, Dict[str, Any]]:
        """
        获取所有插件的状态信息
        
        Returns:
            插件状态信息字典
        """
        metadata_dict = self.discover_plugins_with_metadata()
        status_info = {}
        
        for plugin_name, metadata in metadata_dict.items():
            status_info[plugin_name] = {
                'loaded': plugin_name in self.loaded_plugins,
                'enabled': metadata.enabled,
                'priority': metadata.priority,
                'dependencies': metadata.dependencies,
                'conflicts': metadata.conflicts,
                'has_metadata_file': self.plugin_discoverer.has_plugin_metadata(plugin_name),
                'environment': self.loaded_plugins[plugin_name]['environment'] if plugin_name in self.loaded_plugins else 'not_loaded'
            }
            
        return status_info
