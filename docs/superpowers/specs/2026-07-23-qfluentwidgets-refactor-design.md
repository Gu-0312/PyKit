# QFluentWidgets 重构设计文档

## 概述

将 Python EXE Packer（Python一键打包EXE）的 GUI 层从 ttkbootstrap (tkinter) 迁移到 QFluentWidgets (PySide6)，同时重构核心层接口为信号驱动模式。

## 目标

- 用 QFluentWidgets 实现 Fluent Design 风格的现代化界面
- 核心业务逻辑接口改为回调/信号模式
- 引入 `_metadata.py` 管理应用元数据
- 引入 `app/` 层管理 Application 生命周期
- 引入 `resources/` 统一管理资源文件

## 技术栈

| 层 | 技术 |
|---|------|
| GUI 框架 | PySide6 |
| Fluent 组件库 | qfluentwidgets (PySide6-Fluent-Widgets) |
| 图标 | FluentIcon / FluentIconEngine |
| 打包 | PyInstaller (工具自身打包目标) |

## 项目结构

```
python_exe_packer/
├── main.py                     # 入口（高DPI适配 + 启动）
├── _version.py                 # 版本号
├── _metadata.py                # 应用名称、作者等元数据（新增）
├── app/
│   ├── __init__.py
│   └── application.py          # QApplication + 单例 + 主题初始化
├── gui/
│   ├── __init__.py
│   ├── main_window.py          # FluentWindow + 导航侧栏
│   ├── pack_interface.py       # 打包页面（原 config_panel 功能）
│   ├── log_widget.py           # 日志面板
│   ├── template_interface.py   # 模板管理页面
│   ├── history_interface.py    # 历史统计页面
│   ├── env_interface.py        # 环境管理页面
│   ├── about_interface.py      # 关于页面
│   └── dialogs/
│       ├── __init__.py
│       ├── preview_dialog.py   # 命令预览对话框
│       └── pyi_version_dialog.py  # PyInstaller 版本管理对话框
├── core/
│   ├── __init__.py
│   ├── packer.py               # 核心打包逻辑（回调/信号驱动）
│   ├── dependency.py           # 依赖分析（不变）
│   ├── cache_cleaner.py        # 缓存清理（不变）
│   ├── upx_compressor.py       # UPX 压缩（不变）
│   ├── upx_downloader.py       # UPX 下载（不变）
│   ├── inno_setup.py           # Inno Setup 集成（不变）
│   └── installer.py            # NSIS 安装包生成（不变）
├── utils/
│   ├── __init__.py
│   ├── config_manager.py       # 配置管理（改用 QStandardPaths）
│   ├── env_checker.py          # 环境检测（不变）
│   ├── log_utils.py            # 日志工具（精简，保留核心）
│   ├── file_utils.py           # 文件操作（不变）
│   └── error_parser.py         # 错误解析（不变）
├── resources/
│   ├── icons/                  # 导航图标 SVG/PNG
│   ├── qss/                    # 自定义 QSS 样式（可选）
│   └── icon.ico                # 应用图标
└── requirements.txt
```

## 架构设计

### 应用层（app/）

`application.py` 负责：
- 创建 QApplication 实例
- 设置应用名称、组织名（基于 QStandardPaths）
- 初始化 QFluentWidgets 主题系统
- 检查单例运行（复用 `core.single_instance`）

### GUI 层（gui/）

**main_window.py**：继承 `MSFluentWindow`

导航项定义（5 项）：

| routeKey | 图标 | 标题 | 位置 |
|----------|------|------|------|
| pack | FluentIcon.VIEW_LIST | 打包 | TOP |
| template | FluentIcon.LIBRARY | 模板管理 | TOP |
| history | FluentIcon.DATE_TIME | 历史统计 | TOP |
| env | FluentIcon.SETTING | 环境管理 | TOP |
| about | FluentIcon.INFO | 关于 | BOTTOM |

**pack_interface.py**（打包页面）：
- 左侧主配置区：ScrollArea 内含 Card 分组
  - 基础信息：源文件、输出目录、输出文件名（带浏览按钮）
  - 打包选项（可折叠）：单文件/多文件、隐藏控制台、自动清理、UPX、安装包
  - 依赖管理（可折叠）：隐藏导入列表、排除模块列表
  - 高级选项（可折叠）：图标、版本、自定义参数、Python 解释器
- 右侧日志区：固定宽度面板 + 日志列表
- 底部操作栏：命令预览 + 开始打包 + 停止按钮 + 进度条

**log_widget.py**：
- 基于 QListWidget
- 支持颜色区分（INFO/Success/Warning/Error）
- 自动滚动到底部
- 清空日志功能

**template_interface.py**：
- 左侧模板列表（Card/ListWidget）
- 右侧模板详情展示
- 操作：保存、加载、删除、导出（JSON）、导入（JSON）

**history_interface.py**：
- 顶部统计卡片：总次数、成功率、平均耗时
- 下方 TableView：时间、源文件、模式、结果、耗时
- 操作：清空历史、导出

**env_interface.py**：
- CardWidget 列表，逐项显示环境检测结果
- 操作按钮：重新检测、安装/修复（如 PyInstaller 缺失时引导安装）

**about_interface.py**：
- 居中布局：图标 + 名称 + 版本 + 版权信息

### 核心层（core/）

核心改动仅限于 **packer.py**，将其回调接口从简单的函数引用改为 Qt 信号机制：

```python
class Packer(QObject):
    log_signal = Signal(str)
    progress_signal = Signal(int, str)
    finished_signal = Signal(bool, dict, int)  # success, config, duration
```

其他 core/ 模块保持不变——它们不依赖 Qt，保持纯 Python 业务逻辑。

### 工具层（utils/）

**config_manager.py** 改动：
- `platformdirs` 依赖移除，改用 `QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)`
- 其余逻辑不变

其他 utils/ 模块基本不变，`log_utils.py` 中移除 tkinter 相关的回调逻辑，改为纯 Python logger 方式。

## 数据流

```
用户操作 → pack_interface (表单) → Packer.pack(config)
                                    ↓
                         packer.py 执行打包
                                    ↓
                    log_signal / progress_signal
                                    ↓
              pack_interface 更新 UI + log_widget 追加日志
                                    ↓
                    finished_signal(success, config, duration)
                                    ↓
                main_window 显示结果统计 + ConfigManager.add_to_history()
```

## 配置持久化

config_manager.py 存储位置：
- Windows: `C:/Users/<user>/AppData/Local/PyPacker/config.json`
- 通过 `QStandardPaths.AppDataLocation` 获取（跨平台）

## 主题

QFluentWidgets 内置 Fluent主题（浅色/深色），通过 `setTheme()` 切换。
默认跟随系统主题，在 application.py 初始化时通过 `qconfig.theme = Theme.AUTO` 设置。

## 错误处理

- packer.py 执行 PyInstaller 时的错误：通过 ErrorParser 解析后以 log_signal 输出
- 配置验证错误：在 pack_interface 本地校验后弹出提示
- 环境检测失败：在 env_interface 中以黄色/红色卡片展示

## 待移除的依赖

- `ttkbootstrap`（完全移除）
- `platformdirs`（由 QStandardPaths 替代）
- `windnd`（由 Qt 的 drag-drop 事件替代）

## 新增依赖

- `PySide6`（Qt6 官方 Python 绑定）
- `PySide6-Fluent-Widgets`（QFluentWidgets 组件库）
