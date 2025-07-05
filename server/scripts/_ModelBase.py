from typing import Any
from Base import Base_
import _G
from RPC import RPC

class _ModelBase_(Base_):
    """模型基类"""
    def __init__(self, name: str, modelClass: type):
        """初始化模型基类
        Args:
            name: 名称
            modelClass: 模型类
        """
        super().__init__(name)
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

    @RPC()
    def update(self, data: dict, commit: bool = True, refresh: bool = True):
        """更新数据"""
        log = _G._G_.Log()
        try:
            for key, value in data.items():
                if self.data.get(key) != value:
                    self.data[key] = value
                    self._isDirty = True
            if self._isDirty:
                if commit:
                    if not self.commit():
                        log.e(f'更新数据失败,commit失败: {self.data}')
                        return False
                if refresh:
                    self.refresh()
            return True
        except Exception as e:
            log.ex(e, '更新数据失败')
            return False

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