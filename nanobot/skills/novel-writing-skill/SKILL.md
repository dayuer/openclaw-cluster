---
name: novel-writing-skill
description: >
  AI 辅助小说创作。使用自有算力 DeepSeek-R1 生成小说内容（不消耗官方 API），支持多种风格和章节管理。
  用于“帮我写小说”、“创作故事”、“续写章节”、“小说润色”等场景。
  不用于非虚构类写作（如报告、文档、新闻，请用 content-pipeline）。
author: Survival Team
version: 1.1.0
created: 2026-02-01
updated: 2026-02-15
agents: [general]
---

# Novel Writing Skill

AI 辅助小说创作 — 使用**自有算力 R1** 生成内容，不消耗官方 API 额度。

## 使用方法

### 生成小说段落

```bash
# 生成一个章节
python /app/skills/llm-processor/scripts/llm_process.py custom \
  --prompt "请创作一个武侠小说的开头章节，主角是一个流浪剑客，场景是雨夜的客栈。要求：字数约800字，注重氛围描写和人物刻画，语言风格参考金庸。" \
  --text "占位" \
  --output /tmp/nanobot/chapter1.md
```

### 续写故事

```bash
# 先把已有内容写入文件
# 然后基于已有内容续写
python /app/skills/llm-processor/scripts/llm_process.py custom \
  --prompt "请基于以下已有内容，续写下一个场景（约500字）。保持人物性格和语言风格一致。" \
  --file /tmp/nanobot/chapter1.md \
  --output /tmp/nanobot/chapter2.md
```

### 改写/润色

```bash
python /app/skills/llm-processor/scripts/llm_process.py custom \
  --prompt "请润色以下小说段落，增强场景描写和对话感染力，保持原有情节不变。" \
  --file /tmp/nanobot/draft.md \
  --output /tmp/nanobot/polished.md
```

## 典型工作流

### 创作完整章节 + 发布飞书

1. **V3 规划**: 根据用户描述，规划章节大纲
2. **R1 创作**: 用 llm-processor 生成每个章节内容
3. **R1 润色**: 用 llm-processor 改写润色
4. **V3 发布**: 用 feishu 创建飞书文档

```bash
# Step 1: R1 创作第一章
python /app/skills/llm-processor/scripts/llm_process.py custom \
  --prompt "创作武侠小说《断剑》第一章'雨夜客栈'，800字..." \
  --text "风格:金庸 主角:流浪剑客楚天阔 场景:深山客栈" \
  --output /tmp/nanobot/chapter1.md

# Step 2: 创建飞书文档发布
python /app/skills/feishu/scripts/feishu.py create_doc \
  --title "《断剑》第一章 雨夜客栈" \
  --file /tmp/nanobot/chapter1.md

# Step 3: 清理
rm -rf /tmp/nanobot/*
```

## 支持的风格

通过在 prompt 中指定风格：

- 武侠 (金庸/古龙风格)
- 科幻 (刘慈欣风格)
- 言情 (现代都市)
- 悬疑 (推理探案)
- 奇幻 (西方/东方奇幻)

## ⚠️ 避坑指南

> 每一次失败都变成这里的一条规则。

- 本 skill 依赖 `llm-processor` skill，通过 R1 自有算力生成内容
- R1 推理较慢，一个章节约需 30-60 秒
- 每次生成建议控制在 **1000 字以内**，超长内容分段创作
- 临时文件放 `/tmp/nanobot/`，完成后清理
- 人物强一致性是难点，续写时始终把已有内容作为上下文传入

## 依赖

| Skill / 工具    | 用途             |
| --------------- | ---------------- |
| `llm-processor` | 调用 R1 生成内容 |
| `feishu`        | 发布到飞书文档   |

## 演化日志

| 日期       | 版本  | 变更                                 | 触发原因       |
| ---------- | ----- | ------------------------------------ | -------------- |
| 2026-02-15 | 1.1.0 | name 对齐目录名，对齐 SKILL-STANDARD | 标准化统一优化 |
| 2026-02-01 | 1.0.0 | 初始版本                             | —              |
