<div align="center">
  <img src="readme_pic/architecture_overview.png" alt="cn_sort" width="640">

  # cn_sort

  Fast, accurate sorting for Simplified Chinese word lists — by Pinyin or stroke order.

  [![PyPI](https://img.shields.io/pypi/v/cn-sort?style=flat-square)](https://pypi.org/project/cn-sort/)
  [![Python](https://img.shields.io/pypi/pyversions/cn-sort?style=flat-square)](https://pypi.org/project/cn-sort/)
  [![Downloads](https://img.shields.io/pypi/dm/cn-sort?style=flat-square)](https://pypi.org/project/cn-sort/)
  [![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)](LICENSE)
  [![GitHub stars](https://img.shields.io/github/stars/bmxbmx3/cn_sort?style=flat-square)](https://github.com/bmxbmx3/cn_sort/stargazers)

  [**简体中文**](README_CN.md)
</div>

---

## Installation

```console
pip install cn-sort
```

Requires Python 3.6+. Dependencies (`pypinyin`, `jieba`) are installed automatically.

---

## Quick start

```python
from cn_sort import sort_text_list, Mode

# Sort by Pinyin (default)
sort_text_list(['唯依', '唯衣', '唯一', '啊'])
# → ['啊', '唯一', '唯衣', '唯依']

# Sort by stroke order
sort_text_list(['三', '二', '一', '一二'], mode=Mode.BIHUA)
# → ['一', '一二', '二', '三']

# Polyphonic characters handled by context
sort_text_list(['重要', '重庆'])
# → ['重庆', '重要']   (chóng < zhòng)

# Mixed Chinese / Latin
sort_text_list(['中国', 'abc', '啊'])
# → ['abc', '啊', '中国']

# Million-scale: multiprocess kicks in automatically
sort_text_list(big_list, threshold=100_000)
```

---

## Features

- **Two modes** — `Mode.PINYIN` (pinyin + stroke tiebreaker) or `Mode.BIHUA` (stroke order only)
- **Polyphonic characters** — `pypinyin` uses surrounding context to pick the correct reading
- **Scales to 1M+ words** — auto-switches to a multiprocess producer-consumer pipeline above `threshold`
- **Mixed content** — Latin / numeric / punctuation sorts before CJK by default
- **Zero config** — no extra data downloads; priority table ships inside the package

---

## API

### `sort_text_list(text_list, *, freeze=False, threshold=100_000, mode=Mode.PINYIN) → list[str]`

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `text_list` | `list[str]` | *required* | Words to sort |
| `mode` | `Mode` | `Mode.PINYIN` | Sorting mode |
| `threshold` | `int` | `100_000` | Switch to multiprocess above this count |
| `freeze` | `bool` | `False` | Set `True` when calling outside `if __name__ == '__main__'` on Windows |

### `Mode`

| Value | Behaviour |
|-------|-----------|
| `Mode.PINYIN` | Sort by Pinyin reading; stroke order breaks ties |
| `Mode.BIHUA` | Sort by stroke count only |

### `set_stdout_level(level: str) → bool`

Set console log verbosity. `level` ∈ `{"DEBUG", "INFO", "WARN", "ERROR", "CRITICAL"}`.

---

## How it works

cn_sort converts each word into a tuple of integer priorities, then applies **LSD radix sort** — sorting from the last character column to the first using Python's stable timsort.

![Pinyin sort flow](readme_pic/pinyin_sort_flow.png)

1. **Priority table** — 20 000+ characters pre-ranked by Pinyin + stroke order, stored in `all_word.json` for O(1) lookup.
2. **Word → tuple** — each character maps to a signature (e.g. `人_ren2`) looked up in the table.
3. **LSD radix sort** — `operator.itemgetter` sorts each column in place; stable sort guarantees correct ordering.
4. **Polyphonic chars** — `pypinyin` selects the right reading from word context automatically.

For lists larger than `threshold`, cn_sort spawns a producer-consumer process pool:

![Multiprocess pipeline](readme_pic/multiprocess_pipeline.png)

- **N producer processes** (CPU count − 1): segment with jieba, deduplicate, push to independent queues.
- **1 consumer process**: collects tokens from all queues, builds a priority-tuple cache.
- **Main process**: reassembles segments, applies final radix sort.

---

## Performance

| Scale | Mode | Time |
|-------|------|------|
| < 1 000 words | single-process | < 5 ms |
| 10 000 words | single-process | ~180 ms |
| 1 000 000 words | multiprocess | ~20 s (4-core) |

The jieba segmentation step dominates large-scale runs. Replacing it with a faster segmenter is the highest-leverage future optimisation.

---

## Contributing

```console
git clone https://github.com/bmxbmx3/cn_sort.git
cd cn_sort
pip install pypinyin jieba
```

1. Fork the repo and create a branch: `git checkout -b feat/your-feature`
2. Make changes; add tests where applicable.
3. Open a Pull Request.

Good first contributions: Traditional Chinese support, a pytest test suite, faster large-scale segmentation.

---

## License

[MIT](LICENSE) © bmxbmx3
