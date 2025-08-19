import os
import logging
from dotenv import load_dotenv
from .formatters import CustomFormatter


# 加载插件自身的环境变量
env_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(env_path):
    load_dotenv(env_path)


class LogService:
    """日志服务类，提供统一的日志功能"""
    
    def __init__(self, config: dict = None):
        """
        初始化日志服务
        
        Args:
            config: 配置字典
        """
        self.config = config or {}
        self.loggers = {}
        
        # 配置根日志器
        self._setup_root_logger()
        
    def _setup_root_logger(self):
        """设置根日志器配置"""
        root_logger = logging.getLogger()
        
        # 设置日志级别
        log_level = self.config.get('logging', {}).get('level', 'INFO')
        root_logger.setLevel(getattr(logging, log_level.upper()))
        
        # 创建控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(CustomFormatter())
        
        # 清除现有处理器并添加新的
        root_logger.handlers = []
        root_logger.addHandler(console_handler)
        
    def get_logger(self, name: str) -> logging.Logger:
        """
        获取指定名称的日志器
        
        Args:
            name: 日志器名称（通常是模块名）
            
        Returns:
            配置好的日志器实例
        """
        if name not in self.loggers:
            logger = logging.getLogger(name)
            self.loggers[name] = logger
            
        return self.loggers[name]


# 全局日志服务实例
_log_service = None


def register(app, **dependencies):
    """
    注册日志插件
    
    Args:
        app: FastAPI应用实例
        dependencies: 共享依赖
    """
    global _log_service
    
    config = dependencies.get('config', {})
    _log_service = LogService(config)
    
    # 将日志服务注册为共享依赖
    dependencies['log_service'] = _log_service
    
    # 获取日志器并记录启动信息
    logger = _log_service.get_logger(__name__)
    logger.info("日志服务插件已成功加载")


def get_log_service() -> LogService:
    """
    获取日志服务实例
    
    Returns:
        LogService实例
    """
    global _log_service
    if _log_service is None:
        raise RuntimeError("日志服务尚未初始化")
    return _log_service
