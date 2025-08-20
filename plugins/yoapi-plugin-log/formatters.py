import logging
import datetime


class CustomFormatter(logging.Formatter):
    """自定义日志格式化器，按照指定格式输出日志"""
    
    def format(self, record):
        # 获取当前时间并格式化为 YY-MM-DD-HH:MM:SS
        current_time = datetime.datetime.now().strftime("%y-%m-%d-%H:%M:%S")
        
        # 构建日志消息
        log_message = f"[{record.levelname}][{record.name}]{current_time} || {record.getMessage()}"
        
        return log_message
