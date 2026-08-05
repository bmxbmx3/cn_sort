import json
import logging
import logging.config
import os
import re
from enum import Enum
from itertools import chain
from multiprocessing import Manager, Pool, cpu_count
from multiprocessing import freeze_support

import jieba
import pypinyin
from pypinyin import Style

from cn_sort.decorator import metric_time

current_package_path = os.path.dirname(os.path.abspath(__file__))
_log_path = os.path.join(current_package_path, "res", "logging.conf")
logging.config.fileConfig(_log_path)
logger_all = logging.getLogger("all")
logger_error = logging.getLogger("error")

# Cache the word dict to avoid re-reading JSON on every call.
_word_dict_cache: dict = {}


class Mode(Enum):
    PINYIN = 1  # sort by pinyin then stroke order
    BIHUA = 2   # sort by stroke order only


@metric_time
def get_word_dict(mode: Mode = Mode.PINYIN) -> dict:
    cache_key = mode.value
    if cache_key in _word_dict_cache:
        return _word_dict_cache[cache_key]

    word_dict: dict = {}
    all_word_json_path = os.path.join(current_package_path, "res", "all_word.json")
    with open(all_word_json_path, "r", encoding="utf-8") as f:
        entries = json.load(f)["all_word"]
        if mode == Mode.PINYIN:
            for entry in entries:
                word_dict[entry["signature"]] = entry["pinyin_and_stroke_level"]
        else:
            for entry in entries:
                word_dict[entry["chinese"]] = entry["stroke_increment_level"]

    _word_dict_cache[cache_key] = word_dict
    return word_dict


def get_evaluation_level_tuple(word: str, word_dict: dict, pattern: re.Pattern,
                               mode: Mode = Mode.PINYIN) -> tuple:
    evaluation_level_list = []

    if mode == Mode.PINYIN:
        def errors(x: str) -> str:
            return "no_chinese:" + x

        pinyin_list = pypinyin.pinyin(word, heteronym=False, style=Style.TONE3, errors=errors)

        cur_index = -1
        signature_list = []
        for item in pinyin_list:
            pinyin = item[0]
            pinyin_matches = pattern.findall(pinyin)
            if not pinyin_matches:
                cur_index += 1
                signature_list.append(word[cur_index] + "_" + pinyin)
            else:
                signature_list += list(pinyin_matches[0])
                cur_index += len(pinyin_matches[0])

        evaluation_level = 0
        for signature in signature_list:
            try:
                evaluation_level = word_dict[signature]
            except KeyError:
                logger_error.error("KEYERR_PINYIN: %s", word)
            finally:
                evaluation_level_list.append(evaluation_level)

    else:
        for character in word[:-1]:
            evaluation_level = 0
            try:
                evaluation_level = word_dict[character]
            except KeyError:
                logger_error.error("KEYERR_BIHUA: %s", character)
            finally:
                evaluation_level_list.append(evaluation_level)

    return tuple(evaluation_level_list)


def handle_text_process(text: str, queue, process_id: int):
    max_length = 0
    temp_text_list = []
    jieba.setLogLevel(20)
    seged_word_list = list(jieba.cut(text))

    word_set: set = set()
    for word in seged_word_list:
        if word != "\n":
            temp_text_list.append(word)
        else:
            current_length = len("".join(temp_text_list))
            if current_length > max_length:
                max_length = current_length
            temp_text_list.clear()

        if word not in word_set:
            word_set.add(word)
            queue.put(word)

    queue.put(None)
    logger_all.info("producer %d: %d unique words", process_id, len(word_set))
    return seged_word_list, max_length


def get_filter_word_evaluation_process(queue_list: list) -> dict:
    filter_word_dict: dict = {}
    word_dict = get_word_dict()
    queue_count = len(queue_list)
    word_list = [""] * queue_count
    pattern = re.compile(r"^no_chinese:(.*?)$")

    while True:
        if word_list.count(None) == queue_count:
            logger_all.info("consumer: %d unique words total", len(filter_word_dict))
            break
        for idx in range(queue_count):
            if word_list[idx] is not None:
                word = queue_list[idx].get()
                word_list[idx] = word
                if word is not None and word != "\n" and word not in filter_word_dict:
                    filter_word_dict[word] = get_evaluation_level_tuple(word, word_dict, pattern)

    return filter_word_dict


@metric_time
def multiprocess_split_text_list(text_split_list: list, freeze: bool = False):
    n = len(text_split_list)
    if freeze:
        freeze_support()

    with Manager() as manager:
        # Each producer gets its own independent Queue.
        # Bug fix: original code used [Manager().Queue()] * n which creates n aliases
        # of the same Queue object, causing all producers to share one queue.
        queue_list = [manager.Queue(maxsize=0) for _ in range(n)]

        process_fns = [handle_text_process] * n + [get_filter_word_evaluation_process]
        args_list = (
            [(text_split_list[i], queue_list[i], i + 1) for i in range(n)]
            + [(queue_list,)]
        )

        with Pool(n + 1) as pool:
            async_results = [
                pool.apply_async(func=process_fns[i], args=args_list[i])
                for i in range(n + 1)
            ]
            pool.close()
            pool.join()

        seged_word_list_lists = [async_results[i].get()[0] for i in range(n)]
        max_length_list = [async_results[i].get()[1] for i in range(n)]
        max_length = max(max_length_list)
        seged_word_iter = chain.from_iterable(seged_word_list_lists)
        filter_word_dict = async_results[n].get()

    return seged_word_iter, filter_word_dict, max_length


@metric_time
def hadle_seged_text_word(seged_text_word_iter, max_length: int, filter_word_dict: dict):
    evaluation_level_temp_list = []
    text_word_temp_list = []
    evaluation_level_list = []

    for word in seged_text_word_iter:
        if word == "\n":
            text_word_temp = "".join(text_word_temp_list)
            lack_length = max_length - len(text_word_temp)
            evaluation_level_temp_list.extend([0] * lack_length)
            evaluation_level_temp_list.append(text_word_temp)
            evaluation_level_list.append(tuple(evaluation_level_temp_list))
            text_word_temp_list.clear()
            evaluation_level_temp_list.clear()
        else:
            text_word_temp_list.append(word)
            evaluation_level_temp_list.extend(filter_word_dict[word])

    radix_sort(evaluation_level_list)
    for item in evaluation_level_list:
        yield item[-1].strip("\n")


@metric_time
def handle_text_word(text_list: list, mode: Mode = Mode.PINYIN):
    evaluation_level_list = []
    pattern = re.compile(r"^no_chinese:(.*?)$")
    word_dict = get_word_dict(mode)
    max_length = len(max(text_list, key=len))

    for word in text_list:
        level_tuple = get_evaluation_level_tuple(word, word_dict, pattern, mode)
        lack_length = max_length - len(word)
        combined = tuple(chain(level_tuple, [0] * lack_length, (word,)))
        evaluation_level_list.append(combined)

    radix_sort(evaluation_level_list)
    for item in evaluation_level_list:
        yield item[-1].strip("\n")


@metric_time
def radix_sort(data: list) -> None:
    if not data:
        return
    num_columns = len(data[0])
    for col in range(num_columns - 2, -1, -1):
        data.sort(key=lambda x: x[col])


@metric_time
def get_text_spit_list(text_list: list) -> list:
    n = cpu_count() - 1
    if n <= 1:
        logger_error.error("CPU count %d too low for multiprocess", n + 1)
        return None

    quotient, remainder = divmod(len(text_list), n)
    text_split_list = []
    for i in range(n):
        first_index = i * quotient
        end_index = (i + 1) * quotient if i < n - 1 else None
        text_split_list.append("".join(text_list[first_index:end_index]))
    return text_split_list


@metric_time
def sort_text_list(text_list: list, freeze: bool = False,
                   threshold: int = 100000, mode: Mode = Mode.PINYIN):
    if not text_list:
        return []

    text_list_with_sentinel = [word + "\n" for word in text_list]
    use_multiprocess = (len(text_list_with_sentinel) > threshold and mode == Mode.PINYIN)

    if not use_multiprocess:
        return list(handle_text_word(text_list_with_sentinel, mode))

    text_split_list = get_text_spit_list(text_list_with_sentinel)
    if text_split_list is None:
        logger_error.error("CPU count too low, falling back to single-process")
        return list(handle_text_word(text_list_with_sentinel, mode))

    try:
        seged_word_iter, filter_word_dict, max_length = multiprocess_split_text_list(
            text_split_list, freeze=freeze
        )
    except RuntimeError:
        logger_error.error("Multiprocess RuntimeError, falling back to single-process")
        return list(handle_text_word(text_list_with_sentinel, mode))

    return list(hadle_seged_text_word(seged_word_iter, max_length, filter_word_dict))


def set_stdout_level(level: str) -> bool:
    import configparser
    valid_levels = {"DEBUG", "INFO", "WARN", "ERROR", "CRITICAL"}
    if level not in valid_levels:
        return False
    logging_file_path = os.path.join(current_package_path, "res", "logging.conf")
    cfg = configparser.ConfigParser()
    cfg.read(logging_file_path, encoding="utf-8")
    with open(logging_file_path, "w", encoding="utf-8") as f:
        cfg.write(f)
    return True


if __name__ == "__main__":
    from time import time
    start_time = time()
    result = list(sort_text_list(
        ["中国人民", "中国人民銀行", "中国人"] * 100000,
        mode=Mode.PINYIN,
        threshold=1000,
    ))
    print(f"time: {time() - start_time:.2f}s, count: {len(result)}")
