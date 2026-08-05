import json
import logging
import logging.config
import operator
import os
import re
from enum import Enum
from itertools import chain
from multiprocessing import Process, Queue, cpu_count
from multiprocessing import freeze_support

import numpy as np
import pypinyin
from pypinyin import Style

from cn_sort.decorator import metric_time

current_package_path = os.path.dirname(os.path.abspath(__file__))
_log_path = os.path.join(current_package_path, "res", "logging.conf")
logging.config.fileConfig(_log_path)
logger_all = logging.getLogger("all")
logger_error = logging.getLogger("error")

_word_dict_cache: dict = {}
_pinyin_cache: dict = {}
_NO_CHINESE_PATTERN = re.compile(r"^no_chinese:(.*?)$")

# Batch size for queue IPC -- sends words in chunks to cut round-trips
_QUEUE_BATCH = 500


class Mode(Enum):
    PINYIN = 1
    BIHUA = 2


@metric_time
def get_word_dict(mode: Mode = Mode.PINYIN) -> dict:
    cache_key = mode.value
    if cache_key in _word_dict_cache:
        return _word_dict_cache[cache_key]

    word_dict: dict = {}
    all_word_json_path = os.path.join(current_package_path, "res", "all_word.json")
    with open(all_word_json_path, "r", encoding="utf-8") as f:
        import json as _json
        entries = _json.load(f)["all_word"]
        if mode == Mode.PINYIN:
            for entry in entries:
                word_dict[entry["signature"]] = entry["pinyin_and_stroke_level"]
        else:
            for entry in entries:
                word_dict[entry["chinese"]] = entry["stroke_increment_level"]

    _word_dict_cache[cache_key] = word_dict
    return word_dict


def _get_pinyin(word: str) -> list:
    if word not in _pinyin_cache:
        def errors(x: str) -> str:
            return "no_chinese:" + x
        _pinyin_cache[word] = pypinyin.pinyin(
            word, heteronym=False, style=Style.TONE3, errors=errors
        )
    return _pinyin_cache[word]


def get_evaluation_level_tuple(word: str, word_dict: dict,
                               mode: Mode = Mode.PINYIN) -> tuple:
    evaluation_level_list = []

    if mode == Mode.PINYIN:
        pinyin_list = _get_pinyin(word)
        cur_index = -1
        signature_list = []
        for item in pinyin_list:
            pinyin = item[0]
            pinyin_matches = _NO_CHINESE_PATTERN.findall(pinyin)
            if not pinyin_matches:
                cur_index += 1
                signature_list.append(word[cur_index] + "_" + pinyin)
            else:
                signature_list += list(pinyin_matches[0])
                cur_index += len(pinyin_matches[0])

        for signature in signature_list:
            evaluation_level = 0
            try:
                evaluation_level = word_dict[signature]
            except KeyError:
                logger_error.error("KEYERR_PINYIN: %s", word)
            evaluation_level_list.append(evaluation_level)

    else:
        for character in word[:-1]:
            evaluation_level = 0
            try:
                evaluation_level = word_dict[character]
            except KeyError:
                logger_error.error("KEYERR_BIHUA: %s", character)
            evaluation_level_list.append(evaluation_level)

    return tuple(evaluation_level_list)


def handle_text_process(text: str, queue: Queue, process_id: int):
    """Producer: split on newline sentinel (skip jieba), batch-send unique tokens.

    Words in text are already separated by \\n (added by sort_text_list).
    Splitting directly is 2-4x faster than jieba.cut() which would reload
    its dictionary in every worker process.
    """
    # Re-attach \\n so downstream consumers see the same sentinel format
    # that the original jieba path produced.
    raw_tokens = text.split("\n")
    seged_word_list = []
    for tok in raw_tokens:
        if tok:
            seged_word_list.append(tok + "\n")
        else:
            seged_word_list.append("\n")

    max_length = 0
    word_set: set = set()
    batch = []
    for word in seged_word_list:
        clean = word.rstrip("\n")
        if clean and len(clean) > max_length:
            max_length = len(clean)
        if word not in word_set:
            word_set.add(word)
            batch.append(word)
            if len(batch) >= _QUEUE_BATCH:
                queue.put(batch)
                batch = []

    if batch:
        queue.put(batch)
    queue.put(None)  # sentinel

    logger_all.info("producer %d: %d unique words", process_id, len(word_set))
    return seged_word_list, max_length


def get_filter_word_evaluation_process(queue_list: list, result_queue: Queue):
    """Consumer: drain batched queues, build priority-tuple cache."""
    filter_word_dict: dict = {}
    word_dict = get_word_dict()
    queue_count = len(queue_list)
    done = [False] * queue_count

    while not all(done):
        for idx in range(queue_count):
            if done[idx]:
                continue
            item = queue_list[idx].get()
            if item is None:
                done[idx] = True
            else:
                # item is a batch list
                for word in item:
                    if word is not None and word != "\n" and word.strip("\n"):
                        clean = word.rstrip("\n")
                        if clean and clean not in filter_word_dict:
                            filter_word_dict[clean] = get_evaluation_level_tuple(clean, word_dict)

    logger_all.info("consumer: %d unique words total", len(filter_word_dict))
    result_queue.put(filter_word_dict)


def _producer_worker(text: str, queue: Queue, process_id: int, result_queue: Queue):
    seged, max_len = handle_text_process(text, queue, process_id)
    result_queue.put((process_id, seged, max_len))


@metric_time
def multiprocess_split_text_list(text_split_list: list, freeze: bool = False):
    """Fan-out with Process+Queue (no Manager), jieba-free, batch IPC."""
    n = len(text_split_list)
    if freeze:
        freeze_support()

    queues = [Queue(maxsize=0) for _ in range(n)]
    producer_result_q = Queue()
    consumer_result_q = Queue()

    producers = [
        Process(target=_producer_worker,
                args=(text_split_list[i], queues[i], i + 1, producer_result_q))
        for i in range(n)
    ]
    consumer = Process(target=get_filter_word_evaluation_process,
                       args=(queues, consumer_result_q))

    consumer.start()
    for p in producers:
        p.start()

    producer_results = {}
    for _ in range(n):
        pid, seged, max_len = producer_result_q.get()
        producer_results[pid] = (seged, max_len)

    for p in producers:
        p.join()
    consumer.join()

    filter_word_dict = consumer_result_q.get()
    seged_word_list_lists = [producer_results[i + 1][0] for i in range(n)]
    max_length = max(producer_results[i + 1][1] for i in range(n))
    seged_word_iter = chain.from_iterable(seged_word_list_lists)

    return seged_word_iter, filter_word_dict, max_length


@metric_time
def hadle_seged_text_word(seged_text_word_iter, max_length: int, filter_word_dict: dict):
    """Map tokens to priority tuples and sort with numpy lexsort."""
    evaluation_level_temp_list = []
    text_word_temp_list = []
    rows = []        # list of (priority_tuple, original_word)
    words_out = []   # store original words in row order

    for word in seged_text_word_iter:
        if word.endswith("\n"):
            # This word token carries the \n sentinel — it IS a complete word.
            clean = word.rstrip("\n")
            if clean and clean in filter_word_dict:
                evaluation_level_temp_list.extend(filter_word_dict[clean])
                lack_length = max_length - len(clean)
                evaluation_level_temp_list.extend([0] * lack_length)
                rows.append(tuple(evaluation_level_temp_list))
                words_out.append(clean)
                evaluation_level_temp_list.clear()

    if not rows:
        return

    # numpy lexsort: sort by last key first (same semantics as LSD radix)
    num_cols = len(rows[0])
    if num_cols > 0:
        keys = np.array([[row[col] for row in rows] for col in range(num_cols - 1, -1, -1)],
                        dtype=np.int32)
        order = np.lexsort(keys)
        for i in order:
            yield words_out[i]
    else:
        yield from words_out


@metric_time
def handle_text_word(text_list: list, mode: Mode = Mode.PINYIN):
    """Single-process sort using numpy lexsort for the final ordering step."""
    word_dict = get_word_dict(mode)
    max_length = len(max(text_list, key=len))

    rows = []
    words_out = []
    for word in text_list:
        level_tuple = get_evaluation_level_tuple(word, word_dict, mode)
        lack_length = max_length - len(word)
        padded = level_tuple + (0,) * lack_length
        rows.append(padded)
        words_out.append(word.strip("\n"))

    if not rows:
        return

    num_cols = len(rows[0])
    if num_cols > 0:
        keys = np.array([[row[col] for row in rows] for col in range(num_cols - 1, -1, -1)],
                        dtype=np.int32)
        order = np.lexsort(keys)
        for i in order:
            yield words_out[i]
    else:
        yield from words_out


@metric_time
def radix_sort(data: list) -> None:
    """Legacy in-place sort kept for API compatibility; numpy path used internally."""
    if not data:
        return
    num_columns = len(data[0])
    for col in range(num_columns - 2, -1, -1):
        data.sort(key=operator.itemgetter(col))


@metric_time
def get_text_spit_list(text_list: list) -> list:
    n = cpu_count() - 1
    if n <= 1:
        logger_error.error("CPU count %d too low for multiprocess", n + 1)
        return None

    quotient, _ = divmod(len(text_list), n)
    text_split_list = []
    for i in range(n):
        first_index = i * quotient
        end_index = (i + 1) * quotient if i < n - 1 else None
        text_split_list.append("".join(text_list[first_index:end_index]))
    return text_split_list


@metric_time
def sort_text_list(text_list: list, freeze: bool = False,
                   threshold: int = 100000, mode: Mode = Mode.PINYIN):
    """Sort a list of Chinese words by pinyin or stroke order.

    Args:
        text_list: Words to sort, e.g. ["人", "人民"].
        freeze: Set True when calling outside if __name__ == '__main__' on Windows.
        threshold: Switch to multiprocess above this count (default 100000).
        mode: Mode.PINYIN or Mode.BIHUA.

    Returns:
        Sorted list of strings.
    """
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
