from distutils.core import setup
setup(
    name="cn_sort",
    packages=["cn_sort"],
    version="0.1",
    license="MIT",
    description="按拼音和笔顺快速排序大量简体中文词组（支持百万数量级）。",
    author="bmxbmx3",
    author_email="982766639@qq.com",
    url="https://github.com/bmxbmx3/cn_sort/tree/master",
    download_url="https://github.com/bmxbmx3/cn_sort/archive/v0.1.zip",
    keywords=[
        "njupt",
        "排序",
        "中文",
        "拼音",
        "笔画",
        "词",
        "汉字",
        "chinese",
        "word",
        "sort",
        "pinyin",
        "pronounce",
        "bihua"
    ],
    install_requires=[
        "peewee",
        "pypinyin",
        "jieba"
    ],
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Build Tools",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
    ],
)