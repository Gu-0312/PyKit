import sys
import subprocess
import os
import importlib.util


class EnvChecker:
    def __init__(self):
        self.results = {}

    def check_all(self, python_interpreter=None):
        self.results = {
            "python_version": self._check_python_version(python_interpreter),
            "pyinstaller": self._check_pyinstaller(python_interpreter),
            "virtual_env": self._check_virtual_env(python_interpreter),
            "pip_version": self._check_pip_version(python_interpreter),
            "platform": self._check_platform(),
            "encoding": self._check_encoding(),
            "permissions": self._check_permissions(),
        }
        return self.results

    def _check_python_version(self, python_interpreter=None):
        interpreter = python_interpreter if python_interpreter else sys.executable
        
        if python_interpreter:
            try:
                result = subprocess.run(
                    [interpreter, "--version"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    env=self._get_clean_env()
                )
                if result.returncode == 0:
                    version_str = result.stdout.strip().replace("Python ", "")
                    parts = version_str.split(".")
                    is_compatible = len(parts) >= 2 and int(parts[0]) >= 3 and int(parts[1]) >= 8
                    return {
                        "name": "Python 版本",
                        "value": version_str,
                        "status": "success" if is_compatible else "warning",
                        "message": "版本兼容" if is_compatible else "建议使用 Python 3.8+",
                        "details": f"Python {version_str} ({interpreter})"
                    }
            except Exception:
                pass
        
        version = sys.version_info
        version_str = f"{version.major}.{version.minor}.{version.micro}"
        is_compatible = version.major >= 3 and version.minor >= 8
        return {
            "name": "Python 版本",
            "value": version_str,
            "status": "success" if is_compatible else "warning",
            "message": "版本兼容" if is_compatible else "建议使用 Python 3.8+",
            "details": f"Python {version_str} ({interpreter})"
        }

    def _check_pyinstaller(self, python_interpreter=None):
        interpreter = python_interpreter if python_interpreter else sys.executable

        python_dir = os.path.dirname(interpreter)
        scripts_dir = os.path.join(python_dir, "Scripts")
        pyinstaller_exe = os.path.join(scripts_dir, "pyinstaller.exe")

        python_dir_default = os.path.dirname(sys.executable)
        scripts_dir_default = os.path.join(python_dir_default, "Scripts")
        pyinstaller_exe_default = os.path.join(scripts_dir_default, "pyinstaller.exe")

        # 方法1：直接 import 检测（最可靠，不受 subprocess 环境影响）
        try:
            import PyInstaller
            version = getattr(PyInstaller, "__version__", "unknown")
            return {
                "name": "PyInstaller",
                "value": version,
                "status": "success",
                "message": "已安装",
                "details": f"直接import检测 | PyInstaller {version}"
            }
        except ImportError:
            pass

        # 方法2：通过 importlib 查找模块位置
        try:
            spec = importlib.util.find_spec("PyInstaller")
            if spec is not None and spec.origin:
                return {
                    "name": "PyInstaller",
                    "value": "已安装",
                    "status": "success",
                    "message": "已安装",
                    "details": f"模块位置: {os.path.dirname(spec.origin)}"
                }
        except Exception:
            pass

        # 方法3：通过 subprocess 检测各种命令
        commands = [
            [interpreter, "-m", "PyInstaller"],
            [sys.executable, "-m", "PyInstaller"],
            ["pyinstaller"],
            [interpreter, "-m", "pyinstaller"],
            [sys.executable, "-m", "pyinstaller"],
            [pyinstaller_exe],
            [pyinstaller_exe_default],
        ]

        for cmd in commands:
            try:
                full_cmd = cmd + ["--version"]
                result = subprocess.run(
                    full_cmd, capture_output=True, text=True, timeout=10
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

        # 方法4：用 shell=True（处理某些 Windows 环境下 PATH 查找问题）
        try:
            result = subprocess.run(
                "pyinstaller --version",
                capture_output=True, text=True, timeout=10, shell=True
            )
            if result.returncode == 0:
                version = result.stdout.strip()
                return {
                    "name": "PyInstaller",
                    "value": version,
                    "status": "success",
                    "message": "已安装",
                    "details": f"命令: pyinstaller --version (shell=True) | PyInstaller {version}"
                }
        except Exception:
            pass

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

    def _check_virtual_env(self, python_interpreter=None):
        interpreter = python_interpreter if python_interpreter else sys.executable
        result = {
            "name": "虚拟环境",
            "value": "否",
            "status": "info",
            "message": "使用全局 Python 环境",
            "details": ""
        }
        
        if python_interpreter:
            try:
                result_code = subprocess.run(
                    [interpreter, "-c", "import sys; print('venv' if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.prefix != sys.base_prefix) else 'global')"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    env=self._get_clean_env()
                )
                if result_code.returncode == 0:
                    output = result_code.stdout.strip()
                    if output == "venv":
                        prefix_result = subprocess.run(
                            [interpreter, "-c", "import sys; print(sys.prefix)"],
                            capture_output=True,
                            text=True,
                            timeout=5,
                            env=self._get_clean_env()
                        )
                        prefix = prefix_result.stdout.strip() if prefix_result.returncode == 0 else interpreter
                        return {
                            "name": "虚拟环境",
                            "value": "是",
                            "status": "success",
                            "message": f"当前虚拟环境: {prefix}",
                            "details": f"解释器: {interpreter}"
                        }
            except Exception:
                pass
        else:
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

    def _check_pip_version(self, python_interpreter=None):
        interpreter = python_interpreter if python_interpreter else sys.executable
        
        if getattr(sys, 'frozen', False) and not python_interpreter:
            return {
                "name": "pip",
                "value": "不可用",
                "status": "info",
                "message": "打包环境下不支持 pip 检测",
                "details": "当前为 PyInstaller 打包环境，请指定 Python 解释器路径"
            }
            
        try:
            result = subprocess.run(
                [interpreter, "-m", "pip", "--version"],
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
                "details": f"无法找到 Python 解释器: {interpreter}"
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
