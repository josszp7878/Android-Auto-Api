import time
import _G
from typing import List, Optional  # 添加typing模块导入

# 动作类型枚举
from enum import Enum
class ActionType(Enum):
    CLICK = 'C'
    OPENAPP = 'O'
    SWIPE = 'S'
    BACK = 'B'
    CODE = ''


class _Page_:
    # 类变量
    currentPage = None
    _root = None  # 根页面对象

    @classmethod
    def Root(cls) -> "_Page_":
        log = _G._G_.Log()
        if cls._root is None:
            # log.i('创建根页面++++++++')
            cls._root = cls.createPage("Top")
        # log.i(f'根页面########## {cls._root}')
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
    
    
    @classmethod
    def createPage(cls, name, parent=None, rules=None, inAction=None, outAction=None, alerts=None, timeout=30)->"_Page_":
        """创建页面对象
        
        Args:
            pageName: 页面名称
            parent: 父页面对象
            
        Returns:
            CPage_: 创建的页面对象
        """
        # 检查页面是否已存在
        if parent and name in parent.children:
            return parent.children[name]
            
        # 创建新页面
        page = _Page_(name, parent, rules, inAction, outAction, alerts, timeout)  # 提供空规则列表作为默认值
        
        # 设置父子关系
        if parent:
            page.parent = parent
            parent.children[name] = page
            
        return page
    
    def __init__(self, name, parent=None, rules=None, inAction=None, outAction=None, checkers=None, timeout=30):
        self.name = name
        self.rules: list[str] = rules if rules else []  # 如果rules为None，则使用空列表
        self.parent: Optional["_Page_"] = parent  # 父页面对象
        self.children: dict[str, "_Page_"] = {}  # {name: CPage_对象}
        self.transitions: dict[str, str] = {}  # {actions}
        self.checkWaitTime: float = 1.0  # 默认检查等待时间
        self.inAction: str = inAction if inAction else ''
        self.outAction: str = outAction if outAction else ''
        self.checkers: list[dict] = checkers if checkers else []
        self.timeout: int = timeout  # 默认超时时间
        
        # 如果有父页面，将自己添加为父页面的子页面
        if parent and isinstance(parent, _Page_):
            parent.addChild(self)
    
    def addChild(self, child):
        """添加子页面"""
        self.children[child.name] = child
        return child
    
    def getChild(self, name):
        """获取子页面"""
        return self.children.get(name)
    
    def getAllChildren(self):
        """获取所有子页面"""
        return list(self.children.values())    

    def findPath(self, toPageName):
        """查找从当前页面到目标页面的路径
        
        Args:
            targetName: 目标页面名称
            
        Returns:
            页面对象列表，表示从当前页面到目标页面的路径
        """
        # 先查找目标页面对象
        target_page = self._findPageByName(toPageName)
        if not target_page:
            return None  # 目标页面不存在
        
        # 如果当前页面就是目标页面
        if self.name == toPageName:
            return [self]
        
        # 1. 获取从当前页面到根的路径
        path_to_root_from_current = self._getPathToRoot()
        
        # 2. 获取从目标页面到根的路径
        path_to_root_from_target = target_page._getPathToRoot()
        
        # 3. 找到最低公共祖先(LCA)
        lca = None
        lca_index_current = -1
        lca_index_target = -1
        
        for i, page1 in enumerate(path_to_root_from_current):
            for j, page2 in enumerate(path_to_root_from_target):
                if page1 == page2:  # 找到共同祖先
                    lca = page1
                    lca_index_current = i
                    lca_index_target = j
                    break
            if lca:
                break
        
        if not lca:
            return None  # 没有共同祖先，无法找到路径
        
        # 4. 构建完整路径: 当前页面 -> LCA -> 目标页面
        
        # 从当前页面到LCA的路径
        path_to_lca = path_to_root_from_current[:lca_index_current+1]
        
        # 从LCA到目标页面的路径(需要反转)
        path_from_lca = path_to_root_from_target[:lca_index_target]
        path_from_lca.reverse()
        
        # 完整路径
        complete_path = path_to_lca + path_from_lca
        
        return complete_path

    @classmethod
    def currentPathTo(cls, toPage):
        """查找从当前页面到目标页面的路径"""
        if cls.currentPage is None:
            cls.currentPage = cls.Root()
        log = _G._G_.Log()
        log.i(f'当前页面 {cls.currentPage}')
        path = cls.currentPage.findPath(toPage)
        cls.currentPage = path[-1]
        if path:
            return " → ".join([p.name for p in path])
        return None
    
    def findChild(self, pageName) -> Optional["_Page_"]:
        """在整个页面树中查找指定名称的页面"""
        for child in self.getAllChildren():
            if child.name == pageName:
                return child
            result = child.findChild(pageName)
            if result:
                return result
        return None
    

    def _findPageByName(self, name, visited=None):
        """在整个页面树中查找指定名称的页面
        
        Args:
            name: 页面名称
            visited: 已访问页面集合(内部使用)
            
        Returns:
            找到的页面对象，如果没找到则返回None
        """
        if visited is None:
            visited = set()
        
        if self in visited:
            return None
        visited.add(self)
        
        # 检查当前页面
        if self.name == name:
            return self
        
        # 搜索子页面
        for child in self.getAllChildren():
            result = child._findPageByName(name, visited)
            if result:
                return result
        
        # 搜索父页面
        if self.parent and self.parent not in visited:
            result = self.parent._findPageByName(name, visited)
            if result:
                return result
        
        # 如果这是根页面且没找到，尝试搜索其他应用
        if not self.parent and name != "Top":
            from CApp import CApp_
            for app in CApp_.apps.values():
                if app.rootPage != self and app.rootPage not in visited:
                    result = app.rootPage._findPageByName(name, visited)
                    if result:
                        return result
        
        return None

    def _getPathToRoot(self):
        """获取从当前页面到根页面的路径
        
        Returns:
            页面对象列表，从当前页面到根页面
        """
        path = [self]
        current = self
        
        while current.parent:
            path.append(current.parent)
            current = current.parent
        
        return path

    def findPagesByPath(self, path, visited=None, current_path=None) -> List["_Page_"]:
        """从当前页面开始查找指定路径的页面
        
        Args:
            path: 要查找的页面路径，如 "Settings/Advanced"
                 如果以"/"开头，则从根节点开始查找
            visited: 已访问的页面集合（内部递归使用）
            current_path: 当前路径（内部递归使用）
            
        Returns:
            list: 从当前页面到目标页面的路径列表，未找到则返回None
        """
        if visited is None:
            visited = set()
        if current_path is None:
            current_path = [self]
        
        # 如果以"/"开头，从根节点开始查找
        if path.startswith('/'):
            path = path[1:]  # 移除开头的"/"
            root = self
            while root.parent:
                root = root.parent
            return root.findPagesByPath(path)
        
        # 如果路径为空，返回当前页面
        if not path:
            return current_path
        
        # 分解路径
        parts = path.split('/')
        first_part = parts[0]
        rest_path = '/'.join(parts[1:])
        
        # 标记为已访问
        visited.add(self)
        
        # 先在子节点中查找
        child = self.getChild(first_part)
        if child and child not in visited:
            if len(parts) == 1:  # 最后一级
                return current_path + [child]
            else:  # 继续查找下一级
                return child.findPagesByPath(rest_path, visited, current_path + [child])
        
        # 如果在子节点中未找到，尝试在兄弟节点中查找
        if self.parent:
            for sibling in self.parent.getAllChildren():
                if sibling != self and sibling not in visited:
                    if sibling.name == first_part:
                        if len(parts) == 1:  # 最后一级
                            return current_path + [sibling]
                        else:  # 继续查找下一级
                            return sibling.findPagesByPath(rest_path, visited, 
                                                          current_path + [sibling])
        
        # 如果在兄弟节点中也未找到，尝试在父节点中查找
        if self.parent not in visited:
            return self.parent.findPagesByPath(path, visited, 
                                              current_path + [self.parent])
        
        # 如果没有找到，返回None
        return None

    @classmethod
    def findPagePathFromRoot(cls, path):
        """从根节点开始查找指定路径的页面（类方法）
        
        Args:
            path: 页面的完整路径，如 "Top/Home/Settings"
            
        Returns:
            list: 从根节点到目标页面的路径列表，未找到则返回None
        """
        if not path or not cls.Root():
            return None
        
        # 确保路径以"/"开头
        if not path.startswith('/'):
            path = '/' + path
        
        return cls.Root().findPageByPath(path)
    
    @classmethod
    def checkRules(cls, rules) -> bool: 
        """检查页面规则是否匹配当前屏幕"""
        g = _G._G_
        tools = g.Tools()
        log = g.Log()
        if not rules:
            return True
        if tools.android is None:
            #测试客户端，不执行动作，只打印。
            # log.i(f"检查页面规则：{self.rules}")
            return True
        try:
            # 刷新屏幕信息
            tools.refreshScreenInfos()        
            # 检查所有规则
            all_passed = True
            for rule in rules:
                try:
                    # 如果是代码规则
                    if rule.startswith('{') and rule.endswith('}'):
                        code = rule[1:-1]  # 去掉花括号
                        log.d(f"执行代码规则: {code}")
                        ret = g.Tools().eval(code)
                        if not ret:
                            log.e(f"代码规则不匹配: {rule}")
                            all_passed = False
                            break
                    # 如果是文本规则
                    else:
                        log.d(f"检查文本规则: {rule}")
                        ret = tools.matchScreenText(rule)
                        if not ret:
                            # log.e(f"文本规则不匹配: {rule}")
                            all_passed = False
                            break
                    if not ret:
                        # log.e(f"代码规则不匹配: {rule}")
                        all_passed = False
                        break
                except Exception as e:
                    log.ex(e, f"规则处理失败: {rule}")
                    all_passed = False
                    break
            
            return all_passed
        except Exception as e:
            log.ex(e, f"检查页面规则失败: {self.name}")
            return False
    
    def checkCheckers(self) -> bool:
        """检查应用的检查器"""
        checkers = self.checkers
        if checkers is None or len(checkers) == 0:
            return True
        g = _G._G_
        tools = g.CTools()
        log = g.Log()
        checker = next((checker for checker in checkers if self.checkRules(checker.get("check"))), None)
        if not checker:
            return True
        timeout = checker.get("timeout", -1)
        if timeout > 0:
            #等待指定时间
            time.sleep(timeout)
        elif timeout == 0:
            #等待，当时要读取屏幕上的倒计时信息，根据倒计时信息判断是否退出
            while True:
                time.sleep(1)
                #读取屏幕上的倒计时信息
                text = tools.getScreenText()
                if text.find("倒计时") != -1:
                    #倒计时信息
                    time_str = text.split("倒计时")[1].strip()
                    time_str = time_str.split("秒")[0].strip()
                    time_int = int(time_str)
                    if time_int == 0:
                        break
        tools.evalStr(checker.get("out"))
        time.sleep(2)
        #check是否退出ALERT,如果还没退出，报错，并强制退出
        if _Page_.checkRules(checker.get("check")):
            return True
        else:
            log.e(f"检查器: {checker.get('name')} 未正常退出，强行退出")
            tools.goBack()
            return False

    def doAction(self, actionStr) ->bool:
        """执行到目标页面的动作"""
        if actionStr is None:
            return False
        actionStr = actionStr.strip()
        if actionStr == '':
            return False
        g = _G._G_
        log = g.Log()
        tools = g.CTools()
        
        # 获取动作信息
        log.i(f"执行动作@: {actionStr}")
        # 检查动作字符串中是否包含代码块
        import re
        m = re.search(r'\{\s*(.*?)\s*\}', actionStr)
        if m:
            code = m.group(1)  # 获取花括号内的代码内容
            log.i(f"执行代码块: {code}")
            try:
                result = g.Tools().eval(code)
                return result
            except Exception as e:
                log.ex(e, f"执行代码块失败: {code}")
                return False
        # 判断动作类型        
        m = re.search(r'(?P<action>[^-\s]+)\s*[:：]\s*(?P<target>.*)', actionStr)
        if m:
            action = m.group('action')
            target = m.group('target')
            # 根据动作类型执行相应操作
            if action == ActionType.CLICK.value:
                return tools.click(target)
            elif action == ActionType.OPENAPP.value:
                # 打开应用
                is_home = tools.isHome()
                if not is_home:
                    log.e("不在主屏幕，无法打开应用")
                    return False                
                return tools.click(target, waitTime=2)
            elif action == ActionType.SWIPE.value:
                return tools.swipe(target)
            elif action == ActionType.BACK.value:
                return tools.goBack()
        else:
            return tools.click(actionStr)     
    
    def go(self, targetPage: "_Page_", waitTime=None) -> bool:
        """跳转到目标页面并验证结果"""
        try:
            g = _G._G_
            log = g.Log()
            tools = g.CTools()
            # 判断跳转方向
            pageName = targetPage.name
            success = False
            # log.i(f"跳转页面: {pageName}")
            if pageName in self.children:
                log.i(f'-> {pageName}')
                act = targetPage.inAction.strip()
                if act != '':
                    success = self.doAction(act)
                else:
                    # 如果进入动作失败，执行默认动作，点击页名
                    success = tools.click(pageName)
            elif self.parent and pageName == self.parent.name:
                log.i(f'<- {pageName}')
                act = self.outAction.strip()
                if act != '':
                    success = self.doAction(act)
                else:
                    success = tools.goBack()
                if not success:
                    # 如果离开动作失败，执行默认动作，返回
                    success = tools.goBack()
            else:
                #先返回父页面，再执行进入目标兄弟页面
                success = self.go(self.parent)
                if not success:
                    log.e(f"返回父页面失败: {self.name}")
                    return False
                return self.parent.go(targetPage)
            # 执行动作
            if not success:
                return False
            # log.i(f"检查弹窗: {targetPage.alerts}")
            targetPage.checkCheckers()
            # 等待指定时间
            wait_time = waitTime if waitTime is not None else self.timeout
            if wait_time > 0:
                # log.i(f"... {wait_time} 秒后检查页面")
                time.sleep(wait_time)
            # 验证目标页面
            if targetPage.checkRules(targetPage.rules):
                # log.i(f"成功跳转到 {targetPage.name}")
                # 更新当前页面
                _Page_.setCurrent(targetPage)
                return targetPage
            else:
                log.e(f"未能验证目标页面 {targetPage.name}")
                return None
        except Exception as e:
            log.ex(e, f"跳转失败: {self.name} → {targetPage.name}")
            return None
    
    
    @classmethod
    def toPath(cls, pages) -> str:
        """将页面列表转换为路径字符串"""
        return ' → '.join(page.name for page in pages)
    
    def setRules(self, rules):
        """设置页面规则
        
        Args:
            rules: 页面规则列表
        """
        self.rules = rules
        return self
    
    def setTimeout(self, timeout):
        """设置页面超时时间
        
        Args:
            timeout: 超时时间（秒）
        """
        self.timeout = timeout
        return self
    
    def setInAction(self, action):
        """设置进入页面的动作
        
        Args:
            action: 动作字符串
        """
        self.inAction = action
        return self
    
    def setOutAction(self, action):
        """设置离开页面的动作
        
        Args:
            action: 动作字符串
        """
        self.outAction = action
        return self
    
    @classmethod
    def detectPage(cls, page, depth=0) -> Optional["_Page_"]:
        """递归检测页面
        Args:
            page: 要检测的页面
            depth: 当前递归深度
        """
        # 检查当前页面规则
        if page.checkRules(page.rules):
            # 优先检查子页面
            for child in page.getAllChildren():
                result = cls.detectPage(child, depth + 1)
                if result:
                    return result
            return page
        return None
  