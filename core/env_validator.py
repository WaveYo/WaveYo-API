import os
import logging
from typing import Dict, Any, Optional, List, Callable
from enum import Enum


class EnvVarType(Enum):
    """环境变量类型枚举"""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    LIST = "list"


class EnvValidator:
    """环境变量验证器，提供环境变量的验证和默认值功能"""
    
    def __init__(self):
        self.validators = {
            EnvVarType.STRING: self._validate_string,
            EnvVarType.INTEGER: self._validate_integer,
            EnvVarType.FLOAT: self._validate_float,
            EnvVarType.BOOLEAN: self._validate_boolean,
            EnvVarType.LIST: self._validate_list,
        }
    
    def validate_env_vars(self, plugin_name: str, env_schema: Dict[str, dict]) -> Dict[str, Any]:
        """
        验证插件的环境变量
        
        Args:
            plugin_name: 插件名称
            env_schema: 环境变量模式定义
            
        Returns:
            验证后的环境变量字典
        """
        validated_vars = {}
        errors = []
        warnings = []
        
        for var_name, var_config in env_schema.items():
            value = os.getenv(var_name)
            
            # 如果变量未设置但有默认值，使用默认值
            if value is None and 'default' in var_config:
                value = var_config['default']
                logging.info(f"插件 {plugin_name}: 环境变量 {var_name} 使用默认值: {value}")
            
            # 检查必需变量
            if var_config.get('required', False) and value is None:
                errors.append(f"必需环境变量 {var_name} 未设置")
                continue
            
            # 如果变量为None，跳过验证
            if value is None:
                continue
            
            # 验证变量类型
            var_type = var_config.get('type', EnvVarType.STRING)
            validator = self.validators.get(var_type, self._validate_string)
            
            try:
                validated_value = validator(value, var_config)
                validated_vars[var_name] = validated_value
            except ValueError as e:
                errors.append(f"环境变量 {var_name} 验证失败: {e}")
        
        # 处理错误和警告
        if errors:
            error_msg = f"插件 {plugin_name} 环境变量验证失败:\n" + "\n".join(errors)
            logging.error(error_msg)
            raise ValueError(error_msg)
        
        if warnings:
            warning_msg = f"插件 {plugin_name} 环境变量警告:\n" + "\n".join(warnings)
            logging.warning(warning_msg)
        
        return validated_vars
    
    def _validate_string(self, value: str, config: dict) -> str:
        """验证字符串类型环境变量"""
        if not isinstance(value, str):
            raise ValueError(f"应为字符串类型，实际为 {type(value).__name__}")
        
        # 检查枚举值
        if 'enum' in config and value not in config['enum']:
            raise ValueError(f"值 '{value}' 不在允许的枚举值中: {config['enum']}")
        
        # 检查最小/最大长度
        min_length = config.get('min_length')
        max_length = config.get('max_length')
        
        if min_length is not None and len(value) < min_length:
            raise ValueError(f"长度不能小于 {min_length} 字符")
        
        if max_length is not None and len(value) > max_length:
            raise ValueError(f"长度不能大于 {max_length} 字符")
        
        return value
    
    def _validate_integer(self, value: str, config: dict) -> int:
        """验证整数类型环境变量"""
        try:
            int_value = int(value)
        except ValueError:
            raise ValueError(f"无法转换为整数: '{value}'")
        
        # 检查最小/最大值
        min_val = config.get('min')
        max_val = config.get('max')
        
        if min_val is not None and int_value < min_val:
            raise ValueError(f"值不能小于 {min_val}")
        
        if max_val is not None and int_value > max_val:
            raise ValueError(f"值不能大于 {max_val}")
        
        return int_value
    
    def _validate_float(self, value: str, config: dict) -> float:
        """验证浮点数类型环境变量"""
        try:
            float_value = float(value)
        except ValueError:
            raise ValueError(f"无法转换为浮点数: '{value}'")
        
        # 检查最小/最大值
        min_val = config.get('min')
        max_val = config.get('max')
        
        if min_val is not None and float_value < min_val:
            raise ValueError(f"值不能小于 {min_val}")
        
        if max_val is not None and float_value > max_val:
            raise ValueError(f"值不能大于 {max_val}")
        
        return float_value
    
    def _validate_boolean(self, value: str, config: dict) -> bool:
        """验证布尔类型环境变量"""
        value_lower = value.lower()
        if value_lower in ('true', '1', 'yes', 'on'):
            return True
        elif value_lower in ('false', '0', 'no', 'off'):
            return False
        else:
            raise ValueError(f"无法转换为布尔值: '{value}'")
    
    def _validate_list(self, value: str, config: dict) -> list:
        """验证列表类型环境变量"""
        separator = config.get('separator', ',')
        items = [item.strip() for item in value.split(separator) if item.strip()]
        
        # 检查最小/最大项目数
        min_items = config.get('min_items')
        max_items = config.get('max_items')
        
        if min_items is not None and len(items) < min_items:
            raise ValueError(f"列表项目数不能少于 {min_items}")
        
        if max_items is not None and len(items) > max_items:
            raise ValueError(f"列表项目数不能多于 {max_items}")
        
        return items
    
    def check_env_conflicts(self, plugin_name: str, env_vars: List[str]) -> List[str]:
        """
        检查环境变量冲突
        
        Args:
            plugin_name: 插件名称
            env_vars: 插件使用的环境变量列表
            
        Returns:
            冲突警告消息列表
        """
        warnings = []
        
        for var_name in env_vars:
            # 检查是否与其他插件的环境变量冲突
            # 这里可以扩展为更复杂的冲突检测逻辑
            existing_value = os.getenv(var_name)
            if existing_value and existing_value != os.getenv(var_name, ''):
                warnings.append(f"环境变量 {var_name} 可能与系统或其他插件冲突")
        
        return warnings


# 全局验证器实例
_env_validator = EnvValidator()


def get_env_validator() -> EnvValidator:
    """获取环境变量验证器实例"""
    return _env_validator


def create_env_schema(plugin_name: str, env_definitions: Dict[str, dict]) -> Dict[str, dict]:
    """
    创建环境变量模式模板
    
    Args:
        plugin_name: 插件名称
        env_definitions: 环境变量定义
        
    Returns:
        环境变量模式字典
    """
    return env_definitions


# 示例环境变量模式
EXAMPLE_ENV_SCHEMA = {
    "DB_URL": {
        "type": EnvVarType.STRING,
        "required": True,
        "description": "数据库连接URL"
    },
    "API_KEY": {
        "type": EnvVarType.STRING,
        "required": False,
        "default": "default-key",
        "description": "API访问密钥"
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
