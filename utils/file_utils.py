import os
import shutil
import fnmatch
import subprocess


def get_hidden_process_creation_flags():
    if os.name == 'nt':
        return subprocess.CREATE_NO_WINDOW
    return 0


def run_hidden(args, capture_output=False, text=True, timeout=None, use_hidden=True, cwd=None, **kwargs):
    if use_hidden:
        kwargs['creationflags'] = get_hidden_process_creation_flags()
    kwargs['shell'] = False
    if capture_output:
        kwargs['stdout'] = subprocess.PIPE
        kwargs['stderr'] = subprocess.STDOUT
    return subprocess.run(args, text=text, timeout=timeout, cwd=cwd, **kwargs)


def popen_hidden(args, stdout=None, stderr=None, text=True, cwd=None, env=None, **kwargs):
    kwargs['creationflags'] = get_hidden_process_creation_flags()
    kwargs['shell'] = False
    if stdout is None:
        stdout = subprocess.PIPE
    if stderr is None:
        stderr = subprocess.STDOUT
    return subprocess.Popen(args, stdout=stdout, stderr=stderr, text=text, cwd=cwd, env=env, **kwargs)


def get_file_size(file_path):
    try:
        return os.path.getsize(file_path)
    except (OSError, TypeError):
        return 0


def format_file_size(size_bytes):
    if size_bytes <= 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB"]
    for unit in units:
        if size_bytes < 1024:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.2f} TB"


def ensure_dir_exists(dir_path):
    try:
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
        return True
    except OSError:
        return False


def delete_file(file_path):
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
        return True
    except OSError:
        return False


def delete_dir(dir_path):
    try:
        if os.path.exists(dir_path):
            shutil.rmtree(dir_path)
        return True
    except OSError:
        return False


def list_files(dir_path, pattern="*"):
    try:
        files = []
        for root, dirs, filenames in os.walk(dir_path):
            for filename in fnmatch.filter(filenames, pattern):
                files.append(os.path.join(root, filename))
        return files
    except OSError:
        return []


def get_parent_dir(file_path):
    try:
        return os.path.dirname(os.path.abspath(file_path))
    except (OSError, TypeError):
        return ""


def get_file_name(file_path):
    try:
        return os.path.basename(file_path)
    except (OSError, TypeError):
        return ""


def get_file_extension(file_path):
    try:
        return os.path.splitext(file_path)[1].lower()
    except (OSError, TypeError):
        return ""


def get_file_name_without_ext(file_path):
    try:
        return os.path.splitext(os.path.basename(file_path))[0]
    except (OSError, TypeError):
        return ""


def copy_file(src, dst):
    try:
        ensure_dir_exists(get_parent_dir(dst))
        shutil.copy2(src, dst)
        return True
    except (OSError, shutil.Error):
        return False


def move_file(src, dst):
    try:
        ensure_dir_exists(get_parent_dir(dst))
        shutil.move(src, dst)
        return True
    except (OSError, shutil.Error):
        return False


def is_python_file(file_path):
    ext = get_file_extension(file_path)
    return ext in [".py", ".pyw"]


def is_ico_file(file_path):
    ext = get_file_extension(file_path)
    return ext == ".ico"


def is_executable_file(file_path):
    ext = get_file_extension(file_path)
    return ext == ".exe"


def find_files_by_extension(dir_path, extensions):
    extensions = [ext.lower() for ext in extensions]
    result = []
    for root, dirs, files in os.walk(dir_path):
        for file in files:
            if os.path.splitext(file)[1].lower() in extensions:
                result.append(os.path.join(root, file))
    return result


def get_temp_dir():
    return os.environ.get("TEMP", "/tmp")


def get_home_dir():
    return os.path.expanduser("~")