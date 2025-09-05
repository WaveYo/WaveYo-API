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
    return {"items": []}

def register(app, **dependencies):
    # 获取日志服务
    logger = log_service.get_logger(__name__)
    
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
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from core.env_validator import get_env_validator, EnvVarType

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
    # 使用环境变量验证框架获取数据库URL
    validator = get_env_validator()
    env_schema = {
        "DB_URL": {
            "type": EnvVarType.STRING,
            "required": True,
            "description": "数据库连接URL"
        }
    }
    
    try:
        env_vars = validator.validate_env_vars("demodb", env_schema)
        db_url = env_vars["DB_URL"]
    except ValueError as e:
        # 获取日志服务记录错误
        log_service = dependencies.get('log_service')
        logger = log_service.get_logger(__name__)
        logger.error(f"环境变量验证失败: {e}")
        raise
    
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
from core.env_validator import get_env_validator, EnvVarType

api_key_header = APIKeyHeader(name="X-API-Key")

async def api_key_auth(api_key: str = Depends(api_key_header)):
    # 使用环境变量验证框架获取API密钥
    validator = get_env_validator()
    env_schema = {
        "VALID_API_KEY": {
            "type": EnvVarType.STRING,
            "required": True,
            "description": "有效的API密钥"
        }
    }
    
    try:
        env_vars = validator.validate_env_vars("demoauth", env_schema)
        valid_api_key = env_vars["VALID_API_KEY"]
    except ValueError as e:
        # 获取日志服务记录错误
        log_service = dependencies.get('log_service')
        logger = log_service.get_logger(__name__)
        logger.error(f"环境变量验证失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="服务器配置错误"
        )
    
    # 验证API密钥
    if api_key != valid_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的API密钥"
        )
    return api_key

def register(app, **dependencies):
    # 获取日志服务
    log_service = dependencies.get('log_service')
    logger = log_service.get_logger(__name__)
    
    # 为所有路由添加认证依赖（除了特定路径）
    for route in app.routes:
        if hasattr(route, 'dependencies'):
            # 跳过健康检查和文档路由
            if not any(path in route.path for path in ['/health', '/docs', '/openapi']):
                route.dependencies.insert(0, Depends(api_key_auth))
    
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

2. **推荐包含的文件**:
   - `plugin.json` - 插件元数据文件（推荐）
   - `.env` - 插件环境变量
   - `README.md` - 插件说明文档

### 插件元数据规范

WaveYo-API 提供了统一的插件元数据管理系统，类似 Node.js 的 package.json 系统：

**plugin.json 文件格式**:
```json
{
  "name": "yoapi-plugin-hello-world",
  "version": "1.0.0",
  "description": "示例Hello World插件",
  "author": "开发者名称",
  "priority": 50,
  "dependencies": ["yoapi-plugin-log"],
  "tags": ["example", "hello-world"]
}
```

**字段说明**:
- `name`: 插件名称（必须与目录名一致）
- `version`: 插件版本（遵循语义化版本规范）
- `description`: 插件描述
- `author`: 插件作者
- `priority`: 加载优先级（0-100，数值越大优先级越高，默认50）
- `dependencies`: 依赖的其他插件列表
- `tags`: 插件标签，用于分类和搜索

**向后兼容性**:
- 如果没有 `plugin.json` 文件，系统会自动生成默认元数据
- 默认优先级为50，无依赖关系
- 现有插件无需修改即可继续工作

**优先级加载机制**:
- 优先级范围：0-100，数值越大优先级越高
- 高优先级插件先加载，确保核心服务可用
- 依赖关系优先于优先级（依赖的插件先加载）

**依赖解析**:
- 使用拓扑排序算法解析插件依赖关系
- 自动检测循环依赖并报错
- 依赖关系确保被依赖的插件先加载

### 日志规范

**日志格式**: `[级别][模块名]YY-MM-DD-HH:MM:SS || 消息内容`

**使用示例**:
```python
# 在register函数中通过依赖注入获取日志服务
def register(app, **dependencies):
    # 获取日志服务
    log_service = dependencies.get('log_service')
    logger = log_service.get_logger(__name__)
    
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

### 插件元数据管理

WaveYo-API 提供了强大的插件元数据管理系统，支持：

1. **统一元数据格式**：类似 Node.js package.json 的标准化配置
2. **优先级加载**：支持 0-100 的优先级配置，数值越大优先级越高
3. **依赖管理**：声明式依赖关系，自动拓扑排序
4. **向后兼容**：无元数据文件的插件自动生成默认配置

### 智能加载策略

系统提供多种加载方式：

1. **基础加载** (`load_all_plugins()`)
   - 仅加载插件，不安装依赖
   - 适用于依赖已预先安装的情况

2. **依赖感知加载** (`load_all_plugins_with_deps()`)
   - 自动检测并安装插件依赖
   - 支持`uv pip`和标准`pip`回退
   - 详细的安装日志记录

3. **智能冲突处理** (`load_and_register_plugin_with_deps()`)
   - 自动检测依赖冲突
   - 冲突时自动创建隔离环境
   - 确保插件间依赖隔离

### 加载顺序算法

系统使用先进的加载算法确保正确的执行顺序：

1. **拓扑排序**：基于依赖关系确定加载顺序
2. **优先级排序**：在无依赖关系时按优先级加载
3. **混合策略**：依赖关系优先于优先级

**加载顺序示例**：
```python
# 假设有以下插件：
# - log插件 (优先级90，无依赖)
# - hello-world插件 (优先级50，依赖log插件)
# - utils插件 (优先级70，无依赖)

# 加载顺序：log插件 -> hello-world插件 -> utils插件
# (依赖关系优先，然后按优先级排序)
```

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
from fastapi import APIRouter

router = APIRouter()

@router.get("/test")
async def test_endpoint():
    logger.info("测试端点被调用")
    return {"status": "ok"}

def register(app, **dependencies):
    # 获取日志服务
    log_service = dependencies.get('log_service')
    logger = log_service.get_logger(__name__)
    
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

*最后更新: 2025-09-04*
*版本: 0.1.3*
