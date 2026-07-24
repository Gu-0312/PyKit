import os
import sys
import subprocess
from utils.log_utils import get_logger
from utils.file_utils import run_hidden


logger = get_logger()


class UPXCompressor:
    def __init__(self):
        self.upx_path = self._find_upx()
        if self.upx_path:
            logger.info(f"[UPX] UPX路径: {self.upx_path}")
            version = self.get_upx_version()
            if version:
                logger.info(f"[UPX] UPX版本: {version}")
        else:
            logger.info("[UPX] UPX不可用，压缩功能已禁用")

    def _find_upx(self):
        # 先在打包后 EXE 的解压目录中找
        if getattr(sys, 'frozen', False):
            base = sys._MEIPASS
            meipass_exe = os.path.join(base, "upx.exe")
            if os.path.exists(meipass_exe):
                return meipass_exe
            # 也看看 EXE 同级目录
            exe_dir = os.path.dirname(sys.executable)
            side_exe = os.path.join(exe_dir, "upx.exe")
            if os.path.exists(side_exe):
                return side_exe

        paths = [
            os.path.join(os.environ.get("PROGRAMFILES", "C:\\Program Files"), "UPX"),
            os.path.join(os.environ.get("PROGRAMFILES(X86)", "C:\\Program Files (x86)"), "UPX"),
            os.path.join(os.environ.get("LOCALAPPDATA", "C:\\Users"), "Programs", "UPX"),
            os.path.dirname(os.path.abspath(__file__)),
        ]

        for path in paths:
            upx_exe = os.path.join(path, "upx.exe")
            if os.path.exists(upx_exe):
                return upx_exe

        for path in os.environ.get("PATH", "").split(os.pathsep):
            upx_exe = os.path.join(path, "upx.exe")
            if os.path.exists(upx_exe):
                return upx_exe

        return None

    def is_available(self):
        return self.upx_path is not None

    def set_upx_path(self, path):
        if os.path.exists(path):
            self.upx_path = path
            return True
        return False

    def compress_file(self, file_path, best_compression=True):
        if not self.is_available():
            logger.error("[UPX] UPX不可用，请安装UPX或指定正确路径")
            return False

        if not os.path.exists(file_path):
            logger.error(f"[UPX] 文件不存在: {file_path}")
            return False

        original_size = os.path.getsize(file_path)
        logger.info(f"[UPX] 开始压缩文件: {file_path}")
        logger.info(f"[UPX] 原始大小: {original_size / 1024:.2f} KB")

        cmd = [self.upx_path]

        if best_compression:
            cmd.append("--best")
            logger.debug("[UPX] 使用最高压缩级别")
        else:
            cmd.append("--compress-level=9")
            logger.debug("[UPX] 使用压缩级别9")

        cmd.extend(["--no-progress", file_path])

        try:
            logger.debug(f"[UPX] 执行命令: {' '.join(cmd)}")
            result = run_hidden(
                cmd,
                capture_output=True,
                timeout=300
            )

            if result.returncode == 0:
                compressed_size = os.path.getsize(file_path)
                ratio = (1 - compressed_size / original_size) * 100
                logger.info(f"[UPX] 压缩成功")
                logger.info(f"[UPX] 压缩后大小: {compressed_size / 1024:.2f} KB")
                logger.info(f"[UPX] 压缩率: {ratio:.2f}%")
                if result.stdout:
                    logger.debug(f"[UPX] UPX输出: {result.stdout}")
                return True
            else:
                logger.error(f"[UPX] 压缩失败，返回码: {result.returncode}")
                if result.stderr:
                    logger.error(f"[UPX] 错误信息: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            logger.error("[UPX] 压缩超时(300秒)")
            return False
        except Exception as e:
            logger.error(f"[UPX] 压缩异常: {type(e).__name__}: {str(e)}")
            return False

    def compress_directory(self, dir_path, best_compression=True):
        exe_files = []
        for root, dirs, files in os.walk(dir_path):
            for file in files:
                if file.endswith(".exe") or file.endswith(".dll"):
                    exe_files.append(os.path.join(root, file))

        if not exe_files:
            logger.warning("目录中没有可压缩的文件")
            return False

        logger.info(f"找到 {len(exe_files)} 个可压缩文件")

        success_count = 0
        for file_path in exe_files:
            if self.compress_file(file_path, best_compression):
                success_count += 1

        logger.info(f"UPX压缩完成: {success_count}/{len(exe_files)} 个文件成功")
        return success_count == len(exe_files)

    def get_upx_version(self):
        if not self.is_available():
            return None

        try:
            result = run_hidden(
                [self.upx_path, "--version"],
                capture_output=True,
                timeout=10
            )

            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass

        return None