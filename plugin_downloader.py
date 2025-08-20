#!/usr/bin/env python3
"""
WaveYo-API 插件下载工具
用于从GitHub自动下载并安装插件
"""

import argparse
import subprocess
import os
import sys
import time
import shutil
from typing import Optional, Tuple


class PluginDownloader:
    """插件下载器类"""
    
    def __init__(self, plugins_dir: str = "./plugins"):
        """
        初始化插件下载器
        
        Args:
            plugins_dir: 插件目录路径
        """
        self.plugins_dir = plugins_dir
        # 确保插件目录存在
        os.makedirs(plugins_dir, exist_ok=True)
    
    def parse_repo_name(self, repo_name: str) -> Tuple[str, str]:
        """
        解析GitHub仓库名称
        
        Args:
            repo_name: GitHub仓库名称，格式为 owner/repo 或 owner/repo-name
            
        Returns:
            (owner, repo_name) 元组
            
        Raises:
            ValueError: 如果仓库名称格式不正确
        """
        if '/' not in repo_name:
            raise ValueError(f"无效的GitHub仓库名称格式: {repo_name}。请使用 owner/repo-name 格式")
        
        parts = repo_name.split('/')
        if len(parts) != 2:
            raise ValueError(f"无效的GitHub仓库名称格式: {repo_name}。请使用 owner/repo-name 格式")
        
        return parts[0], parts[1]
    
    def build_git_url(self, owner: str, repo: str) -> str:
        """
        构建Git URL
        
        Args:
            owner: 仓库所有者
            repo: 仓库名称
            
        Returns:
            Git URL
        """
        return f"https://github.com/{owner}/{repo}.git"
    
    def get_target_dir(self, repo_name: str) -> str:
        """
        获取目标目录路径
        
        Args:
            repo_name: 仓库名称
            
        Returns:
            目标目录路径
        """
        return os.path.join(self.plugins_dir, repo_name.split('/')[-1])
    
    def download_plugin(self, repo_name: str, max_retries: int = 3) -> bool:
        """
        下载插件
        
        Args:
            repo_name: GitHub仓库名称
            max_retries: 最大重试次数
            
        Returns:
            是否下载成功
        """
        try:
            # 解析仓库名称
            owner, repo = self.parse_repo_name(repo_name)
            
            # 构建Git URL
            git_url = self.build_git_url(owner, repo)
            
            # 获取目标目录
            target_dir = self.get_target_dir(repo_name)
            
            print(f"开始下载插件: {repo_name}")
            print(f"Git URL: {git_url}")
            print(f"目标目录: {target_dir}")
            
            # 检查目标目录是否已存在
            if os.path.exists(target_dir):
                print(f"警告: 目标目录已存在: {target_dir}")
                response = input("是否覆盖？(y/N): ").lower().strip()
                if response != 'y':
                    print("下载取消")
                    return False
                # 删除现有目录
                shutil.rmtree(target_dir)
            
            # 尝试下载，支持重试
            for attempt in range(max_retries):
                try:
                    print(f"下载尝试 {attempt + 1}/{max_retries}...")
                    
                    # 执行git clone命令
                    result = subprocess.run(
                        ["git", "clone", git_url, target_dir],
                        capture_output=True,
                        text=True,
                        timeout=300  # 5分钟超时
                    )
                    
                    if result.returncode == 0:
                        print(f"✅ 插件下载成功: {repo_name}")
                        print(f"插件已保存到: {target_dir}")
                        
                        # 检查下载的插件是否符合命名规范
                        plugin_dir_name = os.path.basename(target_dir)
                        if not plugin_dir_name.startswith("yoapi-plugin-"):
                            print(f"⚠️  警告: 下载的插件 '{plugin_dir_name}' 不符合 yoapi-plugin-xxx 命名规范")
                            print("建议重命名插件目录以符合规范")
                        
                        return True
                    else:
                        print(f"❌ 下载失败 (尝试 {attempt + 1}): {result.stderr}")
                        
                except subprocess.TimeoutExpired:
                    print(f"❌ 下载超时 (尝试 {attempt + 1})")
                except Exception as e:
                    print(f"❌ 下载过程中发生错误 (尝试 {attempt + 1}): {e}")
                
                # 如果不是最后一次尝试，等待一段时间后重试
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # 指数退避
                    print(f"等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)
            
            print(f"❌ ERROR: 经过 {max_retries} 次尝试后仍然下载失败")
            return False
            
        except ValueError as e:
            print(f"❌ 参数错误: {e}")
            return False
        except Exception as e:
            print(f"❌ 下载过程中发生未知错误: {e}")
            return False
    
    def list_available_plugins(self) -> None:
        """
        列出已安装的插件
        """
        if not os.path.exists(self.plugins_dir):
            print("插件目录不存在")
            return
        
        plugins = []
        for item in os.listdir(self.plugins_dir):
            item_path = os.path.join(self.plugins_dir, item)
            if os.path.isdir(item_path) and item.startswith("yoapi-plugin-"):
                plugins.append(item)
        
        if plugins:
            print("已安装的插件:")
            for plugin in sorted(plugins):
                print(f"  - {plugin}")
        else:
            print("没有找到已安装的插件")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="WaveYo-API 插件下载工具")
    subparsers = parser.add_subparsers(dest='command', help='命令')
    
    # download 命令
    download_parser = subparsers.add_parser('download', help='下载插件')
    download_parser.add_argument('repo_name', help='GitHub仓库名称，格式: owner/repo-name')
    download_parser.add_argument('--retries', type=int, default=3, help='最大重试次数 (默认: 3)')
    download_parser.add_argument('--plugins-dir', default='./plugins', help='插件目录路径 (默认: ./plugins)')
    
    # list 命令
    list_parser = subparsers.add_parser('list', help='列出已安装的插件')
    list_parser.add_argument('--plugins-dir', default='./plugins', help='插件目录路径 (默认: ./plugins)')
    
    args = parser.parse_args()
    
    downloader = PluginDownloader(args.plugins_dir if hasattr(args, 'plugins_dir') else './plugins')
    
    if args.command == 'download':
        success = downloader.download_plugin(args.repo_name, args.retries)
        sys.exit(0 if success else 1)
    elif args.command == 'list':
        downloader.list_available_plugins()
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
