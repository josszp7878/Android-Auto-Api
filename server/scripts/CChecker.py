# import copy
# from typing import Dict, Any, List, Optional, TYPE_CHECKING
# import _G
# if TYPE_CHECKING:
#     from _Tools import _Tools_
# import threading
# import time
# import re

# g = _G.g
# log = g.Log()


# class _Page_:
#     """页面类，用于验证页面状态并执行相应操作"""
#     # 线程安全锁
#     _lock = threading.Lock()
    
#     # 页面类相关的类变量
#     currentPage = None  # 当前页面
#     _root = None        # 根页面对象
    
#     # 默认值实例，在类初始化时创建
#     _DEFAULT = None
    
#     # 默认配置
#     _DEFAULT_CONFIG = {
#         'name': '',
#         'match': None,
#         'childs': None,
#         'event': {},
#         'timeout': 0,
#         'type': 'once',
#         'entry': None,
#         'exit': None
#     }
    
#     @classmethod
#     def Default(cls) -> "_Page_":
#         """获取默认配置实例"""
#         if cls._DEFAULT is None:
#             # 创建默认实例
#             cls._DEFAULT = cls("__default__")
#         return cls._DEFAULT
    
#     @classmethod
#     def Root(cls) -> "_Page_":
#         """获取根页面对象"""
#         if cls._root is None:
#             cls._root = cls.createPage("Top")
#         return cls._root
    
#     @classmethod
#     def setCurrent(cls, page) -> "_Page_":
#         """设置当前页面"""
#         cls.currentPage = page
#         return page
    
#     @classmethod
#     def getCurrent(cls) -> "_Page_":
#         """获取当前页面"""
#         return cls.currentPage
    
#     # @classmethod
#     # def createPage(cls, name, parent=None, inAction=None, outAction=None) -> "CChecker_":
#     #     """创建页面对象
        
#     #     Args:
#     #         name: 页面名称
#     #         parent: 父页面对象（可选）
#     #         inAction: 进入页面的操作（可选）
#     #         outAction: 离开页面的操作（可选）
            
#     #     Returns:
#     #         CChecker_: 创建的页面对象
#     #     """
#     #     # 检查页面是否已存在于父页面的toPages中
#     #     if parent and name in parent.toPages:
#     #         return parent.toPages[name]
            
#     #     # 创建新页面
#     #     page = cls(name, None, None)
        
#     #     # 设置页面特有的属性
#     #     page.inAction = inAction if inAction else ''
#     #     page.outAction = outAction if outAction else ''
        
#     #     # 设置父子关系
#     #     if parent and isinstance(parent, cls):
#     #         # 父页面的toPages指向当前页面
#     #         parent.toPages[name] = page
#     #         # 当前页面的fromPages指向父页面
#     #         page.fromPages[parent.name] = parent
            
#     #     return page

#     def __init__(self, name: str, config: Dict[str, Any] = None, data=None):
#         """初始化检查器，直接定义默认值

#         Args:
#             name: 检查器名称
#             config: 检查器配置字典
#             data: 检查器数据(可选)
#         """
#         # 初始化配置字典
#         self._config = self._DEFAULT_CONFIG.copy()
#         self._config['name'] = name.lower()
        
#         # 运行时属性（不会被序列化）
#         self.data = data or {}    # 附加数据
#         self.pastTime = 0         # 已运行时间
#         self.startTime = 0        # 开始时间
#         self.lastTime = 0         # 上次检查时间
#         self._enabled = False     # 是否启用
#         self.children = []        # 存储由当前检查器启动的子检查器
#         self.childThreads = []    # 存储子检查器的线程
#         self.executedEvents = set()  # 记录已执行的事件
#         self.ret = g.Tools().eRet.none  # 返回值，现在直接存储DoRet枚举
#         self.forceCancelled = False  # 是否被外部强制取消标志
        
#         # 页面相关属性
#         self.inAction = ''        # 进入页面的操作
#         self.outAction = ''       # 离开页面的操作

#         # 在原有基础上添加_Page_类的属性
#         self._checker = self  # 页面与检查器自身相关联
        
#         # 原有CChecker_类的属性初始化
#         self.isTemplate = True
#         self.running = False
#         self.thread = None

#         if data is not None:
#             self.data = data

#     @property
#     def config(self) -> Dict[str, Any]:
#         return self._config

#     @property
#     def name(self) -> str:
#         return self._config['name']
    
#     @name.setter
#     def name(self, value: str):
#         self._config['name'] = value.lower()

    
#     @property
#     def match(self) -> str:
#         return self._config['match'] or self.name.split('-')[-1]
    
#     @match.setter
#     def match(self, value: str):
#         self._config['match'] = value

#     @property
#     def childs(self) -> List[str]:
#         return self._config['childs']
    
#     @childs.setter
#     def childs(self, value: List[str]):
#         self._config['childs'] = value

#     @property
#     def event(self) -> Dict[str, Any]:
#         return self._config['event']
    
#     @event.setter
#     def event(self, value: Dict[str, Any]):
#         self._config['event'] = value.copy() if isinstance(value, dict) else {}

#     @property
#     def timeout(self) -> int:
#         return self._config['timeout']
    
#     @timeout.setter
#     def timeout(self, value: int):
#         self._config['timeout'] = value

#     @property
#     def type(self) -> str:
#         return self._config['type']
    
#     @type.setter
#     def type(self, value: str):
#         self._config['type'] = value

#     @property
#     def entry(self) -> Dict[str, Any]:
#         return self._config['entry']
    
#     @entry.setter
#     def entry(self, value: Dict[str, Any]):
#         self._config['entry'] = value

#     @property
#     def exit(self) -> Dict[str, Any]:
#         return self._config['exit']
    
#     @exit.setter
#     def exit(self, value: Dict[str, Any]):
#         self._config['exit'] = value

#     def __str__(self):
#         return f"{self.name} {self.match}"

#     @property
#     def enabled(self) -> bool:
#         return self._enabled
    
#     @enabled.setter
#     def enabled(self, value: bool):
#         self._enabled = value
#         log.d(f"设置检查器 {self.name} 状态为 {value}")
#         if value:
#             self.startTime = time.time()
#             self.lastTime = 0
    
#     def addProp(self, prop: str, value: str, value1: str = None) -> bool:
#         log = _G.g.Log()
#         try:    
#             if 'mat' in prop:
#                 oldVal = self._config['match']
#                 split = '&|'
#                 if value.startswith('|'):
#                     split = '|&'
#                     value = value[1:]
#                 elif value.startswith('&'):
#                     value = value[1:]
#                 range = _Page_.parseMatchRange(self._config['match'], value1)
#                 value = _Page_._addStrListProp(
#                     self._config['match'], split, value, range)
#                 if value:
#                     self._config['match'] = value
#                     log.d(f"_match: {oldVal} => {self._config['match']}")
#             elif 'event' in prop:
#                 oldVal = self._config['event']
#                 self._config['event'][value] = value1
#                 log.d(f"event: {oldVal} => {self._config['event']}")
#             elif 'entry' in prop:
#                 oldVal = self._config['entry']
#                 self._config['entry'][value] = value1
#                 log.d(f"entry: {oldVal} => {self._config['entry']}")
#             elif 'exit' in prop:
#                 oldVal = self._config['exit']
#                 self._config['exit'] = value
#                 log.d(f"exit: {oldVal} => {self._config['exit']}")
#             else:
#                 log.e(f"不支持add的属性: {prop}")
#                 return False
#             return True
#         except Exception as e:
#             log.ex(e, f"add{prop}失败: {value}")
#             return False
        
#     def removeProp(self, prop: str, value: str) -> bool:
#         """删除指定属性
#         Args:
#             prop: 属性名
#             value: 要删除的值
#         Returns:
#             bool: 删除是否成功
#         """
#         log = _G.g.Log()
#         try:    
#             if 'mat' in prop:
#                 oldVal = self._config['match']
#                 value = value.strip('&').strip('|')
#                 value = _Page_._delStrListProp(self._config['match'], '&|', value)
#                 if value:
#                     self._config['match'] = value
#                     log.d(f"_match: {oldVal} => {self._config['match']}")
#             elif 'chi' in prop or 'che' in prop:  # 兼容旧命令
#                 oldVal = self._config['childs']
#                 split = ','
#                 value = value.strip(split)
#                 value = _Page_._delStrListProp(self._config['childs'], split, value)
#                 if value:
#                     self._config['childs'] = value
#                     log.d(f"_childs: {oldVal} => {self._config['childs']}")
#             elif 'event' in prop:
#                 oldVal = self._config['event']
#                 self._config['event'].pop(value)
#                 log.d(f"event: {oldVal} => {self._config['event']}")
#             elif 'entry' in prop:
#                 oldVal = self._config['entry']
#                 self._config['entry'].pop(value)
#                 log.d(f"entry: {oldVal} => {self._config['entry']}")
#             elif 'exit' in prop:
#                 oldVal = self._config['exit']
#                 self._config['exit'] = ""
#                 log.d(f"exit: {oldVal} => {self._config['exit']}")
#             else:
#                 log.e(f"不支持remove的属性: {prop}")
#                 return False
#             return True
#         except Exception as e:
#             log.ex(e, f"remove{prop}失败: {value}")
#             return False
  

        
#     @classmethod
#     def parseMatchRange(cls, match: str, range: str = None):
#         """解析match的范围
#         Args:
#             match: 要解析的范围的文字
#             range: 范围，可以是坐标，也可以是偏移量. 如果为'_'，则从当前屏幕获取match文字对应的坐标
#         Returns:
#             str: 范围
#         """
#         if not range:
#             return range  
#         tools = g.Tools()
#         # 从当前屏幕获取match文字对应的坐标
#         pos = tools.findTextPos(match)
#         DEF = 75
#         if range == '_':
#             return f'{pos[0]-DEF},{pos[1]-DEF},{pos[0]+DEF},{pos[1]+DEF}'
#         sX, sY = range.split(',') if range else (0, 0)
#         x = int(sX) if sX else 0
#         y = int(sY) if sY else 0
#         if x > 0 or y > 0:

#             if pos:
#                 if x > 0 and y > 0:
#                     range = f'{pos[0] - x},{pos[1]-y},{pos[0]+x},{pos[1]+y}'
#                 elif x > 0:
#                     range = f'{pos[0] - x},{pos[0]+x}'
#                 elif y > 0:
#                     range = f'{pos[1] - y},{pos[1]+y}'
#             else:
#                 return f"e~当前页面未找到{match}文字"
#         return range
    
#     @classmethod
#     def _addStrListProp(cls, curVal: str, split: str, value: str, 
#                         range: str = None):
#         # 为了支持已有ITEM的替换，先将match转换为列表
#         newValue = f'{value}{range}' if range else value
#         if newValue == curVal:
#             return None
#         if curVal:
#             m = re.search(rf'[{split}\s]*{value}[^{split}]*', curVal)
#             newValue = f'{split[0]}{newValue}'
#             if m:
#                 curVal = curVal.replace(m.group(0), newValue)
#             else:                
#                 curVal = f'{curVal}{newValue}'
#         else:
#             curVal = newValue
#         return curVal
    
#     @classmethod
#     def _delStrListProp(cls, curVal: str, split: str, value: str):
#         # 为了支持已有ITEM的替换，先将match转换为列表
#         if curVal:
#             return re.sub(rf'[{split}\s]*{value}', '', curVal)
#         return curVal


#     # 兼容旧代码
#     @property
#     def checks(self) -> List[str]:
#         return self._config['childs']

#     @checks.setter
#     def checks(self, value: List[str]):
#         self._config['childs'] = value

#     @enabled.setter
#     def enabled(self, value: bool):
#         self._enabled = value
#         log.d(f"设置检查器 {self.name} 状态为 {value}")
#         if value:
#             self.startTime = time.time()
#             self.lastTime = 0
    
#     def Match(self) -> bool:
#         """执行检查逻辑
#         Returns:
#             bool: 检查是否通过
#         """
#         result = False
#         try:
#             tools = g.Tools()
#             log.d(f"{self.name}.Match")
#             match = self.match
#             if match == '':
#                 return True
#             # log.d(f"匹配: {match}")
#             result, _ = tools.check(self, f'@{match}')
#         except Exception as e:
#             log.ex(e, f"匹配失败: {match}")
#             result = False
#         return result
    
    
#     # 执行操作
#     def Do(self) -> '_Tools_.eRet':
#         try:
#             events = self._config['event'].items() if self._config['event'] else []
#             tools = g.Tools()
#             ret = tools.eRet.none
#             if len(events) == 0: 
#                 # 没有操作，直接点击match
#                 if tools.click(self.match):
#                     ret = tools.eRet.end
#             else:
#                 for key, action in events:
#                     # 如果该事件已执行过，则跳过
#                     if key in self.executedEvents:
#                         continue
#                     key = key.strip()
#                     execute = False
#                     m = None
                    
#                     # 处理不同类型的key
#                     if key.startswith('%'):
#                         # 概率执行：%30 表示30%的概率执行
#                         try:
#                             probability = int(key[1:])
#                             import random
#                             execute = random.randint(1, 100) <= probability
#                             log.d(f"概率执行({probability}%): {execute}")
#                             # 概率事件无论是否执行，都标记为已处理，避免重复触发
#                             self.executedEvents.add(key)
#                         except Exception as e:
#                             log.ex(e, f"解析概率失败: {key}")
#                             continue
#                     elif key.startswith('-'):
#                         # 延时执行：-5 表示延时5秒后执行
#                         try:
#                             delay = int(key[1:])
#                             log.d(f"延时执行({delay}秒)")
#                             time.sleep(delay)
#                             execute = True
#                             # 延时事件执行后标记为已处理
#                             self.executedEvents.add(key)
#                         except Exception as e:
#                             log.ex(e, f"解析延时失败: {key}")
#                             continue
#                     elif key == '':
#                         # 无条件执行一次
#                         execute = True
#                         log.d("无条件执行")
#                         # 无条件事件执行后标记为已处理
#                         self.executedEvents.add(key)
#                     else:
#                         # 屏幕匹配文本，如果匹配到则执行
#                         execute, m = tools.check(self, key)
#                         # 处理正则表达式捕获组
#                         if execute and isinstance(m, re.Match):
#                             # 将匹配的命名捕获组添加到data中
#                             for k, v in m.groupdict().items():
#                                 self.set(k, v)
#                     # 如果条件满足，执行action
#                     if execute:
#                         action = action.strip() if action else ''
#                         if action == '':
#                             # 空操作默认为点击
#                             if m:
#                                 tools.click(key)
#                         else:
#                             ret = tools.do(self, action)                      
#                         # 文本匹配类型的事件执行后标记为已处理
#                         if m is not None:
#                             self.executedEvents.add(key)                
#                 # log.d(f"{self.name}.Do: {ret}")
#                 if ret != tools.eRet.exit:
#                     ret = tools.eRet.none
#                 return ret
#         except Exception as e:
#             log.ex(e, f"执行操作失败: {self._config['event']}")
#             return tools.eRet.error

   
#     @classmethod
#     def getTemplates(cls, pattern: str) -> List["_Page_"]:
#         """获取匹配指定模式的模板列表"""
#         from _App import _App_
        
#         # 获取所有应用的所有模板
#         all_templates = []
#         for app_name in _App_._templates.keys():
#             templates = _App_._templates[app_name]
#             all_templates.extend(templates)
            
#         # 筛选匹配模式的模板
#         pattern = pattern.lower()
#         return [t for t in all_templates if pattern in t.name.lower()]
        
#     @classmethod
#     def delTemplate(cls, checkName: str = None) -> bool:
#         """删除检查器模板"""
#         from _App import _App_
        
#         if not checkName:
#             return False
            
#         # 解析检查器名称，获取应用名和检查器名
#         checkName = checkName.strip().lower()
#         if _App_.PathSplit in checkName:
#             app_name, checker_name = checkName.split(_App_.PathSplit, 1)
#         else:
#             # 使用当前应用
#             app_name = _App_.curName()
#             checker_name = checkName
            
#         # 构建完整名称
#         full_name = f"{app_name}{_App_.PathSplit}{checker_name}"
            
#         # 在模板列表中查找匹配的模板
#         templates = _App_._templates.get(app_name, [])
#         for i, template in enumerate(templates):
#             if template.name.lower() == full_name:
#                 # 找到匹配的模板，删除它
#                 del templates[i]
                
#                 # 如果不是临时模板，保存配置
#                 if template.type != 'temp':
#                     app = _App_.getApp(app_name, False)
#                     if app:
#                         app.saveConfig()
#                 return True
                
#         return False
        
#     @classmethod
#     def onLoad(cls, oldCls=None):
#         """热加载时的处理"""
#         from _App import _App_
        
#         log.i("加载CChecker")
#         # 使用_App_类的loadConfig方法加载配置
#         _App_.loadConfig()
    
#     @classmethod
#     def getInst(cls, checkerName: str, config: Dict[str, Any] = None, 
#                 create: bool = True) -> Optional["_Page_"]:
#         """获取指定名称的检查器，此方法现在由App类调用
        
#         Args:
#             checkerName: 检查器名称
#             config: 检查器配置
#             create: 如果不存在是否创建
            
#         Returns:
#             CChecker_: 检查器实例，如果不存在且不创建则返回None
#         """
#         checkerName = checkerName.lower()
#         template = g.App().getChecker(checkerName)
#         if not template:
#             log.e(f"{checkerName} 未定义")
#             return None
            
#         # 创建新的检查器实例
#         if create:
#             # 创建新的运行时检查器
#             checker = cls(checkerName)
#             # 深度复制模板配置
#             checker._config = copy.deepcopy(template._config)
            
#             # 更新额外参数
#             if config:
#                 for k, v in config.items():
#                     if k in checker._config:
#                         if isinstance(v, dict):
#                             checker._config[k] = v.copy()
#                         else:
#                             checker._config[k] = v
#             return checker
#         return None
    
#     def begin(self, params: Dict[str, Any] = None) -> threading.Thread:
#         """异步执行checker.begin()
#         """
#         thread = threading.Thread(target=self._begin, args=(params,))
#         thread.start()
#         return thread

#     def _begin(self, params: Dict[str, Any] = None):
#         """执行检查器
#         """
#         tools = g.Tools()
#         try:
#             if params:
#                 for k, v in params.items():
#                     setattr(self, k, v)
#             self._stopAllChildren()            
#             # 确保ret一开始为none，重置强制取消状态
#             ret = tools.eRet.none
#             self.forceCancelled = False
#             if self._onEnter():
#                 # 启动子检查器
#                 self._startChildren()
#                 ret = self._update()
#                 # 首先检查是否被强制取消，如果是则跳过退出逻辑
#                 if ret == tools.eRet.cancel:
#                     # 不执行退出逻辑
#                     pass
#                 else:
#                     # 只有当返回值不是error和cancel时才执行退出逻辑
#                     if ret != tools.eRet.error:
#                         self._onExit()
#             else:
#                 log.d(f"检查器 {self.name} 入口检查未通过")
#             self.ret = ret
#         except Exception as e:
#             log.ex(e, f"执行检查器异常: {self.name}")
#             self.ret = tools.eRet.error
#         finally:
#             self._exit()
    
#     def _exit(self):
#         """退出检查器"""
#         log.d(f"退出 {self.name}")
#         self._stopAllChildren()

#     def _onExit(self):
#         """执行出口逻辑"""
#         log.d(f"执行出口逻辑: {self.name}")
#         tools = g.Tools()
#         tools.do(self, self._config['exit'])

#     def _onEnter(self) -> bool:
#         """执行入口代码
#         根据当前页面名称执行对应的entry代码，然后进行match匹配
#         Returns:
#             bool: 入口执行是否成功
#         """
#         try:
#             entryMap = self._config['entry']
#             # 对entryMap里面的KEY进行tools.do(),根据返回决定是否执行对应的value.
#             # 如果key为空，则直接执行。
#             tools = g.Tools()
#             for key, code in entryMap.items():
#                 ret = key == '' or tools.check(self, key)[0]
#                 if ret:
#                     ret = tools.do(self, code)
#                     log.d(f"执行入口代码: {key}=>{code}=>{ret}")
#                     if ret == tools.eRet.exit:
#                         return False
#             # 如果entry执行成功，延时3秒后进行匹配
#             time.sleep(3)
#             return self.Match()
#         except Exception as e:
#             log.ex(e, f"执行入口代码异常: {self.name}")
#             return False
    
#     def _update(self) -> '_Tools_.eRet':
#         """执行检查器更新逻辑
#         0. 循环判定基于checker的enable属性
#         1. 匹配event是否存在，成功则执行对应逻辑
#         2. 匹配childs里的子检查器，匹配成功则异步执行对应update()
#         3. 如果timeout为正数，判定超时，超时直接跳出更新循环
#         4. 通过设置enable为False可以结束checker生命周期
#         5. 循环跳出后，停止所有子检查器并执行出口逻辑
#         Returns:
#             '_Tools_.eRet': 执行结果
#         """
#         startTime = time.time()
#         self._enabled = True
#         self.children = []
#         self.childThreads = []
#         self.executedEvents = set()  # 重置已执行事件记录
#         tools = g.Tools()
#         ret = tools.eRet.none
#         try:
#             # 主循环，条件是检查器启用状态
#             while self._enabled:
#                 # 首先检查是否被外部强制取消
#                 if self.forceCancelled:
#                     ret = tools.eRet.cancel
#                     break
#                 if self.timeout > 0:
#                     currentTime = time.time()
#                     elapsedTime = currentTime - startTime
#                     if elapsedTime > self.timeout:
#                         log.d(f"checker {self.name} 超时")
#                         ret = tools.eRet.timeout
#                         break
#                 # 执行检查器操作
#                 ret = self.Do()
#                 if ret != tools.eRet.none:
#                     break
#                 time.sleep(1) 
#             return ret
#         except Exception as e:
#             log.ex(e, f"执行检查器更新循环异常: {self.name}")
#             ret = tools.eRet.error
#         finally:
#             # 确保更新结束时禁用检查器
#             self._enabled = False
#             # 再次确保所有子检查器都被停止
#             self._stopAllChildren()
#         return ret

    
#     def _startChildren(self):
#         """启动子检查器"""
#         if self._config['childs']:
#             for childName in self._config['childs'].split(','):
#                 childName = childName.strip()
#                 if not childName:
#                     continue
#                 try:
#                     # 获取当前应用
#                     App = g.App()
#                     curApp = App.cur()
#                     if not curApp:
#                         log.e("未找到当前应用，无法启动子检查器")
#                         continue
                        
#                     # 使用应用的run方法启动子检查器
#                     if curApp.run(childName):
#                         # 查找已创建的检查器实例
#                         for child in curApp._checkers:
#                             if child.name.lower() == childName.lower():
#                                 # 添加到子检查器列表
#                                 self.children.append(child)
#                                 break
#                 except Exception as e:
#                     log.ex(e, f"{childName}启动失败: ")

#     def _stopAllChildren(self):
#         """停止所有子检查器"""
#         try:
#             # 获取当前应用
#             App = g.App()
#             curApp = App.cur()
#             if not curApp:
#                 log.e("未找到当前应用，无法停止子检查器")
#                 return
                
#             # 获取子检查器名称列表
#             childNames = [child.name for child in self.children]
            
#             # 使用应用的stop方法停止子检查器
#             for childName in childNames:
#                 curApp.stop(childName)
                
#             # 清空子检查器和线程列表
#             self.children = []
#             self.childThreads = []
#         except Exception as e:
#             log.ex(e, "停止子检查器失败")

#     # def addChild(self, child):
#     #     """添加子页面（使用toPages实现）"""
#     #     self.toPages[child.name] = child
#     #     child.fromPages[self.name] = self
#     #     return child
    
#     # def getChild(self, name):
#     #     """获取子页面（从toPages中获取）"""
#     #     return self.toPages.get(name)

#     def findPath(self, toPageName):
#         """查找从当前页面到目标页面的路径
        
#         Args:
#             toPageName: 目标页面名称
            
#         Returns:
#             页面对象列表，表示从当前页面到目标页面的路径
#         """
#         # 先查找目标页面对象
#         target = self._findPageByName(toPageName)
#         if not target:
#             return None  # 目标页面不存在
        
#         # 如果当前页面就是目标页面
#         if self.name == toPageName:
#             return [self]
        
#         # 广度优先搜索找到最短路径
#         queue = [(self, [self])]  # (当前页面, 路径)
#         visited = {self}
        
#         while queue:
#             current, path = queue.pop(0)
            
#             # 检查当前页面是否就是目标页面
#             if current == target:
#                 return path
            
#             # 检查子页面
#             for childName in current._config['entry'].keys():
#                 child = current.getChecker(childName)
#                 if child not in visited:
#                     visited.add(child)
#                     queue.append((child, path + [child]))
                    
#             # 检查父页面
#             for parentName in current._config['exit'].keys():
#                 parent = current.getChecker(parentName)
#                 if parent not in visited:
#                     visited.add(parent)
#                     queue.append((parent, path + [parent]))
        
#         # 如果没有找到路径，尝试通过其他应用查找
#         if toPageName != "Top":
#             from _App import _App_
#             for _, app in _App_.apps.items():
#                 if app.rootPage != current and app.rootPage not in visited:
#                     # 从其他应用的根页面重新搜索
#                     other_path = app.rootPage.findPath(toPageName)
#                     if other_path:
#                         return [self] + other_path
        
#         return None  # 没有找到路径

#     @classmethod
#     def currentPathTo(cls, toPage):
#         """查找从当前页面到目标页面的路径"""
#         if cls.currentPage is None:
#             cls.currentPage = cls.Root()
#         log.i(f'当前页面 {cls.currentPage}')
#         path = cls.currentPage.findPath(toPage)
#         cls.currentPage = path[-1] if path else cls.currentPage
#         if path:
#             return cls.toPath(path)
#         return None
    
#     def findChild(self, pageName) -> Optional["_Page_"]:
#         """在整个页面树中查找指定名称的页面"""
#         # 先在直接子页面中查找
#         if pageName in self.toPages:
#             return self.toPages[pageName]
        
#         # 递归查找子页面的子页面
#         for child in self.toPages.values():
#             result = child.findChild(pageName)
#             if result:
#                 return result
                
#         return None
    
#     def _findPageByName(self, name, visited=None):
#         """在整个页面树中查找指定名称的页面
        
#         Args:
#             name: 页面名称
#             visited: 已访问页面集合(内部使用)
            
#         Returns:
#             找到的页面对象，如果没找到则返回None
#         """
#         if visited is None:
#             visited = set()
        
#         if self in visited:
#             return None
#         visited.add(self)
        
#         # 检查当前页面
#         if self.name == name:
#             return self
        
#         # 搜索子页面
#         for child in self.toPages.values():
#             result = child._findPageByName(name, visited)
#             if result:
#                 return result
        
#         # 搜索父页面
#         for parentName in self._config['exit'].keys():
#             parent = self.getChecker(parentName)
#             if parent not in visited:
#                 result = parent._findPageByName(name, visited)
#                 if result:
#                     return result
        
#         # 如果这是根页面且没找到，尝试搜索其他应用
#         if len(self._config['entry']) > 0 and name != "Top":
#             from _App import _App_
#             for app in _App_.apps.values():
#                 if app.rootPage != self and app.rootPage not in visited:
#                     result = app.rootPage._findPageByName(name, visited)
#                     if result:
#                         return result
        
#         return None

#     def _getPathToRoot(self):
#         """获取从当前页面到根页面的路径"""
#         path = [self]
#         current = self
        
#         # 循环查找父页面，直到找到根页面
#         while current._config['entry']:
#             # 如果有多个父页面，选择第一个
#             parentName = next(iter(current._config['entry'].keys()))
#             parent = current.getChecker(parentName)
#             path.append(parent)
#             current = parent
            
#             # 防止循环引用导致的无限循环
#             if parent in path[:-1]:
#                 break
        
#         return path

#     def getAllChildren(self):
#         """获取所有子页面"""
#         return list(self.toPages.values())

#     def go(self, targetPage: "_Page_") -> bool:
#         """跳转到目标页面
        
#         Args:
#             targetPage: 目标页面对象
            
#         Returns:
#             bool: 是否成功跳转到目标页面
#         """
#         if targetPage is None:
#             log.w("目标页面为空，无法跳转")
#             return False
            
#         # 如果已经在目标页面，直接返回成功
#         if self == targetPage:
#             return True
            
#         # 查找从当前页面到目标页面的路径
#         path = self.findPath(targetPage.name)
#         if not path:
#             log.w(f"找不到从{self.name}到{targetPage.name}的路径")
#             return False
            
#         # 执行路径上的跳转操作
#         current = self
#         for i in range(1, len(path)):
#             nextPage = path[i]
#             # 检查是否有直接关联
#             if nextPage.name not in current._config['entry'].keys() and current.name not in nextPage._config['exit'].keys():
#                 log.w(f"页面{current.name}和{nextPage.name}之间没有直接关联")
#                 return False
                
#             # 执行离开当前页面的操作
#             if current.outAction:
#                 tools = _G.g.Tools()
#                 ret = tools.do(current.outAction)
#                 if ret != tools.DoRet.none and ret != tools.DoRet.ok:
#                     log.w(f"执行离开{current.name}页面的操作失败: {current.outAction}")
#                     return False
                    
#             # 执行进入下一个页面的操作
#             if nextPage.inAction:
#                 tools = _G.g.Tools()
#                 ret = tools.do(nextPage.inAction)
#                 if ret != tools.DoRet.none and ret != tools.DoRet.ok:
#                     log.w(f"执行进入{nextPage.name}页面的操作失败: {nextPage.inAction}")
#                     return False
                    
#             # 更新当前页面
#             current = nextPage
#             _Page_.setCurrent(current)
            
#         return True

#     @classmethod
#     def toPath(cls, pages) -> str:
#         """将页面对象列表转换为路径字符串"""
#         if not pages:
#             return ""
#         return " → ".join([p.name for p in pages])
    
#     def match(self) -> bool:
#         """检查当前页面是否匹配屏幕状态"""
#         # 直接调用关联的checker的Match方法
#         return self.Match()

# _Page_.onLoad()



