from datetime import datetime
from typing import Any
from SModels import DeviceModel_, TaskModel_, LogModel_

import _G
class SModelBase_:
    """模型基类"""
    def __init__(self, name: str, modelClass: type):
        """初始化模型基类
        Args:
            name: 名称
            modelClass: 模型类
        """
        if isinstance(name, dict):
            self.data = name
            self._isDirty = False
        else:
            self.data = {'name': name}
            self._isDirty = True
        self.modelClass = modelClass

    @property
    def id(self) -> int:
        return self.data.get('id')
    
    @property
    def name(self) -> str:
        return self.data.get('name')

    def getDBProp(self, key: str, default: Any = None) -> Any:
        """获取数据库属性"""
        return self.data.get(key, default)

    def setDBProp(self, key: str, value: Any)->bool:
        """设置数据库属性"""        
        if isinstance(value, datetime):
            value = value.strftime('%Y-%m-%d %H:%M:%S')
        if self.data.get(key) != value:
            self.data[key] = value
            self._isDirty = True
        return self._isDirty
    
    def setProp(self, data: dict)->bool:
        """设置属性"""
        if not data:
            return False
        try:
            log = _G._G_.Log()
            for key, value in data.items():
                #调用key对应的属性setter,key首字母大写
                setterName = f'set{key.capitalize()}'
                setter = getattr(self, setterName, None)
                log.i(f'设置属性: {key}, {value}, {setter}')
                if setter:
                    setter(value)
            return True
        except Exception as e:
            log.ex(e, f'设置属性失败: {data}')
            return False
        return True
   
    def commit(self)->bool:
        """提交数据更新"""
        log = _G._G_.Log()
        try:
            if not self._isDirty:
                return True
            if self.modelClass is None:
                log.ex(e, '提交数据更新失败,modelClass为空')
                return False
            log.d(f'提交数据更新111: {self.data}')
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

    def update(self, data: dict, commit: bool = True, refresh: bool = True):
        """更新数据"""
        log = _G._G_.Log()
        try:
            for key, value in data.items():
                if self.data.get(key) != value:
                    self.data[key] = value
                    self._isDirty = True
            # log.i(f'更新数据: self._isDirty: {self._isDirty}, commit: {commit}, refresh: {refresh}, modelClass: {self.modelClass.__name__}')
            if self._isDirty:
                # log.i('更新数据111111: ')
                if commit:
                    if not self.commit():
                        log.e(f'更新数据失败,commit失败: {self.data}')
                        return False
                # log.i('更新数据222222: ')
                if refresh:
                    # log.i(f'刷新{self.modelClass.__name__}状态11')
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
            # log.d(f'刷新{self.modelClass.__name__}')
            if self.modelClass is DeviceModel_:
                # log.i(f'刷新设备状态ddddfff: {self.name}, {self.data}')
                dataType = 'devices'
            elif self.modelClass is TaskModel_:
                dataType = 'tasks'
            elif self.modelClass is LogModel_:
                dataType = 'logs'
            data = self.toSheetData()
            g.emit('S2B_sheetUpdate', {'type': dataType, 'data': [data]})
        except Exception as e:
            log.ex(e, '刷新设备状态失败') 