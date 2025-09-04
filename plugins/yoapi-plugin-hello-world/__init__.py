limport os
from fastapi import APIRouter, Depends
from typing import Dict


# 环境变量由插件管理器统一加载
# 插件管理器会自动加载插件目录下的.env文件


# 创建路由器
router = APIRouter(prefix="/hello", tags=["hello"])


@router.get("/")
async def hello_world():
    """
    Hello World 示例端点
    
    Returns:
        dict: 欢迎消息
    """
    return {"message": "Hello, World! Welcome to WaveYo-API!"}


@router.get("/{name}")
async def hello_name(name: str):
    """
    带名称的Hello端点
    
    Args:
        name (str): 用户名
        
    Returns:
        dict: 个性化欢迎消息
    """
    return {"message": f"Hello, {name}! Welcome to WaveYo-API!"}


def register(app, **dependencies):
    """
    注册Hello World插件
    
    Args:
        app: FastAPI应用实例
        dependencies: 共享依赖
    """
    # 获取日志服务
    log_service = dependencies.get('log_service')
    if log_service:
        logger = log_service.get_logger(__name__)
        logger.info("Hello World插件已成功加载")
    
    # 将路由挂载到应用
    app.include_router(router)
    
    # 记录成功信息
    if log_service:
        logger.info(f"Hello World路由已注册: {[route.path for route in router.routes]}")
