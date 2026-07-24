import os
import subprocess
from utils.log_utils import get_logger
from utils.file_utils import ensure_dir_exists, get_file_name_without_ext, run_hidden


logger = get_logger()


class InstallerGenerator:
    NSIS_TEMPLATE = r'''!define APP_NAME "{app_name}"
!define APP_VERSION "{app_version}"
!define APP_PUBLISHER "{app_publisher}"
!define APP_EXE "{app_exe}"
!define INSTALL_DIR "$PROGRAMFILES\{app_name}"
!define OUTPUT_DIR "{output_dir}"

!include "MUI2.nsh"

!define MUI_ICON "{icon_path}"
!define MUI_UNICON "{icon_path}"

!define MUI_WELCOMEPAGE_TITLE "$(^Name) 安装向导"
!define MUI_WELCOMEPAGE_TEXT "欢迎使用 $(^Name) 安装向导。$\n$\n此向导将帮助您在计算机上安装 $(^Name)。"

!define MUI_FINISHPAGE_TITLE "安装完成"
!define MUI_FINISHPAGE_TEXT "$(^Name) 已成功安装到您的计算机。"
!define MUI_FINISHPAGE_RUN "$INSTDIR\${{APP_EXE}}"

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "SimpChinese"

Name "${{APP_NAME}}"
OutFile "${{OUTPUT_DIR}}\${{APP_NAME}}_Setup.exe"
InstallDir "${{INSTALL_DIR}}"
InstallDirRegKey HKLM "Software\${{APP_NAME}}" ""

Section "MainSection" SEC01
  SetOutPath "$INSTDIR"
  File /r "{source_dir}\*"
  WriteRegStr HKLM "Software\${{APP_NAME}}" "" "$INSTDIR"
  WriteRegStr HKLM "Software\${{APP_NAME}}" "Version" "${{APP_VERSION}}"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${{APP_NAME}}" "DisplayName" "${{APP_NAME}}"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${{APP_NAME}}" "UninstallString" "$INSTDIR\uninstall.exe"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${{APP_NAME}}" "DisplayVersion" "${{APP_VERSION}}"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${{APP_NAME}}" "Publisher" "${{APP_PUBLISHER}}"
SectionEnd

Section "Start Menu Shortcut" SEC02
  CreateDirectory "$SMPROGRAMS\${{APP_NAME}}"
  CreateShortCut "$SMPROGRAMS\${{APP_NAME}}\${{APP_NAME}}.lnk" "$INSTDIR\${{APP_EXE}}" "" "$INSTDIR\${{APP_EXE}}" 0
  CreateShortCut "$DESKTOP\${{APP_NAME}}.lnk" "$INSTDIR\${{APP_EXE}}" "" "$INSTDIR\${{APP_EXE}}" 0
SectionEnd

Section "Uninstall"
  Delete "$INSTDIR\uninstall.exe"
  RmDir "$INSTDIR"
  DeleteRegKey HKLM "Software\${{APP_NAME}}"
  DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${{APP_NAME}}"
  Delete "$SMPROGRAMS\${{APP_NAME}}\${{APP_NAME}}.lnk"
  RmDir "$SMPROGRAMS\${{APP_NAME}}"
  Delete "$DESKTOP\${{APP_NAME}}.lnk"
SectionEnd

Function un.onUninstSuccess
  MessageBox MB_ICONINFORMATION|MB_OK "$(^Name) 已成功卸载。"
FunctionEnd

Function un.onInit
  MessageBox MB_ICONQUESTION|MB_YESNO|MB_DEFBUTTON2 "确定要卸载 $(^Name) 吗？" IDYES +2
  Abort
FunctionEnd
'''

    def __init__(self):
        self.nsis_path = self._find_nsis()
        self.on_log = None
        self.on_progress = None
        if self.nsis_path:
            logger.info(f"[NSIS] NSIS路径: {self.nsis_path}")
            version = self.get_nsis_version()
            if version:
                logger.info(f"[NSIS] NSIS版本: {version}")
        else:
            logger.info("[NSIS] NSIS不可用，安装包生成功能已禁用")

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

    def _find_nsis(self):
        common_paths = [
            os.path.join(os.environ.get("PROGRAMFILES", "C:\\Program Files"), "NSIS", "makensis.exe"),
            os.path.join(os.environ.get("PROGRAMFILES(X86)", "C:\\Program Files (x86)"), "NSIS", "makensis.exe"),
            os.path.join(os.environ.get("LOCALAPPDATA", "C:\\Users\\Administrator\\AppData\\Local"), "Programs", "NSIS", "makensis.exe"),
            os.path.join("C:\\", "Program Files", "NSIS", "makensis.exe"),
            os.path.join("C:\\", "Program Files (x86)", "NSIS", "makensis.exe"),
            os.path.join("D:\\", "Program Files", "NSIS", "makensis.exe"),
            os.path.join("D:\\", "Program Files (x86)", "NSIS", "makensis.exe"),
            os.path.join("D:\\", "NSIS", "makensis.exe"),
            os.path.join("E:\\", "Program Files", "NSIS", "makensis.exe"),
            os.path.join("E:\\", "NSIS", "makensis.exe"),
        ]

        for path in common_paths:
            if os.path.exists(path):
                return path

        import subprocess
        try:
            result = subprocess.run(
                ["where", "makensis"],
                capture_output=True, text=True, timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            if result.returncode == 0 and result.stdout.strip():
                nsis_path = result.stdout.strip().split('\n')[0].strip()
                if os.path.exists(nsis_path):
                    return nsis_path
        except Exception:
            pass

        return None

    def is_available(self):
        return self.nsis_path is not None

    def set_nsis_path(self, path):
        if os.path.exists(path):
            self.nsis_path = path
            return True
        return False

    def generate_nsis_script(self, source_dir, output_dir, app_name=None, app_version="1.0.0",
                             app_publisher="Unknown", icon_path=""):
        self._log(f"[NSIS] 开始生成NSIS脚本")
        self._log(f"[NSIS] 源目录: {source_dir}")
        self._log(f"[NSIS] 输出目录: {output_dir}")

        if not os.path.exists(source_dir):
            logger.error(f"[NSIS] 源目录不存在: {source_dir}")
            return None

        if not ensure_dir_exists(output_dir):
            logger.error(f"[NSIS] 无法创建输出目录: {output_dir}")
            return None

        if app_name is None:
            app_name = get_file_name_without_ext(os.path.basename(source_dir))
            logger.debug(f"[NSIS] 使用目录名作为应用名: {app_name}")

        exe_files = [f for f in os.listdir(source_dir) if f.endswith(".exe")]
        if not exe_files:
            logger.error("[NSIS] 源目录中没有exe文件")
            return None

        app_exe = exe_files[0]
        logger.info(f"[NSIS] 应用名称: {app_name}")
        logger.info(f"[NSIS] 应用版本: {app_version}")
        logger.info(f"[NSIS] 发布者: {app_publisher}")
        logger.info(f"[NSIS] 主程序: {app_exe}")
        if icon_path:
            logger.info(f"[NSIS] 图标文件: {icon_path}")

        script_content = self.NSIS_TEMPLATE.format(
            app_name=app_name,
            app_version=app_version,
            app_publisher=app_publisher,
            app_exe=app_exe,
            source_dir=source_dir.replace("\\", "\\\\"),
            output_dir=output_dir.replace("\\", "\\\\"),
            icon_path=icon_path.replace("\\", "\\\\") if icon_path else ""
        )

        script_path = os.path.join(output_dir, f"{app_name}.nsi")
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(script_content)

        logger.info(f"[NSIS] NSIS脚本已生成: {script_path}")
        return script_path

    def build_installer(self, script_path):
        if not self.is_available():
            self._log("[NSIS] [ERROR] NSIS不可用，请安装NSIS或指定正确路径")
            return False

        if not os.path.exists(script_path):
            self._log(f"[NSIS] [ERROR] NSIS脚本不存在: {script_path}")
            return False

        self._log("[NSIS] 开始生成安装包")
        self._progress(10, "编译NSIS安装包...")

        try:
            result = run_hidden(
                [self.nsis_path, script_path],
                capture_output=True,
                timeout=300
            )

            if result.returncode == 0:
                self._log("[NSIS] 安装包生成成功")
                self._progress(90, "NSIS编译完成")

                app_name = get_file_name_without_ext(os.path.basename(script_path))
                output_dir = os.path.dirname(script_path)
                installer_path = os.path.join(output_dir, f"{app_name}_Setup.exe")
                if os.path.exists(installer_path):
                    installer_size = os.path.getsize(installer_path)
                    self._log(f"[NSIS] 安装包路径: {installer_path}")
                    self._log(f"[NSIS] 安装包大小: {installer_size / 1024:.2f} KB")

                return True
            else:
                self._log(f"[NSIS] [ERROR] 安装包生成失败，返回码: {result.returncode}")
                if result.stderr:
                    self._log(f"[NSIS] [ERROR] {result.stderr[:200]}")
                return False

        except subprocess.TimeoutExpired:
            self._log("[NSIS] [ERROR] 安装包生成超时(300秒)")
            return False
        except Exception as e:
            self._log(f"[NSIS] [ERROR] 安装包生成异常: {type(e).__name__}: {str(e)}")
            return False

    def create_installer(self, source_dir, output_dir, app_name=None, app_version="1.0.0",
                         app_publisher="Unknown", icon_path=""):
        self._log(f"[NSIS] 开始创建安装包")
        self._log(f"[NSIS]   源目录: {source_dir}")
        self._log(f"[NSIS]   输出目录: {output_dir}")

        script_path = self.generate_nsis_script(
            source_dir, output_dir, app_name, app_version, app_publisher, icon_path
        )

        if script_path is None:
            return False

        return self.build_installer(script_path)

    def get_nsis_version(self):
        if not self.is_available():
            return None

        try:
            result = run_hidden(
                [self.nsis_path, "/VERSION"],
                capture_output=True,
                timeout=10
            )

            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass

        return None