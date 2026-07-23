import sys
import subprocess
import os
import importlib.util


class EnvChecker:
    def __init__(self):
        self.results = {}

    def check_all(self):
        self.results = {
            "python_version": self._check_python_version(),
            "pyinstaller": self._check_pyinstaller(),
            "virtual_env": self._check_virtual_env(),
            "pip_version": self._check_pip_version(),
            "platform": self._check_platform(),
            "encoding": self._check_encoding(),
            "permissions": self._check_permissions(),
        }
        return self.results

    def _check_python_version(self):
        version = sys.version_info
        version_str = f"{version.major}.{version.minor}.{version.micro}"
        is_compatible = version.major >= 3 and version.minor >= 8
        return {
            "name": "Python 版本",
            "value": version_str,
            "status": "success" if is_compatible else "warning",
            "message": "版本兼容" if is_compatible else "建议使用 Python 3.8+",
            "details": f"Python {version_str} ({sys.executable})"
        }

    def _check_pyinstaller(self):
        # Method 1: Check if PyInstaller is importable by current Python (most reliable)
        try:
            spec = importlib.util.find_spec('PyInstaller')
            if spec is not None:
                # Module found, try to get version via sys.executable -m PyInstaller
                try:
                    result = subprocess.run(
                        [sys.executable, "-m", "PyInstaller", "--version"],
                        capture_output=True, text=True, timeout=10,
                        env=self._get_clean_env()
                    )
                    if result.returncode == 0:
                        version = result.stdout.strip()
                        return {
                            "name": "PyInstaller",
                            "value": version,
                            "status": "success",
                            "message": "已安装",
                            "details": f"命令: {sys.executable} -m PyInstaller | PyInstaller {version}"
                        }
                except Exception:
                    pass
                # Module found but can't get version — still installed
                return {
                    "name": "PyInstaller",
                    "value": "已安装",
                    "status": "success",
                    "message": "已安装 (模块检测通过)",
                    "details": f"PyInstaller 模块位于: {spec.origin}"
                }
        except Exception:
            pass

        # Method 2: Fallback to subprocess commands
        python_dir = os.path.dirname(sys.executable)
        scripts_dir = os.path.join(python_dir, "Scripts")
        pyinstaller_exe = os.path.join(scripts_dir, "pyinstaller.exe")

        commands = [
            [sys.executable, "-m", "PyInstaller"],
            ["pyinstaller"],
            [pyinstaller_exe],
        ]

        for cmd in commands:
            try:
                full_cmd = cmd + ["--version"]
                result = subprocess.run(
                    full_cmd,
                    capture_output=True,
                    text=True,
                    timeout=10,
                    env=self._get_clean_env()
                )
                if result.returncode == 0:
                    version = result.stdout.strip()
                    return {
                        "name": "PyInstaller",
                        "value": version,
                        "status": "success",
                        "message": "已安装",
                        "details": f"命令: {' '.join(cmd)} | PyInstaller {version}"
                    }
            except subprocess.TimeoutExpired:
                continue
            except FileNotFoundError:
                continue
            except Exception:
                continue

        return {
            "name": "PyInstaller",
            "value": "未安装",
            "status": "error",
            "message": "请安装 PyInstaller: pip install pyinstaller",
            "details": f"搜索路径: {pyinstaller_exe}"
        }

    def _get_clean_env(self):
        env = os.environ.copy()
        if 'PYTHONPATH' in env:
            del env['PYTHONPATH']
        return env

    def _check_virtual_env(self):
        result = {
            "name": "虚拟环境",
            "value": "否",
            "status": "info",
            "message": "使用全局 Python 环境",
            "details": ""
        }
        venv = getattr(sys, 'real_prefix', None) or getattr(sys, 'base_prefix', None)
        is_venv = sys.prefix != venv if venv else False
        if is_venv:
            return {
                "name": "虚拟环境",
                "value": "是",
                "status": "success",
                "message": f"当前虚拟环境: {sys.prefix}",
                "details": ""
            }
        if not getattr(sys, 'frozen', False):
            found = self._scan_nearby_venvs()
            if found:
                result["value"] = f"发现 {len(found)} 个"
                result["status"] = "info"
                result["message"] = f"附近虚拟环境: {', '.join(found[:3])}"
                result["details"] = "; ".join(found[:5])
        return result

    def _scan_nearby_venvs(self):
        found = []
        candidates = ["venv", ".venv", "env", ".env", "python_env", ".python_env"]
        scripts_dirs = ["Scripts", "bin"]
        start = os.path.dirname(os.path.abspath(__file__))
        for _ in range(4):
            if os.path.isdir(start):
                for name in candidates:
                    venv_dir = os.path.join(start, name)
                    if os.path.isdir(venv_dir):
                        for sd in scripts_dirs:
                            py = os.path.join(venv_dir, sd, "python.exe")
                            if os.path.exists(py):
                                found.append(os.path.abspath(venv_dir))
                                break
            parent = os.path.dirname(start)
            if parent == start:
                break
            start = parent
        return found

    def _check_pip_version(self):
        if getattr(sys, 'frozen', False):
            return {
                "name": "pip",
                "value": "不可用",
                "status": "info",
                "message": "打包环境下不支持 pip 检测",
                "details": "当前为 PyInstaller 打包环境"
            }
            
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "--version"],
                capture_output=True,
                text=True,
                timeout=10,
                env=self._get_clean_env()
            )
            if result.returncode == 0:
                version_info = result.stdout.strip()
                parts = version_info.split()
                if len(parts) >= 2:
                    version = parts[1]
                else:
                    version = version_info[:50] if version_info else "未知版本"
                return {
                    "name": "pip",
                    "value": version,
                    "status": "success",
                    "message": "已安装",
                    "details": version_info
                }
            else:
                return {
                    "name": "pip",
                    "value": "异常",
                    "status": "warning",
                    "message": "pip 状态异常",
                    "details": result.stderr.strip()[:200]
                }
        except IndexError as e:
            return {
                "name": "pip",
                "value": "检测失败",
                "status": "error",
                "message": f"检测失败: pip版本输出格式异常",
                "details": str(e)
            }
        except FileNotFoundError:
            return {
                "name": "pip",
                "value": "不可用",
                "status": "info",
                "message": "pip 命令不可用",
                "details": "当前环境不支持 pip 命令"
            }
        except Exception as e:
            return {
                "name": "pip",
                "value": "检测失败",
                "status": "error",
                "message": f"检测失败: {str(e)}",
                "details": ""
            }

    def _check_platform(self):
        return {
            "name": "操作系统",
            "value": sys.platform,
            "status": "success",
            "message": f"{os.name} ({sys.platform})",
            "details": f"架构: {sys.maxsize > 2**32 and '64位' or '32位'}"
        }

    def _check_encoding(self):
        return {
            "name": "编码",
            "value": sys.getdefaultencoding(),
            "status": "success",
            "message": f"默认编码: {sys.getdefaultencoding()}",
            "details": f"文件系统编码: {sys.getfilesystemencoding()}"
        }

    def _check_permissions(self):
        test_paths = [
            os.path.join(os.path.expanduser("~"), "Desktop"),
            os.path.join(os.path.expanduser("~"), "Documents"),
            os.path.expanduser("~"),
        ]
        
        writable_dirs = []
        for path in test_paths:
            if os.path.exists(path):
                test_file = os.path.join(path, f".temp_perm_test_{os.getpid()}.tmp")
                try:
                    with open(test_file, "w") as f:
                        f.write("test")
                    os.remove(test_file)
                    writable_dirs.append(os.path.basename(path))
                except PermissionError:
                    continue
                except Exception:
                    continue
        
        if writable_dirs:
            return {
                "name": "写入权限",
                "value": "正常",
                "status": "success",
                "message": f"可写入目录: {', '.join(writable_dirs)}",
                "details": ""
            }
        else:
            return {
                "name": "写入权限",
                "value": "受限",
                "status": "warning",
                "message": "常用目录写入权限受限，请确保输出目录有写入权限",
                "details": f"测试目录: {', '.join(test_paths)}"
            }

    def get_summary(self):
        success = sum(1 for r in self.results.values() if r["status"] == "success")
        warning = sum(1 for r in self.results.values() if r["status"] == "warning")
        error = sum(1 for r in self.results.values() if r["status"] == "error")
        info = sum(1 for r in self.results.values() if r["status"] == "info")
        
        return {
            "total": len(self.results),
            "success": success,
            "warning": warning,
            "error": error,
            "info": info,
            "has_error": error > 0,
            "has_warning": warning > 0
        }
