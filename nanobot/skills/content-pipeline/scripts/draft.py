#!/usr/bin/env python3
from __future__ import annotations
"""
深度撰写模块 — 根据素材和风格规范生成 Markdown 初稿。

本脚本有两种使用模式:

模式 A: 后处理（推荐）
    R1 先通过 llm-processor 生成原始初稿，本脚本做后处理:
    - 插入视觉锚点（金句、图片占位符）
    - 格式检查（禁用词检测、标题层级）
    - 添加元数据

模式 B: 生成大纲
    不调用 LLM，只生成符合 STYLE.md 的大纲模板，
    让 nanobot V3 把大纲传给 R1 生成正文。

用法:
    # 模式 A: 后处理 R1 输出的原始稿件
    python draft.py --raw /tmp/nanobot/draft_raw.md --output /tmp/nanobot/draft_final.md

    # 模式 B: 仅生成大纲
    python draft.py --topic "GPT-5 发布" --angle "创业者视角" --outline-only

    # 从话题直接生成（生成大纲 + 提示调用 R1）
    python draft.py --topic "GPT-5 发布" --output /tmp/nanobot/draft_final.md
"""

import argparse
import json
import os
import random
import re
import sys
from datetime import datetime

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOUL_FILE = os.path.join(SKILL_DIR, "SOUL.md")
STYLE_FILE = os.path.join(SKILL_DIR, "STYLE.md")


# ------ SOUL 规则：禁用词 ------

BANNED_WORDS = [
    # 空泛大词
    "赋能", "抓手", "底层逻辑", "颠覆性", "革命性", "划时代", "里程碑式",
    # AI 味结尾
    "综上所述", "总而言之", "总之", "让我们拭目以待", "值得期待",
    # 水话开头
    "在当今社会", "随着", "众所周知", "不言而喻",
    # 假客气
    "您好", "亲爱的读者", "各位老师", "友友们",
    # 注水修饰
    "非常重要的", "极其关键的", "至关重要", "不可或缺",
    # 空洞形容
    "巨大的成功", "显著的提升", "广泛的关注", "深远的影响",
    # 其他 AI 味
    "不难发现", "由此可见", "毋庸置疑", "笔者认为", "据悉",
]

BANNED_ENDINGS = [
    "综上所述", "总而言之", "总之",
    "让我们拭目以待",
    "欢迎大家在评论区留言",
    "谢谢大家",
    "以上就是",
    "希望对大家有所帮助",
]


# ------ 金句库 ------

GOLDEN_QUOTES = [
    "创业不是选择题，是判断题。你只需要判断：这个事，我做不做。",
    "最贵的成本不是钱，是时间。其次贵的是选错方向浪费的时间。",
    "先做出来，再做好。大多数创业者死在'准备中'。",
    "技术选型的唯一标准：能不能在两周内交付第一版。其余都是噪音。",
    "代码写得好不如问题选得对。解决错误的问题，代码再优雅也是浪费。",
    "不要迷恋新技术。迷恋新问题。技术是手段，问题才是起点。",
    "好的架构不是设计出来的，是演化出来的。先跑通，再重构。",
    "AI 不会替代你。用 AI 的人会替代不用 AI 的人。",
    "提示词工程是个伪命题。真正的壁垒是你喂给 AI 的数据和你独特的判断力。",
    "当每个人都能用 AI 写代码的时候，'写代码'就不再是竞争力。理解需求才是。",
    "AI 的最大风险不是它太聪明，而是它太会说废话。你分不清有用和好听。",
    "每一篇文章都是一次交付。交付质量不够，下次没人打开你的推送。",
    "写作不是表达，是筛选。你把什么删掉，比你写了什么更重要。",
    "读者关心的永远不是你知道什么，而是他能用什么。",
    "数据是最好的说服力。'效果很好'不如'转化率从 2% 涨到 7%'。",
    "效率不是做更多的事，是做对的事。然后把剩下的全砍掉。",
    "焦虑的解药是行动。不是思考，不是计划，是今天就开始做第一步。",
    "赚钱是手段，自由是目的。如果赚钱让你更不自由，那就走错了路。",
    "融资不是终点，是起跑线。跑不动的话，起跑线在哪都一样。",
]


# ------ 大纲生成 ------

def generate_outline(topic: str, angle: str = "") -> str:
    """生成符合 STYLE.md 的文章大纲"""
    
    # 随机选择 2 个金句
    quotes = random.sample(GOLDEN_QUOTES, min(2, len(GOLDEN_QUOTES)))
    
    outline = f"""# [标题：根据话题"{topic}"生成，不超过 30 字，要有钩子]

[Hook: 1-3 句，身份/场景切入 + 反直觉结论]
- 第一句必须有"我"或具体场景
- 前三句内必须制造冲突感
- 不超过 100 字

## [Before: 旧世界/传统做法]

[2-3 段描述当前现状和痛点]
- 用具体场景，不要抽象概念
- 给出具体数字（时间、金额、比例）

> 💡 **{quotes[0]}**

## [After: 新发现/新方法/新趋势]

[2-3 段描述变化和新方式]
- 对比 Before，突出差异
- 给出数据支撑

[📷 这里放一张关于 {topic} 的对比图或流程图]

### 实操要点

1. [具体可执行的步骤 1]
2. [具体可执行的步骤 2]
3. [具体可执行的步骤 3]

## [Proof: 真实数据/案例]

| 指标 | Before | After |
|------|--------|-------|
| [指标1] | [旧数据] | [新数据] |
| [指标2] | [旧数据] | [新数据] |

> 💡 **{quotes[1]}**

## [结尾：弹射式收束]

[1-2 句，给行动建议或犀利反问]
- 不要用"综上所述"、"总之"
- 要像弹弓——蓄力、弹射、读者还在往前飞

---

## 写作指令

- **话题**: {topic}
- **切入角度**: {angle or '根据素材自行判断'}
- **目标字数**: 2000-3000 字
- **语气**: 专业但有温度，像跟同行聊天
- **必须包含**: 具体数据、before/after 对比、至少一个代码块或操作步骤
- **严禁使用**: {', '.join(BANNED_WORDS[:10])} 等空泛词汇
- **结尾**: 行动建议或犀利反问，禁止使用"综上所述"式结尾
"""
    
    return outline


def generate_r1_prompt(topic: str, angle: str = "", material: str = "") -> str:
    """生成给 R1 的完整写作 prompt"""
    
    # 读取 SOUL 和 STYLE
    soul_content = ""
    style_content = ""
    
    if os.path.exists(SOUL_FILE):
        with open(SOUL_FILE, "r", encoding="utf-8") as f:
            soul_content = f.read()
    
    if os.path.exists(STYLE_FILE):
        with open(STYLE_FILE, "r", encoding="utf-8") as f:
            style_content = f.read()
    
    outline = generate_outline(topic, angle)
    
    prompt = f"""你是一个资深的行业分析师和技术专家。请根据以下规范和大纲，撰写一篇深度文章。

===== 人设与边界 (SOUL) =====
{soul_content}

===== 写作风格 (STYLE) =====
{style_content}

===== 文章大纲 =====
{outline}
"""
    
    if material:
        prompt += f"""
===== 参考素材 =====
{material}
"""
    
    prompt += """
===== 输出要求 =====
1. 直接输出 Markdown 正文，不要输出"好的"、"以下是"等废话
2. 严格按照大纲结构写，但标题要换成具体的、有吸引力的文字
3. 每 500 字左右插入一个视觉锚点（金句引用、数据表格、代码块、或图片占位符）
4. 字数控制在 2000-3000 字
5. 所有不确定的数据标注 [⚠️ 待核实]
"""
    
    return prompt


# ------ 后处理 ------

def post_process(content: str, topic: str) -> Tuple[str, List[str]]:
    """
    后处理 R1 输出的原始稿件。
    返回 (处理后的内容, 警告列表)
    """
    warnings = []
    processed = content
    
    # 1. 禁用词检测
    found_banned = []
    for word in BANNED_WORDS:
        if word in processed:
            found_banned.append(word)
            # 不自动删除，标注出来让人工处理
            processed = processed.replace(word, f"~~{word}~~[⛔ 禁用词]")
    
    if found_banned:
        warnings.append(f"发现 {len(found_banned)} 个禁用词: {', '.join(found_banned)}")
    
    # 2. 检查结尾
    last_200 = processed[-200:]
    for ending in BANNED_ENDINGS:
        if ending in last_200:
            warnings.append(f"结尾使用了禁止结尾词: '{ending}'，请手动修改为弹射式结尾")
    
    # 3. 检查视觉锚点密度
    total_chars = len(processed)
    anchor_count = (
        processed.count("> 💡") +
        processed.count("> ⚠️") +
        processed.count("```") // 2 +
        processed.count("[📷") +
        processed.count("| ")  # 表格
    )
    
    expected_anchors = max(1, total_chars // 500)
    if anchor_count < expected_anchors:
        warnings.append(f"视觉锚点不足: 当前 {anchor_count} 个，建议至少 {expected_anchors} 个")
        # 自动插入金句锚点
        processed = _insert_golden_quotes(processed, expected_anchors - anchor_count)
    
    # 4. 检查段落长度
    paragraphs = [p.strip() for p in processed.split("\n\n") if p.strip()]
    long_paragraphs = [i for i, p in enumerate(paragraphs) if len(p) > 300 and not p.startswith("```") and not p.startswith("|")]
    if long_paragraphs:
        warnings.append(f"有 {len(long_paragraphs)} 个段落过长（>300字），建议拆分")
    
    # 5. 检查标题层级
    h1_count = len(re.findall(r'^# [^#]', processed, re.MULTILINE))
    if h1_count > 1:
        warnings.append(f"有 {h1_count} 个 H1 标题，建议只保留 1 个")
    
    # 6. 确保代码块有语言标注
    bare_code_blocks = re.findall(r'^```\s*$', processed, re.MULTILINE)
    if bare_code_blocks:
        warnings.append(f"有 {len(bare_code_blocks)} 个代码块未标注语言")
    
    # 7. 添加元数据
    metadata = f"""
---

> 📝 **文章信息**
> - 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}
> - 主题: {topic}
> - 字数: ~{len(processed)} 字
> - 状态: **初稿 — 需要人工审核**

> ⚠️ **审核清单**
> - [ ] 核实所有数据和数字
> - [ ] 检查人名和公司名的准确性
> - [ ] 补充个人经历和见解
> - [ ] 替换图片占位符 [📷]
> - [ ] 调整语气和风格
> - [ ] 确认结尾足够"弹射"
"""
    
    if warnings:
        metadata += "> \n> **⚠️ 自动检测到的问题:**\n"
        for w in warnings:
            metadata += f"> - {w}\n"
    
    processed += "\n" + metadata
    
    return processed, warnings


def _insert_golden_quotes(content: str, count: int) -> str:
    """在适当位置插入金句锚点"""
    available_quotes = random.sample(GOLDEN_QUOTES, min(count, len(GOLDEN_QUOTES)))
    
    paragraphs = content.split("\n\n")
    insert_interval = max(1, len(paragraphs) // (count + 1))
    
    inserted = 0
    result = []
    
    for i, para in enumerate(paragraphs):
        result.append(para)
        
        if (i + 1) % insert_interval == 0 and inserted < len(available_quotes):
            # 不在标题后面、代码块中间、或已有锚点旁插入
            if not para.startswith("#") and not para.startswith("```") and "> 💡" not in para:
                result.append(f"\n> 💡 **{available_quotes[inserted]}**\n")
                inserted += 1
    
    return "\n\n".join(result)


# ------ 主函数 ------

def main():
    parser = argparse.ArgumentParser(description="深度撰写模块")
    parser.add_argument("--topic", help="选题标题")
    parser.add_argument("--angle", default="", help="切入角度")
    parser.add_argument("--raw", help="R1 输出的原始稿件路径（后处理模式）")
    parser.add_argument("--material", help="参考素材文件路径")
    parser.add_argument("--output", help="输出文件路径")
    parser.add_argument("--outline-only", action="store_true", help="仅生成大纲")
    parser.add_argument("--prompt-only", action="store_true", help="仅生成 R1 prompt")
    
    args = parser.parse_args()
    
    if args.raw:
        # 模式 A: 后处理
        if not os.path.exists(args.raw):
            print(f"❌ 文件不存在: {args.raw}", file=sys.stderr)
            sys.exit(1)
        
        with open(args.raw, "r", encoding="utf-8") as f:
            raw_content = f.read()
        
        topic = args.topic or "未指定"
        processed, warnings = post_process(raw_content, topic)
        
        print(f"✅ 后处理完成")
        print(f"   原始字数: {len(raw_content)}")
        print(f"   处理后字数: {len(processed)}")
        
        if warnings:
            print(f"\n⚠️ 检测到 {len(warnings)} 个问题:")
            for w in warnings:
                print(f"   - {w}")
        
        output_content = processed
    
    elif args.outline_only:
        # 模式 B: 仅大纲
        if not args.topic:
            print("❌ 需要 --topic 参数", file=sys.stderr)
            sys.exit(1)
        
        outline = generate_outline(args.topic, args.angle)
        print("📝 大纲生成完成:")
        output_content = outline
    
    elif args.prompt_only:
        # 生成 R1 prompt
        if not args.topic:
            print("❌ 需要 --topic 参数", file=sys.stderr)
            sys.exit(1)
        
        material = ""
        if args.material:
            with open(args.material, "r", encoding="utf-8") as f:
                material = f.read()
        
        prompt = generate_r1_prompt(args.topic, args.angle, material)
        output_content = prompt
    
    else:
        # 默认: 生成大纲 + 提示调用 R1
        if not args.topic:
            print("❌ 需要 --topic 或 --raw 参数", file=sys.stderr)
            sys.exit(1)
        
        material = ""
        if args.material:
            with open(args.material, "r", encoding="utf-8") as f:
                material = f.read()
        
        # 生成 R1 prompt 并保存
        prompt = generate_r1_prompt(args.topic, args.angle, material)
        prompt_path = "/tmp/nanobot/r1_prompt.md"
        os.makedirs(os.path.dirname(prompt_path), exist_ok=True)
        with open(prompt_path, "w", encoding="utf-8") as f:
            f.write(prompt)
        
        print(f"📝 写作 Prompt 已生成: {prompt_path}")
        print()
        print("下一步 (V3 请执行):")
        print(f"  python /app/skills/llm-processor/scripts/llm_process.py custom \\")
        print(f"    --prompt \"请根据以下指令撰写文章\" \\")
        print(f"    --file {prompt_path} \\")
        print(f"    --output /tmp/nanobot/draft_raw.md")
        print()
        print("R1 输出后，再调用后处理:")
        print(f"  python draft.py --raw /tmp/nanobot/draft_raw.md --topic \"{args.topic}\" --output /tmp/nanobot/draft_final.md")
        
        output_content = prompt
    
    # 输出
    if args.output:
        os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output_content)
        print(f"\n📄 已保存到: {args.output} ({len(output_content)} 字)")
    elif not args.raw:
        # 非后处理模式，打印到 stdout
        print()
        print(output_content)


if __name__ == "__main__":
    main()
