import os
import subprocess
import sys
import logging
from typing import Dict, List, Optional


class DependencyManager:
    """依赖管理器，负责插件依赖的安装和冲突解决"""
    
    def __init__(self, plugins_path: str = "./plugins"):
        """
        初始化依赖管理器
        
        Args:
            plugins_path: 插件目录路径
        """
        self.plugins_path = plugins_path
        self.uv_available = self._check_uv_availability()
        self.plugin_dependencies: Dict[str, List[str]] = {}  # 存储插件依赖信息
        
    def _check_uv_availability(self) -> bool:
        """
        检查uv是否可用
        
        Returns:
            uv是否可用
        """
        try:
            result = subprocess.run(
                ["uv", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.SubprocessError, subprocess.TimeoutExpired):
            logging.warning("uv 不可用，将回退到标准 pip")
            return False
            
    def install_plugin_dependencies(self, plugin_name: str) -> bool:
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
                if self.uv_available:
                    # 尝试使用uv pip（更快）- 直接调用uv命令
                    result = subprocess.run(
                        ["uv", "pip", "install", "-r", abs_requirements_file],
                        capture_output=True,
                        text=True,
                        cwd=plugin_path
                    )
                else:
                    # 回退到标准pip
                    result = subprocess.run(
                        [sys.executable, "-m", "pip", "install", "-r", abs_requirements_file],
                        capture_output=True,
                        text=True,
                        cwd=plugin_path
                    )
            except (FileNotFoundError, subprocess.SubprocessError) as e:
                logging.error(f"安装命令执行失败: {e}")
                return False
            
            if result.returncode == 0:
                logging.info(f"插件 {plugin_name} 依赖安装成功")
                # 记录已安装的依赖
                self._record_plugin_dependencies(plugin_name, requirements_file)
                return True
            else:
                logging.error(f"插件 {plugin_name} 依赖安装失败: {result.stderr}")
                return False
                
        except Exception as e:
            logging.error(f"安装插件 {plugin_name} 依赖时发生错误: {e}")
            return False
            
    def _record_plugin_dependencies(self, plugin_name: str, requirements_file: str) -> None:
        """
        记录插件安装的依赖
        
        Args:
            plugin_name: 插件名称
            requirements_file: requirements.txt文件路径
        """
        try:
            with open(requirements_file, 'r', encoding='utf-8') as f:
                dependencies = [line.strip() for line in f if line.strip() and not line.startswith('#')]
                self.plugin_dependencies[plugin_name] = dependencies
        except Exception as e:
            logging.warning(f"记录插件 {plugin_name} 依赖失败: {e}")
            
    def get_plugin_dependencies(self, plugin_name: str) -> List[str]:
        """
        获取插件安装的依赖
        
        Args:
            plugin_name: 插件名称
            
        Returns:
            依赖列表
        """
        return self.plugin_dependencies.get(plugin_name, [])
        
    def is_uv_available(self) -> bool:
        """
        检查uv是否可用
        
        Returns:
            uv是否可用
        """
        return self.uv_available
        
    def check_dependency_conflicts(self, plugin_name: str) -> Optional[Dict]:
        """
        检查依赖冲突（使用UV进行冲突检测）
        
        Args:
            plugin_name: 插件名称
            
        Returns:
            冲突信息字典，如果没有冲突则返回None
        """
        if not self.uv_available:
            logging.warning(f"UV不可用，无法进行依赖冲突检测")
            return None
            
        try:
            plugin_path = os.path.join(self.plugins_path, plugin_name)
            requirements_file = os.path.join(plugin_path, "requirements.txt")
            
            # 检查是否存在requirements.txt文件
            if not os.path.exists(requirements_file):
                return None
                
            # 创建临时文件用于冲突检测
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as temp_file:
                temp_requirements = temp_file.name
                
            # 使用uv pip compile检测冲突
            result = subprocess.run(
                ["uv", "pip", "compile", "--output-file", temp_requirements, requirements_file],
                capture_output=True,
                text=True,
                cwd=plugin_path,
                timeout=30
            )
            
            # 清理临时文件
            try:
                os.unlink(temp_requirements)
            except:
                pass
            
            if result.returncode != 0:
                # 检测到冲突，解析错误信息
                conflict_info = self._parse_conflict_info(result.stderr, plugin_name)
                return conflict_info
                    
            return None
                
        except subprocess.TimeoutExpired:
            logging.warning(f"插件 {plugin_name} 依赖冲突检测超时")
            return {"type": "timeout", "plugin": plugin_name}
        except Exception as e:
            logging.warning(f"插件 {plugin_name} 依赖冲突检测失败: {e}")
            return None
            
    def _parse_conflict_info(self, stderr: str, plugin_name: str) -> Dict:
        """
        解析UV冲突检测的错误信息
        
        Args:
            stderr: UV命令的错误输出
            plugin_name: 插件名称
            
        Returns:
            冲突信息字典
        """
        conflict_info = {
            "type": "dependency_conflict",
            "plugin": plugin_name,
            "conflicts": []
        }
        
        # 简单的冲突信息解析
        lines = stderr.split('\n')
        for line in lines:
            if "Could not find a version that satisfies the requirement" in line:
                conflict_info["conflicts"].append({
                    "message": line.strip(),
                    "severity": "error"
                })
            elif "has requirement" in line and "but you have" in line:
                conflict_info["conflicts"].append({
                    "message": line.strip(),
                    "severity": "warning"
                })
                
        return conflict_info
        
    def install_plugin_dependencies_with_conflict_check(self, plugin_name: str) -> bool:
        """
        安装插件依赖（包含冲突检测和智能处理）
        
        Args:
            plugin_name: 插件名称
            
        Returns:
            是否成功安装依赖
        """
        # 先检查依赖冲突
        conflicts = self.check_dependency_conflicts(plugin_name)
        
        if conflicts:
            logging.warning(f"插件 {plugin_name} 存在依赖冲突: {conflicts}")
            # TODO: 这里可以添加智能冲突解决策略
            # 例如：自动降级版本、创建隔离环境等
            return False
            
        # 如果没有冲突，正常安装
        return self.install_plugin_dependencies(plugin_name)
