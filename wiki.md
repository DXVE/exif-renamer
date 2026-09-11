# Exif-Renamer 工程 Wiki

> 面向**开发者**的技术文档:读完本文,你应当能在不了解任何历史背景的情况下,理解这个项目是什么、代码如何组织、核心逻辑如何工作,并能动手运行、打包与二次开发。
>
> 与 README 的关系:**README 面向最终用户**(介绍功能、下载与用法);本文面向开发者(讲解实现与工程细节)。两篇文档互相补充,功能层面的介绍请先看 README。

---

## 目录

- [0. 阅读指引](#0-阅读指引)
- [1. 项目速览](#1-项目速览)
- [2. 总体架构](#2-总体架构)
- [3. 运行、打包与发布](#3-运行打包与发布)
- [4. 核心算法与数据流](#4-核心算法与数据流)
- [5. 线程模型与 UI 消息机制](#5-线程模型与-ui-消息机制)
- [6. 接口契约与可配置点](#6-接口契约与可配置点)
- [7. 数据安全边界与红线](#7-数据安全边界与红线)
- [8. 二次开发指引](#8-二次开发指引)
- [9. 文件与速查](#9-文件与速查)
- [附录 A. 常见问题排查](#附录-a-常见问题排查)
- [附录 B. 术语表](#附录-b-术语表)

---

## 0. 阅读指引

本文假定读者具有基础 Python 与桌面 GUI 经验,但对本项目**零背景知识**。

- **只想快速跑起来**:读 [§3.1 从源码运行](#31-从源码运行)。
- **想知道项目在做什么、界面长什么样**:读 [§1](#1-项目速览) 与 [§2.2 界面结构](#22-gui-界面结构)。
- **想理解最关键的一段算法**(日期如何取、文件名如何生成):读 [§4.2 拍摄时间提取](#42-拍摄时间提取) 与 [§4.4 模板渲染与冲突消解](#44-模板渲染与冲突消解)。
- **想改代码**:请完整阅读 [§8 二次开发指引](#8-二次开发指引),并在动手前通读 [§7 红线](#7-数据安全边界与红线)。

约定:

- 文中路径均为**仓库内相对路径**,不依赖克隆位置。
- 引用函数/类时使用「模块内符号名」而非固定行号(行号会随代码漂移,不具参考价值)。
- 两个入口程序文中简称:**主程序**(`src/exif_renamer.py`)与**调试工具**(`src/exif_debugger.py`)。

---

## 1. 项目速览

### 1.1 这是什么

**Exif-Renamer** 是一个纯 GUI 的**多格式文件批量重命名工具**。它读取媒体文件内嵌的 **EXIF 拍摄时间**,再按照用户自定义的**命名模板**把文件重命名(或复制到新目录),用于照片归档、RAW 文件整理等场景。

- **形态**:Windows 桌面 GUI 应用(Tkinter/ttk 实现);核心处理逻辑同时兼容 macOS/Linux 基础运行。
- **技术栈**:Python 3.14+(开发与 CI 均使用 3.14,代码使用 `X | None` 联合类型语法);GUI 使用标准库 Tkinter;第三方依赖仅 `Pillow` 与 `exifread`(且均可选,见 [§3.2](#32-依赖与惰性加载))。
- **两个程序**:
  - 主程序:批量化重命名/复制,包含设置界面、预览、确认弹窗、日志面板与后台线程。
  - 调试工具:单张图片的 EXIF 分析器,左侧展示基本信息与常用 EXIF 字段,右侧展示 exifread 解析出的全部标签,可将结果导出为文本。用于排查"为什么这张照片读不到拍摄时间"。
- **代码规模**:主程序是单文件应用(约 1600 行),核心处理函数、GUI、后台线程都在同一文件内分层组织。

### 1.2 解决什么问题

相机直出、手机拍摄、社交平台下载的照片混在一个目录时,文件名千奇百怪,不便归档检索。该工具的做法是:文件名不再依赖拍摄者随意起的名字,而是以**真实拍摄时间**为锚点,套用统一模板生成可排序、可读的文件名。

### 1.3 核心特性

| 特性 | 说明 |
|---|---|
| EXIF 拍摄时间提取 | 多级降级链自动选取可用时间源,详见 [§4.2](#42-拍摄时间提取) |
| 双解析引擎 | `exifread`(首选,RAW/HEIC 精度高)与 `Pillow`(回退),详见 [§4.2.1](#421-exifread-通道) |
| 自定义命名模板 | 日期/前缀/类型/随机 ID/序号等占位符自由组合,实时预览 |
| 多文件类型 | 图片(含 RAW/HEIC)、视频、音频;扩展名矩阵见 [§6.2](#62-扩展名矩阵) |
| 递归处理 | 可选包含子文件夹;复制模式下在目标目录**保留源目录相对结构** |
| 复制模式 | 勾选后不修改原文件,输出到新目录(相对路径结构保留) |
| 多层确认 | 执行前弹出「异常文件警告」与「完整重命名对照表」两道确认 |
| 后台线程 | 扫描/分析/执行均在后台线程,主界面不阻塞;支持窗口关闭时优雅退出 |

### 1.4 文档分工

| 文档 | 读者 | 内容 |
|---|---|---|
| `README.md` | 最终用户 | 项目起源、功能概览、下载与使用、常见问题 FAQ |
| `wiki.md`(本文) | 开发者 | 架构、算法、线程模型、打包发布、红线与二次开发 |

---

## 2. 总体架构

### 2.1 代码组织

仓库是一个**单目录单文件应用**:绝大部分逻辑集中在 `src/exif_renamer.py`,不设包结构、不设模块分包。文件内自上而下的组织顺序即阅读顺序:

1. **模块级常量**:默认配置(`DEFAULT_SETTINGS`)、扩展名集合、类型查找表、日期格式清单、路径长度上限。
2. **惰性导入基础设施**:`_ensure_exifread` / `_ensure_pil` 及配套模块级状态、锁。
3. **纯函数核心**:日期字符串解析、XMP 解析、EXIF 值解码、拍摄时间提取、ID 生成、模板渲染、文件名清洗。
4. **文件遍历与分类**:目录扫描、系统/隐藏文件过滤、类型勾选匹配、安全的相对路径计算。
5. **重命名计划与执行**:`prepare_rename_plan`(逐文件分析、排序、冲突消解、失败归集)与 `execute_rename`(落地执行)。
6. **自定义对话框**:基于 `Toplevel` 的警告/确认/错误/失败对话框族。
7. **后台工作线程** `RenameWorker`。
8. **主窗口类** `ExifRenamer`(启动、界面构建、队列轮询、事件处理)。

> 由于无分包,公共常量与纯函数都处于模块顶层,便于被 GUI 与后台线程共同引用。

### 2.2 GUI 界面结构

主窗口是一个 `ttk.Notebook`,含两个标签页:

- **设置页**(主操作区):一个可滚动区域,自上而下依次是
  1. **目录输入**:源文件夹(默认指向系统截图目录)、「复制到新目录(保护原文件)」复选框与目标文件夹(仅在复制模式下启用)、「包含子文件夹」复选框;
  2. **处理类型**:图像 / RAW / 视频 / 音频 / 自定义 五个复选框,每类右侧直接显示该类型支持的扩展名;
  3. **文件名模板占位符**:前缀输入框(可清空)、模板输入框、「插入占位符 ▼」下拉菜单(点击即在模板光标处插入,菜单含「恢复默认模板」);
  4. **输出示例**:静态的"当前时间戳示例" + 只读的"当前重命名示例"(随模板/前缀输入实时刷新);
  5. **状态栏**:显示 EXIF 解析引擎检测结果(「✓ 使用 ExifRead 版本号」或「⚠ 使用 PIL,建议安装 exifread」)。
  - 底部固定一个「开始重命名」按钮。
- **日志页**:只读滚动文本框,以 INFO/WARNING/ERROR 三色显示运行日志;点击「开始重命名」会自动清空日志并切换到本页。

主窗口尺寸按屏幕比例动态计算(默认约占宽 60% × 高 80%)并居中;标题栏与任务栏图标取自根目录 `assets/` 下的 PNG 图标。

### 2.3 启动三段式(冷启动优化)

应用启动刻意设计为三个阶段,目的是**让窗口尽快出现在屏幕上**,把耗时导入放到后台:

```
阶段1  骨架上屏         创建 Tk 根窗口、标题/图标/字体/style、Splash 占位文案,
                      立刻 root.update() 强制首帧上屏(目标 < 200ms)
阶段2  后台惰性导入     启动 daemon 线程执行 exifread/PIL 的 import(_boot_heavy_modules);
                      该线程只做纯 import,不触碰任何 Tk 对象,失败不阻断
阶段3  事件驱动补全     主线程每 50ms 轮询 _boot_done 事件;一旦置位,
                      才构建完整控件树、刷新状态栏、隐藏 Splash、启动队列轮询
```

要点:

- 阶段 1 只做轻量初始化,**不** `import exifread`/`Pillow`(这两者在模块顶层通过占位状态 + 惰性加载实现,见 [§3.2](#32-依赖与惰性加载))。
- 阶段 2 无论成败都 `set()` 完成事件,否则阶段 3 会永久空转。
- 窗口图标在 PyInstaller 打包(`sys._MEIPASS`)与源码运行(相对 `src/` 向上找根目录 `assets/`)两种场景下取路径的方式不同,但逻辑收敛于同一个图标加载函数;图标缺失不阻断启动。

### 2.4 主流程(一次典型操作)

```
用户填写设置
  → 点击「开始重命名」
  → 主线程校验参数(源目录存在 / 复制模式必须选目标目录 / 模板非空)
  → 清空三条消息队列,复位关闭事件
  → 启动 RenameWorker 后台线程
        ├─ 清空本线程 EXIF 缓存
        ├─ collect_files_with_categories:遍历目录,按勾选类型收集媒体文件(过滤系统/隐藏文件)
        ├─ prepare_rename_plan:逐文件提取时间、排序、渲染模板、消解冲突,产出 rename_map
        ├─ (若有被忽略或使用备用时间源的文件) 弹「组合警告」,等待用户继续/取消
        ├─ 弹「重命名确认」对照表,等待用户确认
        └─ execute_rename:逐个 os.rename(就地)或 shutil.copy2(复制)
  → worker 发 __finished__ 哨兵与统计 → 主线程收尾:打印统计、失败弹窗、成功则打开结果文件夹
```

弹窗请求经 `request_queue` 送达主线程;worker 在等待期间轮询关闭事件以支持取消(详见 [§5](#5-线程模型与-ui-消息机制))。

### 2.5 进程内线程总览(概念图)

```
┌────────────────────────────── 主线程 (Tk) ──────────────────────────────┐
│  Tk 事件循环 (mainloop)                                                  │
│    ├─ 启动期: 每 50ms 轮询 _boot_done → 阶段3 补全 UI                    │
│    ├─ 运行期: 每 50ms 轮询三条队列 _poll_queues                          │
│    │     ├─ log_queue    → 写日志面板(含哨兵消息派发)                     │
│    │     ├─ request_queue→ 每次至多取 1 条, 交给独立回调弹模态框          │
│    │     └─ response_queue: 对话框结果由 _handle_dialog_request 写回     │
│    └─ WM_DELETE_WINDOW → _on_close: 置 shutdown_event, join worker      │
└──────────────────────────────────────────┬───────────────────────────────┘
                                           │ queue 传递(3 条, 均 FIFO)
┌──────────────────────────────────────────┴───────────────────────────────┐
│  RenameWorker (后台线程, 每次任务新建, daemon)                             │
│    扫描 → 分析 → (请求弹窗,阻塞等待结果) → 执行 → 发 __finished__          │
│    等待弹窗结果期间: response_queue.get(timeout=0.1) 轮询,               │
│                      若 shutdown_event 置位 → 发 __cancelled__ 返回      │
└──────────────────────────────────────────────────────────────────────────┘
   另: boot-heavy-modules daemon 线程 —— 仅启动期存活,负责重模块 import
```

图例:队列方向均为 worker → 主线程(`log_queue`、`request_queue`)或主线程 → worker(`response_queue`),语义见 [§5](#5-线程模型与-ui-消息机制)。

---

## 3. 运行、打包与发布

### 3.1 从源码运行

环境要求:Python 3.14+(开发与 CI 均使用 3.14)。主程序在 Windows 上获得完整支持;macOS/Linux 可运行基础功能。

```bash
# 1) (建议) 创建虚拟环境
python -m venv .venv
# Windows: .venv\Scripts\activate     macOS/Linux: source .venv/bin/activate

# 2) 安装依赖
pip install -r requirements.txt

# 3) 运行主程序
python src/exif_renamer.py

# 4) 调试工具(可选,需已安装 Pillow 与 exifread)
python src/exif_debugger.py
```

依赖清单(`requirements.txt`)只有两行:`Pillow>=9.0` 与 `exifread>=3.0.0`。二者都走惰性导入,详见下节。

### 3.2 依赖与惰性加载

**设计动机**:`exifread` / `Pillow` 导入较慢,若在模块顶层 import,会拖长冷启动。代码改为:

- 模块顶层只保留状态标志(`EXIFREAD_AVAILABLE`、`PIL_AVAILABLE`)与模块引用占位;
- 由 `_ensure_exifread` / `_ensure_pil` 负责真正导入,内部用**双重检查锁**(模块级 `threading.Lock`)防止后台导入线程与工作线程并发导入;
- 启动阶段的后台导入线程会预先触发一次,保证用户点击"开始"时通常已就绪。

**降级语义**(重要,影响时间提取链的行为):

| 安装情况 | 实际行为 |
|---|---|
| 装了 `exifread` | 状态栏显示「✓ 使用 ExifRead」,EXIF 读取走 exifread(RAW/HEIC 解析精度更高) |
| 只装 `Pillow` | 状态栏显示「⚠ 使用 PIL」,EXIF 读取走 PIL 回退,功能仍可用 |
| 两者都没装 | 应用仍能启动(有 GUI),但无法读 EXIF,拍摄时间全部落到**文件修改时间**(见 [§4.2.5](#425-文件修改时间兜底)) |

> 对开发者:任何调用点都应**先查 `EXIFREAD_AVAILABLE` / `PIL_AVAILABLE` 标志再取模块**,不要直接 `import`。新加的重模块也应沿用这一模式。

### 3.3 PyInstaller 打包

仓库提供两个 spec:

| spec 文件 | 产物 | 说明 |
|---|---|---|
| `exif_renamer.spec` | `exif_renamer-<BUILD_TAG>.exe` | 主程序,`console=False`(GUI 无黑框) |
| `exif_debugger.spec` | `exif_debugger-<BUILD_TAG>.exe` | 调试工具,`console=False` |

产物名中的 `<BUILD_TAG>` 取自环境变量 `WM_BUILD_TAG`,缺省为 `dev`(本地随手打包得到 `exif_renamer-dev.exe`;CI 里由 git tag 注入,产物 = `<脚本名>-<tag>.exe`,如 `exif_renamer-v1.0.exe`)。

spec 中值得注意的配置(两个 spec 结构相同,主程序额外把 `assets/icon.ico` 与 `icon.png` 通过 `datas` 注入产物):

- `upx=False`:未启用 UPX 压缩(曾评估用于缩短冷启动耗时,当前关闭以规避安全软件误报);
- `console=False`:窗口程序不弹控制台;
- 入口脚本由 spec 内显式指向 `src/` 下对应文件。

本地打包示例:

```bash
pip install pyinstaller
pyinstaller exif_renamer.spec            # 产物在当前目录 dist? 见下方说明
```

> 说明:本地直接运行 spec 时,`workpath`/`distpath` 沿用 spec 默认值(分别为 `build/` 与 `dist/`,均已由 `.gitignore` 排除)。CI 则用 `--workpath`/`--distpath` 显式覆盖为 `.pyi-build-*/` 与 `.pyi-dist/`,避免两程序共享中间目录互相污染。

**打包注意**:主程序源码运行与打包运行取资源的方式不同(源码时按相对位置找根目录 `assets/icon.png`,打包后读 `sys._MEIPASS` 下注入的 data),改图标/资源时两处都要同步。

### 3.4 发布流水线(CI)

`.github/workflows/release.yml` 定义自动发布,**仅 Windows**(注释明确说明 PyInstaller 不能跨平台产出 Windows exe)。触发方式:推送形如 `v*` 的 git tag。流程为:

1. checkout → 安装 Python 3.14 → 安装 `requirements.txt` + `pyinstaller`;
2. 用两个 spec 分别打包:`pyinstaller --workpath .pyi-build-renamer --distpath .pyi-dist exif_renamer.spec`,调试工具同理(`.pyi-build-debugger`),两者共享 `.pyi-dist` 输出;
   - `WM_BUILD_TAG=${{ github.ref_name }}` 注入产物名,即产物 = `<脚本名>-<tag>.exe`;
3. 校验 `.pyi-dist` 下确有 exe 产物并打印体积;
4. 用 `gh` 删除同名 tag 的旧 release(幂等,便于重发);
5. 用 `softprops/action-gh-release` 上传全部 exe。

源码 zip 由 GitHub 在每个 Release 页面自动生成「Source code (zip) / (tar.gz)」,与 `git archive` 产出等价,不再由 CI 单独打包。

产物命名说明:产物名跟随 git tag,例如 `v1.0` tag 触发后产物为 `exif_renamer-v1.0.exe` 与 `exif_debugger-v1.0.exe`。tag 名即版本号。

### 3.5 环境变量

| 变量 | 默认 | 作用 |
|---|---|---|
| `RENAME_TOOL_MAX_PATH` | `259` | 覆盖新文件路径长度上限(默认值即 Windows MAX_PATH 语义:260 含 null 终止符,有效字符 259),详见 [§4.6](#46-路径长度与跨盘处理) |
| `WM_BUILD_TAG` | `dev` | PyInstaller 产物名的版本标签,本地直接跑 spec 时默认 `dev`,CI 由 `github.ref_name`(即 git tag)注入 |

---

## 4. 核心算法与数据流

一次批处理的数据流在 [§2.4](#24-主流程一次典型操作) 已概览。本节深入算法细节,按执行顺序展开:扫描分类 → 逐文件时间提取 → 计划生成(排序/渲染/冲突/失败归集)→ 执行。

### 4.1 文件发现与分类

`collect_files_with_categories` 返回三份清单:

- `all_files`:目录下(递归或非递归)全部被纳入考虑的文件;
- `media_files`:`all_files` 中扩展名命中用户勾选类型的子集(真正会被重命名的);
- `ignored`:其余文件(`all_files − media_files`),用于弹窗提醒"这些不会被处理"。

遍历规则:

- 递归模式用 `os.walk`,且会**就地剪枝目录列表** `dirs[:] = [d for d in dirs if not d.startswith(('.', '$'))]`——即以 `.` 或 `$` 开头的目录(如 `.git`、`.venv`、`$RECYCLE.BIN`)整体跳过;
- 文件级过滤(递归与非递归一致):系统文件黑名单 `desktop.ini` / `thumbs.db` / `.ds_store` / `ehthumbs.db`(比较时统一 `lower()`);以 `.`、`._` 或 `$` 开头的文件一律跳过;
- 权限异常(`PermissionError`)只记 WARNING 并继续,不中断整批;
- 每处理 50 个文件触发一次进度回调(仅写日志)。

### 4.2 拍摄时间提取

每个媒体文件经 `get_media_datetime` 得到一个 `(datetime, is_fallback, reason)`:

- `datetime`:选定的拍摄时间(naive,不含时区,见 [§4.3](#43-日期字符串解析与时区语义));
- `is_fallback`:是否属于"备用时间源"(决定是否出现在告警弹窗);
- `reason`:时间来源标签(用于日志与告警文案)。

时间来源按以下**优先级链**逐级尝试,**只取第一个成功项**:

| 次序 | 来源 | 适用 | 是否视为备用(fallback) |
|---|---|---|---|
| 1 | exifread 解析 EXIF 的 `DateTimeOriginal` 等标签 | 图片/RAW | 标签名含 `Original` 视为精确时间(否);其余 EXIF 时间标签视为备用(是) |
| 2 | 内嵌 XMP 元数据 | 图片/RAW | 否 |
| 3 | 同名 `.xmp` sidecar 文件 | 图片/RAW | 否 |
| 4 | PIL 回退读取 EXIF | 图片/RAW | 同 exifread:精确 `DateTimeOriginal` 否,其余是 |
| 5 | 文件修改时间 `os.path.getmtime` | **所有未能命中上述来源的文件** | 是 |

> **非图片/RAW 文件**(视频、音频、自定义文件)不进入 EXIF 解析,直接采用文件修改时间(步骤 5)。

若干实现要点:

- 若 exifread 可用但整段解析抛异常,只记 WARNING 并**落到后续优先级**,不影响其他文件;
- 结果按 `filepath` 缓存进**线程隔离缓存**(`threading.local`),同一任务内重复查询直接命中,见 [§5.3](#53-exif-缓存)。

#### 4.2.1 exifread 通道

`exifread.process_file(f, details=True)` 后,按固定顺序尝试以下标签(首个可解析者胜):

```
EXIF DateTimeOriginal → Image DateTime → EXIF DateTimeDigitized
→ EXIF DateTime → EXIF_DateTimeOriginal → Image_DateTime
```

`is_fallback` 的判定规则是**标签名中是否含 `Original`**:含 `Original`(拍摄原始时间)为精确;其余(多为文件生成/数字化时间)按备用处理。若这些标签都解析失败,则继续尝试内嵌 XMP。

#### 4.2.2 XMP 解析

- **内嵌 XMP**:exifread 返回字典中形如 `Image XMP` / `Image XML` / `XMP` / `XML` 的标签,其值交给 `parse_xmp_content` 正则提取;
- **XMP sidecar**:找与文件同主名、同目录的 `<主名>.xmp`(`os.path.splitext` 后拼 `.xmp`),UTF-8 读取(`errors='ignore'`)后同样交给 `parse_xmp_content`。

`parse_xmp_content` 用正则匹配 8 种写法——`xmp:CreateDate`、`xmp:DateCreated`、`xmp:MetadataDate`、`photoshop:DateCreated` 各支持**属性形式**(`xmp:CreateDate="..."`)与**元素形式**(`<xmp:CreateDate>...</xmp:CreateDate>`)。

#### 4.2.3 PIL 回退通道

`PIL.Image.open(...).getexif()` 后,按 `DateTimeOriginal → DateTime → DateTimeDigitized` 顺序读取;EXIF 标签 ID 经 `PIL.ExifTags.TAGS` 反查为名称;取值统一经 `_decode_exif_value` 做安全解码(bytes 优先 utf-8、其次 latin-1,并剥离 `\x00` 与首尾空白)。PIL 解析抛异常记 ERROR 后继续降级。

#### 4.2.4 异常与边界

- 单个标签值解析失败(`parse_date_string` 抛 `ValueError`)→ 该标签视为不可用,尝试下一优先级;
- 任何解析器整体异常 → WARNING/ERROR 日志,不中断整批;
- 整个提取过程的结果**必定非空**:即使所有 EXIF/XMP 均失败,最终也落到文件修改时间,因此 `prepare_rename_plan` 总能拿到一个 `datetime`。

#### 4.2.5 文件修改时间兜底

`os.path.getmtime` → `datetime.fromtimestamp`,`is_fallback=True`,reason 为「File Modification Time」。这也是完全不含 EXIF 的照片(部分手机拍摄、社交平台下载图)的默认落点,README 的 FAQ 对此有用户视角的说明。

### 4.3 日期字符串解析与时区语义

`parse_date_string` 负责把 EXIF/XMP 中的日期文本变成 `datetime`:

1. `str(value).strip()` 去首尾空白;
2. **仅剥离字符串末尾**的时区偏移(`+08:00` / `-05:00` / `Z`),正则 `\s*(?:[+-]\d{2}:\d{2}|Z)\s*$`;
3. 把 `T` 替换为空格(兼容 ISO 8601);
4. 依次尝试 11 种 `strptime` 格式,首个成功者返回:
   - 完整精度:`%Y:%m:%d %H:%M:%S`、`%Y-%m-%d %H:%M:%S`、`%Y/%m/%d %H:%M:%S`;
   - 省秒:`%Y:%m:%d %H:%M`、`%Y-%m-%d %H:%M`、`%Y/%m/%d %H:%M`;
   - 纯日期:`%Y:%m:%d`、`%Y-%m-%d`、`%Y/%m/%d`;
   - ISO:`%Y-%m-%dT%H:%M:%S`、`%Y-%m-%dT%H:%M`(上一步已把 `T` 换成空格,故这两种主要服务于带时区后缀的输入);
5. 全部失败 → 抛 `ValueError`,由上层按"该来源不可用"处理。

**时区语义(刻意取舍,请勿"修复"成换算)**:

- 末尾时区偏移被**直接丢弃**,不换算成本地时间——最终得到的是 **naive datetime**;
- 这是有意设计:重命名只要求文件间相对排序一致与模板可读,不追求跨时区的时间换算;换算反而会让"相机时区设错"的照片时间整体偏移;
- 偏移剥离只用正则锚定**字符串末尾**,避免用 `split` 之类破坏字段中间含 `+`/`-` 的畸形值。

### 4.4 模板渲染与冲突消解

#### 4.4.1 模板与占位符

`apply_template` 按顺序执行:

1. 替换**固定占位符**(一次性替换表):`{YYYY}` `{YY}` `{MM}` `{DD}` `{hh}` `{mm}` `{ss}`(24 小时制)、`{prefix}`、`{filetype}`(输出 `IMAGE` / `RAW` / `VIDEO` / `AUDIO`,自定义类型为 `FILE`)、`{id}`;
2. 正则处理**序号占位符** `{seq}` 与 `{seq:<fmt>}`(如 `{seq:04d}`),`<fmt>` 交给 `format(seq, fmt)`,非法格式回退为纯数字字符串;
3. 移除**所有残余**形如 `{...}` 的内容——即未识别占位符会被静默剔除,模板写错不会报错。

之后经 `sanitize_filename` 清洗:把 Windows 非法字符 `\ / : * ? " < > |` 全部替换为 `_`,并截断到 200 字符以内。扩展名不参与清洗与截断,由调用方在 `base + ext` 处拼接,因此原始扩展名会被保留(如 `.jpeg` 不会被动改写)。

**示例**(示意):模板 `{prefix}-{YYYY}-{MM}-{DD}-{id}` + 前缀 `screenshot` → `screenshot-2026-07-05-A1B2.jpg`。

占位符全集与默认模板见 [§6.1](#61-gui-输入项与默认值)。

#### 4.4.2 计划生成流程

`prepare_rename_plan` 的处理分两段:

1. **收集与排序**:遍历媒体文件,逐个读取原始 mtime → `get_media_datetime` 取时间 → 记入 `file_infos`。对使用备用时间源的文件额外记录一条"预览"(用占位 ID 与序号 1 渲染文件名,用于告警弹窗展示)。全部收集后按 `(datetime, 文件路径)` 排序——排序保证输出顺序稳定、与目录枚举顺序无关。
2. **生成改名对**:按下述循环为每个文件确定 `old → new`,产出 `rename_map`。

#### 4.4.3 冲突消解(两层级)

模板里是否含 `{seq}` 决定了冲突时的对策(同一套循环内实现):

| 情形 | 行为 |
|---|---|
| 模板**含** `{seq}` | 文件名带序号;目标已存在或本批已占用时,`local_seq += 1` 重试(如 `_001`、`_002`…) |
| 模板**不含** `{seq}` | 目标已占用时追加数字后缀 `_2`、`_3`…(基础名先经模板渲染);`conflict_suffix` 复位逻辑见源码注释 |

每文件重试上限 **10000 次**;超限则该文件进入 `failed_analysis` 并跳过。去重依据是 `os.path.exists(new_path)` 或 `new_path` 已在本批 `used_target_paths` 中(处理"两个源文件算出同一目标名"的情形)。

#### 4.4.4 随机 ID 去重

模板含 `{id}` 时,每个文件在计划生成阶段调用 `generate_unique_id(existing_ids)` 拿到一个随机 ID(大写字母 + 数字),保证同批内 ID 唯一:默认 4 位,若 4 位空间被耗尽(同一批超过约 160 万个随机组合仍冲突的概率场景)自动扩位到最多 8 位;单长度内重试上限 10 万次,全部耗尽抛 `RuntimeError`。

#### 4.4.5 计划阶段的失败归集(`failed_analysis`)

以下情形文件**不进** `rename_map`,而是记入 `failed_analysis`(最终在完成弹窗中展示,不执行任何改名):

- 读取文件信息失败(mtime 读不到);
- 分析期发现文件已不存在(收集后被人为删除);
- 分析期 mtime 与收集期不一致(文件被外部改动,见下节);
- 目标路径超长(见 [§4.6](#46-路径长度与跨盘处理));
- 冲突消解达 10000 次上限;
- (复制模式)目标目录创建失败。

### 4.5 mtime 一致性保护

收集(`collect_files_with_categories`)与逐文件分析(`prepare_rename_plan`)之间存在时间窗。分析每个文件前先记录 `original_mtime`,渲染并消解冲突前再比对一次 `os.path.exists` 与当前 mtime:

- 文件不存在 → 跳过;
- mtime 已变化 → **放弃改名**,记入 `failed_analysis` 并提示「文件修改时间已变化,跳过以保证数据一致」。

这是防止"用户/外部程序正在写这个文件时工具把它改名/复制走"导致数据错乱的兜底,改动它之前请先想清楚代价。

### 4.6 路径长度与跨盘处理

- **路径长度上限**:新路径(文件所在目录 + 新文件名)超过 `MAX_PATH_LIMIT`(默认 `259`,可用环境变量 `RENAME_TOOL_MAX_PATH` 覆盖)即记入 `failed_analysis` 并跳过。这是 Windows `MAX_PATH=260`(含结尾 null)语义的显式化。
- **跨驱动器相对路径**:复制模式下要在目标目录还原源目录的**相对结构**,需要把"源文件所在目录"换算成相对路径。`os.path.relpath` 在跨驱动器时会抛 `ValueError` 或退化成 `.`,因此封装了 `safe_relpath`:先 `normpath`;常规 `relpath` 失败或得到 `.`/空时,若路径确实仍在基准目录树下,就手工截取前缀。跨驱动器复制丢失目录结构的历史 bug 正由此修复。
- **目标路径 == 源路径**:就地模式下新文件名与原名相同(已符合模板)则跳过;复制模式下目标文件与源文件同路径(目标即源目录)则跳过。

### 4.7 执行阶段

`execute_rename` 遍历 `rename_map`:

- 就地模式:`os.rename(old, new)`;
- 复制模式:`shutil.copy2(old, new)`(保留元数据),目标目录在计划阶段已按相对结构建好;

单条失败只记 ERROR 日志并收集进失败列表,不中断后续文件。执行成功后,主线程会尝试用系统文件管理器打开结果目录(复制模式打开目标目录,就地模式打开源目录),见 [§5.4](#54-跨平台打开与定位文件)。

---

## 5. 线程模型与 UI 消息机制

### 5.1 角色划分

运行时只有两类长期线程:

- **Tk 主线程**:独占全部 Tk 调用(构建控件、写日志文本框、弹对话框)。通过定时器驱动 `_poll_queues` 消费队列。
- **`RenameWorker` 后台线程**:每次点击"开始"新建一个(daemon),负责扫描、分析、弹窗请求、执行改名,结束后线程对象可复用占位、随任务销毁。

另有启动期短暂存活的 boot 导入线程(见 [§2.3](#23-启动三段式冷启动优化)),它**不得**触碰任何 Tk 对象。

### 5.2 三条队列与消息协定

`start_rename` 会创建/复位三条 `queue.Queue`(并在每次开始时**全部清空**,防止上一任务残留消息串台):

| 队列 | 方向 | 内容 |
|---|---|---|
| `log_queue` | worker → 主线程 | 日志元组 `(message, level)`,或**哨兵消息** `('__finished__', stats)` / `('__no_files__', None)` / `('__cancelled__', None)` / `('__error__', str)` |
| `request_queue` | worker → 主线程 | 弹窗请求字典,`type` 为 `combined_warning` 或 `rename_confirm`,附带渲染所需数据 |
| `response_queue` | 主线程 → worker | 对话框结果布尔值 |

主线程消费侧 `_poll_queues` 的节奏:

1. **每 50ms 触发一次**;先 `get_nowait()` 排空 `log_queue`(每 5 条插一次 `root.update()` 保持界面可响应),日志消息中一旦遇到哨兵,派发给对应回调并复位按钮;
2. 再从 `request_queue` **取至多一条**,用 `root.after(0, ...)` 延到**独立回调** `_handle_dialog_request` 里弹窗(原因见下),随后立即返回,不再续排;
3. `_handle_dialog_request` 弹完模态框后把结果 `put` 进 `response_queue`,并 `after(50, _poll_queues)` 恢复轮询。

> **为什么弹窗必须挪到独立回调?** 自定义对话框用 `parent.wait_window(dialog)` 阻塞运行。若在 `_poll_queues` 内直接弹,主线程会卡在 `wait_window`,50ms 轮询与日志刷新随之停摆——表现为界面"冻住"。挪到 `after(0, ...)` 回调后,`wait_window` 只阻塞该回调,事件循环仍活着。这是排查"弹窗后界面不刷新"类问题时首先要想到的点。

worker 侧的**请求-应答循环**与之配对:发请求后进入 `while True`,用 `response_queue.get(timeout=0.1)` 轮询;每次 `queue.Empty` 都检查 `shutdown_event`,置位则放 `('__cancelled__', None)` 并直接返回(支持窗口关闭时的优雅退出,见 [§5.5](#55-优雅关闭))。

顺序约定:worker 严格按照「先 `combined_warning`(若需)、后 `rename_confirm`」的顺序发起请求,且每次都等待应答;主线程一次只处理一条请求。**反串台设计依赖 FIFO 与单消费者,改动消费顺序前请三思**。

### 5.3 EXIF 缓存

- 存储于模块级 `threading.local()` 实例的 `__dict__`,按 `(filepath) → (datetime, is_fallback, reason)` 缓存 `get_media_datetime` 的结果;
- **为什么用 `threading.local`**:早期版本是模块级普通字典,GUI 线程与 worker 线程共享导致脏读;改成每线程独立字典后天然线程安全;
- **清理时机**:`RenameWorker.run` 的**第一行**调用 `_clear_exif_cache()`——只有放在任务线程起始处才真正清的是"本任务线程"的缓存(早期曾放在主线程的 `start_rename`,清了等于没清,是已修复的历史 bug);
- 无持久化、无磁盘缓存文件;任务结束线程销毁,缓存随线程回收。同一任务内若有文件被外部修改,由 [§4.5](#45-mtime-一致性保护) 的 mtime 二次比对兜底。

### 5.4 跨平台打开与定位文件

对话框与完成提示需要"打开文件 / 在文件管理器中定位"时,按平台分发:

| 动作 | Windows | macOS | Linux |
|---|---|---|---|
| 打开文件 | `os.startfile` | `subprocess` `open` | `xdg-open` |
| 打开所在文件夹并选中 | `explorer /select,<路径>`(**合并为单个字符串参数**) | `open -R <路径>` | 退化为打开所在目录 |
| 打开文件夹 | `os.startfile` | `open` | `xdg-open` |

关键细节:

- Windows 的 `explorer /select` 必须把开关与路径合并成一个参数(`f'/select,{path}'`),拆成两个参数会失效;
- 打开/定位前经 `_safe_realpath` 取真实路径,规避 NTFS junction / 挂载点造成的路径偏差(`realpath` 仅在 Windows 执行,其它平台直接返回原值);
- 所有打开动作整体 try/except,失败静默(不因打不开文件夹而报错)。

### 5.5 优雅关闭

窗口标题栏关闭(`WM_DELETE_WINDOW`)绑定到 `_on_close`:

1. 若 worker 存活:日志提示「正在等待后台任务结束...」;
2. `_shutdown_event.set()`:worker 各等待循环检测到后放 `__cancelled__` 哨兵并返回;
3. `worker.join(timeout=2.0)`:最多等 2 秒;
4. `root.destroy()`。

目的是避免 daemon 线程在**文件操作中途被硬杀**(可能留下半截改名/复制)。若 worker 正处于不检查事件的长操作(如超大批量复制),2 秒超时后仍会销毁窗口,属已知边界。

---

## 6. 接口契约与可配置点

本工具是纯 GUI 应用:**没有命令行参数、没有 dry-run、没有可编程 API/库暴露面**(内部函数虽为纯函数,但属模块私有实现,未承诺稳定接口)。功能契约都通过 GUI 与模块常量表达。

### 6.1 GUI 输入项与默认值

模块顶层 `DEFAULT_SETTINGS` 等常量给出界面初始值(运行期进程内可改,见 [§6.3](#63-持久化与日志)):

| 输入项 | 默认值 |
|---|---|
| 源文件夹 | 当前用户图片目录下的 `Screenshots`(`~` 展开) |
| 复制到新目录 | 关 |
| 目标文件夹 | 空(复制模式开启后必填) |
| 包含子文件夹 | 关 |
| 前缀 | `screenshot` |
| 模板 | `{prefix}-{YYYY}-{MM}-{DD}-{hh}{mm}-{id}` |
| 勾选类型 | 图像、视频 开;RAW、音频、自定义 关 |

模板占位符全集(含「插入占位符」菜单中的中文说明):

| 占位符 | 含义 |
|---|---|
| `{YYYY}` `{YY}` | 四位 / 两位年份 |
| `{MM}` `{DD}` | 月、日 |
| `{hh}` `{mm}` `{ss}` | 时、分、秒(24 小时制) |
| `{prefix}` | 前缀输入框的值 |
| `{filetype}` | 类型标签:`IMAGE`/`RAW`/`VIDEO`/`AUDIO`(自定义类型为 `FILE`,见 [§6.2](#62-扩展名矩阵)) |
| `{id}` | 4–8 位随机大写字母+数字,批内唯一 |
| `{seq}` | 序号 `1,2,3,…` |
| `{seq:0Nd}` | 补零序号,如 `{seq:03d}`→`001`;`<fmt>` 任意合法 format 说明符 |

### 6.2 扩展名矩阵

扩展名集中在模块顶层元组,`EXT_TO_TYPE` 为预计算的扩展名 → 类型标签查找表(避免逐文件线性遍历):

| 类型 | 扩展名 | 默认勾选 |
|---|---|---|
| 图像 `IMAGE_EXTS` | `.jpg` `.jpeg` `.png` `.bmp` `.gif` `.webp` `.heic` | 是 |
| RAW `RAW_EXTS` | `.arw` `.cr2` `.cr3` `.dng` `.nef` `.nrw` `.orf` `.pef` `.raf` `.rw2` `.srw` `.x3f` | 否 |
| 视频 `VIDEO_EXTS` | `.mp4` `.avi` `.mov` `.mkv` `.flv` `.wmv` `.m4v` `.mpg` `.mpeg` | 是 |
| 音频 `AUDIO_EXTS` | `.mp3` `.wav` `.flac` `.aac` `.ogg` `.m4a` `.wma` | 否 |
| 自定义 `CUSTOM_FILE_EXTS` | 默认空元组(UI 提示"请在源代码中添加") | 否 |

> 自定义类型的文件**不参与 EXIF 解析**([§4.2](#42-拍摄时间提取) 提到非图片/RAW 直接用 mtime),时间标签为 `FILE`。

### 6.3 持久化与日志

- **无配置文件**:GUI 选择不持久化,关窗即恢复默认值。这是刻意取舍(README 的 FAQ 也未承诺记忆设置);需要"记住上次设置"属于自然扩展点(见 [§8.3](#83-其他扩展点))。
- **运行日志只在内存**:写进 GUI「日志」标签页的 `ScrolledText`,不落盘、无标准 `logging` 配置。需要文件日志同样属于扩展点。
- **调试工具的导出**:调试工具把左右两个分析面板的文本导出为 UTF-8 `.txt`(选图后可点「导出日志」)。
- **运行期写文件系统的地方只有两处**:重命名/复制目标本身;复制模式下自动创建的目标目录。无中间文件、无临时文件。

---

## 7. 数据安全边界与红线

### 7.1 设计承诺(做什么、不做什么)

| 承诺 | 说明 |
|---|---|
| 不改文件二进制内容 | 只动文件名;EXIF/内容原样保留(复制模式 `copy2` 保留元数据) |
| 不覆盖已存在文件 | 所有目标名都要通过 [§4.4.3](#443-冲突消解两层级) 的存在性检查;整批内也互相去重 |
| 就地 vs 复制二选一 | 就地 `os.rename` 会改动原目录;复制模式 `shutil.copy2` 原文件不动 |
| 执行前两级确认 | 「组合警告」(被忽略文件 / 备用时间源文件)→「完整改名对照表」,均支持取消 |
| **无撤销** | 改名不可逆。界面上无 undo,文档也不承诺;唯一的"保护"是复制模式 + 事前确认 |

README 对此有面向用户的说明与免责表述(个人工具、不建议在未备份数据上运行)。工程侧的对应物是本节红线:任何改动都不得破坏上述承诺。

### 7.2 红线清单

#### A. 数据安全

1. 不得移除"不覆盖已存在文件"的检查(`os.path.exists` + 批内 `used_target_paths` 双保险)。
2. 不得移除 mtime 一致性保护([§4.5](#45-mtime-一致性保护))——它是并发写场景的最后防线。
3. 执行前的人工确认(两道弹窗)不可绕过或默认跳过;确需新增"跳过确认"必须同步提供等效保护。
4. 不要轻率移除 10000 次冲突上限:它防的是极端输入下的死循环。
5. 就地重命名路径必须经过路径长度上限检查(Windows 下超长路径会直接失败)。

#### B. 线程与 UI

6. 所有 Tk 调用必须留在主线程;worker 只允许往队列里放消息。
7. 弹窗必须经 `after(0, ...)` 独立回调,不得在 `_poll_queues` 内直接 `wait_window`。
8. 三队列的"先 warning 后 confirm、一次一条"消费顺序不可随意打乱(反串台依赖 FIFO)。
9. 新加的重型 import 必须走惰性导入 + 锁的模式,不得在模块顶层直接 import 到 GUI 主路径。
10. `threading.local` EXIF 缓存必须在每个任务线程起始处清理,不要挪回主线程。

#### C. 打包与跨平台

11. Windows 下打开文件管理器定位文件时,`explorer /select` 参数必须合成单字符串。
12. 改图标/资源时,`spec` 的 `datas` 注入与源码运行时的相对路径两处要同步。
13. 时区剥离只在字符串末尾做正则匹配,不要用 `split`/`replace` 全局处理(会破坏字段中含 `+` 的值);也不要"顺手"把偏移换算成本地时间(见 [§4.3](#43-日期字符串解析与时区语义))。
14. `.gitignore` 已排除构建产物(见 §9);提交前不要误加 `.venv/`、`.pyi-build-*/`、`.pyi-dist/`、`__pycache__/` 等。

### 7.3 无撤销的缓解措施

由于没有 undo,工程上通过以下手段降低误操作代价:默认源目录可改、复制模式默认关闭但随时可开、执行前完整对照表、失败与跳过文件单独统计并弹窗列出(前若干条)、就地重命名后立即打开目录便于核对。

---

## 8. 二次开发指引

### 8.1 加一种扩展名/文件类型

1. 在 `IMAGE_EXTS` / `RAW_EXTS` / `VIDEO_EXTS` / `AUDIO_EXTS` 之一追加扩展名(全小写、带点);
2. 若属于"自定义文件",追加进 `CUSTOM_FILE_EXTS`(默认空);
3. `EXT_TO_TYPE` 与界面勾选区的扩展名展示均为**预计算/动态生成**,会自动跟随(界面复选框文案直接拼扩展名列表,新增后无需改 UI 代码);
4. 想改类型默认勾选,改 `DEFAULT_SETTINGS['categories']`。

回归:勾选该类型处理一个该扩展名文件,确认能进入改名列表、`{filetype}` 输出正确、非媒体文件过滤不受影响。

### 8.2 加一个占位符

1. 在 `apply_template` 的固定替换表(或序号替换逻辑)中加入新键;
2. 若要在「插入占位符 ▼」菜单中出现,把 `(占位符, 中文说明)` 追加进菜单项列表;
3. 命名规则:纯小写字母;与现有 `{seq}` / `{id}` 语义不同的新变量名,避免与日期简写冲突。

回归:输入含新占位符的模板,确认预览(状态区与输出示例)与真实改名一致;再确认**未识别占位符仍被静默移除**(不抛错)。

### 8.3 其他扩展点

- **记住上次设置**:GUI 状态都在 `tk.*Var` 与 `categories` 上,关窗即丢。若要持久化,建议在启动/退出时读写一个用户配置;注意不要引入绝对路径假设。
- **文件日志**:在 `log()` 与 worker 的 `log` 闭包处旁挂一个文件写入即可;`.gitignore` 已忽略 `*.log`。
- **改造出 CLI / dry-run**:核心纯函数(`collect_files_with_categories`、`prepare_rename_plan`、`execute_rename`)已与 GUI 解耦,理论上可被脚本复用;但它们是模块私有实现,未承诺稳定签名,封装成 CLI 前需先定义好返回结构。README 与本文目前均不承诺 CLI。
- **改启动流程**:若调整三段式启动,务必保证:① 骨架期不 import 重模块;② boot 线程成功失败都必须 `set()` 完成事件;③ 补全 UI 前不启动 `_poll_queues`。
- **调时间解析**:想支持更多日期格式,往 `DATE_FORMATS` 追加 `strptime` 格式串即可(顺序即优先级);但保持末尾时区剥离的正则锚定。

### 8.4 修改后的回归验证清单

覆盖最少场景,改动后再跑一遍:

1. 就地重命名:纯 EXIF 图片、RAW、视频(时间来源各不相同)各一张 → 名字符合模板、无覆盖;
2. 复制模式:勾选后指定目标,源目录含子目录 → 目标目录结构还原、原文件不动;
3. 递归开/关:子文件夹中的文件是否被处理符合预期;
4. 无 EXIF 图片 → 落入文件修改时间 → 出现在"备用时间源"告警、预览正确;
5. 模板冲突:两个同源文件用不含 `{seq}` 模板 → 第二个得到 `_2` 后缀;含 `{seq:03d}` → 序号递增;
6. 模板含未知占位符 → 被移除不报错;含非法字符 → 被替换为 `_`;
7. 处理过程中点关闭窗口 → 后台任务取消、无半截文件、无异常;
8. 目录存在非媒体文件(如 `.txt`)→ 出现在"忽略"列表并可在警告弹窗中右键定位;
9. 超大文件名(路径超上限)→ 计入失败而非崩溃;
10. 无依赖环境(仅 Tk):启动可见状态栏提示缺 exifread,改名全部走 mtime 兜底。

---

## 9. 文件与速查

### 9.1 目录结构

```
仓库根目录
├── README.md                 面向最终用户的文档(功能/下载/使用/FAQ)
├── wiki.md                   本文档(面向开发者)
├── LICENSE                   本项目 MIT 许可证(含 AI 辅助生成内容附加说明)
├── THIRD_PARTY_LICENSES.md   第三方组件(pillow/exifread 等)版权声明与许可
├── requirements.txt          依赖清单(Pillow、exifread)
├── .gitignore                Python/venv/IDE/构建产物忽略
├── .gitattributes            换行符统一 + git archive 排除规则
├── exif_renamer.spec         PyInstaller spec(主程序)
├── exif_debugger.spec        PyInstaller spec(调试工具)
├── .github/
│   └── workflows/
│       └── release.yml       tag 触发的自动发布流水线(Windows)
├── src/
│   ├── exif_renamer.py       主程序(单文件:核心函数 + GUI + 后台线程)
│   └── exif_debugger.py      调试工具(单图 EXIF 分析)
├── assets/
│   ├── icon.ico              EXE 图标(打包用)
│   └── icon.png              窗口图标(运行与打包均会用到)
├── images/                   README 截图素材(已被 .gitignore 忽略,未纳入版本库)
└── history/
    └── (旧版源码归档)        早期单文件版本,仅作演进对照,不参与构建
```

> 说明:`images/`(README 截图素材)与 `history/` 均已被 `.gitignore` 忽略且未纳入版本库,克隆后不存在;`.pyi-build-*/`、`.pyi-dist/`(PyInstaller 中间/输出)、`.venv/`、`__pycache__/`、`build/`、`dist/` 属本地构建产物,从未入库,克隆后不存在。

### 9.2 符号速查(按模块分组,不含行号)

核心处理函数:

| 符号 | 语义 |
|---|---|
| `parse_date_string(s)` | EXIF/XMP 日期字符串 → naive `datetime`;末尾时区偏移剥离;失败抛 `ValueError` |
| `parse_xmp_content(text)` | XMP 文本正则提取日期(8 种写法) |
| `parse_xmp_sidecar(path)` | 读同名 `.xmp` 并解析 |
| `_decode_exif_value(v)` | EXIF 值安全解码(bytes:utf-8→latin-1,剥离 `\x00`) |
| `get_media_datetime(path)` | 拍摄时间提取(优先级链),带线程级缓存,返回 `(datetime, is_fallback, reason)` |
| `generate_unique_id(existing)` | 4–8 位随机 ID,批内去重 |
| `apply_template(tpl, dt, prefix, id, seq, type)` | 模板渲染(占位符 + 残余 `{...}` 移除) |
| `sanitize_filename(name)` | 非法字符替换 + 截断 200 |
| `get_filetype(ext)` | 扩展名 → `IMAGE/RAW/VIDEO/AUDIO/FILE`(查 `EXT_TO_TYPE`),未知扩展名返回空串 |
| `collect_files_with_categories(...)` | 目录遍历与分类,返回 `(all, media, ignored)` |
| `safe_relpath(path, start)` | 跨驱动器安全的相对路径 |
| `prepare_rename_plan(...)` | 生成完整改名计划(排序/冲突/失败归集) |
| `execute_rename(map, copy_mode)` | 落地执行,返回 `(成功数, 失败列表)` |

线程/GUI:

| 符号 | 语义 |
|---|---|
| `RenameWorker` | 后台工作线程(扫描/分析/请求弹窗/执行/哨兵) |
| `ExifRenamer` | 主窗口类(三段式启动、界面、`_poll_queues` 轮询、关闭处理) |
| `CustomDialogBase` 及子类 | 模态对话框族(居中/`wait_window`) |
| `_ensure_exifread` / `_ensure_pil` | 惰性导入(双重检查锁) |
| `_clear_exif_cache` | 清空当前线程 EXIF 缓存 |
| `_on_close` | 关闭时优雅退出(置事件 → join 2s → destroy) |
| `_handle_dialog_request` | 独立回调内弹窗并回写应答 |

常用常量:

| 常量 | 语义 |
|---|---|
| `DEFAULT_SETTINGS` | GUI 初始值全集 |
| `IMAGE_EXTS` … `AUDIO_EXTS`、`CUSTOM_FILE_EXTS` | 类型扩展名元组 |
| `EXT_TO_TYPE` | 扩展名 → 类型标签查找表 |
| `DATE_FORMATS` | 日期解析格式清单(11 种) |
| `MAX_PATH_LIMIT` | 新路径长度上限(默认 259,可被环境变量覆盖) |
| `DEFAULT_IGNORED_FILENAMES` | 系统文件黑名单 |
| `EXIFREAD_AVAILABLE` / `PIL_AVAILABLE` | 解析引擎可用状态(惰性导入后刷新) |

---

## 附录 A. 常见问题排查

> 用户视角的 FAQ 见 README;这里是从代码行为推导的排查表。

| 现象 | 可能原因与处置 |
|---|---|
| 打开立即闪退 / 无窗口 | 环境缺 Tk(Python 需带 Tk 支持);检查启动阶段异常输出;图标缺失不会闪退(有兜底) |
| 状态栏提示"使用 PIL,建议安装 exifread" | 仅装了 Pillow。执行 `pip install exifread` 即可,无需重启代码逻辑(下次启动自动检测) |
| 某些照片名字用了文件修改时间而非拍摄时间 | 该文件无标准 EXIF 或解析失败(可先用调试工具确认);属预期降级,会出现在告警弹窗的"备用时间源"列表 |
| 处理中界面变慢/停顿 | 日志刷新与弹窗在主线程;文件量极大(上万)时日志密集会卡顿,属已知边界(README FAQ 亦有说明),建议分批 |
| 点"开始"后按钮保持"处理中..."且无日志 | worker 正在等待弹窗应答而弹窗未出现?检查是否有旧任务残留(每次开始会清队列);或目录超大扫描未完成,看日志进度 |
| 复制模式目标目录结构与预期不符 | 目标目录按源目录相对结构创建;源/目标在同一驱动器正常;跨盘时走 `safe_relpath` 回退路径,若目标根目录本身是"源目录的子目录/同级"等特殊布局,注意基准目录是源目录 |
| 关闭窗口后任务消失 | 预期行为:`_on_close` 先请求取消并最多等 2 秒,超过即强退;超大批量执行中关窗可能留下未完成项,建议等执行结束再关 |
| 模板里写了奇怪字符/占位符 | 未识别 `{...}` 被移除、非法字符被替换为 `_`,文件不会因此报错 |
| 重命名后打不开结果目录 | `_open_folder` 静默容错;可手动到源目录/目标目录核对文件是否就位 |

## 附录 B. 术语表

| 术语 | 含义 |
|---|---|
| EXIF | 图片文件内嵌的元数据标准,含拍摄时间(`DateTimeOriginal`)等;RAW/HEIC 等容器亦常携带 |
| 拍摄时间 / 精确时间 | 链上含 `Original` 的 EXIF 时间标签,视为最可靠的"何时按下快门" |
| 备用时间源(fallback) | 非 `Original` 的 EXIF 时间、XMP 时间、文件修改时间;命中即进告警弹窗 |
| XMP / sidecar | XMP 为可扩展元数据格式;sidecar 指与图片同主名的独立 `.xmp` 旁路文件(常见于部分相机/处理软件) |
| naive datetime | 不含时区信息的 `datetime`,本项目统一使用(见 [§4.3](#43-日期字符串解析与时区语义)) |
| `rename_map` | 计划阶段产出的 `(旧路径, 新路径)` 列表,是确认弹窗与执行阶段的唯一数据源 |
| 惰性导入 | 把重模块 import 推迟到后台线程/首次调用,缩短冷启动 |
| 三段式启动 | 骨架上屏 → 后台导入重模块 → 事件驱动补全 UI 的启动策略 |
| daemon 线程 | Python 守护线程;主进程退出不等待其结束(故需显式优雅关闭) |

---

*本文档与 README 互补:功能用法以 README 为准,实现细节以本文为准;如两者冲突,以当前源码为准。*
