# WaveYo-API

基于FastAPI的插件化后端服务，采用核心-插件架构设计。

## 特性

- 🚀 **核心-插件架构** - 所有功能以插件形式动态加载
- ⚡ **高性能** - 基于FastAPI和异步编程
- 📝 **统一日志** - 自定义日志格式和统一管理
- 🔧 **依赖自动安装** - 插件依赖自动检测和安装
- 🔐 **环境隔离** - 插件支持独立环境变量
- 📚 **完整文档** - 详细的开发规范和示例

## 项目结构

```
WaveYo-API/
├── core/                 # 核心模块
│   ├── __init__.py
│   └── plugin_manager.py # 插件管理器
├── plugins/              # 插件目录
│   ├── __init__.py
│   ├── yoapi-plugin-log/             # 日志服务插件
│   │   ├── __init__.py
│   │   ├── formatters.py
│   │   └── requirements.txt
│   └── yoapi-plugin-hello-world/     # Hello World示例插件
│       ├── __init__.py
│       └── requirements.txt
├── main.py              # 主程序入口
├── plugin_downloader.py # 插件下载工具
├── yoapi.py            # CLI工具
├── requirements.txt     # 主项目依赖
├── .env                # 环境变量配置
├── .env.example        # 环境变量示例
└── PLUGIN_DEVELOPMENT_GUIDE.md # 插件开发规范
```

## 快速开始

### 1. 使用CLI工具（推荐）

WaveYo-API 提供了强大的CLI工具来简化开发流程：

```bash
# 创建虚拟环境（优先使用uv）
yoapi venv create

# 激活虚拟环境（Windows）
.\.venv\Scripts\activate

# 或激活虚拟环境（Unix/Linux/Mac）
source .venv/bin/activate

# 安装项目依赖
yoapi package install -r requirements.txt

# 启动服务（开发模式）
yoapi run --reload
```

### 2. 传统方式

```bash
# 安装依赖
# 使用uv（推荐）
uv pip install -r requirements.txt

# 或使用pip
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env

# 编辑 .env 文件配置您的设置

# 启动服务
python main.py
```

服务将在 `http://localhost:8000` 启动。

### 4. 测试接口

```bash
# 根端点
curl http://localhost:8000/

# Hello World插件
curl http://localhost:8000/hello/
curl http://localhost:8000/hello/YourName

# 健康检查
curl http://localhost:8000/health

# API文档
打开 http://localhost:8000/docs
```

## CLI工具使用指南

WaveYo-API 提供了强大的命令行工具 `yoapi.py` 来简化开发流程：

### 虚拟环境管理
```bash
# 创建虚拟环境（优先使用uv）
yoapi venv create

# 激活虚拟环境后，可以使用以下命令
```

### 包管理
```bash
# 安装包（优先使用uv）
yoapi package install <package-name>

# 安装requirements.txt中的所有包
yoapi package install -r requirements.txt

# 卸载包
yoapi package uninstall <package-name>
```

### 插件管理
```bash
# 下载插件（从GitHub）
yoapi plugin download owner/repo-name

# 示例：下载MySQL数据库插件
yoapi plugin download WaveYo/yoapi-plugin-mysql-database

# 列出已安装的插件
yoapi plugin list

# 删除插件
yoapi plugin remove <plugin-name>

# 创建新插件（自动添加yoapi-plugin-前缀）
yoapi plugin new my-plugin
```

### 项目运行
```bash
# 运行项目
yoapi run

# 运行项目（热重载模式）
yoapi run --reload
```

## 插件开发

### 插件命名规范
所有插件必须遵循 `yoapi-plugin-xxx` 命名规范，例如：
- `yoapi-plugin-hello-world`
- `yoapi-plugin-log` 
- `yoapi-plugin-mysql-database`

系统只会加载符合此命名规范的插件。

### 插件下载工具
WaveYo-API 提供了插件下载工具，可以从GitHub自动下载插件：

```bash
# 使用CLI工具下载插件（推荐）
yoapi plugin download owner/repo-name

# 或使用原始下载工具
python plugin_downloader.py download owner/repo-name

# 示例：下载MySQL数据库插件
python plugin_downloader.py download WaveYo/yoapi-plugin-mysql-database

# 列出已安装的插件
python plugin_downloader.py list

# 指定重试次数
python plugin_downloader.py download owner/repo-name --retries 5
```

### 创建新插件

1. 在 `plugins/` 目录下创建符合命名规范的插件文件夹
2. 创建 `__init__.py` 文件并实现 `register` 函数
3. 添加 `requirements.txt` 文件声明依赖
4. （可选）添加 `.env` 文件配置环境变量

### 插件示例

参考 `plugins/yoapi-plugin-hello-world/` 和 `plugins/yoapi-plugin-log/` 插件实现。

### 详细规范

查看 [PLUGIN_DEVELOPMENT_GUIDE.md](./PLUGIN_DEVELOPMENT_GUIDE.md) 获取完整的开发规范。

## 核心功能

### 插件管理器

- 自动发现和加载插件
- 依赖自动安装（支持uv pip和标准pip）
- 共享依赖注入
- 插件生命周期管理

### 日志系统

统一日志格式：`[级别][模块名]YY-MM-DD-HH:MM:SS || 消息内容`

示例：
```
[INFO][plugins.hello_world]25-08-20-01:45:00 || Hello World插件已成功加载
```

### 环境变量管理

- 主项目环境变量（`.env`）
- 插件独立环境变量（插件目录下的 `.env`）
- 环境变量加载优先级：插件 > 主项目

## API端点

### 内置端点

- `GET /` - 根端点，显示已加载插件
- `GET /health` - 健康检查
- `GET /docs` - Swagger UI文档
- `GET /openapi.json` - OpenAPI规范

### 插件端点

- `GET /hello` - Hello World示例
- `GET /hello/{name}` - 带名称的问候

## 开发模式

### 调试模式

启用调试日志：
```bash
LOG_LEVEL=DEBUG python main.py
```

### 热重载

使用uvicorn热重载：
```bash
uvicorn main:create_app --reload --host 0.0.0.0 --port 8000
```

## 部署

### 生产环境部署

1. 设置生产环境变量
2. 使用Gunicorn + Uvicorn部署：
```bash
gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:create_app
```

### Docker Compose 本地开发

创建 `docker-compose.yml` 文件：

```yaml
version: '3.8'

services:
  waveyo-api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - LOG_LEVEL=INFO
    volumes:
      - .:/app
      - ./logs:/app/logs
    restart: unless-stopped
```

创建 `Dockerfile` 示例：

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件并安装
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 暴露端口
EXPOSE 8000

# 启动应用
CMD ["python", "main.py"]
```

启动服务：
```bash
docker-compose up --build
```

服务将在 `http://localhost:8000` 启动，支持代码热重载。

## 贡献指南

1. Fork 项目
2. 创建特性分支
3. 提交更改
4. 推送到分支
5. 创建Pull Request

## 许可证

[MIT License](./LICENSE)

## 支持

如有问题，请创建Issue或联系开发团队。

---

*版本: 0.1.0*
*最后更新: 2025-08-20*
