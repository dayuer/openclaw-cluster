# 🏢 Nanobot 多 Agent 团队

> **架构**: 14 个独立 Agent，每个有独立人格、工具集和知识库
> **配置**: `agents.yaml` (项目根目录)

---

## 架构

```
              agents.yaml (14 agents)
                      │
    ┌─────────────────┼─────────────────┐
    ▼                 ▼                 ▼
 顾问团 (11)       销售 (3)          分析 (1)
 general          xiaomi            analytics
 legal            acheng
 mechanic         guanjia
 health
 algo
 metaphysics
 insurance
 food
 rescue
 service
 ucar
```

**每个 Agent 独立拥有:**

- `system_prompt_file` → 角色人格 (来自 `team/roles/{id}.md`)
- `tools` → 工具白名单
- `temperature` / `max_tokens` → 模型参数
- `knowledge` → RAG 知识库 (`agents/{id}/knowledge/`)

**路由**: `role_id == agent_id`，无间接映射

---

## 顾问团 (→ 11 Agents)

| Agent         | 角色   | 人设       | 核心工具        |
| ------------- | ------ | ---------- | --------------- |
| `general`     | 翔哥   | 十年老司机 | `*` (全部)      |
| `legal`       | 叶律   | 铁嘴大状   | knowledge, web  |
| `mechanic`    | 老周   | 修车神医   | knowledge, web  |
| `health`      | 林姨   | 唠叨神医   | knowledge, web  |
| `algo`        | 阿K    | 算法黑客   | data, knowledge |
| `metaphysics` | 裴大师 | 玄学高人   | user_memory     |
| `insurance`   | 严公估 | 理赔推土机 | knowledge, web  |
| `food`        | 饭桶哥 | 觅食向导   | web             |
| `rescue`      | 猛哥   | 救援战神   | notify          |
| `service`     | 小灵通 | 车务管家   | knowledge, web  |
| `ucar`        | 小优优 | 车辆顾问   | knowledge, web  |

## 销售团队 (→ 3 Agents)

| Agent     | 角色     | 人格     | 核心工具      |
| --------- | -------- | -------- | ------------- |
| `xiaomi`  | 获客专员 | 热情主动 | sales, notify |
| `acheng`  | 销售顾问 | 专业耐心 | sales, notify |
| `guanjia` | 售后管家 | 温暖细心 | sales, notify |

## 分析 (→ 1 Agent)

| Agent       | 职责          | 核心工具               |
| ----------- | ------------- | ---------------------- |
| `analytics` | 数据看板/报表 | data, stock, knowledge |

---

## 目录

```
workspace/team/
├── TEAM.md              ← 你正在读的这个文件
└── roles/               ← 角色人格定义 (被 system_prompt_file 引用)
    ├── general.md
    ├── legal.md
    ├── ...
    └── analytics.md
```
