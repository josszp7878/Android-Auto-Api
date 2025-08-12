from typing import Any
from Base import Base_
import _G
from RPC import RPC

class _ModelBase_(Base_):
    """模型基类"""
    def __init__(self, data: dict, modelClass: type):
        """初始化模型基类
        Args:
            name: 名称
            modelClass: 模型类
        """
        super().__init__(data)
        self.modelClass = modelClass

    def _onProp(self, key, value):
        """服务端特殊处理：自动提交到数据库"""
        if self._isDirty:
            self.commit()
   
    def commit(self)->bool:
        """提交数据更新"""
        log = _G._G_.Log()
        try:
            if not self._isDirty:
                return True
            if self.modelClass is None:
                log.e('提交数据更新失败,modelClass为空')
                return False
            
            self.modelClass.commit(self.data)
            self._isDirty = False
            return True
        except Exception as e:
            log.ex(e, '提交数据更新失败')
            return False

    def toSheetData(self) -> dict:
        # 子类可重写
        return self.data
    
    def toClientData(self) -> dict:
        # 子类可重写
        return self.data
    def refresh(self):
        # 子类可重写
        g = _G._G_
        log = g.Log()
        try:
            dataType = None
            className = self.__class__.__name__
            if className == 'SDevice_':
                dataType = 'devices'
            elif className == 'STask_':
                dataType = 'tasks'  
            else:
                return
            data = self.toSheetData()
            g.emit('S2B_sheetUpdate', {'type': dataType, 'data': [data]})
        except Exception as e:
            log.ex(e, '刷新设备状态失败') 