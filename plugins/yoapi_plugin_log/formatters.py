import logging
import datetime
import traceback


class CustomFormatter(logging.Formatter):
    """自定义日志格式化器，按照指定格式输出日志，包含详细的错误堆栈信息"""
    
    def format(self, record):
        # 获取当前时间并格式化为 YY-MM-DD-HH:MM:SS
        current_time = datetime.datetime.now().strftime("%y-%m-%d-%H:%M:%S")
        
        # 构建基础日志消息
        log_message = f"[{record.levelname}][{record.name}]{current_time} || {record.getMessage()}"
        
        # 如果是错误级别，添加详细的堆栈跟踪
        if record.levelno >= logging.ERROR and record.exc_info:
            exc_type, exc_value, exc_traceback = record.exc_info
            if exc_type and exc_value:
                # 获取完整的堆栈跟踪
                stack_trace = traceback.format_exception(exc_type, exc_value, exc_traceback)
                stack_trace_str = ''.join(stack_trace)
                
                # 添加堆栈跟踪到日志消息
                log_message += f"\n详细错误信息:\n{stack_trace_str}"
        
        return log_message
