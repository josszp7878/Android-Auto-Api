from collections import deque
import CTools
from server.scripts import _Log
import CPage
import _CmdMgr

class CPageMgr:
    # 类成员
    pages = {}
    currentPage = None
    pathCache = {}
    
    @classmethod
    def loadConfig(cls, configPath):
        """加载JSON配置文件"""
        import json
        with open(configPath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            for p in data['pages']:
                cls.addPage(p['name'], p['rules'], p['transitions'])

    @classmethod
    def addPage(cls, name, rules, transitions):
        # 处理带变量的规则
        processed_rules = [cls._replaceVars(r) for r in rules]
        
        page = CPage.CPage(name, processed_rules)
        
        # 处理带变量的跳转动作
        for t in transitions:
            action = cls._replaceVars(t['action'])
            page.transitions[t['target']] = action
        
        cls.pages[name] = page

    @classmethod
    def findCurrentPageName(cls):
        """检测当前页面（带区域匹配）"""
        CTools.CTools_.refreshScreenInfos()
        findPage = None
        for page in cls.pages.values():
            for rule in page.rules:
                if cls.evalStr(rule):
                    findPage = page.name
                    break
                else:
                    match, _ = CTools.CTools_.matchScreenText(rule)
                    if match:
                        findPage = page.name
                        break
        return findPage
    
    @classmethod
    def _eval(cls, s):
        """执行代码"""
        _Log.Log_.info(f"执行代码：{s}")
        return eval(s, {'__builtins__': None}, {
            'CTools': CTools.CTools_,
            'DoCmd': _CmdMgr._CmdMgr.do,
            'ToPage': cls.toPage
        })
    
    @classmethod
    def _evalStr(cls, s):
        """执行规则（内部方法）"""
        import re
        if re.match(r'^\s*\{.*\}\s*$', s):
            code = re.search(r'\{(.*)\}', s).group(1)
            try:
                return cls._eval(code)
            except Exception as e:
                _Log.Log_.ex(e, f"执行代码失败: {s}")
                return False
        return 'PASS'

    toPage:str = None
    @classmethod
    def go(cls, target):
        """执行跳转"""
        #缓存目标页面，以备配置字符串里调用
        cls.toPage = target
        path = cls.findPath(target)
        if not path: 
            raise Exception(f"无路径：{cls.currentPage}->{target}")
        
        for pageName in path[1:]:
            action = cls.pages[cls.currentPage].transitions[pageName]
            cls.executeAction(action)
            if cls.findCurrentPageName() != pageName:
                raise Exception(f"跳转失败：{cls.currentPage}->{pageName}")
            cls.currentPage = pageName

    @classmethod
    def _executeAction(cls, action):
        """执行动作（内部方法）"""
        if cls._evalStr(action) == 'PASS':
            CTools.CTools_.clickText(action)

    @classmethod
    def _findPath(cls, target):
        """BFS查找路径（内部方法）"""
        start = cls.currentPage
        if (start, target) in cls.pathCache:
            return cls.pathCache[(start, target)]
        
        visited = set()
        queue = deque([[start]])
        while queue:
            path = queue.popleft()
            current = path[-1]
            if current == target: 
                cls.pathCache[(start, target)] = path
                return path
            for neighbor in cls.pages[current].transitions:
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(path + [neighbor])
        return None 

    @classmethod
    def _replaceVars(cls, s: str) -> str:
        """替换字符串中的$变量"""
        import re
        def replacer(match):
            code = match.group(1)
            try:
                return str(cls._eval(code))
            except Exception as e:
                _Log.Log_.ex(e, f"执行变量代码失败: {code}")
                return match.group(0)
        
        return re.sub(r'\$\s*([\w\(\)]+)', replacer, s)
