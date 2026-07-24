import sys, os
sys.path.insert(0, r'C:\Users\Administrator\Documents\trae_projects\python_exe_packer\python_exe_packer')
os.chdir(r'C:\Users\Administrator\Documents\trae_projects\python_exe_packer\python_exe_packer')
from utils.env_checker import EnvChecker
checker = EnvChecker()
results = checker.check_all()
for key, result in results.items():
    status = result["status"].upper()
    name = result["name"]
    value = result["value"]
    message = result["message"]
    msg = f"[{status}] {name}: {value} - {message}"
    print(msg)
