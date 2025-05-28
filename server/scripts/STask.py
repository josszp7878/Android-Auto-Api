from datetime import datetime
import _G
from _G import TaskState
from SDatabase import db, Database
import _Log
from sqlalchemy import func
from typing import List, Optional


class STask_(db.Model):
    """服务端任务类"""
    __tablename__ = 'tasks'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    deviceId = db.Column(db.String(50), nullable=False)
    taskName = db.Column(db.String(50), nullable=False)
    time = db.Column(db.DateTime, default=datetime.now)  # 创建时间
    endTime = db.Column(db.DateTime)  # 添加结束时间字段
    score = db.Column(db.Integer, default=0)
    progress = db.Column(db.Float, default=0.0)
    state = db.Column(db.String(20), default=TaskState.RUNNING.value)
    life = db.Column(db.Integer, default=0)  # 任务生命，负数表示次数，正数表示时间长度，0表示无生命约束

    # 任务缓存
    _cache = []  # 任务列表
    _lastDate = None  # 最近一次缓存的日期

    @property
    def deviceMgr(self):
        from SDeviceMgr import deviceMgr
        return deviceMgr
    
    @property
    def taskId(self):
        return self.taskName
    
    @property
    def completed(self):
        return self.state in [TaskState.SUCCESS.value, TaskState.FAILED.value]

    @property
    def device(self):
        """获取任务对应的设备,使用缓存避免重复查询"""
        if not hasattr(self, '_device'):
            from SDeviceMgr import deviceMgr
            self._device = deviceMgr.get(self.deviceId)
        return self._device

    def __init__(self, deviceId: str, taskName: str):
        """初始化任务"""
        self.deviceId = deviceId
        self.taskName = taskName
        self.progress = 0.0
        self.state = TaskState.RUNNING.value
        self.time = datetime.now()
        self.life = 0  # 初始化时设置默认生命值

    def start(self):
        """开始任务"""
        self.state = TaskState.RUNNING.value
        db.session.commit()
        _Log._Log_.i(f'任务启动: {self.id}-{self.taskName}')
        STask_.refresh(self)

    def update(self, data: dict):
        """更新任务进度"""
        log = _Log._Log_
        try:
            # 获取data里面属性，可能有多个，更新任务属性，并比较是否有变化，有变化的需要提交到数据库            
            changed = False
            for key, value in data.items():
                if key == 'progress':
                    if self.progress != value:
                        self.progress = value
                        changed = True
                elif key == 'state':
                    if self.state != value:
                        self.state = value
                        changed = True
                elif key == 'score':
                    if self.score != value:
                        self.score = value
                        changed = True
            log.i(f'更新任务数据:  changed: {changed}')
            if changed:
                if Database.commit(self):
                    return STask_.refresh(self)
            return False
        except Exception as e:
            log.ex(e, '更新任务进度失败')
            return False

    def toDict(self):
        """返回任务信息字典"""
        try:
            return {
                'id': self.id or 0,  # 确保id不为null
                'taskName': self.taskName,
                'deviceId': self.deviceId,
                'progress': self.progress,
                'date': self.time.strftime('%Y-%m-%d') if self.time else '',
                'state': self.state,
                'score': self.score,
                'life': self.life or 0
            }
        except Exception as e:
            _Log._Log_.ex(e, '获取任务信息失败')
            return None

    @classmethod
    def refresh(cls, task: 'STask_'):
        """刷新任务状态到界面"""
        try:
            from SDeviceMgr import deviceMgr
            # 如果task为None，直接返回
            log = _Log._Log_
            log.i(f"刷新任务状态: 任务：{task}")
            if not task:
                return
            Database.sql(lambda db: {
                # 获取任务管理器
                _G._G_.emit('S2B_sheetUpdate', {
                        'type': 'tasks',
                        'data': [task.toDict()]
                    })
            })
            
        except Exception as e:
            _Log._Log_.ex(e, '刷新任务状态失败')

    
    @classmethod
    def get(cls, deviceId: str, taskName: str, date=None, create: bool = False) -> Optional['STask_']:
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
            log.e('获取任务失败', f'设备ID为空: {deviceId}-{taskName}')
            return None
        if date is None:
            date = datetime.now().date()
        # 先从缓存查找
        task = next((t for t in cls._cache if t.deviceId == deviceId and t.taskName == taskName and t.time.date() == date), None)
        log.i(f'获取任务: {deviceId}-{taskName}-{date}, task: {task}')
        if task:
            return task
        # 从数据库查找
        try:
            task = cls.query.filter(
                cls.deviceId == deviceId,
                cls.taskName == taskName,
                func.date(cls.time) == date
            ).first()
            log.i(f'从数据库查找任务: {deviceId}-{taskName}-{date}, task: {task}')
            # 如果需要创建
            if task is None and create:
                task = cls(deviceId, taskName)
                db.session.add(task)
                db.session.commit()
                log.i(f'创建任务: {deviceId}-{taskName}-{date}, task: {task}')
            if task:
                cls._cache.append(task)
            return task
        except Exception as e:
            _Log._Log_.ex(e, f'获取任务失败: {deviceId}-{taskName}')
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
            cls._cache = cls.query.filter(
                func.date(cls.time) == date
            ).all()
            cls._lastDate = date
            return cls._cache
        except Exception as e:
            _Log._Log_.ex(e, f'获取日期任务列表失败: {date}')
            return []    
   
    
