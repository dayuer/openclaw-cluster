---
name: llm-processor
description: >
  使用自有算力 DeepSeek-R1 处理文本任务（翻译、摘要、改写、分析）。不消耗官方 API 额度。
  用于“翻译这篇文章”、“帮我总结”、“改写这段文字”、“用 R1 处理”等场景。
  不适合 tool calling 任务（那是 V3 的工作）。
author: Survival Team
version: 1.1.0
created: 2026-01-15
updated: 2026-02-15
agents: [general]
---

# LLM Processor Skill (自有算力)

调用自有服务器上的 DeepSeek-R1 处理纯文本任务。**不消耗官方 API 额度**。

> **分工原则**: 你（V3）负责 tool calling 调度，R1 负责翻译/摘要/改写等内容处理。

## 使用方法

### 翻译（最常用）

```bash
# 翻译文本
python /app/skills/llm-processor/scripts/llm_process.py translate \
  --text "Some English text to translate" --target zh

# 翻译文件
python /app/skills/llm-processor/scripts/llm_process.py translate \
  --file /tmp/nanobot/article.md --target zh --output /tmp/nanobot/article_zh.md
```

### 摘要

```bash
python /app/skills/llm-processor/scripts/llm_process.py summarize \
  --file /tmp/nanobot/article.md --style bullet
```

style 选项: `bullet`(要点列表), `paragraph`(段落), `oneline`(一句话)

### 自定义 Prompt

```bash
python /app/skills/llm-processor/scripts/llm_process.py custom \
  --prompt "请分析以下新闻的行业影响" \
  --file /tmp/nanobot/news.md
```

## 典型工作流

### 新闻翻译 + 飞书文档

1. 用 web-scraper 抓取英文新闻
2. 用 llm-processor 翻译成中文 ← **R1 处理，零 API 消耗**
3. 用 feishu 生成飞书文档

```bash
# Step 1: 抓取
python /app/skills/web-scraper/scripts/scrape.py "https://..." -o /tmp/nanobot/raw.md

# Step 2: 翻译
python /app/skills/llm-processor/scripts/llm_process.py translate \
  --file /tmp/nanobot/raw.md --target zh --output /tmp/nanobot/translated.md

# Step 3: 创建飞书文档
python /app/skills/feishu/scripts/feishu.py create_doc \
  --title "新闻简报" --file /tmp/nanobot/translated.md
```

## ⚠️ 避坑指南

> 每一次失败都变成这里的一条规则。

- 使用自有算力服务器 (115.190.110.32:5000)，**需要服务器在线**
- 超时设置为 120 秒（R1 模型推理较慢），超长文本可能超时
- 自动清理 R1 输出中的 `<think>` 标签，不需要手动处理
- 不适合需要 tool calling 的任务（那是 V3 的工作）
- 输入文本太长时，先分段再调用，否则可能截断

## 演化日志

| 日期       | 版本  | 变更                     | 触发原因       |
| ---------- | ----- | ------------------------ | -------------- |
| 2026-02-15 | 1.1.0 | 对齐 SKILL-STANDARD 规范 | 标准化统一优化 |
| 2026-01-15 | 1.0.0 | 初始版本                 | —              |
