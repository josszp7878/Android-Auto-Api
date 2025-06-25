from _G import TaskState
from SModelBase import SModelBase_
from SModels import TaskModel_
from Task import Task_
from datetime import datetime
from RPC import RPC

class STask_(SModelBase_, Task_):
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
    @classmethod
    def getByID(cls, id: int):
        """根据ID获取任务"""
        from SDeviceMgr import deviceMgr
        devices = deviceMgr.devices
        for device in devices:
            task = device.getTask(id)
            if task:
                return task
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
    
    @RPC()
    def getTaskInfo(self) -> dict:
        """获取任务信息 - RPC方法"""
        try:
            return {
                'success': True,
                'id': self.id,
                'name': self.name,
                'state': self.state.value,
                'progress': self.progress,
                'score': self.score,
                'life': self.life,
                'deviceId': self.deviceId,
                'time': self.time,
                'data': self.data
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    @RPC()
    def updateTaskScore(self, score: int) -> dict:
        """更新任务分数 - RPC方法"""
        try:
            old_score = self.score
            self.score = score
            if self.commit():
                return {
                    'success': True,
                    'taskId': self.id,
                    'oldScore': old_score,
                    'newScore': score,
                    'message': f'任务 {self.name} 分数已更新'
                }
            else:
                return {
                    'success': False,
                    'error': '数据库更新失败'
                }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }    
