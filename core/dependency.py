import ast
import os
import sys
import importlib
import importlib.util
from utils.log_utils import get_logger


logger = get_logger()


class DependencyAnalyzer:
    STANDARD_LIBRARIES = {
        "os", "sys", "re", "json", "xml", "csv", "math", "random", "datetime",
        "time", "threading", "multiprocessing", "subprocess", "socket",
        "urllib", "http", "email", "smtplib", "ftplib", "sqlite3",
        "pickle", "marshal", "hashlib", "hmac", "base64", "binascii",
        "struct", "array", "collections", "itertools", "functools",
        "operator", "copy", "deepcopy", "gc", "weakref", "types",
        "traceback", "logging", "configparser", "argparse", "textwrap",
        "string", "unicodedata", "locale", "io", "tempfile", "shutil",
        "glob", "fnmatch", "linecache", "zipfile", "tarfile", "gzip",
        "bz2", "lzma", "ssl", "select", "errno", "signal", "msvcrt",
        "ctypes", "inspect", "ast", "dis", "pdb", "cProfile", "profile",
        "pstats", "platform", "sysconfig", "site", "pkgutil", "importlib",
        "warnings", "contextlib", "abc", "numbers", "enum", "dataclasses",
        "typing", "typing_extensions", "pathlib", "zoneinfo", "graphlib",
        "statistics", "fractions", "decimal", "cmath", "complex",
        "bisect", "heapq", "queue", "deque", "ChainMap", "Counter",
        "OrderedDict", "defaultdict", "namedtuple", "UserList", "UserDict",
        "UserString", "contextvars", "asyncio", "concurrent", "futures",
        "concurrent.futures", "sched", "queue", "dummy_threading",
        "_thread", "dummy_thread", "winreg", "msilib", "ctypes.wintypes",
        "nt", "posix", "genericpath", "ntpath", "posixpath", "path",
        "sitecustomize", "usercustomize", "py_compile", "compileall",
        "dis", "opcode", "token", "tokenize", "keyword", "symtable",
        "ast", "parser", "astunparse", "tabnanny", "pyclbr",
        "idlelib", "turtle", "doctest", "unittest", "unittest.mock",
        "test", "ensurepip", "venv", "pip", "setuptools", "distutils",
        "pkg_resources", "wheel", "pep517", "pep518", "tomllib",
        "xmlrpc", "xmlrpclib", "cgi", "cgitb", "webbrowser", "getpass",
        "crypt", "pwd", "grp", "spwd", "resource", "nis", "syslog",
        "commands", "pipes", "posixfile", "macpath", "macurl2path",
        "aifc", "audioop", "cgi", "cgitb", "chunk", "crypt", "imghdr",
        "mailcap", "msilib", "nis", "nntplib", "ossaudiodev", "pipes",
        "smtpd", "spwd", "sunau", "telnetlib", "uu", "xdrlib",
        "colorama", "six", "future", "past", "builtins"
    }

    EXCLUDE_MODULES = {
        "__main__", "__init__",
        "test", "tests", "unittest", "pytest", "py_test",
        "numpy.testing", "matplotlib.tests", "scipy.testing",
        "doc", "docs", "example", "examples", "demo", "samples",
        "__pycache__", ".git", ".svn", ".hg", ".tox", ".eggs", "egg-info"
    }

    DEEP_ANALYSIS_EXCLUDED = {
        "numpy", "numpy.", "scipy", "scipy.", "pandas", "pandas.",
        "matplotlib", "matplotlib.", "PIL", "PIL.", "torch", "torch.",
        "tensorflow", "tensorflow.", "PyQt5", "PyQt5.", "PyQt6", "PyQt6.",
        "PySide2", "PySide2.", "PySide6", "PySide6.", "tkinter", "tkinter.",
        "wx", "wx.", "django", "django.", "flask", "flask.", "requests", "requests.",
        "urllib3", "urllib3.", "certifi", "certifi.", "charset_normalizer", "charset_normalizer.",
        "idna", "idna.", "beautifulsoup4", "bs4", "lxml", "lxml.",
        "sqlalchemy", "sqlalchemy.", "jinja2", "jinja2.", "markupsafe", "markupsafe.",
        "werkzeug", "werkzeug.", "click", "click.", "colorama", "colorama.",
        "six", "six.", "future", "future.", "fastapi", "fastapi.", "uvicorn", "uvicorn.",
        "scikit", "scikit.", "sklearn", "sklearn.", "seaborn", "seaborn.",
        "networkx", "networkx.", "sympy", "sympy.", "statsmodels", "statsmodels.",
        "pytest", "pytest.", "unittest", "unittest.", "test", "test.", "tests", "tests.",
    }

    def __init__(self):
        self.visited = set()
        self.dependencies = set()
        self.max_depth = 2
        self.deep_analysis_excluded = self.DEEP_ANALYSIS_EXCLUDED
        self.module_path_cache = {}

    def analyze_file(self, file_path, max_depth=None):
        logger.info(f"[DependencyAnalyzer] 开始分析文件: {file_path}")
        self.visited = set()
        self.dependencies = set()
        if max_depth is not None:
            self.max_depth = max_depth
        self._analyze_file_recursive(file_path, depth=0)
        logger.info(f"[DependencyAnalyzer] 文件分析完成，找到 {len(self.dependencies)} 个依赖")
        return sorted(self.dependencies)

    def _analyze_file_recursive(self, file_path, depth=0):
        if not os.path.isfile(file_path):
            logger.debug(f"[DependencyAnalyzer] 文件不存在: {file_path}")
            return

        file_path = os.path.abspath(file_path)
        if file_path in self.visited:
            logger.debug(f"[DependencyAnalyzer] 已访问过: {file_path}")
            return

        if depth > self.max_depth:
            logger.debug(f"[DependencyAnalyzer] 超过最大深度({self.max_depth})，跳过: {file_path}")
            return

        logger.debug(f"[DependencyAnalyzer] 分析文件: {file_path} (深度: {depth})")
        self.visited.add(file_path)

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            logger.debug(f"[DependencyAnalyzer] 文件读取成功，大小: {len(content)} 字节")
        except (OSError, UnicodeDecodeError) as e:
            logger.warning(f"[DependencyAnalyzer] 无法读取文件: {file_path}, 错误: {e}")
            return

        try:
            tree = ast.parse(content)
            logger.debug(f"[DependencyAnalyzer] AST解析成功")
        except SyntaxError as e:
            logger.warning(f"[DependencyAnalyzer] 文件语法错误: {file_path}, 错误: {e}")
            return

        imports = self._extract_imports(tree)
        logger.debug(f"[DependencyAnalyzer] 提取到 {len(imports)} 个import语句")

        for imp in imports:
            if self._is_standard_library(imp):
                logger.debug(f"[DependencyAnalyzer] 跳过标准库: {imp}")
                continue

            if self._should_exclude(imp):
                logger.debug(f"[DependencyAnalyzer] 跳过排除模块: {imp}")
                continue

            if imp not in self.dependencies:
                self.dependencies.add(imp)
                logger.info(f"[DependencyAnalyzer] 添加依赖: {imp}")

            should_recurse = True
            for excluded in self.deep_analysis_excluded:
                if imp == excluded or imp.startswith(excluded):
                    should_recurse = False
                    logger.debug(f"[DependencyAnalyzer] 跳过深度分析大型库: {imp}")
                    break

            if not should_recurse:
                continue

            module_path = self._find_module_path(imp, os.path.dirname(file_path))
            if module_path:
                logger.debug(f"[DependencyAnalyzer] 递归分析: {module_path}")
                self._analyze_file_recursive(module_path, depth + 1)
            else:
                logger.debug(f"[DependencyAnalyzer] 未找到模块路径: {imp}")

    def _extract_imports(self, tree):
        imports = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)

            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)

                    for alias in node.names:
                        full_name = f"{node.module}.{alias.name}"
                        imports.append(full_name)

        return imports

    def _is_standard_library(self, module_name):
        parts = module_name.split(".")
        for i in range(len(parts), 0, -1):
            name = ".".join(parts[:i])
            if name in self.STANDARD_LIBRARIES:
                return True
        return False

    def _should_exclude(self, module_name):
        for exclude in self.EXCLUDE_MODULES:
            if module_name == exclude or module_name.startswith(exclude + "."):
                return True
        return False

    def _find_module_path(self, module_name, search_dir=None):
        if module_name == "__main__":
            return None

        cache_key = (module_name, search_dir)
        if cache_key in self.module_path_cache:
            return self.module_path_cache[cache_key]

        paths = []

        if search_dir:
            paths.append(search_dir)

        paths.extend(sys.path)

        parts = module_name.split(".")

        for path in paths:
            if not os.path.isdir(path):
                continue

            module_path = os.path.join(path, *parts)

            if os.path.isfile(module_path + ".py"):
                result = module_path + ".py"
                self.module_path_cache[cache_key] = result
                return result

            if os.path.isfile(module_path + ".pyw"):
                result = module_path + ".pyw"
                self.module_path_cache[cache_key] = result
                return result

            init_path = os.path.join(module_path, "__init__.py")
            if os.path.isfile(init_path):
                result = init_path
                self.module_path_cache[cache_key] = result
                return result

        try:
            spec = importlib.util.find_spec(module_name)
            if spec and spec.origin:
                result = spec.origin
                self.module_path_cache[cache_key] = result
                return result
        except (ImportError, ValueError):
            pass

        self.module_path_cache[cache_key] = None
        return None

    def get_hidden_imports(self, file_path):
        logger.info(f"[DependencyAnalyzer] 获取hidden_imports: {file_path}")
        dependencies = self.analyze_file(file_path)
        hidden_imports = []

        for dep in dependencies:
            try:
                importlib.import_module(dep)
                hidden_imports.append(dep)
                logger.debug(f"[DependencyAnalyzer] 验证通过: {dep}")
            except ImportError as e:
                logger.debug(f"[DependencyAnalyzer] 无法导入模块(跳过): {dep}, 错误: {e}")

        logger.info(f"[DependencyAnalyzer] hidden_imports验证完成，有效依赖: {len(hidden_imports)}")
        return hidden_imports

    def analyze_project(self, project_dir):
        all_dependencies = set()

        for root, dirs, files in os.walk(project_dir):
            dirs[:] = [d for d in dirs if d not in self.EXCLUDE_MODULES]

            for file in files:
                if file.endswith(".py") or file.endswith(".pyw"):
                    file_path = os.path.join(root, file)
                    deps = self.analyze_file(file_path)
                    all_dependencies.update(deps)

        return sorted(all_dependencies)

    @staticmethod
    def get_redundant_modules():
        return [
            "tkinter", "tkinter.*",
            "matplotlib", "matplotlib.*",
            "numpy", "numpy.*",
            "scipy", "scipy.*",
            "pandas", "pandas.*",
            "PIL", "PIL.*",
            "PyQt5", "PyQt5.*",
            "PyQt6", "PyQt6.*",
            "PySide2", "PySide2.*",
            "PySide6", "PySide6.*",
            "wx", "wx.*",
            "pygame", "pygame.*",
            "requests", "requests.*",
            "urllib3", "urllib3.*",
            "certifi", "certifi.*",
            "charset_normalizer", "charset_normalizer.*",
            "idna", "idna.*",
            "beautifulsoup4", "bs4",
            "lxml", "lxml.*",
            "sqlalchemy", "sqlalchemy.*",
            "django", "django.*",
            "flask", "flask.*",
            "fastapi", "fastapi.*",
            "uvicorn", "uvicorn.*",
            "jinja2", "jinja2.*",
            "markupsafe", "markupsafe.*",
            "werkzeug", "werkzeug.*",
            "click", "click.*",
            "colorama", "colorama.*",
            "six", "six.*",
            "future", "future.*",
        ]