import importlib
import pkgutil
import logging
import os
import subprocess
import sys
from typing import Dict, List, Any, Optional
from fastapi import FastAPI


class PluginManager:
    """插件管理器，负责插件的发现、加载和注册"""
    
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
        self.shared_dependencies: Dict[str, Any] = {}
        
    def register_shared_dependency(self, name: str, dependency: Any) -> None:
        """
        注册共享依赖
        
        Args:
            name: 依赖名称
            dependency: 依赖对象
        """
        self.shared_dependencies[name] = dependency
        
    def discover_plugins(self) -> List[str]:
        """
        发现可用的插件

        Returns:
            插件名称列表
        """
        try:
            # 检查插件目录是否存在
            import os
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
            
    def load_and_register_plugin(self, plugin_name: str) -> bool:
        """
        加载并注册单个插件
        
        Args:
            plugin_name: 插件名称
            
        Returns:
            是否成功加载
        """
        try:
            # 动态导入插件模块
            module = importlib.import_module(f"plugins.{plugin_name}")
            
            # 检查插件是否包含register函数
            if not hasattr(module, 'register'):
                logging.warning(f"插件 {plugin_name} 缺少 register 函数")
                return False
                
            # 调用插件的register函数
            module.register(self.app, **self.shared_dependencies)
            
            # 记录已加载的插件
            self.loaded_plugins[plugin_name] = {
                'module': module,
                'status': 'loaded'
            }
            
            logging.info(f"成功加载插件: {plugin_name}")
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
        return self.shared_dependencies.get(name)
        
    def _install_plugin_dependencies(self, plugin_name: str) -> bool:
        """
        安装插件的依赖项
        
        Args:
            plugin_name: 插件名称
            
        Returns:
            是否成功安装依赖
        """
        try:
            plugin_path = os.path.join(self.plugins_path, plugin_name)
            requirements_file = os.path.join(plugin_path, "requirements.txt")
            
            # 检查是否存在requirements.txt文件
            if not os.path.exists(requirements_file):
                logging.info(f"插件 {plugin_name} 没有 requirements.txt 文件，跳过依赖安装")
                return True
                
            logging.info(f"开始安装插件 {plugin_name} 的依赖...")
            
            # 使用绝对路径确保文件可访问
            abs_requirements_file = os.path.abspath(requirements_file)
            
            # 使用uv pip安装依赖（如果可用），否则使用pip
            try:
                # 尝试使用uv pip（更快）- 直接调用uv命令
                result = subprocess.run(
                    ["uv", "pip", "install", "-r", abs_requirements_file],
                    capture_output=True,
                    text=True,
                    cwd=plugin_path
                )
            except (FileNotFoundError, subprocess.SubprocessError):
                # 回退到标准pip
                result = subprocess.run(
                    [sys.executable, "-m", "pip", "install", "-r", abs_requirements_file],
                    capture_output=True,
                    text=True,
                    cwd=plugin_path
                )
            
            if result.returncode == 0:
                logging.info(f"插件 {plugin_name} 依赖安装成功")
                return True
            else:
                logging.error(f"插件 {plugin_name} 依赖安装失败: {result.stderr}")
                return False
                
        except Exception as e:
            logging.error(f"安装插件 {plugin_name} 依赖时发生错误: {e}")
            return False
            
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
