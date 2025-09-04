import os
import subprocess
import sys
import logging
import importlib
from typing import Dict, Any, Optional


class IsolatedPluginExecutor:
    """隔离插件执行器，负责为有冲突的插件创建隔离执行环境"""
    
    def __init__(self, plugins_path: str = "./plugins"):
        """
        初始化隔离执行器
        
        Args:
            plugins_path: 插件目录路径
        """
        self.plugins_path = plugins_path
        self.isolated_environments: Dict[str, Dict[str, Any]] = {}  # 存储隔离环境信息
        
    def create_isolated_environment(self, plugin_name: str, python_version: str = "3.11") -> bool:
        """
        为插件创建隔离执行环境
        
        Args:
            plugin_name: 插件名称
            python_version: Python版本
            
        Returns:
            是否成功创建隔离环境
        """
        try:
            plugin_path = os.path.join(self.plugins_path, plugin_name)
            env_path = os.path.join(plugin_path, f".venv_{plugin_name}")
            
            # 检查是否已存在隔离环境
            if os.path.exists(env_path):
                logging.info(f"插件 {plugin_name} 的隔离环境已存在，跳过创建")
                return True
                
            logging.info(f"为插件 {plugin_name} 创建隔离环境...")
            
            # 使用uv创建虚拟环境
            result = subprocess.run(
                ["uv", "venv", env_path, "--python", python_version],
                capture_output=True,
                text=True,
                cwd=plugin_path
            )
            
            if result.returncode == 0:
                self.isolated_environments[plugin_name] = {
                    'env_path': env_path,
                    'python_version': python_version,
                    'status': 'created'
                }
                logging.info(f"成功为插件 {plugin_name} 创建隔离环境")
                return True
            else:
                logging.error(f"创建隔离环境失败: {result.stderr}")
                return False
                
        except Exception as e:
            logging.error(f"创建插件 {plugin_name} 隔离环境时发生错误: {e}")
            return False
            
    def install_dependencies_in_isolated_env(self, plugin_name: str) -> bool:
        """
        在隔离环境中安装插件依赖
        
        Args:
            plugin_name: 插件名称
            
        Returns:
            是否成功安装依赖
        """
        try:
            if plugin_name not in self.isolated_environments:
                logging.error(f"插件 {plugin_name} 没有隔离环境")
                return False
                
            plugin_path = os.path.join(self.plugins_path, plugin_name)
            requirements_file = os.path.join(plugin_path, "requirements.txt")
            env_path = self.isolated_environments[plugin_name]['env_path']
            
            # 检查是否存在requirements.txt文件
            if not os.path.exists(requirements_file):
                logging.info(f"插件 {plugin_name} 没有 requirements.txt 文件，跳过依赖安装")
                return True
                
            logging.info(f"在隔离环境中安装插件 {plugin_name} 的依赖...")
            
            # 使用uv pip在隔离环境中安装依赖
            abs_requirements_file = os.path.abspath(requirements_file)
            
            # 根据平台确定Python解释器路径
            if sys.platform == "win32":
                python_executable = os.path.join(env_path, "Scripts", "python.exe")
            else:
                python_executable = os.path.join(env_path, "bin", "python")
            
            result = subprocess.run(
                ["uv", "pip", "install", "-r", abs_requirements_file, "--python", python_executable],
                capture_output=True,
                text=True,
                cwd=plugin_path
            )
            
            if result.returncode == 0:
                self.isolated_environments[plugin_name]['status'] = 'dependencies_installed'
                logging.info(f"成功在隔离环境中安装插件 {plugin_name} 的依赖")
                return True
            else:
                logging.error(f"在隔离环境中安装依赖失败: {result.stderr}")
                return False
                
        except Exception as e:
            logging.error(f"在隔离环境中安装插件 {plugin_name} 依赖时发生错误: {e}")
            return False
            
    def load_plugin_from_isolated_env(self, plugin_name: str) -> Optional[Any]:
        """
        从隔离环境中加载插件模块
        
        Args:
            plugin_name: 插件名称
            
        Returns:
            插件模块，如果加载失败则返回None
        """
        try:
            if plugin_name not in self.isolated_environments:
                logging.error(f"插件 {plugin_name} 没有隔离环境")
                return None
                
            env_path = self.isolated_environments[plugin_name]['env_path']
            
            # 添加隔离环境的site-packages到Python路径
            site_packages_path = self._get_site_packages_path(env_path)
            if site_packages_path:
                sys.path.insert(0, site_packages_path)
            
            # 动态导入插件模块
            module = importlib.import_module(f"plugins.{plugin_name}")
            
            # 更新环境状态
            self.isolated_environments[plugin_name]['status'] = 'loaded'
            logging.info(f"成功从隔离环境中加载插件: {plugin_name}")
            
            return module
            
        except ImportError as e:
            logging.error(f"从隔离环境导入插件 {plugin_name} 失败: {e}")
            return None
        except Exception as e:
            logging.error(f"从隔离环境加载插件 {plugin_name} 时发生错误: {e}")
            return None
            
    def _get_site_packages_path(self, env_path: str) -> Optional[str]:
        """
        获取虚拟环境的site-packages路径
        
        Args:
            env_path: 虚拟环境路径
            
        Returns:
            site-packages路径，如果无法确定则返回None
        """
        # 根据不同平台确定site-packages路径
        if sys.platform == "win32":
            site_packages = os.path.join(env_path, "Lib", "site-packages")
        else:
            site_packages = os.path.join(env_path, "lib", f"python{sys.version_info.major}.{sys.version_info.minor}", "site-packages")
        
        if os.path.exists(site_packages):
            return site_packages
        return None
        
    def cleanup_isolated_env(self, plugin_name: str) -> bool:
        """
        清理插件的隔离环境
        
        Args:
            plugin_name: 插件名称
            
        Returns:
            是否成功清理
        """
        try:
            if plugin_name in self.isolated_environments:
                env_path = self.isolated_environments[plugin_name]['env_path']
                
                # 移除Python路径中的site-packages
                site_packages_path = self._get_site_packages_path(env_path)
                if site_packages_path and site_packages_path in sys.path:
                    sys.path.remove(site_packages_path)
                
                # 删除隔离环境目录
                import shutil
                if os.path.exists(env_path):
                    shutil.rmtree(env_path)
                
                # 从记录中移除
                del self.isolated_environments[plugin_name]
                
                logging.info(f"已清理插件 {plugin_name} 的隔离环境")
                return True
                
            return False
            
        except Exception as e:
            logging.error(f"清理插件 {plugin_name} 隔离环境时发生错误: {e}")
            return False
