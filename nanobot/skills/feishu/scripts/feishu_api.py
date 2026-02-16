#!/usr/bin/env python3
from __future__ import annotations
"""
飞书API封装层
提供飞书开放平台API的基础封装和认证管理
"""

import requests
import time
import json
import os
from typing import Any
from datetime import datetime, timedelta


class FeishuAPI:
    """飞书API客户端"""
    
    BASE_URL = "https://open.feishu.cn/open-apis"
    
    def __init__(self, config: Dict[str, Any]):
        """初始化飞书API客户端"""
        self.config = config
        self.app_id = config['feishu']['app_id']
        self.app_secret = config['feishu']['app_secret']
        self.tenant_access_token = None
        self.token_expires_at = None
        
        # 请求配置
        self.timeout = config.get('timeout', 30)
        self.max_retries = config.get('max_retries', 3)
        self.retry_delay = config.get('retry_delay', 1)
        
        # 调试模式
        self.debug = config.get('debug', False)
    
    def _log(self, message: str, level: str = "INFO"):
        """日志记录"""
        if self.debug:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{timestamp}] [{level}] {message}")
    
    def _ensure_token(self) -> bool:
        """确保有有效的tenant_access_token"""
        if self.tenant_access_token and self.token_expires_at:
            # 检查token是否即将过期（提前5分钟刷新）
            if datetime.now() < self.token_expires_at - timedelta(minutes=5):
                return True
        
        # 获取新token
        return self._refresh_token()
    
    def _refresh_token(self) -> bool:
        """刷新tenant_access_token"""
        url = f"{self.BASE_URL}/auth/v3/tenant_access_token/internal"
        data = {
            "app_id": self.app_id,
            "app_secret": self.app_secret
        }
        
        try:
            response = requests.post(url, json=data, timeout=self.timeout)
            response.raise_for_status()
            result = response.json()
            
            if result.get('code') == 0:
                self.tenant_access_token = result['tenant_access_token']
                # token有效期通常是2小时，这里设置为1小时50分钟以提前刷新
                self.token_expires_at = datetime.now() + timedelta(minutes=110)
                self._log(f"Token刷新成功，有效期至: {self.token_expires_at}")
                return True
            else:
                self._log(f"Token刷新失败: {result.get('msg', '未知错误')}", "ERROR")
                return False
                
        except requests.exceptions.RequestException as e:
            self._log(f"Token刷新请求失败: {e}", "ERROR")
            return False
    
    def get_tenant_access_token(self) -> Optional[str]:
        """获取tenant_access_token"""
        if self._ensure_token():
            return self.tenant_access_token
        return None
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Optional[Dict[str, Any]]:
        """发送API请求"""
        if not self._ensure_token():
            self._log("无法获取有效的token", "ERROR")
            return None
        
        url = f"{self.BASE_URL}{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.tenant_access_token}",
            "Content-Type": "application/json; charset=utf-8"
        }
        
        # 合并headers
        if 'headers' in kwargs:
            headers.update(kwargs.pop('headers'))
        
        # 重试逻辑
        for attempt in range(self.max_retries):
            try:
                self._log(f"请求 {method} {url} (尝试 {attempt + 1}/{self.max_retries})")
                
                response = requests.request(
                    method=method,
                    url=url,
                    headers=headers,
                    timeout=self.timeout,
                    **kwargs
                )
                
                # 记录响应状态
                self._log(f"响应状态: {response.status_code}")
                
                # 处理响应
                if response.status_code == 200:
                    result = response.json()
                    
                    # 检查飞书API错误码
                    if result.get('code') == 0:
                        return result.get('data')
                    else:
                        self._log(f"API错误: {result.get('msg', '未知错误')} (code: {result.get('code')})", "ERROR")
                        
                        # token过期，尝试刷新
                        if result.get('code') == 99991663:  # token过期
                            self._log("Token过期，尝试刷新...")
                            self.tenant_access_token = None
                            if not self._ensure_token():
                                return None
                            continue
                        
                        return None
                else:
                    self._log(f"HTTP错误: {response.status_code} - {response.text}", "ERROR")
                    
                    # 429 Too Many Requests，等待后重试
                    if response.status_code == 429:
                        retry_after = int(response.headers.get('Retry-After', 5))
                        self._log(f"速率限制，等待 {retry_after} 秒后重试")
                        time.sleep(retry_after)
                        continue
                    
                    return None
                    
            except requests.exceptions.Timeout:
                self._log(f"请求超时 (尝试 {attempt + 1}/{self.max_retries})", "WARNING")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (attempt + 1))
                continue
                
            except requests.exceptions.RequestException as e:
                self._log(f"请求异常: {e} (尝试 {attempt + 1}/{self.max_retries})", "ERROR")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (attempt + 1))
                continue
        
        self._log(f"所有 {self.max_retries} 次尝试都失败了", "ERROR")
        return None
    
    def get(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict[str, Any]]:
        """发送GET请求"""
        return self._make_request('GET', endpoint, params=params)
    
    def post(self, endpoint: str, data: Optional[Dict] = None) -> Optional[Dict[str, Any]]:
        """发送POST请求"""
        return self._make_request('POST', endpoint, json=data)
    
    def put(self, endpoint: str, data: Optional[Dict] = None) -> Optional[Dict[str, Any]]:
        """发送PUT请求"""
        return self._make_request('PUT', endpoint, json=data)
    
    def delete(self, endpoint: str) -> Optional[Dict[str, Any]]:
        """发送DELETE请求"""
        return self._make_request('DELETE', endpoint)
    
    def upload_file(self, file_path: str, endpoint: str, form_data: Optional[Dict] = None) -> Optional[Dict[str, Any]]:
        """上传文件"""
        if not self._ensure_token():
            self._log("无法获取有效的token", "ERROR")
            return None
        
        url = f"{self.BASE_URL}{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.tenant_access_token}"
        }
        
        try:
            with open(file_path, 'rb') as f:
                files = {'file': (os.path.basename(file_path), f)}
                
                if form_data:
                    # 合并表单数据
                    data = form_data.copy()
                else:
                    data = {}
                
                self._log(f"上传文件: {file_path} -> {url}")
                
                response = requests.post(
                    url,
                    headers=headers,
                    files=files,
                    data=data,
                    timeout=self.timeout * 3  # 文件上传需要更长时间
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get('code') == 0:
                        return result.get('data')
                    else:
                        self._log(f"文件上传API错误: {result.get('msg', '未知错误')}", "ERROR")
                        return None
                else:
                    self._log(f"文件上传HTTP错误: {response.status_code}", "ERROR")
                    return None
                    
        except FileNotFoundError:
            self._log(f"文件不存在: {file_path}", "ERROR")
            return None
        except Exception as e:
            self._log(f"文件上传异常: {e}", "ERROR")
            return None
    
    # 常用API端点封装
    
    def create_document(self, folder_token: Optional[str], title: str, content: str) -> Optional[Dict[str, Any]]:
        """创建文档"""
        endpoint = "/drive/v1/files/create"
        data = {
            "type": "docx",
            "title": title,
            "folder_token": folder_token
        }
        
        result = self.post(endpoint, data)
        if result:
            # 创建成功后写入内容
            document_id = result.get('node_token')
            if document_id:
                return self.update_document_content(document_id, content)
        return None
    
    def update_document_content(self, document_id: str, content: str) -> Optional[Dict[str, Any]]:
        """更新文档内容"""
        # 这里需要实现文档内容的实际写入
        # 飞书文档API比较复杂，需要分块写入
        # 暂时返回文档信息
        return {
            "document_id": document_id,
            "title": "待实现",
            "url": f"https://feishu.cn/docx/{document_id}"
        }
    
    def search_documents(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """搜索文档 (需要 drive:drive 权限)"""
        endpoint = "/suite/docs-api/search/object"
        data = {
            "search_key": query,
            "count": min(limit, 50),
            "offset": 0,
            "owner_ids": [],
            "docs_types": [],
        }
        
        result = self.post(endpoint, data)
        if result:
            return result.get('docs_entities', [])
        return []
    
    def upload_to_drive(self, file_path: str, folder_token: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """上传文件到云空间"""
        endpoint = "/drive/v1/files/upload_all"
        
        form_data = {}
        if folder_token:
            form_data['parent_node'] = folder_token
        
        return self.upload_file(file_path, endpoint, form_data)
    
    def list_folder(self, folder_token: Optional[str] = None) -> List[Dict[str, Any]]:
        """列出文件夹内容"""
        endpoint = "/drive/v1/files"
        params = {"page_size": 200}
        if folder_token:
            params["folder_token"] = folder_token
        
        result = self.get(endpoint, params=params)
        if result:
            return result.get('files', [])
        return []
    
    def create_folder(self, name: str, parent_token: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """创建文件夹"""
        endpoint = "/drive/v1/files/create_folder"
        data = {
            "name": name,
            "folder_token": parent_token or ""
        }
        
        return self.post(endpoint, data)
    
    def get_file_info(self, file_token: str) -> Optional[Dict[str, Any]]:
        """获取文件信息"""
        endpoint = f"/drive/v1/files/{file_token}"
        return self.get(endpoint)
    
    def delete_file(self, file_token: str) -> bool:
        """删除文件"""
        endpoint = f"/drive/v1/files/{file_token}"
        result = self.delete(endpoint)
        return result is not None


# 测试代码
if __name__ == "__main__":
    # 简单测试
    import os
    import sys
    
    # 添加父目录到路径
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    # 测试配置
    test_config = {
        'feishu': {
            'app_id': 'test_app_id',
            'app_secret': 'test_app_secret'
        },
        'debug': True
    }
    
    api = FeishuAPI(test_config)
    print("✅ API客户端初始化成功")
    
    # 测试token获取
    token = api.get_tenant_access_token()
    if token:
        print(f"✅ Token获取成功: {token[:20]}...")
    else:
        print("❌ Token获取失败（预期中，因为使用了测试配置）")