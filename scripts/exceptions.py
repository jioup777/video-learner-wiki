"""
统一异常类定义
"""

class VideoLearnerError(Exception):
    """视频学习器基础异常类"""
    pass


class PlatformError(VideoLearnerError):
    """平台相关异常"""
    pass


class DownloadError(PlatformError):
    """下载失败异常"""
    pass


class CookiesError(DownloadError):
    """Cookies无效或过期异常"""
    pass


class ASRError(VideoLearnerError):
    """ASR转录异常"""
    pass


class FileSizeError(ASRError):
    """文件过大异常"""
    pass


class TranscriptionError(ASRError):
    """转录失败异常"""
    pass


class NoteGenerationError(VideoLearnerError):
    """笔记生成异常"""
    pass


class UploadError(VideoLearnerError):
    """上传异常"""
    pass


class FeishuAPIError(UploadError):
    """飞书API异常"""
    pass


class ConfigurationError(VideoLearnerError):
    """配置错误异常"""
    pass


class APIKeyError(ConfigurationError):
    """API密钥错误异常"""
    pass
