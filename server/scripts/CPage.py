import time
import _G
import CTools
from typing import List, Optional  # 添加typing模块导入

# 动作类型枚举
from enum import Enum
class ActionType(Enum):
    CLICK = 'C'
    OPENAPP = 'O'
    SWIPE = 'S'
    BACK = 'B'
    CODE = ''

class CPage_:
    # 类变量
    currentPage = None
    ROOT = None  # 根页面对象
    UNKNOWN_PAGE = 'unknown'
    
    @classmethod
    def setCurrent(cls, page) -> "CPage_":
        """设置当前页面"""
        cls.currentPage = page
        return page
    
    @classmethod
    def getCurrent(cls) -> "CPage_":
        """获取当前页面"""
        return cls.currentPage
    
    @classmethod
    def setRoot(cls, page) -> "CPage_":
        """设置根页面"""
        cls.ROOT = page
        return page
    
    @classmethod
    def getRoot(cls) -> "CPage_":
        """获取根页面"""
        return cls.ROOT
    
    def __init__(self, name, rules, parent=None):
        self.name = name
        self.rules = rules  
        self.parent = parent  # 父页面对象
        self.children = {}  # {name: CPage_对象}
        self.transitions = {}  # {actions}
        self.checkWaitTime = 1.0  # 默认检查等待时间
        
        # 如果有父页面，将自己添加为父页面的子页面
        if parent and isinstance(parent, CPage_):
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

    def findPath(self, targetName, path=None, visited=None):
        """查找路径（纯树形结构遍历）"""
        if path is None:
            path = []
        if visited is None:
            visited = set()

        # 防止循环
        if self in visited:
            return None
        visited.add(self)

        current_path = path + [self]

        # 找到目标
        if self.name == targetName:
            return current_path

        # 优先查找子节点
        for child in self.getAllChildren():
            result = child.findPath(targetName, current_path, visited.copy())
            if result:
                return result

        # 查找父节点和兄弟节点
        if self.parent:
            # 向上查找父节点的其他子节点（兄弟节点）
            for sibling in self.parent.getAllChildren():
                if sibling != self and sibling not in visited:
                    result = sibling.findPath(targetName, current_path, visited.copy())
                    if result:
                        return result

            # 继续向上查找父节点的路径
            result = self.parent.findPath(targetName, current_path, visited.copy())
            if result:
                return result

        # 全局查找其他应用的页面（通过CApp获取所有根页面）
        from CApp import CApp_
        for app in CApp_.apps.values():
            if app.rootPage not in visited:
                result = app.rootPage.findPath(targetName, current_path, visited.copy())
                if result:
                    return result

        return None
    
    def findPagesByPath(self, path, visited=None, current_path=None) -> List["CPage_"]:
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
        if not path or not cls.ROOT:
            return None
        
        # 确保路径以"/"开头
        if not path.startswith('/'):
            path = '/' + path
        
        return cls.ROOT.findPageByPath(path)
    
    def checkRules(self):
        """检查页面规则是否匹配当前屏幕"""
        g = _G._G_
        tools = g.CTools()
        log = g.Log()
        
        if not self.rules:
            log.w(f"页面 {self.name} 无有效规则")
            return False
        if tools.android is None:
            #测试客户端，不执行动作，只打印。
            # log.i(f"检查页面规则：{self.rules}")
            return True
        try:
            # 刷新屏幕信息
            tools.refreshScreenInfos()        
            # 检查所有规则
            all_passed = True
            for rule in self.rules:
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
                            log.e(f"文本规则不匹配: {rule}")
                            all_passed = False
                            break
                    if not ret:
                        log.e(f"代码规则不匹配: {rule}")
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
    
    def doAction(self, targetPage):
        """执行到目标页面的动作"""
        g = _G._G_
        log = g.Log()
        tools = g.CTools()
        
        # 获取动作信息
        action_str = self.transitions.get(targetPage.name)
        if tools.android is None:
            #测试客户端，不执行动作，只打印。
            # log.i(f"执行动作：{action_str}")
            return True
        # 判断动作类型
        if action_str is None or action_str.strip() == '':
            # 默认点击操作
            log.i(f"点击: {targetPage.name}")
            result = tools.click(targetPage.name)
            log.i(f"点击结果: {result}")
            return result
        
        # 解析动作字符串
        if '-' in action_str:
            action_type_key, target = action_str.split('-', 1)
            # 获取动作类型枚举
            actionType = next((at for at in ActionType if at.value == action_type_key), 
                             ActionType.CODE)
            
            # 根据动作类型执行相应操作
            if actionType == ActionType.CLICK:
                log.i(f"点击: {target}")
                result = tools.click(target)
                log.i(f"点击结果: {result}")
                return result
            
            elif actionType == ActionType.OPENAPP:
                # 打开应用
                is_home = tools.isHome()
                if not is_home:
                    log.e("不在主屏幕，无法打开应用")
                    return False
                
                result = tools.click(target)
                if result:
                    log.i("等待应用启动...")
                    time.sleep(2)
                return result
            
            elif actionType == ActionType.SWIPE:
                log.i(f"滑动屏幕: {target}")
                result = tools.swipe(target)
                return result
            
            elif actionType == ActionType.BACK:
                log.i("执行返回操作")
                result = tools.goBack()
                return result
        else:
            # 执行代码
            log.i(f"执行代码: {action_str}")
            try:
                result = g.Tools().eval(action_str)
                log.i(f"代码执行结果: {result}")
                return bool(result)
            except Exception as e:
                log.ex(e, f"执行代码失败: {action_str}")
                return False        
        return False
    
    def go(self, targetPage, checkWaitTime=None) -> Optional["CPage_"]:
        """跳转到目标页面并验证结果"""
        try:
            g = _G._G_
            log = g.Log()
            log.i(f'->{targetPage.name}')
            # 使用指定的等待时间或默认值
            wait_time = checkWaitTime if checkWaitTime is not None else self.checkWaitTime
            # 执行动作
            # log.i(f"从 {self.name} 跳转到 {targetPage.name}")
            success = self.doAction(targetPage)
            if not success:
                log.e(f"执行动作失败: {self.name} → {targetPage.name}")
                return None
            # 等待指定时间
            if wait_time > 0:
                # log.i(f"... {wait_time} 秒后检查页面")
                time.sleep(wait_time)
            
            # 验证目标页面
            if targetPage.checkRules():
                # log.i(f"成功跳转到 {targetPage.name}")
                # 更新当前页面
                CPage_.setCurrent(targetPage)
                return targetPage
            else:
                log.e(f"跳转失败: 未能验证目标页面 {targetPage.name}")
                return None
        except Exception as e:
            log.ex(e, f"跳转失败: {self.name} → {targetPage.name}")
            return None
    
    
    @classmethod
    def toPath(cls, pages) -> str:
        """将页面列表转换为路径字符串"""
        return ' → '.join(page.name for page in pages)
  