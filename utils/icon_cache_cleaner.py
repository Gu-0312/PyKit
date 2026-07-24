"""
Windows图标缓存清理工具
用于解决打包后EXE图标不更新的问题
"""
import os
import subprocess
import sys
from utils.log_utils import get_logger

logger = get_logger()


class IconCacheCleaner:
    """清理Windows图标缓存，使EXE图标正确显示"""
    
    @staticmethod
    def clear_icon_cache():
        """清理Windows图标缓存"""
        if sys.platform != "win32":
            return False
        
        success = True
        
        # 方法1: 使用ie4uinit刷新图标缓存 (Windows 10/11)
        try:
            result = subprocess.run(
                ["ie4uinit.exe", "-show"],
                capture_output=True,
                timeout=10
            )
            logger.info(f"[IconCache] 刷新图标缓存: 返回码={result.returncode}")
        except FileNotFoundError:
            logger.debug("[IconCache] ie4uinit.exe 不存在，跳过")
        except Exception as e:
            logger.debug(f"[IconCache] ie4uinit.exe 执行失败: {e}")
        
        # 方法2: 删除图标缓存文件
        try:
            local_appdata = os.environ.get("LOCALAPPDATA", "")
            if local_appdata:
                # 删除IconCache.db
                icon_cache_path = os.path.join(local_appdata, "IconCache.db")
                if os.path.exists(icon_cache_path):
                    try:
                        os.remove(icon_cache_path)
                        logger.info(f"[IconCache] 已删除: {icon_cache_path}")
                    except PermissionError:
                        logger.debug(f"[IconCache] 文件被占用，跳过: {icon_cache_path}")
                
                # 删除Explorer缩略图缓存
                explorer_dir = os.path.join(local_appdata, "Microsoft", "Windows", "Explorer")
                if os.path.isdir(explorer_dir):
                    for filename in os.listdir(explorer_dir):
                        if filename.startswith("thumbcache_") and filename.endswith(".db"):
                            thumb_path = os.path.join(explorer_dir, filename)
                            try:
                                os.remove(thumb_path)
                                logger.info(f"[IconCache] 已删除缩略图缓存: {filename}")
                            except PermissionError:
                                logger.debug(f"[IconCache] 缩略图缓存被占用，跳过: {filename}")
        except Exception as e:
            logger.debug(f"[IconCache] 清理缓存文件失败: {e}")
        
        # 方法3: 刷新Shell图标缓存
        try:
            result = subprocess.run(
                ["cmd", "/c", "taskkill", "/f", "/im", "explorer.exe"],
                capture_output=True,
                timeout=5
            )
            if result.returncode == 0:
                # 等待一小段时间后重启Explorer
                import time
                time.sleep(0.5)
                subprocess.Popen(
                    ["cmd", "/c", "start", "explorer.exe"],
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                logger.info("[IconCache] 已重启Explorer以刷新图标缓存")
        except Exception as e:
            logger.debug(f"[IconCache] 重启Explorer失败（非致命）: {e}")
        
        return success
    
    @staticmethod
    def clear_folder_cache(folder_path):
        """清理指定文件夹的图标缓存（通过touch文件）"""
        if not os.path.isdir(folder_path):
            return
        
        # 创建desktop.ini文件以刷新图标显示
        desktop_ini = os.path.join(folder_path, "desktop.ini")
        try:
            if not os.path.exists(desktop_ini):
                with open(desktop_ini, "w", encoding="utf-16") as f:
                    f.write("[.ShellClassInfo]\n")
        except Exception:
            pass
