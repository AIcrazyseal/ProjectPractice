"""
import random
a = random.randint(0,100)
b = random.randint(0,100)
print("a=",a,"b=",b,"a*b=",a*b)
"""

import os
import sys
# 查看当前工作目录
print("当前工作目录:", os.getcwd())
# 列出当前目录的文件
print("当前目录的文件:", os.listdir('.'))

# 检查文件是否存在
if os.path.exists('a.txt'):
    print("文件存在")
else:
    print("文件不存在")
f = open('ProjectPractice/code/a.txt','r',encoding='utf-8')
s = f.readline()
print(s)


