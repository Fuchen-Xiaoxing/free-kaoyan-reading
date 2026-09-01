# 脚本接口与调用契约（按需加载）

> **加载时机**：仅当进入**阶段 3**（错题归档 / 墨墨导入）调用脚本前，按需读取本文件。日常讲题（阶段 0-2）无需加载，保持上下文精简。分支 B（纯词汇/归档类）会话同样适用。
>
> ⚠️ **【强约束】AI 严禁调用 view_file / grep 查看 `scripts/` 目录下的 Python 源码文件。所有脚本调用方式、参数和 JSON Schema 完全以本契约规范为准，直接构造 JSON 与执行命令行。只有脚本报错且 stderr 无法定位时，才允许定点查看报错位置。**
>
> 📁 **输入模式与传参约定**：**优先推荐直接参数/管道模式**——所有脚本均原生支持通过 `--json '<JSON字符串>'` 或标准输入（stdin 管道）直接传入数据，无需落地磁盘临时文件，消除工具链往返开销。若调用方选择写入临时文件，直接单步写入 `tmp/free-kaoyan-reading/<本篇唯一ID>/` 即可，**严禁在 shell 额外调用 `mkdir -p`**（脚本内部已原生支持目录自创建）。`record_error.py` 与 `memo_import.py` 在处理临时文件成功后**默认自动删除输入 JSON 及因此变空的临时子目录**（`--keep-json` 可保留）。

## 1. 错题本批量归档：`scripts/record_error.py`

- **命令格式**：`python scripts/record_error.py [--file <路径>] [--info] --json <JSON字符串或文件路径> [--keep-json]`（亦支持 stdin 管道输入，**建议省略 `--file` 走默认安全持久化路径**）
- **功能特性**：
  - **安全持久化与路径自愈**：`--file` 参数可选（传入目录或 `.md` 时自动自愈为 `考研英语/错题本.md`）。在 Open Minis / Android PRoot 环境下，默认优先探测已挂载的外部文档目录（`/var/minis/mounts/Documents/考研英语/错题本.md`）或系统公共文档目录（`/storage/emulated/0/Documents/考研英语/错题本.md`），支持 Obsidian、WPS 或自带文件管理器直接查阅；若未挂载则安全保存在 `/var/minis/workspace/错题本.md`；支持环境变量 `KAOYAN_ERROR_NOTEBOOK` 自定义路径；
  - **存储状态诊断**：支持 `--info` / `--status` 快速查看当前解析到的错题本路径、可写性与已存错题数量；
  - **历史数据自动迁移**：若检测到旧 Skill 目录中残留有效错题，首次归档时自动将历史条目无损合并至持久化错题本，并备份旧文件；
  - **数据归档与校验**：ID 自动去重递增、12 类错误类型与能力短板严格校验、YAML frontmatter + 正文格式批量追加（只追加、不覆盖、自动清理占位符 `（暂无）`）。脚本内置宽容度别名映射。**归档成功后默认自动删除输入 JSON 临时文件及其变空的临时父目录**（`--keep-json` 保留）。
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

## 2. 核心词汇校验与墨墨背单词一键导入：`scripts/memo_import.py`

- **命令格式**：`python scripts/memo_import.py --json <JSON字符串或文件路径> [--validate-only] [--dry-run] [--format text|json|markdown] [--keep-json]`（亦支持 stdin 管道输入）
- **Token 机制**：自动从环境变量 `MAIMEMOTOKEN` 或 `MAIMEMO_TOKEN` 读取，无需显式传 `--token`。
- **功能特性**：
  - **一体化词汇校验**：自动字段归一化、忽略大小写去重、强制 ≤30 个词条截断保护；`--validate-only` 模式仅进行去重校验与截断，不发起网络请求；
  - **智能解析与兜底**：自动查询 `voc_id`；未直接收录的词条自动执行**基于规则的后缀还原（复数 `-s/-es`、过去分词 `-ed`、分词 `-ing`）原型二次查询**；未收录短语自动拆分为单词兜底解析（**自动过滤 the/of/to 等虚词，虚词不进入查询与导入**，报告中单列「跳过虚词」明细）；
  - **学习状态自动分流**：比对已有学习记录后自动将新词添加待背、旧词提升提前复习；
  - **单步直接执行**：用户在正文审阅确认后，**直接执行正式导入**（无需在 live 对话中多跑一次 `--dry-run` 浪费轮次）。**正式导入成功后默认自动删除输入 JSON 临时文件及其变空的临时父目录**（`--keep-json` 保留；`--dry-run` / `--validate-only` 不删除）。API 类脚本建议设 `timeout ≥ 120s`。
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
- **输出**：stdout 打印分类统计报告（包含新加待背、提前复习、词组拆分明细、跳过虚词、无法识别及统计汇总）；成功清理时追加一行 `🧹 已自动清理临时输入文件: <路径>`。

