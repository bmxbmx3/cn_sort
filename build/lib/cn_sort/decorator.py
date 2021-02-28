import logging.config
import logging
from time import *
import os

# 这个模块主要用来放一些装饰器的函数。

# def set_log_cofig(func):
#     """
#     日志基本设置的装饰器。
#     :param func: 待包装的函数。
#     :return: None。
#     """
#     def wrapper(*args, **kwargs):
#         # 日志格式
#         LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
#         DATE_FORMAT = "%m/%d/%Y %H:%M:%S %process"
#         logging.basicConfig(
#             level=logging.INFO,
#             format=LOG_FORMAT,
#             datefmt=DATE_FORMAT)
#         return func(*args, **kwargs)
#     return wrapper


# @set_log_cofig
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
        current_package_path = os.path.dirname(os.path.abspath(__file__))  # 获得当前包所在的绝对路径，很重要！！！识别不出来就很麻烦
        logging.config.fileConfig("".join([current_package_path,"\\res\\logging.conf"]))
        logger_all=logging.getLogger("all")
        logger_all.info("%s函数运行时间为%fs" % (func.__name__, end_time - start_time))
        return result
    return wrapper