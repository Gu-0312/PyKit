import os
import sys
import ctypes
import hashlib


class SingleInstance:
    def __init__(self):
        self.mutex_handle = None
        exe_path = os.path.abspath(sys.executable)
        hash_val = hashlib.sha256(exe_path.encode()).hexdigest()[:16]
        self.mutex_name = f"Global\\PyPacker_{hash_val}"

    def acquire(self):
        if sys.platform == 'win32':
            kernel32 = ctypes.windll.kernel32
            
            kernel32.SetLastError(0)
            self.mutex_handle = kernel32.CreateMutexW(None, False, self.mutex_name)
            if self.mutex_handle == 0:
                return False
                
            last_error = kernel32.GetLastError()
            
            if last_error == 183:
                kernel32.CloseHandle(self.mutex_handle)
                self.mutex_handle = None
                return False
                
            return True
        else:
            lock_file = os.path.join(
                os.environ.get("TEMP", "/tmp"),
                "PyPacker.lock"
            )
            self.lock_file = lock_file
            try:
                self.lock_handle = open(self.lock_file, 'w')
                self.lock_handle.write(str(os.getpid()))
                self.lock_handle.flush()
                return True
            except IOError:
                return False

    def release(self):
        if sys.platform == 'win32':
            if self.mutex_handle:
                try:
                    ctypes.windll.kernel32.CloseHandle(self.mutex_handle)
                except Exception:
                    pass
                self.mutex_handle = None
        else:
            if self.lock_handle:
                try:
                    self.lock_handle.close()
                except Exception:
                    pass
                self.lock_handle = None
            try:
                if hasattr(self, 'lock_file') and os.path.exists(self.lock_file):
                    os.remove(self.lock_file)
            except Exception:
                pass

    def __del__(self):
        self.release()