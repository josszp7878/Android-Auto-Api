from SModelBase import SModelBase_
from SModels import AppModel_
from _App import _App_
from datetime import datetime
from RPC import RPC

class SApp_(_App_):
    """服务端App类"""
    def __init__(self, data: dict):
        """初始化App"""
        # 先初始化父类_App_（它会处理SModelBase_的初始化）
        super().__init__(data)
        # 设置数据库模型
        self._model = AppModel_
    
    @classmethod
    def get(cls, deviceId: str, name: str, create: bool = False):
        """获取或创建App"""
        data = AppModel_.get(deviceId, name, create)
        if data:
            return cls(data)
        return None
    
    
    @property
    def deviceId(self) -> str:
        return self.getDBProp('deviceId', '')
    
    @property
    def totalScore(self) -> float:
        return float(self.getDBProp('totalScore', 0.0))
    
    @totalScore.setter
    def totalScore(self, score: float):
        self.setDBProp('totalScore', score)
    
    @property
    def income(self) -> float:
        return float(self.getDBProp('income', 0.0))
    
    @income.setter
    def income(self, income: float):
        self.setDBProp('income', income)
    
    @property
    def status(self) -> str:
        return self.getDBProp('status', 'idle')
    
    @status.setter
    def status(self, status: str):
        self.setDBProp('status', status)
    
    @property
    def lastUpdate(self) -> str:
        return self.getDBProp('lastUpdate')
    
    def updateStats(self, totalScore: float = None, income: float = None, status: str = None):
        """更新统计信息"""
        if totalScore is not None:
            self.totalScore = totalScore
        if income is not None:
            self.income = income
        if status is not None:
            self.status = status
        self.setDBProp('lastUpdate', datetime.now())
        return self.commit()    
    
    @RPC()
    def getAppInfo(self) -> dict:
        """获取App信息 - RPC方法"""
        return self.data