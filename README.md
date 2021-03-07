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

```shell
pip install cn_sort --upgrade
```

如果提示缺少依赖，运行以下命令：

```shell
pip install -r requirements.txt
```

# 使用

## 入门

基本用法如下：

```python
from cn_sort.process_cn_word import *

if __name__ == "__main__":
   # 先按拼音，再按笔顺排序
   text_list = ["重心", "河水", "重庆", "河流", "WTO世贸组织"]  # 待排序的中文词组列表
   result_text_list = list(sort_text_list(text_list, mode=Mode.PINYIN))  # mode=Mode.pinyin可以不写
   print(result_text_list)
   # 输出：
   # ['WTO世贸组织', '重庆', '河流', '河水', '重心']

   # 只按笔顺排序
   text_list = ["二", "重要", "三", "一二", "一", "22", "1", "a", "重庆"]  # 待排序的中文词组列表
   a = list(sort_text_list(mode=Mode.BIHUA))
   print(a)

   # 输出：
   # ['1', '22', 'a', '一', '一二', '二', '三', '重庆', '重要']
```

## 设置输出日志级别

```python
from cn_sort.process_cn_word import *

if __name__ == "__main__":
    set_stdout_level("CRITICAL")  # 日志级别：DEBUG、INFO、WARN、ERROR、CRITIAL
```

# 构思

cn_sort库的核心思想是基数排序，思想类似这篇提到的对英文单词的排序： [Java 实现 单词排序———基数排序](https://www.jianshu.com/p/3331930a90bf) 。

cn_sort库排序分两种模式：

* 模式一（默认）：对词从左往右逐字先对比拼音排序，当拼音相同时再对比笔顺的排序方式，如`["唯依","唯衣","唯一","啊"]`排序为`["啊","唯一", "唯衣", "唯依"]`。
* 模式二：对词从左往右逐字对比笔顺排序，如`["三","二","一","一二"]`排序为`["一","一二", "二", "三"]`。

cn_sort库分为词组量少（排序方式一）与词组量多（排序方式二）的排序方式，这两种方式默认的词组量阈值为100000。模式一分排序方式一与排序方式二，模式二只采用排序方式一。

核心算法位于./cn_sort/process_cn_word.py。

## 排序方式一

cn_sort库当词组量少时，包含最基本的排序功能。

对于模式一的基本思想如下图：

<div align="center">
  <img src="https://github.com/bmxbmx3/cn_sort/blob/master/readme_pic/%E8%AF%8D%E7%BB%84%E9%87%8F%E5%B0%91.png" width="60%"/>
  <br>词组量少时的排序思想</br>
  <br></br>
</div>

①每个词用pypinyin转化为拼音二维组。

②各字按其拼音和笔顺查表，转化为优先级二维组（列数以所有词的最大长度为界，短于该长度的词末尾补0）

③从最低位往最高位，对优先级二维数组纵向采用python的tim排序，横向采用基数排序。

④查表，将优先级二维数组恢复为排序好的词组。

对于模式二，只需把词组拆成字，再按笔顺转换成对应的优先级二维组即可，原理同上。

## 排序方式二

cn_sort库当词组量多时，采用多进程提高运算速度。先将词组量按cpu数-1来分段，用cpu数-1个生产者进程处理这分段后的词组量，为了提高运行速度，采用jieba分割并过滤出重复的词元，最后将这些词元放于1个消费者进程中，按词组量少时的情况排序，最后再按每个词间的'\n'
定位标志，重新恢复成排序好的词组。大体构思如下：

<div align="center">
  <img src="https://github.com/bmxbmx3/cn_sort/blob/master/readme_pic/%E8%AF%8D%E7%BB%84%E9%87%8F%E5%A4%9A.png" width="60%"/>
  <br>词组量多时的排序思想</br>
  <br></br>
</div>

为了便于对多进程处理中文排序的理解，我这里写了一个demo：

```python
from multiprocessing import *
from multiprocessing.pool import Pool
from openpyxl import Workbook
from time import *


# 这里替换为生产者与消费者进程，包括中文排序
def write_to_excel(num_split):
    index = num_split[0]  # 第index个进程
    num_list = num_split[1]  # 顺序分割后的数据量

    # 写入文件
    wb = Workbook()
    ws = wb.create_sheet("newSheet")
    for i in range(len(num_list)):
        ws.cell(row=i + 1, column=1).value = num_list[i]
    wb.save('test' + str(index) + '.xlsx')
    print("正在生成第" + str(index + 1) + "个文件")


if __name__ == "__main__":

    # 计算程序运行时间
    start_time = time()

    # 原始数据
    num = list(range(1, 1000000 + 1))

    # 分割数据量
    n = 100
    num_split = []
    quotient, remainder = divmod(len(num), n)
    for i in range(n):
        first_index = i * quotient
        end_index = (i + 1) * quotient if i < n - 1 else None
        temp = num[first_index:end_index]
        num_split.append([i, temp])

    # 多进程处理数据（耗尽cpu算力）
    cpu_n = cpu_count()  # 获取cpu数，控制进程量
    pool = Pool(cpu_n)
    for i in range(n):
        pool.apply_async(func=write_to_excel, args=(num_split[i],))
    pool.close()
    pool.join()

    end_time = time()
    print("耗时" + str(end_time - start_time))
```

在这个demo基础上，cn_sort库增添了生产者与消费者进程，以及进程间的通信。

当多进程任务切换频繁出现错误时，应将程序入口放在`if __name__=="__main__":`下执行，除此以外，sort_text_list函数的freeze参数应设置为True：

```python
if __name__ == "__main__":
    set_stdout_level("INFO")
    sort_text_list(["992", "3.", "2.", "重庆", "人民", "Awsl"] * 1000000, freeze=True)

    # 一百万词组量排序输出
    # 2021-03-02 16:36:45,611 - all - INFO - get_text_spit_list函数运行时间为0.182560s
    # 2021-03-02 16:36:48,230 - all - INFO - get_word_dict函数运行时间为0.222509s
    # 2021-03-02 16:37:00,198 - all - INFO - 分词进程1已切割8个不重复的词
    # 2021-03-02 16:37:00,314 - all - INFO - 分词进程9已切割8个不重复的词
    # 2021-03-02 16:37:00,327 - all - INFO - 分词进程5已切割8个不重复的词
    # 2021-03-02 16:37:00,389 - all - INFO - 分词进程3已切割8个不重复的词
    # 2021-03-02 16:37:00,390 - all - INFO - 分词进程10已切割8个不重复的词
    # 2021-03-02 16:37:00,397 - all - INFO - 分词进程2已切割8个不重复的词
    # 2021-03-02 16:37:00,417 - all - INFO - 分词进程4已切割8个不重复的词
    # 2021-03-02 16:37:00,490 - all - INFO - 分词进程11已切割8个不重复的词
    # 2021-03-02 16:37:00,493 - all - INFO - 分词进程6已切割8个不重复的词
    # 2021-03-02 16:37:00,558 - all - INFO - 分词进程7已切割8个不重复的词
    # 2021-03-02 16:37:00,598 - all - INFO - 分词进程8已切割8个不重复的词
    # 2021-03-02 16:37:00,598 - all - INFO - 分词总结果为7个不重复的词
    # 2021-03-02 16:37:02,306 - all - INFO - multiprocess_split_text_list函数运行时间为16.693209s
    # 2021-03-02 16:37:02,308 - all - INFO - hadle_seged_text_word函数运行时间为0.000000s
    # 2021-03-02 16:37:02,448 - all - INFO - sort_text_list函数运行时间为18.033616s
```

## 设置词组量阈值

如果你要更改使用排序方式一与排序方式二之间的词组量阈值，可对sort_text_list函数的threshold参数进行调整：

```python
from cn_sort.process_cn_word import *

if __name__ == "__main__":
    set_stdout_level("INFO")
    sort_text_list(["992", "人民", "Awsl"] * 100000, freeze=True, threshold=5000)

    # 所处理的词组量为3*100000=300000，大于阈值5000，此时cn_sort采用排序方式二
```

## 注意

pypinyin会将一个字的不同声调标注为这种形式：如“啊”字，四种声调及轻声标注为a（轻声）、a1（平声）、a2（上声）、a3（去声）、a4（入声）。

## 日志

cn_sort库保存了中文排序各函数运行的记录。

如果有找不到优先级的词，即pyinyin无法发现该词对应的拼音（表明该词有待收入优先级表中），该记录会存于当前文件夹下所生成的error.log中，显示示例如下：

```locale
2019-10-31 00:34:29,922 - error - ERROR - 无法找到词语“→
”中的拼音索引为“→”
2019-10-31 00:34:48,193 - error - ERROR - 无法找到词语“→
”中的拼音索引为“→”
2021-02-28 17:15:10,143 - error - ERROR - 无法找到词语“→
”中的拼音索引为“→”
``` 

如果你想观察cn_sort库各函数运行的时间等细节，该记录会存于当前文件夹下所生成的all.log中，显示示例如下：

```locale
2021-03-02 16:28:18,582 - all - INFO - multiprocess_split_text_list函数运行时间为19.873153s
2021-03-02 16:28:18,584 - all - INFO - hadle_seged_text_word函数运行时间为0.000000s
2021-03-02 16:28:18,727 - all - INFO - sort_text_list函数运行时间为21.789078s
2021-03-02 16:28:26,124 - all - INFO - radix_sort函数运行时间为2.552099s
2021-03-02 16:36:45,611 - all - INFO - get_text_spit_list函数运行时间为0.182560s
2021-03-02 16:36:48,230 - all - INFO - get_word_dict函数运行时间为0.222509s
2021-03-02 16:37:00,198 - all - INFO - 分词进程1已切割8个不重复的词
2021-03-02 16:37:00,314 - all - INFO - 分词进程9已切割8个不重复的词
2021-03-02 16:37:00,327 - all - INFO - 分词进程5已切割8个不重复的词
2021-03-02 16:37:00,389 - all - INFO - 分词进程3已切割8个不重复的词
2021-03-02 16:37:00,390 - all - INFO - 分词进程10已切割8个不重复的词
2021-03-02 16:37:00,397 - all - INFO - 分词进程2已切割8个不重复的词
2021-03-02 16:37:00,417 - all - INFO - 分词进程4已切割8个不重复的词
2021-03-02 16:37:00,490 - all - INFO - 分词进程11已切割8个不重复的词
2021-03-02 16:37:00,493 - all - INFO - 分词进程6已切割8个不重复的词
2021-03-02 16:37:00,558 - all - INFO - 分词进程7已切割8个不重复的词
2021-03-02 16:37:00,598 - all - INFO - 分词进程8已切割8个不重复的词
2021-03-02 16:37:00,598 - all - INFO - 分词总结果为7个不重复的词
```

# 效果（粗略计算）

试验环境（华硕，已用5年）：

* 系统：Windows 10专业版（64位）
* 处理器： Intel(R) Core(TM) i5-4200H CPU @ 2.80 GHz 2.79 GHz
* 已安装内存：12.0 GB

当词组量<=100000时，对于万级的词组量排序速度大概能控制在1-2秒，十万级的词组量大概能控制在5-10秒。

当词组量>100000时，对于百万级的词组量，排序速度可控制在15-30秒。

process_cn_word.py（含核心算法）主要函数运行时间测试如下：

```python
from cn_sort.process_cn_word import *

if __name__ == "__main__":
    set_stdout_level("INFO")
    print(list(sort_text_list(["awsl", ",wa", "重要", "重庆", "人民", "Awsl"])))

# 输出
# 2021-03-01 12:59:53,215 - all - INFO - handle_text_word函数运行时间为0.000000s
# 2021-03-01 12:59:53,218 - all - INFO - sort_text_list函数运行时间为0.003029s
# 2021-03-01 12:59:53,352 - all - INFO - get_word_dict函数运行时间为0.130002s
# 2021-03-01 12:59:53,355 - all - INFO - radix_sort函数运行时间为0.000000s
# [',wa', 'Awsl', 'awsl', '重庆', '人民', '重要']
```

可见cn_sort库主要耗时在对all_word表（字符优先级表，json文件）的I/O传输上（get_word_dict函数预先获取all_word表以用于排序）。

# 缺陷

此版（第一版）对汉字排序的基本思想，其实属于基数排序的一种：最低位优先基数排序。特别是这篇介绍基数排序相关算法的文章：[常见的五类排序算法图解和实现（多关键字排序：基数排序以及各个排序算法的总结）](https://www.cnblogs.com/kubixuesheng/p/4374225.html)
原来基数排序还有最高位基数排序算法、链式基数排序算法等。这让我突然意识到之前对词组转换为优先级二维组时补0的操作，可能反而给空间复杂度造成了负担，也许换成链式基数排序算法能解决这一问题，而且最高位基数排序算法我也未曾尝试过，想看一下后续如果用它相比最低位基数排序算法在时间复杂度上有没有较大的提升。

同时我也发现，受限于排序算法的稳定性，若词组中大量出现相同或者相近的词，以及词的长度出现某几个词很长而其余的词都很短的情况，程序运行的效率会严重下降。

我所查阅的资料中，算法导论含有用最高位基数排序算法（MSD）对英文单词逐级排序的描述：[Algorithms: String Sorts](https://www.informit.com/articles/article.aspx?p=2180073) 。
后面我会花点时间好好研究一下MSD的原理，看能否应用到第二版cn_sort库中。

# 表结构

预先收集好两万多个汉字的笔顺与拼音，并排序好汉字的优先级，存储于./cn_sort/res/chinese_words.db，为了pip安装时提高速度，将chinese_words.db精简为json文件，存于./cn_sort/res/all_word.json（预置的汉字优先级表）。

预置的汉字优先级表all_word.json，是采取以空间换时间的思想，将两万多个汉字罗列出它们按拼音和笔顺作标准共同排序下的优先级（对应all_word表中的evaluation_level字段），这样利用hash表的特性，对于一个字能迅速找出它的优先级，从而提高排序速度。

同时为了解决多音字排序的问题，比如`['重要','重庆']`排序为`['重庆','重要']`
，我顺带将一字多音（含轻声）的情况纳入汉字优先级表中，同时为了让cn_sort库更具通用性，all_word表也扩展收入了大小写字母、数字、标点符号等字符，将它们的优先级设在汉字的优先级之前，同时将pypinyin未能识别以及all_word表未收录的字的优先级标注为0（优先级最高）。

表结构如下：

<div align="center">
  <img src="https://github.com/bmxbmx3/cn_sort/blob/master/readme_pic/%E8%A1%A8%E6%A8%A1%E5%9E%8B.png" width="60%"/>
  <br>表模型</br>
  <br></br>
</div>

各表截图：

<div align="center">
  <img src="https://github.com/bmxbmx3/cn_sort/blob/master/readme_pic/pinyin%E8%A1%A8.png" width="60%"/>
  <br>pinyin表</br>
  <br></br>
</div>

<div align="center">
  <img src="https://github.com/bmxbmx3/cn_sort/blob/master/readme_pic/word_pinyin%E8%A1%A8.png" width="60%"/>
  <br>word_pinyin表</br>
  <br></br>
</div>

<div align="center">
  <img src="https://github.com/bmxbmx3/cn_sort/blob/master/readme_pic/bihua%E8%A1%A8.png" width="60%"/>
  <br>bihua表</br>
  <br></br>
</div>

<div align="center">
  <img src="https://github.com/bmxbmx3/cn_sort/blob/master/readme_pic/word%E8%A1%A8.png" width="60%"/>
  <br>word表</br>
  <br></br>
</div>

<div align="center">
  <img src="https://github.com/bmxbmx3/cn_sort/blob/master/readme_pic/all_word%E8%A1%A8.png" width="60%"/>
  <br>all_word表</br>
  <br></br>
</div>

我制作all_word表标注汉字加其他字符的优先级的基本思路：

1. 收集汉字所有可能的拼音，将它们按英文单词排序获得拼音的优先级，存于pinyin表中。
2. 收集两万多个汉字，将pinyin表中拼音的优先级标注在这些汉字上，存于word_pinyin表中。
3. 收集汉字所有可能的笔顺，将它们按笔顺数排序获得笔顺的优先级，存于bihua表中。
4. 按笔顺和拼音作为排序标准（拼音为主，笔顺为辅），排序两万多个汉字的优先级，存于word表中。同时为了区分多音字，将一字多音用“字_音”的标识符（对应word表中的signature字段）标明唯一的多音字，比如将“啊”表示为“啊_
   a”、“啊_a1”、“啊_a2”、“啊_a3”、“啊_a4”的标识符。
5. 将其他字符（大小写字母、数字、标点符号）的优先级与来自word表中汉字的优先级共同存入all_word表中。

# 引申

其实在设计第一版之前，我还见到一种最原始的中文排序思想，参考这篇文章：[Python 中文排序](https://www.jianshu.com/p/715c21c90919)
。这篇文章被转载了很多次，所贴链接的那篇文章作者我也不太确定是不是原作者，不过他的想法是对于两个词，先从前往后比较拼音的优先级，若拼音优先级相同再比较笔划的优先级，最后比较词长——这是很容易想到的一种中文排序思路，可以用于小规模的中文词汇的排序，但若规模放大，我试过这种排序的效率严重下降，正好自己那段时间学数据结构的知识，又重新设计了一种基数排序中文词汇的方法，万级的规模下效率相比原来有了进一步提升。

当然对这个词汇转化而来的优先级二维数组，还有一种加权排序的思想，如这篇文章：[英文字符串排序算法](https://www.cnblogs.com/Narule/p/12852317.html)
。即从词的开头往后依次对各位字赋予逐渐减少的权重（因为中文排序最原始的思想是从词的第一位往后比较，权重逐渐减少即重要程度从前往后依次降低），然后对词按所组成各字的优先级计算加权和，代表了该词的优先级，最后比较词的优先级即可达到词汇排序的效果。但是这种思想有些弊端，一是权重的选取可以是任意的，不好把握，二是各权值之间必须相差足够大，对词计算后的优先级才能有明显的区分——有点类似TOPSIS算法。碍于计算机对精度的处理，若权值取得不够好，中文排序也差强人意，但若权值相差足够大，万级数量的汉字按其优先级与权值相乘后反而可能会造成溢出。我不太推荐这种加权排序的思想。

也许有人会问我做这个按笔顺与拼音排序的库有什么用，直接按拼音排序有何不可？其实早年有人提出过按笔顺排序是中国特有的排序方式，特别是正式会议的名单中，姓名的排序按笔顺就显得有必要了。我所搜集到的相关资料如下：

* [汉字排序就按中国传统来](http://m.cfan.com.cn/pcarticle/110309)
* [汉字排序——笔画序之议](https://zhuanlan.zhihu.com/p/22474563https://zhuanlan.zhihu.com/p/22474563)
* [按姓氏笔画排序和按姓名笔画排序的规则是什么？](https://www.zhihu.com/question/50695431)
* [按笔画顺序排列是中国特色的名单排序方法](https://zhuanlan.zhihu.com/p/26652690)

也有很多人对这种排序进行过讨论，比如[按姓氏笔画排序在程序中是怎么实现的？](https://bbs.csdn.net/topics/200018185)

当然也有像如段首文字排序、字典的编纂、五笔打字等也会用到按笔顺的排序理念。

随着时代的进步，人们更习惯于打字代替手写，可能会慢慢忽略按笔顺排序的重要性，所以我的cn_sort库也兼具按拼音排序的功能，特别是设计成拼音为主、笔顺为辅的排序方式，以符合人们的习惯。

除此之外，由中文词汇的排序可以扩展到更通用的情况：一个元素同时有多个属性，这些属性按重要程度贡献了元素的排序优先级，一个对象由多个这样的元素按一定顺序组成，现在的要求是对多个对象从前往后按元素的优先级排序。在中文排序的例子中，对象是词，元素是汉字，字同时有拼音（包含多音字）和笔划这两种属性，且汉字以万计；在英文排序的例子中，对象是词，元素是字母，字母同时只有单词表中的顺序属性（大小写也可看做顺序这一属性），且字母只有26个——显然英文排序的情况要比中文排序简单的多，若是推广到中英文混合排序，即词汇中夹杂着汉字与字母，或者更复杂一些，再加上符号，情况变得更困难了，比如知乎的这个问题，涉及对牌照的排序：[要对汽车牌照进行链式基数排序，折半查找，按城市分块索引查找，要求使用顺序表、静态链表等数据结构。?](https://www.zhihu.com/question/27405561)
——就目前来看，词汇排序的首要任务是按所组成语素的优先级，把多个词汇转变成一个二维数组，后面的重点是选用什么样的方法对这个二维数组进行处理来达到词汇排序的效果。

# TODO

## 完善readme

* [ ] 更新表结构部分
* [ ] 介绍排序方式二的多进程机制

## 编程

* [ ] 尝试采用最高位基数排序算法提高速度
* [ ] 尝试采用链式基数排序算法节省空间
* [ ] 更新modify_db/new_chinese_words.db的数据

## 部署

* [ ] 更改项目为github action打包部署
* [ ] 迁移项目到gitee

# 声明

cn_sort库为本人（bmxbmx3）设计，若要转载readme.md中的内容或者调用本库，请注明引用或转载，侵权必究。
