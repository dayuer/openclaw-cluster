#!/usr/bin/env python3
from __future__ import annotations
"""
飞书自动化模块
提供模板系统和批量文档操作
"""

import json
import os
import re
from typing import Any
from datetime import datetime
from pathlib import Path


class FeishuAuto:
    """飞书自动化操作类"""
    
    TEMPLATE_DIR = Path(__file__).parent.parent / "templates"
    
    def __init__(self, api, config: Dict[str, Any]):
        """初始化自动化模块"""
        self.api = api
        self.config = config
        # 允许 config 覆盖 template 目录
        custom_dir = config.get("defaults", {}).get("template_dir")
        if custom_dir:
            self.TEMPLATE_DIR = Path(custom_dir)
    
    def batch_create_documents(self, template_name: str, data_list: List[Dict[str, Any]],
                                folder_token: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        批量创建文档
        
        Args:
            template_name: 模板名称（不含扩展名）
            data_list: 数据列表，每个元素生成一份文档
            folder_token: 目标文件夹token（可选）
            
        Returns:
            创建结果列表
        """
        print(f"🚀 批量创建文档 — 模板: {template_name}, 共 {len(data_list)} 份")
        
        # 加载模板
        template_content = self._load_template(template_name)
        if template_content is None:
            print(f"❌ 模板 '{template_name}' 不存在")
            return []
        
        results = []
        for idx, data in enumerate(data_list, 1):
            print(f"  [{idx}/{len(data_list)}] 生成文档...")
            
            try:
                # 渲染模板
                rendered = self._render_template(template_content, data)
                
                # 提取标题（第一行 # 标题）
                title = self._extract_title(rendered, data, idx)
                
                # 通过 API 创建文档
                from feishu_doc import FeishuDoc
                doc = FeishuDoc(self.api)
                doc_info = doc.create_document(title, rendered, folder_token)
                
                results.append({
                    "success": doc_info is not None,
                    "index": idx,
                    "title": title,
                    "doc_info": doc_info,
                })
            except Exception as e:
                print(f"  ❌ 第 {idx} 份失败: {e}")
                results.append({
                    "success": False,
                    "index": idx,
                    "title": f"文档_{idx}",
                    "error": str(e),
                })
        
        success_count = sum(1 for r in results if r["success"])
        print(f"✅ 批量创建完成: {success_count}/{len(data_list)} 成功")
        return results
    
    # ── Template helpers ──
    
    def _load_template(self, template_name: str) -> Optional[str]:
        """加载模板文件"""
        # 尝试多种扩展名
        for ext in [".md", ".txt", ""]:
            path = self.TEMPLATE_DIR / f"{template_name}{ext}"
            if path.is_file():
                with open(path, "r", encoding="utf-8") as f:
                    return f.read()
        return None
    
    def _render_template(self, template: str, data: Dict[str, Any]) -> str:
        """
        渲染模板 — 替换 {{variable}} 占位符
        
        支持:
            {{date}}       — 当前日期 YYYY-MM-DD
            {{time}}       — 当前时间 HH:MM:SS
            {{datetime}}   — 当前日期时间
            {{data.key}}   — data 字典中的值
            {{data.a.b}}   — 嵌套键
        """
        now = datetime.now()
        
        def _resolve(match):
            key = match.group(1).strip()
            
            # 内置变量
            if key == "date":
                return now.strftime("%Y-%m-%d")
            if key == "time":
                return now.strftime("%H:%M:%S")
            if key == "datetime":
                return now.strftime("%Y-%m-%d %H:%M:%S")
            
            # data.xxx 嵌套访问
            if key.startswith("data."):
                parts = key.split(".")[1:]
                value = data
                for part in parts:
                    if isinstance(value, dict):
                        value = value.get(part, "")
                    else:
                        return ""
                return str(value) if value != "" else ""
            
            # 直接顶层 key
            if key in data:
                return str(data[key])
            
            return match.group(0)  # 未匹配则保留原样
        
        return re.sub(r"\{\{(.+?)\}\}", _resolve, template)
    
    def _extract_title(self, rendered: str, data: Dict[str, Any], index: int) -> str:
        """从渲染后的内容中提取标题"""
        # 尝试从第一行 # 标题 提取
        first_line = rendered.split("\n", 1)[0].strip()
        match = re.match(r"^#\s+(.+)$", first_line)
        if match:
            return match.group(1).strip()
        
        # 尝试从 data 的 title 字段
        if "title" in data:
            return str(data["title"])
        
        return f"文档_{index}"
    
    def list_templates(self) -> List[str]:
        """列出可用模板"""
        if not self.TEMPLATE_DIR.is_dir():
            return []
        
        templates = []
        for f in sorted(self.TEMPLATE_DIR.iterdir()):
            if f.is_file() and f.suffix in (".md", ".txt"):
                templates.append(f.stem)
        return templates


# 测试代码
if __name__ == "__main__":
    print("🤖 飞书自动化模块测试")
    
    class MockAPI:
        def post(self, endpoint, data):
            return {"node_token": "test_doc_123"}
        
        def get(self, endpoint):
            return {}
    
    api = MockAPI()
    auto = FeishuAuto(api, {})
    
    # 测试模板渲染
    template = "# {{date}} 报告\n\n用户: {{data.user}}\n数据: {{data.count}}"
    rendered = auto._render_template(template, {"user": "张三", "count": 42})
    print(f"渲染结果:\n{rendered}")
    
    # 测试标题提取
    title = auto._extract_title(rendered, {}, 1)
    print(f"提取标题: {title}")
    
    # 测试模板列表
    templates = auto.list_templates()
    print(f"可用模板: {templates}")
    
    print("✅ 自动化模块测试完成")
