# cn_sort

按拼音和笔顺精确、快速排序大量简体中文词组（支持百万数量级，简体中文与非中文混用的词组也可），有效解决多音字混排的问题。

# 依赖

运行python版本：
+ 3.6+

本项目涉及以下依赖：
+ jieba
+ pypinyin

# 安装

pip安装命令：

```
pip install cn_sort --upgrade
```

如果提示缺少依赖，运行以下命令：

```
pip install -r requirements.txt
```

# 使用

## 入门

```
from cn_sort.process_cn_word import *

text_list = ["重心", "河水", "重庆", "河流", "WTO世贸组织"]      # 待排序的中文词组列表
result_text_list=list(sort_text_list(text_list))        # 按拼音和笔顺排序后的中文字组列表
print(result_text_list)

# 输出为：
# ['WTO世贸组织', '重庆', '河流', '河水', '重心']
```

## 设置输出日志级别

```
set_stdout_level("CRITICAL")        # 日志级别：DEBUG、INFO、WARN、ERROR、CRITIAL
```

# 构思



# 来源

待补充。


# 缺陷

待补充。


# 表结构

待补充。

