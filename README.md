# cn_sort

按拼音、笔顺和词的字数精确、快速排序大量简体中文词组（支持百万数量级，简体中文与非中文混用的词组也可），有效解决多音字混排的问题。

# 安装

适用于3.6+的python版本。

依赖：
+ jieba
+ pypinyin

pip命令：

```
pip install cn_sort --upgrade
```

# 使用

```
from cn_sort.process_cn_word import *

text_list = ["重心", "河水", "重庆", "河流", "WTO世贸组织"]      # 待排序的中文词组列表
result_text_list=list(sort_text_list(text_list))        # 按拼音和笔顺排序后的中文字组列表
print(result_text_list)

# 输出为：
# ['WTO世贸组织', '重庆', '河流', '河水', '重心']
```

具体使用见函数注释。
