import os
import contextlib
import sys
import uvicorn
from fastapi import FastAPI
from core import PluginManager


def is_uvicorn_reload() -> bool:
    """
    检测是否在uvicorn热重载模式下运行
    
    Returns:
        bool: 如果是热重载模式返回True，否则返回False
    """
    # 检查是否通过uvicorn启动且启用了reload参数
    return any("uvicorn" in arg and "--reload" in arg for arg in sys.argv)


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 获取插件管理器实例
    plugin_manager = app.state.plugin_manager
    
    # 启动时加载插件（按依赖关系顺序）
    plugin_manager.load_plugins_by_dependencies()
    
    # 如果不是uvicorn热重载模式，提示用户手动重启
    if not is_uvicorn_reload() and __name__ != "__main__":
        print("⚠️  提示: Python不支持热插拔，插件更改需要手动重启服务")
        print("💡 建议: 使用 'uvicorn main:create_app --reload' 启动以获得热重载支持")
    
    yield
    # 关闭时清理资源（可选）


def create_app() -> FastAPI:
    """创建并配置FastAPI应用"""
    
    # 创建FastAPI应用
    app = FastAPI(
        title="WaveYo-API",
        description="基于FastAPI的插件化后端服务",
        version="0.1.0",
        lifespan=lifespan
    )
    
    # 创建插件管理器
    plugin_manager = PluginManager(app, "./plugins")
    
    # 将插件管理器存储到应用状态
    app.state.plugin_manager = plugin_manager
    
    # 构建配置
    app_config = {
        'logging': {
            'level': os.getenv('LOG_LEVEL', 'INFO')
        }
    }
    
    # 注册共享依赖
    plugin_manager.register_shared_dependency('config', app_config)
        
    @app.get("/")
    async def root():
        """根端点"""
        return {
            "message": "Welcome to WaveYo-API",
            "version": "0.1.5",
            "loaded_plugins": list(plugin_manager.get_loaded_plugins().keys())
        }
    
    @app.get("/health")
    async def health_check():
        """健康检查端点"""
        return {"status": "healthy", "timestamp": "2025-08-20T01:31:00Z"}
    
    return app


if __name__ == "__main__":
    # 创建应用
    app = create_app()
    
    # 获取端口配置，支持环境变量和命令行参数
    port = int(os.getenv("PORT", 8000))
    
    # 检查命令行参数中是否有端口指定
    for i, arg in enumerate(sys.argv):
        if arg == "--port" and i + 1 < len(sys.argv):
            try:
                port = int(sys.argv[i + 1])
            except ValueError:
                print(f"⚠️  警告: 无效的端口号 '{sys.argv[i + 1]}'，使用默认端口 {port}")
        elif arg.startswith("--port="):
            try:
                port = int(arg.split("=")[1])
            except (ValueError, IndexError):
                print(f"⚠️  警告: 无效的端口号格式 '{arg}'，使用默认端口 {port}")
    
    # 启动服务器
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )
