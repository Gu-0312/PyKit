import os
import sys
import subprocess
import tempfile
from utils.log_utils import get_logger
from utils.file_utils import ensure_dir_exists, get_file_name_without_ext, get_file_name, popen_hidden, run_hidden
from utils.error_parser import ErrorParser
from core.dependency import DependencyAnalyzer
from core.cache_cleaner import CacheCleaner
from core.inno_setup import InnoSetup
from core.upx_compressor import UPXCompressor
from _version import get_version
from PySide6.QtCore import QObject, Signal


logger = get_logger()


class Packer(QObject):
    log_signal = Signal(str)
    progress_signal = Signal(int, str)
    finished_signal = Signal(bool, dict, int)
    DEFAULT_EXCLUDES = [
        "test", "tests", "unittest", "pytest",
        "numpy.testing", "matplotlib.tests", "scipy.testing",
        "doc", "docs", "example", "examples", "demo", "samples",
        "__pycache__", ".git", ".svn", ".hg", ".tox", ".eggs", "egg-info",
    ]
    
    LARGE_LIBRARIES = [
        "numpy", "scipy", "pandas", "matplotlib",
        "torch", "tensorflow", "keras",
        "PyQt5", "PyQt6", "PySide2", "PySide6",
        "wx", "wxpython",
        "django", "flask", "fastapi",
        "beautifulsoup4", "bs4", "lxml",
        "sqlalchemy", "jinja2",
        "requests", "urllib3",
        "scikit-learn", "sklearn", "scikit-image",
        "networkx", "sympy", "statsmodels",
        "opencv-python", "cv2",
        "pytorch-lightning", "lightning",
        "pydantic", "pydantic-settings",
        "aiohttp", "asyncio",
        "pywin32", "win32api", "win32con", "win32gui",
        "pycairo", "cairocffi",
        "pyarrow", "feather",
        "xlrd", "xlwt", "openpyxl", "xlsxwriter",
        "pymongo", "redis", "psycopg2",
        "mysql-connector-python", "mysql",
        "boto3", "botocore",
        "google-cloud-storage", "google-cloud",
        "azure-storage-blob", "azure",
        "PIL", "Pillow",
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.dependency_analyzer = DependencyAnalyzer()
        self.cache_cleaner = CacheCleaner()
        self.inno_setup = InnoSetup()
        self.upx_compressor = UPXCompressor()
        self.on_log = None
        self.on_progress = None

    def _find_pyinstaller_command(self, source_dir=None, python_interpreter=None):
        commands_by_interpreter = []

        if python_interpreter and os.path.exists(python_interpreter):
            python_dir = os.path.dirname(python_interpreter)
            scripts_dir = os.path.join(python_dir, "Scripts")
            pyinstaller_exe = os.path.join(scripts_dir, "pyinstaller.exe")
            commands_by_interpreter = [
                [python_interpreter, "-m", "PyInstaller"],
                [pyinstaller_exe],
            ]
            self._log(f"[pack] 使用指定的Python解释器: {python_interpreter}")
        else:
            python_dir = os.path.dirname(sys.executable)
            scripts_dir = os.path.join(python_dir, "Scripts")
            pyinstaller_exe = os.path.join(scripts_dir, "pyinstaller.exe")

        python_dir_default = os.path.dirname(sys.executable)
        scripts_dir_default = os.path.join(python_dir_default, "Scripts")
        pyinstaller_exe_default = os.path.join(scripts_dir_default, "pyinstaller.exe")

        commands = [
            [sys.executable, "-m", "PyInstaller"],
            [sys.executable, "-m", "pyinstaller"],
        ] + list(commands_by_interpreter) + [
            ["pyinstaller"],
            ["python", "-m", "PyInstaller"],
            ["python3", "-m", "PyInstaller"],
            [pyinstaller_exe],
            [pyinstaller_exe_default],
        ]

        cwd = source_dir if source_dir else os.path.dirname(sys.executable)

        logger.info(f"[pack] 当前Python路径: {sys.executable}")
        logger.info(f"[pack] 当前Python版本: {sys.version}")
        logger.info(f"[pack] 搜索PyInstaller目录: {scripts_dir if python_interpreter else scripts_dir_default}")
        logger.info(f"[pack] 工作目录: {cwd}")

        # 尝试用 subprocess.run 直接调用（不使用 use_hidden）
        # 部分环境下 use_hidden=True 会导致命令执行异常
        try:
            direct_cmd = [sys.executable, "-m", "PyInstaller", "--version"]
            direct_result = subprocess.run(
                direct_cmd, capture_output=True, text=True, timeout=10, shell=False
            )
            if direct_result.returncode == 0:
                logger.info(f"[pack] 直接调用成功: {sys.executable} -m PyInstaller")
                return [sys.executable, "-m", "PyInstaller"]
        except Exception as e:
            logger.info(f"[pack] 直接调用失败: {e}")

        seen = set()
        for cmd in commands:
            key = " ".join(cmd)
            if key in seen:
                continue
            seen.add(key)
            try:
                full_cmd = cmd + ["--version"]
                logger.info(f"[pack] 尝试命令: {' '.join(full_cmd)}")

                result = run_hidden(full_cmd, capture_output=True, text=True, timeout=10, use_hidden=True, cwd=cwd)
                logger.info(f"[pack] 返回码: {result.returncode}")
                if result.stdout:
                    logger.info(f"[pack] 标准输出: {result.stdout.strip()}")
                if result.stderr:
                    logger.info(f"[pack] 错误输出: {result.stderr.strip()}")

                if result.returncode == 0:
                    logger.info(f"[pack] 找到PyInstaller命令: {' '.join(cmd)}")
                    logger.info(f"[pack] PyInstaller版本输出: {result.stdout.strip()}")
                    return cmd
            except FileNotFoundError:
                logger.info(f"[pack] 命令不存在: {' '.join(cmd)}")
            except Exception as e:
                logger.info(f"[pack] 命令执行异常: {' '.join(cmd)}, 错误: {type(e).__name__}: {str(e)}")

        # 尝试通过 python 命令（非 sys.executable）找 PyInstaller
        for py_cmd in [["python"], ["python3"], ["py"]]:
            try:
                full_cmd = py_cmd + ["-m", "PyInstaller", "--version"]
                result = subprocess.run(full_cmd, capture_output=True, text=True, timeout=10, shell=False)
                if result.returncode == 0:
                    logger.info(f"[pack] 通过 {py_cmd[0]} -m PyInstaller 找到")
                    return py_cmd + ["-m", "PyInstaller"]
            except Exception:
                continue

        logger.warning("[pack] 未找到可用的PyInstaller命令")
        logger.warning(f"[pack] 请确保已安装PyInstaller: pip install pyinstaller")
        logger.warning(f"[pack] 或手动检查: {pyinstaller_exe_default}")
        logger.warning(f"[pack] 诊断: sys.executable={sys.executable}")
        logger.warning(f"[pack] 诊断: python_interpreter={python_interpreter}")
        logger.warning(f"[pack] 诊断: PATH={os.environ.get('PATH', '')}")
        return None

    def ensure_pyinstaller(self, source_dir=None, python_interpreter=None):
        if self._find_pyinstaller_command(source_dir, python_interpreter):
            return True

        self._log("[pack] 检测到PyInstaller未安装，正在尝试自动安装...")
        try:
            install_cwd = source_dir if source_dir else os.path.dirname(sys.executable)

            # 如果是打包后的EXE，sys.executable 不是 Python 解释器，改用 python 命令
            if getattr(sys, 'frozen', False) and not python_interpreter:
                install_cmds = [
                    ["python", "-m", "pip", "install", "pyinstaller"],
                    ["python3", "-m", "pip", "install", "pyinstaller"],
                    ["py", "-m", "pip", "install", "pyinstaller"],
                ]
            else:
                interpreter = python_interpreter if python_interpreter else sys.executable
                install_cmds = [[interpreter, "-m", "pip", "install", "pyinstaller"]]

            installed = False
            for install_cmd in install_cmds:
                try:
                    result = run_hidden(
                        install_cmd,
                        capture_output=True,
                        timeout=180,
                        cwd=install_cwd
                    )
                    if result.returncode == 0:
                        installed = True
                        break
                except Exception:
                    continue

            if not installed:
                self._log("[pack] PyInstaller自动安装失败，请手动安装：pip install pyinstaller")
                return False

            self._log("[pack] PyInstaller安装成功")
            cmd = self._find_pyinstaller_command(source_dir, None)
            if cmd:
                return True
            else:
                self._log("[pack] [WARN] PyInstaller安装成功但命令不可用，尝试使用默认解释器")
                return True
        except Exception as e:
            self._log(f"[pack] PyInstaller安装异常: {str(e)}")
            return False

    def detect_venv(self, source_file):
        if not source_file or not os.path.exists(source_file):
            return None

        source_dir = os.path.dirname(source_file)
        
        venv_dirs = ["venv", ".venv", "env", ".env", "python_env", ".python_env"]
        
        current_dir = source_dir
        while current_dir and current_dir != os.path.dirname(current_dir):
            for venv_name in venv_dirs:
                venv_path = os.path.join(current_dir, venv_name)
                if os.path.isdir(venv_path):
                    python_exe = os.path.join(venv_path, "Scripts", "python.exe")
                    if os.path.exists(python_exe):
                        self._log(f"[pack] 自动检测到虚拟环境: {python_exe}")
                        return python_exe
                    
                    python_exe = os.path.join(venv_path, "bin", "python.exe")
                    if os.path.exists(python_exe):
                        self._log(f"[pack] 自动检测到虚拟环境: {python_exe}")
                        return python_exe
            
            current_dir = os.path.dirname(current_dir)
        
        return None

    def set_progress_callback(self, callback):
        self.on_progress = callback
        if callback:
            self.progress_signal.connect(callback)

    def set_log_callback(self, callback):
        self.on_log = callback
        logger.set_gui_callback(callback)
        if callback:
            self.log_signal.connect(callback)

    def _log(self, message):
        logger.info(message)
        self.log_signal.emit(message)

    def _progress(self, percent, message):
        self.progress_signal.emit(percent, message)

    def _cleanup_redundant_files(self, source_dir, output_dir):
        try:
            build_dir = os.path.join(source_dir, "build")
            if os.path.exists(build_dir):
                import shutil
                shutil.rmtree(build_dir)
                self._log(f"[pack] 已删除build目录: {build_dir}")

            import shutil
            for root, dirs, files in os.walk(source_dir):
                for dir_name in dirs[:]:
                    if dir_name == "__pycache__":
                        cache_path = os.path.join(root, dir_name)
                        try:
                            shutil.rmtree(cache_path)
                            self._log(f"[pack] 已删除__pycache__: {cache_path}")
                        except Exception as e:
                            self._log(f"[pack] [WARN] 无法删除__pycache__: {e}")

            if output_dir:
                for root, dirs, files in os.walk(output_dir):
                    for dir_name in dirs[:]:
                        if dir_name == "__pycache__":
                            cache_path = os.path.join(root, dir_name)
                            try:
                                shutil.rmtree(cache_path)
                                self._log(f"[pack] 已删除输出目录__pycache__: {cache_path}")
                            except Exception as e:
                                self._log(f"[pack] [WARN] 无法删除__pycache__: {e}")

            self._log("[pack] 冗余文件清理完成")
        except Exception as e:
            self._log(f"[pack] [WARN] 清理冗余文件时出错: {e}")

    def _create_inno_installer(self, config, exe_path, output_dir, output_name, app_version, app_icon):
        self._log("[pack] 使用 Inno Setup 生成安装包")
        if not self.inno_setup.is_installed():
            self._log("[pack] [ERROR] 未找到Inno Setup编译器(ISCC)")
            self._log("[pack] [ERROR] 请先安装Inno Setup后再启用生成安装包功能")
            self._log("[pack] [ERROR] Inno Setup下载地址: https://jrsoftware.org/isdl.php")
            return

        self.inno_setup.set_log_callback(self.on_log)
        self.inno_setup.set_progress_callback(self.on_progress)
        success = self.inno_setup.create_installer(
            exe_path=exe_path,
            output_dir=output_dir,
            app_name=output_name,
            app_version=app_version,
            app_icon=app_icon
        )
        if success:
            self._cleanup_green_files(config, output_dir, output_name, app_version)

    def _cleanup_green_files(self, config, output_dir, output_name, app_version):
        setup_file = os.path.join(output_dir, f"{output_name}-{app_version}-setup.exe")
        if os.path.exists(setup_file):
            file_size = os.path.getsize(setup_file)
            self._log(f"[pack] 安装包已生成: {setup_file}")
            self._log(f"[pack] 安装包大小: {file_size / (1024 * 1024):.2f} MB")
            self._log("[pack] 安装包生成成功，开始清理绿色版文件")
            if config.get("single_file", False):
                green_exe = os.path.join(output_dir, f"{output_name}.exe")
                if os.path.exists(green_exe):
                    try:
                        os.remove(green_exe)
                        self._log(f"[pack] 已删除绿色版EXE: {green_exe}")
                    except Exception as e:
                        self._log(f"[pack] [WARN] 无法删除绿色版EXE: {e}")
            else:
                green_dir = os.path.join(output_dir, output_name)
                if os.path.exists(green_dir):
                    try:
                        import shutil
                        shutil.rmtree(green_dir)
                        self._log(f"[pack] 已删除绿色版文件夹: {green_dir}")
                    except Exception as e:
                        self._log(f"[pack] [WARN] 无法删除绿色版文件夹: {e}")
            self._log("[pack] 安装包生成成功")
        else:
            self._log(f"[pack] [WARN] 安装包文件不存在: {setup_file}")
            self._log("[pack] [WARN] 跳过绿色版文件清理")

    def _detect_qt_bindings(self, python_interpreter=None):
        qt_packages = ["PyQt5", "PyQt6", "PySide2", "PySide6"]
        installed = []
        
        if python_interpreter and os.path.exists(python_interpreter):
            try:
                import subprocess
                result = subprocess.run(
                    [python_interpreter, "-c", 
                     "import importlib.util; pkgs=['PyQt5','PyQt6','PySide2','PySide6']; print(';'.join([p for p in pkgs if importlib.util.find_spec(p) is not None]))"],
                    capture_output=True, text=True, timeout=10
                )
                if result.returncode == 0:
                    modules = result.stdout.strip().split(';')
                    for module in modules:
                        if module and module in qt_packages:
                            installed.append(module)
            except Exception:
                pass
        
        if not installed:
            for pkg in qt_packages:
                try:
                    __import__(pkg)
                    installed.append(pkg)
                except ImportError:
                    pass
        
        return installed

    def _detect_used_qt_binding(self, source_file, hidden_imports):
        qt_bindings = {"PyQt5", "PyQt6", "PySide2", "PySide6"}
        for imp in hidden_imports:
            base = imp.split(".")[0]
            if base in qt_bindings:
                return base
        if source_file and os.path.exists(source_file):
            imports = self._scan_source_imports(source_file)
            for imp in imports:
                if imp in qt_bindings:
                    return imp
            
            project_imports = self._scan_project_imports(source_file)
            for imp in project_imports:
                base = imp.split(".")[0]
                if base in qt_bindings:
                    return base
        return None

    def _scan_source_imports(self, source_file):
        if not source_file or not os.path.exists(source_file):
            return set()
        
        imports = set()
        try:
            with open(source_file, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            
            # 尝试使用AST解析（更准确）
            try:
                import ast
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            # 保留完整的导入名称，如 PIL.Image
                            imports.add(alias.name)
                            base = alias.name.split(".")[0]
                            imports.add(base)
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            # 保留完整的导入名称，如 PIL.Image
                            imports.add(node.module)
                            base = node.module.split(".")[0]
                            imports.add(base)
                return imports
            except SyntaxError:
                pass
            
            # 如果AST解析失败，使用简单的文本解析
            for line in content.splitlines():
                line = line.strip()
                if line.startswith("import "):
                    mod = line.split()[1]
                    imports.add(mod)
                    base = mod.split(".")[0]
                    imports.add(base)
                elif line.startswith("from "):
                    mod = line.split()[1]
                    imports.add(mod)
                    base = mod.split(".")[0]
                    imports.add(base)
            return imports
        except Exception:
            return set()

    def _scan_project_imports(self, source_file):
        """扫描整个项目目录中的所有Python文件，检测导入的模块"""
        if not source_file or not os.path.exists(source_file):
            return set()
        
        all_imports = set()
        source_dir = os.path.dirname(source_file)
        
        try:
            import ast
            for root, dirs, files in os.walk(source_dir):
                dirs[:] = [d for d in dirs if d not in ("__pycache__", ".git", ".svn", "venv", ".venv")]
                for filename in files:
                    if filename.endswith(".py"):
                        filepath = os.path.join(root, filename)
                        try:
                            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                                content = f.read()
                            
                            # 尝试使用AST解析（更准确）
                            try:
                                tree = ast.parse(content)
                                for node in ast.walk(tree):
                                    if isinstance(node, ast.Import):
                                        for alias in node.names:
                                            # 保留完整的导入名称，如 PIL.Image
                                            all_imports.add(alias.name)
                                            base = alias.name.split(".")[0]
                                            all_imports.add(base)
                                    elif isinstance(node, ast.ImportFrom):
                                        if node.module:
                                            # 保留完整的导入名称，如 PIL.Image
                                            all_imports.add(node.module)
                                            base = node.module.split(".")[0]
                                            all_imports.add(base)
                                continue
                            except SyntaxError:
                                pass
                            
                            # 如果AST解析失败，使用简单的文本解析
                            for line in content.splitlines():
                                line = line.strip()
                                if line.startswith("import "):
                                    mod = line.split()[1]
                                    all_imports.add(mod)
                                    base = mod.split(".")[0]
                                    all_imports.add(base)
                                elif line.startswith("from "):
                                    mod = line.split()[1]
                                    all_imports.add(mod)
                                    base = mod.split(".")[0]
                                    all_imports.add(base)
                        except Exception:
                            continue
        except Exception:
            pass
        
        return all_imports

    def _check_requirements_txt_for_pil(self, source_file):
        """检查requirements.txt中是否包含PIL/Pillow依赖"""
        if not source_file:
            return False
        
        source_dir = os.path.dirname(source_file)
        requirements_files = [
            os.path.join(source_dir, "requirements.txt"),
            os.path.join(source_dir, "req.txt"),
            os.path.join(source_dir, "dependencies.txt"),
        ]
        
        for req_file in requirements_files:
            if os.path.exists(req_file):
                try:
                    with open(req_file, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read().lower()
                        if "pillow" in content or "pil" in content:
                            self._log(f"[PIL] 在 {req_file} 中检测到 PIL/Pillow 依赖")
                            return True
                except Exception:
                    continue
        
        return False

    def _add_pil_deps(self, cmd, hidden_imports, source_file, python_interpreter=None):
        needs_pil = False
        
        # 检查是否已经在隐藏导入列表中
        if "PIL" in hidden_imports or any(imp.startswith("PIL.") for imp in hidden_imports):
            needs_pil = True
            self._log("[PIL] 从隐藏导入列表中检测到 PIL")
        elif source_file and os.path.exists(source_file):
            # 扫描源文件中的导入
            imports = self._scan_source_imports(source_file)
            if "PIL" in imports or any(imp.startswith("PIL.") for imp in imports):
                needs_pil = True
                self._log(f"[PIL] 从源文件中检测到 PIL 导入: {[imp for imp in imports if 'PIL' in imp.upper()]}")
            else:
                # 扫描项目目录中的导入
                project_imports = self._scan_project_imports(source_file)
                if "PIL" in project_imports or any(imp.startswith("PIL.") for imp in project_imports):
                    needs_pil = True
                    self._log(f"[PIL] 从项目目录中检测到 PIL 导入: {[imp for imp in project_imports if 'PIL' in imp.upper()]}")
                # 检查 requirements.txt
                elif self._check_requirements_txt_for_pil(source_file):
                    needs_pil = True
                    self._log("[PIL] 从 requirements.txt 中检测到 PIL 依赖")
        
        if not needs_pil:
            env_has_pil = False
            if python_interpreter:
                try:
                    result = run_hidden(
                        [python_interpreter, "-c", "import PIL; print('PIL installed')"],
                        capture_output=True, text=True, timeout=10
                    )
                    if result.returncode == 0:
                        env_has_pil = True
                        self._log("[PIL] 用户环境中安装了 PIL")
                except Exception:
                    pass
            
            if not env_has_pil:
                try:
                    import PIL
                    env_has_pil = True
                    self._log("[PIL] 打包工具环境中安装了 PIL")
                except ImportError:
                    pass
            
            if env_has_pil:
                needs_pil = True
                self._log("[PIL] 当前环境安装了 PIL，默认添加依赖")
            else:
                self._log("[PIL] 当前环境未安装 PIL，跳过")
                return
        
        if "PIL" not in hidden_imports:
            hidden_imports.append("PIL")

        has_collect_all_pil = False
        for i in range(len(cmd) - 1):
            if cmd[i] == "--collect-all" and cmd[i+1] == "PIL":
                has_collect_all_pil = True
                break
        
        if not has_collect_all_pil:
            cmd.append("--collect-all")
            cmd.append("PIL")
            self._log("[PIL] 添加 --collect-all PIL")

        added_count = 0
        
        # 完整的PIL子模块列表，确保所有常用子模块都被包含
        all_pil_submodules = [
            "PIL.Image", "PIL.ImageDraw", "PIL.ImageFont", "PIL.ImageFilter",
            "PIL.ImageEnhance", "PIL.ImageOps", "PIL.ImageChops", "PIL.ImageColor",
            "PIL.ImageFile", "PIL.ImageMode", "PIL.ImagePalette", "PIL.ImagePath",
            "PIL.ImageSequence", "PIL.ImageStat", "PIL.ImageTk", "PIL.ImageWin",
            "PIL.ImageGrab", "PIL.ImageMorph", "PIL.ImagePoint", "PIL.ImageTransform",
            "PIL.TiffImagePlugin", "PIL.TiffTags", "PIL.PngImagePlugin",
            "PIL.JpegImagePlugin", "PIL.GifImagePlugin", "PIL.BmpImagePlugin",
            "PIL.WmfImagePlugin", "PIL.TgaImagePlugin", "PIL.PpmImagePlugin",
            "PIL.SgiImagePlugin", "PIL.FliImagePlugin", "PIL.PcdImagePlugin",
            "PIL.PixImagePlugin", "PIL.XbmImagePlugin", "PIL.XpmImagePlugin",
            "PIL.XvImagePlugin", "PIL.EpsImagePlugin", "PIL.IcnsImagePlugin",
            "PIL.ImImagePlugin", "PIL.MspImagePlugin", "PIL.PcxImagePlugin",
            "PIL.PsdImagePlugin", "PIL.SunImagePlugin", "PIL.FitsImagePlugin",
            "PIL.Hdf5StubImagePlugin", "PIL.MicImagePlugin", "PIL.MpegImagePlugin",
            "PIL.MpoImagePlugin", "PIL.PalmImagePlugin", "PIL.PdfImagePlugin",
            "PIL.SpiderImagePlugin", "PIL.TgaImagePlugin", "PIL.WebPImagePlugin",
            "PIL.WmfImagePlugin", "PIL.XcursorImagePlugin", "PIL.XpmImagePlugin",
            "PIL.BlpImagePlugin", "PIL.CurImagePlugin", "PIL.DcxImagePlugin",
            "PIL.IcoImagePlugin", "PIL.Jpeg2KImagePlugin", "PIL.LibImagePlugin",
        ]
        
        try:
            import PIL
            pil_dir = os.path.dirname(PIL.__file__)
            prefix = "PIL."
            
            # 扫描PIL目录中的所有.py文件
            for f in os.listdir(pil_dir):
                if f == "__init__.py":
                    continue
                if f.endswith(".py"):
                    mod_name = prefix + f[:-3]
                    if mod_name not in hidden_imports:
                        hidden_imports.append(mod_name)
                        added_count += 1
            
            # 也检查子目录中的模块
            for item in os.listdir(pil_dir):
                item_path = os.path.join(pil_dir, item)
                if os.path.isdir(item_path) and not item.startswith("_"):
                    init_file = os.path.join(item_path, "__init__.py")
                    if os.path.exists(init_file):
                        submod_name = prefix + item
                        if submod_name not in hidden_imports:
                            hidden_imports.append(submod_name)
                            added_count += 1
        except Exception:
            # 如果无法导入PIL，使用预定义的完整列表
            for mod in all_pil_submodules:
                if mod not in hidden_imports:
                    hidden_imports.append(mod)
                    added_count += 1

        self._log(f"[PIL] 添加了 {added_count} 个 PIL 子模块")

    def _add_pywin32_deps(self, cmd, source_file=""):
        needs_pywin32 = False
        if source_file and os.path.exists(source_file):
            try:
                imports = self._scan_source_imports(source_file)
                needs_pywin32 = any(imp in ("pywin32", "win32api", "win32gui", "win32con",
                                             "win32com", "pythoncom", "pywintypes") or
                                    imp.startswith("win32") or imp.startswith("pythoncom")
                                    for imp in imports)
            except Exception:
                pass

        if not needs_pywin32:
            return

        try:
            import site
            for site_dir in site.getsitepackages():
                pywin32_system32 = os.path.join(site_dir, "pywin32_system32")
                if os.path.isdir(pywin32_system32):
                    cmd.extend(["--paths", pywin32_system32])
                    self._log(f"[pywin32] 添加 pywin32_system32 路径: {pywin32_system32}")
                    break

            import pywintypes
            pywin32_dir = os.path.dirname(pywintypes.__file__)
            if pywin32_dir not in " ".join(cmd):
                cmd.extend(["--paths", pywin32_dir])
                self._log(f"[pywin32] 添加 pywin32 路径: {pywin32_dir}")
        except ImportError:
            pass
        except Exception as e:
            self._log(f"[pywin32] 添加路径时出错: {e}")

    def _add_large_lib_deps(self, cmd, hidden_imports, source_file, python_interpreter=None):
        if not source_file or not os.path.exists(source_file):
            return

        all_imports = set()
        imports = self._scan_source_imports(source_file)
        all_imports.update(imports)
        
        project_imports = self._scan_project_imports(source_file)
        all_imports.update(project_imports)
        
        all_imports.update(hidden_imports)

        for lib in self.LARGE_LIBRARIES:
            has_lib = False
            for imp in all_imports:
                if imp == lib or imp.startswith(lib + "."):
                    has_lib = True
                    break
            
            if has_lib:
                has_collect_all = False
                for i in range(len(cmd) - 1):
                    if cmd[i] == "--collect-all" and cmd[i+1] == lib:
                        has_collect_all = True
                        break
                
                if not has_collect_all:
                    env_has_lib = False
                    if python_interpreter:
                        try:
                            result = run_hidden(
                                [python_interpreter, "-c", f"import {lib}; print('{lib} installed')"],
                                capture_output=True, text=True, timeout=5
                            )
                            if result.returncode == 0:
                                env_has_lib = True
                        except Exception:
                            pass
                    
                    if not env_has_lib:
                        try:
                            __import__(lib)
                            env_has_lib = True
                        except ImportError:
                            pass
                    
                    if env_has_lib:
                        cmd.append("--collect-all")
                        cmd.append(lib)
                        self._log(f"[{lib}] 添加 --collect-all {lib}")

    def _add_tkinter_deps(self, cmd, hidden_imports, source_file=""):
        imports = self._scan_source_imports(source_file)
        needs_tk = "tkinter" in imports or "Tkinter" in imports or "tkinter" in [i for i in hidden_imports]
        if not needs_tk and source_file:
            return

        try:
            import _tkinter
            tk_root = os.path.dirname(_tkinter.__file__)
        except (ImportError, AttributeError):
            self._log("[tkinter] _tkinter 未安装，跳过")
            return

        hidden_imports.extend(["_tkinter", "tkinter"])
        self._log("[tkinter] 添加 _tkinter/tkinter 隐藏导入")

        tcl_dir = os.environ.get("TCL_LIBRARY", "")
        tk_dir = os.environ.get("TK_LIBRARY", "")

        if not tcl_dir:
            tcl_versions = ["8.6", "8.5", "8.4"]
            prefixes = [sys.exec_prefix, sys.prefix, os.path.dirname(sys.executable)]
            for p in prefixes:
                for v in tcl_versions:
                    for base in ["tcl", os.path.join("lib", "tcl")]:
                        candidate = os.path.abspath(os.path.join(p, base, f"tcl{v}"))
                        if os.path.isdir(candidate) and os.path.isfile(os.path.join(candidate, "init.tcl")):
                            tcl_dir = candidate
                            self._log(f"[tkinter] 自动检测 Tcl 目录: {tcl_dir}")
                            break
                    if tcl_dir:
                        break
                if tcl_dir:
                    break

        if not tk_dir:
            for p in prefixes:
                for v in tcl_versions:
                    for base in ["tcl", os.path.join("lib", "tcl")]:
                        candidate = os.path.abspath(os.path.join(p, base, f"tk{v}"))
                        if os.path.isdir(candidate) and os.path.isfile(os.path.join(candidate, "ttk", "ttk.tcl")):
                            tk_dir = candidate
                            self._log(f"[tkinter] 自动检测 Tk 目录: {tk_dir}")
                            break
                    if tk_dir:
                        break
                if tk_dir:
                    break

        if tcl_dir:
            cmd.extend(["--add-data", f"{tcl_dir};tcl"])
            self._log(f"[tkinter] 添加 Tcl 数据目录: {tcl_dir} -> tcl")
        else:
            self._log("[tkinter] [WARN] 未找到 Tcl 目录，打包后 tkinter 可能无法运行")

        if tk_dir:
            cmd.extend(["--add-data", f"{tk_dir};tk"])
            self._log(f"[tkinter] 添加 Tk 数据目录: {tk_dir} -> tk")
        else:
            self._log("[tkinter] [WARN] 未找到 Tk 目录，打包后 tkinter 可能无法运行")

        dll_dir = tk_root if tk_root else None
        if dll_dir and os.path.isdir(dll_dir):
            tcl_dlls = [f for f in os.listdir(dll_dir) if f.lower().startswith("tcl") and f.lower().endswith(".dll")]
            tk_dlls = [f for f in os.listdir(dll_dir) if f.lower().startswith("tk") and f.lower().endswith(".dll")]
            for dll in tcl_dlls + tk_dlls:
                dll_path = os.path.join(dll_dir, dll)
                cmd.extend(["--add-binary", f"{dll_path};."])
                self._log(f"[tkinter] 添加 Tcl/Tk DLL: {dll}")
        elif tk_root and os.path.isdir(tk_root):
            dll_dir = tk_root
            tcl_dlls = [f for f in os.listdir(dll_dir) if f.lower().startswith("tcl") and f.lower().endswith(".dll")]
            tk_dlls = [f for f in os.listdir(dll_dir) if f.lower().startswith("tk") and f.lower().endswith(".dll")]
            for dll in tcl_dlls + tk_dlls:
                dll_path = os.path.join(dll_dir, dll)
                cmd.extend(["--add-binary", f"{dll_path};."])
                self._log(f"[tkinter] 添加 Tcl/Tk DLL: {dll}")

    def analyze_project_dependencies(self, source_file):
        """全面分析项目依赖，帮助诊断打包后运行时错误"""
        if not source_file or not os.path.exists(source_file):
            return {"error": "源文件不存在"}
        
        result = {
            "project_imports": [],
            "missing_modules": [],
            "installed_modules": [],
            "suggested_hidden_imports": [],
            "common_issues": [],
            "analysis_log": []
        }
        
        self._log("[诊断] 开始分析项目依赖...")
        
        # 扫描项目所有文件的导入
        project_imports = self._scan_project_imports(source_file)
        result["project_imports"] = sorted(list(project_imports))
        self._log(f"[诊断] 检测到项目使用 {len(project_imports)} 个模块")
        
        # 检查每个模块是否安装
        for module in sorted(project_imports):
            try:
                __import__(module)
                result["installed_modules"].append(module)
            except ImportError:
                result["missing_modules"].append(module)
        
        if result["missing_modules"]:
            self._log(f"[诊断] [WARN] 以下模块未安装: {result['missing_modules']}")
            result["common_issues"].append(f"未安装的模块: {', '.join(result['missing_modules'])}")
        
        # 常用依赖的隐藏导入建议
        hidden_imports_map = {
            "PIL": ["PIL", "PIL.Image", "PIL.ImageDraw", "PIL.ImageFont", "--collect-all PIL"],
            "tkinter": ["tkinter", "_tkinter", "--collect-data tkinter"],
            "PyQt5": ["PyQt5", "PyQt5.QtCore", "PyQt5.QtGui", "PyQt5.QtWidgets", "--collect-all PyQt5"],
            "PyQt6": ["PyQt6", "PyQt6.QtCore", "PyQt6.QtGui", "PyQt6.QtWidgets", "--collect-all PyQt6"],
            "PySide2": ["PySide2", "PySide2.QtCore", "PySide2.QtGui", "PySide2.QtWidgets", "--collect-all PySide2"],
            "PySide6": ["PySide6", "PySide6.QtCore", "PySide6.QtGui", "PySide6.QtWidgets", "--collect-all PySide6"],
            "matplotlib": ["matplotlib", "matplotlib.pyplot", "matplotlib.backends", "--collect-all matplotlib"],
            "numpy": ["numpy", "--collect-all numpy"],
            "pandas": ["pandas", "--collect-all pandas"],
            "scipy": ["scipy", "--collect-all scipy"],
            "requests": ["requests", "--collect-all requests"],
            "beautifulsoup4": ["bs4", "beautifulsoup4"],
            "lxml": ["lxml", "--collect-all lxml"],
            "sqlite3": ["sqlite3"],
            "pywin32": ["win32com", "win32api", "win32ui", "pythoncom"],
            "pyttsx3": ["pyttsx3", "pyttsx3.drivers.sapi5"],
            "openpyxl": ["openpyxl", "--collect-all openpyxl"],
            "xlrd": ["xlrd", "--collect-all xlrd"],
            "xlwt": ["xlwt", "--collect-all xlwt"],
            "docx": ["docx", "--collect-all python-docx"],
            "psutil": ["psutil"],
            "threading": [],
            "multiprocessing": ["multiprocessing"],
            "subprocess": [],
            "json": [],
            "os": [],
            "sys": [],
            "re": [],
            "datetime": [],
            "time": [],
            "collections": [],
            "pathlib": [],
            "shutil": [],
            "tempfile": [],
            "hashlib": [],
            "base64": [],
            "urllib": ["urllib", "urllib.request", "urllib.parse"],
            "http": ["http", "http.client"],
            "socket": [],
            "ctypes": [],
            "pickle": [],
            "configparser": [],
            "logging": [],
            "traceback": [],
            "warnings": [],
            "functools": [],
            "itertools": [],
            "operator": [],
            "math": [],
            "random": [],
            "statistics": [],
            "decimal": [],
            "fractions": [],
            "string": [],
            "textwrap": [],
            "csv": [],
            "io": [],
            "codecs": [],
            "encodings": [],
            "locale": [],
            "calendar": [],
            "datetime": [],
            "zoneinfo": [],
            "argparse": [],
            "getopt": [],
            "cmd": [],
            "shlex": [],
            "platform": [],
            "sysconfig": [],
            "site": [],
            "types": [],
            "typing": [],
            "dataclasses": [],
            "enum": [],
            "abc": [],
            "contextlib": [],
            "contextvars": [],
            "asyncio": [],
            "concurrent": ["concurrent", "concurrent.futures"],
            "queue": [],
            "select": [],
            "signal": [],
            "mmap": [],
            "array": [],
            "bisect": [],
            "heapq": [],
            "numbers": [],
            "copy": [],
            "weakref": [],
            "gc": [],
            "inspect": [],
            "dis": [],
            "reprlib": [],
            "pprint": [],
            "graphlib": [],
            "difflib": [],
            "hashlib": [],
            "hmac": [],
            "secrets": [],
            "os": [],
            "io": [],
            "time": [],
            "datetime": [],
            "calendar": [],
            "zoneinfo": [],
            "statistics": [],
            "math": [],
            "cmath": [],
            "decimal": [],
            "fractions": [],
            "random": [],
            "statistics": [],
            "itertools": [],
            "functools": [],
            "operator": [],
            "collections": [],
            "collections.abc": [],
            "heapq": [],
            "bisect": [],
            "array": [],
            "weakref": [],
            "types": [],
            "enum": [],
            "typing": [],
            "dataclasses": [],
            "abc": [],
            "contextlib": [],
            "contextvars": [],
            "asyncio": [],
            "concurrent": [],
            "threading": [],
            "multiprocessing": [],
            "subprocess": [],
            "signal": [],
            "traceback": [],
            "logging": [],
            "warnings": [],
            "errno": [],
            "ctypes": [],
            "pathlib": [],
            "os": [],
            "shutil": [],
            "glob": [],
            "fnmatch": [],
            "linecache": [],
            "fileinput": [],
            "stat": [],
            "filecmp": [],
            "tempfile": [],
            "io": [],
            "textwrap": [],
            "unicodedata": [],
            "string": [],
            "re": [],
            "difflib": [],
            "pprint": [],
            "reprlib": [],
            "enum": [],
            "types": [],
            "copy": [],
            "weakref": [],
            "gc": [],
            "inspect": [],
            "sys": [],
            "builtins": [],
            "__main__": [],
        }
        
        # 生成建议的隐藏导入
        for module in result["installed_modules"]:
            if module in hidden_imports_map:
                suggestions = hidden_imports_map[module]
                for suggestion in suggestions:
                    if suggestion not in result["suggested_hidden_imports"]:
                        result["suggested_hidden_imports"].append(suggestion)
        
        # 检查常见问题
        if "PIL" in result["project_imports"] and "PIL" not in result["installed_modules"]:
            result["common_issues"].append("PIL/Pillow 未安装，请运行: pip install Pillow")
        
        if "tkinter" in result["project_imports"]:
            try:
                import _tkinter
            except ImportError:
                result["common_issues"].append("tkinter 未正确安装，可能需要安装 python3-tk")
        
        if any(m.startswith("PyQt") or m.startswith("PySide") for m in result["project_imports"]):
            result["common_issues"].append("Qt 绑定需要 --collect-all 参数，请确保使用对应绑定的 --collect-all")
        
        # 检查数据文件问题
        source_dir = os.path.dirname(source_file)
        for root, dirs, files in os.walk(source_dir):
            dirs[:] = [d for d in dirs if d not in ("__pycache__", ".git", ".svn", "venv", ".venv")]
            for filename in files:
                if filename.endswith((".png", ".jpg", ".jpeg", ".gif", ".ico", ".ttf", ".otf", ".json", ".txt", ".csv")):
                    file_rel_path = os.path.relpath(os.path.join(root, filename), source_dir)
                    result["analysis_log"].append(f"[数据文件] 发现资源文件: {file_rel_path}")
        
        self._log("[诊断] 依赖分析完成")
        
        return result

    def build_command(self, config):
        self._log("[build_command] 开始构建PyInstaller命令")

        source_file = config.get("source_file", "")
        source_dir = os.path.dirname(source_file) if source_file else None

        pyinstaller_cmd = self._find_pyinstaller_command(source_dir, config.get("python_interpreter"))
        if pyinstaller_cmd is None:
            raise RuntimeError("未找到可用的PyInstaller命令")

        cmd = list(pyinstaller_cmd)
        self._log(f"[build_command] PyInstaller命令: {' '.join(pyinstaller_cmd)}")

        if config.get("single_file", False):
            cmd.append("--onefile")
            self._log("[build_command] 打包模式: 单文件模式 (--onefile)")
        else:
            cmd.append("--onedir")
            self._log("[build_command] 打包模式: 多文件模式 (--onedir)")
        
        # 添加优化参数提升打包速度
        cmd.append("--noconfirm")
        self._log("[build_command] 添加 --noconfirm 参数，跳过确认提示")

        windowed = config.get("windowed", False)
        
        # 如果源文件是 .pyw 扩展名，自动启用隐藏控制台
        source_file = config.get("source_file", "")
        if source_file.lower().endswith(".pyw"):
            windowed = True
            self._log(f"[build_command] 源文件为 .pyw，自动启用隐藏控制台")
        
        if windowed:
            cmd.append("--noconsole")
            self._log("[build_command] 隐藏控制台窗口 (--noconsole)")
        else:
            self._log("[build_command] 显示控制台窗口")

        icon_path = config.get("icon", "")
        self._log(f"[build_command] 配置中的图标路径: '{icon_path}'")
        
        if icon_path:
            if os.path.exists(icon_path):
                icon_path = os.path.abspath(icon_path)
                cmd.extend(["-i", icon_path])
                self._log(f"[build_command] 使用用户指定的图标: {icon_path}")
            else:
                self._log(f"[build_command] [WARN] 用户指定的图标文件不存在: {icon_path}")
                icon_path = ""
        
        if not icon_path:
            default_icon = os.path.join(os.path.dirname(__file__), "../icon.ico")
            default_icon = os.path.abspath(default_icon)
            if os.path.exists(default_icon):
                icon_path = default_icon
                cmd.extend(["-i", icon_path])
                self._log(f"[build_command] 使用默认图标: {icon_path}")
            else:
                self._log("[build_command] 未指定图标，使用PyInstaller默认图标")

        output_dir = config.get("output_dir", "")
        if output_dir:
            ensure_dir_exists(output_dir)
            cmd.extend(["--distpath", output_dir])
            self._log(f"[build_command] 输出目录: {output_dir}")
        else:
            self._log("[build_command] 输出目录: 默认")

        work_dir = tempfile.mkdtemp(prefix="pyinstaller_")
        cmd.extend(["--workpath", work_dir])
        cmd.extend(["--specpath", work_dir])
        self._log(f"[build_command] 临时工作目录: {work_dir}")
        
        if source_dir:
            cmd.extend(["--paths", source_dir])
            self._log(f"[build_command] 添加项目路径: {source_dir}")

        self._add_pywin32_deps(cmd, source_file)

        if config.get("name"):
            cmd.extend(["-n", config["name"]])
            self._log(f"[build_command] 输出文件名: {config['name']}")
        else:
            self._log("[build_command] 输出文件名: 默认")

        hidden_imports = config.get("hidden_imports", [])
        python_interpreter = config.get("python_interpreter")
        self._add_tkinter_deps(cmd, hidden_imports, source_file)
        self._add_pil_deps(cmd, hidden_imports, source_file, python_interpreter)
        self._add_large_lib_deps(cmd, hidden_imports, source_file, python_interpreter)
        
        needs_pil = "PIL" in hidden_imports or any(imp.startswith("PIL.") for imp in hidden_imports)
        
        for imp in hidden_imports:
            cmd.extend(["--hidden-import", imp])
        self._log(f"[build_command] 隐藏依赖数量: {len(hidden_imports)}")
        if hidden_imports:
            self._log(f"[build_command] 隐藏依赖列表: {hidden_imports}")

        excludes = config.get("excludes", [])
        
        if config.get("auto_exclude", True):
            excludes.extend(self.DEFAULT_EXCLUDES)
            self._log(f"[build_command] 添加 {len(self.DEFAULT_EXCLUDES)} 个默认排除模块")
        
        if needs_pil:
            excludes = [e for e in excludes if e not in ("PIL", "PIL.")]
            self._log("[build_command] 检测到 PIL 依赖，从排除列表中移除 PIL")

        python_interpreter = config.get("python_interpreter")
        qt_bindings = self._detect_qt_bindings(python_interpreter)
        source_file = config.get("source_file", "")
        used_qt = self._detect_used_qt_binding(source_file, hidden_imports)
        
        if used_qt:
            excluded_qt = [qt for qt in qt_bindings if qt != used_qt]
            excludes.extend(excluded_qt)
            self._log(f"[build_command] 检测到使用的Qt绑定: {used_qt}")
            self._log(f"[build_command] 安装的Qt绑定: {qt_bindings}")
            self._log(f"[build_command] 排除其他Qt绑定: {excluded_qt}")
            
            if f"--collect-all {used_qt}" not in " ".join(cmd):
                cmd.extend(["--collect-all", used_qt])
                self._log(f"[build_command] 添加 --collect-all {used_qt} 以确保Qt插件和资源被正确收集")
            
            # PySide6 需要 shiboken6 作为底层绑定
            if used_qt == "PySide6":
                if "--collect-all shiboken6" not in " ".join(cmd):
                    cmd.extend(["--collect-all", "shiboken6"])
                    self._log("[build_command] 添加 --collect-all shiboken6 以确保PySide6底层绑定被正确收集")
        elif qt_bindings:
            self._log(f"[build_command] 未检测到使用Qt绑定，但环境中安装了: {qt_bindings}")
            self._log("[build_command] 为避免误排除，不排除任何Qt绑定")
            for qt in qt_bindings:
                if f"--collect-all {qt}" not in " ".join(cmd):
                    cmd.extend(["--collect-all", qt])
                    self._log(f"[build_command] 添加 --collect-all {qt} 以确保Qt插件和资源被正确收集")
                    if qt == "PySide6":
                        if "--collect-all shiboken6" not in " ".join(cmd):
                            cmd.extend(["--collect-all", "shiboken6"])
                            self._log("[build_command] 添加 --collect-all shiboken6 以确保PySide6底层绑定被正确收集")

        for exc in excludes:
            cmd.extend(["--exclude-module", exc])
        self._log(f"[build_command] 排除模块数量: {len(excludes)}")

        data_files = config.get("data_files", [])
        for data in data_files:
            if isinstance(data, tuple):
                src, dst = data
                cmd.extend(["--add-data", f"{src}{os.pathsep}{dst}"])
                self._log(f"[build_command] 添加数据文件: {src} -> {dst}")
        
        # UPX处理
        if config.get("enable_upx", False):
            upx_path = config.get("upx_path", "") or getattr(self, "_upx_path", "")
            if upx_path and os.path.exists(upx_path):
                cmd.extend(["--upx-dir", upx_path])
                self._log(f"[build_command] 使用UPX压缩: {upx_path}")
            else:
                self._log("[build_command] [WARN] 已启用UPX但未找到upx.exe，跳过UPX")
                config["_upx_enabled"] = False
        else:
            config["_upx_enabled"] = False
            self._log("[build_command] 禁用UPX压缩")

        custom_args = config.get("custom_args", "")
        if custom_args:
            import shlex
            args_list = shlex.split(custom_args)
            cmd.extend(args_list)
            self._log(f"[build_command] 添加自定义参数: {' '.join(args_list)}")

        source_file = config.get("source_file", "")
        if not source_file or not os.path.exists(source_file):
            self._log(f"[build_command] 错误: 源文件不存在: {source_file}")
            raise ValueError("源文件不存在")

        cmd.append(source_file)
        self._log(f"[build_command] 源文件: {source_file}")

        self._log(f"[build_command] 命令构建完成，参数数量: {len(cmd)}")
        return cmd, work_dir

    def run_pyinstaller(self, cmd, stop_event=None):
        self._log("[run_pyinstaller] 开始执行PyInstaller")
        self._log(f"[run_pyinstaller] 完整命令: {' '.join(cmd)}")

        source_file = cmd[-1] if cmd else ""
        cwd = os.path.dirname(source_file) if source_file else os.path.dirname(sys.executable)
        self._log(f"[run_pyinstaller] 工作目录: {cwd}")

        process = None
        try:
            self._log("[run_pyinstaller] 创建子进程...")
            process = popen_hidden(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                bufsize=1,
                cwd=cwd
            )

            self._log("[run_pyinstaller] 子进程创建成功，开始读取输出...")

            full_output = []
            line_count = 0
            error_lines = []

            for line in process.stdout:
                if stop_event and stop_event.is_set():
                    self._log("[run_pyinstaller] 收到取消信号，终止子进程...")
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()
                    self._log("[run_pyinstaller] 子进程已终止")
                    return False

                line = line.strip()
                if line:
                    line_count += 1
                    full_output.append(line)

                    import re
                    progress_match = re.search(r'(\d+)%', line)
                    if progress_match:
                        progress = int(progress_match.group(1))
                        if 10 <= progress <= 90:
                            self._progress(progress, "打包中...")

                    if "error" in line.lower() or "exception" in line.lower() or "traceback" in line.lower():
                        error_lines.append(line)
                        self._log(f"[run_pyinstaller] [ERROR] {line}")
                    elif "warning" in line.lower():
                        self._log(f"[run_pyinstaller] [WARN] {line}")
                    elif any(keyword in line.lower() for keyword in ["collecting", "analyzing", "building", "copying", "packaging"]):
                        self._log(f"[run_pyinstaller] [INFO] {line}")
                    else:
                        self._log(f"[run_pyinstaller] {line}")

            self._log(f"[run_pyinstaller] 输出行数: {line_count}")

            self._log("[run_pyinstaller] 等待子进程结束...")
            process.wait()
            self._log(f"[run_pyinstaller] 子进程结束，返回码: {process.returncode}")

            if process.returncode != 0:
                self._log("[run_pyinstaller] PyInstaller执行失败")
                error_output = "\n".join(full_output[-30:]) if full_output else ""
                self._log(f"[run_pyinstaller] 最后30行输出:\n{error_output}")

                if error_lines:
                    self._log(f"[run_pyinstaller] 错误行数量: {len(error_lines)}")
                    for err_line in error_lines[-10:]:
                        self._log(f"[run_pyinstaller] 错误详情: {err_line}")

                raise RuntimeError(f"PyInstaller执行失败，返回码: {process.returncode}")

            self._log("[run_pyinstaller] PyInstaller执行成功")
            return True

        except subprocess.CalledProcessError as e:
            self._log(f"[run_pyinstaller] PyInstaller调用错误: {str(e)}")
            self._log(f"[run_pyinstaller] 错误诊断: {ErrorParser.format_error_report(str(e))}")
            return False
        except FileNotFoundError:
            self._log("[run_pyinstaller] 错误: 找不到PyInstaller或Python可执行文件")
            self._log(f"[run_pyinstaller] Python路径: {sys.executable}")
            return False
        except Exception as e:
            self._log(f"[run_pyinstaller] 打包过程异常: {type(e).__name__}: {str(e)}")
            self._log(f"[run_pyinstaller] 错误诊断: {ErrorParser.format_error_report(str(e))}")
            return False

    def pack(self, config, stop_event=None):
        self._log("[pack] ==================== 开始打包流程 ====================")
        self._progress(0, "开始打包")

        try:
            source_file = config.get("source_file", "")
            if not source_file or not os.path.exists(source_file):
                self._log("[pack] [ERROR] 源文件不存在")
                self._log(f"[pack] [ERROR] 指定路径: {source_file}")
                return False

            source_dir = os.path.dirname(source_file)

            python_interpreter = config.get("python_interpreter")
            
            if config.get("auto_detect_venv", True) and not python_interpreter:
                self._log("[pack] 步骤0/5: 自动检测虚拟环境")
                detected_venv = self.detect_venv(source_file)
                if detected_venv:
                    python_interpreter = detected_venv
                    config["python_interpreter"] = python_interpreter
                    self._log(f"[pack] 自动检测到虚拟环境: {python_interpreter}")
                else:
                    self._log("[pack] 未检测到虚拟环境，使用默认Python解释器")

            if stop_event and stop_event.is_set():
                self._log("[pack] 打包已取消")
                return False

            self._log("[pack] 步骤1/5: 检查PyInstaller")
            if not self.ensure_pyinstaller(source_dir, python_interpreter):
                self._log("[pack] [ERROR] PyInstaller未安装且自动安装失败，请手动安装")
                return False
            self._log("[pack] PyInstaller检查通过")

            self._log(f"[pack] 源文件: {source_file}")
            self._log(f"[pack] 输出目录: {config.get('output_dir', '')}")
            self._log(f"[pack] 打包模式: {'单文件' if config.get('single_file') else '多文件'}")
            self._log(f"[pack] 是否隐藏控制台: {'是' if config.get('windowed') else '否'}")

            if config.get("auto_clean", True):
                self._progress(5, "清理缓存")
                self._log("[pack] 步骤1/5: 清理PyInstaller缓存")
                project_dir = os.path.dirname(source_file)
                self._log(f"[pack] 项目目录: {project_dir}")
                self.cache_cleaner.clean_pyinstaller_cache(project_dir)
                self._log("[pack] 缓存清理完成")

                self._log("[pack] 清理旧输出文件")
                output_dir = config.get("output_dir", "")
                output_name = config.get("name", "")
                if output_dir and output_name:
                    old_exe = os.path.join(output_dir, f"{output_name}.exe")
                    old_dir = os.path.join(output_dir, output_name)
                    
                    if os.path.exists(old_exe):
                        deleted = False
                        for attempt in range(3):
                            try:
                                os.remove(old_exe)
                                self._log(f"[pack] 已删除旧文件: {old_exe}")
                                deleted = True
                                break
                            except PermissionError:
                                if attempt < 2:
                                    import time
                                    time.sleep(0.5)
                                    self._log(f"[pack] 文件被占用，等待重试...")
                                else:
                                    self._log(f"[pack] [ERROR] 无法删除旧文件（文件被占用）")
                                    self._log(f"[pack] [ERROR] 请关闭正在运行的程序: {old_exe}")
                                    self._log("[pack] [ERROR] 然后重新打包")
                                    return False
                    
                    if os.path.exists(old_dir):
                        import shutil
                        try:
                            shutil.rmtree(old_dir)
                            self._log(f"[pack] 已删除旧文件夹: {old_dir}")
                        except Exception as e:
                            self._log(f"[pack] [WARN] 无法删除旧文件夹: {e}")

            if stop_event and stop_event.is_set():
                self._log("[pack] 打包已取消")
                return False

            if config.get("auto_detect_deps", True):
                self._progress(10, "分析依赖")
                self._log("[pack] 步骤2/5: 自动分析依赖")
                auto_hidden_imports = self.dependency_analyzer.get_hidden_imports(source_file)
                existing_hidden_imports = config.get("hidden_imports", [])
                merged_imports = list(set(existing_hidden_imports + auto_hidden_imports))
                config["hidden_imports"] = merged_imports
                self._log(f"[pack] 自动检测到 {len(auto_hidden_imports)} 个依赖模块")
                if merged_imports:
                    self._log(f"[pack] 合并后的依赖列表: {merged_imports}")
            else:
                self._log("[pack] 步骤2/5: 跳过自动依赖检测")

            self._progress(15, "构建命令")
            self._log("[pack] 步骤3/5: 构建PyInstaller命令")
            cmd, work_dir = self.build_command(config)
            self._log(f"[pack] 命令构建完成，临时目录: {work_dir}")

            if stop_event and stop_event.is_set():
                self._log("[pack] 打包已取消")
                if os.path.exists(work_dir):
                    self.cache_cleaner.delete_dir(work_dir)
                return False

            self._progress(20, "执行PyInstaller")
            self._log("[pack] 步骤4/5: 执行PyInstaller打包")
            if not self.run_pyinstaller(cmd, stop_event):
                self._log("[pack] [ERROR] PyInstaller执行失败")
                if os.path.exists(work_dir):
                    self.cache_cleaner.delete_dir(work_dir)
                return False
            self._log("[pack] PyInstaller打包完成")

            self._progress(80, "清理临时文件")
            self._log("[pack] 步骤5/6: 清理临时文件")
            if os.path.exists(work_dir):
                self._log(f"[pack] 删除临时目录: {work_dir}")
                self.cache_cleaner.delete_dir(work_dir)
                self._log("[pack] 临时文件清理完成")
            else:
                self._log("[pack] 临时目录不存在，跳过清理")

            self._progress(85, "清理冗余文件")
            self._log("[pack] 步骤5.5/6: 清理冗余文件")
            self._cleanup_redundant_files(source_dir, output_dir)

            if config.get("_upx_enabled") and self.upx_compressor.is_available():
                self._progress(87, "UPX压缩")
                self._log("[pack] 执行UPX后压缩")
                output_dir = config.get("output_dir", "")
                output_name = config.get("name", "")
                if config.get("single_file", False):
                    exe_path = os.path.join(output_dir, f"{output_name}.exe")
                    if os.path.exists(exe_path):
                        self.upx_compressor.compress_file(exe_path)
                    else:
                        self._log("[pack] [WARN] 未找到EXE文件，跳过UPX压缩")
                else:
                    app_dir = os.path.join(output_dir, output_name)
                    if os.path.isdir(app_dir):
                        self.upx_compressor.compress_directory(app_dir)
                    else:
                        self._log("[pack] [WARN] 未找到输出目录，跳过UPX压缩")

            if config.get("create_installer", False):
                self._progress(85, "生成安装包")
                self._log("[pack] 步骤6/6: 生成安装包")

                output_dir = config.get("output_dir", "")
                output_name = config.get("name", "")
                app_icon = config.get("icon", "")
                app_version = config.get("app_version") or get_version()

                if config.get("single_file", False):
                    self._log("[pack] [WARN] 当前为单文件模式，安装包将只包含单个EXE文件")
                    self._log("[pack] [WARN] 建议使用多文件模式(-D)以生成完整的安装程序")
                    exe_path = os.path.join(output_dir, f"{output_name}.exe")
                else:
                    self._log("[pack] 当前为多文件模式，将打包整个文件夹")
                    exe_path = os.path.join(output_dir, output_name, f"{output_name}.exe")

                self._log(f"[pack] 查找EXE文件: {exe_path}")
                if not os.path.exists(exe_path) and config.get("single_file", False):
                    alt_path = os.path.join(output_dir, output_name, f"{output_name}.exe")
                    if os.path.exists(alt_path):
                        exe_path = alt_path
                        self._log(f"[pack] 在多文件模式路径找到EXE: {exe_path}")

                if not os.path.exists(exe_path):
                    self._log(f"[pack] [WARN] 未找到EXE文件，无法生成安装包: {exe_path}")
                else:
                    self._create_inno_installer(config, exe_path, output_dir, output_name, app_version, app_icon)
            self._progress(100, "打包完成")
            self._log("[pack] ==================== 打包流程完成 ====================")
            self._log("[pack] 打包任务完成，结果: 成功")

            return True

        except Exception as e:
            self._log(f"[pack] [ERROR] 打包失败: {type(e).__name__}: {str(e)}")
            import traceback
            self._log(f"[pack] [ERROR] 堆栈信息:\n{traceback.format_exc()}")
            self._log(f"[pack] [ERROR] 错误诊断: {ErrorParser.format_error_report(str(e))}")
            return False

    def validate_config(self, config):
        errors = []

        if not config.get("source_file"):
            errors.append("请选择源文件")
        elif not os.path.exists(config["source_file"]):
            errors.append(f"源文件不存在: {config['source_file']}")
        elif not config["source_file"].endswith((".py", ".pyw")):
            errors.append("源文件必须是.py或.pyw文件")

        if not config.get("output_dir"):
            errors.append("请选择输出目录")
        elif not os.path.isdir(config["output_dir"]):
            try:
                os.makedirs(config["output_dir"])
            except OSError:
                errors.append(f"无法创建输出目录: {config['output_dir']}")

        if config.get("icon") and not os.path.exists(config["icon"]):
            errors.append(f"图标文件不存在: {config['icon']}")

        return errors

    def get_default_config(self, source_file=""):
        config = {
            "source_file": source_file,
            "output_dir": os.path.dirname(source_file) if source_file else "",
            "name": get_file_name_without_ext(source_file) if source_file else "",
            "single_file": False,
            "windowed": False,
            "icon": "",
            "hidden_imports": [],
            "excludes": [],
            "data_files": [],
            "auto_clean": True,
            "auto_detect_deps": True,
            "app_version": get_version(),
            "enable_upx": None
        }
        return config

    def detect_dependencies(self, source_file):
        return self.dependency_analyzer.get_hidden_imports(source_file)

    def get_redundant_modules(self):
        return self.dependency_analyzer.get_redundant_modules()