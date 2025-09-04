# WaveYo-API 插件开发规范

## 概述

WaveYo-API 采用核心-插件架构，所有业务功能都以插件形式动态加载。本文档详细说明插件开发规范和要求。

## 插件类型规范

### 1. API端点插件

**用途**: 提供RESTful API端点

**文件结构**:
```
plugins/
└── yoapi-plugin-demoapi/
    ├── __init__.py          # 主文件，必须包含register函数
    ├── requirements.txt     # 插件依赖
    ├── .env                # 插件环境变量（可选）
    └── routers/            # 子路由（可选）
        └── v1.py
```

**命名规范**: 必须使用 `yoapi-plugin-` 前缀，例如 `yoapi-plugin-demoapi`

**代码示例**:
```python
# plugins/yoapi-plugin-demoapi/__init__.py
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
└── yoapi-plugin-demodb/
    ├── __init__.py
    ├── requirements.txt
    ├── .env
    ├── models.py           # 数据模型
    └── services.py         # 服务类
```

**命名规范**: 必须使用 `yoapi-plugin-` 前缀，例如 `yoapi-plugin-mysql-demodb`

**代码示例**:
```python
# plugins/yoapi-plugin-demodb/__init__.py
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
└── yoapi-plugin-autdemoauthh/
    ├── __init__.py
    ├── requirements.txt
    ├── .env
    ├── middleware.py       # 认证中间件
    └── services.py         # 认证服务
```

**命名规范**: 必须使用 `yoapi-plugin-` 前缀，例如 `yoapi-plugin-demoauth`

**代码示例**:
```python
# plugins/yoapi-plugin-demoauth/__init__.py
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
└── yoapi-plugin-utils/
    ├── __init__.py
    ├── requirements.txt
    ├── .env
    └── tools.py           # 工具函数
```

**命名规范**: 必须使用 `yoapi-plugin-` 前缀，例如 `yoapi-plugin-utils`

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

1. **加载顺序和优先级**:
   - 插件环境变量 > 主项目环境变量
   - 插件管理器会自动加载插件目录下的`.env`文件
   - 支持环境变量覆盖（插件变量优先于主项目变量）

2. **命名规范**:
   - 使用大写字母和下划线命名（如`DATABASE_URL`, `API_KEY`）
   - 建议添加插件前缀避免冲突（如`LOG_LEVEL`, `HELLO_MESSAGE_TEMPLATE`）

3. **环境变量验证框架**:
   WaveYo-API提供了强大的环境变量验证框架，支持类型检查、默认值、必需性验证等：

   ```python
   from core.env_validator import get_env_validator, EnvVarType, create_env_schema

   # 定义环境变量模式
   ENV_SCHEMA = {
       "DB_URL": {
           "type": EnvVarType.STRING,
           "required": True,
           "description": "数据库连接URL"
       },
       "MAX_CONNECTIONS": {
           "type": EnvVarType.INTEGER,
           "required": False,
           "default": 10,
           "min": 1,
           "max": 100,
           "description": "最大连接数"
       },
       "DEBUG_MODE": {
           "type": EnvVarType.BOOLEAN,
           "required": False,
           "default": "false",
           "description": "调试模式开关"
       }
   }

   def register(app, **dependencies):
       # 验证环境变量
       validator = get_env_validator()
       try:
           env_vars = validator.validate_env_vars("your-plugin-name", ENV_SCHEMA)
           # 使用验证后的环境变量
           db_url = env_vars["DB_URL"]
       except ValueError as e:
           logger.error(f"环境变量验证失败: {e}")
           raise
   ```

4. **冲突检测机制**:
   - 系统会自动检测跨插件的环境变量冲突
   - 当多个插件设置相同的环境变量但值不同时会发出警告
   - 冲突检测包括：变量覆盖冲突和跨插件值不一致冲突

   **冲突示例警告**:
   ```
   [WARNING][plugin_manager]环境变量冲突: DATABASE_URL 在插件 plugin-a(mysql://localhost:3306/db1) 和 plugin-b(mysql://localhost:3306/db2) 中存在不同值
   [WARNING][plugin_manager]环境变量被覆盖: LOG_LEVEL 值从 'INFO' 改为 'DEBUG' 由插件 plugin-c 修改
   ```

5. **最佳实践**:
   - 使用环境变量验证框架确保变量类型和安全
   - 为可选变量提供合理的默认值
   - 避免使用过于通用的变量名（如`HOST`, `PORT`）
   - 在插件文档中明确说明所需的环境变量

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

## CLI工具使用

WaveYo-API 提供了强大的命令行工具来简化插件开发和管理流程：

### 插件管理命令

```bash
# 创建新插件（自动添加yoapi-plugin-前缀）
yoapi plugin new my-plugin

# 下载插件（从GitHub）
yoapi plugin download owner/repo-name

# 示例：下载MySQL数据库插件
yoapi plugin download WaveYo/yoapi-plugin-mysql-database

# 列出已安装的插件
yoapi plugin list

# 删除插件
yoapi plugin remove plugin-name
```

### 虚拟环境和依赖管理

```bash
# 创建虚拟环境（优先使用uv）
yoapi venv create

# 安装项目依赖
yoapi package install -r requirements.txt

# 安装特定包
yoapi package install package-name

# 卸载包
yoapi package uninstall package-name
```

### 项目运行

```bash
# 运行项目
yoapi run

# 运行项目（热重载模式）
yoapi run --reload
```

### 插件下载工具（原始方式）

```bash
# 使用原始下载工具
python plugin_downloader.py download owner/repo-name

# 列出已安装的插件
python plugin_downloader.py list

# 指定重试次数
python plugin_downloader.py download owner/repo-name --retries 5
```

## 故障排除

### 常见问题

1. **插件加载失败**
   - 检查`register`函数是否存在
   - 验证依赖是否安装成功
   - 确认插件名称符合`yoapi-plugin-xxx`规范

2. **依赖安装失败**
   - 检查`requirements.txt`格式
   - 确认网络连接正常
   - 尝试使用CLI工具重新安装依赖

3. **环境变量未加载**
   - 确认`.env`文件路径正确
   - 检查变量命名规范

4. **CLI工具问题**
   - 确保虚拟环境已激活
   - 检查Python路径是否正确

### 调试技巧

启用调试日志：
```bash
LOG_LEVEL=DEBUG python main.py
```

使用CLI工具运行：
```bash
yoapi run
```

检查已加载插件：
```bash
curl http://localhost:8000/
```

使用CLI工具列出插件：
```bash
yoapi plugin list
```

---

*最后更新: 2025-08-20*
*版本: 0.1.2*
