import logging
import logging.config
import os
from functools import wraps
from time import time

current_package_path = os.path.dirname(os.path.abspath(__file__))
_log_path = os.path.join(current_package_path, "res", "logging.conf")
logging.config.fileConfig(_log_path)
_logger_decorator = logging.getLogger("all")


def metric_time(func):
    """Log the execution time of the decorated function."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time()
        result = func(*args, **kwargs)
        _logger_decorator.info("%s函数运行时间为%fs", func.__name__, time() - start)
        return result
    return wrapper
