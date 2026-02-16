#!/usr/bin/env python3
from __future__ import annotations
"""
飞书文档操作模块
提供文档创建、编辑、搜索、管理等高级功能
"""

import json
import re
from typing import Any
from datetime import datetime


class FeishuDoc:
    """飞书文档操作类"""
    
    def __init__(self, api):
        """初始化文档操作类"""
        self.api = api
    
    def create_document(self, title: str, content: str, folder_token: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        创建飞书文档
        
        Args:
            title: 文档标题
            content: 文档内容（Markdown格式）
            folder_token: 目标文件夹token（可选）
            
        Returns:
            文档信息字典，包含document_id、title、url等
        """
        print(f"📄 创建文档: {title}")
        
        # 1. 创建文档 — 使用 docx API
        endpoint = "/docx/v1/documents"
        data = {"title": title}
        if folder_token:
            data["folder_token"] = folder_token
        
        result = self.api.post(endpoint, data)
        if not result:
            print("❌ 创建文档失败")
            return None
        
        document = result.get('document', {})
        document_id = document.get('document_id')
        if not document_id:
            print("❌ 获取文档ID失败")
            return None
        
        print(f"✅ 文档创建成功，ID: {document_id}")
        
        # 2. 写入内容
        write_result = self.write_document_content(document_id, content)
        if not write_result:
            print("⚠️  文档创建成功，但写入内容失败")
        
        # 3. 返回文档信息
        doc_info = {
            "document_id": document_id,
            "title": title,
            "url": f"https://feishu.cn/docx/{document_id}",
            "folder_token": folder_token,
            "created_at": datetime.now().isoformat(),
            "content_written": write_result is not None
        }
        
        return doc_info
    
    def write_document_content(self, document_id: str, content: str) -> bool:
        """
        写入文档内容
        
        Args:
            document_id: 文档ID（同时也是 root block_id）
            content: 文档内容（Markdown格式）
            
        Returns:
            是否成功
        """
        print(f"📝 写入文档内容: {document_id}")
        
        # 将Markdown转换为内部块结构
        blocks = self._markdown_to_blocks(content)
        if not blocks:
            print("❌ 内容转换失败")
            return False
        
        # 按顺序处理：普通块批量写入，表格块特殊处理（两阶段创建）
        pending_blocks = []  # 累积的普通飞书块
        success_count = 0
        total_count = 0
        
        for block in blocks:
            if block["type"] == "table":
                # 1) 先 flush 前面累积的普通块
                if pending_blocks:
                    n = self._write_children_batch(document_id, document_id, pending_blocks)
                    success_count += n
                    total_count += len(pending_blocks)
                    pending_blocks = []
                
                # 2) 创建表格 (两阶段)
                table_data = block.get("data", {})
                ok = self._create_table_block(document_id, document_id, table_data)
                total_count += 1
                if ok:
                    success_count += 1
            else:
                # 普通块 → 转换并累积
                fbs = self._blocks_to_feishu_json(block)
                pending_blocks.extend(fbs)
                # 如果累积到 50 个，先 flush
                if len(pending_blocks) >= 50:
                    n = self._write_children_batch(document_id, document_id, pending_blocks)
                    success_count += n
                    total_count += len(pending_blocks)
                    pending_blocks = []
        
        # 3) flush 剩余的普通块
        if pending_blocks:
            n = self._write_children_batch(document_id, document_id, pending_blocks)
            success_count += n
            total_count += len(pending_blocks)
        
        if total_count == 0:
            print("❌ 没有内容可写入")
            return False
        
        success_rate = success_count / total_count
        if success_rate > 0.5:
            print(f"✅ 内容写入完成: {success_count}/{total_count} 个块成功")
            return True
        else:
            print(f"⚠️  内容写入部分失败: {success_count}/{total_count} 个块成功")
            return False
    
    def _write_children_batch(self, document_id: str, parent_block_id: str,
                               feishu_blocks: List[Dict], batch_size: int = 50) -> int:
        """
        批量写入子块
        
        Returns:
            成功写入的块数
        """
        endpoint = f"/docx/v1/documents/{document_id}/blocks/{parent_block_id}/children"
        success = 0
        
        for i in range(0, len(feishu_blocks), batch_size):
            batch = feishu_blocks[i:i + batch_size]
            data = {"children": batch, "index": -1}
            
            result = self.api.post(endpoint, data)
            if result:
                children = result.get('children', [])
                success += len(children) if children else len(batch)
            else:
                print(f"  ❌ 写入 {len(batch)} 个块失败")
        
        return success
    
    def _create_table_block(self, document_id: str, parent_block_id: str,
                             table_data: Dict) -> bool:
        """
        创建飞书表格 (两阶段：先建壳，再填充单元格)
        
        Args:
            document_id: 文档ID
            parent_block_id: 父块ID（通常是文档根ID）
            table_data: {"headers": [...], "rows": [[...], ...]}
        """
        headers = table_data.get("headers", [])
        rows = table_data.get("rows", [])
        
        col_count = len(headers) if headers else (len(rows[0]) if rows else 0)
        row_count = (1 if headers else 0) + len(rows)  # +1 for header row
        
        if col_count == 0 or row_count == 0:
            print("  ⚠️  空表格，跳过")
            return False
        
        print(f"  📊 创建表格: {row_count}行 × {col_count}列")
        
        # 阶段 1: 创建表格壳
        endpoint = f"/docx/v1/documents/{document_id}/blocks/{parent_block_id}/children"
        table_block = {
            "block_type": 31,
            "table": {
                "property": {
                    "row_size": row_count,
                    "column_size": col_count
                }
            }
        }
        
        result = self.api.post(endpoint, {"children": [table_block], "index": -1})
        if not result:
            print("  ❌ 创建表格失败, 回退为文本")
            # 降级为纯文本
            self._write_table_as_text(document_id, parent_block_id, table_data)
            return False
        
        # 从响应中提取 cell block IDs
        # 响应结构: { "children": [{ "block_type": 31, "table": { "cells": ["cellId1", "cellId2", ...] } }] }
        children = result.get('children', [])
        if not children:
            print("  ❌ 表格创建返回为空")
            return False
        
        table_info = children[0]
        cell_ids = table_info.get('table', {}).get('cells', [])
        
        if len(cell_ids) < row_count * col_count:
            print(f"  ⚠️  单元格数量不足: 期望 {row_count * col_count}, 实际 {len(cell_ids)}")
            # 尝试用已有的
        
        # 阶段 2: 填充每个单元格
        # cell_ids 排列顺序: [row0_col0, row0_col1, ..., row1_col0, row1_col1, ...]
        all_rows = []
        if headers:
            all_rows.append(headers)
        all_rows.extend(rows)
        
        cell_endpoint_tmpl = f"/docx/v1/documents/{document_id}/blocks/{{}}/children"
        filled = 0
        
        for row_idx, row in enumerate(all_rows):
            for col_idx, cell_text in enumerate(row):
                cell_index = row_idx * col_count + col_idx
                if cell_index >= len(cell_ids):
                    break
                
                cell_block_id = cell_ids[cell_index]
                cell_content = {
                    "children": [{
                        "block_type": 2,
                        "text": self._make_text_obj(cell_text)
                    }],
                    "index": -1
                }
                
                cell_result = self.api.post(
                    cell_endpoint_tmpl.format(cell_block_id),
                    cell_content
                )
                if cell_result:
                    filled += 1
        
        total_cells = row_count * col_count
        print(f"  ✅ 表格填充完成: {filled}/{total_cells} 个单元格")
        return filled > 0
    
    def _write_table_as_text(self, document_id: str, parent_block_id: str,
                              table_data: Dict):
        """降级方案：表格转为纯文本"""
        headers = table_data.get("headers", [])
        rows = table_data.get("rows", [])
        text_blocks = []
        if headers:
            text_blocks.append({"block_type": 2, "text": self._make_text_obj(" | ".join(headers))})
        for row in rows:
            text_blocks.append({"block_type": 2, "text": self._make_text_obj(" | ".join(row))})
        if text_blocks:
            self._write_children_batch(document_id, parent_block_id, text_blocks)
    
    def _make_text_elements(self, text: str) -> List[Dict]:
        """解析行内格式，返回飞书 text_run 元素列表"""
        elements = []
        
        # 行内格式正则：粗斜体, 粗体, 斜体, 代码, 删除线, 链接
        pattern = re.compile(
            r'(\*{3}(.+?)\*{3})'               # ***粗斜体***
            r'|(\*{2}(.+?)\*{2})'              # **粗体**
            r'|(\*(.+?)\*)'                     # *斜体*
            r'|(`(.+?)`)'                       # `代码`
            r'|(~~(.+?)~~)'                     # ~~删除线~~
            r'|(\[([^\]]+)\]\(([^)]+)\))'       # [文字](链接)
        )
        
        last_end = 0
        for m in pattern.finditer(text):
            # 匹配前的普通文本
            if m.start() > last_end:
                plain = text[last_end:m.start()]
                if plain:
                    elements.append({"text_run": {"content": plain}})
            
            if m.group(2):      # ***粗斜体***
                elements.append({"text_run": {"content": m.group(2), "text_element_style": {"bold": True, "italic": True}}})
            elif m.group(4):    # **粗体**
                elements.append({"text_run": {"content": m.group(4), "text_element_style": {"bold": True}}})
            elif m.group(6):    # *斜体*
                elements.append({"text_run": {"content": m.group(6), "text_element_style": {"italic": True}}})
            elif m.group(8):    # `代码`
                elements.append({"text_run": {"content": m.group(8), "text_element_style": {"inline_code": True}}})
            elif m.group(10):   # ~~删除线~~
                elements.append({"text_run": {"content": m.group(10), "text_element_style": {"strikethrough": True}}})
            elif m.group(12):   # [文字](链接)
                elements.append({"text_run": {"content": m.group(12), "text_element_style": {"link": {"url": m.group(13)}}}})
            
            last_end = m.end()
        
        # 剩余文本
        if last_end < len(text):
            remaining = text[last_end:]
            if remaining:
                elements.append({"text_run": {"content": remaining}})
        
        if not elements:
            elements.append({"text_run": {"content": text}})
        
        return elements
    
    def _make_text_obj(self, text: str) -> Dict:
        """创建飞书 Text 对象"""
        return {"elements": self._make_text_elements(text)}
    
    def _blocks_to_feishu_json(self, block: Dict) -> List[Dict]:
        """
        将内部块结构转换为飞书 API JSON 格式（列表类会展开为多个 block）
        
        飞书 block_type 值:
        2=text, 3=h1, 4=h2, 5=h3, 6=h4, 7=h5, 8=h6,
        12=bullet, 13=ordered, 14=code, 15=quote, 22=divider
        """
        btype = block.get("type")
        data = block.get("data", {})
        
        if btype == "heading":
            level = data.get("level", 1)
            text = data.get("text", "")
            block_type = 2 + level  # h1=3, h2=4, h3=5, ...
            heading_key = f"heading{level}"
            return [{"block_type": block_type, heading_key: self._make_text_obj(text)}]
        
        elif btype == "paragraph":
            text_data = data.get("text", {})
            content = text_data.get("content", "") if isinstance(text_data, dict) else str(text_data)
            return [{"block_type": 2, "text": self._make_text_obj(content)}]
        
        elif btype == "bullet_list":
            # 每个列表项是一个独立的 bullet block
            items = data.get("items", [])
            return [{"block_type": 12, "bullet": self._make_text_obj(item)} for item in items]
        
        elif btype == "ordered_list":
            items = data.get("items", [])
            return [{"block_type": 13, "ordered": self._make_text_obj(item)} for item in items]
        
        elif btype == "code":
            code = data.get("code", "")
            return [{"block_type": 14, "code": self._make_text_obj(code)}]
        
        elif btype == "quote":
            text = data.get("text", "")
            return [{"block_type": 15, "quote": self._make_text_obj(text)}]
        
        elif btype == "divider":
            return [{"block_type": 22, "divider": {}}]
        
        elif btype == "table":
            # 表格转为多行普通文本
            headers = data.get("headers", [])
            rows = data.get("rows", [])
            result = [{"block_type": 2, "text": self._make_text_obj(" | ".join(headers))}]
            for row in rows:
                result.append({"block_type": 2, "text": self._make_text_obj(" | ".join(row))})
            return result
        
        return []
    
    def _markdown_to_blocks(self, markdown: str) -> List[Dict[str, Any]]:
        """
        将Markdown转换为飞书文档块
        
        Args:
            markdown: Markdown格式文本
            
        Returns:
            飞书文档块列表
        """
        blocks = []
        lines = markdown.split('\n')
        
        i = 0
        while i < len(lines):
            line = lines[i].rstrip()
            
            # 空行 — 只跳过，不生成 divider（真正的分割线用 --- 表示）
            if not line:
                i += 1
                continue
            
            # 标题 (#, ##, ###)
            match = re.match(r'^(#{1,6})\s+(.+)$', line)
            if match:
                level = len(match.group(1))
                text = match.group(2)
                
                blocks.append({
                    "type": "heading",
                    "data": {
                        "level": level,
                        "text": text
                    }
                })
                i += 1
                continue
            
            # 分割线 (---, ***, ___)
            if re.match(r'^[-*_]{3,}\s*$', line):
                blocks.append({
                    "type": "divider",
                    "data": {}
                })
                i += 1
                continue
            
            # 无序列表 (-, *, +)
            match = re.match(r'^[-*+]\s+(.+)$', line)
            if match:
                text = match.group(1)
                
                # 收集连续列表项
                list_items = [text]
                j = i + 1
                while j < len(lines):
                    next_match = re.match(r'^[-*+]\s+(.+)$', lines[j])
                    if next_match:
                        list_items.append(next_match.group(1))
                        j += 1
                    else:
                        break
                
                blocks.append({
                    "type": "bullet_list",
                    "data": {
                        "items": list_items
                    }
                })
                i = j
                continue
            
            # 有序列表 (1., 2., 3.)
            # 注意：要区分 "1. 列表项" 和 "6. 风险分析" (章节标题)
            # 只有数字<=3时当作新列表开始，或者是已有列表的连续项
            match = re.match(r'^(\d+)\.\s+(.+)$', line)
            if match:
                num = int(match.group(1))
                text = match.group(2)
                
                # 检查是否像子节号 (如 "6.1 宏观风险")
                is_subsection = re.match(r'^\d+(\.\d+)+\s+', line.strip())
                
                # 只有数字<=3且不像子节号时，才当作有序列表
                if num <= 3 and not is_subsection:
                    list_items = [text]
                    j = i + 1
                    while j < len(lines):
                        next_match = re.match(r'^(\d+)\.\s+(.+)$', lines[j])
                        if next_match:
                            list_items.append(next_match.group(2))
                            j += 1
                        else:
                            break
                    
                    blocks.append({
                        "type": "ordered_list",
                        "data": {
                            "items": list_items
                        }
                    })
                    i = j
                    continue
                # 否则 fall through 到段落处理
            
            # 代码块 (```)
            if line.startswith('```'):
                language = line[3:].strip() or "plaintext"
                
                # 收集代码内容
                code_lines = []
                j = i + 1
                while j < len(lines) and not lines[j].startswith('```'):
                    code_lines.append(lines[j])
                    j += 1
                
                if j < len(lines):  # 找到结束标记
                    blocks.append({
                        "type": "code",
                        "data": {
                            "language": language,
                            "code": '\n'.join(code_lines)
                        }
                    })
                    i = j + 1
                else:
                    # 没有结束标记，当作普通文本
                    blocks.append({
                        "type": "paragraph",
                        "data": {
                            "text": line
                        }
                    })
                    i += 1
                continue
            
            # 引用 (>)
            if line.startswith('> '):
                quote_text = line[2:]
                
                # 收集连续引用
                quote_lines = [quote_text]
                j = i + 1
                while j < len(lines) and lines[j].startswith('> '):
                    quote_lines.append(lines[j][2:])
                    j += 1
                
                blocks.append({
                    "type": "quote",
                    "data": {
                        "text": '\n'.join(quote_lines)
                    }
                })
                i = j
                continue
            
            # 表格（简单实现）
            if '|' in line and not line.startswith('|--'):
                # 尝试解析表格
                cells = [cell.strip() for cell in line.split('|') if cell.strip()]
                if cells:
                    # 检查下一行是否是分隔线
                    if i + 1 < len(lines) and '|' in lines[i + 1] and '--' in lines[i + 1]:
                        # 收集表格行
                        table_rows = [cells]
                        j = i + 2
                        while j < len(lines) and '|' in lines[j] and '--' not in lines[j]:
                            row_cells = [cell.strip() for cell in lines[j].split('|') if cell.strip()]
                            if row_cells:
                                table_rows.append(row_cells)
                            j += 1
                        
                        if len(table_rows) > 1:
                            blocks.append({
                                "type": "table",
                                "data": {
                                    "headers": table_rows[0],
                                    "rows": table_rows[1:]
                                }
                            })
                            i = j
                            continue
            
            # 普通段落
            # 收集连续文本行
            paragraph_lines = [line]
            j = i + 1
            while j < len(lines) and lines[j].strip() and not re.match(r'^[#\-*+>]', lines[j].strip()):
                paragraph_lines.append(lines[j].strip())
                j += 1
            
            text = ' '.join(paragraph_lines)
            
            # 检查是否有内联格式
            formatted_text = self._parse_inline_formatting(text)
            
            blocks.append({
                "type": "paragraph",
                "data": {
                    "text": formatted_text
                }
            })
            i = j
        
        return blocks
    
    def _parse_inline_formatting(self, text: str) -> Dict[str, Any]:
        """
        解析内联格式（粗体、斜体、行内代码、删除线、链接等）
        
        支持:
            ***粗斜体***, **粗体**, *斜体*,
            `行内代码`, ~~删除线~~, [链接文字](url)
        
        Args:
            text: 原始文本
            
        Returns:
            格式化文本字典，包含 segments 列表
        """
        # 正则匹配行内格式 — 按优先级排序
        pattern = re.compile(
            r'(\*{3}(.+?)\*{3})'           # group 1,2: ***粗斜体***
            r'|(\*{2}(.+?)\*{2})'          # group 3,4: **粗体**
            r'|(\*(.+?)\*)'                # group 5,6: *斜体*
            r'|(`(.+?)`)'                  # group 7,8: `行内代码`
            r'|(~~(.+?)~~)'                # group 9,10: ~~删除线~~
            r'|(\[([^\]]+)\]\(([^)]+)\))'  # group 11,12,13: [文字](链接)
        )
        
        segments = []
        last_end = 0
        
        for m in pattern.finditer(text):
            # 匹配前的普通文本
            if m.start() > last_end:
                plain = text[last_end:m.start()]
                if plain:
                    segments.append({"text": plain, "style": "plain"})
            
            if m.group(2):      # ***粗斜体***
                segments.append({"text": m.group(2), "style": "bold_italic"})
            elif m.group(4):    # **粗体**
                segments.append({"text": m.group(4), "style": "bold"})
            elif m.group(6):    # *斜体*
                segments.append({"text": m.group(6), "style": "italic"})
            elif m.group(8):    # `行内代码`
                segments.append({"text": m.group(8), "style": "code"})
            elif m.group(10):   # ~~删除线~~
                segments.append({"text": m.group(10), "style": "strikethrough"})
            elif m.group(12):   # [文字](链接)
                segments.append({"text": m.group(12), "style": "link", "url": m.group(13)})
            
            last_end = m.end()
        
        # 剩余的普通文本
        if last_end < len(text):
            remaining = text[last_end:]
            if remaining:
                segments.append({"text": remaining, "style": "plain"})
        
        # 如果完全没匹配到任何格式，返回原始纯文本
        if not segments:
            return {"content": text, "format": "plain"}
        
        return {"content": text, "format": "rich", "segments": segments}
    
    def search_documents(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        搜索文档
        
        Args:
            query: 搜索关键词
            limit: 结果数量限制
            
        Returns:
            文档列表
        """
        print(f"🔍 搜索文档: {query}")
        
        endpoint = "/suite/docs-api/search/object"
        data = {
            "search_key": query,
            "count": min(limit, 50),
            "offset": 0,
            "owner_ids": [],
            "docs_types": [],
        }
        
        result = self.api.post(endpoint, data)
        if not result:
            print("❌ 搜索失败")
            return []
        
        docs = result.get('docs_entities', [])
        
        # 格式化结果
        formatted_results = []
        for doc in docs:
            formatted_results.append({
                "token": doc.get('docs_token'),
                "title": doc.get('title'),
                "type": doc.get('docs_type'),
                "url": doc.get('url', f"https://feishu.cn/docx/{doc.get('docs_token', '')}"),
                "owner": doc.get('owner_id')
            })
        
        print(f"✅ 找到 {len(formatted_results)} 个文档")
        return formatted_results
    
    def get_document_info(self, document_token: str) -> Optional[Dict[str, Any]]:
        """
        获取文档信息
        
        Args:
            document_token: 文档token
            
        Returns:
            文档信息
        """
        print(f"📋 获取文档信息: {document_token}")
        
        endpoint = f"/drive/v1/files/{document_token}"
        
        result = self.api.get(endpoint)
        if not result:
            print("❌ 获取文档信息失败")
            return None
        
        return {
            "token": result.get('token'),
            "title": result.get('name'),
            "type": result.get('type'),
            "url": result.get('url'),
            "created_time": result.get('created_time'),
            "modified_time": result.get('modified_time'),
            "owner": result.get('owner_id'),
            "size": result.get('size'),
            "parent_token": result.get('parent_token')
        }
    
    def delete_document(self, document_token: str) -> bool:
        """
        删除文档
        
        Args:
            document_token: 文档token
            
        Returns:
            是否成功
        """
        print(f"🗑️  删除文档: {document_token}")
        
        endpoint = f"/drive/v1/files/{document_token}"
        
        result = self.api.delete(endpoint)
        if result:
            print("✅ 文档删除成功")
            return True
        else:
            print("❌ 文档删除失败")
            return False
    
    def share_document(self, document_token: str, permission: str = "view") -> Optional[str]:
        """
        生成文档分享链接
        
        Args:
            document_token: 文档token
            permission: 权限（view/edit）
            
        Returns:
            分享链接
        """
        print(f"🔗 生成分享链接: {document_token}")
        
        endpoint = f"/drive/v1/permissions/{document_token}/public"
        data = {
            "type": permission,
            "external_access": True
        }
        
        result = self.api.post(endpoint, data)
        if not result:
            print("❌ 生成分享链接失败")
            return None
        
        share_url = result.get('url')
        if share_url:
            print(f"✅ 分享链接生成成功: {share_url}")
            return share_url
        else:
            print("❌ 未获取到分享链接")
            return None


# 测试代码
if __name__ == "__main__":
    # 简单测试
    print("📄 飞书文档模块测试")
    
    # 模拟API
    class MockAPI:
        def post(self, endpoint, data):
            print(f"  POST {endpoint}")
            if "search" in endpoint:
                return {"files": [{"token": "test123", "name": "测试文档", "type": "docx"}]}
            return {"node_token": "test_doc_123"}
        
        def get(self, endpoint):
            print(f"  GET {endpoint}")
            return {"token": "test123", "name": "测试文档"}
        
        def delete(self, endpoint):
            print(f"  DELETE {endpoint}")
            return {"success": True}
    
    api = MockAPI()
    doc = FeishuDoc(api)
    
    # 测试搜索
    results = doc.search_documents("测试", 10)
    print(f"搜索结果: {len(results)} 条")
    
    # 测试Markdown转换
    test_md = """# 测试标题

这是一个段落。

- 列表项1
- 列表项2

> 这是一个引用
"""
    blocks = doc._markdown_to_blocks(test_md)
    print(f"转换块数: {len(blocks)}")
    
    print("✅ 文档模块测试完成")