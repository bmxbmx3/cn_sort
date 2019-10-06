from peewee import *
import sqlite3
from cn_sort.decorator import *
from cn_sort.process_cn_word import *
import logging

# 这个模块主要用来操作chinese_words.db与chinese_words_backup.db。

db = SqliteDatabase("chinese_words.db")


class all_word(Model):
    """
    all_word表peewee模型。
    """
    signature = CharField(primary_key=True)
    evaluation_level = IntegerField(null=True)

    class Meta:
        database = db
        indexes = (
            (("signature", "evaluation_level"), True),
        )


class pinyin(Model):
    """
    pinyin表peewee模型。
    """
    pronounce = CharField(primary_key=True)
    pronounce_level = IntegerField(null=True)

    class Meta:
        database = db
        indexes = (
            (("pronounce", "pronounce_level"), True),
        )


class bihua(Model):
    """
    bihua表peewee模型。
    """
    chinese = CharField(primary_key=True)
    stroke_level = IntegerField()

    class Meta:
        database = db
        indexes = (
            (("chinese", "stroke_level"), True),
        )


class word(Model):
    """
    word表peewee模型。
    """
    chinese = CharField()
    pronounce_level = IntegerField(null=True)
    stroke_level = IntegerField(null=True)
    evaluation_level = IntegerField(null=True)
    signature = CharField(primary_key=True, null=True)

    class Meta:
        database = db
        indexes = (
            (("chinese",
              "pronounce_level",
              "stroke_level",
              "evaluation_level",
              "signature"),
             True),
        )


class word_pinyin(Model):
    """
    word_pinyin表peewee模型。
    """
    chinese = CharField()
    pronounce = CharField(null=True)
    pronounce_level = IntegerField(null=True)

    class Meta:
        database = db
        indexes = (
            (("chinese", "pronounce", "pronounce_level"), True),
        )


@metric_time
def batch_update(obj, data, fields, batch_size=100):
    """
    数据库批量更新。
    用法：
        # 批量更新word表中chinese字段的元素为"我"
        db.connect()
        data=[]        # 储存待更新的行记录。
        word_query=word.select()
        for row in word_query:
            row.chinese="我"        # 待更新的字段
            data.append(row)
        batch_update(word,data,fields=[word.chinese])       #批量更新
        db.close()
    :param obj: 表名。
    :param data:储存待更新的行记录。
    :param fields:待更新的字段名。
    :param batch_size:批量更新的记录的数量。
    :return:None。
    """
    with db.atomic():
        obj.bulk_update(data, fields=fields, batch_size=batch_size)
        logging.info("%s表已更新成功" % (obj.__name__))


@metric_time
def batch_insert(obj, data, batch_size=100):
    """
    数据库批量插入。
    用法：
        # 批量插入4条记录("zhidao",100)到pinyin表中
        db.connect()
        data=[]        # 储存待更新的行记录。
        for row in range(4):
            temp_data=("zhidao",100)        # 待插入的记录为元组格式，且从前往后分别对应表的字段
            data.append(temp_data)      # data批量保存要插入的记录
        batch_insert(pinyin,data)       # 批量插入
        db.close()
    :param obj: 表名
    :param data: 储存待插入的行记录。
    :param batch_size: 批量插入的记录的数量。
    :return: None。
    """
    with db.atomic():
        for batch in chunked(data, batch_size):
            obj.insert_many(batch).execute()
        logging.info("%s表已插入成功" % (obj.__name__))


@metric_time
def backup(src_name, dst_name):
    """
    备份数据库。
    用法：
        backup("chinese_words.db","chinese_words_backup.db")
    :param src_name:源数据库名。
    :param dst_name:目标数据库名。
    :return:None。
    """
    con = sqlite3.connect(src_name)
    bck = sqlite3.connect(dst_name)
    with bck:
        con.backup(bck)
    bck.close()
    con.close()
    logging.info("%s数据库成功备份到%s数据库" % (src_name, dst_name))


@db_connnect("chinese_words.db")
@metric_time
def get_word_dict():
    """
    获取所有字的索引表。
    :return: 所有字的索引表。
    """
    word_dict = {}
    all_word_query = all_word().select()
    for row in all_word_query:
        word_dict[row.signature] = row.evaluation_level
    return word_dict

# TODO:插入汉字及对应的读音到表中,该方法需进一步简化
@db_connnect
@metric_time
def insert_word(insert_chinese, insert_pronounce):
    insert_stroke_level = 0  # 待插入文字的笔顺对应的索引，由表查询得
    insert_evaluation_level = 0  # 待插入文字的对应评级索引，由表查询排序所得

    pinyin_dict = {
        row.pronounce: row.pronounce_level for row in pinyin.select()}  # 构建拼音的索引词典
    bihua_dict = {
        row.chinese: row.stroke_level for row in bihua.select()}  # 构建笔顺的索引词典
    evaluation_record_list = [
        (row.pronounce_level,
         row.stroke_level,
         row.signature) for row in word.select()]  # 构建所有发音的字由发音和笔顺对应的索引列表
    insert_signature = "".join(
        [insert_chinese, "_", insert_pronounce])  # 待插入文字的签名
    insert_pronounce_level = pinyin_dict[insert_pronounce]  # 待插入文字的拼音索引

    # 判断后续能否进行插入操作
    try:
        insert_stroke_level = bihua_dict[insert_chinese]
    except KeyError:
        logging.error("无法找到字”%s“在bihua表中的笔顺索引，不能实行插入操作" % word)
    else:
        word_data = []
        word_pinyin_data = []
        all_word_data = []

        # 插入到word_pinyin表中
        word_pinyin_data.append(
            (insert_chinese, insert_pronounce, insert_pronounce_level))
        try:
            batch_insert(word_pinyin, word_pinyin_data)
        except IntegrityError:
            logging.error("待插入的文字的相关信息已存在于word_pinyin表中")

        # 重排序后插入到word表中
        evaluation_record_list.append(
            (insert_pronounce_level,
             insert_stroke_level,
             insert_signature))  # 添加待插入的文字的索引记录
        radix_sort(evaluation_record_list)  # 重新排序所有词的索引列表
        insert_evaluation_level = evaluation_record_list.index(
            (insert_pronounce_level, insert_stroke_level, insert_signature)) + 1  # 获得待插入文字的索引
        word.delete().execute()  # 清空word表
        # 构建要插入的word_data
        for i in range(len(evaluation_record_list)):
            record = evaluation_record_list[i]
            signature = record[2]
            chinese = signature.split("_")[0]
            word_data.append((signature, chinese, record[0], record[1], i + 1))
        try:
            batch_insert(word, word_data)
        except IntegrityError:
            logging.error("待插入的文字的相关信息已存在于word表中")

        # 插入到all_word表中
        for i in range(len(evaluation_record_list)):
            a = evaluation_record_list[i]
            signature = a[2]
            evaluation_level = i + 97
            all_word_data.append((signature, evaluation_level))
        all_word.delete().where(all_word.evaluation_level >
                                96).execute()  # 将all_word表中除了ascii的所有字符删除
        try:
            batch_insert(all_word, all_word_data)
        except IntegrityError:
            logging.error("待插入的文字的相关信息已存在于all_word表中")
