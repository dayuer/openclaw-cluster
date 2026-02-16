#!/usr/bin/env python3
"""
飞书集成工具 - 主脚本
企业级飞书集成解决方案，支持文档管理、文件操作、空间管理和自动化工作流
"""

import argparse
import sys
import os
import json
from pathlib import Path

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from feishu_api import FeishuAPI
from feishu_doc import FeishuDoc
from feishu_file import FeishuFile
from feishu_space import FeishuSpace
from feishu_auto import FeishuAuto


class FeishuCLI:
    """飞书命令行接口"""
    
    def __init__(self, config_path=None):
        """初始化飞书CLI"""
        config = self._load_config(config_path)
        self.api = FeishuAPI(config)
        self.doc = FeishuDoc(self.api)
        self.file = FeishuFile(self.api)
        self.space = FeishuSpace(self.api)
        self.auto = FeishuAuto(self.api, config)
    
    def _load_config(self, config_path=None):
        """加载配置文件，环境变量优先"""
        config = {"feishu": {}, "defaults": {}}
        
        if config_path is None:
            config_dir = Path(__file__).parent.parent / "config"
            for name in ("config.yaml", "config.example.yaml"):
                p = config_dir / name
                if p.exists():
                    config_path = p
                    break
        
        if config_path and Path(config_path).exists():
            try:
                import yaml
                with open(config_path, "r", encoding="utf-8") as f:
                    config = yaml.safe_load(f) or config
            except ImportError:
                pass  # yaml 不可用时使用默认空 config
            except Exception as e:
                print(f"⚠️  加载配置文件失败: {e}，使用默认配置")
        
        # 环境变量覆盖
        feishu = config.setdefault("feishu", {})
        if os.getenv("FEISHU_APP_ID"):
            feishu["app_id"] = os.getenv("FEISHU_APP_ID")
        if os.getenv("FEISHU_APP_SECRET"):
            feishu["app_secret"] = os.getenv("FEISHU_APP_SECRET")
        
        return config
    
    # ── 文档操作 ──
    
    def create_doc(self, title, content=None, file_path=None, folder_token=None):
        """创建文档"""
        print(f"📄 创建文档: {title}")
        if file_path:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
            except Exception as e:
                print(f"❌ 读取文件失败: {e}")
                return None
        if not content:
            print("❌ 必须提供内容或文件路径")
            return None
        try:
            doc_info = self.doc.create_document(title, content, folder_token)
            if doc_info:
                print(f"✅ 文档创建成功: {doc_info.get('url', 'N/A')}")
            return doc_info
        except Exception as e:
            print(f"❌ 创建文档失败: {e}")
            return None
    
    def append_doc(self, doc_id, content=None, file_path=None):
        """追加内容到文档"""
        print(f"📝 追加内容到文档: {doc_id}")
        if file_path:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
            except Exception as e:
                print(f"❌ 读取文件失败: {e}")
                return False
        if not content:
            print("❌ 必须提供内容或文件路径")
            return False
        try:
            result = self.doc.write_document_content(doc_id, content)
            if result:
                print("✅ 内容追加成功")
            return result
        except Exception as e:
            print(f"❌ 追加内容失败: {e}")
            return False
    
    def get_doc(self, doc_id):
        """获取文档信息"""
        try:
            info = self.doc.get_document_info(doc_id)
            if info:
                print(f"✅ 文档标题: {info.get('title', 'N/A')}")
                print(json.dumps(info, ensure_ascii=False, indent=2))
            return info
        except Exception as e:
            print(f"❌ 获取文档失败: {e}")
            return None
    
    def delete_doc(self, doc_id):
        """删除文档"""
        try:
            return self.doc.delete_document(doc_id)
        except Exception as e:
            print(f"❌ 删除文档失败: {e}")
            return False
    
    def share_doc(self, doc_id, permission="view"):
        """生成分享链接"""
        try:
            url = self.doc.share_document(doc_id, permission)
            if url:
                print(f"✅ 分享链接: {url}")
            return url
        except Exception as e:
            print(f"❌ 生成分享链接失败: {e}")
            return None
    
    def search_doc(self, query, limit=20):
        """搜索文档"""
        print(f"🔍 搜索文档: {query}")
        try:
            results = self.doc.search_documents(query, limit)
            if results:
                print(f"✅ 找到 {len(results)} 个文档")
                for i, doc in enumerate(results, 1):
                    print(f"  {i}. {doc.get('title', '无标题')} - {doc.get('url', 'N/A')}")
            else:
                print("❌ 未找到相关文档")
            return results or []
        except Exception as e:
            print(f"❌ 搜索文档失败: {e}")
            return []
    
    # ── 文件操作 ──
    
    def upload_file(self, file_path, folder_token=None):
        """上传文件"""
        print(f"📁 上传文件: {file_path}")
        if not os.path.exists(file_path):
            print(f"❌ 文件不存在: {file_path}")
            return None
        try:
            file_info = self.file.upload_file(file_path, folder_token)
            if file_info:
                print(f"✅ 文件上传成功: {file_info.get('url', 'N/A')}")
            return file_info
        except Exception as e:
            print(f"❌ 上传文件失败: {e}")
            return None
    
    def download_file(self, file_token, output_path):
        """下载文件"""
        print(f"📥 下载文件: {file_token} → {output_path}")
        try:
            result = self.file.download_file(file_token, output_path)
            if result:
                print(f"✅ 文件下载成功: {output_path}")
            return result
        except Exception as e:
            print(f"❌ 下载文件失败: {e}")
            return False
    
    def list_files(self, folder_token=None):
        """列出文件"""
        print("📋 列出文件...")
        try:
            files = self.file.list_files(folder_token)
            if files:
                print(f"✅ 找到 {len(files)} 个文件/文件夹")
                for i, item in enumerate(files, 1):
                    icon = "📁" if item.get("type") == "folder" else "📄"
                    print(f"  {i}. {icon} {item.get('name', '未命名')}")
            else:
                print("📭 文件夹为空")
            return files or []
        except Exception as e:
            print(f"❌ 列出文件失败: {e}")
            return []
    
    def move_file(self, file_token, target_folder):
        """移动文件"""
        print(f"📦 移动文件: {file_token} → {target_folder}")
        try:
            result = self.file.move_file(file_token, target_folder)
            if result:
                print("✅ 文件移动成功")
            return result
        except Exception as e:
            print(f"❌ 移动文件失败: {e}")
            return False
    
    def delete_file(self, file_token):
        """删除文件"""
        try:
            return self.file.delete_file(file_token)
        except Exception as e:
            print(f"❌ 删除文件失败: {e}")
            return False
    
    # ── 空间操作 ──
    
    def create_folder(self, name, parent_folder=None):
        """创建文件夹"""
        try:
            return self.space.create_folder(name, parent_folder)
        except Exception as e:
            print(f"❌ 创建文件夹失败: {e}")
            return None
    
    def list_folders(self, parent_folder=None):
        """列出文件夹"""
        try:
            return self.space.list_folders(parent_folder)
        except Exception as e:
            print(f"❌ 列出文件夹失败: {e}")
            return []
    
    # ── 自动化 ──
    
    def batch_create(self, template_name, data_file):
        """批量创建文档"""
        if not os.path.exists(data_file):
            print(f"❌ 数据文件不存在: {data_file}")
            return None
        try:
            with open(data_file, "r", encoding="utf-8") as f:
                if data_file.endswith(".json"):
                    data = json.load(f)
                else:
                    data = [json.loads(line) for line in f if line.strip()]
            
            if not isinstance(data, list):
                data = [data]
            
            return self.auto.batch_create_documents(template_name, data)
        except Exception as e:
            print(f"❌ 批量创建失败: {e}")
            return None
    
    def list_templates(self):
        """列出可用模板"""
        templates = self.auto.list_templates()
        if templates:
            print(f"📋 可用模板 ({len(templates)} 个):")
            for t in templates:
                print(f"  • {t}")
        else:
            print("📭 暂无模板")
        return templates
    
    # ── 连接测试 ──
    
    def test_connection(self):
        """测试飞书连接"""
        print("🔗 测试飞书连接...")
        try:
            token = self.api.get_tenant_access_token()
            if token:
                print("✅ 连接成功！")
                return True
            else:
                print("❌ 连接失败")
                return False
        except Exception as e:
            print(f"❌ 连接测试失败: {e}")
            return False
    
    # ── CLI 解析 ──
    
    def run(self):
        """运行命令行接口"""
        parser = argparse.ArgumentParser(
            description="飞书集成工具 — 文档/文件/空间/自动化",
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )
        sub = parser.add_subparsers(dest="command", help="可用命令")
        
        # ── 文档命令 ──
        
        p = sub.add_parser("create_doc", help="创建文档")
        p.add_argument("--title", required=True, help="文档标题")
        p.add_argument("--content", help="Markdown 内容")
        p.add_argument("--file", help="从文件读取内容")
        p.add_argument("--folder", help="目标文件夹 token")
        
        p = sub.add_parser("append_doc", help="追加内容到文档")
        p.add_argument("--doc_id", required=True, help="文档 ID")
        p.add_argument("--content", help="Markdown 内容")
        p.add_argument("--file", help="从文件读取内容")
        
        p = sub.add_parser("get_doc", help="获取文档信息")
        p.add_argument("--doc_id", required=True, help="文档 ID")
        
        p = sub.add_parser("delete_doc", help="删除文档")
        p.add_argument("--doc_id", required=True, help="文档 ID")
        
        p = sub.add_parser("share_doc", help="生成分享链接")
        p.add_argument("--doc_id", required=True, help="文档 ID")
        p.add_argument("--permission", default="view", choices=["view", "edit"], help="权限")
        
        p = sub.add_parser("search_doc", help="搜索文档")
        p.add_argument("--query", required=True, help="搜索关键词")
        p.add_argument("--limit", type=int, default=20, help="结果数量")
        
        # ── 文件命令 ──
        
        p = sub.add_parser("upload_file", help="上传文件")
        p.add_argument("--file_path", required=True, help="文件路径")
        p.add_argument("--folder", help="目标文件夹 token")
        
        p = sub.add_parser("download_file", help="下载文件")
        p.add_argument("--file_token", required=True, help="文件 token")
        p.add_argument("--output", required=True, help="输出路径")
        
        p = sub.add_parser("list_files", help="列出文件")
        p.add_argument("--folder", help="文件夹 token")
        
        p = sub.add_parser("move_file", help="移动文件")
        p.add_argument("--file_token", required=True, help="文件 token")
        p.add_argument("--target_folder", required=True, help="目标文件夹 token")
        
        p = sub.add_parser("delete_file", help="删除文件")
        p.add_argument("--file_token", required=True, help="文件 token")
        
        # ── 空间命令 ──
        
        p = sub.add_parser("create_folder", help="创建文件夹")
        p.add_argument("--name", required=True, help="文件夹名称")
        p.add_argument("--parent", help="父文件夹 token")
        
        p = sub.add_parser("list_folders", help="列出文件夹")
        p.add_argument("--parent", help="父文件夹 token")
        
        # ── 自动化命令 ──
        
        p = sub.add_parser("batch_create", help="批量创建文档")
        p.add_argument("--template", required=True, help="模板名称")
        p.add_argument("--data_file", required=True, help="数据文件 (JSON)")
        
        p = sub.add_parser("list_templates", help="列出可用模板")
        
        # ── 其他 ──
        
        sub.add_parser("test_connection", help="测试飞书连接")
        
        # 解析
        args = parser.parse_args()
        if not args.command:
            parser.print_help()
            return
        
        # 分发命令
        cmd = args.command
        
        if cmd == "create_doc":
            self.create_doc(args.title, args.content, args.file, args.folder)
        elif cmd == "append_doc":
            self.append_doc(args.doc_id, args.content, args.file)
        elif cmd == "get_doc":
            self.get_doc(args.doc_id)
        elif cmd == "delete_doc":
            self.delete_doc(args.doc_id)
        elif cmd == "share_doc":
            self.share_doc(args.doc_id, args.permission)
        elif cmd == "search_doc":
            self.search_doc(args.query, args.limit)
        elif cmd == "upload_file":
            self.upload_file(args.file_path, args.folder)
        elif cmd == "download_file":
            self.download_file(args.file_token, args.output)
        elif cmd == "list_files":
            self.list_files(args.folder)
        elif cmd == "move_file":
            self.move_file(args.file_token, args.target_folder)
        elif cmd == "delete_file":
            self.delete_file(args.file_token)
        elif cmd == "create_folder":
            self.create_folder(args.name, args.parent)
        elif cmd == "list_folders":
            self.list_folders(args.parent)
        elif cmd == "batch_create":
            self.batch_create(args.template, args.data_file)
        elif cmd == "list_templates":
            self.list_templates()
        elif cmd == "test_connection":
            self.test_connection()
        else:
            print(f"❌ 未知命令: {cmd}")
            parser.print_help()


def main():
    """主函数"""
    debug_mode = os.getenv("FEISHU_DEBUG", "0") == "1"
    try:
        cli = FeishuCLI()
        cli.run()
    except KeyboardInterrupt:
        print("\n👋 用户中断")
        sys.exit(0)
    except Exception as e:
        print(f"❌ 程序执行失败: {e}")
        if debug_mode:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()