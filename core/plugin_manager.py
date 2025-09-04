import importlib
import pkgutil
import logging
import os
import subprocess
import sys
from typing import Dict, List, Any, Optional
from fastapi import FastAPI
from dotenv import load_dotenv
from .env_validator import get_env_validator


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
        self.plugin_env_vars: Dict[str, Dict[str, str]] = {}  # 存储插件环境变量映射
        
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
                logging.warning(f"[WARNING][plugin_manager]插件目录不存在: {self.plugins_path}")
                return []
                
            # 发现插件 - 只加载符合 yoapi-plugin-xxx 命名规范的插件
            plugins = []
            for module_info in pkgutil.iter_modules([self.plugins_path]):
                if module_info.ispkg and module_info.name.startswith("yoapi-plugin-"):  # 只处理符合命名规范的包类型插件
                    plugins.append(module_info.name)
                    
            logging.info(f"[INFO][plugin_manager]发现 {len(plugins)} 个符合命名规范的插件: {plugins}")
            return plugins
            
        except Exception as e:
            logging.error(f"[ERROR][plugin_manager]发现插件时发生错误: {e}")
            return []
            
    def _load_plugin_env_vars(self, plugin_name: str) -> bool:
        """
        加载插件的环境变量
        
        Args:
            plugin_name: 插件名称
            
        Returns:
            是否成功加载环境变量
        """
        try:
            plugin_path = os.path.join(self.plugins_path, plugin_name)
            env_file = os.path.join(plugin_path, '.env')
            
            if os.path.exists(env_file):
                # 记录当前环境变量状态用于冲突检测
                current_env_vars = {}
                for key in os.environ.keys():
                    current_env_vars[key] = os.getenv(key)
                
                load_dotenv(env_file, override=True)  # 插件变量优先于主项目变量
                
                # 检测环境变量冲突
                self._check_env_conflicts(plugin_name, current_env_vars)
                
                logging.info(f"[INFO][plugin_manager]已加载插件 {plugin_name} 的环境变量")
                return True
            return False
        except Exception as e:
            logging.warning(f"[WARNING][plugin_manager]加载插件 {plugin_name} 环境变量失败: {e}")
            return False
            
    def _check_env_conflicts(self, plugin_name: str, previous_env_vars: Dict[str, str]) -> None:
        """
        检查环境变量冲突
        
        Args:
            plugin_name: 插件名称
            previous_env_vars: 加载前的环境变量状态
        """
        conflicts = []
        
        for key in os.environ.keys():
            current_value = os.getenv(key)
            previous_value = previous_env_vars.get(key)
            
            # 检查是否是新设置的变量或者值发生了变化
            if previous_value is None and current_value is not None:
                # 新变量，检查是否与其他插件冲突
                for loaded_plugin, plugin_vars in self.plugin_env_vars.items():
                    if key in plugin_vars and plugin_vars[key] != current_value:
                        conflicts.append({
                            'variable': key,
                            'plugin1': loaded_plugin,
                            'value1': plugin_vars[key],
                            'plugin2': plugin_name,
                            'value2': current_value
                        })
            elif previous_value is not None and current_value != previous_value:
                # 变量值被覆盖，记录冲突
                conflicts.append({
                    'variable': key,
                    'previous_value': previous_value,
                    'new_value': current_value,
                    'plugin': plugin_name
                })
        
        # 记录冲突信息
        if conflicts:
            for conflict in conflicts:
                if 'plugin1' in conflict:
                    logging.warning(
                        f"[WARNING][plugin_manager]环境变量冲突: {conflict['variable']} "
                        f"在插件 {conflict['plugin1']}({conflict['value1']}) 和 "
                        f"{conflict['plugin2']}({conflict['value2']}) 中存在不同值"
                    )
                else:
                    logging.warning(
                        f"[WARNING][plugin_manager]环境变量被覆盖: {conflict['variable']} "
                        f"值从 '{conflict['previous_value']}' 改为 '{conflict['new_value']}' "
                        f"由插件 {conflict['plugin']} 修改"
                    )
        
        # 更新插件环境变量记录
        if plugin_name not in self.plugin_env_vars:
            self.plugin_env_vars[plugin_name] = {}
        
        for key in os.environ.keys():
            if key not in previous_env_vars or os.getenv(key) != previous_env_vars.get(key):
                self.plugin_env_vars[plugin_name][key] = os.getenv(key)
            
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
            
            # 动态导入插件模块
            module = importlib.import_module(f"plugins.{plugin_name}")
            
            # 检查插件是否包含register函数
            if not hasattr(module, 'register'):
                logging.warning(f"[WARNING][plugin_manager]插件 {plugin_name} 缺少 register 函数")
                return False
                
            # 调用插件的register函数
            module.register(self.app, **self.shared_dependencies)
            
            # 记录已加载的插件
            self.loaded_plugins[plugin_name] = {
                'module': module,
                'status': 'loaded'
            }
            
            logging.info(f"[INFO][plugin_manager]成功加载插件: {plugin_name}")
            return True
            
        except ImportError as e:
            logging.error(f"[ERROR][plugin_manager]导入插件 {plugin_name} 失败: {e}")
            return False
        except Exception as e:
            logging.error(f"[ERROR][plugin_manager]加载插件 {plugin_name} 时发生错误: {e}")
            return False
            
    def load_all_plugins(self) -> None:
        """
        加载所有发现的插件
        """
        plugins = self.discover_plugins()
        for plugin_name in plugins:
            self.load_and_register_plugin(plugin_name)
            
        logging.info(f"[INFO][plugin_manager]总共加载了 {len(self.loaded_plugins)}/{len(plugins)} 个插件")
        
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
                logging.info(f"[INFO][plugin_manager]插件 {plugin_name} 没有 requirements.txt 文件，跳过依赖安装")
                return True
                
            logging.info(f"[INFO][plugin_manager]开始安装插件 {plugin_name} 的依赖...")
            
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
                logging.info(f"[INFO][plugin_manager]插件 {plugin_name} 依赖安装成功")
                return True
            else:
                logging.error(f"[ERROR][plugin_manager]插件 {plugin_name} 依赖安装失败: {result.stderr}")
                return False
                
        except Exception as e:
            logging.error(f"[ERROR][plugin_manager]安装插件 {plugin_name} 依赖时发生错误: {e}")
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
            logging.warning(f"[WARNING][plugin_manager]插件 {plugin_name} 依赖安装失败，跳过加载")
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
                
        logging.info(f"[INFO][plugin_manager]总共成功加载了 {success_count}/{len(plugins)} 个插件（包含依赖安装）")
