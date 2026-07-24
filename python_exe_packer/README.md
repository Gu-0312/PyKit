# PyKit - Python EXE Packer

一键将 Python 项目打包为 Windows 可执行文件的图形化工具，基于 PyInstaller。  
A graphical tool for one-click packaging of Python projects into Windows executables, powered by PyInstaller.

---

## 截图 / Screenshot

![PyKit](https://img.shields.io/badge/PyKit-1.0.0-blue) ![Python](https://img.shields.io/badge/Python-3.8%2B-green) ![PySide6](https://img.shields.io/badge/PySide6-6.5%2B-orange)

---

## 功能特性 / Features

### 打包功能 / Packaging

- **一键打包**：支持单文件 (`--onefile`) 和多文件 (`--onedir`) 两种模式
- **隐藏控制台**：可选无控制台窗口运行 (`--noconsole`)
- **UPX 压缩**：集成 UPX，进一步减小体积
- **自动排除**：自动排除测试/文档/缓存等无用模块
- **自动检测依赖**：智能分析源码中的 import，自动添加隐藏导入
- **批处理模式**：批量打包多个项目
- **打包文件分析器**：分析已打包 EXE 的内部结构

### 环境管理 / Environment

- **虚拟环境扫描**：自动检测项目目录中的 `.venv` / `venv` / `env` 等虚拟环境
- **一键创建 Venv**：支持从界面直接创建并初始化虚拟环境
- **环境检查**：启动时自动检测 Python、PyInstaller、pip 等环境状态
- **多解释器支持**：指定任意 Python 解释器路径

### 界面与体验 / UI & UX

- **精美的 Fluent Design 界面**：基于 QFluentWidgets，支持 FluentUI 风格
- **深色/浅色主题**：一键切换，跟随系统
- **多语言支持**：内置国际化框架
- **配置记忆**：自动保存和恢复打包配置
- **打包历史统计**：记录打包次数、成功/失败统计
- **实时日志**：打包过程实时输出详细日志
- **图标制作工具**：PNG → ICO 格式转换

### 安装包 / Installer

- **Inno Setup 集成**：打包完成后自动生成 Windows 安装程序
- **版本号管理**：支持设置应用版本号
- **自定义图标**：支持自定义 EXE 和安装包图标

---

## 系统要求 / System Requirements

- **OS**: Windows 10 / 11 (64-bit)
- **Python**: 3.8+
- **PyInstaller**: 5.0+

---

## 快速开始 / Quick Start

```bash
# 克隆仓库 / Clone repository
git clone https://github.com/Gu-0312/PyKit.git
cd PyKit

# 安装依赖 / Install dependencies
pip install -r requirements.txt

# 运行程序 / Run the application
python main.py
```

### 依赖列表 / Dependencies

```
PySide6>=6.5.0
PySide6-Fluent-Widgets>=1.0.0
Pillow>=10.0.0
```

可通过以下方式安装 PyInstaller（若未安装）：  
Install PyInstaller if not already installed:

```bash
pip install pyinstaller
```

---

## 使用指南 / User Guide

### 基本流程 / Basic Workflow

1. **选择源文件** — 点击「浏览」选择要打包的 `.py` 文件
2. **配置选项** — 选择打包模式、输出路径、图标等
3. **开始打包** — 点击「开始打包」，等待完成
4. **自动打开输出目录** — 打包完成后自动打开输出文件夹

### 高级用法 / Advanced Usage

| 功能 | 说明 |
|------|------|
| **自动检测依赖** | 开启后自动扫描源码中的 import，生成 `--hidden-import` 列表 |
| **自动排除模块** | 排除 `test`、`docs`、`__pycache__` 等无用模块，减小体积 |
| **批处理模式** | 在「批处理」对话框中添加多个项目，一次完成全部打包 |
| **虚拟环境** | 开启「自动检测 Venv」后会自动使用项目虚拟环境中的 PyInstaller |
| **自定义 PyInstaller 参数** | 在「额外参数」中输入任意 PyInstaller 原生参数 |
| **打包文件分析** | 选择已生成的 EXE，点击「分析」查看内部模块结构 |

---

## 项目结构 / Project Structure

```
PyKit/
├── python_exe_packer/
│   ├── app/                 # 应用入口 / Application entry
│   ├── core/                # 核心逻辑 / Core logic
│   │   ├── packer.py        # 打包引擎 / Packaging engine
│   │   ├── dependency.py    # 依赖分析 / Dependency analyzer
│   │   ├── inno_setup.py    # Inno Setup 集成 / Installer generation
│   │   └── upx_compressor.py # UPX 压缩 / UPX compression
│   ├── gui/                 # 图形界面 / GUI
│   │   ├── main_window.py   # 主窗口 / Main window
│   │   ├── pack_interface.py # 打包界面 / Pack interface
│   │   ├── env_interface.py # 环境管理 / Environment management
│   │   ├── icon_maker_interface.py # 图标制作 / Icon maker
│   │   └── ...
│   ├── utils/               # 工具模块 / Utilities
│   │   ├── env_checker.py   # 环境检测 / Environment checker
│   │   ├── config_manager.py # 配置管理 / Config manager
│   │   └── ...
│   ├── main.py              # 程序入口 / Entry point
│   └── requirements.txt     # 依赖列表 / Dependencies
└── config/                  # 配置文件 / Configuration files
```

---

## 技术栈 / Tech Stack

| 组件 | 技术 |
|------|------|
| **GUI 框架** | PySide6 (Qt6) |
| **UI 组件库** | QFluentWidgets (Fluent Design) |
| **打包引擎** | PyInstaller |
| **图标处理** | Pillow (PIL) |
| **安装包** | Inno Setup |
| **压缩** | UPX |

---

## 常见问题 / FAQ

**Q: 生成的 EXE 体积很大 / The generated EXE is too large**  
A: 开启「自动排除模块」可以大幅减小体积。PySide6 应用通常需要 30-80MB。Enable "Auto Exclude Modules" to reduce size. PySide6 apps typically need 30-80MB.

**Q: 提示 PyInstaller 未安装 / PyInstaller not found**  
A: 运行 `pip install pyinstaller`。程序启动时会自动检测环境。Run `pip install pyinstaller`. The app checks the environment on startup.

**Q: 打包后运行时缺少模块 / Missing module at runtime**  
A: 开启「自动检测依赖」或手动在「隐藏导入」中添加缺失的模块。Enable "Auto Detect Dependencies" or manually add the missing module to "Hidden Imports".

**Q: 支持打包为单个 EXE 吗？/ Support single-file packaging?**  
A: 支持，选择「单文件模式」即可。Yes, select "Single File Mode".

---

## 许可证 / License

MIT License

Copyright (c) 2026 Gu-0312

## 作者 / Author

**Gu-0312** — [GitHub](https://github.com/Gu-0312)

## 免责声明 / Disclaimer

本工具仅供参考，不提供任何担保。用户在使用本工具时应遵守相关法律法规，开发者对因使用本工具造成的任何损失或问题不承担责任。  
This tool is for reference only and is provided without any warranty. Users should comply with applicable laws when using this tool. The developer assumes no responsibility for any loss or issues caused by the use of this tool.
