import logging
from typing import Dict, Any, Optional


class SharedDependencyRegistry:
    """共享依赖注册表，负责管理插件间共享的依赖"""
    
    def __init__(self):
        self.shared_dependencies: Dict[str, Any] = {}
        
    def register_shared_dependency(self, name: str, dependency: Any) -> None:
        """
        注册共享依赖
        
        Args:
            name: 依赖名称
            dependency: 依赖对象
        """
        if name in self.shared_dependencies:
            logging.warning(f"共享依赖 '{name}' 已存在，将被覆盖")
        
        self.shared_dependencies[name] = dependency
        logging.info(f"已注册共享依赖: {name}")
        
    def get_shared_dependency(self, name: str) -> Optional[Any]:
        """
        获取共享依赖
        
        Args:
            name: 依赖名称
            
        Returns:
            依赖对象，如果不存在则返回None
        """
        dependency = self.shared_dependencies.get(name)
        if dependency is None:
            logging.debug(f"[DEBUG][shared_dependency_registry]共享依赖 '{name}' 不存在")
        return dependency
        
    def remove_shared_dependency(self, name: str) -> bool:
        """
        移除共享依赖
        
        Args:
            name: 依赖名称
            
        Returns:
            是否成功移除
        """
        if name in self.shared_dependencies:
            del self.shared_dependencies[name]
            logging.info(f"已移除共享依赖: {name}")
            return True
        return False
        
    def get_all_shared_dependencies(self) -> Dict[str, Any]:
        """
        获取所有共享依赖
        
        Returns:
            所有共享依赖的字典
        """
        return self.shared_dependencies.copy()
        
    def clear_all_shared_dependencies(self) -> None:
        """
        清除所有共享依赖
        """
        count = len(self.shared_dependencies)
        self.shared_dependencies.clear()
        logging.info(f"已清除所有 {count} 个共享依赖")
