# 脚本接口与调用契约（按需加载）

> **加载时机**：仅当进入**阶段 3**（错题归档 / 词汇导出 / 墨墨导入）调用脚本前，按需读取本文件。日常讲题（阶段 0-2）无需加载，保持上下文精简。
>
> ⚠️ **【强约束】AI 严禁调用 view_file / grep 查看 `scripts/` 目录下的 Python 源码文件。所有脚本调用方式、参数和 JSON Schema 完全以本契约规范为准，直接构造 JSON 与执行命令行。只有脚本报错且 stderr 无法定位时，才允许定点查看报错位置。**

## 1. 词汇表格导出：`scripts/vocab_export.py`

- **命令格式**：`python scripts/vocab_export.py --json <JSON文件路径或JSON字符串> [--format markdown|json]`
- **功能特性**：自动去重（忽略大小写）、强制限制 ≤30 个词条（超出自动截断），默认以 Markdown 表格输出至 stdout。
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
- **输出**：stdout 打印标准 Markdown 表格（表头：`| # | 单词 / 词组 | 文中释义 | 态度色彩 | 出处 |`）。

## 2. 墨墨背单词一键导入：`scripts/memo_import.py`

- **命令格式**：`python scripts/memo_import.py --json <JSON文件路径或JSON字符串> [--dry-run] [--format text|json]`
- **Token 机制**：自动从环境变量 `MAIMEMOTOKEN` 或 `MAIMEMO_TOKEN` 读取，无需显式传 `--token`。
- **功能特性**：自动查询 `voc_id`，未收录短语自动拆分为单词兜底解析，比对已有学习记录后自动将新词添加待背、旧词提升提前复习。用户审阅确认表格后，**直接执行正式导入**（无需在 live 对话中多跑一次 `--dry-run` 浪费轮次）。
- **输入 JSON Schema**：与 `vocab_export.py` 输入格式完全一致（直接传入同一个 JSON 文件即可）。
- **输出**：stdout 打印分类统计报告（包含新加待背、提前复习、词组拆分明细、无法识别及统计汇总）。

## 3. 错题本批量归档：`scripts/record_error.py`

- **命令格式**：`python scripts/record_error.py --file 错题本.md --json <JSON文件路径或JSON字符串>`
- **功能特性**：ID 自动去重递增、12 类错误类型与能力短板严格校验、YAML frontmatter + 正文格式批量追加至 `错题本.md`（只追加、不覆盖）。脚本内置宽容度别名映射（如兼容 `type`/`shortboard`/`body` 等简写键名）。
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
