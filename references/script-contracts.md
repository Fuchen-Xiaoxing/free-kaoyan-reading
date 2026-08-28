# 脚本接口与调用契约（按需加载）

> **加载时机**：仅当进入**阶段 3**（错题归档 / 词汇导出 / 墨墨导入）调用脚本前，按需读取本文件。日常讲题（阶段 0-2）无需加载，保持上下文精简。分支 B（纯词汇/归档类）会话同样适用。
>
> ⚠️ **【强约束】AI 严禁调用 view_file / grep 查看 `scripts/` 目录下的 Python 源码文件。所有脚本调用方式、参数和 JSON Schema 完全以本契约规范为准，直接构造 JSON 与执行命令行。只有脚本报错且 stderr 无法定位时，才允许定点查看报错位置。**
>
> 📁 **临时文件约定**：临时 JSON 统一写入 `tmp/free-kaoyan-reading/<本篇唯一ID>/`（相对当前工作目录；不可写时改用系统临时目录下的同名路径）。`file_write` 不会自动创建父目录——写入前必须先执行 `mkdir -p <目录>`。`record_error.py` 与 `memo_import.py` 成功后**默认自动删除输入 JSON 及因此变空的临时子目录**，调用方无需再手动清理（`--keep-json` 可保留）。

## 1. 词汇清单校验：`scripts/vocab_export.py`

- **命令格式**：`python scripts/vocab_export.py --json <JSON文件路径或JSON字符串> [--format check|markdown|json]`
- **功能特性**：自动去重（忽略大小写）、强制限制 ≤30 个词条（超出自动截断）、剔除缺 word 字段的无效条目。**默认 `check` 模式输出紧凑校验简报，不输出整表**——Markdown 表格由 AI 在正文中自行渲染（校验有修正时，严格按简报附带的最终清单与词序渲染），避免同一张表进两遍上下文。
- **输入 JSON Schema**（词汇对象数组）：
  ```json
  [
    {
      "word": "单词或词组 (如 transparent)",
      "meaning": "文中释义 (如 透明的；易懂的)",
      "tone": "态度色彩 (如 正 / 负 / 中性 / 讽刺)",
      "source": "出处 (如 Q21 题干 / Q23 选项 B / Q24 定位关键句)"
    }
  ]
  ```
- **输出**：
  - `check`（默认）：校验通过时一行简报（如 `✅ 校验通过：共 29 词，无重复、未超限、无无效条目`）；有修正时列出移除项并附最终词序清单（逗号分隔），供 AI 按此渲染。
  - `markdown`：完整 Markdown 表格（表头：`| # | 单词 / 词组 | 文中释义 | 态度色彩 | 出处 |`），仅调试/存档用。
  - `json`：归一化后的 JSON 数组。

## 2. 墨墨背单词一键导入：`scripts/memo_import.py`

- **命令格式**：`python scripts/memo_import.py --json <JSON文件路径或JSON字符串> [--dry-run] [--format text|json] [--keep-json]`
- **Token 机制**：自动从环境变量 `MAIMEMOTOKEN` 或 `MAIMEMO_TOKEN` 读取，无需显式传 `--token`。
- **功能特性**：自动查询 `voc_id`；未收录短语自动拆分为单词兜底解析（**自动过滤 the/of/to 等虚词，虚词不进入查询与导入**，报告中单列「跳过虚词」明细）；比对已有学习记录后自动将新词添加待背、旧词提升提前复习。用户审阅确认表格后，**直接执行正式导入**（无需在 live 对话中多跑一次 `--dry-run` 浪费轮次）。**正式导入成功后默认自动删除输入 JSON 临时文件及其变空的临时父目录**（`--keep-json` 保留；`--dry-run` 不删除）。API 类脚本建议设 `timeout ≥ 120s`。
- **输入 JSON Schema**：与 `vocab_export.py` 输入格式完全一致（直接传入同一个 JSON 文件即可）。
- **输出**：stdout 打印分类统计报告（包含新加待背、提前复习、词组拆分明细、跳过虚词、无法识别及统计汇总）；成功清理时追加一行 `🧹 已自动清理临时输入文件: <路径>`（属预期日志，无需向用户报错）。

## 3. 错题本批量归档：`scripts/record_error.py`

- **命令格式**：`python scripts/record_error.py --file 错题本.md --json <JSON文件路径或JSON字符串> [--keep-json]`
- **功能特性**：ID 自动去重递增、12 类错误类型与能力短板严格校验、YAML frontmatter + 正文格式批量追加至 `错题本.md`（只追加、不覆盖）。脚本内置宽容度别名映射（如兼容 `type`/`shortboard`/`body` 等简写键名）。**归档成功后默认自动删除输入 JSON 临时文件及其变空的临时父目录**（`--keep-json` 保留）。
- **输入 JSON Schema**（错题对象数组）：
  ```json
  [
    {
      "id": "2009-T4-Q21",
      "question_type": "细节题",
      "error_type": "无对应内容",
      "ability_shortboard": "词汇",
      "keyword": "题干定位词或核心切入点",
      "location": "原文定位 (如 L12-13)",
      "restore": "错误还原 (用户自述思路 + 诊断思维误区)",
      "attribution": "方法论归因 (违背/忽略的原则)",
      "lesson": "教训金句 (一句话前瞻策略)",
      "analysis": "详细复盘正文"
    }
  ]
  ```
- **字段别名兼容**：`question_type` (支持 `type`/`题型`), `ability_shortboard` (支持 `shortboard`/`ability`/`能力短板`), `error_type` (支持 `error`/`错误类型`), `analysis` (支持 `body`/`content`/`正文`)。
- **枚举约束**：
  - `error_type` 必须严格属于 12 类之一：`定位错误`、`无对应内容`、`过度推理`、`偷换概念/嫁接`、`因果倒置`、`态度背离`、`细节背离主旨`、`绝对化误选`、`审题不清`、`比较/时态偷换`、`词义误解`、`长难句误读`。
  - `ability_shortboard` 必须严格属于：`词汇`、`语法`、`主旨` 之一。
