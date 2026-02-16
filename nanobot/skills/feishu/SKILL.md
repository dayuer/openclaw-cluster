---
name: feishu
description: >
  企业级飞书集成工具 — 文档创建/读取/更新、文件上传/下载、空间管理、模板批量创建。
  用于“创建飞书文档”、“上传到飞书”、“飞书日报”、“搜索飞书文档”等场景。
  不用于企业微信、钉钉或其他 IM 平台操作。
author: Survival Team
version: 1.1.0
created: 2026-01-15
updated: 2026-02-15
agents: [general]
---

# 🚀 飞书集成工具 (feishu)

## 使用方法

```bash
python /app/skills/feishu/scripts/feishu.py <command> [参数]
```

## 📄 文档操作

| command      | 说明         | 必需参数                              |
| ------------ | ------------ | ------------------------------------- |
| `create_doc` | 创建文档     | `--title`, `--content` 或 `--file`    |
| `append_doc` | 追加内容     | `--doc_id`, `--content` 或 `--file`   |
| `get_doc`    | 获取文档信息 | `--doc_id`                            |
| `delete_doc` | 删除文档     | `--doc_id`                            |
| `share_doc`  | 生成分享链接 | `--doc_id`, `--permission`(view/edit) |
| `search_doc` | 搜索文档     | `--query`, `--limit`(可选)            |

```bash
# 从 Markdown 文件创建文档
python feishu.py create_doc --title "运营日报" --file /tmp/nanobot/report.md

# 往已有文档追加内容
python feishu.py append_doc --doc_id "Dqc6dRx..." --content "## 新增章节"

# 搜索文档
python feishu.py search_doc --query "运营日报" --limit 5
```

## 📁 文件操作

| command         | 说明     | 必需参数                          |
| --------------- | -------- | --------------------------------- |
| `upload_file`   | 上传文件 | `--file_path`, `--folder`(可选)   |
| `download_file` | 下载文件 | `--file_token`, `--output`        |
| `list_files`    | 列出文件 | `--folder`(可选)                  |
| `move_file`     | 移动文件 | `--file_token`, `--target_folder` |
| `delete_file`   | 删除文件 | `--file_token`                    |

```bash
# 上传文件到指定文件夹
python feishu.py upload_file --file_path /data/report.pdf --folder "fldcn123..."

# 下载文件
python feishu.py download_file --file_token "boxcn456..." --output /tmp/output.pdf
```

## 🗂️ 空间管理

| command         | 说明       | 必需参数                   |
| --------------- | ---------- | -------------------------- |
| `create_folder` | 创建文件夹 | `--name`, `--parent`(可选) |
| `list_folders`  | 列出文件夹 | `--parent`(可选)           |

## 🤖 自动化

| command          | 说明         | 必需参数                           |
| ---------------- | ------------ | ---------------------------------- |
| `batch_create`   | 批量创建文档 | `--template`, `--data_file` (JSON) |
| `list_templates` | 列出可用模板 | 无                                 |

模板支持变量: `{{date}}`, `{{time}}`, `{{datetime}}`, `{{data.xxx}}`

```bash
# 批量创建日报
python feishu.py batch_create --template daily_report --data_file /tmp/stats.json
```

## 🔧 其他

| command           | 说明         |
| ----------------- | ------------ |
| `test_connection` | 测试飞书连接 |

## 📦 Markdown 格式支持

文档内容支持以下 Markdown 语法，自动转换为飞书块:

- 标题 `# ~ ######`、段落、无序/有序列表
- 代码块、引用、分割线、表格
- 行内格式: **粗体**, _斜体_, **_粗斜体_**, `行内代码`, ~~删除线~~, [链接](url)

## 📁 目录结构

```
feishu/
├── SKILL.md
├── scripts/
│   ├── feishu.py          # CLI 入口 (17 个命令)
│   ├── feishu_api.py      # API 封装 + Token 管理
│   ├── feishu_doc.py      # 文档操作 + Markdown 解析
│   ├── feishu_file.py     # 文件上传/下载/管理
│   ├── feishu_space.py    # 空间/文件夹管理
│   └── feishu_auto.py     # 模板系统 + 批量操作
├── config/
│   └── config.example.yaml
└── templates/
    └── daily_report.md    # 日报模板示例
```

## ⚙️ 配置

优先使用环境变量 `FEISHU_APP_ID` / `FEISHU_APP_SECRET`，  
也可复制 `config/config.example.yaml` → `config/config.yaml` 填入凭证。

调试模式: `export FEISHU_DEBUG=1`

## ⚠️ 避坑指南

> 每一次失败都变成这里的一条规则。

- 文档内容必须是合法 Markdown，原始 HTML 会被过滤
- `doc_id` 和 `file_token` 是不同的标识符，不要混淆
- 批量操作前先用 `test_connection` 确认连接正常
- Token 过期报错时，脚本会自动刷新，不需要手动处理

## 演化日志

| 日期       | 版本  | 变更                     | 触发原因       |
| ---------- | ----- | ------------------------ | -------------- |
| 2026-02-15 | 1.1.0 | 对齐 SKILL-STANDARD 规范 | 标准化统一优化 |
| 2026-01-15 | 1.0.0 | 初始版本                 | —              |
