import os
import subprocess
import tempfile
import uuid
from utils.log_utils import get_logger
from _version import get_version

logger = get_logger()


class InnoSetup:
    def __init__(self):
        self.on_log = None
        self.on_progress = None

    def set_log_callback(self, callback):
        self.on_log = callback

    def set_progress_callback(self, callback):
        self.on_progress = callback

    def _log(self, message):
        logger.info(message)
        if self.on_log:
            self.on_log(message)

    def _progress(self, percent, message):
        if self.on_progress:
            self.on_progress(percent, message)

    def _find_iscc_from_registry(self):
        try:
            import winreg
            keys_to_check = [
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Inno Setup 6_is1"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Inno Setup_is1"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\Inno Setup 6_is1"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\Inno Setup_is1"),
            ]
            
            for hkey, subkey in keys_to_check:
                try:
                    with winreg.OpenKey(hkey, subkey, 0, winreg.KEY_READ) as key:
                        install_location, _ = winreg.QueryValueEx(key, "InstallLocation")
                        if install_location:
                            iscc_path = os.path.join(install_location, "ISCC.exe")
                            if os.path.exists(iscc_path):
                                self._log(f"[InnoSetup] 通过注册表找到 ISCC: {iscc_path}")
                                return iscc_path
                except FileNotFoundError:
                    continue
                except Exception as e:
                    continue
        except Exception:
            pass
        return None

    def find_iscc(self):
        common_paths = [
            os.path.join(os.environ.get("ProgramFiles", "C:\\Program Files"), "Inno Setup 6", "ISCC.exe"),
            os.path.join(os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)"), "Inno Setup 6", "ISCC.exe"),
            os.path.join(os.environ.get("ProgramFiles", "C:\\Program Files"), "Inno Setup", "ISCC.exe"),
            os.path.join(os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)"), "Inno Setup", "ISCC.exe"),
            os.path.join("C:\\", "Program Files", "Inno Setup 6", "ISCC.exe"),
            os.path.join("C:\\", "Program Files (x86)", "Inno Setup 6", "ISCC.exe"),
            os.path.join("C:\\", "Program Files", "Inno Setup", "ISCC.exe"),
            os.path.join("C:\\", "Program Files (x86)", "Inno Setup", "ISCC.exe"),
            os.path.join(os.environ.get("LOCALAPPDATA", "C:\\Users\\Administrator\\AppData\\Local"), "Programs", "Inno Setup 6", "ISCC.exe"),
            os.path.join(os.environ.get("LOCALAPPDATA", "C:\\Users\\Administrator\\AppData\\Local"), "Programs", "Inno Setup", "ISCC.exe"),
            os.path.join("D:\\", "Program Files", "Inno Setup 6", "ISCC.exe"),
            os.path.join("D:\\", "Program Files (x86)", "Inno Setup 6", "ISCC.exe"),
            os.path.join("D:\\", "Program Files", "Inno Setup", "ISCC.exe"),
            os.path.join("D:\\", "Program Files (x86)", "Inno Setup", "ISCC.exe"),
            os.path.join("D:\\", "Inno Setup 6", "ISCC.exe"),
            os.path.join("D:\\", "Inno Setup", "ISCC.exe"),
            os.path.join("E:\\", "Program Files", "Inno Setup 6", "ISCC.exe"),
            os.path.join("E:\\", "Program Files (x86)", "Inno Setup 6", "ISCC.exe"),
            os.path.join("E:\\", "Program Files", "Inno Setup", "ISCC.exe"),
            os.path.join("E:\\", "Program Files (x86)", "Inno Setup", "ISCC.exe"),
            os.path.join("E:\\", "Inno Setup 6", "ISCC.exe"),
            os.path.join("E:\\", "Inno Setup", "ISCC.exe"),
        ]

        for path in common_paths:
            if os.path.exists(path):
                self._log(f"[InnoSetup] 找到 ISCC: {path}")
                return path

        reg_path = self._find_iscc_from_registry()
        if reg_path:
            return reg_path

        import subprocess
        try:
            result = subprocess.run(
                ["where", "iscc"],
                capture_output=True,
                text=True,
                timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            if result.returncode == 0 and result.stdout.strip():
                iscc_path = result.stdout.strip().split('\n')[0].strip()
                if os.path.exists(iscc_path):
                    self._log(f"[InnoSetup] 通过where命令找到 ISCC: {iscc_path}")
                    return iscc_path
        except Exception:
            pass

        try:
            result = subprocess.run(
                ["cmd", "/c", "where", "iscc"],
                capture_output=True,
                text=True,
                timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            if result.returncode == 0 and result.stdout.strip():
                iscc_path = result.stdout.strip().split('\n')[0].strip()
                if os.path.exists(iscc_path):
                    self._log(f"[InnoSetup] 通过cmd where命令找到 ISCC: {iscc_path}")
                    return iscc_path
        except Exception:
            pass

        self._log("[InnoSetup] 在常见路径中未找到 ISCC")
        self._log(f"[InnoSetup] 搜索路径: {common_paths}")
        return None

    def is_installed(self):
        return self.find_iscc() is not None

    def _validate_and_convert_icon(self, icon_path):
        max_file_size = 500 * 1024
        standard_sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
        
        try:
            from PIL import Image
            
            if os.path.getsize(icon_path) > max_file_size:
                self._log(f"[InnoSetup] [WARN] 图标文件过大 ({os.path.getsize(icon_path) / 1024:.1f} KB)，需要转换")
                needs_convert = True
            else:
                try:
                    with Image.open(icon_path) as img:
                        if img.format == 'ICO' and len(img.info.get('sizes', [img.size])) >= 2:
                            self._log(f"[InnoSetup] 图标文件格式正确，包含 {len(img.info.get('sizes', [img.size]))} 个尺寸")
                            return icon_path, None
                        else:
                            self._log(f"[InnoSetup] [WARN] 图标文件格式不是标准ICO或尺寸不足，需要转换")
                            needs_convert = True
                except Exception:
                    self._log(f"[InnoSetup] [WARN] 无法识别图标文件格式，需要转换")
                    needs_convert = True
            
            if needs_convert:
                with Image.open(icon_path) as img:
                    if img.mode != 'RGBA':
                        img = img.convert('RGBA')
                    
                    icon_sizes = []
                    for size in standard_sizes:
                        if size[0] <= img.size[0] and size[1] <= img.size[1]:
                            icon_sizes.append(img.resize(size, Image.LANCZOS))
                    
                    if not icon_sizes:
                        icon_sizes.append(img.resize((32, 32), Image.LANCZOS))
                    
                    temp_ico = tempfile.NamedTemporaryFile(suffix='.ico', delete=False)
                    temp_ico_path = temp_ico.name
                    temp_ico.close()
                    
                    icon_sizes[0].save(temp_ico_path, format='ICO', sizes=[s.size for s in icon_sizes])
                    self._log(f"[InnoSetup] 图标已转换并保存到: {temp_ico_path}")
                    return temp_ico_path, temp_ico_path
            
        except ImportError:
            self._log(f"[InnoSetup] [WARN] Pillow未安装，无法校验和转换图标，跳过图标配置")
        except Exception as e:
            self._log(f"[InnoSetup] [WARN] 图标转换失败: {str(e)}，跳过图标配置")
        
        return None, None

    def _validate_icon_line(self, line):
        import re
        icon_line_pattern = r'^Name:\s*"[^"]+";\s*Filename:\s*"[^"]+"(;\s*IconFilename:\s*"[^"]+")?$'
        if re.match(icon_line_pattern, line.strip()):
            return True
        return False

    def generate_script(self, exe_path, output_dir, app_name, app_version=None, app_icon=""):
        if app_version is None:
            app_version = get_version()
        app_dir = os.path.dirname(exe_path).replace("\\", "/")
        exe_name = os.path.basename(exe_path)
        output_dir_clean = output_dir.replace("\\", "/")

        icon_file = ""
        icon_filename = ""
        if app_icon:
            icon_path_clean = app_icon.replace("\\", "/")
            icon_file = f'SetupIconFile="{icon_path_clean}"'
            icon_filename = f'; IconFilename: "{icon_path_clean}"'
            self._log(f"[InnoSetup] 使用图标文件: {app_icon}")

        license_text = f'''许可协议

版权所有 (C) 2026 {app_name}

本软件仅供个人使用。未经授权，不得用于商业用途。

您可以自由使用、复制和分发本软件，但不得修改或逆向工程本软件。

接受本协议即表示您同意上述条款。'''

        escaped_license = license_text.replace('"', '\\"').replace('\n', '\\n')

        script_content = f'''
[Setup]
AppId={{{{5B68A8A2-7D1E-4F3A-9B8D-7E9F8A7B6C5D}}}}
AppName="{app_name}"
AppVersion="{app_version}"
AppVerName="{app_name} {app_version}"
AppPublisher=个人开发者
AppPublisherURL=https://example.com/
AppSupportURL=https://example.com/
AppUpdatesURL=https://example.com/
DefaultDirName={{autopf}}\\{app_name}
DefaultGroupName={app_name}
OutputDir="{output_dir_clean}"
OutputBaseFilename={app_name}-{app_version}-setup
Compression=lzma
SolidCompression=yes
{icon_file}
WizardImageFile=
WizardSmallImageFile=
UninstallDisplayName="{app_name} {app_version}"
AllowCancelDuringInstall=no
ShowLanguageDialog=no

[Languages]
Name: "chinesesimplified"; MessagesFile: "compiler:Languages\\ChineseSimplified.isl"

[License]
LicenseText="{escaped_license}"

[Files]
Source: "{app_dir}\\*"; DestDir: "{{app}}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{{group}}\\{app_name}"; Filename: "{{app}}\\{exe_name}"{icon_filename}
Name: "{{group}}\\卸载 {app_name}"; Filename: "{{uninstallexe}}"
Name: "{{commondesktop}}\\{app_name}"; Filename: "{{app}}\\{exe_name}"{icon_filename}

[Registry]
Root: HKLM; Subkey: "SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{app_name}"; ValueType: string; ValueName: "DisplayName"; ValueData: "{app_name} {app_version}"; Flags: uninsdeletevalue
Root: HKLM; Subkey: "SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{app_name}"; ValueType: string; ValueName: "UninstallString"; ValueData: "{{uninstallexe}}"; Flags: uninsdeletevalue
Root: HKLM; Subkey: "SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{app_name}"; ValueType: string; ValueName: "DisplayVersion"; ValueData: "{app_version}"; Flags: uninsdeletevalue
Root: HKLM; Subkey: "SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{app_name}"; ValueType: string; ValueName: "Publisher"; ValueData: "个人开发者"; Flags: uninsdeletevalue
Root: HKLM; Subkey: "SOFTWARE\\{app_name}"; ValueType: string; ValueName: "InstallPath"; ValueData: "{{app}}"; Flags: uninsdeletevalue

[Run]
Filename: "{{app}}\\{exe_name}"; Description: "运行 {app_name}"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "{{app}}\\{exe_name}"; Parameters: "/uninstall"; Flags: skipifsilent
        '''.strip()

        return script_content

    def compile_installer(self, script_path):
        iscc_path = self.find_iscc()
        if not iscc_path:
            self._log("[InnoSetup] [ERROR] 未找到ISCC编译器，请确保已安装Inno Setup")
            self._log("[InnoSetup] [ERROR] Inno Setup下载地址: https://jrsoftware.org/isdl.php")
            return False

        self._log(f"[InnoSetup] 开始编译安装包，脚本路径: {script_path}")
        self._log(f"[InnoSetup] ISCC路径: {iscc_path}")

        try:
            self._log("[InnoSetup] 正在调用ISCC编译，请稍候...")
            process = subprocess.Popen(
                [iscc_path, script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=False,
                creationflags=subprocess.CREATE_NO_WINDOW
            )

            full_output = []
            error_found = False
            for line_bytes in process.stdout:
                try:
                    line = line_bytes.decode('utf-8').strip()
                except UnicodeDecodeError:
                    try:
                        line = line_bytes.decode('gbk').strip()
                    except UnicodeDecodeError:
                        line = line_bytes.decode('gbk', errors='replace').strip()
                if line:
                    full_output.append(line)
                    if "Error" in line:
                        error_found = True
                        self._log(f"[InnoSetup] [ERROR] {line}")
                    elif "Warning" in line:
                        self._log(f"[InnoSetup] [WARN] {line}")
                    elif "Compiling" in line or "Successfully" in line or "Done" in line:
                        self._log(f"[InnoSetup] [INFO] {line}")

            process.wait()
            self._log(f"[InnoSetup] 编译完成，返回码: {process.returncode}")

            if process.returncode == 0:
                self._log("[InnoSetup] 安装包编译成功")
                return True
            else:
                self._log(f"[InnoSetup] [ERROR] 安装包编译失败，返回码: {process.returncode}")
                if full_output:
                    self._log(f"[InnoSetup] [ERROR] 最后10行输出:")
                    for line in full_output[-10:]:
                        self._log(f"[InnoSetup] [ERROR]   {line}")
                return False

        except FileNotFoundError:
            self._log(f"[InnoSetup] [ERROR] ISCC文件不存在: {iscc_path}")
            return False
        except PermissionError:
            self._log(f"[InnoSetup] [ERROR] 没有权限执行ISCC，请以管理员身份运行")
            return False
        except Exception as e:
            self._log(f"[InnoSetup] [ERROR] 编译过程异常: {type(e).__name__}: {str(e)}")
            return False

    def create_installer(self, exe_path, output_dir, app_name, app_version=None, app_icon=""):
        if app_version is None:
            app_version = get_version()
        self._log("[InnoSetup] 开始创建安装包")
        self._log(f"[InnoSetup] 输入参数:")
        self._log(f"[InnoSetup]   EXE路径: {exe_path}")
        self._log(f"[InnoSetup]   输出目录: {output_dir}")
        self._log(f"[InnoSetup]   应用名称: {app_name}")
        self._log(f"[InnoSetup]   应用版本: {app_version}")
        self._log(f"[InnoSetup]   图标文件: {app_icon if app_icon else '无'}")

        if not os.path.exists(exe_path):
            self._log(f"[InnoSetup] [ERROR] EXE文件不存在: {exe_path}")
            return False

        app_dir_check = os.path.dirname(exe_path)
        self._log(f"[InnoSetup] 检查目录: {app_dir_check}")
        self._log(f"[InnoSetup] 目录存在: {os.path.exists(app_dir_check)}")
        if os.path.exists(app_dir_check):
            self._log(f"[InnoSetup] 目录内容: {os.listdir(app_dir_check)[:5]}...")

        final_icon_path = app_icon
        converted_icon_path = None
        if app_icon:
            icon_absolute_path = os.path.abspath(app_icon)
            if not os.path.exists(icon_absolute_path):
                self._log(f"[InnoSetup] [ERROR] 图标文件不存在: {icon_absolute_path}")
                return False
            
            final_icon_path, converted_icon_path = self._validate_and_convert_icon(icon_absolute_path)
            if not final_icon_path:
                self._log(f"[InnoSetup] [WARN] 图标校验/转换失败，将不使用图标")
                final_icon_path = ""

        script_content = self.generate_script(exe_path, output_dir, app_name, app_version, final_icon_path)

        import re
        template_pattern = r'\{\{.*?\}\}'
        all_matches = re.findall(template_pattern, script_content)

        innosetup_constants = {'app', 'group', 'tmp', 'autopf', 'commondesktop', 
                               'commonprograms', 'commonstartup', 'uninstallexe', 
                               'winappdir', 'winstartup', 'documents', 'desktop'}

        guid_pattern = r'^[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}$'

        bad_matches = []
        for match in all_matches:
            inner = match[2:-2]
            if re.match(guid_pattern, inner):
                continue
            if inner.lower() in innosetup_constants:
                continue
            bad_matches.append(match)

        if bad_matches:
            self._log(f"[InnoSetup] [ERROR] 检测到未替换的模板变量: {bad_matches}")
            for i, line in enumerate(script_content.split('\n'), 1):
                if any(match in line for match in bad_matches):
                    self._log(f"[InnoSetup] [ERROR] 第{i}行包含模板变量: {line}")
            self._log(f"[InnoSetup] [ERROR] 如果是 Inno Setup 原生语法，请确认是否已正确转义")
            raise ValueError(f"检测到未替换的模板变量: {bad_matches}")

        guid_pattern = r'(?<!\{)\{[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}\}(?!\})'
        guid_matches = re.findall(guid_pattern, script_content)
        if guid_matches:
            self._log(f"[InnoSetup] [WARN] 检测到裸的单层花括号 GUID: {guid_matches}")
            self._log(f"[InnoSetup] [WARN] 建议改为双层花括号格式，例如: {{guid}}")

        self._log(f"[InnoSetup] 生成的安装脚本内容:")
        for i, line in enumerate(script_content.split('\n'), 1):
            self._log(f"[InnoSetup]   {i:3d}: {line}")

        lines = script_content.split('\n')
        in_icons_section = False
        for i, line in enumerate(lines):
            if line.strip().startswith('[Icons]'):
                in_icons_section = True
                continue
            if in_icons_section and line.strip() and not line.strip().startswith('['):
                if not self._validate_icon_line(line):
                    self._log(f"[InnoSetup] [WARN] [Icons]段第{i+1}行格式不正确，将跳过: {line}")
                    lines[i] = ""

        script_content = '\n'.join(lines)

        with tempfile.NamedTemporaryFile(mode='w', suffix='.iss', delete=False, encoding='utf-8') as f:
            f.write(script_content)
            script_path = f.name

        self._log(f"[InnoSetup] 生成安装脚本: {script_path}")

        try:
            success = self.compile_installer(script_path)
            if success:
                setup_file = os.path.join(output_dir, f"{app_name}-{app_version}-setup.exe")
                if os.path.exists(setup_file):
                    file_size = os.path.getsize(setup_file)
                    self._log(f"[InnoSetup] 安装包已生成: {setup_file}")
                    self._log(f"[InnoSetup] 文件大小: {file_size / (1024 * 1024):.2f} MB")
            return success
        finally:
            if os.path.exists(script_path):
                try:
                    os.remove(script_path)
                    self._log(f"[InnoSetup] 已清理临时脚本文件")
                except OSError as e:
                    self._log(f"[InnoSetup] [WARN] 无法清理临时脚本: {e}")
            if converted_icon_path and os.path.exists(converted_icon_path):
                try:
                    os.remove(converted_icon_path)
                    self._log(f"[InnoSetup] 已清理临时图标文件")
                except OSError as e:
                    self._log(f"[InnoSetup] [WARN] 无法清理临时图标: {e}")