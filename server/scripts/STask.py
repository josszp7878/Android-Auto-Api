from datetime import datetime
from _G import TaskState
import _Log
from typing import List, Optional
from SModelBase import SModelBase_
from SModels import TaskModel


class STask_(SModelBase_):
    """服务端任务类"""
    # 任务缓存
    _cache: List['STask_'] = []  # 任务列表
    _lastDate = None  # 最近一次缓存的日期

    def __init__(self, name: str):
        """初始化任务"""
        super().__init__(name, TaskModel)
    
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
    
    def setLife(self, life: int):
        if self.setDBProp('life', life):
            self.commit()
            from SDevice import SDevice_
            SDevice_.sendClient('S2C_updateTask', self.deviceId, {
                'name': self.name,
                'life': life
            })
    
    @property
    def deviceId(self):
        return self.getDBProp('deviceId')    
    
    def start(self):
        """开始任务"""
        self.update({'state': TaskState.RUNNING.value})
        _Log._Log_.i(f'任务启动: {self.id}-{self.name}')

    @classmethod
    def getByID(cls, id) -> Optional['STask_']:
        """根据ID获取任务"""
        log = _Log._Log_
        log.d(f'根据ID获取任务: {id}, {cls._cache}')
        return next((d for d in cls._cache if d.id == id), None)   

    @classmethod
    def get(cls, deviceId: int, name: str, date: datetime = None, create: bool = False) -> Optional['STask_']:
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
        data = next((t for t in cls._cache if t.deviceId == deviceId and t.name == name and t.time.date() == date), None)
        log.d(f'获取任务: {deviceId}-{name}-{date}, task: {data}')
        if data:
            return data        
        try:
            if date is None:
                date = datetime.now().date()
            data = TaskModel.get(deviceId, name, date, create)
            if data:
                data = STask_(data)
                log.d(f'创建任务: {deviceId}-{name}-{date}, task: {data}')
                cls._cache.append(data)
            return data
        except Exception as e:
            log.ex(e, f'获取任务失败: {deviceId}-{name}')
            return None
    
    @classmethod
    def gets(cls, date=None) -> List['STask_']:
        """
        获取特定日期的所有任务
        :param date: 日期，默认为今天
        :return: 任务列表
        """
        log = _Log._Log_
        if date is None:
            date = datetime.now().date()
        if cls._lastDate == date:
            return cls._cache
        # 清除当前缓存
        try:
            tasks = TaskModel.all(date)
            cls._cache = [cls(t) for t in tasks]
            log.d(f'获取日期任务列表: {date}, {cls._cache}')
            cls._lastDate = date
            return cls._cache
        except Exception as e:
            log.ex(e, f'获取日期任务列表失败: {date}')
            return []    
    