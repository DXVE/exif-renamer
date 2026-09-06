# Exif-Renamer · 工程 Wiki

> 面向开发者：接入、二开、排查。比 README 更工程化，比散落的源码注释更系统。

---

## 0. 阅读对象与本文约定

- **目标读者**：要把这个项目接进自己工具链 / 改造算法 / 排查问题的工程师。
- **不适用**：纯使用者直接看 `README.md`；本项目**无** AI 协作硬约束文档（无 `AGENTS.md` / `CLAUDE.md`），所以本文第 8 章会把分散在源码、spec、CI 注释里的红线集中列一份。
- **术语约定**：「主程序」指 `src/exif_renamer.py`；「调试工具」指 `src/exif_debugger.py`；「后台线程」指 `RenameWorker`（`threading.Thread`）。
- **行号引用**：所有 `file:line` 都使用**仓库内相对路径**（如 `src/exif_renamer.py:290`）。仓库根目录以下一律用 `src/`、`assets/` 等相对写法，不出现任何 `C:\Users\...` 之类死路径。
- **章节交叉引用**：正文与附录中的 §X.Y 形式，指向本文档内部章节；不写绝对章节编号，章节改名不影响。

---

## 1. 项目定位与适用场景

**定位**：基于 EXIF 拍摄日期 + 自定义命名模板，对图片（含 RAW）/ 视频/音频等文件做**批量重命名**的 Windows GUI 工具（`tkinter`）。

**适用场景**：

- 拍照归档：相机直出、手机拍摄、社交平台保存等来源文件混乱，需统一成「拍摄日期+序号」风格。
- RAW 整理：保留 `EXIF DateTimeOriginal` 作为可信时间源。
- 「就地重命名」与「复制到新目录（原文件保留）」两种安全模式（默认前者）。
- 自带 EXIF 调试工具，便于排查「为什么这张照片读不到拍摄日期」。

**关键边界**：

- 单文件不超过 50MB（基础库限制）。
- 不修改图像/视频/音频的二进制内容（只改文件名 + mtime）。
- 不覆盖已存在文件（冲突时递增 `_2` / `{seq}`）。
- 无 undo / 回滚机制——执行前有两层人工确认对话框。

---

## 2. 系统架构总览

### 2.1 ASCII 线程模型图

```
┌────────────────────────────────────────────────────────────────────┐
│                       Tk 主线程 (ExifRenamer)                       │
│                                                                    │
│  ┌──────────────┐    ┌────────────────┐    ┌──────────────────┐  │
│  │  GUI Widgets │◄──►│  log_queue     │    │  request_queue    │  │
│  │  StringVar/  │    │  (日志消息)     │    │  (弹出确认请求)   │  │
│  │  BooleanVar  │    └────────┬───────┘    └──────────┬─────────┘  │
│  └──────┬───────┘             │                       │            │
│         │  start_rename()     │ poll(50ms)            │            │
│         ▼                     ▼                       ▼            │
│  ┌─────────────────────────┐  │   ┌────────────────────────────────┐
│  │   RenameWorker.run()    │  │   │  response_queue (yes/no 返回)  │
│  │   (后台 daemon 线程)    │  │   └──────────────┬─────────────────┘
│  │                         │  │                  ▲
│  │  ① collect_files        │  │   ┌──────────────┴───────────────┐
│  │     with_categories     │  │   │  CombinedWarningDialog        │
│  │  ② get_media_datetime   │  │   │  (列出忽略+备用时间源文件)    │
│  │     EXIF→XMP→PIL→mtime │  │   │  ──用户点继续/取消──►          │
│  │  ③ prepare_rename_plan  │  │   │  CustomConfirmDialog          │
│  │     apply_template      │  │   │  (完整 old→new 对照表)        │
│  │     conflict_resolve    │  │   │  ──用户点开始──►              │
│  │  ④ execute_rename       │  │   └──────────────────────────────┘
│  │     os.rename 或        │  │
│  │     shutil.copy2        │  │                                  
│  │                         │  │                                  
│  │  shutdown_event (优雅取消)│  │                                  
│  └─────────────────────────┘  │                                  
│                                │                                  
└────────────────────────────────┼──────────────────────────────────┘
                                 │
                                 ▼
                  ┌──────────────────────────┐
                  │  文件系统                  │
                  │  源目录 / 目标目录         │
                  │  (无配置/日志/中间文件)   │
                  └──────────────────────────┘
```

**关键不变量**：

- 主线程只跑 Tk 事件循环；所有耗时的扫描 / EXIF 读取 / 排序 / 渲染都在 `RenameWorker` 后台线程。
- 后台线程**不直接操作 Tk Widget**——所有 UI 操作经 `log_queue` / `request_queue` / `response_queue` 三个 `queue.Queue`，由主线程的 `_poll_queues` 每 50ms 轮询。
- 主线程通过 `after(0, lambda: dialog.show())` 在事件循环回调里弹模态对话框，把用户选择塞回 `response_queue`，后台线程同步阻塞读取。
- `shutdown_event`（`threading.Event`）让用户点窗口关闭时能优雅终止后台线程。

### 2.2 双 GUI 脚本结构

| 文件 | 行数 | 角色 | 入口 |
|---|---|---|---|
| `<REPO>/src/exif_renamer.py` | 1652 | 主程序：扫描 + EXIF + 命名 + 重命名/复制 + GUI | `main()` (1646) → `ExifRenamer().run()` (1642) → `root.mainloop()` |
| `<REPO>/src/exif_debugger.py` | 174 | 辅助：单图 EXIF 检视 + 导出日志 | `if __name__ == "__main__"` (172) |

`exif_renamer.py` 内部模块划分（按行号）：

| 区段 | 行号 | 职责 |
|---|---|---|
| 常量 / 扩展名 | 16-65 | `DEFAULT_SETTINGS` / `IMAGE_EXTS` / `RAW_EXTS` / `VIDEO_EXTS` / `AUDIO_EXTS` / `EXT_TO_TYPE` |
| 延迟导入 | 69-118 | `_ensure_exifread()` / `_ensure_pil()`（双检锁） |
| 日期解析 / EXIF / XMP | 143-287 | `parse_date_string` / `parse_xmp_content` / `parse_xmp_sidecar` / `get_media_datetime` |
| ID / 模板 / 清洗 | 290-345 | `generate_unique_id` / `apply_template` / `sanitize_filename` / `get_filetype` / `_is_selected_category` |
| 目录遍历与分类 | 377-439 | `collect_files_with_categories` / `safe_relpath` / `get_relative_dir` |
| 重命名计划 | 462-613 | `prepare_rename_plan` |
| 执行 | 616-637 | `execute_rename` |
| 路径工具 | 641-649 | `_safe_realpath` |
| 对话框类 | 653-915 | `CustomDialogBase` / `CustomConfirmDialog` / `CombinedWarningDialog` / `ErrorDialog` / `FailureDialog` |
| 后台线程 | 920-1056 | `RenameWorker` |
| 主窗口 | 1061-1643 | `ExifRenamer` |
| 入口 | 1646-1652 | `main()` / `if __name__ == "__main__"` |

### 2.3 启动三阶段

```
main() (1646)
  │
  ├─ ExifRenamer.__init__ (1061)
  │    ├─ 创建 Tk root + 主窗口骨架（部分 widgets）
  │    ├─ 显示中央占位条 _show_splash (1163) ─► 避免黑屏
  │    └─ 启动 _boot_thread (1182 后台线程)
  │          └─ _ensure_exifread() + _ensure_pil()   加载重模块
  │
  ├─ root.mainloop() 进入 Tk 事件循环 (1642)
  │
  └─ _wait_for_boot (1194) ─ 50ms 轮询 _boot_done
        └─ 完成时构建完整 widgets + 启动 _poll_queues (1485)
              └─ 每 50ms 轮询 log_queue / request_queue
```

**为什么分阶段**：tkinter 启动慢，EXIF/PIL 又是大模块；后台线程加载期间用户能看到中央占位条，避免「点了没反应」的体验问题。

---

## 3. 运行与打包（完整闭环）

### 3.1 从空环境到 GUI 启动

**Python 版本口径**：

- **最低支持**：Python 3.10+（无 `python_requires` 显式声明，README 声明）
- **本地验证**：3.14.7（`.venv/L`）
- ** CI 实跑**：3.14（`.github/workflows/release.yml`）

**结论**：3.10~3.14 都应可用；3.14 验证最充分。Python 3.10~3.12 是用户环境主战场，建议本地也用 3.10+ 验证兼容性。

#### 步骤 1：创建虚拟环境

```bash
# PowerShell / cmd / Git Bash 一致
python -m venv .venv
```

#### 步骤 2：激活

```bash
# PowerShell
.\.venv\Scripts\Activate.ps1

# cmd
.\.venv\Scripts\activate.bat

# Git Bash
source .venv/Scripts/activate
```

#### 步骤 3：安装依赖

```bash
pip install -r requirements.txt   # Pillow>=9.0 + exifread>=3.0.0
```

**依赖仅两行**（`requirements.txt`）：

| 依赖 | 用途 | 缺失降级 |
|---|---|---|
| `Pillow>=9.0` | PIL Image + ExifTags，回退路径 | 强依赖，缺失则报错 |
| `exifread>=3.0.0` | 主 EXIF 解析（RAW/HEIC 必需） | 缺失则自动降级到 PIL，UI 提示安装 |

第三方库均采用**延迟导入**（`_ensure_exifread` / `_ensure_pil`），启动期不阻塞 UI。

#### 步骤 4：启动 GUI

```bash
python src/exif_renamer.py
```

启动期会观察到的现象（按时间顺序）：

1. 中央占位条（tkinter 启动条）出现。
2. 后台线程导入 exifread + Pillow（约 1-3 秒，RAW 库较大）。
3. 主窗口弹出：源目录 + 处理类型勾选 + 文件名模板 + 状态栏。
4. EXIF 调试工具是独立脚本：`python src/exif_debugger.py`。

#### 步骤 5：验证启动成功

- 主窗口标题：「图片水印工具」外其它字段（无）。
- 默认源目录：`<用户>\Pictures\Screenshots`。
- 默认前缀：`screenshot`。
- 默认模板：`{prefix}-{YYYY}-{MM}-{DD}-{hh}{mm}-{id}`。

**若窗口未弹**：

- `python` 报错说找不到模块 → 检查 `pip install` 是否在 venv 激活状态下执行。
- 主窗口弹出但 `exifread` 状态栏显示「未安装」→ `pip install exifread`，重启。
- 主窗口弹出但所有图片都走备用时间源 → 多半是手机截图/社交平台下载，无标准 EXIF。

### 3.2 PyInstaller 双 spec

两个独立 spec 文件，**共享 distpath、独立 workpath**：

```bash
# 在仓库根
pyinstaller --workpath .pyi-build-renamer --distpath .pyi-dist exif_renamer.spec
pyinstaller --workpath .pyi-build-debugger --distpath .pyi-dist exif_debugger.spec
```

| spec | 产物 | datas | 资源 |
|---|---|---|---|
| `<REPO>/exif_renamer.spec` | `exif_renamer-<BUILD_TS>.exe` | `assets/icon.ico` + `assets/icon.png` | EXE icon = `assets/icon.ico` |
| `<REPO>/exif_debugger.spec` | `exif_debugger-<BUILD_TS>.exe` | 无 | 默认 |

**关键参数**：

- `BUILD_TS`：由 CI 注入环境变量 `WM_BUILD_TAG=YYYYMMDD-HHmmss`，spec 读取后拼接到产物名。
- `upx_exclude=['vcruntime140.dll','ucrtbase.dll']`：UPX 压缩这些系统 DLL 会引发兼容问题。
- `console=False`：窗口应用不弹控制台；调试时改 `True` 看 traceback。

#### 步骤 1：清理旧产物

```bash
# 必须清，否则 PyInstaller 会复用旧 .pyi-build 缓存冲突
rmdir /s /q .pyi-build-renamer .pyi-build-debugger .pyi-dist
# Git Bash 等价：rm -rf .pyi-build-renamer .pyi-build-debugger .pyi-dist
```

#### 步骤 2：安装 PyInstaller

```bash
pip install pyinstaller
```

#### 步骤 3：打包并验证

打包完成后：

- 检查 `.pyi-dist/exif_renamer-<时间戳>.exe` 文件大小（正常 ~25-40 MB）。
- 双击运行，验证启动顺序与源码运行一致（步骤 5 同）。
- 双击 `.pyi-dist/exif_debugger-<时间戳>.exe`，验证单图 EXIF 检视。

**若 exe 启动后无图标**：spec 中 `datas` 没把 `assets/icon.png` 打到运行时目录（运行时用 `PhotoImage(file=...)`），加回去重打。

### 3.3 CI 流水线（.github/workflows/release.yml）

### 3.2 PyInstaller 双 spec

两个独立 spec 文件，**共享 distpath、独立 workpath**：

```bash
# 在仓库根
pyinstaller --workpath .pyi-build-renamer --distpath .pyi-dist exif_renamer.spec
pyinstaller --workpath .pyi-build-debugger --distpath .pyi-dist exif_debugger.spec
```

| spec | 产物 | datas | 资源 |
|---|---|---|---|
| `<REPO>/exif_renamer.spec` | `exif_renamer-<BUILD_TS>.exe` | `assets/icon.ico` + `assets/icon.png` | EXE icon = `assets/icon.ico` |
| `<REPO>/exif_debugger.spec` | `exif_debugger-<BUILD_TS>.exe` | 无 | 默认 |

**关键参数**：

- `BUILD_TS`：由 CI 注入环境变量 `WM_BUILD_TAG=YYYYMMDD-HHmmss`，spec 读取后拼接到产物名。
- `upx_exclude=['vcruntime140.dll','ucrtbase.dll']`：UPX 压缩这些系统 DLL 会引发兼容问题。
- `console=False`：窗口应用不弹控制台；调试时改 `True` 看 traceback。

### 3.3 CI 流水线（.github/workflows/release.yml）

```
git push tag v<版本> (例: v1.2.3)
       │
       ▼
runs-on: windows-latest
       │
       ├─ actions/checkout@v7
       ├─ actions/setup-python@v7  ─► Python 3.14
       │
       ├─ PowerShell 生成 BUILD_TS（北京时间，+8h 偏移）
       │     └─ 注入 GITHUB_ENV: WM_BUILD_TAG
       │
       ├─ pip install -r requirements.txt
       ├─ pip install pyinstaller
       │
       ├─ git archive  ─► <repo>-<ts>.zip（源码包）
       │
       ├─ pyinstaller ─► exif_renamer-<ts>.exe   (workpath=.pyi-build-renamer)
       ├─ pyinstaller ─► exif_debugger-<ts>.exe  (workpath=.pyi-build-debugger)
       │
       ├─ 验证 .pyi-dist/*.exe 存在
       │
       ├─ gh release delete <tag> --yes  (清理同名旧 Release)
       └─ softprops/action-gh-release@v3
             └─ 上传源码 zip + 所有 exe
```

**关键约束**：

- **Windows-only**：`PyInstaller 不能跨平台`，CI 强制 windows-latest。
- **双 workpath**：避免两次打包的中间文件互相覆盖。
- **时区硬编码 +8h**：改时区改 release.yml 中生成 `BUILD_TS` 的 PowerShell 段。

### 3.4 环境变量

| 变量 | 默认 | 用途 | 来源 |
|---|---|---|---|
| `RENAME_TOOL_MAX_PATH` | 259 (Windows MAX_PATH) | 覆盖路径长度上限 |
| `WM_BUILD_TAG` | 无 | 注入到 spec，拼接产物名的时间戳 |

---

## 4. 核心算法

入口 `start_rename` (1557) → 构造 `params` → 启动 `RenameWorker.run()` → 走完四步流水线。

### 4.1 文件发现与分类

`collect_files_with_categories(folder, recursive, selected, log_func, progress_callback)` (377-439)：

- `recursive=False`：`os.listdir` 顶层目录（417-435）。
- `recursive=True`：`os.walk`，跳过：
  - 以 `.` 或 `$` 开头的目录（392）
  - `DEFAULT_IGNORED_FILENAMES`：`desktop.ini`、`thumbs.db`、`.ds_store`、`ehthumbs.db`（354-359）
  - 以 `.`/`._`/`$` 开头的文件名
- 通过 `EXT_TO_TYPE` (54-64) 把扩展名映射为 `IMAGE / RAW / VIDEO / AUDIO / FILE` 标签；按用户在 GUI 勾选的 `categories` 过滤（`_is_selected_category`, 362-374）。
- `progress_callback` 每 50 个文件触发一次（用于后台线程报告扫描进度）。

返回 `(all_files, media_files, ignored_fullpaths)`。

### 4.2 拍摄日期提取优先级链

`get_media_datetime(filepath, log_func)` (210-287)，严格优先级：

```
① EXIF DateTimeOriginal      ─► exifread 主路径
② Image DateTime             ─► exifread 备胎
③ EXIF DateTimeDigitized     ─► exifread 备胎
④ EXIF DateTime              ─► exifread 最后
⑤ Image XMP / XML            ─► exifread 内嵌 XMP
⑥ 同名 .xmp sidecar 文件      ─► parse_xmp_sidecar (179-198)
⑦ PIL Image.getexif()        ─► DateTimeOriginal/DateTime/DateTimeDigitized
⑧ os.path.getmtime           ─► 最后兜底
```

- 全部 EXIF/XMP/PIL 都失败时回退到文件 mtime（284-286）。
- 返回 `(datetime, is_fallback, reason)`：`is_fallback=True` 表示不是 `DateTimeOriginal`，触发 UI 警告对话框。
- **线程本地缓存**：`_exif_cache = threading.local()` (134)；后台线程起始处调 `_clear_exif_cache()` (137) 清空脏数据。

**为什么用 exifread 而非纯 PIL**：PIL 对 RAW（CR2/NEF/ARW）和 HEIC 几乎无 EXIF 支持；exifread 才能完整读取厂商私有 tag。

#### 4.2.1 降级链的统一返回语义

`get_media_datetime` 返回 `(datetime, is_fallback: bool, reason: str)` 三元组。每层降级的 `reason` 取值如下：

| 命中层 | `is_fallback` | `reason` 取值 | UI 行为 |
|---|---|---|---|
| ① EXIF DateTimeOriginal | `False` | `""` 或 `"EXIF DateTimeOriginal"` | 不警告 |
| ② Image DateTime | `True` | `"Image DateTime"` | 警告 |
| ③ EXIF DateTimeDigitized | `True` | `"EXIF DateTimeDigitized"` | 警告 |
| ④ EXIF DateTime | `True` | `"EXIF DateTime"` | 警告 |
| ⑤ 内嵌 XMP | `True` | `"XMP Embedded"` | 警告 |
| ⑥ `.xmp` sidecar | `True` | `"XMP Sidecar"` | 警告 |
| ⑦ PIL | `True` | `"PIL"` | 警告 |
| ⑧ mtime | `True` | `"File Modification Time"` | 警告（最严重） |

`CombinedWarningDialog`（§7.4）会把 `is_fallback=True` 的文件列在右栏，让用户**显式确认**接受这些时间源；用户取消则整个批处理中止。

#### 4.2.2 异常与空值的传递

- `exifread.process_file` 抛异常 → `log_func` 写 WARNING，继续降级到下一层。
- `PIL.Image.open` 失败（损坏图）→ `log_func` 写 WARNING，降级到 mtime。
- 命中层的日期字符串解析失败（`parse_date_string` 全失败）→ **当作未命中**，降级到下一层。
- 8 层全失败 → 返回 `(datetime.fromtimestamp(mtime), True, "File Modification Time")`；仍保留非空值（永不返回 `None`）。

#### 4.2.3 性能说明

- **EXIF 读取是 IO 密集**（每文件打开 + 解析 + 关闭）；1000 张图约 5-15 秒（取决于 EXIF 复杂度）。
- 缓存机制：`_exif_cache` 避免同线程重复 IO；后台线程起始处调 `_clear_exif_cache()` 防跨任务污染。

### 4.3 日期解析与时区剥离

`DATE_FORMATS` (121-126) 列 11 种格式：

```python
DATE_FORMATS = [
    "%Y:%m:%d %H:%M:%S",            # EXIF 标准
    "%Y-%m-%d %H:%M:%S",
    "%Y/%m/%d %H:%M:%S",
    "%Y:%m:%d %H:%M:%S%z",          # 带时区
    "%Y-%m-%dT%H:%M:%S",            # ISO 8601 (T 分隔)
    "%Y-%m-%dT%H:%M:%S.%f",
    "%Y-%m-%dT%H:%M:%S%z",
    # ...等
]
```

`parse_date_string(date_str)` (143-155)：

1. 预处理：剥离末尾 `±HH:MM` / `-HH:MM` / `Z` 时区偏移；`T` 替换为空格。
2. 顺序 `strptime`，首个成功即返回。

### 4.4 模板渲染与占位符

`apply_template(template, dt, prefix, file_id, seq, filetype)` (302-336)：

```python
# 占位符映射
"{YYYY}" → dt.strftime("%Y")
"{YY}"   → dt.strftime("%y")
"{MM}"   → dt.strftime("%m")
"{DD}"   → dt.strftime("%d")
"{hh}"   → dt.strftime("%H")
"{mm}"   → dt.strftime("%M")
"{ss}"   → dt.strftime("%S")
"{prefix}"   → prefix
"{filetype}" → filetype (image/raw/video/audio)
"{id}"       → file_id (generate_unique_id 生成)
"{seq}"      → seq (默认 %d，可自定义如 {seq:03d})
# 未识别占位符被删除（不报错）
```

`sanitize_filename(filename, max_name_len=200)` (339-345)：把 `\/:*?"<>` 替换为 `_`；截断到 `max_name_len`。

### 4.5 冲突解决

`prepare_rename_plan` (462-613) 在两个层面处理冲突：

**第一层（计划内互冲突）**：

```python
used_target_paths = set()    # 计划内所有"已分配"目标路径
```

**第二层（计划内 vs 计划外文件已存在）**：

| 模板是否含 `{seq}` | 冲突处理 | 上限 |
|---|---|---|
| **含 `{seq}`** | `local_seq += 1`，文件名带递增序号 | 10000 次 (`max_retries=10000`, 541) |
| **不含 `{seq}`** | `conflict_suffix += 1`，文件名变 `base_2.ext / base_3.ext / ...` | 10000 次 (596-599) |

**`generate_unique_id` (290-299)**：4 位字母数字 ID，撞库后自动扩到 5/6/7/8 位，最多 100000 次尝试。

#### `prepare_rename_plan` 返回结构

```python
{
    "rename_map": {
        # 成功条目：源路径 → 目标路径（已通过冲突解决且通过 mtime 一致性校验）
        "C:\\Photos\\IMG_0001.jpg": "C:\\Photos\\screenshot-20240101-120000-A3F2.jpg",
        ...
    },
    "fallback_files": [
        # 使用 mtime 等备用时间源的文件清单，会在 CombinedWarningDialog 中告知用户
        ("C:\\Photos\\phone_screenshot.png", "文件修改时间"),
        ...
    ],
    "fallback_previews": [
        # 与 fallback_files 配对的预览（old → new 路径），用于对话框展示
        ("old_path", "new_path"),
        ...
    ],
    "failed_analysis": {
        # 因冲突超限 / 路径超长 / mtime 不一致等原因跳过的文件及原因
        "C:\\Photos\\bad.jpg": "冲突超限 (max_retries=10000)",
        ...
    },
    "ignored_files": [
        # 被跳过未处理的文件（系统隐藏 / 排除名 / 不在选中类别）
        ("C:\...\thumbs.db", "默认忽略文件名"),
        ...
    ],
}
```

后台线程 `RenameWorker.run()` 根据这个返回结构决定弹哪些对话框、按什么顺序弹。

### 4.6 一致性保护（mtime 比对）

```python
# 伪代码：执行前再次 os.path.getmtime 比对，若发现原文件被改动则跳过
```

避免后台线程在准备计划期间，原文件被外部修改（用户在资源管理器里 mv 了一下）导致 mv 到错位置。

### 4.7 执行阶段（os.rename vs shutil.copy2）

`execute_rename(rename_map, copy_mode, log_func)` (616-637)：

| `copy_mode` | 操作 | 特点 |
|---|---|---|
| `False`（默认） | `os.rename(old, new)` | 同盘内**原子**，跨盘失败 |
| `True` | `shutil.copy2(old, new)` | 保留 mtime 等元数据；跨盘可用 |

返回 `(success_count, failed_list)`。

#### 复制模式目录映射

复制模式下，目标路径不是简单的文件名拼接——`prepare_rename_plan` 会保留**相对目录结构**：

```
源目录:    C:\Photos\Trip\Day1\IMG_0001.jpg
复制目标:  C:\Backup\Trip\Day1\IMG_0001.jpg
                                  ^^^^^^^^^ 保留 Day1 子目录
```

`safe_relpath` (442) + `get_relative_dir` (458) 负责这个映射，跨驱动器时安全回退。

#### 同目录重命名边界

- **同目录重命名**：默认模式（`copy_to_new=False`）就是同目录重命名。冲突时按 §4.5 规则解决。
- **跨目录复制**：勾选 `copy_to_new=True` 后，源 → 目标跨目录，目标子树不存在时 `makedirs(exist_ok=True)` 自动建。
- **跨盘复制**：`shutil.copy2` 自动处理，**无此问题**。
- **跨盘重命名**：`os.rename` 跨盘会 `OSError`（Windows 错误 `ERROR_NOT_SAME_DEVICE`），自动进 `failed_list`。
- **环形/互相占用**：`used_target_paths` 集合防止重命名计划内部冲突；计划外的目标路径冲突走 §4.5 冲突解决。

---

## 5. 接口契约

### 5.1 GUI 输入项完整清单

`DEFAULT_SETTINGS` (27-41) 默认值：

| 字段 | 默认值 | 说明 |
|---|---|---|
| `source_folder` | `~\Pictures\Screenshots` | 源目录 |
| `prefix` | `screenshot` | 模板中的 `{prefix}` |
| `template` | `{prefix}-{YYYY}-{MM}-{DD}-{hh}{mm}-{id}` | 命名模板 |
| `recursive` | `False` | 包含子文件夹 |
| `copy_to_new` | `False` | 复制模式 vs 重命名模式 |
| `target_folder` | （空） | 仅复制模式启用 |
| `categories` | `{image:True, raw:False, custom_file:False, video:True, audio:False}` | 处理类型勾选 |

`start_rename` (1557-1597) 校验：

- 源文件夹必须存在且是目录
- 复制模式勾选 → 目标文件夹必须填（不存在则 `makedirs(exist_ok=True)`）
- 模板非空字符串

**持久化行为**：所有"配置"都是 GUI 内 `tk.StringVar` / `tk.BooleanVar` 内存态，**重启即丢默认值**——无任何配置文件（详见 §6.1）。

### 5.2 支持的扩展名矩阵

| 类别 | 扩展名常量 | 值 |
|---|---|---|
| 图像 `IMAGE_EXTS` (44) | `.jpg .jpeg .png .bmp .gif .webp .heic` | 7 个 |
| RAW `RAW_EXTS` (45-46) | `.arw .cr2 .cr3 .dng .nef .nrw .orf .pef .raf .rw2 .srw .x3f` | 12 个 |
| 视频 `VIDEO_EXTS` (47-48) | `.mp4 .avi .mov .mkv .flv .wmv .m4v .mpg .mpeg` | 9 个 |
| 音频 `AUDIO_EXTS` (49) | `.mp3 .wav .flac .aac .ogg .m4a .wma` | 7 个 |
| 自定义 `CUSTOM_FILE_EXTS` (51) | 空 `()` | 0 个（需改源码） |

`EXT_TO_TYPE` (54-64) 预计算扩展名到类型标签的 dict；新增类型时同步加到这里。

### 5.3 「无 CLI / 无 dry-run / 无 library 暴露面」的设计现状

**现状**（grep 已确认）：

- ❌ 无 `argparse` / `click` / `fire` / `typer`
- ❌ 无 `dry-run` 选项
- ❌ 无 `__all__` 或 library 暴露（无 `setup.py` / `pyproject.toml`）
- ✅ `main()` (1646) 无参数；`if __name__ == "__main__": main()` (1651-1652) 直接 `root.mainloop()`

**为什么会这样**：

1. 项目定位是 GUI 工具，不是 CLI / library——用户场景是"打开窗口→选目录→点开始"，CLI 反人类。
2. dry-run 缺失由「两层人工确认对话框」补偿（详见 §7.4）。
3. 接入 library 化的改造点建议见 §9.3。

---

## 6. 持久化与日志

### 6.1 无配置文件的设计取舍

仓库内**没有任何**配置文件（无 JSON/YAML/TOML；grep 已确认零命中），所有 GUI 配置项都是 `tk.StringVar` / `tk.BooleanVar` 内存态，**重启即丢默认值**。

**为什么这样设计**：

- 项目目标用户是摄影/视频归档的轻度用户，不需要"切换多个预设"。
- 默认值已经覆盖 90% 场景（`{prefix}-{YYYY}-{MM}-{DD}-{hh}{mm}-{id}` + screenshot 前缀）。
- 持久化意味着要写文件路径选择 → 用户已经被"选源目录"的负担占了，加一个 settings 路径只会更糟。

**取舍**：如果未来用户有"不同项目用不同模板"的需求，可以加 `~/.config/exif_renamer.json` 之类的 settings 文件——改造点见 §9。

### 6.2 GUI 内日志面板

`_create_log_tab` (1421-1432) 创建一个 `ScrolledText` 日志面板：

- **三色 tag**：`INFO / / ERROR /`（`log` 方法 1477）根据 level 染色。
- **来源**：后台线程经 `log_queue.put((level, msg))` → 主线程 `_poll_queues` (1485) 每 50ms 取出并写入。
- **无文件日志**：`.gitignore:30` 排除 `*.log`，项目本身也不生成日志文件。
- **大量文件时性能问题**：>10000 文件时日志刷新可能让界面短暂停顿（README FAQ1, 181-182）。后台线程持续 `log_queue.put` 会让主线程队列堆积。

### 6.3 exif_debugger 的 EXIF 日志导出

调试工具 `src/exif_debugger.py:149-170` 的"导出日志"按钮：

- `filedialog.asksaveasfilename` 让用户选保存路径。
- 默认文件名 `<原文件名>_exif_log.txt`，默认目录与图片同目录。
- 文件内容：左侧 PIL 基本信息 + 12 个常用 EXIF 字段；右侧全部 EXIF 标签（过滤缩略图与 >200 字节 bytes）。

### 6.4 自动打开目标文件夹

`on_rename_finished` (1607-1623) 在重命名完成（成功）后：

- 写完成统计到日志
- 弹 `FailureDialog`（如有失败）
- **自动用系统资源管理器打开目标文件夹**（`subprocess.Popen(['explorer', target])` 或 `open -R` 或 `xdg-open`）

`_open_folder` (1628-1640) 是跨平台封装：

```python
def _open_folder(self, folder):
    if platform.system() == "Windows":
        subprocess.Popen(['explorer', folder])
    elif platform.system() == "Darwin":
        subprocess.Popen(['open', folder])
    else:
        subprocess.Popen(['xdg-open', folder])
```

---

## 7. 安全边界

### 7.1 不修改原图二进制

整个工具只做两件事：

- `os.rename(old, new)` — 改文件名（目录项）
- `shutil.copy2(old, new)` — 复制（保留 mtime，不动内容）

**不读取 / 写入**图像二进制内容（除 EXIF/XMP 元数据，但这些只在解析时读，不写回）。

### 7.2 重命名 vs 复制的实现差异

| 模式 | 适用场景 | 风险 |
|---|---|---|
| **重命名**（默认） | 原目录就地整理 | 操作不可逆（详见 §7.5） |
| **复制** | 把整理后的副本放新目录 | 占双倍空间；原文件保留可作为回滚手段 |

`copy_mode` 决定 `execute_rename` 用 `os.rename` 还是 `shutil.copy2` (616-637)。

### 7.3 不覆盖保证 + 冲突上限

`prepare_rename_plan` (462-613) 严格**永不覆盖**已存在文件：

- 若目标路径已存在或本次计划中其他条目占用，走 §4.5 的冲突解决流程。
- 冲突上限 `max_retries=10000`（541, 596）；超限则文件进 `failed_analysis` 并跳过。
- 失败原因写入日志，最终弹 `FailureDialog`（888-915）展示最多 10 个失败文件。

### 7.4 两层人工确认

后台线程**不直接执行**——先回到主线程弹模态对话框：

**第一层 `CombinedWarningDialog` (722-873)**：

- 左 =被跳过的文件（系统隐藏/默认忽略名）。
- 右 =会用备用时间源的文件（不是 `DateTimeOriginal`）。
- 右键文件项可"打开文件"/"在资源管理器中定位"。

**第二层 `CustomConfirmDialog` (679-719)**：

- 完整 `old → new` 对照表（可滚动）。
- 用户必须**显式点"开始处理"**才真正执行。

这两层由 `_handle_dialog_request` (1523) 在主线程 `after(0, ...)` 回调里弹，用户选择塞回 `response_queue` 给后台线程。

### 7.5 无撤销/回滚的代价与缓解

**代价**：

- 一旦 `os.rename` 执行，原文件名立即丢失。
- 没有 `.trash` / `.git mv` / 回收站机制。
- 跨盘移动时 `os.rename` 会失败（自动捕获 `OSError` 进 `failed_list`）。

**缓解**：

- 第一选择：**勾选「复制到新目录」**（`copy_to_new=True`）——原文件保留。
- 第二选择：先在备份上试跑一遍（README 免责声明, 205-211）。
- 第三选择：执行前看 `CustomConfirmDialog` 的对照表（人工审计）。

### 7.6 关闭时的线程保护

`_on_close` (1209-1218)：

```python
def _on_close(self):
    self._shutdown_event.set()
    if self._worker and self._worker.is_alive():
        self._worker.join(timeout=2.0)
    self.root.destroy()
```

- `shutdown_event` 让后台线程在下一个检查点优雅退出（`RenameWorker.run()` 检查 `_shutdown_event.is_set()`）。
- `join(timeout=2.0)` 给 2 秒缓冲，超过就强 destroy（daemon 线程被系统回收）。
- 避免后台线程正在 `os.rename` 时窗口被销毁导致状态不一致。

### 7.7 README 免责声明

原文摘要（出自 README 末尾）：

> 本项目为个人学习作品，部分逻辑及代码由 AI 辅助生成（DeepSeek & AstrBot），**不建议在生产环境或未备份的重要数据上使用**。

任何二次发布/打包必须保留这段。

---

## 8. 常见踩坑与红线（按硬/软分层）

本项目**无** AGENTS.md / CLAUDE.md，红线散落在以下来源——本章是这类信息的**唯一集中地**。**§8.1-§8.3 是硬红线**（违反会破坏功能/打包）；**§8.4 是软约束**（违反只会降级体验或性能）。

### 8.1 数据安全硬红线（绝不可破）

| # | 红线 |
|---|---|
| 1 | **永不覆盖**：若目标文件已存在或本次计划中其他条目占用，必须按 §4.5 冲突解决（`{seq}` 自增或 `name_2.ext` 后缀）。 |
| 2 | **执行前 mtime 一致性检查**：后台线程在准备计划期间，若发现原文件被外部修改，**必须跳过**该文件（见 §4.6）。 |
| 3 | **两层人工确认不可绕过**：`CombinedWarningDialog`（列出忽略文件 + 备用时间源）必须先弹；用户确认后才弹 `CustomConfirmDialog`（完整 old→new 对照表）；用户再次确认后才执行 `execute_rename`。后台线程**不直接执行**。 |
| 4 | **跨盘重命名走 `OSError` 捕获**：不要 try/except 静默吞——必须进 `failed_list` 弹 `FailureDialog`。 |
| 5 | **关闭窗口必须 `worker.join(timeout=2.0)`**：见 `_on_close`，避免后台线程在 `os.rename` 中途被强 destroy 导致状态不一致。 |

### 8.2 资源与打包硬红线

源码相关：

| # | 红线 |
|---|---|
| 6 | 运行时 `__file__` 在 `src/`，需 `..\assets\icon.png`；打包后 `__file__` 在 `sys._MEIPASS`，路径不同；图标缺失**不应阻断启动**（catch 异常降级）。 |
| 7 | `PhotoImage` 必须存为实例变量否则被 GC 后图标消失。 |
| 8 | Windows 用 `xpnative` 主题，非 Windows 平台 fallback 到 `clam`。 |
| 9 | 鼠标滚轮事件要兼容 Windows (`<MouseWheel>`)、Linux (`<Button-4>`/`<Button-5>`) 两种绑定。 |
| 10 | `CUSTOM_FILE_EXTS = ()` 默认空——「自定义文件类型默认为空，请在源代码中添加」。新增自定义扩展名改源码即可，无需改 GUI。 |
| 11 | `_safe_realpath`：Windows 上处理 NTFS junction / mount point，其它平台直接返回。 |

打包相关：

| # | 红线 |
|---|---|
| 12 | `upx_exclude=['vcruntime140.dll','ucrtbase.dll']`：UPX 压缩这些系统 DLL 会引发兼容问题。 |
| 13 | spec 必须在仓库根运行（pyproject.toml 不存在，spec 自身校验 `os.getcwd()` 加 README.md 探测）。 |
| 14 | **PyInstaller 不能跨平台，CI 强制 windows-latest**。 |
| 15 | 时间戳生成固定 `+8h` 偏移到北京时间，改时区改 release.yml 中生成 `BUILD_TS` 的 PowerShell 段。 |
| 16 | 双 spec 必须用**独立 workpath**（`.pyi-build-renamer`/`.pyi-build-debugger`）但**共享 distpath**（`.pyi-dist`），否则中间文件冲突。 |

### 8.3 跨盘 / 同盘 / 路径边界（行为规则）

| # | 规则 |
|---|---|
| 17 | `os.rename` 同盘内**原子**；**跨盘失败** → 进 `failed_list`。 |
| 18 | `shutil.copy2` 跨盘可用，**保留 mtime 等元数据**。 |
| 19 | 复制模式下目标路径保留**源相对目录结构**（`safe_relpath` + `get_relative_dir`），跨驱动器安全回退。 |
| 20 | `used_target_paths` 集合防止重命名计划内部冲突；超出 10000 次重试进 `failed_analysis` 跳过。 |
| 21 | `MAX_PATH_LIMIT` 默认 259（Windows MAX_PATH），可通过 `RENAME_TOOL_MAX_PATH` 环境变量覆盖；超限文件跳过。 |

### 8.4 软约束（违反不破坏功能，但会降级）

| # | 软约束 |
|---|---|
| 12 | >10,000 文件时日志刷新可能让界面短暂停顿 |
| 13 | 没装 `exifread` 时部分手机/社媒下载的照片无 EXIF，会回退到文件修改时间 |
| 14 | `RAW` 是缩写，不要与图片（image）混淆——勾选 RAW 类型但缺 `exifread` 库时仍走 PIL |
| 15 | 重名冲突最多重试 10000 次；超过会记入 `failed_analysis` 跳过 |

---

## 9. 二次开发指引

### 9.1 新增 RAW/视频/音频/自定义扩展名

```python
# 在 exif_renamer.py 顶部常量区
RAW_EXTS = (
    '.arw', '.cr2', '.cr3', '.dng', '.nef', '.nrw',
    '.orf', '.pef', '.raf', '.rw2', '.srw', '.x3f',
    # 在这里追加
    '.your_format',
)
```

`EXT_TO_TYPE` (54-64) 是从上述 4 个常量**预计算**的，**改完 RAW_EXTS 后必须同步更新**或重启（首次访问时才计算）。

### 9.2 新增自定义占位符

`apply_template` (302-336) 的占位符替换链：

```python
# 当前支持：{YYYY} {YY} {MM} {DD} {hh} {mm} {ss} {prefix} {filetype} {id} {seq[:fmt]}
replacements = {
    "{YYYY}": lambda: dt.strftime("%Y"),
    # 新增：
    "{HH24}": lambda: dt.strftime("%H"),   # 例
    "{ISO}": lambda: "ISO-xxx",            # 例：可读 EXIF ISO
}
```

**注意**：占位符在 GUI 的"插入占位符 ▼"菜单（1345-1375）里同步注册才能让用户看到。

### 9.3 改造为 CLI（argparse 改造点建议）

最小侵入方案：

1. **不破坏现有 GUI**：在 `main()` 之前加 CLI 分支。
2. 复用 `collect_files_with_categories` / `get_media_datetime` / `prepare_rename_plan` / `execute_rename`（这些已经是纯函数）。
3. 跳过 `RenameWorker` 队列，直接同步调用。
4. GUI 仅作 dry-run 预览（`print(rename_map)`）。

伪代码骨架：

```python
def cli_main(args):
    files, media, ignored = collect_files_with_categories(
        args.source, args.recursive, args.categories, log_func=print)
    plan = prepare_rename_plan(
        args.source, files, media, ignored, args.template, args.prefix,
        args.copy, args.target, log_func=print)
    if args.dry_run:
        for old, new in plan['rename_map'].items():
            print(f"{old} → {new}")
    else:
        success, failed = execute_rename(plan['rename_map'], args.copy, log_func=print)
        print(f"{success} succeeded, {len(failed)} failed")
        sys.exit(0 if not failed else 1)
```

### 9.4 增加 undo / 回收站机制的设计思路

最简方案：

```python
# execute_rename 期间记录
undo_log = []
for old, new in rename_map.items():
    try:
        if copy_mode: shutil.copy2(old, new)
        else: os.rename(old, new)
        undo_log.append((new, old, copy_mode))   # 反向记录
    except OSError as e:
        log(f"failed: {old} → {e}")
```

- **持久化 undo_log** 到 `<目标目录>/.exif_renamer_undo.json`，下次启动可读。
- **撤销**：从 JSON 读出 `(new, old, copy_mode)`，按反向 `os.rename` / 删除。
- **清理**：撤销完成后删 JSON；过期（比如 7 天）自动删。
- **陷阱**：撤销时若用户已手动改了 `new` 文件名 / 删了文件，需更精细的冲突处理（参考 `prepare_rename_plan` 的冲突逻辑）。

替代方案：用 OS 回收站（Windows `send2trash` 库；macOS Finder；Linux `gio trash`）——但这会让原文件消失，需要二次确认对话框。

### 9.5 修改后的回归验证矩阵

修改核心函数（`get_media_datetime` / `prepare_rename_plan` / `execute_rename` / `apply_template` / 扩展名常量）后，**至少跑完下列场景**：

| 场景 | 验证内容 | 预期 |
|---|---|---|
| **EXIF 正常图** | 含 DateTimeOriginal 的相机原图（`.jpg`/`.dng`/`.cr2`） | 不进 CombinedWarningDialog 的"备用时间源"列表 |
| **EXIF 无/损坏图** | 手机截图 + 手动改扩展名的破损文件 | 触发"文件修改时间"警告，进 CombinedWarningDialog 右栏 |
| **XMP 命中** | Adobe Lightroom 已写入 XMP 的 RAW | 命中「XMP Embedded」/「XMP Sidecar」reason |
| **PIL 兜底** | 缺 exifread 库时跑测试图 | 自动降级到 PIL reason="PIL" |
| **模板渲染** | `{prefix}-{YYYY}-{MM}-{DD}-{hh}{mm}-{id}` 跑一张 2024-01-15 14:30:00 拍摄 | 期望 `screenshot-2024-01-15-1430-A3F2` |
| **`{seq}` 冲突** | 同一目录手动塞两个同名目标文件 | 第一个走 `{seq}=1`，第二个走 `{seq}=2` |
| **无 `{seq}` 冲突** | 模板不带 `{seq}` 时塞两个同名 | 文件名变 `_2.ext`、`_3.ext` |
| **复制模式跨目录** | `copy_to_new=True`，源 `C:\A\B\IMG.jpg` → 目标 `D:\Backup` | 落 `D:\Backup\B\IMG.jpg`，保留 B 子目录 |
| **跨盘重命名** | 源在 C: 盘，目标在 D: 盘 | 全部进 `failed_list`，弹 `FailureDialog` |
| **mtime 不一致** | 准备计划期间外部修改了文件 | 该文件进 `failed_analysis`，跳过执行 |
| **两层确认** | 任意正常运行流程 | CombinedWarningDialog → CustomConfirmDialog → 执行；用户取消任一对话框都中止 |
| **关闭窗口** | 后台 worker 跑时点 X | `_on_close` 触发 `shutdown_event.set()` + `worker.join(2.0)` + `destroy()` |
| **EXIF 调试工具** | `python src/exif_debugger.py` 跑一张图 | 显示 PIL 基本信息 + 12 个常用 EXIF + 全部 EXIF 标签 |

打包后额外跑：

| 场景 | 预期 |
|---|---|
| 双击 `exif_renamer-<ts>.exe` | 主窗口弹出，EXIF 状态正常显示 |
| 双击 `exif_debugger-<ts>.exe` | 调试窗口弹出，选图→显示 EXIF |
| 图标缺失（删除 `assets/icon.png` 重打） | 主窗口仍能启动，运行时图标为空——**不阻断启动**（红线 6） |

---

## 10. 目录结构与各文件用途

```
git-ChongMingMing/
├── README.md                                # 用户向说明：功能/截图/下载/FAQ/免责声明
├── wiki.md                                  # 本文档（工程视角）
├── requirements.txt                         # Pillow>=9.0 + exifread>=3.0.0（仅两行）
├── .gitignore                               # 排除 .venv/ .pyi-*/ history/ images/ *.log
├── .gitattributes                           # LF 规范化 + release 包排除规则
├── exif_renamer.spec                        # PyInstaller spec：主程序 exe
├── exif_debugger.spec                       # PyInstaller spec：调试工具 exe
├── .github/
│   └── workflows/
│       └── release.yml                      # Windows-only CI：tag v* → exe + 源码 zip → Release
├── assets/
│   ├── icon.ico                             # EXE 资源图标（spec 嵌入）
│   └── icon.png                             # GUI iconphoto 用（spec 注入运行时目录）
├── images/                                  # README 截图（1.png~4.png，已入库但 .gitignore 排除）
├── history/
│   └── 旧.py                                # 旧版本归档（已入库但 .gitignore 排除）
└── src/
    ├── exif_renamer.py                      # 主程序（1652 行，tkinter GUI）
    └── exif_debugger.py                     # EXIF 调试工具（174 行，tkinter GUI）
```

**关键文件用途速查**：

| 文件 | 编辑频度 | 修改影响面 |
|---|---|---|
| `src/exif_renamer.py` | 高 | 主功能；改完需同步 README「功能说明」+ 测试两个 GUI |
| `src/exif_debugger.py` | 低 | 独立脚本，与主程序无依赖关系 |
| `requirements.txt` | 低 | 仅在新增依赖时改；同步 CI 与 README |
| `exif_renamer.spec` | 低 | 仅在新增打包资源时改 |
| `exif_debugger.spec` | 低 | 同上 |
| `.github/workflows/release.yml` | 中 | 改时区/触发条件/产物名时改 |
| `README.md` | 中 | 用户向；新功能/参数变更需同步 |
| `.gitignore` | 低 | 添加新忽略路径时改 |

---

## 附录 A · 函数 / 类速查表

> 仅作为导航表，不带行号——行号随代码漂移，请在 IDE 中以符号名定位。

| 符号 | 职责 |
|---|---|
| `_ensure_exifread()` | 双检锁惰性导入 exifread；返回 module |
| `_ensure_pil()` | 双检锁惰性导入 PIL.Image + TAGS |
| `_clear_exif_cache()` | 清空当前线程 `_exif_cache.__dict__` |
| `parse_date_string(date_str)` | 按 `DATE_FORMATS` 顺序 strptime；预处理剥时区/T 分隔符 |
| `parse_xmp_content(xmp_str)` | 7 个正则从 XMP/XML 抽 CreateDate / DateCreated 等 |
| `parse_xmp_sidecar(filepath, log_func)` | 读同名 `.xmp` Adobe sidecar 并解析日期 |
| `_decode_exif_value(val)` | bytes 安全 decode（utf-8 → latin-1，剥 `\x00`） |
| `get_media_datetime(filepath, log_func)` | 主入口：EXIF → XMP → PIL → mtime；返回 `(dt, is_fallback, reason)` |
| `generate_unique_id(existing_ids)` | 4~8 位字母数字 ID，撞库自动扩；`max_attempts=100000` |
| `apply_template(template, dt, prefix, file_id, seq, filetype)` | 替换模板占位符；未识别占位符被删除 |
| `sanitize_filename(filename, max_name_len=200)` | 替换 `\/:*?"<>` 为 `_`；截断到 max_name_len |
| `get_filetype(ext)` | 查 `EXT_TO_TYPE` 表，返回类型标签 |
| `_is_selected_category(ext, selected)` | 判断扩展名所属类别是否被 GUI 勾选 |
| `collect_files_with_categories(folder, recursive, selected, log_func, progress_callback)` | 遍历源目录，按扩展名筛选；返回 `(all_files, media_files, ignored)` |
| `safe_relpath(path, start)` | 安全的 relpath，跨驱动器时回退到 start 树内截取 |
| `get_relative_dir(full_path, base_folder)` | 取 dirname 再调 safe_relpath |
| `prepare_rename_plan(folder, all_files, media_files, ignored_fullpaths, template, prefix, copy_mode, target_base, log_func)` | 主重命名计划器；返回 `rename_map / fallback_files / failed_analysis` 等 |
| `execute_rename(rename_map, copy_mode, log_func)` | 按 copy_mode 选 shutil.copy2 或 os.rename |
| `_safe_realpath(path)` | Windows realpath（处理 NTFS junction / mount point） |
| `class CustomDialogBase` | Tkinter 对话框基类 |
| `class CustomConfirmDialog(CustomDialogBase)` | 二选一确认对话框（是 / 否） |
| `class CombinedWarningDialog(CustomDialogBase)` | 双列警告窗（忽略文件 + 备用时间源文件） |
| `class ErrorDialog(CustomDialogBase)` | 简单错误弹窗 |
| `class FailureDialog(CustomDialogBase)` | 显示最多 10 个失败文件 |
| `class RenameWorker(threading.Thread)` | 后台线程：扫描 → 计划 → 两次确认 → 执行 |
| `class ExifRenamer` | Tkinter 主窗口 |
| `ExifRenamer._show_splash` / `_hide_splash` | 启动期占位条 |
| `ExifRenamer._boot_heavy_modules` | 后台线程跑 `_ensure_exifread()` + `_ensure_pil()` |
| `ExifRenamer._wait_for_boot` | 50ms 轮询 `_boot_done` |
| `ExifRenamer._on_close` | shutdown_event + worker.join + destroy |
| `ExifRenamer._create_*` 系列 | 分块构建 UI（目录 / 类型 / 占位符 / 输出 / 状态 / 日志） |
| `ExifRenamer.log` | 往 log_text 加带 level tag 的行 |
| `ExifRenamer._poll_queues` | 50ms 轮询 log_queue / request_queue |
| `ExifRenamer._handle_dialog_request` | after(0) 回调弹模态对话框 |
| `ExifRenamer.start_rename` | 校验输入 + 启动 RenameWorker |
| `ExifRenamer.on_rename_finished` | 完成统计 + 弹失败 + 打开目标文件夹 |
| `ExifRenamer._open_folder` | 跨平台打开文件夹 |
| `ExifRenamer.run` | `root.mainloop()` |
| `main()` | `ExifRenamer().run()` |

---

## 附录 B · 常量速查

> 仅作为导航表，文件位置以模块级标识符定位，不带行号。

### B.1 DEFAULT_SETTINGS

| Key | 默认值 |
|---|---|
| `source_folder` | `~\Pictures\Screenshots` |
| `prefix` | `"screenshot"` |
| `template` | `"{prefix}-{YYYY}-{MM}-{DD}-{hh}{mm}-{id}"` |
| `recursive` | `False` |
| `copy_to_new` | `False` |
| `target_folder` | `""` |
| `categories.image` | `True` |
| `categories.raw` | `False` |
| `categories.custom_file` | `False` |
| `categories.video` | `True` |
| `categories.audio` | `False` |

### B.2 扩展名常量

| 常量 | 扩展名 |
|---|---|
| `IMAGE_EXTS` | `.jpg .jpeg .png .bmp .gif .webp .heic` |
| `RAW_EXTS` | `.arw .cr2 .cr3 .dng .nef .nrw .orf .pef .raf .rw2 .srw .x3f` |
| `VIDEO_EXTS` | `.mp4 .avi .mov .mkv .flv .wmv .m4v .mpg .mpeg` |
| `AUDIO_EXTS` | `.mp3 .wav .flac .aac .ogg .m4a .wma` |
| `CUSTOM_FILE_EXTS` | `()` 空 |
| `EXT_TO_TYPE` | 扩展名 → 类型标签 dict（运行时计算） |

### B.3 DATE_FORMATS

11 种 EXIF 日期编码（详见 §4.3），含带时区、T 分隔符等变体。

### B.4 路径长度限制

| 名称 | 值 |
|---|---|
| `MAX_PATH_LIMIT` | `int(os.environ.get("RENAME_TOOL_MAX_PATH", "259"))` |
| `max_name_len`（sanitize_filename） | 200 |
| `max_attempts`（generate_unique_id） | 100000 |
| `max_retries`（冲突解决） | 10000 |

### B.5 默认忽略文件名

`DEFAULT_IGNORED_FILENAMES`：

```python
{'desktop.ini', 'thumbs.db', '.ds_store', 'ehthumbs.db'}
```

### B.6 主题与平台 fallback

| 平台 | Tk 主题 | 打开文件夹命令 |
|---|---|---|
| Windows | `xpnative` | `explorer` |
| macOS | `xpnative` | `open` |
| Linux | `clam` | `xdg-open` |

---

## 附录 C · README 章节交叉引用

| README 章节 | 本文覆盖 |
|---|---|
| 项目起源 / 中心思想 | §1 |
| 程序截图 | （wiki 不含截图，参考 README） |
| 功能概览表 | §5 |
| 下载与使用 | §3.1，§3.3 |
| 快速上手 5 步 | §5.1 |
| 文件类型支持（完整扩展名表） | §5.2 |
| 拍摄日期提取（优先级链） | §4.2 |
| 文件名模板系统 | §4.4 |
| FAQ Q1（>10k 文件卡顿） | §8.4 第 12 条 |
| FAQ Q2（EXIF 读不到） | §4.2，§8.4 第 13 条 |
| FAQ Q3（增加 RAW 格式） | §9.1 |
| FAQ Q4（重名冲突） | §4.5，§8.4 第 15 条 |
| 免责声明 | §7.7 |
| 鸣谢 | （不属于工程内容） |

---

## 附录 D · 踩坑索引（按类别）

> 按风险来源分类。行号随代码漂移，故省略；按描述或 §8 章节定位。

### 资源与运行时

| # | 类别 | 描述 | 详见 |
|---|---|---|---|
| 1 | 资源路径 | 运行时 `__file__` 在 `src/`，需 `..\assets\icon.png`；打包后路径不同；缺失不应阻断启动 | §8.1 第 1 条 |
| 2 | GC | `PhotoImage` 必须存为实例变量否则被 GC 后图标消失 | §8.1 第 2 条 |
| 3 | 主题 | Windows 用 `xpnative`，其它平台 fallback `clam` | §8.1 第 3 条 |
| 4 | 鼠标滚轮 | Windows (`<MouseWheel>`) 与 Linux (`<Button-4>`/`<Button-5>`) 双绑定 | §8.1 第 4 条 |
| 5 | realpath | Windows NTFS junction / mount point 处理 | §8.1 第 6 条 |

### 业务行为

| # | 类别 | 描述 | 详见 |
|---|---|---|---|
| 6 | 自定义扩展名 | `CUSTOM_FILE_EXTS = ()` 默认空，需改源码 | §8.1 第 5 条 |
| 7 | EXIF 降级 | 没装 exifread 时回退到 mtime | §8.4 第 13 条 |
| 8 | RAW vs Image | 勾 RAW 但缺 exifread 库时仍走 PIL | §8.4 第 14 条 |
| 9 | 冲突上限 | 重名冲突最多重试 10000 次 | §8.4 第 15 条 |
| 10 | 性能 | >10,000 文件时日志刷新可能让界面短暂停顿 | §8.4 第 12 条 |

### 打包与 CI

| # | 类别 | 描述 | 详见 |
|---|---|---|---|
| 11 | UPX | 排除 `vcruntime140.dll` / `ucrtbase.dll` | §8.2 第 7 条 |
| 12 | spec 运行目录 | spec 必须在仓库根运行 | §8.2 第 8 条 |
| 13 | 跨平台打包 | PyInstaller 不能跨平台，CI 强制 windows-latest | §8.3 第 9 条 |
| 14 | 时区 | 时间戳生成固定 +8h 偏移到北京时间 | §8.3 第 10 条 |
| 15 | PyInstaller 目录 | 双 spec 必须独立 workpath + 共享 distpath | §8.3 第 11 条 |

---

*本文档与 `README.md` 互补：README 给最终使用者提供下载/截图/快速上手，wiki 给开发者提供架构/算法/红线索引。修改算法 / 扩展功能时优先改本文档对应章节；用户向功能描述改 README。*