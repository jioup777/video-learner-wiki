"""
Video Learner Downloaders
支持平台: Bilibili, YouTube, Douyin
"""

from .bilibili import BilibiliDownloader
from .youtube import YouTubeDownloader
from .douyin import DouyinDownloader

__all__ = ['BilibiliDownloader', 'YouTubeDownloader', 'DouyinDownloader']
