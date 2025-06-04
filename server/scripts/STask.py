from datetime import datetime
from _G import TaskState
import _Log
from typing import List, Optional
from SModelBase import SModelBase_
from SModels import TaskModel_
from Task import TaskBase


class STask_(SModelBase_, TaskBase):
    """服务端任务类"""
    def __init__(self, name: str):
        """初始化任务"""
        super().__init__(name, TaskModel_)
    
    @property
    def state(self)->TaskState:
        state = self.getDBProp('state')
        if state is None:
            return TaskState.IDLE
        return TaskState(state)
    
    @property
    def progress(self)->int:
        return self.getDBProp('progress', 0)
    
    @property
    def score(self)->int:
        return self.getDBProp('score', 0)
    
    @property
    def life(self)->int:
        return self.getDBProp('life', 10)
    
    @property
    def time(self)->str:
        return self.getDBProp('time')
    
    @property
    def deviceId(self):
        return self.getDBProp('deviceId', 0)
    
    def setLife(self, life: int):
        if self.setDBProp('life', life):
            log = _Log._Log_
            log.d(f'设2置任务生命周期: {self.id}, life ={life}, isDirty = {self._isDirty}')
            self.commit()
            from SDevice import SDevice_
            SDevice_.sendClient('S2C_updateTask', self.deviceId, {
                'name': self.name,
                'life': life
            })
    
    @property
    def deviceId(self):
        return self.getDBProp('deviceId')    

    def toSheetData(self) -> dict:
        # 子类可重写
        data = super().toSheetData()
        if self.life != 0:
            data['progress'] = data.get('progress', 0) / float(abs(self.life))
        return data