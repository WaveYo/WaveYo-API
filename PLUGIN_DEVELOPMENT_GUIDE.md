# WaveYo-API 插件开发规范

## 概述

WaveYo-API 采用微内核架构，所有业务功能都以插件形式动态加载。本文档详细说明插件开发规范和要求。

## 插件类型规范

### 1. API端点插件

**用途**: 提供RESTful API端点

**文件结构**:
```
plugins/
└── api_plugin/
    ├── __init__.py          # 主文件，必须包含register函数
    ├── requirements.txt     # 插件依赖
    ├── .env                # 插件环境变量（可选）
    └── routers/            # 子路由（可选）
        └── v1.py
```

**代码示例**:
```python
# plugins/api_plugin/__init__.py
from fastapi import APIRouter, Depends
from plugins.log import get_log_service

router = APIRouter(prefix="/api", tags=["api"])

@router.get("/items")
async def get_items():
    logger = get_log_service().get_logger(__name__)
    logger.info("查询物品列表")
    return {"items": []}

def register(app, **dependencies):
    logger = get_log_service().get_logger(__name__)
    app.include_router(router)
    logger.info("API插件已注册")
```

### 2. 数据库服务插件

**用途**: 提供数据库连接和CRUD服务

**文件结构**:
```
plugins/
└── database/
    ├── __init__.py
    ├── requirements.txt
    ├── .env
    ├── models.py           # 数据模型
    └── services.py         # 服务类
```

**代码示例**:
```python
# plugins/database/__init__.py
import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# 加载插件环境变量
env_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(env_path):
    load_dotenv(env_path)

class DatabaseService:
    def __init__(self, db_url: str):
        self.engine = create_async_engine(db_url)
        self.async_session = sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )
    
    async def get_session(self):
        async with self.async_session() as session:
            yield session

def register(app, **dependencies):
    db_url = os.getenv("DB_URL")
    if not db_url:
        raise ValueError("DB_URL环境变量未设置")
    
    db_service = DatabaseService(db_url)
    dependencies['db_service'] = db_service
    
    logger = dependencies.get('log_service').get_logger(__name__)
    logger.info("数据库服务插件已加载")
```

### 3. 认证授权插件

**用途**: 提供无侵入式的安全控制

**文件结构**:
```
plugins/
└── auth/
    ├── __init__.py
    ├── requirements.txt
    ├── .env
    ├── middleware.py       # 认证中间件
    └── services.py         # 认证服务
```

**代码示例**:
```python
# plugins/auth/__init__.py
from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader

api_key_header = APIKeyHeader(name="X-API-Key")

async def api_key_auth(api_key: str = Depends(api_key_header)):
    # 验证API密钥逻辑
    if api_key != "valid-key":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的API密钥"
        )
    return api_key

def register(app, **dependencies):
    # 为所有路由添加认证依赖（除了特定路径）
    for route in app.routes:
        if hasattr(route, 'dependencies'):
            # 跳过健康检查和文档路由
            if not any(path in route.path for path in ['/health', '/docs', '/openapi']):
                route.dependencies.insert(0, Depends(api_key_auth))
    
    logger = dependencies.get('log_service').get_logger(__name__)
    logger.info("认证插件已加载，已为所有路由添加认证")
```

### 4. 工具类插件

**用途**: 提供通用工具功能

**文件结构**:
```
plugins/
└── utils/
    ├── __init__.py
    ├── requirements.txt
    ├── .env
    └── tools.py           # 工具函数
```

## 开发要求

### 文件结构规范

1. **必须包含的文件**:
   - `__init__.py` - 主文件，必须包含`register`函数
   - `requirements.txt` - 插件依赖声明

2. **可选文件**:
   - `.env` - 插件环境变量
   - `README.md` - 插件说明文档

### 日志规范

**日志格式**: `[级别][模块名]YY-MM-DD-HH:MM:SS || 消息内容`

**使用示例**:
```python
from plugins.log import get_log_service

logger = get_log_service().get_logger(__name__)

# 不同级别的日志
logger.debug("调试信息")
logger.info("普通信息")
logger.warning("警告信息")
logger.error("错误信息")
logger.critical("严重错误")

# 带上下文的日志
logger.info("成功查询到API密钥, ID: 67fac2dc-7c19-11f0-b527-b8cef6abb894")
```

### 依赖管理规范

1. **requirements.txt格式**:
```txt
# 注释说明
package-name==version
another-package>=1.2.0
```

2. **依赖安装**:
   - 系统会自动检测并安装插件依赖
   - 优先使用`uv pip`（直接调用uv命令），回退到标准`pip`
   - 使用绝对路径确保requirements.txt文件可访问
   - 依赖安装失败会导致插件加载失败

### 环境变量规范

1. **加载顺序**:
   - 首先加载插件自身的`.env`文件
   - 然后加载主项目的环境变量

2. **命名规范**:
   - 使用大写字母和下划线
   - 添加前缀避免冲突（如`PLUGIN_DB_URL`）

## 核心功能

### 插件依赖自动安装

系统提供两种加载方式：

1. **基础加载** (`load_all_plugins()`)
   - 仅加载插件，不安装依赖
   - 适用于依赖已预先安装的情况

2. **依赖感知加载** (`load_all_plugins_with_deps()`)
   - 自动检测并安装插件依赖
   - 支持`uv pip`和标准`pip`回退
   - 详细的安装日志记录

### 共享依赖使用

通过依赖注入获取共享服务：

```python
def register(app, **dependencies):
    # 获取日志服务
    log_service = dependencies.get('log_service')
    logger = log_service.get_logger(__name__)
    
    # 获取数据库服务
    db_service = dependencies.get('db_service')
    
    # 获取配置
    config = dependencies.get('config')
```

## 最佳实践

### 错误处理
```python
def register(app, **dependencies):
    try:
        # 插件初始化逻辑
        logger = dependencies.get('log_service').get_logger(__name__)
        logger.info("插件初始化成功")
    except Exception as e:
        logger.error(f"插件初始化失败: {e}")
        raise
```

### 性能优化
- 使用异步编程模式
- 避免在register函数中执行耗时操作
- 合理使用缓存

### 安全性
- 验证输入参数
- 使用环境变量存储敏感信息
- 遵循最小权限原则

## 插件示例模板

### 基础插件模板
```python
import os
from dotenv import load_dotenv
from fastapi import APIRouter
from plugins.log import get_log_service

# 加载环境变量
env_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(env_path):
    load_dotenv(env_path)

router = APIRouter()

@router.get("/test")
async def test_endpoint():
    logger = get_log_service().get_logger(__name__)
    logger.info("测试端点被调用")
    return {"status": "ok"}

def register(app, **dependencies):
    logger = get_log_service().get_logger(__name__)
    app.include_router(router)
    logger.info("插件已成功注册")
```

## 故障排除

### 常见问题

1. **插件加载失败**
   - 检查`register`函数是否存在
   - 验证依赖是否安装成功

2. **依赖安装失败**
   - 检查`requirements.txt`格式
   - 确认网络连接正常

3. **环境变量未加载**
   - 确认`.env`文件路径正确
   - 检查变量命名规范

### 调试技巧

启用调试日志：
```bash
LOG_LEVEL=DEBUG python main.py
```

检查已加载插件：
```bash
curl http://localhost:8000/
```

---

*最后更新: 2025-08-20*
*版本: 0.1.0*
