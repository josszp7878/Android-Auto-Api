from SModelBase import SModelBase_
from SModels import AppModel_
from _App import _App_
from datetime import datetime
from RPC import RPC

class SApp_(SModelBase_, _App_):
    """服务端App类"""
    def __init__(self, data: dict):
        """初始化App"""
        # 先初始化SModelBase_
        SModelBase_.__init__(self, data, AppModel_)
        # 从data中获取appName来初始化_App_
        _App_.__init__(self,  data)
    
    @classmethod
    def get(cls, deviceId: str, appName: str, create: bool = False):
        """获取或创建App"""
        data = AppModel_.get(deviceId, appName, create)
        if data:
            return cls(data)
        return None
    
    @classmethod
    def getByID(cls, id: int):
        """根据ID获取App"""
        from SDeviceMgr import deviceMgr
        devices = deviceMgr.devices
        for device in devices:
            for app in device._apps.values():
                if hasattr(app, 'id') and app.id == id:
                    return app
        return None
    
    @property
    def appName(self) -> str:
        return self.getDBProp('appName', '')
    
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
        try:
            return {
                'success': True,
                'id': self.id,
                'appName': self.appName,
                'deviceId': self.deviceId,
                'totalScore': self.totalScore,
                'income': self.income,
                'status': self.status,
                'lastUpdate': self.lastUpdate,
                'data': self.data
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    @RPC()
    def updateAppStats(self, totalScore: float = None, income: float = None, status: str = None) -> dict:
        """更新App统计 - RPC方法"""
        try:
            old_data = {
                'totalScore': self.totalScore,
                'income': self.income,
                'status': self.status
            }
            
            if self.updateStats(totalScore, income, status):
                return {
                    'success': True,
                    'appId': self.id,
                    'appName': self.appName,
                    'oldData': old_data,
                    'newData': {
                        'totalScore': self.totalScore,
                        'income': self.income,
                        'status': self.status
                    },
                    'message': f'App {self.appName} 统计已更新'
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