from datetime import datetime
import _G
from _G import TaskState
import _Log
from sqlalchemy import func
from typing import List, Optional
from SModelBase import SModelBase_
from SModels import TaskModel


class STask_(SModelBase_):
    """服务端任务类"""
    # 任务缓存
    _cache = []  # 任务列表
    _lastDate = None  # 最近一次缓存的日期

    def __init__(self, deviceId: str, name: str):
        """初始化任务"""
        super().__init__(TaskModel, {'deviceId': deviceId, 'name': name})
        
    @property
    def deviceMgr(self):
        from SDeviceMgr import deviceMgr
        return deviceMgr
    
    @property
    def state(self):
        return self.getDBProp('state')
    
    @property
    def progress(self):
        return self.getDBProp('progress')
    
    @property
    def score(self):
        return self.getDBProp('score')
    
    @property
    def life(self):
        return self.getDBProp('life')
    
    def start(self):
        """开始任务"""
        self.update({'state': TaskState.RUNNING.value})
        _Log._Log_.i(f'任务启动: {self.id}-{self.name}')


    @classmethod
    def get(cls, deviceId: str, name: str, date=None, create: bool = False) -> Optional['STask_']:
        """
        获取指定设备、应用的某天任务
        :param deviceId: 设备ID
        :param taskName: 任务名称
        :param date: 日期，默认为今天
        :param create: 不存在时是否创建
        :return: 任务对象或None
        """
        log = _Log._Log_
        if deviceId is None:
            log.e('获取任务失败', f'设备ID为空: {deviceId}-{name}')
            return None
        if date is None:
            date = datetime.now().date()
        # 先从缓存查找
        task = next((t for t in cls._cache if t.deviceId == deviceId and t.name == name and t.time.date() == date), None)
        log.i(f'获取任务: {deviceId}-{name}-{date}, task: {task}')
        if task:
            return task
        # 从数据库查找
        try:
            task = TaskModel.get({'deviceId': deviceId, 'name': name, 'date': date}, create=create)
            log.i(f'从数据库查找任务: {deviceId}-{name}-{date}, task: {task}')
            # 如果需要创建
            if task is None and create:
                task = cls(deviceId, name)
                cls._cache.append(task)
                log.i(f'创建任务: {deviceId}-{name}-{date}, task: {task}')
            return task
        except Exception as e:
            _Log._Log_.ex(e, f'获取任务失败: {deviceId}-{name}')
            return None
    
    @classmethod
    def gets(cls, date=None) -> List['STask_']:
        """
        获取特定日期的所有任务
        :param date: 日期，默认为今天
        :return: 任务列表
        """
        if date is None:
            date = datetime.now().date()
        if cls._lastDate == date:
            return cls._cache
        # 清除当前缓存
        try:
            tasks = TaskModel.query.filter(
                func.date(TaskModel.time) == date
            ).all()
            cls._cache = [cls(t.deviceId, t.name) for t in tasks]
            cls._lastDate = date
            return cls._cache
        except Exception as e:
            _Log._Log_.ex(e, f'获取日期任务列表失败: {date}')
            return []    
   
    
