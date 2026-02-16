#!/usr/bin/env python3
from __future__ import annotations
"""
记忆管理模块 — 防选题撞车、防观点矛盾、追踪创作历史。

功能:
  1. 记录每次创作（选题、立场、引用数据）
  2. 检查新选题是否与历史冲突
  3. 检查立场是否与之前矛盾
  4. 查询和搜索历史记录

存储格式:
    memory/YYYY-MM-DD.json — 每天一个文件，追加写入
    每条记录: {
        "timestamp": "2026-02-12T21:30:00",
        "topic": "选题标题",
        "stance": {"AI Agent": "看多", "Tesla FSD": "谨慎乐观"},
        "data_cited": ["GPT-5 参数 10T", "推理成本降 80%"],
        "platforms": ["飞书", "知乎"],
        "status": "draft|published|abandoned"
    }

用法:
    # 记录一次创作
    python memory.py log --topic "GPT-5 发布" --stance "AI Agent:看多" --data-cited "参数10T, 成本降80%"

    # 检查选题是否写过
    python memory.py check --topic "GPT-5 相关"

    # 检查立场是否矛盾
    python memory.py stance --entity "Tesla FSD" --new-stance "看空"

    # 搜索历史
    python memory.py search --query "GPT"

    # 列出最近记录
    python memory.py list --days 7
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from typing import Any
from pathlib import Path

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEMORY_DIR = os.path.join(SKILL_DIR, "memory")


def ensure_memory_dir():
    """确保记忆目录存在"""
    os.makedirs(MEMORY_DIR, exist_ok=True)


def get_today_file() -> str:
    """获取今天的记忆文件路径"""
    return os.path.join(MEMORY_DIR, f"{datetime.now().strftime('%Y-%m-%d')}.json")


def load_day_entries(filepath: str) -> List[Dict]:
    """加载某天的记忆条目"""
    if not os.path.exists(filepath):
        return []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []


def save_day_entries(filepath: str, entries: List[Dict]):
    """保存某天的记忆条目"""
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)


def load_all_entries(days: int = 30) -> List[Dict]:
    """加载最近 N 天的所有记忆条目"""
    ensure_memory_dir()
    all_entries = []
    
    for i in range(days):
        date = datetime.now() - timedelta(days=i)
        filepath = os.path.join(MEMORY_DIR, f"{date.strftime('%Y-%m-%d')}.json")
        entries = load_day_entries(filepath)
        for entry in entries:
            entry["_date"] = date.strftime("%Y-%m-%d")
        all_entries.extend(entries)
    
    return all_entries


def _similarity(a: str, b: str) -> float:
    """字级 Jaccard 相似度"""
    set_a = set(a)
    set_b = set(b)
    if not set_a or not set_b:
        return 0.0
    return len(set_a & set_b) / len(set_a | set_b)


def _keyword_overlap(a: str, b: str) -> float:
    """关键词重叠度"""
    # 分词（按空格和标点）
    import re
    words_a = set(re.findall(r'[\u4e00-\u9fff]+|[a-zA-Z]+', a.lower()))
    words_b = set(re.findall(r'[\u4e00-\u9fff]+|[a-zA-Z]+', b.lower()))
    
    if not words_a or not words_b:
        return 0.0
    
    return len(words_a & words_b) / min(len(words_a), len(words_b))


# ------ 命令实现 ------

def cmd_log(args):
    """记录一次创作"""
    ensure_memory_dir()
    
    # 解析立场
    stance = {}
    if args.stance:
        for item in args.stance.split(","):
            item = item.strip()
            if ":" in item:
                entity, opinion = item.split(":", 1)
                stance[entity.strip()] = opinion.strip()
            elif "：" in item:
                entity, opinion = item.split("：", 1)
                stance[entity.strip()] = opinion.strip()
            else:
                stance[item] = "中性"
    
    # 解析引用数据
    data_cited = []
    if args.data_cited:
        data_cited = [d.strip() for d in args.data_cited.split(",") if d.strip()]
    
    # 解析平台
    platforms = []
    if hasattr(args, "platforms") and args.platforms:
        platforms = [p.strip() for p in args.platforms.split(",") if p.strip()]
    
    entry = {
        "timestamp": datetime.now().isoformat(),
        "topic": args.topic,
        "stance": stance,
        "data_cited": data_cited,
        "platforms": platforms,
        "status": getattr(args, "status", "draft"),
        "notes": getattr(args, "notes", ""),
    }
    
    # 追加到今天的文件
    filepath = get_today_file()
    entries = load_day_entries(filepath)
    entries.append(entry)
    save_day_entries(filepath, entries)
    
    print(f"✅ 记忆已记录")
    print(f"   选题: {args.topic}")
    if stance:
        print(f"   立场: {stance}")
    if data_cited:
        print(f"   数据: {data_cited}")
    print(f"   文件: {filepath}")


def cmd_check(args):
    """检查选题是否写过（防撞车）"""
    all_entries = load_all_entries(days=90)
    
    if not all_entries:
        print("✅ 记忆库为空，没有冲突。")
        return
    
    topic = args.topic
    collisions = []
    
    for entry in all_entries:
        entry_topic = entry.get("topic", "")
        sim_char = _similarity(topic, entry_topic)
        sim_kw = _keyword_overlap(topic, entry_topic)
        
        # 综合相似度
        sim = max(sim_char, sim_kw)
        
        if sim > 0.4:
            collisions.append({
                "date": entry.get("_date", entry.get("timestamp", "")[:10]),
                "topic": entry_topic,
                "similarity": round(sim, 2),
                "stance": entry.get("stance", {}),
                "status": entry.get("status", "unknown"),
            })
    
    # 按相似度排序
    collisions.sort(key=lambda x: x["similarity"], reverse=True)
    
    if not collisions:
        print(f"✅ 「{topic}」没有发现冲突选题。可以放心写！")
    else:
        print(f"⚠️ 「{topic}」发现 {len(collisions)} 个相似选题:")
        print()
        for c in collisions[:5]:
            emoji = "🔴" if c["similarity"] > 0.7 else "🟡" if c["similarity"] > 0.5 else "🟢"
            print(f"  {emoji} [{c['date']}] {c['topic']}")
            print(f"     相似度: {c['similarity']} | 状态: {c['status']}")
            if c["stance"]:
                print(f"     立场: {c['stance']}")
            print()
        
        if collisions[0]["similarity"] > 0.7:
            print("⛔ 建议: 高度相似！换一个角度，或者放弃这个选题。")
        elif collisions[0]["similarity"] > 0.5:
            print("💡 建议: 有一定重叠，建议换一个切入角度。")
        else:
            print("✅ 相似度较低，可以写但注意差异化。")


def cmd_stance(args):
    """检查立场是否矛盾"""
    all_entries = load_all_entries(days=90)
    
    entity = args.entity
    new_stance = args.new_stance
    
    # 搜索历史立场
    history = []
    for entry in all_entries:
        stances = entry.get("stance", {})
        for ent, opinion in stances.items():
            if _keyword_overlap(entity, ent) > 0.5:
                history.append({
                    "date": entry.get("_date", entry.get("timestamp", "")[:10]),
                    "entity": ent,
                    "opinion": opinion,
                    "topic": entry.get("topic", ""),
                })
    
    if not history:
        print(f"✅ 没有关于「{entity}」的历史立场记录。可以自由表态。")
        return
    
    print(f"📋 关于「{entity}」的历史立场:")
    print()
    for h in history:
        print(f"  [{h['date']}] {h['entity']}: {h['opinion']}")
        print(f"     文章: {h['topic']}")
    
    print()
    
    # 检查矛盾
    latest = history[-1]
    if latest["opinion"] != new_stance:
        # 简单判断是否矛盾（看多 vs 看空）
        opposites = {
            ("看多", "看空"), ("看空", "看多"),
            ("支持", "反对"), ("反对", "支持"),
            ("推荐", "不推荐"), ("不推荐", "推荐"),
            ("乐观", "悲观"), ("悲观", "乐观"),
        }
        
        pair = (latest["opinion"], new_stance)
        if pair in opposites:
            print(f"⚠️ 立场反转! 上次({latest['date']}): {latest['opinion']} → 这次: {new_stance}")
            print(f"   如果确实要改，请在文章中说明原因（新数据、新事件）。")
            print(f"   否则读者会觉得你前后矛盾。")
        else:
            print(f"💡 立场有变化但不算矛盾: {latest['opinion']} → {new_stance}")
    else:
        print(f"✅ 立场一致: {new_stance}。没有矛盾。")


def cmd_search(args):
    """搜索历史记录"""
    all_entries = load_all_entries(days=90)
    query = args.query.lower()
    
    results = []
    for entry in all_entries:
        # 在选题、立场、数据中搜索
        searchable = json.dumps(entry, ensure_ascii=False).lower()
        if query in searchable:
            results.append(entry)
    
    if not results:
        print(f"🔍 没有找到与「{args.query}」相关的记录。")
        return
    
    print(f"🔍 找到 {len(results)} 条与「{args.query}」相关的记录:")
    print()
    for entry in results[:10]:
        date = entry.get("_date", entry.get("timestamp", "")[:10])
        topic = entry.get("topic", "未知")
        status = entry.get("status", "unknown")
        print(f"  [{date}] {topic} ({status})")
        if entry.get("stance"):
            print(f"    立场: {entry['stance']}")
        if entry.get("data_cited"):
            print(f"    数据: {', '.join(entry['data_cited'][:3])}")
        print()


def cmd_list(args):
    """列出最近的记录"""
    days = getattr(args, "days", 7)
    all_entries = load_all_entries(days=days)
    
    if not all_entries:
        print(f"📋 最近 {days} 天内没有创作记录。")
        return
    
    print(f"📋 最近 {days} 天的创作记录 (共 {len(all_entries)} 条):")
    print()
    
    for entry in all_entries:
        date = entry.get("_date", entry.get("timestamp", "")[:10])
        topic = entry.get("topic", "未知")
        status = entry.get("status", "unknown")
        
        status_emoji = {"draft": "📝", "published": "✅", "abandoned": "❌"}.get(status, "❓")
        
        print(f"  {status_emoji} [{date}] {topic}")
        if entry.get("stance"):
            print(f"     立场: {entry['stance']}")
        if entry.get("platforms"):
            print(f"     平台: {', '.join(entry['platforms'])}")
    
    print()
    
    # 统计
    status_counts = {}
    for entry in all_entries:
        s = entry.get("status", "unknown")
        status_counts[s] = status_counts.get(s, 0) + 1
    
    print(f"📊 统计: {status_counts}")


def main():
    parser = argparse.ArgumentParser(description="记忆管理模块")
    subparsers = parser.add_subparsers(dest="command", help="操作")
    
    # log
    log_parser = subparsers.add_parser("log", help="记录一次创作")
    log_parser.add_argument("--topic", required=True, help="选题标题")
    log_parser.add_argument("--stance", help="立场（格式: 实体:观点,实体:观点）")
    log_parser.add_argument("--data-cited", help="引用的数据（逗号分隔）")
    log_parser.add_argument("--platforms", help="发布平台（逗号分隔）")
    log_parser.add_argument("--status", default="draft", choices=["draft", "published", "abandoned"],
                           help="状态")
    log_parser.add_argument("--notes", default="", help="备注")
    
    # check
    check_parser = subparsers.add_parser("check", help="检查选题是否写过")
    check_parser.add_argument("--topic", required=True, help="要检查的选题标题")
    
    # stance
    stance_parser = subparsers.add_parser("stance", help="检查立场是否矛盾")
    stance_parser.add_argument("--entity", required=True, help="实体名称")
    stance_parser.add_argument("--new-stance", required=True, help="新立场")
    
    # search
    search_parser = subparsers.add_parser("search", help="搜索历史记录")
    search_parser.add_argument("--query", required=True, help="搜索关键词")
    
    # list
    list_parser = subparsers.add_parser("list", help="列出最近记录")
    list_parser.add_argument("--days", type=int, default=7, help="查看最近几天")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    ensure_memory_dir()
    
    dispatch = {
        "log": cmd_log,
        "check": cmd_check,
        "stance": cmd_stance,
        "search": cmd_search,
        "list": cmd_list,
    }
    
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
