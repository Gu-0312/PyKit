import os
import json
import tempfile
import logging
from PySide6.QtCore import QStandardPaths
from _version import get_version

logger = logging.getLogger(__name__)


class ConfigManager:
    def __init__(self):
        self.config_dir = QStandardPaths.writableLocation(
            QStandardPaths.AppLocalDataLocation
        )
        self.config_file = os.path.join(self.config_dir, "config.json")
        self.history_file = os.path.join(self.config_dir, "history.json")
        self.templates_file = os.path.join(self.config_dir, "templates.json")
        self.default_config = {
            "source_file": "",
            "output_dir": "",
            "name": "",
            "single_file": True,
            "windowed": True,
            "icon": "",
            "hidden_imports": [],
            "excludes": [],
            "data_files": [],
            "auto_clean": True,
            "auto_detect_deps": True,
            "app_version": get_version(),
            "auto_open_output": True,
            "custom_args": "",
            "show_save_confirm": True,
            "enable_upx": None,
            "theme": "auto",
            "language": "zh",
        }

    def load_config(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    return {**self.default_config, **config}
            except Exception:
                return self.default_config.copy()
        return self.default_config.copy()

    def save_config(self, config):
        try:
            if not os.path.exists(self.config_dir):
                os.makedirs(self.config_dir)

            fd, temp_path = tempfile.mkstemp(prefix="pypacker_config_", suffix=".tmp", dir=self.config_dir)
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    json.dump(config, f, indent=2, ensure_ascii=False)
                os.replace(temp_path, self.config_file)
                return True
            except Exception:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                return False
        except Exception:
            return False

    def load_history(self, max_count=10):
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, "r", encoding="utf-8") as f:
                    history = json.load(f)
                return history[:max_count]
            except Exception:
                return []
        return []

    def add_to_history(self, config, success, duration=0):
        try:
            import time
            history = self.load_history(max_count=100)
            record = {
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "source_file": config.get("source_file", ""),
                "output_dir": config.get("output_dir", ""),
                "name": config.get("name", ""),
                "single_file": config.get("single_file", False),
                "windowed": config.get("windowed", False),
                "success": success,
                "duration": duration
            }
            history.insert(0, record)
            history = history[:10]
            if not os.path.exists(self.config_dir):
                os.makedirs(self.config_dir)

            fd, temp_path = tempfile.mkstemp(prefix="pypacker_history_", suffix=".tmp", dir=self.config_dir)
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    json.dump(history, f, indent=2, ensure_ascii=False)
                os.replace(temp_path, self.history_file)
                return True
            except Exception:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                return False
        except Exception:
            return False

    def clear_history(self):
        try:
            if os.path.exists(self.history_file):
                os.remove(self.history_file)
            return True
        except Exception:
            return False

    def get_stats(self):
        history = self.load_history(max_count=100)

        if not history:
            return {
                "total_count": 0,
                "success_count": 0,
                "fail_count": 0,
                "success_rate": 0,
                "avg_duration": 0,
                "min_duration": 0,
                "max_duration": 0,
                "latest_time": "",
                "avg_duration_str": "0 秒",
                "min_duration_str": "-",
                "max_duration_str": "-"
            }

        total_count = len(history)
        success_count = sum(1 for h in history if h.get("success", False))
        fail_count = total_count - success_count
        success_rate = round((success_count / total_count) * 100, 1) if total_count > 0 else 0

        durations = [h.get("duration", 0) for h in history if h.get("duration", 0) > 0]
        if durations:
            avg_duration = round(sum(durations) / len(durations), 1)
            min_duration = min(durations)
            max_duration = max(durations)
        else:
            avg_duration = 0
            min_duration = 0
            max_duration = 0

        latest_time = history[0].get("timestamp", "") if history else ""

        return {
            "total_count": total_count,
            "success_count": success_count,
            "fail_count": fail_count,
            "success_rate": success_rate,
            "avg_duration": avg_duration,
            "min_duration": min_duration,
            "max_duration": max_duration,
            "latest_time": latest_time,
            "avg_duration_str": self._format_duration(avg_duration),
            "min_duration_str": self._format_duration(min_duration) if min_duration > 0 else "-",
            "max_duration_str": self._format_duration(max_duration) if max_duration > 0 else "-"
        }

    def _format_duration(self, seconds):
        if seconds < 60:
            return f"{seconds:.1f} 秒"
        else:
            minutes = int(seconds // 60)
            secs = seconds % 60
            return f"{minutes} 分 {secs:.1f} 秒"

    def load_templates(self):
        logger.debug(f"[ConfigManager] 加载模板文件: {self.templates_file}")
        if os.path.exists(self.templates_file):
            try:
                with open(self.templates_file, "r", encoding="utf-8") as f:
                    templates = json.load(f)
                logger.debug(f"[ConfigManager] 成功加载 {len(templates)} 个模板")
                return templates
            except Exception as e:
                logger.error(f"[ConfigManager] 加载模板失败: {e}")
                return []
        else:
            logger.debug(f"[ConfigManager] 模板文件不存在")
            return []

    def save_template(self, name, config, description=""):
        try:
            import time
            templates = self.load_templates()

            template = {
                "name": name,
                "description": description,
                "config": config,
                "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "updated_at": time.strftime("%Y-%m-%d %H:%M:%S")
            }

            existing_index = None
            for i, t in enumerate(templates):
                if t["name"] == name:
                    existing_index = i
                    break

            if existing_index is not None:
                templates[existing_index] = template
            else:
                templates.append(template)

            if not os.path.exists(self.config_dir):
                os.makedirs(self.config_dir)

            fd, temp_path = tempfile.mkstemp(prefix="pypacker_templates_", suffix=".tmp", dir=self.config_dir)
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    json.dump(templates, f, indent=2, ensure_ascii=False)
                os.replace(temp_path, self.templates_file)
                return True
            except Exception:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                return False
        except Exception:
            return False

    def delete_template(self, name):
        try:
            name = str(name)
            templates = self.load_templates()

            templates = [t for t in templates if str(t["name"]) != name]

            if not os.path.exists(self.config_dir):
                os.makedirs(self.config_dir)

            fd, temp_path = tempfile.mkstemp(prefix="pypacker_templates_", suffix=".tmp", dir=self.config_dir)
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    json.dump(templates, f, indent=2, ensure_ascii=False)
                os.replace(temp_path, self.templates_file)
                return True
            except Exception:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                return False
        except Exception:
            return False

    def get_template(self, name):
        name = str(name)
        templates = self.load_templates()
        for template in templates:
            if str(template["name"]) == name:
                return template
        return None

    def get_template_names(self):
        templates = self.load_templates()
        return [t["name"] for t in templates]
