#!/usr/bin/env python3
"""
WaveYo-API CLI 工具
统一的项目管理和插件开发工具
"""

import argparse
import os
import sys
import subprocess
import shutil
import platform
from pathlib import Path
from typing import Optional, List, Tuple


class YoAPICLI:
    """WaveYo-API CLI 工具类"""
    
    def __init__(self):
        self.project_root = Path.cwd()
        self.plugins_dir = self.project_root / "plugins"
        self.venv_dir = self.project_root / ".venv"
        self.config_file = self.project_root / ".yoapirc"
        
    def check_uv_available(self) -> bool:
        """
        检查uv包管理器是否可用
        
        Returns:
            bool: uv是否可用
        """
        try:
            result = subprocess.run(["uv", "--version"], capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
            return False
    
    def get_package_manager(self) -> Tuple[str, str]:
        """
        获取包管理器
        
        Returns:
            Tuple[str, str]: (包管理器名称, 包管理器命令)
        """
        if self.check_uv_available():
            return ("uv", "uv pip")
        
        # 询问用户是否使用pip
        print("❌ uv包管理器不可用")
        choice = input("是否使用pip作为替代？(y/N): ").lower().strip()
        if choice == 'y':
            return ("pip", "pip")
        else:
            print("💡 建议安装uv以获得更好的性能:")
            print("   curl -LsSf https://astral.sh/uv/install.sh | sh")
            print("   或者使用pip安装: pip install uv")
            sys.exit(1)
    
    def create_venv(self) -> int:
        """
        创建虚拟环境
        
        Returns:
            int: 退出代码
        """
        pkg_manager, pkg_cmd = self.get_package_manager()
        
        if pkg_manager == "uv":
            print("🔄 使用uv创建虚拟环境...")
            cmd = ["uv", "venv", ".venv"]
        else:
            print("🔄 使用venv创建虚拟环境...")
            cmd = [sys.executable, "-m", "venv", ".venv"]
        
        try:
            result = subprocess.run(cmd)
            if result.returncode == 0:
                print("✅ 虚拟环境创建成功")
                
                # 提供激活指令
                if os.name == 'nt':  # Windows
                    print("请激活虚拟环境:")
                    print("    .venv\\Scripts\\activate")
                else:  # Unix/Linux/Mac
                    print("请激活虚拟环境:")
                    print("    source .venv/bin/activate")
                
                return 0
            else:
                print("❌ 虚拟环境创建失败")
                return 1
        except Exception as e:
            print(f"❌ 创建虚拟环境时出错: {e}")
            return 1
    
    def install_package(self, package_name: str) -> int:
        """
        安装Python包
        
        Args:
            package_name: 包名称或requirements.txt文件路径
            
        Returns:
            int: 退出代码
        """
        if not self.ensure_venv_activated():
            return 1
        
        pkg_manager, pkg_cmd = self.get_package_manager()
        
        # 检查是否是requirements.txt文件
        if package_name.endswith('.txt') and os.path.exists(package_name):
            if pkg_manager == "uv":
                cmd = ["uv", "pip", "install", "-r", package_name]
            else:
                cmd = ["pip", "install", "-r", package_name]
        else:
            if pkg_manager == "uv":
                cmd = ["uv", "pip", "install", package_name]
            else:
                cmd = ["pip", "install", package_name]
        
        try:
            print(f"📦 使用{pkg_manager}安装包: {package_name}")
            return subprocess.run(cmd).returncode
        except Exception as e:
            print(f"❌ 安装包失败: {e}")
            return 1
    
    def uninstall_package(self, package_name: str) -> int:
        """
        卸载Python包
        
        Args:
            package_name: 包名称
            
        Returns:
            int: 退出代码
        """
        if not self.ensure_venv_activated():
            return 1
        
        pkg_manager, pkg_cmd = self.get_package_manager()
        
        if pkg_manager == "uv":
            cmd = ["uv", "pip", "uninstall", package_name]
        else:
            cmd = ["pip", "uninstall", "-y", package_name]
        
        try:
            print(f"🗑️  使用{pkg_manager}卸载包: {package_name}")
            return subprocess.run(cmd).returncode
        except Exception as e:
            print(f"❌ 卸载包失败: {e}")
            return 1
        
    def ensure_venv_activated(self) -> bool:
        """
        确保虚拟环境已激活
        
        Returns:
            bool: 是否在虚拟环境中
        """
        # 改进的虚拟环境检测
        # 检查Python执行文件路径是否在虚拟环境目录中
        python_executable = Path(sys.executable)
        
        # 检查是否在虚拟环境目录中
        if self.venv_dir.exists() and python_executable.is_relative_to(self.venv_dir):
            return True
        
        # 检查传统的虚拟环境标志
        if (hasattr(sys, 'real_prefix') or 
            (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)):
            return True
        
        # 检查VIRTUAL_ENV环境变量
        if os.environ.get('VIRTUAL_ENV'):
            return True
        
        # 检查是否存在虚拟环境目录
        if self.venv_dir.exists():
            # 提供正确的激活命令
            if os.name == 'nt':  # Windows
                activate_cmd = ".venv\\Scripts\\activate"
                print("⚠️  检测到虚拟环境但未激活，请手动激活:")
                print(f"    {activate_cmd}")
                print("或者使用: .\\.venv\\Scripts\\activate")
            else:  # Unix/Linux/Mac
                activate_cmd = "source .venv/bin/activate"
                print("⚠️  检测到虚拟环境但未激活，请手动激活:")
                print(f"    {activate_cmd}")
            
            return False
        
        print("❌ 未检测到虚拟环境，请先创建并激活虚拟环境")
        print("使用 uv: uv venv .venv")
        print("使用 venv: python -m venv .venv")
        return False
    
    def run_project(self, reload: bool = False) -> int:
        """
        运行项目
        
        Args:
            reload: 是否启用热重载
            
        Returns:
            int: 退出代码
        """
        if not self.ensure_venv_activated():
            return 1
        
        # 获取虚拟环境中的Python解释器路径
        if os.name == 'nt':  # Windows
            python_executable = self.venv_dir / "Scripts" / "python.exe"
        else:  # Unix/Linux/Mac
            python_executable = self.venv_dir / "bin" / "python"
        
        if reload:
            print("🚀 启动项目（热重载模式）...")
            # 使用uvicorn运行
            if self.check_uv_available():
                cmd = ["uv", "run", "uvicorn", "main:create_app", "--reload", "--host", "0.0.0.0", "--port", "8000"]
            else:
                cmd = [str(python_executable), "-m", "uvicorn", "main:create_app", "--reload", "--host", "0.0.0.0", "--port", "8000"]
        else:
            print("🚀 启动项目...")
            # 直接运行main.py
            cmd = [str(python_executable), "main.py"]
        
        try:
            return subprocess.run(cmd).returncode
        except KeyboardInterrupt:
            print("\n🛑 服务已停止")
            return 0
        except Exception as e:
            print(f"❌ 启动失败: {e}")
            return 1
    
    def download_plugin(self, repo_name: str) -> int:
        """
        下载插件
        
        Args:
            repo_name: GitHub仓库名称
            
        Returns:
            int: 退出代码
        """
        if not self.ensure_venv_activated():
            return 1
        
        # 使用现有的插件下载工具
        try:
            cmd = [sys.executable, "plugin_downloader.py", "download", repo_name]
            return subprocess.run(cmd).returncode
        except Exception as e:
            print(f"❌ 下载插件失败: {e}")
            return 1
    
    def list_plugins(self) -> int:
        """
        列出已安装的插件
        
        Returns:
            int: 退出代码
        """
        if not self.ensure_venv_activated():
            return 1
        
        try:
            cmd = [sys.executable, "plugin_downloader.py", "list"]
            return subprocess.run(cmd).returncode
        except Exception as e:
            print(f"❌ 列出插件失败: {e}")
            return 1
    
    def remove_plugin(self, plugin_name: str) -> int:
        """
        删除插件
        
        Args:
            plugin_name: 插件名称
            
        Returns:
            int: 退出代码
        """
        if not self.ensure_venv_activated():
            return 1
        
        plugin_dir = self.plugins_dir / plugin_name
        
        if not plugin_dir.exists():
            print(f"❌ 插件 '{plugin_name}' 不存在")
            return 1
        
        if not plugin_name.startswith("yoapi-plugin-"):
            print(f"⚠️  警告: 插件 '{plugin_name}' 不符合命名规范")
        
        try:
            confirm = input(f"确定要删除插件 '{plugin_name}' 吗？(y/N): ").lower().strip()
            if confirm != 'y':
                print("删除操作已取消")
                return 0
            
            shutil.rmtree(plugin_dir)
            print(f"✅ 插件 '{plugin_name}' 已删除")
            return 0
        except Exception as e:
            print(f"❌ 删除插件失败: {e}")
            return 1
    
    def create_plugin(self, plugin_name: str) -> int:
        """
        创建新插件
        
        Args:
            plugin_name: 插件名称（会自动添加yoapi-plugin-前缀）
            
        Returns:
            int: 退出代码
        """
        if not self.ensure_venv_activated():
            return 1
        
        # 确保插件名称符合规范
        if not plugin_name.startswith("yoapi-plugin-"):
            plugin_name = f"yoapi-plugin-{plugin_name}"
        
        plugin_dir = self.plugins_dir / plugin_name
        
        if plugin_dir.exists():
            print(f"❌ 插件 '{plugin_name}' 已存在")
            return 1
        
        try:
            # 创建插件目录
            plugin_dir.mkdir(parents=True, exist_ok=True)
            
            # 创建 __init__.py
            init_content = '''from fastapi import APIRouter, Depends
from plugins.log import get_log_service

router = APIRouter()

@router.get("/")
async def root():
    """示例端点"""
    logger = get_log_service().get_logger(__name__)
    logger.info("端点被调用")
    return {"message": "Hello from {plugin_name}"}

def register(app, **dependencies):
    """插件注册函数"""
    logger = get_log_service().get_logger(__name__)
    app.include_router(router, prefix="/{endpoint_prefix}")
    logger.info("{plugin_name} 插件已成功注册")
'''.replace("{plugin_name}", plugin_name).replace("{endpoint_prefix}", plugin_name.replace("yoapi-plugin-", ""))
            
            (plugin_dir / "__init__.py").write_text(init_content, encoding='utf-8')
            
            # 创建 requirements.txt
            requirements_content = '''# {plugin_name} 依赖
# 示例依赖，请根据实际需要修改
fastapi>=0.100.0
'''
            (plugin_dir / "requirements.txt").write_text(requirements_content.replace("{plugin_name}", plugin_name), encoding='utf-8')
            
            # 创建 README.md
            readme_content = '''# {plugin_name}

WaveYo-API 插件

## 功能描述

这里描述插件的主要功能

## 安装

插件会自动被 WaveYo-API 发现和加载

## 配置

可选的环境变量配置说明

## API端点

- `GET /{endpoint_prefix}/` - 示例端点

## 开发说明

这里添加开发相关的说明
'''
            (plugin_dir / "README.md").write_text(readme_content.replace("{plugin_name}", plugin_name).replace("{endpoint_prefix}", plugin_name.replace("yoapi-plugin-", "")), encoding='utf-8')
            
            print(f"✅ 插件 '{plugin_name}' 创建成功")
            print(f"📍 位置: {plugin_dir}")
            print("📁 包含文件:")
            print("   - __init__.py (主程序)")
            print("   - requirements.txt (依赖)")
            print("   - README.md (说明文档)")
            
            return 0
            
        except Exception as e:
            print(f"❌ 创建插件失败: {e}")
            # 清理创建的文件
            if plugin_dir.exists():
                shutil.rmtree(plugin_dir)
            return 1


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="WaveYo-API CLI 工具")
    subparsers = parser.add_subparsers(dest='command', help='命令')
    
    # run 命令
    run_parser = subparsers.add_parser('run', help='运行项目')
    run_parser.add_argument('--reload', action='store_true', help='启用热重载')
    
    # venv 命令组
    venv_parser = subparsers.add_parser('venv', help='虚拟环境管理')
    venv_subparsers = venv_parser.add_subparsers(dest='venv_command', help='虚拟环境子命令')
    
    # venv create
    venv_subparsers.add_parser('create', help='创建虚拟环境')
    
    # package 命令组
    package_parser = subparsers.add_parser('package', help='包管理')
    package_subparsers = package_parser.add_subparsers(dest='package_command', help='包子命令')
    
    # package install
    install_parser = package_subparsers.add_parser('install', help='安装包')
    install_parser.add_argument('package_name', help='包名称')
    
    # package uninstall
    uninstall_parser = package_subparsers.add_parser('uninstall', help='卸载包')
    uninstall_parser.add_argument('package_name', help='包名称')
    
    # plugin 命令组
    plugin_parser = subparsers.add_parser('plugin', help='插件管理')
    plugin_subparsers = plugin_parser.add_subparsers(dest='plugin_command', help='插件子命令')
    
    # plugin download
    download_parser = plugin_subparsers.add_parser('download', help='下载插件')
    download_parser.add_argument('repo_name', help='GitHub仓库名称，格式: owner/repo-name')
    
    # plugin list
    plugin_subparsers.add_parser('list', help='列出插件')
    
    # plugin remove
    remove_parser = plugin_subparsers.add_parser('remove', help='删除插件')
    remove_parser.add_argument('plugin_name', help='插件名称')
    
    # plugin new
    new_parser = plugin_subparsers.add_parser('new', help='创建新插件')
    new_parser.add_argument('plugin_name', help='插件名称（会自动添加yoapi-plugin-前缀）')
    
    args = parser.parse_args()
    
    cli = YoAPICLI()
    
    if args.command == 'run':
        return cli.run_project(args.reload)
    elif args.command == 'venv':
        if args.venv_command == 'create':
            return cli.create_venv()
        else:
            venv_parser.print_help()
            return 1
    elif args.command == 'package':
        if args.package_command == 'install':
            return cli.install_package(args.package_name)
        elif args.package_command == 'uninstall':
            return cli.uninstall_package(args.package_name)
        else:
            package_parser.print_help()
            return 1
    elif args.command == 'plugin':
        if args.plugin_command == 'download':
            return cli.download_plugin(args.repo_name)
        elif args.plugin_command == 'list':
            return cli.list_plugins()
        elif args.plugin_command == 'remove':
            return cli.remove_plugin(args.plugin_name)
        elif args.plugin_command == 'new':
            return cli.create_plugin(args.plugin_name)
        else:
            plugin_parser.print_help()
            return 1
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
