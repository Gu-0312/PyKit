import os
import glob

from utils.i18n import tr


class BuildCleaner:
    def __init__(self):
        self.log_callback = None

    def set_log_callback(self, callback):
        self.log_callback = callback

    def _log(self, msg):
        if self.log_callback:
            self.log_callback(msg)

    def scan(self, project_dir):
        artifacts = {"dirs": [], "files": []}
        for pattern in ("dist", "build"):
            d = os.path.join(project_dir, pattern)
            if os.path.isdir(d):
                artifacts["dirs"].append(d)
        for f in glob.glob(os.path.join(project_dir, "*.spec")):
            artifacts["files"].append(f)
        return artifacts

    def clean(self, project_dir):
        artifacts = self.scan(project_dir)
        total = 0
        for d in artifacts["dirs"]:
            import shutil
            shutil.rmtree(d, ignore_errors=True)
            self._log(f"[clean] 删除目录: {d}")
            total += 1
        for f in artifacts["files"]:
            os.remove(f)
            self._log(f"[clean] 删除文件: {f}")
            total += 1
        return total
