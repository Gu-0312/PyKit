import logging


class Logger(logging.Logger):
    def __init__(self, name="PyPacker"):
        super().__init__(name)
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(
            "[%(asctime)s] %(levelname)s: %(message)s", datefmt="%H:%M:%S"
        ))
        self.addHandler(handler)
        self.setLevel(logging.INFO)
        self.gui_callback = None

    def set_gui_callback(self, callback):
        self.gui_callback = callback

    def _log_with_gui(self, level, msg, *args, **kwargs):
        super()._log(level, msg, args, **kwargs)
        if self.gui_callback:
            self.gui_callback(msg)

    def info(self, msg, *args, **kwargs):
        self._log_with_gui(logging.INFO, msg, *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        self._log_with_gui(logging.WARNING, msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        self._log_with_gui(logging.ERROR, msg, *args, **kwargs)


_logger = None


def get_logger():
    global _logger
    if _logger is None:
        _logger = Logger()
    return _logger
