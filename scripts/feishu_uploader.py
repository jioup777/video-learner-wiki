"""
飞书文档上传模块(Wiki版本)
直接在wiki节点下创建子文档
"""

import os
import json
import requests
from typing import Optional, List, Dict


class FeishuUploader:
    """飞书文档上传器(Wiki版本)"""

    API_BASE = "https://open.feishu.cn/open-apis"

    def __init__(self, app_id: str = None, app_secret: str = None,
                 space_id: str = None, parent_token: str = None):
        """
        初始化飞书上传器

        Args:
            app_id: 飞书应用ID
            app_secret: 飞书应用密钥
            space_id: 飞书知识库空间ID
            parent_token: 父节点Token(wiki节点)
        """
        self.app_id = app_id or os.getenv('FEISHU_APP_ID')
        self.app_secret = app_secret or os.getenv('FEISHU_APP_SECRET')
        self.space_id = space_id or os.getenv('FEISHU_SPACE_ID')
        self.parent_token = parent_token or os.getenv('FEISHU_PARENT_TOKEN')
        self.tenant_token = None

        # 验证配置
        if not self.app_id or not self.app_secret:
            raise ValueError(
                "未配置飞书应用凭证。\n"
                "请设置环境变量: FEISHU_APP_ID 和 FEISHU_APP_SECRET\n"
                "获取方式: 飞书开放平台 (https://open.feishu.cn/app) > 创建自建应用"
            )

        if not self.space_id:
            raise ValueError(
                "未配置飞书空间ID。\n"
                "请设置环境变量: FEISHU_SPACE_ID"
            )

        if not self.parent_token:
            raise ValueError(
                "未配置飞书父节点Token。\n"
                "请设置环境变量: FEISHU_PARENT_TOKEN\n"
                "获取方式: 飞书知识库 > 右键目标文件夹 > 复制Node Token"
            )

        # 获取访问令牌
        self._get_tenant_token()

    def is_configured(self) -> bool:
        """检查是否配置完整"""
        return bool(self.app_id and self.app_secret and
                   self.space_id and self.parent_token and self.tenant_token)

    def _get_tenant_token(self) -> str:
        """获取tenant_access_token"""
        url = f"{self.API_BASE}/auth/v3/tenant_access_token/internal"

        data = {
            "app_id": self.app_id,
            "app_secret": self.app_secret
        }

        headers = {'Content-Type': 'application/json'}

        response = requests.post(url, headers=headers, json=data, timeout=30)

        if response.status_code != 200:
            raise RuntimeError(f"获取tenant_token失败: {response.text}")

        result = response.json()

        if 'tenant_access_token' not in result:
            raise RuntimeError(f"响应中未找到tenant_access_token: {result}")

        self.tenant_token = result['tenant_access_token']
        print("  [飞书] 访问令牌已获取 (应用授权)")
        return self.tenant_token

    def _get_headers(self, use_user_token: bool = False) -> dict:
        """获取认证请求头"""
        return {
            'Content-Type': 'application/json',
            'Authorization': f"Bearer {self.tenant_token}"
        }

    def upload(self, content: str, title: str) -> str:
        """
        上传笔记到飞书(在wiki节点下创建子文档)

        Args:
            content: 笔记内容(Markdown格式)
            title: 文档标题

        Returns:
            飞书wiki链接
        """
        if not self.is_configured():
            raise RuntimeError("飞书未配置完整")

        print(f"  [飞书] 开始上传文档到Wiki: {title}")

        # 1. 创建wiki节点
        node_token, obj_token = self._create_wiki_node(title)
        print(f"  [飞书] Wiki节点已创建: {node_token}")
        print(f"  [飞书] 文档ID: {obj_token}")

        # 2. 写入内容
        self._write_content(obj_token, content)
        print(f"  [飞书] 内容写入完成")

        # 3. 返回wiki链接
        link = f"https://www.feishu.cn/wiki/{node_token}"
        print(f"  [飞书] Wiki链接: {link}")

        return link

    def _create_wiki_node(self, title: str) -> tuple:
        """
        在wiki节点下创建子文档

        Args:
            title: 文档标题

        Returns:
            (node_token, obj_token) 元组
        """
        # 在wiki节点下创建子文档
        url = f"{self.API_BASE}/wiki/v2/spaces/{self.space_id}/nodes"

        data = {
            "space_id": self.space_id,
            "parent_node_token": self.parent_token,
            "obj_type": "docx",
            "node_type": "origin",
            "title": title
        }

        response = requests.post(
            url,
            headers=self._get_headers(),
            json=data,
            timeout=30
        )

        print(f"  [飞书] 创建节点响应: {response.status_code}")

        if response.status_code != 200:
            print(f"  [飞书] 响应内容: {response.text}")
            raise RuntimeError(f"创建wiki节点失败: {response.text}")

        result = response.json()

        if result.get('code') != 0:
            print(f"  [飞书] 错误码: {result.get('code')}, 错误信息: {result.get('msg')}")
            raise RuntimeError(f"创建wiki节点失败: {result.get('msg', '未知错误')}")

        if 'data' not in result or 'node' not in result['data']:
            raise RuntimeError(f"创建wiki节点失败: 响应格式错误 - {result}")

        node = result['data']['node']
        node_token = node['node_token']
        obj_token = node['obj_token']

        return node_token, obj_token

    def _write_content(self, obj_token: str, content: str):
        """
        写入内容到文档（逐块追加）
        
        飞书 block_type 映射:
          1=Page, 2=Text(段落), 3=Heading1, 4=Heading2, 5=Heading3,
          6=Heading4, 7=Heading5, 8=Heading6, 9=Heading7, 10=Heading8, 11=Heading9,
          14=Bullet(无序列表), 15=Ordered(有序列表), 17=Code, 18=Quote, 23=Divider
        """
        blocks = self._markdown_to_blocks(content)
        
        base_url = f"{self.API_BASE}/docx/v1/documents/{obj_token}/blocks/{obj_token}/children"
        
        # 分批写入（每批最多 50 个 block）
        batch_size = 50
        for i in range(0, len(blocks), batch_size):
            batch = blocks[i:i+batch_size]
            response = requests.post(
                base_url,
                headers=self._get_headers(),
                json={"children": batch},
                timeout=60
            )
            if response.status_code != 200:
                result = response.json()
                print(f"  [飞书] 写入块 {i+1}-{i+len(batch)} 失败: {result.get('msg', response.text[:100])}")
            else:
                print(f"  [飞书] 写入块 {i+1}-{i+len(batch)} 成功")
    
    def _markdown_to_blocks(self, markdown: str) -> List[Dict]:
        """
        将Markdown转换为飞书Block格式
        
        支持的块类型：heading1-9, text(段落)
        其他格式（列表、代码、引用等）降级为 text 块（保留前缀符号）
        """
        blocks = []
        lines = markdown.split('\n')
        i = 0
        
        while i < len(lines):
            line = lines[i]
            
            # 跳过空行
            if not line.strip():
                i += 1
                continue
            
            stripped = line.strip()
            
            # HTML 标签 - 跳过
            if stripped.startswith('<details') or stripped.startswith('</details') or stripped.startswith('<summary') or stripped.startswith('</summary'):
                i += 1
                continue
            
            # 标题 (## ~ ######)
            if stripped.startswith('#'):
                heading_match = stripped.lstrip('#')
                level = len(stripped) - len(heading_match)
                heading_text = heading_match.strip()
                if not heading_text:
                    i += 1
                    continue
                block_type = min(2 + level, 11)
                heading_key = f"heading{level}"
                blocks.append({
                    "block_type": block_type,
                    heading_key: {
                        "elements": [{"text_run": {"content": heading_text}}]
                    }
                })
                i += 1
                continue
            
            # 分割线
            if stripped == '---':
                blocks.append({
                    "block_type": 2,
                    "text": {"elements": [{"text_run": {"content": "────────────────"}}]}
                })
                i += 1
                continue
            
            # 代码块 ```
            if stripped.startswith('```'):
                lang = stripped[3:].strip()
                code_lines = []
                i += 1
                while i < len(lines) and not lines[i].strip().startswith('```'):
                    code_lines.append(lines[i])
                    i += 1
                code_text = '\n'.join(code_lines)
                if code_text.strip():
                    blocks.append({
                        "block_type": 2,
                        "text": {"elements": [{"text_run": {"content": f"[代码{lang}] {code_text[:200]}{'...' if len(code_text)>200 else ''}"}}]}
                    })
                i += 1
                continue
            
            # 引用块 >
            if stripped.startswith('> '):
                quote_text = stripped[2:]
                blocks.append({
                    "block_type": 2,
                    "text": {"elements": [{"text_run": {"content": f"💬 {quote_text}"}}]}
                })
                i += 1
                continue
            
            # 无序列表 - 用 text 块 + 前缀
            if stripped.startswith('- ') or stripped.startswith('* '):
                list_text = self._parse_inline_format(stripped[2:].strip())
                blocks.append({
                    "block_type": 2,
                    "text": {"elements": [{"text_run": {"content": f"• {list_text}"}}]}
                })
                i += 1
                continue
            
            # 有序列表
            if stripped and stripped[0].isdigit() and '. ' in stripped[:4]:
                list_text = self._parse_inline_format(stripped.split('. ', 1)[1].strip())
                blocks.append({
                    "block_type": 2,
                    "text": {"elements": [{"text_run": {"content": f"{stripped.split('.')[0]}. {list_text}"}}]}
                })
                i += 1
                continue
            
            # 普通段落 - 合并连续非空行
            para_lines = [stripped]
            i += 1
            while i < len(lines) and lines[i].strip() and not lines[i].strip().startswith('#') and not lines[i].strip().startswith('- ') and not lines[i].strip().startswith('* ') and lines[i].strip() != '---' and not lines[i].strip().startswith('```') and not lines[i].strip().startswith('> ') and not lines[i].strip().startswith('<'):
                para_lines.append(lines[i].strip())
                i += 1
            
            para_text = self._parse_inline_format('\n'.join(para_lines))
            blocks.append({
                "block_type": 2,
                "text": {
                    "elements": [{"text_run": {"content": para_text}}]
                }
            })
        
        return blocks
    
    def _parse_inline_format(self, text: str) -> str:
        """简化内联格式：去除 Markdown 粗体/斜体标记"""
        # 去除 **粗体**
        text = text.replace('**', '')
        # 去除 *斜体*
        text = text.replace('*', '')
        # 去除 `行内代码`
        text = text.replace('`', '')
        return text


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("用法: python feishu_uploader.py <笔记文件> [标题]")
        print("\n环境变量:")
        print("  FEISHU_APP_ID        - 飞书应用ID")
        print("  FEISHU_APP_SECRET    - 飞书应用密钥")
        print("  FEISHU_SPACE_ID      - 飞书空间ID")
        print("  FEISHU_PARENT_TOKEN  - 父节点Token")
        sys.exit(1)

    file_path = sys.argv[1]
    title = sys.argv[2] if len(sys.argv) > 2 else None

    if not os.path.exists(file_path):
        print(f"文件不存在: {file_path}")
        sys.exit(1)

    if not title:
        title = os.path.splitext(os.path.basename(file_path))[0]

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    try:
        uploader = FeishuUploader()
        link = uploader.upload(content, title)
        print(f"\n✅ 上传成功: {link}")
    except Exception as e:
        print(f"\n❌ 上传失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)