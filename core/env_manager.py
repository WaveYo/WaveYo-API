import os
import logging
from typing import Dict
from dotenv import load_dotenv


class EnvManager:
    """环境变量管理器，负责插件环境变量的加载和冲突检测"""
    
    def __init__(self):
        self.plugin_env_vars: Dict[str, Dict[str, str]] = {}  # 存储插件环境变量映射
        
    def load_plugin_env_vars(self, plugin_name: str, plugins_path: str) -> bool:
        """
        加载插件的环境变量
        
        Args:
            plugin_name: 插件名称
            plugins_path: 插件目录路径
            
        Returns:
            是否成功加载环境变量
        """
        try:
            plugin_path = os.path.join(plugins_path, plugin_name)
            env_file = os.path.join(plugin_path, '.env')
            env_example_file = os.path.join(plugin_path, '.env.example')
            
            # 如果.env文件不存在但.env.example存在，自动复制示例文件
            if not os.path.exists(env_file) and os.path.exists(env_example_file):
                import shutil
                shutil.copy2(env_example_file, env_file)
                logging.info(f"已从 .env.example 创建 .env 文件用于插件 {plugin_name}")
            
            if os.path.exists(env_file):
                # 记录当前环境变量状态用于冲突检测
                current_env_vars = {}
                for key in os.environ.keys():
                    current_env_vars[key] = os.getenv(key)
                
                load_dotenv(env_file, override=True)  # 插件变量优先于主项目变量
                
                # 检测环境变量冲突
                self._check_env_conflicts(plugin_name, current_env_vars)
                
                logging.info(f"已加载插件 {plugin_name} 的环境变量")
                return True
            return True  # 如果没有.env文件，也返回True表示成功（没有环境变量需要加载）
        except Exception as e:
            logging.warning(f"加载插件 {plugin_name} 环境变量失败: {e}")
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
                        f"环境变量冲突: {conflict['variable']} "
                        f"在插件 {conflict['plugin1']}({conflict['value1']}) 和 "
                        f"{conflict['plugin2']}({conflict['value2']}) 中存在不同值"
                    )
                else:
                    logging.warning(
                        f"环境变量被覆盖: {conflict['variable']} "
                        f"值从 '{conflict['previous_value']}' 改为 '{conflict['new_value']}' "
                        f"由插件 {conflict['plugin']} 修改"
                    )
        
        # 更新插件环境变量记录
        if plugin_name not in self.plugin_env_vars:
            self.plugin_env_vars[plugin_name] = {}
        
        for key in os.environ.keys():
            if key not in previous_env_vars or os.getenv(key) != previous_env_vars.get(key):
                self.plugin_env_vars[plugin_name][key] = os.getenv(key)
                
    def get_plugin_env_vars(self, plugin_name: str) -> Dict[str, str]:
        """
        获取插件设置的环境变量
        
        Args:
            plugin_name: 插件名称
            
        Returns:
            插件设置的环境变量字典
        """
        return self.plugin_env_vars.get(plugin_name, {})
        
    def clear_plugin_env_vars(self, plugin_name: str) -> None:
        """
        清理插件设置的环境变量
        
        Args:
            plugin_name: 插件名称
        """
        if plugin_name in self.plugin_env_vars:
            del self.plugin_env_vars[plugin_name]
