#!/usr/bin/env python3
"""测试dashscope导入"""

try:
    from http import HTTPStatus
    from dashscope.audio.asr import Transcription
    import dashscope
    import os

    print("✅ 所有导入成功!")
    print(f"dashscope version: {dashscope.__version__ if hasattr(dashscope, '__version__') else 'unknown'}")
    print(f"Transcription类: {Transcription}")
    print(f"HTTPStatus: {HTTPStatus.OK}")

except Exception as e:
    print(f"❌ 导入失败: {e}")
    import traceback
    traceback.print_exc()
