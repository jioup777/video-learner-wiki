"""
工具函数和装饰器
"""

import time
import functools
from typing import Callable, Type, Tuple, Optional
from .exceptions import VideoLearnerError


def retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable] = None
):
    """
    重试装饰器
    
    Args:
        max_attempts: 最大重试次数
        delay: 初始延迟时间（秒）
        backoff: 退避倍数（每次重试延迟时间乘以该值）
        exceptions: 需要重试的异常类型
        on_retry: 重试时的回调函数
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            current_delay = delay
            last_exception = None
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == max_attempts:
                        break
                    
                    if on_retry:
                        on_retry(attempt, max_attempts, e)
                    
                    print(f"[WARN] {func.__name__} 失败 (尝试 {attempt}/{max_attempts}): {e}")
                    time.sleep(current_delay)
                    current_delay *= backoff
            
            raise last_exception
        
        return wrapper
    return decorator


def format_error(error: Exception) -> str:
    """
    格式化异常信息
    
    Args:
        error: 异常对象
        
    Returns:
        格式化后的错误信息
    """
    error_type = type(error).__name__
    error_msg = str(error)
    
    if isinstance(error, VideoLearnerError):
        return f"[{error_type}] {error_msg}"
    else:
        return f"[ERROR] {error_type}: {error_msg}"


def sanitize_filename(filename: str) -> str:
    """
    清理文件名，移除非法字符
    
    Args:
        filename: 原始文件名
        
    Returns:
        清理后的文件名
    """
    illegal_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
    sanitized = filename
    
    for char in illegal_chars:
        sanitized = sanitized.replace(char, '_')
    
    sanitized = sanitized.strip()
    
    # 限制文件名长度
    if len(sanitized) > 200:
        sanitized = sanitized[:200]
    
    return sanitized or 'unnamed'


def safe_int(value, default: int = 0) -> int:
    """
    安全地转换为整数
    
    Args:
        value: 要转换的值
        default: 转换失败时的默认值
        
    Returns:
        整数值
    """
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def format_duration(seconds: float) -> str:
    """
    格式化时间长度
    
    Args:
        seconds: 秒数
        
    Returns:
        格式化后的时间字符串 (如: 1m30s)
    """
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    
    if minutes > 0:
        return f"{minutes}m{secs}s"
    else:
        return f"{secs}s"
