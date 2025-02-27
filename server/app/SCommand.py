# from datetime import datetime
# from flask import current_app
# from flask_socketio import emit
# from sqlalchemy import func
# from .models import db
# from .command_history import CommandHistory
# from .SDeviceMgr import SDeviceMgr, deviceMgr
# from .stask import STask, TaskState
# from scripts.logger import Log
# from pathlib import Path
# from .SEarningMgr import SEarningMgr
# import json

# class SCommand:
#     """服务器命令处理类"""
    
#     COMMANDS = {
#         '帮助': ('帮助信息', '_cmd_help'),
#         '状态': ('服务器状态', '_cmd_status'),
#         '清除': ('清除日志', '_cmd_clearLog'),
#         '设备列表': ('列出所有设备', '_cmd_list'),
#         '日志': ('手动打印日志', '_cmd_log'),
#         '进度': ('查询任务进度', '_cmd_progress'),
#         '继续': ('继续暂停任务', '_cmd_resume'),
#         '调试': ('显示调试信息', '_cmd_debug'),
#         '任务列表': ('显示任务', '_cmd_show_tasks'),
#         '设置日期': ('设置任务管理器日期', '_cmd_set_date'),
#         '停止': ('停止当前任务', '_cmd_stop'),
#         '保存结果': ('保存命令结果', 'saveResult'),
#         '分析收益': ('分析收益', 'analyzeEarnings'),
#         '打开应用': ('打开指定应用', '_cmd_openapp'),
#         '应用列表': ('列出所有应用', '_cmd_apps'),
#     }
    
#     # 注册所有命令
#     @classmethod
#     def register_commands(cls):
#         """注册所有命令"""
#         from .Server import cmdMgr
        
#         # 导入SCmds模块以确保命令被注册
#         from . import SCmds
   