---
name: web-scraper
description: >
  获取网页数据并转为干净 Markdown/JSON。支持正文智能提取、链接/图片/元数据提取、CSS 选择器精确定位。
  用于“抓取网页”、“读取这个链接”、“提取页面内容”、“爬取文章”等场景。
  不用于 JavaScript 动态渲染页面或需要登录的页面。
author: Survival Team
version: 1.1.0
created: 2026-01-15
updated: 2026-02-15
agents: [general]
---

# Web Scraper Skill

轻量级网页数据提取工具，专为 AI Agent 设计。获取页面内容并自动清理为可读的 Markdown 格式。

## 使用方法

### 获取页面正文（最常用）

```bash
python /app/skills/web-scraper/scripts/scrape.py "https://example.com"
```

自动使用 readability 算法提取正文，去除导航栏、广告、侧边栏等噪声。

### 提取所有链接

```bash
python /app/skills/web-scraper/scripts/scrape.py "https://example.com" --mode links
```

### 提取所有图片

```bash
python /app/skills/web-scraper/scripts/scrape.py "https://example.com" --mode images
```

### 获取页面元数据（标题、描述、关键词）

```bash
python /app/skills/web-scraper/scripts/scrape.py "https://example.com" --mode meta
```

### 完整结构化数据（JSON 格式）

```bash
python /app/skills/web-scraper/scripts/scrape.py "https://example.com" --mode full
```

### 用 CSS 选择器精确提取

```bash
# 提取文章正文区域
python /app/skills/web-scraper/scripts/scrape.py "https://example.com" --selector "article .content"

# 提取价格列表
python /app/skills/web-scraper/scripts/scrape.py "https://example.com" --selector ".price-list li"
```

### 保存到文件

```bash
python /app/skills/web-scraper/scripts/scrape.py "https://example.com" -o /tmp/nanobot/page.md
```

## 参数说明

| 参数           | 说明                                       | 默认值        |
| -------------- | ------------------------------------------ | ------------- |
| `url`          | 目标 URL                                   | 必填          |
| `--mode`       | 提取模式: text/html/links/images/full/meta | text          |
| `--selector`   | CSS 选择器 (覆盖 mode)                     | 无            |
| `-o, --output` | 保存到文件路径                             | 输出到 stdout |
| `--ua`         | 自定义 User-Agent                          | Chrome UA     |
| `--timeout`    | 超时秒数                                   | 30            |
| `--json`       | links/images 模式使用 JSON 输出            | 否            |

## 提取模式说明

| 模式     | 输出            | 适合场景           |
| -------- | --------------- | ------------------ |
| `text`   | 正文 Markdown   | 读文章、分析内容   |
| `html`   | 原始 HTML       | 需要完整页面       |
| `links`  | 所有链接列表    | 发现子页面、导航   |
| `images` | 所有图片列表    | 素材收集           |
| `meta`   | 页面元数据 JSON | SEO 分析、快速预览 |
| `full`   | 完整结构化 JSON | 综合分析           |

## ⚠️ 避坑指南

> 每一次失败都变成这里的一条规则。

- 本工具只能抓取**静态渲染**的页面，JavaScript 动态加载的内容无法获取
- 对于需要登录的页面，需要先通过其他方式获取 Cookie
- 请尊重网站的 robots.txt 和使用条款
- 建议先用 `--mode meta` 预览页面信息，再决定用什么模式提取
- 部分网站会屏蔽默认 UA，遇到 403 时尝试用 `--ua` 自定义 User-Agent

## 双模型集成

抓取内容后如需翻译/摘要/分析，优先使用 `llm-processor` skill（R1 自有算力）：

```bash
# 1. 抓取英文文章
python /app/skills/web-scraper/scripts/scrape.py "https://..." -o /tmp/nanobot/raw.md

# 2. R1 翻译为中文
python /app/skills/llm-processor/scripts/llm_process.py translate \
  --file /tmp/nanobot/raw.md --target zh --output /tmp/nanobot/zh.md

# 3. 创建飞书文档
python /app/skills/feishu/scripts/feishu.py create_doc \
  --title "xxx" --file /tmp/nanobot/zh.md
```

## 演化日志

| 日期       | 版本  | 变更                     | 触发原因       |
| ---------- | ----- | ------------------------ | -------------- |
| 2026-02-15 | 1.1.0 | 对齐 SKILL-STANDARD 规范 | 标准化统一优化 |
| 2026-01-15 | 1.0.0 | 初始版本                 | —              |
