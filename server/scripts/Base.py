from datetime import datetime
from typing import Any
import _G
class Base_():
    """统一的基类，提供属性更新和脏标记功能"""
    
    def __init__(self, data: dict):
        if isinstance(data, dict):
            self.data = data
            self._isDirty = False
        else:
            self.data = {'name': data}
            self._isDirty = True

    @property
    def id(self) -> int:
        return int(self.getDBProp('id', 0))
    
    @id.setter
    def id(self, id:int):
        self.setDBProp('id', id)
            
    @property
    def name(self) -> str:
        return self.getDBProp('name')
    
    @property
    def isDirty(self):
        """获取脏标记"""
        return self._isDirty
    
    @isDirty.setter
    def isDirty(self, value: bool):
        """设置脏标记"""
        self._isDirty = value

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
    
    def setProp(self, params):
        """统一的属性设置方法"""
        if not params:
            return False
        g = _G._G_
        log = g.Log()
        try:
            log.i(f'{self.__class__.__name__}属性更新: {params}')
            changed = False
            
            for key, value in params.items():
                # 尝试直接设置属性
                if hasattr(self, key):
                    try:
                        oldValue = getattr(self, key)
                        if oldValue != value:
                            setattr(self, key, value)
                            self._isDirty = True
                            log.i(f'设置属性: {key} = {value}')
                            changed = True
                    except AttributeError:
                        pass
                    except Exception as e:
                        log.ex(e, f'设置属性: {key} = {value}')
                        continue

                if not changed:
                    self.setDBProp(key, value)

                if changed:
                    # 调用子类的特殊处理钩子
                    self._onProp(key, value)
            return changed
        except Exception as e:
            log.ex(e, f'{self.__class__.__name__}属性更新失败')
            return False
    
    def _onProp(self, key, value):
        """属性设置后的钩子方法，子类可以重写进行特殊处理"""
        pass 

