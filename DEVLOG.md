# Kylopro-Nexus 开发日志

> **用途**：跨对话上下文记忆。新对话读 README.md 了解架构，再读本文件最新 Phase 恢复进度。
> **项目位置**：`c:\Users\qianchen\Desktop\nanobot\Kylopro-Nexus\`
> **nanobot 工作区**：`c:\Users\qianchen\Desktop\nanobot\Kylopro-Nexus\workspace\`
> **完整历史备份**：`DEVLOG.md.bak`

---

## Phase 1~3.2 摘要 (2026-03-06 ~ 2026-03-07)

> 详细记录见 `DEVLOG.md.bak`

| Phase | 内容 | 关键产出 |
|-------|------|----------|
| 1 | 环境搭建、双核路由原型 | core/provider.py, core/engine.py, setup.bat |
| 1.x | 灵魂缺失导致复读机 | 发现需要 SOUL.md 注入人格 |
| 2 | 脑肢协同修复 | core/tools.py, AgentLoop 工具注册, TaskInbox 自动运行 |
| 2.5 | MiniMax 切换 + ReAct/路由器原型 | 发现 Kylopro vs nanobot 调用链断裂，确定"融入 nanobot"方向 |
| 3 | nanobot 深度融合 | config.json 统一, workspace/tools_init.py, core/kylopro_tools.py, TaskBridge |
| 3.1 | 上游监测 + 自开发框架约束 | P5/P6 任务创建, AGENTS.md 规则 |
| 3.2 | P7 架构收敛 | 删 49 文件, core/ 精简为 3 文件, bat 脚本修复, 双进程冲突发现与修复 |

**Phase 1~3.2 关键决策**：
- 废弃 Kylopro 自研 provider/engine/react_loop，全部迁入 nanobot 原生链路
- 统一配置源为 `~/.nanobot/config.json`
- 工作区指向 `Kylopro-Nexus/workspace/`，开启 restrictToWorkspace
- 生产入口统一为 `nanobot gateway`（venv 环境）
- 发现并修复双进程冲突（AppData Python312 vs venv）

---

## Phase 4 — 2026-03-07 (模型稳定性 + 调度架构)

### 背景

Phase 3 清理后重启网关，发现两个问题：
1. MiniMax 模型在多轮工具调用后回退为文本输出 `functions.task_write({...})`
2. MiniMax 触发 429 TPM rate limit，错误直接以原始 JSON 发给用户

### 根因分析

**文本化工具调用**：MiniMax 第一轮正确返回 `tool_calls` API 调用，但工具执行后的第二轮迭代中回退为文本输出。一旦文本进入 session 历史，后续对话全部被污染。

**429 限流**：Provider 层没有任何 retry/fallback 逻辑。

### 修复内容

#### 1. 文本工具调用拦截器 (`nanobot/agent/loop.py` + `subagent.py`)

在 `_run_agent_loop` 的 else 分支（模型没返回 tool_calls 时）：
- 检测回复文本中的 `functions.xxx({...})` 模式
- 匹配到已注册工具 → 解析参数 → 执行工具 → `continue` 循环
- 未匹配 → 正常作为最终回复输出
- 子 Agent 循环同步应用

#### 2. Provider retry + fallback (`nanobot/providers/litellm_provider.py`)

```
primary model
  ↓ 429 rate limit
retry: 5s backoff + 重试 1 次
  ↓ 仍然失败
fallback model (自动切换)
```

#### 3. AgentLoop 错误处理

provider 返回 `finish_reason="error"` → 友好提示，不发原始错误文本。

#### 4. 主 Agent 调度模式 (`AGENTS.md`)

新增章节：主 Agent 调度模式、直接执行 vs spawn 判断、回复风格规则。

### 修改文件清单

| 文件 | 改动 |
|------|------|
| `nanobot/providers/litellm_provider.py` | retry + fallback，新增 fallback 参数 |
| `nanobot/agent/loop.py` | 文本拦截器 + error 处理 |
| `nanobot/agent/subagent.py` | 文本拦截器 + error 处理 |
| `nanobot/config/schema.py` | `AgentDefaults.fallback_model` |
| `nanobot/cli/commands.py` | `_make_provider()` 传递 fallback |
| `workspace/AGENTS.md` | 调度模式 + 回复风格 |

### 验证结果

- 95 个 nanobot 测试全部通过
- 文本拦截器 6 个场景测试通过

---

## Phase 5 — 2026-03-08 (模型切回 DeepSeek + 阶梯调度设计)

### 背景

MiniMax 作为主力模型在生产环境持续出现两个致命问题：
1. **429 TPM 限流**：在 Telegram 多轮对话中频繁触发，经 MiniMax 官方确认为 API 速率限制
2. **文本化工具调用**：尽管 Phase 4 已实现拦截器，但 MiniMax 的工具调用稳定性仍不如 DeepSeek

决策：**将主力模型切回 DeepSeek-chat，MiniMax 降级为 fallback**。

### 变更内容

#### 1. config.json 模型切换

```json
// 之前
"model": "minimax/abab6.5s-chat",
"provider": "minimax",
"fallbackModel": "deepseek/deepseek-chat"

// 之后
"model": "deepseek/deepseek-chat",
"provider": "deepseek",
"fallbackModel": "minimax/abab6.5s-chat"
```

#### 2. 三层模型阶梯调度设计

| 层级 | 模型 | 用途 | 触发方式 |
|------|------|------|----------|
| L1 主力 | `deepseek/deepseek-chat` | 日常对话、任务调度、工具调用 | 默认 |
| L2 深度 | `deepseek/deepseek-reasoner` | 架构设计、根因分析、多步规划 | `deep_think` 工具 |
| L3 辅助 | `minimax/abab6.5s-chat` | DeepSeek 限流时自动切换 | Provider fallback |

#### 3. 文档全面更新

| 文件 | 改动 |
|------|------|
| `~/.nanobot/config.json` | model/provider/fallback 互换 |
| `workspace/SOUL.md` | 多模型大脑描述更新为 DeepSeek 主力 |
| `workspace/AGENTS.md` | 新增"模型阶梯调度规则"章节，更新优先级 |
| `README.md` | 完全重写：架构图、模型调度、工具清单、目录结构、文件索引、新对话恢复指南 |
| `DEVELOPMENT_ROADMAP.md` | 精简为当前状态（删除已完成的历史规划） |
| `tasks/` | 4 个已完成任务移至 done/（P0, P0.5, P1, P7） |

#### 4. Telegram 双进程冲突修复

Gateway 启动报 `telegram.error.Conflict: terminated by other getUpdates request`。
根因：4 个 Python 进程（2 个 venv + 2 个 AppData Python312）同时抢同一 bot token。
修复：全部杀掉 → 等 10s polling 超时 → 单一 venv 实例启动。

### 新对话恢复要点

1. `README.md` — 文件索引，了解按需读取哪些文件
2. `DEVLOG.md` 最后一个 Phase — 最新进度
3. `tasks/pending/` — 待办任务（5 项: P2, P3, P4, P5, P6）
4. `workspace/AGENTS.md` — 行为规则 + 阶梯调度

关键技术事实：
- 生产 Python：`c:\Users\qianchen\Desktop\nanobot\venv\Scripts\python.exe`
- nanobot 源码版（非 pip 安装版）
- 主力模型：`deepseek/deepseek-chat` + fallback `minimax/abab6.5s-chat`
- 深度推理：`deepseek/deepseek-reasoner`（通过 `deep_think` 工具）
- 文本拦截器在 `loop.py:_extract_text_tool_calls()` 和 `subagent.py`
- Session：`workspace/sessions/telegram_8534144265.jsonl`

---

## Phase 7 — 2026-03-08 (搜索集成 + 财务模块)

### 背景

用户无法注册 Brave Search，改为接入 Tavily（专为 AI Agent 优化）+ DuckDuckGo（免费无限）。
同时用户提出"财务模块"需求：追踪 API 用量、月度配额管理、按每周人民币限额控制行为。

### 三层搜索策略

```
需要搜索 → Tavily（月 1000 次免费，高质量摘要）
            ↓ 额度耗尽
          → DuckDuckGo（永久免费，无额度限制）
            ↓ 已知精确 URL
          → web_fetch（nanobot 原生，零成本）
```

### 新增文件

| 文件 | 说明 |
|------|------|
| `core/cost_tracker.py` | 财务追踪核心：Tavily 配额、模型 token 费用（人民币）、每周预算管理 |
| `data/local_config.json` | Tavily API key（gitignored） |
| `data/financial_config.json` | 预算配置：weekly_budget_rmb=20、阈值、模型定价 |
| `skills/cost-manager/SKILL.md` | 搜索后端选择规则、预算决策、主动汇报时机 |

### 新增工具（注册到 AgentLoop）

| 工具名 | 类 | 说明 |
|--------|------|------|
| `tavily_search` | `TavilySearchTool` | Tavily 搜索，自动检查配额 |
| `ddg_search` | `DuckDuckGoSearchTool` | DuckDuckGo 免费 fallback |
| `cost_check` | `CostCheckTool` | 查看 Tavily 剩余、预算余额、模型费用 |
| `set_weekly_budget` | `SetWeeklyBudgetTool` | 设置每周人民币预算 |

### 财务模块设计

**配额切换（自动）**：
- `TavilySearchTool.execute()` 在调用前检查 `tracker.tavily_remaining()`
- 额度不足时直接返回提示，让 Kylo 改调 `ddg_search`

**预算管理**：
- `CostTracker` 维护 `data/cost_state.json`（周重置 + 月重置）
- `budget_level()` 返回 ok / warn / stop
- 模型 token 费用通过 `record_token_usage()` 记录（当前需主动调用，框架层拦截待后续集成）

**定价参考（人民币/1K tokens）**：
- deepseek-chat: 输入 ¥0.002 / 输出 ¥0.008
- deepseek-reasoner: 输入 ¥0.004 / 输出 ¥0.016
- minimax: 输入/输出各 ¥0.001

### 修改文件

| 文件 | 操作 |
|------|------|
| `core/kylopro_tools.py` | 新增 import + 4 个工具类 + register 调用 |
| `docs/capability_map.md` | 更新搜索表（Tavily/DDG/web_fetch）+ 新增财务章节 |

### 安装包

```
tavily-python==0.7.22  ✅
duckduckgo-search==8.1.1  ✅
```

### 待跟进

- `CostTracker.record_token_usage()` 目前需主动调用；未来可在 `litellm_provider.py` response 拦截层自动记录
- DuckDuckGo 高频使用时有 IP 限速风险（Kylo 会在报错时提示等待 1 分钟）

---

## Phase 6 — 2026-03-08 (P2/P3/P4/P5/P6 规范化落地)

### 背景

Phase 5 完成模型切换与文档重写后，5 项待办任务（P2-P6）均停留在规划阶段。本 Phase 将这些任务中可独立于外部资源的部分一次性落地。

### 变更内容

#### P4 完成：技能整合收尾

更新 `skills/kylopro-dev/SKILL.md`：
- 修正 workspace 路径（已从 `workspace/` 子目录切为根目录）
- 新增"需求归属判断"五层决策流程
- 新增 nanobot 当前已知工具表（含 web_search/web_fetch/cron）
- 更正开发优先级顺序
- 添加"启动前杀 AppData Python312 进程"提醒

#### P2 完成：向量记忆实现

新建 `memory/memory_manager.py`:
- ChromaDB 持久化后端（存储到 `memory/vector_store/`）
- 嵌入模型：`paraphrase-multilingual-MiniLM-L12-v2`
- CLI 接口：`store | search | delete | list`
- 四类集合：`preference | decision | project_fact | code`
- 依赖：`pip install chromadb sentence-transformers`

更新 `skills/kylo-memory/SKILL.md`:
- 替换"预期接口"描述为完整 CLI 命令示例
- 明确两层记忆体系（nanobot 原生文本层 vs ChromaDB 向量层）
- 明确存储/检索时机与集合分类表

#### P6 完成：自开发框架文档化

新建 `docs/capability_map.md`:
- 完整能力映射表（文件操作/命令执行/子任务/深度推理/网络/记忆/IDE控制/消息）
- 资源申请规则表（缺 token/账号/程序/权限时的说明模板）
- 禁止模式清单（防止在旧 core/ 层堆功能、防止伪造资源、防止 GUI 优先）
- 新功能开发前置检查清单

#### P3 完成：Antigravity SKILL 增强

重写 `skills/antigravity/SKILL.md`：
- 完整三级降级策略：MCP → 命令行 → pyautogui bridge
- MCP server 配置模板（可直接复制到 config.json）
- 常见场景决策表
- GUI bridge CLI 接口规范（由 IDE 生成，Kylo 只调用）

#### P5 完成：首次上游监测

新建 `docs/reports/nanobot_upstream_20260308.md`：
- nanobot 当前所有模块状态清单
- 可立即复用的新能力（web_fetch 零配置可用，cron 可自动化，web_search 需 Brave key）
- Kylopro 自实现 vs 原生能力对比（无重叠，均为补充）
- 下次检查时间：2026-03-22

### 修改文件清单

| 文件 | 操作 |
|------|------|
| `skills/kylopro-dev/SKILL.md` | 全面更新 |
| `skills/kylo-memory/SKILL.md` | 重写为完整 CLI 规范 |
| `skills/antigravity/SKILL.md` | 重写为三级策略 |
| `memory/memory_manager.py` | 新建（ChromaDB CLI 工具） |
| `docs/capability_map.md` | 新建（能力映射决策表） |
| `docs/reports/nanobot_upstream_20260308.md` | 新建（首次监测报告） |

### 关键发现：web_fetch 可立即使用

nanobot 已在 loop.py 注册 `WebFetchTool`，无需任何额外配置。
Kylo 可以直接通过工具调用抓取任意 URL，适用于：
- GitHub changelog 抓取
- nanobot 上游文档检查
- 任务相关外部资源读取

### 待确认资源

- **Brave Search API key** — 已注册但未配置，激活 `web_search` 工具需要此 key
- **chromadb + sentence-transformers** — 向量记忆依赖，需在 venv 中安装

### 新对话恢复要点

1. `DEVLOG.md` Phase 6 — 本次所有变更
2. `docs/capability_map.md` — 开发前先查能力归属
3. `docs/reports/nanobot_upstream_20260308.md` — 上游监测基线
4. `tasks/pending/` — 5 项任务均已完成规范化，可推进实际安装和验证

---

## Phase 8 — 2026-03-08 (双脑架构 L0 本地模型)

### 背景与设计决策

用户提出：Kylo 有两个大脑——云 API 大脑和本地模型大脑。对于财务运算等"主要是 Python 执行"的任务，
应该用本地模型零成本处理，不消耗云 API 额度。同时梳理哪些技能可以交给本地模型。

**核心洞察**：对于财务运算/格式转换/日志分析，主体工作是 Python 代码执行，
本地 7B 模型（Ollama）完全能生成所需的简单 Python 脚本，无需 cloud API 推理。

### 四层大脑架构（Phase 8 后）

| 层级 | 标识 | 工具/模型 | 成本 | 用途 |
|------|------|---------|------|------|
| L0 | 本地脑 | `local_think` → Ollama qwen2.5-coder:7b | ¥0/次 | 财务运算、Python 脚本、格式转换、日志分析 |
| L1 | 主力脑 | deepseek-chat（当前会话 agent） | ¥/token | 用户对话、任务调度、工具协调 |
| L2 | 深度脑 | `deep_think` → deepseek-reasoner | ¥¥/token | 架构设计、Bug 根因、多步规划 |
| L3 | 备用脑 | minimax（Provider auto-fallback on 429） | ¥/token | L1 限流保护 |

### L0 适合的任务分类

**强制走 L0（mode=run_code）**：
- 财务运算（预算余额/百分比/token 费用）
- 文件格式转换（JSON/CSV/Markdown）
- 日志分析（统计/提取/清洗）
- 生成固定格式报告
- 日期/时间计算

**优先走 L0（mode=chat）**：
- 技术文档摘要（无私有上下文）
- 简单翻译
- 代码注释/Docstring 生成
- Shell 命令查询

**保留 L1/L2（不走 L0）**：
- 用户自然语言对话（需人格 SOUL.md）
- 涉及项目历史/记忆的问答
- 复杂架构设计（L2）
- 多工具协调任务

### 新增文件

| 文件 | 说明 |
|------|------|
| `skills/local-brain/SKILL.md` | L0 路由守则，always:true，定义 L0/L1/L2 决策规则 |

### 修改文件

| 文件 | 改动 |
|------|------|
| `core/kylopro_tools.py` | 新增 `LocalThinkTool` 类 + `register_kylopro_tools` 中注册 |
| `data/financial_config.json` | 新增 local/ollama 模型定价（¥0） |
| `docs/skills_evolution_roadmap.md` | v1.1: 新增 T0 本地脑部署章节，L0 工具已就绪 |

### LocalThinkTool 技术规范

```python
# 工具名: local_think
# Ollama endpoint: http://localhost:11434/api/generate
# 默认模型: qwen2.5-coder:7b
# 参数:
#   prompt    必填 — 请求内容
#   mode      chat（默认）| run_code  
#   model     可选，覆盖默认模型
#   context   可选，附加上下文

# run_code 模式流程:
# 1. 构建代码生成提示词（强制只输出代码块）
# 2. 调用 Ollama → 获取 response
# 3. 正则提取 ```python...``` 代码块
# 4. subprocess.run([sys.executable, "-c", code], timeout=30)
# 5. 返回 stdout，失败时返回 stderr + 生成代码
```

注意事项：
- Ollama 未运行时返回明确安装指引，不影响其他工具
- `sys.executable` = venv Python，代码在 workspace 目录下执行
- 超时设 30s，防止死循环

### 部署前置（用户操作）

```
1. 下载 Ollama: https://ollama.ai/download
2. 拉取模型: ollama pull qwen2.5-coder:7b
3. 验证: curl http://localhost:11434/api/tags
```

工具已就绪，Ollama 安装完后 Kylo 即可自动使用 L0 层。

### 工具总数

Phase 8 后 Kylopro 注册工具：**11 个**
```
task_inbox / deep_think / task_read / task_write / task_interrupt
tavily_search / ddg_search / cost_check / set_weekly_budget
local_think  ← 本 Phase 新增
```

### 新对话恢复要点

1. `DEVLOG.md` Phase 8 — 四层大脑架构、L0 工具、部署前置
2. `skills/local-brain/SKILL.md` — L0 路由规则
3. `docs/skills_evolution_roadmap.md` T0 — Ollama 部署步骤
4. `core/kylopro_tools.py` — `LocalThinkTool` 实现细节

---

## Phase 9 — 2026-03-08 (三模型精细化 + HeartbeatService 本地集成)

### 背景

用户实际安装了 5 个 Ollama 模型，Phase 8 框架设计用了不存在的 `qwen2.5-coder:7b`。
本 Phase 将框架精细化为实际安装的 3 个主力模型，并将 L0 与 nanobot 框架深度集成：
1. HeartbeatService `_decide` 阶段改用本地模型（零 API 成本心跳决策）
2. OllamaProvider 实现 nanobot `LLMProvider` 接口（无冗余引擎）
3. 三模型职责分工精确化

### 已安装 Ollama 模型清单

| 模型 | 大小 | 职责 |
|------|------|------|
| `qwen2.5:7b` | 4.7 GB | 通用对话、文档摘要、轻量决策、HeartbeatService skip/run |
| `deepseek-coder-v2:16b` | 8.9 GB | Python 代码生成、Shell 脚本、格式转换 |
| `deepseek-r1:latest` | 5.2 GB | 链式推理、财务分析、多步规划（含 `<think>` CoT）|
| `qwen3.5:latest` | 6.6 GB | 备用通用（最新 Qwen 系列，可替换 qwen2.5:7b）|
| `llama3.2:latest` | 2.0 GB | 超轻量、速度优先的快速响应场景 |

### 五层大脑架构（Phase 9 后）

| 层 | 标识 | 模型/工具 | 成本 | 用途 |
|----|------|---------|------|------|
| L0a | 通用本地 | `qwen2.5:7b` via `local_think(mode=chat)` | ¥0 | 摘要、翻译、文档分析、心跳决策 |
| L0b | 代码本地 | `deepseek-coder-v2:16b` via `local_think(mode=run_code)` | ¥0 | Python 脚本、财务运算、格式转换 |
| L0c | 推理本地 | `deepseek-r1:latest` via `local_think(mode=reason)` | ¥0 | CoT 推理、多步计划、复杂分析 |
| L1 | 主力云脑 | `deepseek-chat`（agent 主循环） | ¥/token | 用户对话、工具调度、任务协调 |
| L2 | 深度云脑 | `deep_think` → deepseek-reasoner | ¥¥/token | 架构设计、复杂 Bug、深度规划 |

心跳层：HeartbeatService `_decide` → `OllamaProvider(qwen2.5:7b)` — 心跳跳过/执行决策完全本地

### LocalThinkTool 更新（三模型路由）

```python
_LOCAL_MODELS = {
    "chat":     "qwen2.5:7b",           # 通用：摘要/翻译/分析/问答
    "run_code": "deepseek-coder-v2:16b", # 代码：Python/Shell/格式转换
    "reason":   "deepseek-r1:latest",    # 推理：财务/规划/CoT
}
```

- `mode=chat` — 纯文本响应，qwen2.5:7b，轻量快速
- `mode=run_code` — 代码生成 + subprocess 执行，deepseek-coder-v2:16b
- `mode=reason` — 链式推理，deepseek-r1，保留 `<think>` 标签

### HeartbeatService 本地集成

**设计原则**：不新建引擎，实现 nanobot `LLMProvider` ABC，直接传入已有 HeartbeatService。

**新增文件**：`core/local_provider.py`

```python
class OllamaProvider(LLMProvider):
    """实现 nanobot LLMProvider 接口，aiohttp → localhost:11434/api/chat"""
    # 支持 tool_calls（心跳虚拟工具）
    # 完全隔离，不设置 litellm.api_base 全局变量

def create_local_provider(model: str) -> OllamaProvider | None:
    # TCP 检查 localhost:11434，不可达则返回 None（静默降级）
```

**nanobot 改动（最小化）**：

| 文件 | 改动 |
|------|------|
| `nanobot/config/schema.py` | `HeartbeatConfig` 增加 `local_model: str | None = None` |
| `nanobot/heartbeat/service.py` | `__init__` 增加 `local_provider` 参数；`_decide()` 优先用本地 provider |
| `nanobot/cli/commands.py` | 从 workspace `tools_init.py` 动态加载 `create_local_provider`（与 `_register_workspace_tools` 同一 importlib 模式） |

**config.json 配置**：

```json
"gateway": {
  "heartbeat": {
    "enabled": true,
    "intervalS": 1800,
    "localModel": "qwen2.5:7b"
  }
}
```

### SubagentManager 与 L0 的配合规则

```
简单 Python 任务  → local_think(mode=run_code)   ← 不 spawn
单次文本分析      → local_think(mode=chat)        ← 不 spawn
复杂多步任务      → subagent.spawn(...)           ← 使用 L1 cloud
需要 SOUL 人格    → L1 直接回复                   ← 不走 L0
```

### 新增/修改文件汇总

| 文件 | 类型 | 说明 |
|------|------|------|
| `core/local_provider.py` | 新增 | OllamaProvider 实现 LLMProvider 接口 |
| `core/kylopro_tools.py` | 修改 | LocalThinkTool 三模型路由 + reason 模式 |
| `tools_init.py` | 修改 | 导出 `create_local_provider` |
| `nanobot/config/schema.py` | 修改 | HeartbeatConfig.local_model |
| `nanobot/heartbeat/service.py` | 修改 | _decide 阶段本地 provider |
| `nanobot/cli/commands.py` | 修改 | 动态加载 local provider 传给 HeartbeatService |
| `skills/local-brain/SKILL.md` | 改写 | 五层架构 + 三模型路由表 + SubagentManager 规则 |
| `~/.nanobot/config.json` | 修改 | heartbeat.localModel = "qwen2.5:7b" |

### 工具总数

Phase 9 后 Kylopro 注册工具：**11 个**（不变）

### 新对话恢复要点

1. `core/local_provider.py` — OllamaProvider，nanobot LLMProvider 实现
2. `core/kylopro_tools.py` — LocalThinkTool 三模型路由（chat/run_code/reason）
3. `nanobot/heartbeat/service.py` — `_decide` 本地化，心跳决策零成本
4. `skills/local-brain/SKILL.md` — 五层架构 + L0/L1 分工规则
5. ~~**待操作**：Python 3.12 已从 AppData 丢失~~ → **Phase 10 已修复**

---

## Phase 10 — 2026-03-08 (Python 修复 + 屏幕工具 + 权限分层)

### 背景

Phase 9 结束时记录了"Python 3.12 已从 AppData 丢失"的待操作项。本 Phase 修复该问题，并新增屏幕操作能力和分层权限体系。

### 1. Python 3.12 从 Package Cache 修复

**根因**：`C:\Users\qianchen\AppData\Local\Programs\Python\Python312\python.exe` 丢失，只剩 `python3.dll`。但 `venv\Scripts\python.exe` 内嵌 shims 依赖宿主 Python。

**修复路径**（无需重下载）：
```
Package Cache 位置: C:\ProgramData\Package Cache\{44BC9F9C...}\
安装: exe.msi  → 恢复 python.exe
     lib.msi  → 恢复 stdlib（encodings 等 199 个模块）
     pip.msi, tcltk.msi, test.msi
```

**验证**：`venv\Scripts\python.exe -c "import nanobot; print('OK')"` → 输出 OK。

### 2. OS ACL 实验（失败并回滚）

尝试 `icacls /deny "qianchen:(D,W)"` 保护 python.exe 和 config.json → **失败**：
- Windows DENY D 标志包含 `Synchronize`，阻止一切文件 handle 打开
- Python 无法执行任何 `open()`，gateway 启动报 `PermissionError`
- `attrib +R config.json` 导致 nanobot 配置迁移写回失败

**结论**：对 AI agent 而言，行为规则约束（AGENTS.md）是唯一不破坏系统功能的保护机制。

### 3. GBK 编码修复（PYTHONUTF8=1）

**问题**：Gateway banner 含 🐈 emoji，PowerShell 终端 GBK 编码 → `UnicodeEncodeError`。  
**修复**：`[System.Environment]::SetEnvironmentVariable("PYTHONUTF8","1","User")` 设置永久用户环境变量。

### 4. ScreenTool 实现（屏幕操作）

**新增依赖**：
```
pyautogui 0.9.54
mss 10.1.0
Pillow 12.1.1
```

**实现**：`core/kylopro_tools.py` 新增 `ScreenTool` 类：

| 动作 | 说明 |
|------|------|
| `screenshot` | 截图，base64 返回 |
| `click` / `double_click` / `right_click` | 鼠标点击 |
| `move` | 鼠标移动（不点击） |
| `scroll` | 滚动 |
| `type` | 输入文字 |
| `hotkey` | 组合键（如 `ctrl+c`） |
| `press` | 单键 |
| `windows` | 列出所有窗口 |
| `focus_window` | 激活指定窗口 |

```python
pyautogui.FAILSAFE = True   # 鼠标移到左上角立即中止
pyautogui.PAUSE = 0.05
```

### 5. 分层权限体系（AGENTS.md 重写）

将原「绝对禁止」列表重写为三层 P0/P1/P2 分级授权模型：

| 层级 | 触发 | 典型操作 |
|------|------|----------|
| **P0** 默认运行 | 始终激活 | 读文件、截图、写工作区文件 |
| **P1** 监管授权 | 说「允许/可以」 | screen click/type、pip install、修改 nanobot 源码 |
| **P2** 特殊任务 | 「我知道风险，允许你……」 | pip uninstall、删 venv、升级核心包 |

- P2 操作强制备案到 `data/` 目录
- 永久禁止列表缩减到 5 条真正危险操作
- P1/P2 激活时在回复开头标注 `[P1 已激活 · 本次对话]`

### 新增/修改文件汇总

| 文件 | 类型 | 说明 |
|------|------|------|
| `core/kylopro_tools.py` | 修改 | 新增 ScreenTool（11 个动作），`import base64, io`，注册到 agent_loop |
| `AGENTS.md` | 重写 | 从硬编码禁止列表改为 P0/P1/P2 分层权限框架 |

### 工具总数

Phase 10 后 Kylopro 注册工具：**12 个**（新增 `screen`）

### 新对话恢复要点

1. **Python 3.12 已修复** — venv 完整，所有依赖正常
2. `PYTHONUTF8=1` 已设为永久用户环境变量 — emoji 不再崩溃
3. `core/kylopro_tools.py` — ScreenTool 已注册，P0 自由截图，P1 允许交互
4. `AGENTS.md` — P0/P1/P2 分层权限，不再写死禁止列表
5. Gateway 运行状态：连接 Telegram 149.154.166.110:443，HeartbeatService 本地 qwen2.5:7b
