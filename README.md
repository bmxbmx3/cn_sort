<div align="center">

# cn_sort

**Fast, accurate Chinese word sorting by Pinyin or stroke order**

*快速、精确地按拼音或笔顺排序简体中文词组*

[![PyPI version](https://img.shields.io/pypi/v/cn-sort.svg?style=flat-square)](https://pypi.org/project/cn-sort/)
[![Python versions](https://img.shields.io/pypi/pyversions/cn-sort.svg?style=flat-square)](https://pypi.org/project/cn-sort/)
[![Downloads](https://img.shields.io/pypi/dm/cn-sort.svg?style=flat-square)](https://pypi.org/project/cn-sort/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)](https://opensource.org/licenses/MIT)
[![GitHub stars](https://img.shields.io/github/stars/bmxbmx3/cn_sort.svg?style=flat-square)](https://github.com/bmxbmx3/cn_sort/stargazers)

[Installation](#installation) · [Quick Start](#quick-start) · [API](#api-reference) · [How It Works](#how-it-works) · [Contributing](#contributing)

</div>

---

## Overview

`cn_sort` sorts Simplified Chinese word lists by **Pinyin** (with stroke order as tiebreaker) or **stroke order** alone. It handles polyphonic characters correctly using context-aware pinyin detection, and scales to millions of words via a multi-process pipeline.

> 支持百万量级中文词组排序，多音字自动识别，中英混排均可处理。

```python
from cn_sort import sort_text_list, Mode

sort_text_list(['唯依', '唯衣', '唯一', '啊'])
# → ['啊', '唯一', '唯衣', '唯依']

sort_text_list(['重要', '重庆'])
# → ['重庆', '重要']  ✓ polyphonic: chóng vs zhòng
```

---

## Features

| Feature | Details |
|---------|---------|
| 🔤 **Pinyin sort** | Tone-aware, uses context to pick correct reading for polyphonic chars |
| ✍️ **Stroke-order sort** | Pure stroke-count ordering (Mode.BIHUA) |
| ⚡ **Scales to 1M+ words** | Auto-switches to multiprocess producer-consumer pipeline |
| 🔡 **Mixed content** | Latin / numeric / CJK all handled; non-CJK sorts before CJK |
| 📦 **Zero config** | `pip install cn-sort` — no extra data downloads needed |

---

## Installation

```bash
pip install cn-sort
```

**Requirements:** Python 3.6+, `pypinyin`, `jieba` (installed automatically)

---

## Quick Start

```python
from cn_sort import sort_text_list, Mode

# --- Pinyin mode (default) ---
sort_text_list(['唯依', '唯衣', '唯一', '啊'])
# ['啊', '唯一', '唯衣', '唯依']

# --- Stroke-order mode ---
sort_text_list(['三', '二', '一', '一二'], mode=Mode.BIHUA)
# ['一', '一二', '二', '三']

# --- Polyphonic character handling ---
sort_text_list(['重要', '重庆'])
# ['重庆', '重要']   (chóng < zhòng)

# --- Mixed Chinese / English ---
sort_text_list(['中国', 'abc', '啊'])
# ['abc', '啊', '中国']

# --- Large-scale: multiprocess kicks in automatically ---
sort_text_list(my_million_word_list)   # threshold=100000 by default
```

---

## API Reference

### `sort_text_list(text_list, freeze=False, threshold=100000, mode=Mode.PINYIN) → list[str]`

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `text_list` | `list[str]` | *required* | Words to sort |
| `mode` | `Mode` | `Mode.PINYIN` | `PINYIN` or `BIHUA` |
| `threshold` | `int` | `100_000` | Switch to multiprocess above this count |
| `freeze` | `bool` | `False` | Set `True` when calling outside `if __name__ == '__main__'` on Windows |

### `set_stdout_level(level: str) → bool`

Set console log verbosity. `level` ∈ `{"DEBUG", "INFO", "WARN", "ERROR", "CRITICAL"}`.

### `Mode` (enum)

| Value | Meaning |
|-------|---------|
| `Mode.PINYIN` | Sort by Pinyin reading, stroke order as tiebreaker |
| `Mode.BIHUA` | Sort by stroke count only |

---

## How It Works

cn_sort uses **LSD Radix Sort** — each word is converted to a tuple of integer priorities, then sorted column-by-column (last character first) using Python's stable timsort.

![Architecture Overview](readme_pic/architecture_overview.png)

### Step-by-step (Pinyin mode)

![Pinyin Sort Flow](readme_pic/pinyin_sort_flow.png)

1. **Priority table** — 20 000+ characters pre-ranked by pinyin + stroke order, stored in `all_word.json` for O(1) hash lookup
2. **Word → tuple** — each character maps to `char_pinyin` signature (e.g. `人_ren2`), looked up in the table
3. **LSD radix sort** — sort from least-significant column to most-significant using `operator.itemgetter` for speed
4. **Polyphonic chars** — `pypinyin` uses surrounding context to pick the correct reading automatically

![Radix Sort Diagram](readme_pic/radix_sort_diagram.png)

### Stroke-order mode

![Stroke Sort Flow](readme_pic/stroke_sort_flow.png)

Characters are ranked by their stroke increment level instead of pinyin signature. No jieba dependency needed.

### Large-scale multiprocess pipeline

When `len(words) > threshold`, cn_sort spawns a producer-consumer process pool:

![Multiprocess Pipeline](readme_pic/multiprocess_pipeline.png)

- **N producer processes** (one per CPU − 1): segment text with jieba, deduplicate, push to independent queues
- **1 consumer process**: reads all queues, builds a priority-tuple cache for every unique token
- **Main process**: reassembles segments using the cache, applies final radix sort

### Priority table schema

![Priority Table](readme_pic/word_priority_table.png)

---

## Performance

![Benchmark](readme_pic/benchmark_chart.png)

| Scale | Mode | Time |
|-------|------|------|
| < 1 000 words | single-process | < 5 ms |
| 10 000 words | single-process | ~180 ms |
| 1 000 000 words | multiprocess | ~20 s (4-core) |

*README note: the jieba segmentation step dominates large-scale runs. Replacing jieba with a faster segmenter would be the highest-leverage future optimisation.*

### Polyphonic example

![Polyphonic Example](readme_pic/polyphonic_example.png)

---

## Dependencies

| Package | Purpose |
|---------|---------|
| [pypinyin](https://github.com/mozillazg/python-pinyin) | Context-aware hanzi → pinyin conversion |
| [jieba](https://github.com/fxsjy/jieba) | Chinese word segmentation (multiprocess mode only) |

---

## Contributing

Contributions are welcome! Here's how to get started:

```bash
git clone https://github.com/bmxbmx3/cn_sort.git
cd cn_sort
pip install pypinyin jieba
```

1. Fork the repo and create a feature branch: `git checkout -b feat/your-feature`
2. Make your changes and add tests if applicable
3. Open a Pull Request — describe what you changed and why

**Good first issues:** improving large-scale performance, adding Traditional Chinese support, writing a test suite.

---

## License

[MIT](LICENSE) © bmxbmx3
