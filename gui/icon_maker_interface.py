import os
from PIL import Image
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QGroupBox, QCheckBox,
    QMessageBox, QFileDialog, QScrollArea
)
from PySide6.QtGui import QPixmap, QImage
from qfluentwidgets import (
    PushButton, LineEdit, InfoBar, InfoBarPosition,
    setTheme, Theme, CardWidget
)

from utils.i18n import tr


class IconMakerInterface(QWidget):
    """图标制作工具界面"""

    def __init__(self):
        super().__init__()
        self.init_ui()
        self._connect_signals()

    def init_ui(self):
        self.setObjectName("iconMakerInterface")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        # 标题
        title_label = QLabel(tr("icon_maker_title"))
        title_label.setStyleSheet("font-size: 24px; font-weight: bold;")
        layout.addWidget(title_label)

        # 源文件选择
        source_group = CardWidget(self)
        source_layout = QVBoxLayout(source_group)
        source_layout.setContentsMargins(20, 15, 20, 15)
        
        source_title = QLabel(tr("icon_source_file"))
        source_title.setStyleSheet("font-size: 14px; font-weight: 600; margin-bottom: 10px;")
        source_layout.addWidget(source_title)
        
        source_row = QHBoxLayout()
        self.source_edit = LineEdit()
        self.source_edit.setPlaceholderText(tr("icon_select_source"))
        self.source_btn = PushButton(tr("browse"))
        source_row.addWidget(self.source_edit)
        source_row.addWidget(self.source_btn)
        source_layout.addLayout(source_row)
        layout.addWidget(source_group)

        # 预览区域
        preview_group = CardWidget(self)
        preview_layout = QVBoxLayout(preview_group)
        preview_layout.setContentsMargins(20, 15, 20, 15)
        
        preview_title = QLabel(tr("icon_preview"))
        preview_title.setStyleSheet("font-size: 14px; font-weight: 600; margin-bottom: 10px;")
        preview_layout.addWidget(preview_title)
        
        self.preview_label = QLabel()
        self.preview_label.setStyleSheet("background-color: #f0f0f0; border-radius: 8px;")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setMinimumHeight(200)
        preview_layout.addWidget(self.preview_label)
        layout.addWidget(preview_group)

        # 输出设置
        output_group = CardWidget(self)
        output_layout = QVBoxLayout(output_group)
        output_layout.setContentsMargins(20, 15, 20, 15)
        
        output_title = QLabel(tr("icon_output_settings"))
        output_title.setStyleSheet("font-size: 14px; font-weight: 600; margin-bottom: 10px;")
        output_layout.addWidget(output_title)
        
        # 输出路径
        output_row = QHBoxLayout()
        self.output_edit = LineEdit()
        self.output_edit.setPlaceholderText(tr("icon_select_output"))
        self.output_btn = PushButton(tr("browse"))
        output_row.addWidget(self.output_edit)
        output_row.addWidget(self.output_btn)
        output_layout.addLayout(output_row)
        
        # 尺寸选择
        sizes_title = QLabel(tr("icon_sizes"))
        sizes_title.setStyleSheet("font-size: 13px; font-weight: 500; margin-top: 15px; margin-bottom: 10px;")
        output_layout.addWidget(sizes_title)
        
        size_options = [
            (16, "16x16"),
            (32, "32x32"),
            (48, "48x48"),
            (64, "64x64"),
            (128, "128x128"),
            (256, "256x256"),
        ]
        
        sizes_row = QHBoxLayout()
        sizes_row.setSpacing(10)
        self.size_checkboxes = {}
        for size, label in size_options:
            cb = QCheckBox(f"{label}")
            cb.setChecked(True)
            self.size_checkboxes[size] = cb
            sizes_row.addWidget(cb)
        output_layout.addLayout(sizes_row)
        
        # 保持比例
        self.keep_ratio_cb = QCheckBox(tr("icon_keep_ratio"))
        self.keep_ratio_cb.setChecked(True)
        output_layout.addWidget(self.keep_ratio_cb)
        
        # 添加透明背景
        self.transparent_bg_cb = QCheckBox(tr("icon_transparent_bg"))
        output_layout.addWidget(self.transparent_bg_cb)
        
        layout.addWidget(output_group)

        # 转换按钮
        self.convert_btn = PushButton(tr("icon_convert"))
        self.convert_btn.setStyleSheet("font-size: 16px; padding: 10px 40px;")
        layout.addWidget(self.convert_btn)

        # 底部提示
        tips_label = QLabel(tr("icon_tips"))
        tips_label.setStyleSheet("font-size: 12px; color: #666;")
        tips_label.setWordWrap(True)
        layout.addWidget(tips_label)

    def _connect_signals(self):
        self.source_btn.clicked.connect(self._select_source)
        self.output_btn.clicked.connect(self._select_output)
        self.convert_btn.clicked.connect(self._convert)
        self.source_edit.textChanged.connect(self._update_preview)

    def _select_source(self):
        """选择源图片文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            tr("icon_select_source"),
            "",
            tr("icon_image_formats")
        )
        if file_path:
            self.source_edit.setText(file_path)
            self._update_preview()

    def _select_output(self):
        """选择输出目录"""
        dir_path = QFileDialog.getExistingDirectory(
            self,
            tr("icon_select_output"),
            ""
        )
        if dir_path:
            self.output_edit.setText(dir_path)

    def _update_preview(self):
        """更新预览"""
        path = self.source_edit.text().strip()
        if not path or not os.path.exists(path):
            self.preview_label.clear()
            self.preview_label.setText(tr("icon_no_preview"))
            return
        
        try:
            pixmap = QPixmap(path)
            if pixmap.isNull():
                self.preview_label.setText(tr("icon_invalid_image"))
                return
            
            # 缩放预览
            preview_size = 150
            pixmap = pixmap.scaled(
                preview_size, preview_size,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.preview_label.setPixmap(pixmap)
        except Exception as e:
            self.preview_label.setText(f"{tr('icon_preview_error')}: {str(e)}")

    def _convert(self):
        """转换图片为ICO格式"""
        source_path = self.source_edit.text().strip()
        output_dir = self.output_edit.text().strip()
        
        if not source_path or not os.path.exists(source_path):
            InfoBar.warning(
                title=tr("warning"),
                content=tr("icon_select_source_first"),
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP_RIGHT,
                duration=3000,
                parent=self
            )
            return
        
        if not output_dir or not os.path.isdir(output_dir):
            InfoBar.warning(
                title=tr("warning"),
                content=tr("icon_select_output_first"),
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP_RIGHT,
                duration=3000,
                parent=self
            )
            return
        
        # 获取选中的尺寸
        selected_sizes = [size for size, cb in self.size_checkboxes.items() if cb.isChecked()]
        if not selected_sizes:
            InfoBar.warning(
                title=tr("warning"),
                content=tr("icon_select_at_least_one_size"),
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP_RIGHT,
                duration=3000,
                parent=self
            )
            return
        
        # 排序尺寸（从小到大）
        selected_sizes.sort()
        
        try:
            # 打开源图片
            image = Image.open(source_path)
            
            # 如果图片模式不是RGBA，转换为RGBA
            if image.mode != 'RGBA':
                image = image.convert('RGBA')
            
            # 添加透明背景：将白色背景替换为透明
            if self.transparent_bg_cb.isChecked():
                # 获取像素数据
                datas = image.getdata()
                
                # 创建新的像素数据，将白色（接近白色）替换为透明
                new_data = []
                for item in datas:
                    # 检查是否接近白色（R, G, B > 240）
                    if item[0] > 240 and item[1] > 240 and item[2] > 240:
                        new_data.append((255, 255, 255, 0))  # 透明
                    else:
                        new_data.append(item)
                
                # 更新图片数据
                image.putdata(new_data)
            
            # 创建图标尺寸列表
            icon_sizes = [(size, size) for size in selected_sizes]
            
            # 生成文件名
            base_name = os.path.splitext(os.path.basename(source_path))[0]
            output_path = os.path.join(output_dir, f"{base_name}.ico")
            
            # 保存为ICO
            image.save(output_path, format='ICO', sizes=icon_sizes)
            
            InfoBar.success(
                title=tr("success"),
                content=tr("icon_convert_success").format(path=output_path),
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP_RIGHT,
                duration=3000,
                parent=self
            )
            
        except Exception as e:
            InfoBar.error(
                title=tr("error"),
                content=tr("icon_convert_error").format(error=str(e)),
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP_RIGHT,
                duration=3000,
                parent=self
            )

    def retranslateUi(self):
        """重新翻译界面"""
        pass