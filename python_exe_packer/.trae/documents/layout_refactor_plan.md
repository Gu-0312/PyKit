# 布局重构计划

## 项目调研结论

当前 `config_panel.py` 使用 `grid` 布局但存在以下问题：
- 分组框左右边距过大（padx=12），导致两侧大片灰色空白
- 输入框和列表框尺寸固定（width/height），未充分利用空间
- 分组之间垂直间距较大（pady=10-12），底部留白多
- 标签页使用默认宽度，未等宽排布

## 修改文件

- `gui/config_panel.py` - 主要修改目标，重新布局三个标签页
- `gui/main_window.py` - 调整 Notebook 样式，使标签等宽

## 修改步骤

### 步骤1：修改 main_window.py - 标签等宽

在 `_setup_styles()` 中添加 Notebook 标签等宽配置：
```python
style.configure('TNotebook', tabmargins=[0, 0, 0, 0])
```

### 步骤2：重写 config_panel.py

#### 通用调整（三个页面）
1. Notebook pack 边距改为 padx=4, pady=4
2. 所有 LabelFrame grid 改为 padx=6, pady=(6, 0) 或 pady=4
3. 所有容器添加 columnconfigure(0, weight=1) 或 columnconfigure(1, weight=1)

#### 基础配置页面调整
1. 基本设置分组：columnconfigure(1, weight=1)，输入框 sticky=tk.W+tk.E
2. 打包模式分组：RadioButton 使用 sticky=tk.W+tk.E，左右均匀分布
3. 高级选项分组：Checkbutton 使用 sticky=tk.W+tk.E

#### 高级选项页面调整
1. 界面设置分组：输入框整行拉伸，复选框占满宽度
2. 数据文件分组：Listbox 删除 width/height，添加 sticky=tk.N+tk.S+tk.W+tk.E，高度提升
3. 版本信息分组：输入框横向拉伸

#### 依赖管理页面调整
1. 顶部按钮框架：添加 columnconfigure 使按钮等宽
2. 依赖模块分组：Listbox 删除 width/height，添加 sticky=tk.N+tk.S+tk.W+tk.E
3. 排除模块分组：同依赖模块分组

## 潜在依赖与注意事项

1. 确保所有控件变量名不变，避免影响其他模块
2. 保持原有功能不变，仅调整尺寸和布局
3. 测试窗口缩放时控件是否正确响应

## 风险处理

1. 如果布局出现错位，逐步调整 columnconfigure 和 sticky 参数
2. Listbox 设置高度时注意不要超出窗口范围
3. 标签等宽可能在不同系统上表现不同，需测试验证