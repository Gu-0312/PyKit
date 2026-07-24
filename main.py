import sys
import ctypes


def set_dpi_awareness():
    try:
        if sys.platform == "win32":
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass


def main():
    set_dpi_awareness()

    from core.single_instance import SingleInstance
    instance = SingleInstance()
    if not instance.acquire():
        sys.exit(1)

    try:
        from app.application import Application
        from gui.main_window import MainWindow

        app = Application()
        window = MainWindow()
        window.show()
        sys.exit(app.exec())
    finally:
        instance.release()


if __name__ == "__main__":
    main()
