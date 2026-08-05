<div align="center">
  <img src="readme_pic/architecture_overview.png" alt="cn_sort" width="640">

  # cn_sort

  快速、精确地按拼音或笔顺排序简体中文词组，支持百万量级。

  [![PyPI](https://img.shields.io/pypi/v/cn-sort?style=flat-square)](https://pypi.org/project/cn-sort/)
  [![Python](https://img.shields.io/pypi/pyversions/cn-sort?style=flat-square)](https://pypi.org/project/cn-sort/)
  [![Downloads](https://img.shields.io/pypi/dm/cn-sort?style=flat-square)](https://pypi.org/project/cn-sort/)
  [![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)](LICENSE)
  [![GitHub stars](https://img.shields.io/github/stars/bmxbmx3/cn_sort?style=flat-square)](https://github.com/bmxbmx3/cn_sort/stargazers)

  [**English**](README.md)
</div>

---

## 安装

```console
pip install cn-sort
```

需要 Python 3.6+，依赖（`pypinyin`、`jieba`）自动安装。

---

## 快速开始

```python
from cn_sort import sort_text_list, Mode

# 按拼音排序（默认）
sort_text_list(['唯依', '唯衣', '唯一', '啊'])
# → ['啊', '唯一', '唯衣', '唯依']

# 按笔顺排序
sort_text_list(['三', '二', '一', '一二'], mode=Mode.BIHUA)
# → ['一', '一二', '二', '三']

# 多音字自动识别
sort_text_list(['重要', '重庆'])
# → ['重庆', '重要']   （chóng < zhòng）

# 中英混排
sort_text_list(['中国', 'abc', '啊'])
# → ['abc', '啊', '中国']

# 百万词级别，自动启用多进程
sort_text_list(big_list, threshold=100_000)
```

---

## 特性

- **两种排序模式** — `Mode.PINYIN`（拼音+笔顺消歧）或 `Mode.BIHUA`（纯笔顺）
- **多音字智能处理** — `pypinyin` 根据词语上下文自动选择正确读音
- **百万词级别扩展** — 超过 `threshold` 自动切换多进程生产者-消费者架构
- **中英混排** — 非中文字符（字母、数字、标点）排在汉字前面
- **开箱即用** — 优先级表随包发布，无需额外下载数据

---

## API

### `sort_text_list(text_list, *, freeze=False, threshold=100_000, mode=Mode.PINYIN) → list[str]`

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `text_list` | `list[str]` | *必填* | 待排序词组列表 |
| `mode` | `Mode` | `Mode.PINYIN` | 排序模式 |
| `threshold` | `int` | `100_000` | 超过此数量时启用多进程 |
| `freeze` | `bool` | `False` | Windows 下非 `if __name__ == '__main__'` 调用时设 `True` |

### `Mode`

| 值 | 行为 |
|----|------|
| `Mode.PINYIN` | 按拼音排序，笔顺消歧 |
| `Mode.BIHUA` | 仅按笔顺排序 |

### `set_stdout_level(level: str) → bool`

设置控制台日志级别，`level` 可选 `"DEBUG"` / `"INFO"` / `"WARN"` / `"ERROR"` / `"CRITICAL"`。

---

## 算法原理

cn_sort 将每个词转换为整数优先级元组，再用 **LSD 基数排序**——从最后一列到第一列逐列用 Python timsort 稳定排序。

![拼音排序流程](readme_pic/pinyin_sort_flow.png)

1. **优先级表** — 2 万多个汉字按拼音+笔顺预先排好优先级，存入 `all_word.json`，查询 O(1)。
2. **词→元组** — 每个字通过拼音签名（如 `人_ren2`）查表，得到整数优先级。
3. **LSD 基数排序** — 用 `operator.itemgetter` 逐列原地排序，稳定性保证正确顺序。
4. **多音字** — `pypinyin` 自动根据词语上下文选择正确读音。

词组数量超过 `threshold` 时，启用多进程架构：

![多进程流水线](readme_pic/multiprocess_pipeline.png)

- **N 个生产者进程**（CPU 核数 - 1）：jieba 分词，去重，推入各自独立队列。
- **1 个消费者进程**：从所有队列收集词，建立优先级元组缓存。
- **主进程**：汇总分段结果，执行最终排序。

---

## 性能

| 规模 | 模式 | 耗时 |
|------|------|------|
| < 1 000 词 | 单进程 | < 5 ms |
| 10 000 词 | 单进程 | 约 180 ms |
| 1 000 000 词 | 多进程 | 约 20 s（4 核） |

大规模模式下，jieba 分词是主要瓶颈；替换为更快的分词器是最高性价比的优化方向。

---

## 贡献

```console
git clone https://github.com/bmxbmx3/cn_sort.git
cd cn_sort
pip install pypinyin jieba
```

1. Fork 仓库，创建功能分支：`git checkout -b feat/your-feature`
2. 修改代码，视情况添加测试。
3. 开启 Pull Request。

欢迎的贡献方向：繁体中文支持、pytest 测试套件、大规模分词提速。

---

## 许可证

[MIT](LICENSE) © bmxbmx3
