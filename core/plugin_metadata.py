import json
import os
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum


class PluginPriority(Enum):
    """插件优先级枚举"""
    LOWEST = 0
    LOW = 25
    NORMAL = 50
    HIGH = 75
    HIGHEST = 100
    SYSTEM = 1000  # 系统级插件


@dataclass
class PluginMetadata:
    """插件元数据类，用于管理插件的配置信息"""
    
    name: str
    version: str = "1.0.0"
    description: str = ""
    author: str = ""
    license: str = "MIT"
    priority: int = PluginPriority.NORMAL.value
    dependencies: List[str] = field(default_factory=list)
    conflicts: List[str] = field(default_factory=list)
    requires: List[str] = field(default_factory=list)
    provides: List[str] = field(default_factory=list)
    enabled: bool = True
    config_schema: Optional[Dict[str, Any]] = None
    
    # 内部字段
    _plugin_path: Optional[str] = None
    _metadata_file: Optional[str] = None
    
    @classmethod
    def from_file(cls, plugin_path: str) -> Optional['PluginMetadata']:
        """
        从plugin.json文件加载插件元数据
        
        Args:
            plugin_path: 插件目录路径
            
        Returns:
            PluginMetadata实例，如果加载失败则返回None
        """
        metadata_file = os.path.join(plugin_path, "plugin.json")
        
        if not os.path.exists(metadata_file):
            return None
            
        try:
            with open(metadata_file, 'r', encoding='utf-8') as f:
                metadata_data = json.load(f)
                
            # 验证必需字段
            if 'name' not in metadata_data:
                logging.error(f"插件元数据文件 {metadata_file} 缺少必需的 'name' 字段")
                return None
                
            # 创建元数据实例
            metadata = cls(
                name=metadata_data['name'],
                version=metadata_data.get('version', '1.0.0'),
                description=metadata_data.get('description', ''),
                author=metadata_data.get('author', ''),
                license=metadata_data.get('license', 'MIT'),
                priority=metadata_data.get('priority', PluginPriority.NORMAL.value),
                dependencies=metadata_data.get('dependencies', []),
                conflicts=metadata_data.get('conflicts', []),
                requires=metadata_data.get('requires', []),
                provides=metadata_data.get('provides', []),
                enabled=metadata_data.get('enabled', True),
                config_schema=metadata_data.get('config_schema'),
                _plugin_path=plugin_path,
                _metadata_file=metadata_file
            )
            
            logging.info(f"成功加载插件 {metadata.name} 的元数据")
            return metadata
            
        except json.JSONDecodeError as e:
            logging.error(f"插件元数据文件 {metadata_file} JSON格式错误: {e}")
            return None
        except Exception as e:
            logging.error(f"加载插件元数据文件 {metadata_file} 时发生错误: {e}")
            return None
    
    @classmethod
    def create_default(cls, plugin_name: str, plugin_path: str) -> 'PluginMetadata':
        """
        创建默认的插件元数据
        
        Args:
            plugin_name: 插件名称
            plugin_path: 插件目录路径
            
        Returns:
            默认的PluginMetadata实例
        """
        return cls(
            name=plugin_name,
            version="1.0.0",
            description=f"{plugin_name} plugin for WaveYo API",
            author="WaveYo Developer",
            license="MIT",
            priority=PluginPriority.NORMAL.value,
            dependencies=[],
            conflicts=[],
            requires=[],
            provides=[],
            enabled=True,
            config_schema=None,
            _plugin_path=plugin_path,
            _metadata_file=os.path.join(plugin_path, "plugin.json")
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """将元数据转换为字典"""
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "license": self.license,
            "priority": self.priority,
            "dependencies": self.dependencies,
            "conflicts": self.conflicts,
            "requires": self.requires,
            "provides": self.provides,
            "enabled": self.enabled,
            "config_schema": self.config_schema
        }
    
    def save(self) -> bool:
        """
        保存元数据到文件
        
        Returns:
            是否成功保存
        """
        if not self._metadata_file:
            logging.error("无法保存元数据：未设置元数据文件路径")
            return False
            
        try:
            with open(self._metadata_file, 'w', encoding='utf-8') as f:
                json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
                
            logging.info(f"已保存插件 {self.name} 的元数据到 {self._metadata_file}")
            return True
            
        except Exception as e:
            logging.error(f"保存插件元数据到 {self._metadata_file} 时发生错误: {e}")
            return False
    
    def validate(self) -> List[str]:
        """
        验证元数据的有效性
        
        Returns:
            错误消息列表，如果验证通过则返回空列表
        """
        errors = []
        
        # 验证名称
        if not self.name or not isinstance(self.name, str):
            errors.append("插件名称必须是非空字符串")
        
        # 验证版本格式
        if not self.version or not isinstance(self.version, str):
            errors.append("版本号必须是非空字符串")
        
        # 验证优先级范围
        if not isinstance(self.priority, int) or self.priority < 0 or self.priority > 1000:
            errors.append("优先级必须是0-1000之间的整数")
        
        # 验证依赖项类型
        if not isinstance(self.dependencies, list) or not all(isinstance(dep, str) for dep in self.dependencies):
            errors.append("依赖项必须是字符串列表")
        
        # 验证冲突项类型
        if not isinstance(self.conflicts, list) or not all(isinstance(conf, str) for conf in self.conflicts):
            errors.append("冲突项必须是字符串列表")
        
        return errors
    
    def has_dependency_conflicts(self, other_plugin: 'PluginMetadata') -> bool:
        """
        检查与另一个插件是否存在依赖冲突
        
        Args:
            other_plugin: 另一个插件元数据
            
        Returns:
            是否存在冲突
        """
        # 检查当前插件是否在另一个插件的冲突列表中
        if self.name in other_plugin.conflicts:
            return True
            
        # 检查另一个插件是否在当前插件的冲突列表中
        if other_plugin.name in self.conflicts:
            return True
            
        return False
    
    def __str__(self) -> str:
        return f"PluginMetadata(name={self.name}, version={self.version}, priority={self.priority})"
    
    def __repr__(self) -> str:
        return self.__str__()


class PluginMetadataManager:
    """插件元数据管理器，负责批量处理插件元数据"""
    
    def __init__(self, plugins_path: str = "./plugins"):
        self.plugins_path = plugins_path
        self.metadata_cache: Dict[str, PluginMetadata] = {}
    
    def load_all_metadata(self) -> Dict[str, PluginMetadata]:
        """
        加载所有插件的元数据
        
        Returns:
            插件名称到元数据的映射
        """
        from .plugin_discoverer import PluginDiscoverer
        
        discoverer = PluginDiscoverer(self.plugins_path)
        plugins = discoverer.discover_plugins()
        
        all_metadata = {}
        
        for plugin_name in plugins:
            plugin_path = os.path.join(self.plugins_path, plugin_name)
            metadata = self.load_plugin_metadata(plugin_name, plugin_path)
            
            if metadata:
                all_metadata[plugin_name] = metadata
                self.metadata_cache[plugin_name] = metadata
        
        return all_metadata
    
    def load_plugin_metadata(self, plugin_name: str, plugin_path: str) -> Optional[PluginMetadata]:
        """
        加载单个插件的元数据
        
        Args:
            plugin_name: 插件名称
            plugin_path: 插件目录路径
            
        Returns:
            PluginMetadata实例，如果加载失败则返回None
        """
        # 首先尝试从文件加载
        metadata = PluginMetadata.from_file(plugin_path)
        
        if metadata:
            return metadata
        
        # 如果没有元数据文件，创建默认元数据
        logging.info(f"插件 {plugin_name} 没有 plugin.json 文件，使用默认元数据")
        return PluginMetadata.create_default(plugin_name, plugin_path)
    
    def resolve_dependencies(self, metadata_dict: Dict[str, PluginMetadata]) -> List[str]:
        """
        解析插件依赖关系，返回拓扑排序的插件列表
        
        Args:
            metadata_dict: 插件名称到元数据的映射
            
        Returns:
            拓扑排序的插件名称列表
        """
        from collections import defaultdict, deque
        
        # 构建依赖图
        graph = defaultdict(list)
        in_degree = defaultdict(int)
        
        for plugin_name, metadata in metadata_dict.items():
            if not metadata.enabled:
                continue
                
            in_degree[plugin_name] = 0
            
            for dep in metadata.dependencies:
                if dep in metadata_dict and metadata_dict[dep].enabled:
                    graph[dep].append(plugin_name)
                    in_degree[plugin_name] += 1
        
        # 拓扑排序
        queue = deque([name for name, degree in in_degree.items() if degree == 0])
        result = []
        
        while queue:
            current = queue.popleft()
            result.append(current)
            
            for neighbor in graph[current]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        # 检查是否有循环依赖
        if len(result) != len([name for name, metadata in metadata_dict.items() if metadata.enabled]):
            logging.warning("检测到循环依赖或未解析的依赖关系")
            # 回退到优先级排序
            return self.sort_by_priority(metadata_dict)
        
        return result
    
    def sort_by_priority(self, metadata_dict: Dict[str, PluginMetadata]) -> List[str]:
        """
        按优先级对插件进行排序
        
        Args:
            metadata_dict: 插件名称到元数据的映射
            
        Returns:
            按优先级排序的插件名称列表（优先级高的在前）
        """
        enabled_plugins = [(name, metadata) for name, metadata in metadata_dict.items() if metadata.enabled]
        sorted_plugins = sorted(enabled_plugins, key=lambda x: x[1].priority, reverse=True)
        return [name for name, _ in sorted_plugins]
    
    def check_conflicts(self, metadata_dict: Dict[str, PluginMetadata]) -> List[str]:
        """
        检查插件之间的冲突
        
        Args:
            metadata_dict: 插件名称到元数据的映射
            
        Returns:
            冲突消息列表
        """
        conflicts = []
        plugin_names = list(metadata_dict.keys())
        
        for i, name1 in enumerate(plugin_names):
            for name2 in plugin_names[i+1:]:
                metadata1 = metadata_dict[name1]
                metadata2 = metadata_dict[name2]
                
                if metadata1.has_dependency_conflicts(metadata2):
                    conflicts.append(f"插件 {name1} 和 {name2} 存在冲突")
        
        return conflicts
