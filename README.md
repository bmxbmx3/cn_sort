# cn_sort

按拼音和笔顺快速排序大量简体中文词组（支持百万数量级，简体中文与非中文混用的词组也可）。

# 使用
```
from cn_sort.process_cn_word import *

text_list = ["人群", "河水", "人", "河流", "WTO世贸组织"]      # 待排序的中文词组列表
result_text_list=list(sort_text_list(text_list))        # 按拼音和笔顺排序后的中文字组列表
print(result_text_list)

# 输出为：
# ['WTO世贸组织', '河流', '河水', '人', '人群']
```