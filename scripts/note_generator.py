"""
笔记生成模块（Agent内置版）
不再调用外部GLM API，改为生成prompt文件供Agent大模型使用。

Agent流程：
1. 脚本完成下载+ASR，输出转录文件
2. Agent读取转录文本，直接用当前对话大模型生成笔记
3. Agent上传笔记到飞书Wiki
"""

import os
import sys
from datetime import datetime
from pathlib import Path


# 笔记生成prompt模板，Agent可直接使用
NOTE_PROMPT_TEMPLATE = """你是一位专业的学习笔记整理专家。请根据视频转录文本，整理成结构化的学习笔记。

输出格式要求（Markdown）：
## 核心主题
（一句话概括）

## 核心观点
（3-5条，每条简洁明了）

## 典型案例
（如有，提取具体例子）

## 实践建议
（可执行的建议）

## 核心金句
（3-5句，简短有力）

注意事项：
- 加粗关键内容
- 保持逻辑清晰
- 提取精华，去除废话
- 如内容不适用某部分，可省略该部分
- 不要在笔记中重复转录原文"""


def format_note(transcript: str, video_title: str, video_url: str, generated_notes: str) -> str:
    """
    格式化最终笔记：将Agent生成的笔记内容与转录原文拼接
    
    Args:
        transcript: 转录文本
        video_title: 视频标题
        video_url: 视频URL
        generated_notes: Agent大模型生成的笔记内容
    
    Returns:
        完整笔记（Markdown格式）
    """
    now = datetime.now()
    
    note = f"""# 【视频笔记】{video_title}

> 原始链接：{video_url}
> 🤖 此笔记由 Video Learner 智能生成

---

{generated_notes}

---

## 📝 完整转录内容

{transcript}
"""
    
    return note


def get_prompt() -> str:
    """返回笔记生成prompt，供Agent使用"""
    return NOTE_PROMPT_TEMPLATE


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='笔记格式化工具（配合Agent使用）')
    parser.add_argument('transcript_file', help='转录文本文件')
    parser.add_argument('--title', required=True, help='视频标题')
    parser.add_argument('--url', default='', help='视频URL')
    parser.add_argument('--notes-file', required=True, help='Agent生成的笔记内容文件')
    parser.add_argument('--output', '-o', help='输出文件路径')
    
    args = parser.parse_args()
    
    with open(args.transcript_file, 'r', encoding='utf-8') as f:
        transcript = f.read()
    
    with open(args.notes_file, 'r', encoding='utf-8') as f:
        generated_notes = f.read()
    
    note = format_note(transcript, args.title, args.url, generated_notes)
    
    output_path = args.output or args.transcript_file.replace('.txt', '_note.md')
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(note)
    
    print(f"✅ 笔记已生成: {output_path}")


if __name__ == "__main__":
    main()
