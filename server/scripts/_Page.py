import time
import _G
from typing import List, Optional, Dict, Any, Callable
import CChecker
import _Log


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
    def createPage(cls, name, parent=None, matches=None, inAction=None, outAction=None, checkers=None, dialogs=None, timeout=2)->"_Page_":
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
        page = _Page_(name, parent, matches, inAction, outAction, checkers, dialogs, timeout)  # 提供空规则列表作为默认值
        
        # 设置父子关系
        if parent:
            page.parent = parent
            parent.children[name] = page
            
        return page
    
    def __init__(self, name, parent=None, matches=None, inAction=None, outAction=None, checkers=None, dialogs=None, timeout=30):
        self.name = name
        self.matches: list[str] = matches if matches else [] 
        self.parent: Optional["_Page_"] = parent  # 父页面对象
        self.children: dict[str, "_Page_"] = {}  # {name: CPage_对象}
        self.inAction: str = inAction if inAction else ''
        self.outAction: str = outAction if outAction else ''
        # 从配置中创建检查器
        self.checkers = {name: CChecker.CChecker_(name, config, self) for name, config in checkers.items()} if checkers else {}
        self.dialogs: dict[str, dict] = dialogs if dialogs else {}
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

    def findPagesByPath(self, path, visited=None, curPath=None) -> List["_Page_"]:
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
        if curPath is None:
            curPath = [self]
        
        # 如果以"/"开头，从根节点开始查找
        if path.startswith('/'):
            path = path[1:]  # 移除开头的"/"
            root = self
            while root.parent:
                root = root.parent
            return root.findPagesByPath(path)
        
        # 如果路径为空，返回当前页面
        if not path:
            return curPath
        
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
                return curPath + [child]
            else:  # 继续查找下一级
                return child.findPagesByPath(rest_path, visited, curPath + [child])
        
        # 如果在子节点中未找到，尝试在兄弟节点中查找
        if self.parent:
            for sibling in self.parent.getAllChildren():
                if sibling != self and sibling not in visited:
                    if sibling.name == first_part:
                        if len(parts) == 1:  # 最后一级
                            return curPath + [sibling]
                        else:  # 继续查找下一级
                            return sibling.findPagesByPath(rest_path, visited, 
                                                          curPath + [sibling])
        
        # 如果在兄弟节点中也未找到，尝试在父节点中查找
        if self.parent not in visited:
            return self.parent.findPagesByPath(path, visited, 
                                              curPath + [self.parent])
        
        # 如果没有找到，返回None
        return None

    
    def match(self) -> bool: 
        """检查页面规则是否匹配当前屏幕"""
        g = _G._G_
        tools = g.CTools()
        log = g.Log()
        if not self.matches:
            return True
        if tools.android is None:
            # 测试客户端，不执行动作，只打印。
            return True
        try:
            # 刷新屏幕信息
            tools.refreshScreenInfos()        
            # 检查所有规则
            all_passed = True
            for rule in self.matches:
                try:
                    # 如果是代码规则
                    if rule.startswith('{') and rule.endswith('}'):
                        code = rule[1:-1]  # 去掉花括号
                        log.d(f"执行代码规则: {code}")
                        ret = g.Tools().eval(self, code)
                        if not ret:
                            log.d(f"代码规则不匹配: {rule}")
                            all_passed = False
                            break
                    # 如果是文本规则
                    else:
                        log.d(f"检查文本规则: {rule}")
                        ret = tools.matchText(rule)
                        if not ret:
                            log.d(f"文本规则不匹配: {rule}")
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
    
    def detectPage(self, depth=0) -> Optional["_Page_"]:
        """递归检测页面
        Args:   
            page: 要检测的页面
            depth: 当前递归深度
        """
        ret = None
        # 检查当前页面规则
        if self.match():
            ret = self
            # 优先检查子页面
            for child in self.getAllChildren():
                result = child.detectPage(depth + 1)
                if result:
                    ret = result
                    break
        return ret
    
    def go(self, targetPage: "_Page_") -> bool:
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
                    success = tools.eval(self, act)
                else:
                    # 如果进入动作失败，执行默认动作，点击页名
                    success = tools.click(pageName)
            elif self.parent and pageName == self.parent.name:
                log.i(f'<- {pageName}')
                act = self.outAction.strip()
                if act != '':
                    success = tools.eval(self, act)
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
            return success
        except Exception as e:
            log.ex(e, f"跳转失败: {self.name} → {targetPage.name}")
            return False
    
    
    @classmethod
    def toPath(cls, pages) -> str:
        """将页面列表转换为路径字符串"""
        return ' → '.join(page.name for page in pages)
    
    
 
  
