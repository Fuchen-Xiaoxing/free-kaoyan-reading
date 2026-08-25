# CHANGELOG

## [Unreleased] - 2026-08-25

### 架构与上下文工程优化 (Context & Architecture Optimization)

- **`sentence-advanced` 按域拆分（消除单笔 53KB 加载瓶颈）**：
  - 移除原 53KB 单体文件 `references/sentence-advanced.md`，按领域细分并建立 `references/sentence-advanced/` 目录：
    - `non-finite.md` —— 非谓语动词系统精粹（谓语 vs 非谓语、三大形态、三步判断法、doing/done/to do 深度全景、状态动词逢考必主动、with 复合结构）。
    - `clauses.md` —— 从句四象限决策系统（底层两意义、四象限决策矩阵、三大黄金判词、定语从句全景、that 不省略铁律、同位语 vs 定语从句、疑问词+to do）。
    - `special-patterns.md` —— 句式骨架、特殊句型与高频逻辑（词性骨架、断句三原则、引导词省略、主谓隔离还原、标点体系、It 句型判别、FANBOYS 并列、比较对比、as 用法、否定对比、虚拟语气）。
    - `examples.md` —— 3 个考研真题长难句标准 5 板块示范案例（few-shot 独立分离，仅在格式需要对齐时按需参考）。
  - 将「长难句为阅读解题赋能」（4 大赋能实战场景）整合迁入 [`references/sentence-core.md`](file:///C:/Users/Lenovo/Desktop/free-kaoyan-reading/references/sentence-core.md)，使长难句常规拆解直接具备定位改写、比较锁定、态度定乾坤与生词代号化能力。
  - 所有拆分文件均配备顶部带锚点目录（TOC），支持结合 `grep` 进行章节级外科手术式定点读取。

- **`SKILL.md` 内部去重与加载矩阵收敛**：
  - 简化两条铁律第一条，剔除正文中重复的长难句按需加载说明。
  - 精简开工必读注释，将分散在各阶段的引用触发规则统一收敛至全局唯一的「参考文件与按需加载总表」（模块/文件 × 触发条件 × 读取方式）。
  - 合并工程约束与错题规范，消除与阶段 3 和导航表的重叠表述。

- **消除 Schema 冗余与错题本模板精简**：
  - 清理 `错题本.md` 中冗余内联的「12 类错误类型（封闭枚举）」表格与「能力短板三件套」列表，使错题本保持纯净数据追加结构，消除多处同步维护负担。
  - 解除 `references/error-log-format.md` 对 `error-types.md` 的嵌套“参见”描述，改为平行独立规范。

- **`scripts/record_error.py` 升级支持真批量追加**：
  - `--json` 支持接收 JSON 数组（`[{...}, {...}]`）或单个对象，支持 stdin 管道输入。
  - 内部自动校验、动态维护批次内递增去重 ID，单次调用即可原子化完成篇末所有错题批量追加。

---

## [1.0.0] - 2026-08-24

### 重构与优化 (Refactoring)

- **Frontmatter 规范化**：
  - `name` 统一为 `free-kaoyan-reading`（通过 `^[a-z0-9-]+$` 正则校验）。
  - `description` 压缩至 123 字符（≤300 字符），采用“做什么 + 何时触发”两段式，完整保留全部 9 个触发词。
  - 移除非标准 `compatibility` 字段，内容迁移至正文「## 依赖说明」。
- **SKILL.md 瘦身与去重（143 行，≤150 行）**：
  - 迁移 12 类错误类型至 `references/error-types.md`。
  - 迁移错题本 Schema 规范至 `references/error-log-format.md`。
  - 整合 5 处分散的停顿等待指令为「停顿规则表」，消除重复并保留全部交互边界。
  - 消除多余的发音注记禁令和“严禁主动讲长难句”重复表述，统一遵循 `references/style-guide.md` 规范。
  - 上下文回查优化为“开工读取一次后信任上下文；确需回查时用 grep 定位关键词所在行再定点读取，禁止全文件重读”。
  - 阶段 1 末尾新增「输出前自检 checklist」。
- **长难句方法论拆分与模板规范**：
  - 将原 `references/sentence-methodology.md` 无损拆分为 `references/sentence-core.md`（常规核心拆解）与 `references/sentence-advanced.md`（高阶句式库与示范演练），均配备顶部带锚点 TOC。
  - 将「标准化长难句 5 板块输出模板规范」迁入 `references/sentence-core.md`；【板块二：模块化断句与结构积木】采用极简纯序号（`[1]`, `[2]`...），且仅断句切分的分句积木英文采用 LaTeX 格式（`$\text{...}$`），其余单词/句子板块保持标准纯文本。
- **超长引用文件索引**：
  - 给 `references/methodology.md` 添加顶部完整章节目录 TOC。
- **确定性操作代码化 (scripts/)**：
  - 新增 `scripts/record_error.py` 实现 12 类错误枚举/能力短板校验、ID 自动去重递增与只追加归档。
  - 新增 `scripts/vocab_export.py` 实现词汇去重、≤30 词上限截断警告与格式化导出（支持标准 Markdown 表格 `| # | 单词 / 词组 | 文中释义 | 态度色彩 | 出处 |` 格式输出）。
