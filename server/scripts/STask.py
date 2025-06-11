from _G import TaskState
from SModelBase import SModelBase_
from SModels import TaskModel_
from Task import TaskBase
from datetime import datetime

class STask_(SModelBase_, TaskBase):
    """服务端任务类"""
    def __init__(self, name: str):
        """初始化任务"""
        super().__init__(name, TaskModel_)
    
    @classmethod
    def get(cls, deviceId: str, name: str, date:datetime=None, create: bool = False):
        """获取或创建任务"""
        data = TaskModel_.get(deviceId, name, date, create)
        if data:
            return cls(data)
        return None
    
    @property
    def state(self)->TaskState:
        state = self.getDBProp('state')
        if state is None:
            return TaskState.IDLE
        return TaskState(state)
    
    @property
    def progress(self)->int:
        return int(self.getDBProp('progress', 0))
    
    @property
    def score(self)->int:
        return int(self.getDBProp('score', 0))
    
    @score.setter
    def score(self, score: int):
        self.setDBProp('score', score)

    @property
    def life(self)->int:
        return int(self.getDBProp('life', 10))
    
    def setLife(self, life: int):
        if self.setDBProp('life', life):
            # log = _Log._Log_
            # log.d(f'设2置任务生命周期: {self.id}, life ={life}, isDirty = {self._isDirty}')
            self.commit()
            from SDevice import SDevice_
            SDevice_.sendClient('S2C_updateTask', self.deviceId, {
                'id': self.id,
                'life': life
            })
    
    @property
    def time(self)->str:
        return self.getDBProp('time')
    
    @property
    def deviceId(self)->int:
        return int(self.getDBProp('deviceId', 0))
    
    def toSheetData(self) -> dict:
        data = super().toSheetData()
        data['progress'] = self.progress  # 直接用整数
        data['life'] = self.life
        return data
    

    