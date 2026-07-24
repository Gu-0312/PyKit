# Python一键打包EXE

基于 PyInstaller 的 Python 一键打包工具，提供直观的图形化界面，让打包变得简单高效。

## 功能特性

- **一键打包**：支持单文件和多文件两种打包模式
- **自动检测**：智能检测项目依赖和虚拟环境
- **隐藏控制台**：支持无控制台模式运行
- **图标设置**：自定义程序图标
- **UPX压缩**：支持UPX压缩减小文件体积
- **安装包生成**：支持Inno Setup生成安装程序
- **配置记忆**：自动保存和加载打包配置
- **图标制作**：内置PNG转ICO图标工具

## 系统要求

- Windows 10/11
- Python 3.8+
- PyInstaller 5.0+

## 安装依赖

```bash
pip install -r requirements.txt
```

## 运行程序

```bash
python main.py
```

## 使用说明

### 基本设置

1. **选择源文件**：点击浏览按钮选择要打包的 Python 脚本
2. **选择输出目录**：设置打包后文件的输出位置
3. **设置输出名称**：自定义生成的 EXE 文件名

### 打包选项

- **单文件模式**：将所有依赖打包成单个 EXE 文件
- **多文件模式**：生成一个包含多个文件的目录
- **隐藏控制台**：运行时不显示命令行窗口
- **自动清理缓存**：打包前自动清理旧的构建文件
- **启用 UPX 压缩**：使用 UPX 压缩减小文件体积

### 高级选项

- **图标文件**：设置程序图标（必须是 .ico 格式）
- **应用版本**：设置应用版本号
- **自定义参数**：添加额外的 PyInstaller 参数

### 依赖管理

- **自动检测**：自动分析项目依赖并添加隐藏导入
- **隐藏导入**：手动添加需要额外导入的模块
- **排除模块**：排除不需要的模块以减小体积

## 项目结构

```
python_exe_packer/
├── app/                 # 应用程序入口
│   └── application.py   # 应用程序类
├── core/                # 核心功能模块
│   ├── packer.py       # 打包核心逻辑
│   ├── dependency.py   # 依赖分析
│   ├── inno_setup.py   # Inno Setup 安装包生成
│   ├── upx_compressor.py # UPX 压缩
│   └── single_instance.py # 单实例检测
├── gui/                 # 图形界面
│   ├── main_window.py  # 主窗口
│   ├── pack_interface.py # 打包界面
│   ├── template_interface.py # 模板管理
│   ├── history_interface.py # 历史统计
│   ├── env_interface.py # 环境管理
│   ├── icon_maker_interface.py # 图标制作
│   └── about_interface.py # 关于页面
├── utils/               # 工具模块
│   ├── config_manager.py # 配置管理
│   ├── env_checker.py  # 环境检测
│   ├── file_utils.py   # 文件工具
│   ├── i18n.py         # 国际化支持
│   └── theme_manager.py # 主题管理
├── icon.ico             # 应用图标
├── main.py              # 程序入口
├── requirements.txt     # 依赖列表
└── _metadata.py         # 应用元数据
```

## 技术栈

- **框架**：PySide6 + Qt6
- **UI组件**：QFluentWidgets
- **打包工具**：PyInstaller
- **图标处理**：Pillow

## 许可证

MIT License

## 作者

Gu-0312

## 免责声明

本工具仅供参考，不提供任何担保。作者对使用本工具造成的任何损失或问题不承担责任。请在部署前充分测试您的打包应用。