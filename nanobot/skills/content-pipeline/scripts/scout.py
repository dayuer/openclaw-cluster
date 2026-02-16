#!/usr/bin/env python3
from __future__ import annotations
"""
热点侦察 + 选题筛选

功能:
  1. 通过 nanobot 内置的 web_search 搜索热点（本脚本生成搜索查询）
  2. 对搜索结果进行筛选、评分、排序
  3. 输出格式化的选题列表

用法:
    # 生成查询建议 + 筛选结果
    python scout.py --keywords "AI Agent,SaaS" --count 5

    # 从已有素材文件筛选（nanobot 搜索后保存的结果）
    python scout.py --from-file /tmp/nanobot/search_results.md --count 5

    # 输出到文件
    python scout.py --keywords "AI,创业" --output /tmp/nanobot/topics.md

设计思路:
    本脚本 **不直接调用搜索 API**（那是 nanobot V3 的活）。
    它负责：
    1. 生成最优搜索查询组合
    2. 如果有素材文件，对其进行筛选和评分
    3. 输出格式化的选题建议

    典型调用链：
    V3: web_search("AI Agent framework trending")
    V3: write_file /tmp/nanobot/search_results.md "搜索结果..."
    V3: exec python scout.py --from-file /tmp/nanobot/search_results.md
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime
from dataclasses import dataclass, field, asdict

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEMORY_DIR = os.path.join(SKILL_DIR, "memory")


@dataclass
class TopicCandidate:
    """选题候选"""
    title: str
    source: str = ""
    url: str = ""
    hot_score: float = 0.0
    relevance_score: float = 0.0
    controversy_score: float = 0.0
    angles: List[str] = field(default_factory=list)
    key_points: List[str] = field(default_factory=list)
    one_liner: str = ""


# ------ 查询生成器 ------

QUERY_TEMPLATES = [
    # (模板, 描述)
    ("{keyword} 最新争议 OR 重大更新 site:twitter.com OR site:reddit.com", "社交热议"),
    ("{keyword} github trending 2026", "技术趋势"),
    ("{keyword} pricing model change OR 定价调整", "商业变动"),
    ("{keyword} 融资 OR raised OR funding 2026", "融资动态"),
    ("{keyword} 实测 OR review OR 评测 2026", "深度评测"),
    ("{keyword} vs 对比 2026", "产品对比"),
    ("{keyword} 甚至 OR 居然 OR 没想到", "反直觉内容"),
]


def generate_queries(keywords: str) -> List[dict]:
    """生成最优搜索查询组合"""
    keyword_list = [k.strip() for k in keywords.split(",") if k.strip()]
    queries = []

    for kw in keyword_list:
        for template, desc in QUERY_TEMPLATES[:3]:  # 每个关键词取前3个模板
            query = template.format(keyword=kw)
            queries.append({
                "query": query,
                "keyword": kw,
                "type": desc,
            })

    return queries


# ------ 素材筛选器 ------

# 新闻通稿特征词（用于过滤低质量内容）
PRESS_RELEASE_SIGNALS = [
    "新闻稿", "发布会", "宣布", "隆重推出", "正式发布",
    "行业领先", "全球领先", "开创性", "里程碑式",
    "战略合作", "全面合作", "达成合作",
]

# 观点/争议信号词（有价值内容的标志）
OPINION_SIGNALS = [
    "但是", "然而", "不过", "争议", "质疑", "问题是",
    "其实", "反而", "没想到", "甚至", "竟然",
    "实测", "踩坑", "真实体验", "经验", "教训",
    "数据", "对比", "vs", "测试结果",
]

# 用户定位关键词（影响相关性评分）
USER_PROFILE_KEYWORDS = [
    "AI", "Agent", "LLM", "编程", "coding", "programming",
    "出海", "海外", "SaaS", "独立开发", "创业", "startup",
    "效率", "自动化", "工具", "产品",
]


def score_content(text: str, title: str) -> dict:
    """对一条内容进行评分"""
    text_lower = text.lower()
    title_lower = title.lower()

    # 1. 通稿过滤
    press_count = sum(1 for signal in PRESS_RELEASE_SIGNALS if signal in text)
    is_press_release = press_count >= 3

    # 2. 观点/争议评分 (0-10)
    opinion_count = sum(1 for signal in OPINION_SIGNALS if signal in text)
    controversy_score = min(opinion_count * 1.5, 10.0)

    # 3. 相关性评分 (0-10)
    relevance_count = sum(1 for kw in USER_PROFILE_KEYWORDS if kw.lower() in text_lower or kw.lower() in title_lower)
    relevance_score = min(relevance_count * 1.5, 10.0)

    # 4. 热度评分 (基于启发式)
    hot_score = 5.0  # 基础分
    # 有数字 = 可能有数据 = 加分
    if re.search(r'\d+%|\d+[万亿]|$\d+|¥\d+', text):
        hot_score += 1.5
    # 有代码 = 技术深度 = 加分
    if "```" in text or "github.com" in text_lower:
        hot_score += 1.0
    # 有名人/知名公司 = 加分
    known_entities = ["OpenAI", "Google", "Meta", "Tesla", "Elon", "Sam Altman", "字节", "阿里", "腾讯"]
    entity_count = sum(1 for e in known_entities if e.lower() in text_lower)
    hot_score += min(entity_count * 0.8, 3.0)
    hot_score = min(hot_score, 10.0)

    return {
        "is_press_release": is_press_release,
        "hot_score": round(hot_score, 1),
        "relevance_score": round(relevance_score, 1),
        "controversy_score": round(controversy_score, 1),
        "composite_score": round(
            hot_score * 0.3 + relevance_score * 0.4 + controversy_score * 0.3,
            1
        ),
    }


def parse_search_results(content: str) -> List[TopicCandidate]:
    """从搜索结果文件解析出选题候选"""
    candidates = []

    # 尝试按段落分割
    sections = re.split(r'\n(?=#{1,3}\s|---|\*\*)', content)

    for section in sections:
        section = section.strip()
        if not section or len(section) < 50:
            continue

        # 提取标题（第一行或 ## 标题）
        lines = section.split("\n")
        title = lines[0].strip().lstrip("#").strip().strip("*").strip()
        if not title or len(title) < 5:
            continue

        # 提取 URL
        urls = re.findall(r'https?://[^\s\)]+', section)
        url = urls[0] if urls else ""

        # 评分
        scores = score_content(section, title)

        # 跳过通稿
        if scores["is_press_release"]:
            continue

        # 生成切入角度
        angles = []
        if scores["controversy_score"] > 5:
            angles.append("争议分析")
        if scores["hot_score"] > 7:
            angles.append("热点解读")
        if "实测" in section or "评测" in section:
            angles.append("实操评测")
        if "vs" in section.lower() or "对比" in section:
            angles.append("产品对比")
        if not angles:
            angles.append("深度分析")

        # 生成一句话核心看点
        one_liner = title[:50]
        for signal in OPINION_SIGNALS:
            idx = section.find(signal)
            if idx > 0:
                sentence_end = section.find("。", idx)
                if sentence_end > 0:
                    one_liner = section[idx:sentence_end + 1][:80]
                    break

        candidate = TopicCandidate(
            title=title[:60],
            source="web_search",
            url=url,
            hot_score=scores["hot_score"],
            relevance_score=scores["relevance_score"],
            controversy_score=scores["controversy_score"],
            angles=angles,
            key_points=[],
            one_liner=one_liner,
        )
        candidates.append(candidate)

    # 按综合评分排序
    candidates.sort(
        key=lambda c: c.hot_score * 0.3 + c.relevance_score * 0.4 + c.controversy_score * 0.3,
        reverse=True,
    )

    return candidates


def check_memory_collision(topic_title: str) -> Optional[dict]:
    """检查选题是否与记忆中的历史题目冲突"""
    if not os.path.exists(MEMORY_DIR):
        return None

    for filename in os.listdir(MEMORY_DIR):
        if not filename.endswith(".json"):
            continue
        filepath = os.path.join(MEMORY_DIR, filename)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                entries = json.load(f)
            for entry in entries:
                if entry.get("topic") and _similarity(topic_title, entry["topic"]) > 0.6:
                    return entry
        except (json.JSONDecodeError, KeyError):
            continue

    return None


def _similarity(a: str, b: str) -> float:
    """简单的字符级 Jaccard 相似度"""
    set_a = set(a)
    set_b = set(b)
    if not set_a or not set_b:
        return 0.0
    return len(set_a & set_b) / len(set_a | set_b)


# ------ 输出格式化 ------

def format_topics_compact(candidates: List[TopicCandidate], count: int = 5) -> str:
    """紧凑格式：给 IM 推送用"""
    lines = [f"📰 今日选题建议 ({datetime.now().strftime('%m-%d %H:%M')})"]
    lines.append("")

    for i, c in enumerate(candidates[:count], 1):
        composite = round(c.hot_score * 0.3 + c.relevance_score * 0.4 + c.controversy_score * 0.3, 1)
        lines.append(f"[{composite}] {i}. {c.title}")
        lines.append(f"   角度: {' / '.join(c.angles)}")
        if c.one_liner and c.one_liner != c.title:
            lines.append(f"   看点: {c.one_liner}")
        
        # 检查记忆冲突
        collision = check_memory_collision(c.title)
        if collision:
            lines.append(f"   ⚠️ 注意: {collision.get('date', '')} 写过类似选题 \"{collision.get('topic', '')}\"")
        
        lines.append("")

    lines.append("💡 回复数字选择要写的选题（如 '1'）")
    return "\n".join(lines)


def format_topics_full(candidates: List[TopicCandidate], count: int = 5) -> str:
    """完整格式：Markdown 报告"""
    lines = [f"# 📰 今日选题建议"]
    lines.append(f"\n> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("")

    for i, c in enumerate(candidates[:count], 1):
        composite = round(c.hot_score * 0.3 + c.relevance_score * 0.4 + c.controversy_score * 0.3, 1)
        lines.append(f"## {i}. {c.title}")
        lines.append("")
        lines.append(f"- **综合评分**: {composite}/10")
        lines.append(f"- **热度**: {c.hot_score}/10 | **相关性**: {c.relevance_score}/10 | **争议性**: {c.controversy_score}/10")
        lines.append(f"- **来源**: {c.source}")
        if c.url:
            lines.append(f"- **链接**: {c.url}")
        lines.append(f"- **切入角度**: {' / '.join(c.angles)}")
        if c.one_liner and c.one_liner != c.title:
            lines.append(f"- **核心看点**: {c.one_liner}")
        
        collision = check_memory_collision(c.title)
        if collision:
            lines.append(f"- ⚠️ **记忆冲突**: {collision.get('date', '')} 写过类似选题")
        
        lines.append("")
        lines.append("---")
        lines.append("")

    lines.append("\n💡 回复数字选择要写的选题")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="热点侦察 + 选题筛选")
    parser.add_argument("--keywords", default="AI Agent,SaaS,出海,创业", help="搜索关键词（逗号分隔）")
    parser.add_argument("--from-file", help="从文件读取搜索结果（而非生成查询）")
    parser.add_argument("--count", type=int, default=5, help="输出选题数量")
    parser.add_argument("--output", help="输出到文件")
    parser.add_argument("--format", choices=["compact", "full"], default="full", help="输出格式")
    parser.add_argument("--queries-only", action="store_true", help="仅输出搜索查询（不筛选）")

    args = parser.parse_args()

    if args.queries_only:
        # 模式 1: 只生成查询，给 nanobot V3 去执行搜索
        queries = generate_queries(args.keywords)
        print("🔍 推荐搜索查询:")
        print()
        for i, q in enumerate(queries, 1):
            print(f"{i}. [{q['type']}] {q['query']}")
        
        print(f"\n共 {len(queries)} 条查询")
        print("V3 请依次执行 web_search，把结果合并保存到文件后，再调用 scout.py --from-file")
        return

    if args.from_file:
        # 模式 2: 从文件筛选
        if not os.path.exists(args.from_file):
            print(f"❌ 文件不存在: {args.from_file}", file=sys.stderr)
            sys.exit(1)
        
        with open(args.from_file, "r", encoding="utf-8") as f:
            content = f.read()
        
        candidates = parse_search_results(content)
        print(f"✅ 从文件中筛选出 {len(candidates)} 个选题候选")
    else:
        # 模式 3: 生成查询 + 提示调用搜索
        queries = generate_queries(args.keywords)
        print("📡 热点侦察 — 搜索查询生成完成")
        print()
        print("推荐搜索查询 (V3 请执行 web_search):")
        for i, q in enumerate(queries[:5], 1):
            print(f"  {i}. {q['query']}")
        print()
        print("搜索完成后，将结果保存到文件，再调用:")
        print(f"  python scout.py --from-file /tmp/nanobot/search_results.md --count {args.count}")
        
        # 同时输出一个空的模板文件
        candidates = []

    if candidates:
        if args.format == "compact":
            report = format_topics_compact(candidates, args.count)
        else:
            report = format_topics_full(candidates, args.count)
    else:
        report = "暂无筛选结果。请先执行搜索并保存结果到文件。"

    if args.output:
        os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"\n📝 选题报告已保存: {args.output}")
    else:
        print()
        print(report)


if __name__ == "__main__":
    main()
