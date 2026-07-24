import os
import shutil
from utils.log_utils import get_logger
from utils.file_utils import delete_dir, delete_file


logger = get_logger()


class CacheCleaner:
    PYINSTALLER_DIRS = ["build", "dist"]
    CACHE_DIRS = ["__pycache__", ".pytest_cache", ".tox", ".eggs"]
    CACHE_FILES = ["*.pyc", "*.pyo", "*.pyd", "*.egg-info"]

    def __init__(self):
        self.cleaned_files = 0
        self.cleaned_dirs = 0

    def clean_pyinstaller_cache(self, project_dir):
        self.cleaned_files = 0
        self.cleaned_dirs = 0

        logger.info(f"开始清理PyInstaller缓存: {project_dir}")

        for dir_name in self.PYINSTALLER_DIRS:
            dir_path = os.path.join(project_dir, dir_name)
            if os.path.exists(dir_path):
                delete_dir(dir_path)
                self.cleaned_dirs += 1
                logger.info(f"已删除目录: {dir_path}")

        spec_file = os.path.join(project_dir, "*.spec")
        import glob
        for spec in glob.glob(spec_file):
            delete_file(spec)
            self.cleaned_files += 1
            logger.info(f"已删除文件: {spec}")

        logger.info(f"PyInstaller缓存清理完成: 删除 {self.cleaned_dirs} 个目录, {self.cleaned_files} 个文件")

    def clean_python_cache(self, project_dir):
        self.cleaned_files = 0
        self.cleaned_dirs = 0

        logger.info(f"开始清理Python缓存: {project_dir}")

        for root, dirs, files in os.walk(project_dir):
            dirs[:] = [d for d in dirs if d not in ("venv", ".venv", "env")]

            for cache_dir in self.CACHE_DIRS:
                if cache_dir in dirs:
                    cache_path = os.path.join(root, cache_dir)
                    delete_dir(cache_path)
                    self.cleaned_dirs += 1
                    dirs.remove(cache_dir)
                    logger.debug(f"已删除缓存目录: {cache_path}")

            import fnmatch
            for file in files:
                if any(fnmatch.fnmatch(file, pattern) for pattern in self.CACHE_FILES):
                    file_path = os.path.join(root, file)
                    delete_file(file_path)
                    self.cleaned_files += 1
                    logger.debug(f"已删除缓存文件: {file_path}")

        logger.info(f"Python缓存清理完成: 删除 {self.cleaned_dirs} 个目录, {self.cleaned_files} 个文件")

    def clean_all(self, project_dir):
        logger.info(f"开始全面清理缓存: {project_dir}")
        self.clean_pyinstaller_cache(project_dir)
        self.clean_python_cache(project_dir)
        logger.info("全面缓存清理完成")

    def get_cleaned_stats(self):
        return {
            "files": self.cleaned_files,
            "dirs": self.cleaned_dirs
        }

    def delete_dir(self, dir_path):
        delete_dir(dir_path)

    @staticmethod
    def clean_temp_files(temp_dir=None):
        if temp_dir is None:
            temp_dir = os.environ.get("TEMP", "/tmp")

        logger.info(f"清理临时目录: {temp_dir}")

        packer_temp = os.path.join(temp_dir, "pyinstaller")
        if os.path.exists(packer_temp):
            delete_dir(packer_temp)
            logger.info(f"已删除PyInstaller临时目录: {packer_temp}")

        packer_logs = os.path.join(temp_dir, "py_packer_*.log")
        import glob
        for log_file in glob.glob(packer_logs):
            if os.path.isfile(log_file):
                try:
                    os.remove(log_file)
                    logger.debug(f"已删除日志文件: {log_file}")
                except OSError:
                    pass