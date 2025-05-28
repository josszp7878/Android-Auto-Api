from datetime import datetime
from typing import Any
import _G

class SModelBase_:
    """模型基类"""
    def __init__(self, modelClass, params: dict):
        model = modelClass.get(params, create=False)
        self.cls = modelClass
        if model:
            self.model = model
            self.data: dict = model.toDict()
        else:
            self.model = None
            self.data: dict = params
        self._isDirty = False

    @property
    def id(self) -> int:
        return self.data.get('id')

    @property
    def name(self) -> str:
        return self.data.get('name')

    def getDBProp(self, key: str, default: Any = None) -> Any:
        """获取数据库属性"""
        return self.data.get(key, default)

    def setDBProp(self, key: str, value: Any):
        """设置数据库属性"""
        if isinstance(value, datetime):
            value = value.strftime('%Y-%m-%d %H:%M:%S')
        if self.data.get(key) != value:
            self.data[key] = value
            self._isDirty = True

    def commit(self)->bool:
        """提交数据更新"""
        log = _G._G_.Log()
        try:
            if not self._isDirty:
                return True
            if self.model is None:
                self.model = self.cls.get(self.name, create=True)
            log.i(f'提交数据3333: {self.data}')
            result = self.model.commit(self.data)
            self._isDirty = False
            return result
        except Exception as e:
            log.ex(e, '提交数据失败')
            return False

    def toSheetData(self) -> dict:
        # 子类可重写
        return self.data
    
    def update(self, data: dict, commit: bool = True, refresh: bool = True):
        """更新数据"""
        log = _G._G_.Log()
        try:
            for key, value in data.items():
                if self.data.get(key) != value:
                    self.data[key] = value
                    self._isDirty = True
            if commit:
                return self.commit()
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
            strType = None
            if self.cls.__name__ == 'DeviceModel':
                strType = 'devices'
            elif self.cls.__name__ == 'TaskModel':
                strType = 'tasks'
            log.i(f'刷新{strType}状态: {self.data}, self.cls.__name__: {self.cls.__name__}') 
            if strType:
                g.emit('S2B_sheetUpdate', {'type': strType, 'data': [self.toSheetData()]})
        except Exception as e:
            log.ex(e, '刷新设备状态失败') 