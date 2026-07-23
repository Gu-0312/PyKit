import os
import sys


class VenvScanner:
    VENV_NAMES = ["venv", ".venv", "env", ".env", "python_env", ".python_env"]

    def scan_project_dir(self, start_dir):
        found = []
        current_dir = os.path.abspath(start_dir)
        while current_dir and current_dir != os.path.dirname(current_dir):
            for venv_name in self.VENV_NAMES:
                venv_path = os.path.join(current_dir, venv_name)
                python_exe = os.path.join(venv_path, "Scripts", "python.exe")
                if os.path.exists(python_exe):
                    found.append((os.path.basename(current_dir), python_exe))
            current_dir = os.path.dirname(current_dir)
        return found

    def scan_common_locations(self):
        found = []
        home = os.path.expanduser("~")
        search_roots = [
            home,
            os.path.join(home, "Documents"),
            os.path.join(home, "Desktop"),
            os.path.join(home, "Projects"),
            os.path.join(home, "source"),
        ]
        for root in search_roots:
            if os.path.isdir(root):
                try:
                    for entry in os.listdir(root):
                        entry_path = os.path.join(root, entry)
                        if os.path.isdir(entry_path):
                            for venv_name in self.VENV_NAMES:
                                venv_path = os.path.join(entry_path, venv_name)
                                python_exe = os.path.join(venv_path, "Scripts", "python.exe")
                                if os.path.exists(python_exe):
                                    found.append((entry, python_exe))
                                    break
                except PermissionError:
                    continue
        return found

    def scan_all(self, start_dir=None):
        found = []
        if start_dir:
            found.extend(self.scan_project_dir(start_dir))
        found.extend(self.scan_common_locations())
        seen = set()
        unique = []
        for name, path in found:
            if path not in seen:
                seen.add(path)
                unique.append((name, path))
        return unique
