from time import *
import functools
from peewee import *
import logging

# 这个模块主要用来放一些装饰器的函数。


def db_connnect(text):
    """
    连接sqlite数据库的装饰器。
    :param text: 要连接的数据库名。
    :return: None。
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            db = SqliteDatabase(text)
            db.connect()
            result = func(*args, **kwargs)
            db.close()
            return result
        return wrapper
    return decorator


def set_log_cofig(func):
    """
    日志基本设置的装饰器。
    :param func: 待包装的函数。
    :return: None。
    """
    def wrapper(*args, **kwargs):
        # 日志格式
        LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
        DATE_FORMAT = "%m/%d/%Y %H:%M:%S %process"
        logging.basicConfig(
            level=logging.INFO,
            format=LOG_FORMAT,
            datefmt=DATE_FORMAT)
        return func(*args, **kwargs)
    return wrapper


@set_log_cofig
def metric_time(func):
    """
    测量函数运行时间的装饰器。
    :param func:待包装的函数。
    :return: None。
    """
    def wrapper(*args, **kwargs):
        start_time = time()
        result = func(*args, **kwargs)
        end_time = time()
        logging.info("%s函数运行时间为%fs" % (func.__name__, end_time - start_time))
        return result
    return wrapper
