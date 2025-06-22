import _G
class Base_():
    """统一的基类，提供属性更新和脏标记功能"""
    
    def __init__(self):
        self._isDirty = False
        # 统一使用data字典存储属性
        if not hasattr(self, 'data'):
            self.data = {}
    
    @property
    def isDirty(self):
        """获取脏标记"""
        return self._isDirty
    
    @isDirty.setter
    def isDirty(self, value: bool):
        """设置脏标记"""
        self._isDirty = value
    
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
                    if self.data.get(key) != value:
                        self.data[key] = value
                        self._isDirty = True
                        log.i(f'设置到data: {key} = {value}')
                        changed = True
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