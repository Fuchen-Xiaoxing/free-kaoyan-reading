# OpenMinis Android 客户端 Skill 开发与适配指南

> **适用客户端**：OpenMinis for Android (基于 PRoot + Alpine Linux + Native Offload 架构)  
> **文档定位**：面向准备为 Minis Android 客户端开发或移植 AI Skill 的开发者与高级用户。

---

## 目录
1. [Minis 客户端与 Skill 运行机制](#1-minis-客户端与-skill-运行机制)
   - [三级渐进加载机制 (Progressive Disclosure)](#11-三级渐进加载机制-progressive-disclosure)
   - [目录规范与命名映射 (Slugify)](#12-目录规范与命名映射-slugify)
   - [Frontmatter 解析与关键截断限制](#13-frontmatter-解析与关键截断限制)
   - [20 个 Skill 的 Prompt 槽位竞争机制](#14-20-个-skill-的-prompt-槽位竞争机制)
2. [Android 沙箱运行环境与特性 (PRoot + Alpine Linux)](#2-android-沙箱运行环境与特性-proot--alpine-linux)
   - [ARM64 原生性能优势](#21-arm64-原生性能优势)
   - [进程模型：每次调用均为独立全新会话](#22-进程模型每次调用均为独立全新会话)
   - [硬链接转换为软链接 (--link2symlink)](#23-硬链接转换为软链接---link2symlink)
   - [Alpine musl libc 依赖约束](#24-alpine-musl-libc-依赖约束)
   - [系统级网络代理自动同步](#25-系统级网络代理自动同步)
3. [Android 专属原生能力：Native Offload 命令行工具](#3-android-专属原生能力native-offload-命令行工具)
   - [独有杀手级工具：android-a11y-cli (无障碍自动化)](#31-独有杀手级工具android-a11y-cli-无障碍自动化)
   - [独有杀手级工具：android-shizuku-cli (免 Root ADB 特权)](#32-独有杀手级工具android-shizuku-cli-免-root-adb-特权)
   - [核心设备集成指令集 (android-*)](#33-核心设备集成指令集-android-)
   - [通用能力指令集 (minis-*)](#34-通用能力指令集-minis-)
4. [权限安全门禁系统 (Offload Gate)](#4-权限安全门禁系统-offload-gate)
   - [三态安全策略定义](#41-三态安全策略定义)
   - [敏感指令的指引义务](#42-敏感指令的指引义务)
5. [文件系统与 UI 交互协议 (minis:// 与 /var/minis/)](#5-文件系统与-ui-交互协议-minis-与-varminis)
   - [虚拟路径映射表](#51-虚拟路径映射表)
   - [多媒体内联渲染机制](#52-多媒体内联渲染机制)
   - [外部存储挂载与只读保护](#53-外部存储挂载与只读保护)
6. [跨平台双端适配指南 (iOS vs Android)](#6-跨平台双端适配指南-ios-vs-android)
   - [指令名称映射差异](#61-指令名称映射差异)
   - [双端环境智能嗅探模板](#62-双端环境智能嗅探模板)
7. [防踩坑与最佳实践清单](#7-防踩坑与最佳实践清单)
8. [实战示例：完整生产级 Skill 样例](#8-实战示例完整生产级-skill-样例)

---

## 1. Minis 客户端与 Skill 运行机制

### 1.1 三级渐进加载机制 (Progressive Disclosure)

为避免大量 Skill 的说明直接撑爆大模型的上下文窗口（Context Window），Minis 采用了严格的三级分层加载架构：

```
Level 1: 元数据摘要 (Metadata)    --> 始终驻留系统 Prompt，用于模型意图匹配（触发阶段）
Level 2: SKILL.md 主体内容        --> 触发匹配后，模型通过 file_read 读入完整工作流（< 5000 词）
Level 3: 辅助脚本与参考资料        --> 运行时按需调用 scripts/、references/（无上下文大小限制）
```

### 1.2 目录规范与命名映射 (Slugify)

每个 Skill 必须存放在一个独立的文件夹中：

```text
<skill-id>/
├── SKILL.md              # [必须] 包含 YAML frontmatter 和工作流说明
├── scripts/              # [可选] 可执行脚本 (Python/Shell/Node等)
├── references/           # [可选] 详细参考文档、数据结构字典、API Spec
└── assets/               # [可选] 模板文件、样例素材等
```

* **沙箱内挂载路径**：统一挂载在 `/var/minis/skills/<skill-id>/`
* **宿主机物理路径**：`<filesDir>/minis-global/skills/<skill-id>/`
* **Skill ID 生成规则**：Minis 根据 `SKILL.md` 中 frontmatter 的 `name` 自动进行 slugify：
  $$\text{id} = \text{name.lowercase().replaceAll([^a-z0-9]+, "-").trim("-")}$$
  *例如：`name: My Custom Skill` 解析后的 ID 为 `my-custom-skill`，其路径即为 `/var/minis/skills/my-custom-skill/SKILL.md`*。

### 1.3 Frontmatter 解析与关键截断限制

```yaml
---
name: demo-skill
description: 详细描述该 Skill 的功能与何时触发。请务必将核心关键词放在前 150 字符内。
version: 1.0.0
---

# Demo Skill 指南
...正文...
```

> [!WARNING]
> **200 字符硬截断机制**：  
> Minis 在向系统提示词注入 `<available_skills>` 片段时，会对 `description` 进行截断处理：
> ```kotlin
> if (desc.length > MAX_SKILL_DESC_LENGTH) { // MAX_SKILL_DESC_LENGTH = 200
>     desc = desc.substring(0, MAX_SKILL_DESC_LENGTH) + "…"
> }
> ```
> **开发者必须注意**：务必将 Skill 的“核心用途”以及“何时触发（When to trigger）”写在描述的前 150 个字符内，避免因截断导致模型无法识别意图！

### 1.4 20 个 Skill 的 Prompt 槽位竞争机制

系统 Prompt 片段中**最多同时展示 20 个已启用的 Skill**。当设备安装的 Skill 数量超过 20 时，系统按以下优先级排序填充槽位：
1. **内置 Skill (Bundled)**：最高优先级（如 `skill-creator`）。
2. **7 天内更新/安装的新 Skill**：按更新时间倒序排序，最多占用 10 个槽位。
3. **高频使用 Skill**：根据 `use_count`（模型读取 `SKILL.md` 的累计频次）倒序填满剩余槽位。
4. **未入选的剩余 Skill**：会被合并为末尾的一行文本提示：
   `"N more skills not shown above: skill-a, skill-b... List /var/minis/skills/ or grep to search all."`

---

## 2. Android 沙箱运行环境与特性 (PRoot + Alpine Linux)

Minis Android 客户端在底层使用 **PRoot**（基于 Linux `ptrace` 机制的用户态 chroot）启动了一个 ARM64 的 Alpine Linux 环境。

### 2.1 ARM64 原生性能优势
* **原生运行**：与 iOS 版使用的 iSH（基于 x86-32 动态二进制翻译）不同，Android 版 PRoot 直接在宿主机 ARM64 CPU 上原生执行指令。
* **高吞吐**：数据分析、Python 脚本执行、视频处理等任务的速度比 iOS 端快 5~20 倍。

### 2.2 进程模型：每次调用均为独立全新会话
* Agent 工具 `shell_execute` 的底层执行方式为：
  ```bash
  /bin/sh -c "<your_command>"
  ```
* **生命周期约束**：每次工具调用都会生成一个**全新的短命进程**，没有持久的交互式终端会话。
* **无状态性**：在一次 `shell_execute` 中 `export VAR=123` 或 `cd /tmp`，下一次调用将完全失效。如需共享状态，请使用文件读写或单条命令拼接（`cd /path && export VAR=1 && ...`）。

### 2.3 硬链接转换为软链接 (--link2symlink)
* Android 系统的 zygote 挂载机制禁止普通应用 UID 跨目录创建硬链接（Hardlink）。
* 为防止 Alpine 的包管理器 `apk`、Python 工具 `uv` 或 `npm` 在解包时因硬链接报错 `EPERM`，PRoot 启用了 `--link2symlink`，并将 `UV_LINK_MODE=symlink` 写入了默认环境。
* **编写脚本时**：切勿依赖硬链接的原子更新特性。

### 2.4 Alpine musl libc 依赖约束
* 沙箱基于 **Alpine Linux**，C 运行时库为 **musl libc**（非 glibc）。
* 预编译的外部 Linux 二进制程序不能直接复制到沙箱使用，除非：
  * 使用静态编译（`gcc -static`）。
  * 针对 `musl` 编译。
  * 安装 `gcompat` 兼容层。
* Python 第三方包若包含 C 扩展，优先通过 `apk add py3-numpy` 等系统源安装，或者使用支持 `musllinux` 的 wheel。

### 2.5 系统级网络代理自动同步
* 沙箱会自动监听 Android 系统的 HTTP/HTTPS 代理配置，并向每个子进程注入：
  * `http_proxy`, `https_proxy`, `all_proxy`, `no_proxy`
* 沙箱内部的 `curl`, `wget`, `pip`, `npm` 会自动复用系统或企业代理配置（包括抓包工具如 Charles / Mitmproxy）。

---

## 3. Android 专属原生能力：Native Offload 命令行工具

Minis 巧妙利用 PRoot 的 `execve` 劫持机制：在沙箱内 `/usr/local/bin/` 植入桩（Stub）程序。当 Shell 试图执行该命令时，PRoot 会截获调用并通过抽象 UNIX 套接字（Abstract Socket）转交给 Android 原生代码执行，并将结果以标准输出格式返回给沙箱。

### 3.1 独有杀手级工具：android-a11y-cli (无障碍自动化)

通过 Android 系统无障碍服务（AccessibilityService）实现完整的屏幕读取与交互自动化。

#### 常用命令速查：
```bash
# 1. 连通性测试
android-a11y-cli service ping

# 2. 系统截屏（支持 API 30+，返回图片绝对路径或 base64）
android-a11y-cli ui screenshot --scale 0.5

# 3. 提取当前屏幕 UI 树与文本
android-a11y-cli ui dump                      # 导出整棵 UI 节点树
android-a11y-cli ui find --text "发送"        # 查找包含指定文本的节点

# 4. 点击与模拟输入
android-a11y-cli tap text "确定"
android-a11y-cli tap xy 540 1200
android-a11y-cli tap node <node_id>
android-a11y-cli input text "Hello" --node <node_id>
android-a11y-cli input key BACK               # 支持 BACK / HOME / RECENTS / NOTIFICATIONS

# 5. 滑动、手势与等待
android-a11y-cli scroll node <node_id> --direction down
android-a11y-cli gesture swipe 500 1600 500 400
android-a11y-cli wait stable --timeout 3000   # 等待界面动画完成、DOM 稳定
```

### 3.2 独有杀手级工具：android-shizuku-cli (免 Root ADB 特权)

只要设备上运行了 [Shizuku](https://shizuku.rikka.app/)，Agent 就能在沙箱内直接获得 **ADB Shell 权限（UID 2000）** 甚至 **Root 权限（UID 0）**。

#### 常用命令速查：
```bash
# 1. 检查 Shizuku 状态
android-shizuku-cli service ping

# 2. 应用管理 (pm)
android-shizuku-cli package list --format json
android-shizuku-cli package install /path/to/app.apk
android-shizuku-cli package uninstall com.example.app

# 3. Activity 与组件调度 (am)
android-shizuku-cli activity start -n com.tencent.mm/.ui.LauncherUI
android-shizuku-cli activity force-stop com.example.app

# 4. 系统设置调整 (settings)
android-shizuku-cli settings get global airplane_mode_on
android-shizuku-cli settings set system screen_brightness 200

# 5. 权限管理
android-shizuku-cli permission grant com.example.app android.permission.CAMERA
```

### 3.3 核心设备集成指令集 (android-*)

| 指令名称 | 功能描述 | 核心子命令与参数示例 |
| :--- | :--- | :--- |
| `android-clipboard` | 系统剪贴板读写 | `get` / `set "文本"` |
| `android-notification`| 发送与监听系统通知 | `send --title "任务完成" --body "耗时 3 分钟"` |
| `android-photos` | 查询与读取相册照片 | `list --limit 5` / `get --id <photo_id>` |
| `android-calendar` | 日历事件读取与创建 | `list --days 7` / `add --title "会议" --start "2026-09-30 10:00"` |
| `android-contacts` | 读取联系人通讯录 | `search "张三"` / `list` |
| `android-location` | 获取定位信息 | `get --accurate` |
| `android-alarm` | 闹钟与倒计时设置 | `set --time "07:30"` / `timer --seconds 300` |
| `android-speak` | 系统级 TTS 语音播报 | `"正在为您处理第 3 个任务"` |
| `android-weather` | 获取天气数据 | `current` / `forecast` |
| `android-open` | 使用默认应用打开资源 | `url "https://..."` / `app com.example.pkg` |

> [!NOTE]
> 所有 `android-*` 指令均遵循通用标准输出格式：
> * 默认 JSON Envelope：`{ "ok": true, "data": ... }` 或 `{ "ok": false, "error": { "code": "...", "message": "..." } }`
> * 常用修饰标志：
>   * `--compact`：将 JSON 压缩为单行。
>   * `-q`, `--quiet`：剥除 envelope 外壳，仅输出原始数据。

### 3.4 通用能力指令集 (minis-*)

* `minis-model-use`：直接在 Shell 脚本中调用客户端配置的大语言模型（支持文本补全、子任务分解、多模态识图）。
* `minis-browser-use`：控制内置无头/可视化浏览器（网页导航、提取 DOM、抓取 Cookies、执行 JavaScript）。
* `minis-sessions-cli`：跨会话检索与查询历史聊天记录。
* `minis-scheduled`：管理后台定时触发的自动化任务。
* `minis-config`：受控地查询或变更 Minis 客户端配置项。

---

## 4. 权限安全门禁系统 (Offload Gate)

Minis 客户端对敏感的原生能力实行严格的分级权限控制：

### 4.1 三态安全策略定义
* `BYPASS`（始终允许）：日常权限（剪贴板、日历、相机、天气等）在初次授权后默认自动允许。
* `ASK_ONCE`（单次会话询问）：触发时会挂起沙箱调用，并在 Android 界面弹出对话框等待用户手动点击确认。
* `NOT_ALLOWED`（默认禁止）：直接拦截调用并返回 `PERMISSION_DENIED`。

### 4.2 敏感指令的指引义务
> [!IMPORTANT]
> **`android-a11y-cli` 和 `android-shizuku-cli` 默认就是 `NOT_ALLOWED` 级别！**  
> 因为这两者具备操纵其他 App 和系统的极高权限。如果你的 Skill 依赖这两项功能，**必须在 `SKILL.md` 的操作前置说明中写明引导**：
> > “若命令返回 PERMISSION_DENIED，请前往 Minis 设置 -> 权限 -> 集成 (Integrations) 中将对应权限调整为允许。”

---

## 5. 文件系统与 UI 交互协议 (minis:// 与 /var/minis/)

Minis 设计了会话隔离的虚拟资源协议 `minis://`，它在 Linux 沙箱文件、宿主机持久化存储以及聊天 UI 渲染之间建立了无缝映射。

### 5.1 虚拟路径映射表

| Linux 沙箱路径 | 对应 UI 协议 URL | 作用域 | 核心用途说明 |
| :--- | :--- | :--- | :--- |
| `/var/minis/attachments/` | `minis://attachments/<file>` | 当前会话 | **多媒体展示区**。放进此目录的图片、音频、视频会自动在聊天气泡中内联渲染。 |
| `/var/minis/workspace/` | `minis://workspace/<file>` | 当前会话 | **工作区**。用于存放生成的数据集、源码工程、中间文本。 |
| `/var/minis/browser/` | `minis://browser/<file>` | 当前会话 | 浏览器工具捕获的快照、截图和会话文件。 |
| `/var/minis/offloads/` | `minis://offloads/<file>` | 当前会话 | 存放 Offload 工具生成的大型数据与临时 Cookie 凭证。 |
| `/var/minis/memory/` | （无 URL） | 全局共享 | 存放长期跨会话记忆（`YYYY-MM-DD.md`, `GLOBAL.md`）。 |
| `/var/minis/mounts/<name>/`| `minis://mounts/<name>/` | 全局/用户 | 用户通过 Android 存储访问框架 (SAF) 挂载的本地文件夹（如 Obsidian 库）。 |

### 5.2 多媒体内联渲染机制
如果你的 Skill 执行了绘图（matplotlib）、音频录制或屏幕截图，请将生成的文件保存至 `/var/minis/attachments/`，并在最终回复中使用标准 Markdown 语法：

```markdown
这是分析生成的趋势图：
![趋势分析图](minis://attachments/trend_2026.png)

为您合成的音频播报：
![语音播报](minis://attachments/output.mp3)
```
客户端的富文本渲染器会自动解析该协议，并在聊天界面中呈现出原生图片或播放控件。

### 5.3 外部存储挂载与只读保护
* 用户挂载的外部目录（`/var/minis/mounts/<name>/`）可能被用户设置为“只读模式”。
* Minis 内部实现了写保护哨兵脚本（Write Guards）。如果脚本在未解锁的挂载路径执行覆盖写操作，会被沙箱直接拦截并报错。建议先将文件写入 `/var/minis/workspace/` 完成后再进行同步。

---

## 6. 跨平台双端适配指南 (iOS vs Android)

许多现存的 Minis Skill 诞生于 iOS 平台。如果你希望制作一份在 iOS 与 Android 均能完美运行的跨平台 Skill，请遵循以下规则：

### 6.1 指令名称映射差异

| 功能需求 | Android 客户端指令 | iOS 客户端指令 |
| :--- | :--- | :--- |
| 剪贴板操作 | `android-clipboard` | `apple-clipboard` |
| 日历操作 | `android-calendar` | `apple-calendar` |
| 闹钟/倒计时 | `android-alarm` | `apple-alarm` |
| 照片/相册 | `android-photos` | `apple-photos` |
| 语音朗读 (TTS) | `android-speak` | `apple-speak` |
| 系统通知 | `android-notification` | `apple-notification` |
| 健康数据 | `android-health` (若集成) | `apple-health` (HealthKit) |
| 提醒事项 | *（使用 calendar 或本地便签）* | `apple-reminders` |
| UI 自动化 | `android-a11y-cli` / `android-shizuku-cli` | 无原生直接支持 |

### 6.2 双端环境智能嗅探模板
在 Skill 的 Bash 脚本中，可以通过检测命令是否存在或判断 CPU 架构来平滑分流：

```bash
#!/bin/sh
set -e

# 跨平台剪贴板获取函数
get_clipboard() {
    if command -v android-clipboard >/dev/null 2>&1; then
        android-clipboard get -q
    elif command -v apple-clipboard >/dev/null 2>&1; then
        apple-clipboard get -q
    else
        echo "Error: No supported clipboard tool found." >&2
        return 1
    fi
}

CONTENT=$(get_clipboard)
echo "Got clipboard content: $CONTENT"
```

---

## 7. 防踩坑与最佳实践清单

1. **Description 绝不拖沓**：
   * 严禁在 `description` 中写“本插件由 xxx 编写，版本 1.0.0”等冗余废话。
   * 必须严格描述：**做什么（What it does）** + **何时触发（Trigger phrases/contexts）**。
   * 保持长度在 150 字符以内，以防 200 字符硬截断。
2. **命令输出降噪**：
   * 调用 `android-*` CLI 时尽量附带 `--quiet` 或 `-q`，或者管道传给 `jq -r '.data'`，只向大模型输出必要数据，避免庞大的 JSON 结构浪费 Token。
3. **依赖工具按需探测与安装**：
   * 不要假设沙箱内已经预装了 `curl`、`jq`、`python3` 或 `ffmpeg`。
   * 采用防御性编程：
     ```bash
     command -v jq >/dev/null 2>&1 || apk add --no-cache jq
     ```
4. **长耗时命令善用 delay 参数**：
   * 在使用 Agent 的 `shell_execute` 工具时，如果需要等待某个系统动作或轮询，使用参数 `delay` 代替命令内的 `sleep`，释放 Shell 资源。
5. **严禁在 Skill 中捆绑冗余文档**：
   * Skill 目录内不要包含 `README.md`、`INSTALL.md`、`CHANGELOG.md` 等非 Agent 执行必需的人类阅读文档，避免干扰上下文。

---

## 8. 实战示例：完整生产级 Skill 样例

以下为一个针对 Android 客户端量身定制的完整实用 Skill：**自动化截屏分析与辅助操作工具 (`android-screen-helper`)**。

### `android-screen-helper/SKILL.md`

```markdown
---
name: android-screen-helper
description: 截取当前 Android 手机屏幕画面，进行多模态视觉分析，或通过无障碍服务自动查找并点击屏幕控件。
version: 1.0.0
---

# Android Screen Helper 指南

本 Skill 用于让 Agent 能够“看见”并“操作”用户的 Android 手机当前屏幕。

## 前置环境检查
在执行操作前，必须先验证无障碍服务连通性：
```bash
android-a11y-cli service ping -q
```
* 如果返回 `{ "ok": true }`，表明服务正常。
* 如果返回错误或 PERMISSION_DENIED，立即中止并回复用户：“请在系统「设置 -> 无障碍/辅助功能」中启用 Minis，并在「Minis 设置 -> 权限 -> 集成」中授权 `android-a11y-cli`。”

---

## 常用工作流

### 流程一：捕获当前屏幕并查看
1. 截取屏幕并缩放至 50%（降低图像尺寸以节约视觉 Token）：
```bash
mkdir -p /var/minis/attachments
OUT_JSON=$(android-a11y-cli ui screenshot --scale 0.5)
IMG_SRC=$(echo "$OUT_JSON" | jq -r '.data.path')
cp "$IMG_SRC" /var/minis/attachments/current_screen.png
```
2. 调用工具 `read_image` 传入 `/var/minis/attachments/current_screen.png` 进行多模态内容识别。
3. 如果需要向用户展示截图，回复中使用：
```markdown
![当前屏幕画面](minis://attachments/current_screen.png)
```

### 流程二：定位并点击指定控件
1. 优先采用文本匹配点击：
```bash
android-a11y-cli tap text "确认支付"
```
2. 若文本点击失败，先 Dump UI 树查找节点：
```bash
android-a11y-cli ui dump > /tmp/screen_ui.json
# 提取对应包名或控件 resource-id 的节点 ID
NODE_ID=$(jq -r '.data.nodes[] | select(.text=="确认支付") | .id' /tmp/screen_ui.json | head -n 1)
if [ -n "$NODE_ID" ]; then
    android-a11y-cli tap node "$NODE_ID"
fi
```
3. 点击完成后，等待页面稳定：
```bash
android-a11y-cli wait stable --timeout 2000
```
```
