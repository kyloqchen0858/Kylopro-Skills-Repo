# Long-term Memory

This file stores important information that should persist across sessions.

## User Information

- **Name**: qianchen
- **Timezone**: UTC+8
- **Language**: 中文为主，可接受英文技术名词
- **Communication Preferences**: 偏好直接、技术化、少废话的表达；希望先动手落实，再汇报结果

## Preferences

- 有 IDE 订阅能力，可让外部 IDE 生成质量更高的实现代码
- Kylo 负责架构决策、接口规范、调度与整合
- 不希望 Kylo 在低质量场景下硬写大量 pyautogui 或向量库实现
- 已提供 GitHub token，可用于仓库检查、下载与上游同步

## Project Context

**Kylopro-Nexus 项目状态**：
- 项目位置：c:\Users\qianchen\Desktop\nanobot\Kylopro-Nexus\
- nanobot 是源码版，可直接修改框架代码
- 95 个 nanobot 测试通过
- 工作区限制：只能访问 workspace 目录，无法直接读取项目根目录文件

**当前开发优先级**：
1. P1: TaskBridge 并发与中断（测试通过，待生产验证）
2. P2: 向量记忆接口规范
3. P3: Antigravity MCP-first 重建
4. P4: AGENTS 与 SKILL 整合
5. P5: nanobot 上游双周监测机制
6. P6: Kylo 自开发框架

**模型阶梯调度配置**：
- L1 主力：deepseek/deepseek-chat（日常对话）
- L2 深度：deepseek/deepseek-reasoner（通过 deep_think 工具触发）
- L3 辅助：minimax/abab6.5s-chat（fallback）

**本地 Ollama 模型状态**：
- ollama 版本：0.17.7
- 当前保留模型：qwen2.5:7b (4.7 GB)、deepseek-coder-v2:16b (8.9 GB)、deepseek-r1:latest (5.2 GB)
- 已删除模型：gpt-oss:20b (13 GB)、gemma3:12b (8.1 GB)、deepseek-r1:32b (19 GB)、qwen2.5-coder:1.5b-base (986 MB)
- 总存储占用：约 18.8 GB（清理后）
- 存储空间：C盘112GB可用，D盘624GB可用
- ollama 安装位置：C:\Users\qianchen\AppData\Local\Programs\Ollama\ollama.exe

## Important Notes

**财务配置**：
- 每周预算：¥50.00（原为¥20.00）
- 更新规则：每周一更新额度，上周剩余额度可叠加到下周
- 模型余额：
  - Minimax：¥15.00（测试额度，模型不稳定需测试效果，调用前需告知用户）
  - DeepSeek：¥50.00
- 预警机制：
  - 余额低于20%时提示
  - 余额低于5%时停止非关键付费API

**技能状态**：
- TaskBridge 生产验证已完成，并发与中断机制测试通过
- 可用技能：kylopro-dev、task-inbox、system-manager、kylo-memory、antigravity
- 工具调用正常：task_inbox、deep_think、task_read、task_write、task_interrupt

**系统优化需求**：
- 用户关注内存和存储空间管理
- 需要评估模型迁移到D盘的可能性
- 需要整理C盘文件，识别不常用应用可卸载
- 低耗能任务优先使用本地ollama模型

**存储清理状态**：
- 已完成模型清理：删除4个模型释放41GB空间，保留3个核心模型
- 已卸载程序：Proton Drive、Python 3.12.1非核心组件(8个)、旧版Microsoft Visual C++运行时(10个)
- 虚拟环境清理：释放131MB空间，但错误清理了重要依赖
- 重要依赖恢复需求：litellm(大语言模型库)和lark_oapi(飞书开放平台SDK)需要重新安装

**未来集成计划**：
- 用户计划开发自主工作能力：操作飞书工作流、Notion文件整理
- 用户将在Notion或飞书中构建内容，Kylo需要读取、整理、生成任务并自主执行
- litellm和lark_oapi是未来飞书/Notion集成的重要依赖

---

*This file is automatically updated by nanobot when important information should be remembered.*