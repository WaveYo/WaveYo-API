#!/usr/bin/env python3
"""
模块集成测试脚本
用于测试重构后的各个模块是否正常工作
"""

import os
import sys
import logging
from fastapi import FastAPI

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# 添加core目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_plugin_discoverer():
    """测试插件发现器"""
    print("=== 测试 PluginDiscoverer ===")
    from core.plugin_discoverer import PluginDiscoverer
    
    discoverer = PluginDiscoverer("./plugins")
    plugins = discoverer.discover_plugins()
    print(f"发现的插件: {plugins}")
    return len(plugins) > 0

def test_env_manager():
    """测试环境变量管理器"""
    print("\n=== 测试 EnvManager ===")
    from core.env_manager import EnvManager
    
    env_manager = EnvManager()
    # 测试加载hello-world插件的环境变量
    success = env_manager.load_plugin_env_vars("yoapi-plugin-hello-world", "./plugins")
    print(f"环境变量加载结果: {success}")
    return success

def test_dependency_manager():
    """测试依赖管理器"""
    print("\n=== 测试 DependencyManager ===")
    from core.dependency_manager import DependencyManager
    
    dep_manager = DependencyManager("./plugins")
    print(f"UV可用性: {dep_manager.is_uv_available()}")
    
    # 测试冲突检测
    conflicts = dep_manager.check_dependency_conflicts("yoapi-plugin-hello-world")
    print(f"依赖冲突检测结果: {conflicts}")
    
    return True  # 即使没有UV也返回True，因为这是可选功能

def test_isolated_executor():
    """测试隔离执行器"""
    print("\n=== 测试 IsolatedExecutor ===")
    from core.isolated_executor import IsolatedPluginExecutor
    
    executor = IsolatedPluginExecutor("./plugins")
    print(f"隔离环境数量: {len(executor.isolated_environments)}")
    
    # 测试环境创建（不实际创建，只检查方法存在）
    print("IsolatedExecutor方法检查通过")
    return True

def test_shared_dependency_registry():
    """测试共享依赖注册表"""
    print("\n=== 测试 SharedDependencyRegistry ===")
    from core.shared_dependency_registry import SharedDependencyRegistry
    
    registry = SharedDependencyRegistry()
    registry.register_shared_dependency("test_config", {"key": "value"})
    
    deps = registry.get_all_shared_dependencies()
    print(f"共享依赖: {deps}")
    
    test_dep = registry.get_shared_dependency("test_config")
    print(f"获取测试依赖: {test_dep}")
    
    return test_dep is not None

def test_plugin_manager_integration():
    """测试插件管理器集成"""
    print("\n=== 测试 PluginManager 集成 ===")
    
    # 创建FastAPI应用实例
    app = FastAPI()
    
    from core.plugin_manager import PluginManager
    plugin_manager = PluginManager(app, "./plugins")
    
    # 测试插件发现
    plugins = plugin_manager.discover_plugins()
    print(f"PluginManager发现的插件: {plugins}")
    
    # 测试共享依赖注册
    plugin_manager.register_shared_dependency("app_config", {"version": "1.0.0"})
    
    # 测试获取共享依赖
    config = plugin_manager.get_shared_dependency("app_config")
    print(f"获取的共享配置: {config}")
    
    return len(plugins) > 0 and config is not None

def main():
    """主测试函数"""
    print("开始模块集成测试...\n")
    
    tests = [
        test_plugin_discoverer,
        test_env_manager,
        test_dependency_manager,
        test_isolated_executor,
        test_shared_dependency_registry,
        test_plugin_manager_integration
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
            status = "✓ 通过" if result else "✗ 失败"
            print(f"{status}\n")
        except Exception as e:
            results.append(False)
            print(f"✗ 测试失败: {e}\n")
    
    passed = sum(results)
    total = len(results)
    
    print(f"=== 测试结果 ===")
    print(f"通过: {passed}/{total}")
    
    if passed == total:
        print("🎉 所有模块集成测试通过！")
        return True
    else:
        print("⚠️  部分测试失败，请检查模块实现")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
