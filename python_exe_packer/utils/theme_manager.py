from qfluentwidgets import Theme, qconfig


class ThemeManager:
    """主题管理器 - 只负责QPlainTextEdit等非qfluentwidgets组件的样式"""

    def __init__(self):
        self._current_theme = qconfig.theme

    def get_log_colors(self):
        """获取日志组件的颜色配置"""
        if self._current_theme == Theme.DARK:
            return {
                "INFO": "#9CA3AF",
                "SUCCESS": "#34D399",
                "WARNING": "#FBBF24",
                "ERROR": "#F87171",
            }
        return {
            "INFO": "#6B7280",
            "SUCCESS": "#10B981",
            "WARNING": "#F59E0B",
            "ERROR": "#EF4444",
        }

    def get_log_widget_stylesheet(self):
        """获取日志组件(QPlainTextEdit)的样式表"""
        if self._current_theme == Theme.DARK:
            return """
                QPlainTextEdit {
                    background-color: #2D2D2D;
                    color: #F3F4F6;
                    border: none;
                    font-family: Consolas, Monaco, monospace;
                    font-size: 13px;
                    padding: 8px;
                }
                QPlainTextEdit::focus {
                    outline: none;
                }
            """
        else:
            return """
                QPlainTextEdit {
                    background-color: #FFFFFF;
                    color: #1F2937;
                    border: none;
                    font-family: Consolas, Monaco, monospace;
                    font-size: 13px;
                    padding: 8px;
                }
                QPlainTextEdit::focus {
                    outline: none;
                }
            """

    def update_theme(self, theme):
        """更新当前主题状态"""
        self._current_theme = theme


_theme_manager = None


def get_theme_manager():
    global _theme_manager
    if _theme_manager is None:
        _theme_manager = ThemeManager()
    return _theme_manager
