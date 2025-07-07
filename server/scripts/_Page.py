import copy
import json
from typing import Dict, Any, List, Optional, TYPE_CHECKING
import _G
if TYPE_CHECKING:
    from _Tools import _Tools_
    from CApp import CApp_
import threading
import time
import re

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
        'event': {},
        'timeout': [0, None],  # 第一个元素是时间，第二个是操作
        'entry': None,
        'exit': None
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

    def __init__(self, app: 'CApp_', name: str, data=None, config=None):
        """初始化检查器，直接定义默认值
        Args:
            name: 检查器名称
            config: 检查器配置字典
            data: 检查器数据(可选)
        """
        self._name = name       # 页面名称
        self._app: "CApp_" = app         # 应用名称
        self._parent = None     # 父页面对象
        self._config = config or {}
        
        # 运行时属性（不会被序列化）
        self.data = data or {}   # 附加数据
        self._running = False    # 是否运行
        self.ret = _G.g.Tools().eRet.none  # 返回值，现在直接存储DoRet枚举
        self.forceCancelled = False  # 是否被外部强制取消标志
        if data is not None:
            self.data = data
        self._exitPages = []  # 存储可以从当前页面退出到的页面列表
        self._timeout = None  # 超时时间
        self._timeoutOp = None  # 超时操作
        self._timeouted = False  # 是否已经处理过超时
        self._startTime = time.time()  # 开始时间

    # 进入次数
    @property
    def count(self) -> int:
        """获取进入次数"""
        return self.data.get('count', 0)
    @count.setter
    def count(self, value: int):
        """设置进入次数"""
        self.data['count'] = value

    # 最大进入次数
    @property
    def maxCount(self) -> int:
        """获取最大进入次数"""
        return self.data.get('_maxCount', -1)
    
    def toJson(self) -> str:
        """转换为json字符串"""
        #只保存以不以_开头的属性
        data = {
            k: v for k, v in self.data.items() if not k.startswith('_')
        }
        return json.dumps(data)
    
    def fromJson(self, jsonStr: str):
        """从json字符串转换为对象"""
        data = json.loads(jsonStr)
        self.data.update(data)

    def __getattr__(self, name):
        """重写 __getattr__ 方法，使 page.num 可以访问 page.data['num']"""
        #解析 name_type,先找最后一个'_'
        pos = name.rfind('_') + 1
        key = name
        if pos > 1:
            key = name[:pos]
            type = name[pos]
        else:
            type = 'str'
        if key in self.data:
            val = self.data[key]
            if type == 'n':
                return int(val)
            elif type == 'f':
                return float(val)
            elif type == 'b':
                return bool(val)
            else:
                return val
        return None    
  
    @property
    def parent(self) -> "_Page_":
        """获取父页面"""
        if self._parent is None:
            # 获取exit里面value为'<'的key
            for key, value in self.curPage.exit.items():
                if value == '<':
                    self._parent = self.getPage(key)
        return self._parent

    @parent.setter
    def parent(self, value: "_Page_"):
        # 设置父页面引用
        self._parent = value


    @property
    def app(self) -> "CApp_":
        return self._app
    
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
        if prop in self.data:
            return self.data[prop]
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
    def timeout(self) -> list:
        """获取超时配置数组 [timeout_seconds, operation]"""
        if self._timeout is None:
            timeoutConfig = self.getProp('timeout') or [0, None]
            if not isinstance(timeoutConfig, list) or len(timeoutConfig) < 2:
                timeoutConfig = [0, None]
            # 确保类型正确
            try:
                timeoutConfig[0] = int(timeoutConfig[0])
            except (ValueError, TypeError):
                timeoutConfig[0] = 0
            if not isinstance(timeoutConfig[1], str):
                timeoutConfig[1] = None
            self._timeout = timeoutConfig
        return self._timeout

    @timeout.setter
    def timeout(self, value):
        self._timeout = None  # 清空缓存
        if isinstance(value, list) and len(value) >= 2:
            # 确保存入的是[时间, 操作]格式
            processed = [
                str(value[0]) if value[0] is not None else '0',
                str(value[1]) if value[1] is not None else None
            ]
            self.setProp('timeout', processed)
        else:
            self.setProp('timeout', [0, None])

    def _updateTimeout(self, tools: "_Tools_")->bool:
        """更新超时检查"""
        timeoutConfig = self.timeout  # 这会触发getter处理
        timeout = timeoutConfig[0]
        op = timeoutConfig[1]
        
        if timeout <= 0:
            return False
        if self._timeouted:
            return True
        
        pastTime = time.time() - self._startTime
        g = _G.g
        log = g.Log()
        log.d(f"{self.name} 倒计时 {timeout-pastTime}")
        
        if pastTime > timeout:
            if not self._timeouted:
                log.d(f"页面 {self.name} 超时, timeout op: {op}")
                if op:
                    self.ret = tools.do(op)
                else:
                    self.ret = tools.eRet.exit
                self._timeouted = True
            return True
        return False
    

    @property
    def entry(self) -> Dict[str, Any]:
        return self.getProp('entry') or {}
    
    @entry.setter
    def entry(self, value: Dict[str, Any]):
        self.setProp('entry', value)

    @property
    def exit(self) -> Dict[str, Any]:
        return self.getProp('exit') or {}
    
    @property
    def isAlert(self) -> bool:
        return len(self.exit) == 0
    
    @isAlert.setter
    def isAlert(self, value: bool):
        self.setProp('isAlert', value)

    def __str__(self):
        return f"{self.name} {self._match}"

    @property
    def running(self) -> bool:
        return self._running

    
    def addProp(self, prop: str, value: str, value1: str = None) -> bool:
        g = _G.g
        log = g.Log()
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
                    # log.d(f"_match: {oldVal} => {self._config['match']}")
            elif prop in self._config:
                # oldVal = self._config[prop]
                self._config[prop][value] = value1
                # log.d(f"{prop}: {oldVal} => {value1}")
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
                value = _Page_._delStrListProp(
                    self._config['match'], '&|', value)
                if value:
                    self._config['match'] = value
                    # log.d(f"_match: {oldVal} => {self._config['match']}")
            elif prop in self._config:
                # oldVal = self._config[prop]
                self._config[prop].pop(value)
                # log.d(f"{prop}: {oldVal} => {self._config[prop]}")
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

    def match(self) -> bool:
        """执行检查逻辑
        Returns:
            bool: 检查是否通过
        """
        g = _G.g
        try:
            tools = g.Tools()
            if not tools.isAndroid() and self == self.app.toPage:
                return True
            m = self._match
            return tools.check(m, self.app)
        except Exception as e:
            g.Log().ex(e, "页面匹配失败")
            return False

    def _doEvent(self, key: str, action: str):
        g = _G.g
        log = g.Log()
        try:
            tools = g.Tools()
            key = key.strip()
            execute = False
            ret = tools.eRet.none            
            # 如果不是用户事件，进行常规检查
            if not execute:
                if key.startswith('-'):
                    # 延时执行：-5 表示延时5秒后执行
                    delay = int(key[1:])
                    log.d(f"延时{delay}秒后执行")
                    time.sleep(delay)
                    execute = True
                elif key == '':
                    log.d("无条件执行")
                    execute = True
                else:
                    if key.startswith('%'):
                        # 处理概率
                        probability = 0
                        m = re.match(r'%(\d+)(.*)', key)
                        if m:
                            probability = int(m.group(1))
                            key = m.group(2)
                        if probability > 0:
                            import random
                            if random.randint(1, 100) > probability:
                                # log.d(f"{probability}%概率：不执行{key}")
                                return False
                    # 屏幕匹配文本，如果匹配到则执行
                    execute = tools.check(key, self.app)
                    if execute:
                        log.d(f">e: {key}")
                    
            # 如果条件满足，执行action
            if execute:
                action = action.strip() if action else ''
                if action == '':
                    # 如果action为空，当成点击匹配文字，调试回到上一页
                    action = '@it.click("","@app.last().back()")'
                ret = tools.do(action)                      
            return ret
        except Exception as e:
            log.ex(e, f"执行事件{key}失败")
            return tools.eRet.error

    @classmethod
    def onLoad(cls, oldCls=None):
        """热加载时的处理，强制替换所有App中的Page实例为新类实例"""
        if oldCls:
            g = _G.g
            log = g.Log()
            # 强制替换所有App中的Page实例
            from  CApp import CApp_
            for app in CApp_.apps().values():
                if hasattr(app, '_pages'):
                    for name, oldPage in list(app._pages.items()):
                        # 用新类实例化，保留config和data
                        newPage = cls(app, name, data=getattr(oldPage, 'data', None), config=getattr(oldPage, '_config', None))
                        app._pages[name] = newPage
                        # 替换当前页面、根页面等引用
                        if getattr(app, '_curPage', None) is oldPage:
                            app._curPage = newPage
                        if getattr(app, 'rootPage', None) is oldPage:
                            app.rootPage = newPage
                        if getattr(app, '_lastPage', None) is oldPage:
                            app._lastPage = newPage
                        if getattr(app, '_toPage', None) is oldPage:
                            app._toPage = newPage
                        if getattr(app, '_path', None):
                            app._path = [newPage if p is oldPage else p for p in app._path]
    
    def copy(self, data: Dict[str, Any] = None) -> Optional["_Page_"]:
        """ 获取页面实例
        Args:
            data: 页面参数数据
        Returns:
            _Page_: 页面实例
        """
        # 创建新的运行时页面
        page = _Page_(self._app, self._name, config=self._config)
        # 深度复制模板配置
        page[_G.TEMP] = True 
        # 更新额外参数
        if data:
            page.data.update(data)
        return page
  
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
                tools.do(alwaysDo)
        except Exception as e:
            log.ex(e, f"执行入口代码失败: {self.name}")

    def doExit(self, toPage: str = None):
        """执行出口代码
        """
        g = _G.g
        log = g.Log()
        toPage = toPage.strip() if toPage else ''
        try:
            action = self.exit.get(toPage) if self.exit else None
            tools = g.Tools()
            action = action.strip() if action else ''
            if action and action != '':
                action = action.strip('&')
                tools.do(action)
        except Exception as e:
            log.ex(e, f"执行出口代码失败: {self.name}")

    def begin(self)->bool:
        """执行页面
        """
        if self.running:
            return True
        if self.maxCount > 0 and self.count >= self.maxCount:
            return False
        self.count += 1
        self._running = True  # 设置页面为运行状态
        self._doEntry()
        return True
    
    def end(self, cancel=False):
        """结束页面"""
        if not self.running:
            return True
        tools = g.Tools()
        if cancel:
            self.ret = tools.eRet.cancel
        else:
            self.ret = tools.eRet.exit
        self.forceCancelled = True
        return self._end()

    def update(self) -> bool:
        """执行页面更新逻辑
        1. 直接执行事件KEY对应的ACTION，_doEvent方法内部会处理用户事件逻辑
        
        由App._update方法驱动，每次调用只执行一次事件检测和处理
        
        Returns:
            bool: 执行结果
        """
        g = _G.g
        tools = g.Tools()
        log = g.Log()
        try:
            # 检查是否被外部强制取消
            if self.forceCancelled:
                self.forceCancelled = False
                return self._end()
            # 检查超时
            if self._updateTimeout(tools):
                return self._end()
            
            # 事件检测和处理
            event = self.event
            if len(event) == 0:
                event[self.name] = ''
            for key, action in event.items():
                # 直接调用_doEvent处理事件（包括用户事件）
                self.ret = self._doEvent(key, action)
                if self.ret != tools.eRet.none:
                    break
            return self._end()
        except Exception as e:
            log.ex(e, f"执行页面更新循环异常: {self.name}")
            return True
        
    def _end(self)->bool:
        tools = _G.g.Tools()
        bRet = self.ret == tools.eRet.none
        if self.ret == tools.eRet.exit:
            # 正常退出，执行退出逻辑
            self.doExit()
        if not bRet:
            #退出，设置为非运行状态
            self._running = False
        return bRet
    
    def click(self, text: str = '', do: str = ''):
        """模拟点击操作，在PC平台额外执行指定操作
        Args:
            text: 要点击的文本
            do: 要执行的操作，支持以下格式:
                < : 页面跳转到上一页
                >pageName: 跳转到pageName指定的页面
                +d: 收获d金币，如果d不是数字，则收获this.d金币
        """
        g = _G.g
        log = g.Log()
        try:
            text = text.strip() if text else ''
            if text == '@':
                text = self.name
            if text == '':
                # 如果text为空，则尝试从当前页面获取匹配文字
                text = self.data.get('_mt')
                if text is None:
                    log.e("当前没有匹配文字供点击")
                    return False
            tools = g.Tools()
            # 调用tools.click
            log.i(f"点击: {text}")
            tools.click(text)        
            # 在PC平台执行额外操作
            if not tools.isAndroid():
                do = do.strip() if do else ''
                if do == '':
                    do = '@it.back()'
                elif not do.startswith('@'):
                    do = f'@{do}'
                tools.do(do)
                log.i(f"模拟点击:text={text} do:{do} ")
        except Exception as e:
            log.ex(e, f"执行点击操作失败: {text}")
            return False
        return True

_Page_.onLoad()



