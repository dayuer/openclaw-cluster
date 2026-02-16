#!/usr/bin/env python3
from __future__ import annotations
"""
飞书空间管理模块
提供文件夹创建、列举、空间信息等功能
"""

from typing import Any


class FeishuSpace:
    """飞书空间管理类"""
    
    def __init__(self, api):
        """初始化空间管理类"""
        self.api = api
    
    def create_folder(self, name: str, parent_token: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        创建文件夹
        
        Args:
            name: 文件夹名称
            parent_token: 父文件夹token（None则在根目录创建）
            
        Returns:
            文件夹信息字典
        """
        print(f"📁 创建文件夹: {name}")
        
        try:
            result = self.api.create_folder(name, parent_token)
            if result:
                folder_info = {
                    "token": result.get("token"),
                    "name": name,
                    "parent_token": parent_token,
                    "url": result.get("url"),
                }
                print(f"✅ 文件夹创建成功: {folder_info.get('token', 'N/A')}")
                return folder_info
            else:
                print("❌ 文件夹创建失败")
                return None
        except Exception as e:
            print(f"❌ 创建文件夹失败: {e}")
            return None
    
    def list_folders(self, parent_token: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        列出文件夹（仅返回文件夹，过滤掉文件）
        
        Args:
            parent_token: 父文件夹token（None则列出根目录）
            
        Returns:
            文件夹列表
        """
        print("📋 列出文件夹...")
        
        try:
            all_items = self.api.list_folder(parent_token)
            if not all_items:
                print("📭 目录为空")
                return []
            
            # 只保留文件夹类型
            folders = [
                {
                    "token": item.get("token"),
                    "name": item.get("name"),
                    "type": item.get("type"),
                }
                for item in all_items
                if item.get("type") == "folder"
            ]
            
            print(f"✅ 找到 {len(folders)} 个文件夹")
            for i, folder in enumerate(folders, 1):
                print(f"  {i}. 📁 {folder.get('name', '未命名')}")
            
            return folders
        except Exception as e:
            print(f"❌ 列出文件夹失败: {e}")
            return []
    
    def get_space_info(self) -> Optional[Dict[str, Any]]:
        """
        获取云空间使用情况
        
        Returns:
            空间信息字典
        """
        print("📊 获取空间信息...")
        
        try:
            # 列出根目录获取大致信息
            root_items = self.api.list_folder(None)
            
            file_count = 0
            folder_count = 0
            if root_items:
                for item in root_items:
                    if item.get("type") == "folder":
                        folder_count += 1
                    else:
                        file_count += 1
            
            space_info = {
                "root_files": file_count,
                "root_folders": folder_count,
                "root_total": file_count + folder_count,
            }
            
            print(f"✅ 空间概况: {folder_count} 个文件夹, {file_count} 个文件 (仅根目录)")
            return space_info
        except Exception as e:
            print(f"❌ 获取空间信息失败: {e}")
            return None


# 测试代码
if __name__ == "__main__":
    print("🗂️  飞书空间模块测试")
    
    class MockAPI:
        def create_folder(self, name, parent):
            return {"token": "fld_test123", "url": f"https://feishu.cn/drive/folder/fld_test123"}
        
        def list_folder(self, parent):
            return [
                {"token": "fld_001", "name": "工作文档", "type": "folder"},
                {"token": "fld_002", "name": "模板库", "type": "folder"},
                {"token": "doc_001", "name": "周报.docx", "type": "docx"},
            ]
    
    api = MockAPI()
    space = FeishuSpace(api)
    
    # 测试创建文件夹
    result = space.create_folder("测试文件夹")
    print(f"创建结果: {result}")
    
    # 测试列出文件夹
    folders = space.list_folders()
    print(f"文件夹数: {len(folders)}")
    
    # 测试空间信息
    info = space.get_space_info()
    print(f"空间信息: {info}")
    
    print("✅ 空间模块测试完成")
