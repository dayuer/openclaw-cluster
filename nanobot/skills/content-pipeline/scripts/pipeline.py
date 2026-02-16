#!/usr/bin/env python3
"""
Content Pipeline 主控 — 一键跑完"侦察 → 选题 → 写作 → 飞书"全流程。

用法:
    # 全自动流水线（侦察 + 等待选择 + 写作 + 飞书）
    python pipeline.py run

    # 仅侦察选题
    python pipeline.py scout

    # 指定选题直接写作
    python pipeline.py draft --topic "GPT-5 发布" --angle "创业者视角"

    # 查看记忆（已写过的选题）
    python pipeline.py memory --action list

环境:
    需要在 nanobot 容器内运行（/app/workspace/...）
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime

# 路径常量
SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(SKILL_DIR, "scripts")
SOUL_FILE = os.path.join(SKILL_DIR, "SOUL.md")
STYLE_FILE = os.path.join(SKILL_DIR, "STYLE.md")
MEMORY_DIR = os.path.join(SKILL_DIR, "memory")
TMP_DIR = "/tmp/nanobot"

# 依赖 skill 路径
LLM_PROCESSOR = "/app/skills/llm-processor/scripts/llm_process.py"
FEISHU_DOC = "/app/skills/feishu/scripts/feishu.py"


def ensure_dirs():
    """确保必要目录存在"""
    os.makedirs(TMP_DIR, exist_ok=True)
    os.makedirs(MEMORY_DIR, exist_ok=True)


def run_script(script_path, args_list, capture=True):
    """运行 Python 脚本"""
    cmd = [sys.executable, script_path] + args_list
    print(f"🔧 执行: {' '.join(cmd)}")

    if capture:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        if result.returncode != 0:
            print(f"❌ 脚本失败: {result.stderr}", file=sys.stderr)
            return None
        return result.stdout.strip()
    else:
        return subprocess.run(cmd, timeout=180)


def cmd_scout(args):
    """阶段 1: 热点侦察"""
    print("=" * 60)
    print("📡 阶段 1: 热点侦察")
    print("=" * 60)

    scout_args = [
        "--count", str(getattr(args, "count", 5)),
    ]
    if hasattr(args, "keywords") and args.keywords:
        scout_args.extend(["--keywords", args.keywords])

    output_path = os.path.join(TMP_DIR, "topics.md")
    scout_args.extend(["--output", output_path])

    scout_script = os.path.join(SCRIPTS_DIR, "scout.py")
    result = run_script(scout_script, scout_args)

    if result:
        print(result)
    
    if os.path.exists(output_path):
        with open(output_path, "r", encoding="utf-8") as f:
            print("\n📋 完整选题报告:")
            print(f.read())

    print('\n💡 回复数字选择要写的选题（如 "1"），或输入自定义选题。')
    return output_path


def cmd_draft(args):
    """阶段 2: 深度撰写"""
    print("=" * 60)
    print("✍️ 阶段 2: 深度撰写")
    print("=" * 60)

    topic = args.topic
    angle = getattr(args, "angle", "")
    raw_file = getattr(args, "raw", None)

    if not topic:
        print("❌ 请用 --topic 指定选题", file=sys.stderr)
        sys.exit(1)

    draft_script = os.path.join(SCRIPTS_DIR, "draft.py")
    draft_args = [
        "--topic", topic,
        "--output", os.path.join(TMP_DIR, "draft_final.md"),
    ]
    if angle:
        draft_args.extend(["--angle", angle])
    if raw_file:
        draft_args.extend(["--raw", raw_file])

    result = run_script(draft_script, draft_args)
    if result:
        print(result)

    output_path = os.path.join(TMP_DIR, "draft_final.md")
    if os.path.exists(output_path):
        with open(output_path, "r", encoding="utf-8") as f:
            content = f.read()
            print(f"\n✅ 初稿生成完成 ({len(content)} 字)")
            # 显示前300字预览
            print("\n📖 预览 (前 300 字):")
            print(content[:300] + "...")

    return output_path


def cmd_publish(args):
    """阶段 3: 推送到飞书"""
    print("=" * 60)
    print("📤 阶段 3: 推送到飞书")
    print("=" * 60)

    draft_path = getattr(args, "file", os.path.join(TMP_DIR, "draft_final.md"))
    title = getattr(args, "title", "[草稿] 待修改标题")

    if not os.path.exists(draft_path):
        print(f"❌ 初稿文件不存在: {draft_path}", file=sys.stderr)
        sys.exit(1)

    # 调用飞书文档 skill
    feishu_args = [
        "create_doc",
        "--title", title,
        "--file", draft_path,
    ]

    result = run_script(FEISHU_DOC, feishu_args)
    if result:
        print(result)
        # 解析飞书返回的 URL
        for line in result.split("\n"):
            if "url" in line.lower() or "http" in line:
                print(f"\n🔗 飞书文档: {line}")

    return result


def cmd_memory(args):
    """查看/管理记忆"""
    memory_script = os.path.join(SCRIPTS_DIR, "memory.py")
    memory_args = [args.memory_action]

    if hasattr(args, "topic") and args.topic:
        memory_args.extend(["--topic", args.topic])
    if hasattr(args, "query") and args.query:
        memory_args.extend(["--query", args.query])
    if hasattr(args, "stance") and args.stance:
        memory_args.extend(["--stance", args.stance])
    if hasattr(args, "data_cited") and args.data_cited:
        memory_args.extend(["--data-cited", args.data_cited])

    result = run_script(memory_script, memory_args)
    if result:
        print(result)


def cmd_run(args):
    """全自动流水线"""
    print("🚀 Content Pipeline — 全自动流水线启动")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    ensure_dirs()

    # 阶段 1: 侦察
    cmd_scout(args)

    print("\n" + "=" * 60)
    print("⏸️  等待你选择选题...")
    print("   在 nanobot 对话中回复数字即可。")
    print("   或者手动运行: pipeline.py draft --topic '你的选题'")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Content Pipeline — 全自动内容创作流水线",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python pipeline.py run                           # 全自动流水线
  python pipeline.py scout --keywords "AI,创业"     # 仅侦察选题
  python pipeline.py draft --topic "GPT-5 发布"    # 指定选题写作
  python pipeline.py memory list                   # 查看记忆
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # run
    run_parser = subparsers.add_parser("run", help="运行全自动流水线")
    run_parser.add_argument("--keywords", default="AI Agent,SaaS,出海,创业", help="搜索关键词")
    run_parser.add_argument("--count", type=int, default=5, help="选题数量")

    # scout
    scout_parser = subparsers.add_parser("scout", help="仅侦察选题")
    scout_parser.add_argument("--keywords", default="AI Agent,SaaS,出海,创业", help="搜索关键词")
    scout_parser.add_argument("--count", type=int, default=5, help="选题数量")
    scout_parser.add_argument("--output", help="输出文件路径")

    # draft
    draft_parser = subparsers.add_parser("draft", help="指定选题写作")
    draft_parser.add_argument("--topic", required=True, help="选题标题")
    draft_parser.add_argument("--angle", default="", help="切入角度")
    draft_parser.add_argument("--raw", help="原始素材文件路径")
    draft_parser.add_argument("--output", help="输出文件路径")

    # publish
    pub_parser = subparsers.add_parser("publish", help="推送到飞书")
    pub_parser.add_argument("--file", default=os.path.join(TMP_DIR, "draft_final.md"), help="初稿文件路径")
    pub_parser.add_argument("--title", default="[草稿] 待修改标题", help="飞书文档标题")

    # memory
    mem_parser = subparsers.add_parser("memory", help="记忆管理")
    mem_parser.add_argument("memory_action", choices=["list", "search", "log", "check"],
                            help="操作: list(列表)/search(搜索)/log(记录)/check(检查)")
    mem_parser.add_argument("--topic", help="选题标题")
    mem_parser.add_argument("--query", help="搜索关键词")
    mem_parser.add_argument("--stance", help="对某事物的立场")
    mem_parser.add_argument("--data-cited", help="引用的数据")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    ensure_dirs()

    dispatch = {
        "run": cmd_run,
        "scout": cmd_scout,
        "draft": cmd_draft,
        "publish": cmd_publish,
        "memory": cmd_memory,
    }

    dispatch[args.command](args)


if __name__ == "__main__":
    main()
