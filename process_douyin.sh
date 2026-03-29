#!/bin/bash
# 抖音视频处理脚本（优化版）
# 功能：抖音链接 → 下载 → 转录 → 笔记 → 飞书
set -e

WORKSPACE="/home/ubuntu/.openclaw/workspace-video-learner"
DOUYIN_MCP="${WORKSPACE}/douyin-mcp-server"
OUTPUT_DIR="${WORKSPACE}/output"
TMP_DIR="/tmp"

# 参数检查
if [ -z "$1" ]; then
    echo "用法：$0 <抖音分享链接>"
    exit 1
fi

douyin_url="$1"
video_id=$(date +%Y%m%d_%H%M%S)

echo "🎯 开始处理抖音视频..."
echo "链接：$douyin_url"

# 步骤 1：下载视频（-a download 直接下载，无需单独获取链接）
echo "📥 下载无水印视频..."
uv run --directory "${DOUYIN_MCP}" python douyin-video/scripts/douyin_downloader.py \
    -l "$douyin_url" \
    -a download \
    -o "${TMP_DIR}" \
    --quiet

# 找到下载的视频文件
video_file=$(ls -t ${TMP_DIR}/*.mp4 2>/dev/null | head -1)
if [ -z "$video_file" ]; then
    echo "❌ 下载失败，未找到视频文件"
    exit 1
fi
echo "✅ 视频已下载：$video_file"

# 步骤 2：提取音频
echo "🎵 提取音频..."
audio_file="${TMP_DIR}/douyin_${video_id}.mp3"
ffmpeg -i "$video_file" \
    -vn -acodec libmp3lame -q:a 2 \
    "$audio_file" \
    -y -loglevel quiet

# 步骤 3：Whisper 转录
echo "🎙️ 语音转录..."
source ~/.openclaw/venv/bin/activate
whisper "$audio_file" \
    --language Chinese \
    --model small \
    --output_dir "$TMP_DIR" \
    --output_format txt \
    2>/dev/null

transcript_file="${TMP_DIR}/douyin_${video_id}.txt"
if [ ! -f "$transcript_file" ]; then
    transcript_file="${TMP_DIR}/$(basename "$audio_file" .mp3).txt"
fi

if [ ! -f "$transcript_file" ]; then
    echo "❌ 转录失败，未找到文本文件"
    exit 1
fi
echo "✅ 转录完成：$transcript_file"

# 步骤 4：生成学习笔记
echo "📝 生成学习笔记..."
# TODO: 调用 GLM-4-Flash 生成笔记
# 可以使用现有的 smart_note_generator.py

# 步骤 5：上传飞书
echo "☁️ 上传飞书..."
# TODO: 调用 feishu_wiki 工具上传

# 清理临时文件
echo "🧹 清理临时文件..."
rm -f "$video_file" "$audio_file" "$transcript_file"

echo "✅ 处理完成！"
