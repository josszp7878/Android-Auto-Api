import copy
from typing import Dict, Any, List, Optional, TYPE_CHECKING
import _G
if TYPE_CHECKING:
    from _Tools import _Tools_
    from _App import _App_
import threading
import time
import re

g = _G.g
log = g.Log()


class _Page_:
    """页面类，用于验证页面状态并执行相应操作"""
    # 线程安全锁
    _lock = threading.Lock()
    
    # 页面类相关的类变量
    currentPage = None  # 当前页面
    _root = None        # 根页面对象
    
    # 默认值实例，在类初始化时创建
    _DEFAULT = None
    
    # 默认配置
    _DEFAULT_CONFIG = {
        'name': '',
        'match': None,
        'childs': None,
        'event': {},
        'timeout': 0,
        'type': 'once',
        'entry': None,
        'exit': None,
        'schedule': {}
    }
    
    @classmethod
    def Default(cls) -> "_Page_":
        """获取默认配置实例"""
        if cls._DEFAULT is None:
            # 创建默认实例
            cls._DEFAULT = cls("__default__")
        return cls._DEFAULT
    
    @classmethod
    def Root(cls) -> "_Page_":
        """获取根页面对象"""
        return cls._root
    
    @classmethod
    def setCurrent(cls, page) -> "_Page_":
        """设置当前页面"""
        cls.currentPage = page
        return page
    
    @classmethod
    def getCurrent(cls) -> "_Page_":
        """获取当前页面"""
        return cls.currentPage

    def __init__(self, app: str, name: str, data=None):
        """初始化检查器，直接定义默认值
        Args:
            name: 检查器名称
            config: 检查器配置字典
            data: 检查器数据(可选)
        """
        self._name = name       # 页面名称
        self._app = app         # 应用名称
        self._parent = None     # 父页面对象
        
        # 运行时属性（不会被序列化）
        self.data = data or {}   # 附加数据
        self._running = False    # 是否启用
        self.ret = g.Tools().eRet.none  # 返回值，现在直接存储DoRet枚举
        self.forceCancelled = False  # 是否被外部强制取消标志
        if data is not None:
            self.data = data
        self._config = {}
        self._life: float = 0  # 默认生命长度，>0：表示时间长度，单位为秒 <0:表示能循环次数。 0：表示生命无限
        self.resetLife()
        self._alwaysMatch = False 

    def __getattr__(self, name):
        """重写 __getattr__ 方法，使 page.num 可以访问 page.data['num']"""
        if name in self.data:
            return self.data[name]
        return None
    
    @property
    def life(self) -> float:
        val = self._life
        if val == 0:
            return 1
        percent = -1
        if val > 0:
            # 如果life大于0,以时间计算生命
            pastTime = time.time() - self._startTime
            percent = (self._life - pastTime)/self._life
        else:
            # 如果life小于0,以循环次数计算生命
            percent = (self._life - self._loopCount)/abs(val)
        ret = max(0, min(percent, 1))
        # if ret == 0:
        #     log.d(f"页面{self.name}生命结束")
        return ret
    
    @life.setter
    def life(self, value: float):
        self._life = value
        self.resetLife()

    def resetLife(self):
        self._startTime = time.time()
        self._loopCount = 0

    @property
    def parent(self)->"_Page_":
        """获取父页面"""
        if self._parent is None:
            #获取exit里面value为'<'的key
            for key, value in self.curPage.exit.items():
                if value == '<':
                    self._parent = self.getPage(key)
        return self._parent

    @parent.setter
    def parent(self, value: "_Page_"):
        # 设置父页面引用
        self._parent = value


    def setParent(self, parent: "_Page_"):
        if parent is None:
            return
        self.parent = parent
        # 处理父页面的exit和子页面的entry的链接关系 
        # 如果父页面存在exit配置且子页面存在entry配置
        if hasattr(parent, '_config') and hasattr(self, '_config'):
            parentExit = parent.getProp('exit')
            if not parentExit:
                parentExit = {}
                parent._config['exit'] = parentExit
            entry = self.getProp('entry')
            if not entry:
                entry = {}
                self._config['entry'] = entry
            exit = self.getProp('exit')
            if not exit:
                exit = {}
                self._config['exit'] = exit    
            parentExit[f'{self.name}'] = ''
            entry[f'{parent.name}'] = ''
            exit[f'{parent.name}'] = '<'

    @property
    def app(self) -> "_App_":
        if self._app is None:
            return None
        g = _G.g
        return g.App().getApp(self._app)
    
    @property
    def config(self) -> Dict[str, Any]:
        return self._config
    
    @config.setter
    def config(self, value: Dict[str, Any]):
        self._config.update(value)


    @property
    def name(self) -> str:
        return self._name
    
    @name.setter
    def name(self, value: str):
        self._name = value

    def getProp(self, prop: str):
        """获取属性"""
        if hasattr(self, '_config'):
            if prop in self._config:
                return self._config[prop]
        return None
    
    def setProp(self, prop: str, value: Any):
        if hasattr(self, '_config'):
            self._config[prop] = value
    
    @property
    def _match(self) -> str:
        return self.getProp('match') or self.name.split('-')[-1]
    
    @_match.setter
    def _match(self, value: str):
        self.setProp('match', value)

    @property
    def childs(self) -> List[str]:
        return self.getProp('childs') or []
    
    @childs.setter
    def childs(self, value: List[str]):
        self.setProp('childs', value)

    @property
    def event(self) -> Dict[str, Any]:
        return self.getProp('event') or {}
    
    @event.setter
    def event(self, value: Dict[str, Any]):
        self.setProp('event', value)

    @property
    def timeout(self) -> int:
        return self.getProp('timeout') or 0
    
    @timeout.setter
    def timeout(self, value: int):
        self.setProp('timeout', value)

    @property
    def type(self) -> str:
        return self.getProp('type') or 'once'
    
    @type.setter
    def type(self, value: str):
        self.setProp('type', value)

    @property
    def entry(self) -> Dict[str, Any]:
        return self.getProp('entry') or {}
    
    @entry.setter
    def entry(self, value: Dict[str, Any]):
        self.setProp('entry', value)

    @property
    def exit(self) -> Dict[str, Any]:
        return self.getProp('exit') or {}
    
    @exit.setter
    def exit(self, value: Dict[str, Any]):
        self.setProp('exit', value)

    @property
    def schedule(self) -> Dict[str, Any]:
        """获取调度配置"""
        return self.getProp('schedule') or {}
    
    @schedule.setter
    def schedule(self, value: Dict[str, Any]):
        """设置调度配置"""
        self.setProp('schedule', value)

    def __str__(self):
        return f"{self.name} {self._match}"

    @property
    def running(self) -> bool:
        return self._running

    
    def addProp(self, prop: str, value: str, value1: str = None) -> bool:
        log = _G.g.Log()
        try:    
            if 'mat' in prop:
                oldVal = self._config['match']
                split = '&|'
                if value.startswith('|'):
                    split = '|&'
                    value = value[1:]
                elif value.startswith('&'):
                    value = value[1:]
                range = _Page_.parseMatchRange(self._config['match'], value1)
                value = _Page_._addStrListProp(
                    self._config['match'], split, value, range)
                if value:
                    self._config['match'] = value
                    log.d(f"_match: {oldVal} => {self._config['match']}")
            elif prop in self._config:
                oldVal = self._config[prop]
                self._config[prop][value] = value1
                log.d(f"{prop}: {oldVal} => {value1}")
            else:
                log.e(f"不支持add的属性: {prop}")
                return False
            return True
        except Exception as e:
            log.ex(e, f"add{prop}失败: {value}")
            return False
        
    def removeProp(self, prop: str, value: str) -> bool:
        """删除指定属性
        Args:
            prop: 属性名
            value: 要删除的值
        Returns:
            bool: 删除是否成功
        """
        log = _G.g.Log()
        try:    
            if 'mat' in prop:
                oldVal = self._config['match']
                value = value.strip('&').strip('|')
                value = _Page_._delStrListProp(self._config['match'], '&|', value)
                if value:
                    self._config['match'] = value
                    log.d(f"_match: {oldVal} => {self._config['match']}")
            elif prop in self._config:
                oldVal = self._config[prop]
                self._config[prop].pop(value)
                log.d(f"{prop}: {oldVal} => {self._config[prop]}")
            else:
                log.e(f"不支持remove的属性: {prop}")
                return False
            return True
        except Exception as e:
            log.ex(e, f"remove{prop}失败: {value}")
            return False
  
        
    @classmethod
    def parseMatchRange(cls, match: str, range: str = None):
        """解析match的范围
        Args:
            match: 要解析的范围的文字
            range: 范围，可以是坐标，也可以是偏移量. 如果为'_'，则从当前屏幕获取match文字对应的坐标
        Returns:
            str: 范围
        """
        if not range:
            return range  
        tools = g.Tools()
        # 从当前屏幕获取match文字对应的坐标
        pos = tools.findTextPos(match)
        DEF = 75
        if range == '_':
            return f'{pos[0]-DEF},{pos[1]-DEF},{pos[0]+DEF},{pos[1]+DEF}'
        sX, sY = range.split(',') if range else (0, 0)
        x = int(sX) if sX else 0
        y = int(sY) if sY else 0
        if x > 0 or y > 0:

            if pos:
                if x > 0 and y > 0:
                    range = f'{pos[0] - x},{pos[1]-y},{pos[0]+x},{pos[1]+y}'
                elif x > 0:
                    range = f'{pos[0] - x},{pos[0]+x}'
                elif y > 0:
                    range = f'{pos[1] - y},{pos[1]+y}'
            else:
                return f"e~当前页面未找到{match}文字"
        return range
    
    @classmethod
    def _addStrListProp(cls, curVal: str, split: str, value: str, 
                        range: str = None):
        # 为了支持已有ITEM的替换，先将match转换为列表
        newValue = f'{value}{range}' if range else value
        if newValue == curVal:
            return None
        if curVal:
            m = re.search(rf'[{split}\s]*{value}[^{split}]*', curVal)
            newValue = f'{split[0]}{newValue}'
            if m:
                curVal = curVal.replace(m.group(0), newValue)
            else:                
                curVal = f'{curVal}{newValue}'
        else:
            curVal = newValue
        return curVal
    
    @classmethod
    def _delStrListProp(cls, curVal: str, split: str, value: str):
        # 为了支持已有ITEM的替换，先将match转换为列表
        if curVal:
            return re.sub(rf'[{split}\s]*{value}', '', curVal)
        return curVal
   
    @property
    def running(self) -> bool:
        return self._running    

    def alwaysMatch(self, value: bool):
        self._alwaysMatch = value

    def match(self) -> bool:
        """执行检查逻辑
        Returns:
            bool: 检查是否通过
        """
        try:
            if self._alwaysMatch:
                #一次性开关
                self._alwaysMatch = False
                return True
            tools = g.Tools()
            m = self._match
            # log.d(f"匹配: {match}")
            result, _ = tools.check(self, m)
            # log.d(f"{self.name}.Match({m})={result}")
            return result
        except Exception as e:
            log.ex(e, "页面匹配失败")
            return False

        
    def _doEvent(self, key: str, action: str):
        try:
            tools = g.Tools()
            key = key.strip()
            execute = False
            ret = tools.eRet.none
            
            # 检查是否为用户事件
            app = self.app
            userEvents = getattr(app, 'userEvents', [])
            
            # 检查是否为用户事件触发
            for eventName in userEvents:
                if eventName in key:
                    # 用户事件匹配，直接执行
                    log.d(f"用户事件触发: {eventName} 在 {key}")
                    execute = True
                    break
            
            # 如果不是用户事件，进行常规检查
            if not execute:
                # 处理不同类型的key
                if key.startswith('%'):
                    # 概率执行：%30 表示30%的概率执行
                    probability = int(key[1:])
                    import random
                    execute = random.randint(1, 100) <= probability
                    log.d(f"概率执行({probability}%): {execute}")
                elif key.startswith('-'):
                    # 延时执行：-5 表示延时5秒后执行
                    delay = int(key[1:])
                    log.d(f"延时执行({delay}秒)")
                    time.sleep(delay)
                    execute = True
                elif key == '':
                    log.d("无条件执行")
                    execute = True
                else:
                    # 屏幕匹配文本，如果匹配到则执行
                    execute, _ = tools.check(self, key)
                    
            # 如果条件满足，执行action
            if execute:
                action = action.strip() if action else ''
                if action == '':
                    # 空操作默认为点击
                    tools.click(key)
                else:
                    ret = tools.do(self, action)                      
            return ret
        except Exception as e:
            log.ex(e, f"执行事件{key}失败")
            return tools.eRet.error

    @classmethod
    def onLoad(cls, oldCls=None):
        """热加载时的处理"""
        if oldCls:
            from  _App import _App_
            _App_.loadConfig()
    
    def getInst(self, data: Dict[str, Any] = None) -> Optional["_Page_"]:
        """ 获取页面实例
        Args:
            template: 页面模板
            config: 页面配置
        Returns:
            _Page_: 页面实例
        """
        # 创建新的运行时页面
        page = _Page_(g.App().cur().name, self.name)
        # 深度复制模板配置
        config = copy.deepcopy(self._config)
        # 更新额外参数
        if data:
            for k, v in data.items():
                if k in page._config:
                    if isinstance(v, dict):
                        config[k] = v.copy()
                    else:
                        config[k] = v
        page._config = config
        return page
    
    def renter(self) -> bool:
        """重新进入页面
        Returns:
            bool: 是否成功进入
        """
        g = _G.g
        log = g.Log()
        try:
            if self.life == 0:
                return False
            back = self.app.back()
            if not back:
                return False
            log.d(f"重新进入页面: {self.name}")
            return self.app.toPage(self, resetLife=False)
        except Exception as e:
            log.ex(e, f"重新进入页面失败: {self.name}")
            return False
    
    def begin(self, params: Dict[str, Any] = None) -> threading.Thread:
        """异步执行page.begin()
        """
        thread = threading.Thread(target=self._begin, args=(params,))
        thread.start()
        return thread
        
    def _doEntry(self):
        """执行入口代码
        """
        g = _G.g
        log = g.Log()
        try:
            tools = g.Tools()
            entry = self.entry
            alwaysDo = entry.get('')
            if alwaysDo:
                tools.do(self, alwaysDo)
            firstDo = entry.get('#', None)
            if firstDo and self.life == 1:
                log.d(f"执行首次代码: {firstDo}")
                tools.do(self, firstDo)
        except Exception as e:
            log.ex(e, f"执行入口代码失败: {self.name}")

    def doExit(self, toPage: str = None):
        """执行出口代码
        """
        g = _G.g
        log = g.Log()
        try:
            tools = g.Tools()
            exit = self.exit
            if toPage:
                action = exit.get(toPage, None)
                if action:
                    tools.do(self, action)
                if action == '<':
                    log.i(f"< {toPage}")
                else:
                    log.i(f"> {toPage}")
            else:
                alwaysDo = exit.get('')
                if alwaysDo:
                    tools.do(self, alwaysDo)
        except Exception as e:
            log.ex(e, f"执行出口代码失败: {self.name}")

    def _begin(self, params: Dict[str, Any] = None):
        """执行页面
        """
        tools = g.Tools()
        try:
            if params:
                for k, v in params.items():
                    setattr(self, k, v)
            self._loopCount += 1          
            # 确保ret一开始为none，重置强制取消状态
            ret = tools.eRet.none
            self.forceCancelled = False
            self._doEntry()
            
            # 执行页面更新
            ret = self.update()
            
            # 首先检查是否被强制取消，如果是则跳过退出逻辑
            if ret != tools.eRet.cancel and ret != tools.eRet.error:
                # 只有当返回值不是error和cancel时才执行退出逻辑
                self.doExit()
            self.ret = ret
        except Exception as e:
            log.ex(e, f"执行页面异常: {self.name}")
            self.ret = tools.eRet.error
        finally:
            log.d(f"页面 {self.name} 结束")
    
    def end(self, cancel=False):
        """结束页面"""
        tools = g.Tools()
        if cancel:
            self.ret = tools.eRet.cancel
        else:
            self.ret = tools.eRet.end
        self.forceCancelled = True

    def update(self) -> '_Tools_.eRet':
        """执行页面更新逻辑
        1. 直接执行事件KEY对应的ACTION，_doEvent方法内部会处理用户事件逻辑
        
        由App._update方法驱动，每次调用只执行一次事件检测和处理
        
        Returns:
            '_Tools_.eRet': 执行结果
        """
        tools = g.Tools()
        ret = tools.eRet.none
        log = _G._G_.Log()
        
        try:
            # 检查是否被外部强制取消
            if self.forceCancelled:
                ret = tools.eRet.cancel
                return ret
                
            # 检查超时
            if self.timeout > 0:
                currentTime = time.time()
                elapsedTime = currentTime - self._startTime
                if elapsedTime > self.timeout:
                    log.d(f"页面 {self.name} 超时")
                    ret = tools.eRet.timeout
                    return ret
            
            # 事件检测和处理
            eventTriggered = False
            for key, action in self.event.items():
                if not key or not action:
                    continue
                
                # 直接调用_doEvent处理事件（包括用户事件）
                ret = self._doEvent(key, action)
                if ret != tools.eRet.none:
                    eventTriggered = True
                    break
             
            return ret
        except Exception as e:
            log.ex(e, f"执行页面更新循环异常: {self.name}")
            ret = tools.eRet.error
            return ret


_Page_.onLoad()



