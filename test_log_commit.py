#!/usr/bin/env python3
import sys
import os
sys.path.append('server/scripts')

# 强制刷新输出
def flush_print(msg):
    print(msg)
    sys.stdout.flush()

flush_print("=== 开始测试日志提交 ===")

# 设置环境
import _G
_G._G_.load(True)  # 设置为服务端模式

flush_print("环境设置完成")

# 初始化Flask应用
from SDatabase import Database
Database.init()

flush_print("Flask应用初始化完成")

# 导入日志模块
from _Log import _Log_

flush_print("日志模块导入完成")

# 测试日志添加
flush_print("开始添加日志...")
result = _Log_.add('测试日志提交功能', 'test', 'i')
flush_print(f"日志添加结果: {result}")

flush_print("=== 测试完成 ===") 