from setuptools import setup,find_packages

with open("README.md", "r",encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="cn_sort",
    version="0.4.2b2",
    license="MIT",
    description="按拼音和笔顺快速排序大量简体中文词组（支持百万数量级）。",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="bmxbmx3",
    author_email="982766639@qq.com",
    url="https://github.com/bmxbmx3/cn_sort/tree/master",
    download_url="https://github.com/bmxbmx3/cn_sort/archive/0.4.2b2.tar.gz",
    keywords=[
        "njupt chinese word sort pronounce bihua 排序 中文 拼音 笔画 笔顺 词 汉字",
    ],
    install_requires=[
        "peewee",
        "pypinyin",
        "jieba"
    ],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Build Tools",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7"
    ],
    package_data={
        "cn_sort": ["res/*.db"]
    },
    package_dir={"": "cn_sort"},
    packages=find_packages("cn_sort"),
    python_requires=">=3.6"
)
