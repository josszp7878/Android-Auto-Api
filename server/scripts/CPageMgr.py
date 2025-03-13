from collections import deque
import time
import _G
import CTools
import CPage
import _CmdMgr
import re
import json

class CPageMgr_:
    # 类成员
    pages = {}
    currentPage = None
    pathCache = {}
    topology = {}  # {pageName: {'in': set(), 'out': set()}}
    # 新增返回跳转记录
    backTransitions = {}  # {pageName: {'fromPage': str, 'action': str}}
    ROOT_PAGE = "Top"
    
    # 动作类型枚举
    from enum import Enum
    class ActionType(Enum):
        CLICK = 'C'
        OPENAPP = 'O'
        SWIPE = 'S'
        BACK = 'B'
        CODE = ''

    # @classmethod
    # def Clone(cls, oldCls):
    #     """克隆当前实例"""

    @classmethod
    def init(cls):
        g = _G._G_
        log = g.Log()
        try:
            configDir = g.configDir()
            log.i('初始化页面管理器', f"配置目录: {configDir}")
            cls._loadConfig(f"{configDir}/pages.json")
            cls.currentPage = cls.ROOT_PAGE
            log.i(f"页面管理器初始化完成，当前页设为: {cls.ROOT_PAGE}")
        except Exception as e:
            log.ex(e, f"初始化失败")
      
    @classmethod
    def _addTransition(cls, parent, child, inAction=None):
        """添加页面跳转关系（修复拓扑关系建立）"""
        # 确保父节点存在拓扑结构
        if parent not in cls.topology:
            cls.topology[parent] = {'in': set(), 'out': set()}
        if child not in cls.topology:
            cls.topology[child] = {'in': set(), 'out': set()}
        
        # 正向跳转（父->子）
        cls.topology[parent]['out'].add(child)
        # 逆向跳转（子->父）
        cls.topology[child]['in'].add(parent)
        cls.pages[parent].transitions[child] = inAction
        
    @classmethod
    def _loadConfig(cls, configPath):
        """支持自动推断与显式配置的混合模式"""
        g = _G._G_
        log = g.Log()
        try:
            with open(configPath, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
        except Exception as e:
            log.ex(e, f"加载配置文件失败: {configPath}")
            return
        
        def process_node(node_config, context_parent=None):
            for page_name, page_config in node_config.items():
                # 初始化拓扑结构时使用page_name
                cls.topology.setdefault(page_name, {'in': set(), 'out': set()})
                
                # 优先使用显式配置的parent，否则使用上下文父节点
                explicit_parent = page_config.get('parent')
                effective_parent = explicit_parent if explicit_parent is not None else context_parent
                
                # 根节点特殊处理
                if page_name == cls.ROOT_PAGE:
                    effective_parent = None
                    
                # 创建页面对象时直接使用page_name
                cls.pages[page_name] = CPage.CPage_(
                    name=page_name,  # 使用当前page_name
                    rules=page_config.get('check', []),
                    parent=effective_parent  # 最终确定的父节点
                )
                
                # 再处理父节点关系
                if effective_parent:
                    cls._addTransition(effective_parent, page_name)
                
                # 处理规则类型检查
                rules = page_config.get('check', [])  # 获取当前页面的规则
                for idx, rule in enumerate(rules):
                    if not isinstance(rule, str):
                        log.e(f"页面 [{page_name}] 的规则 #{idx+1} 类型错误: {type(rule)}")
                        rules[idx] = str(rule)
                        log.w(f"已自动转换为字符串: {rules[idx]}")
                
                # 递归处理子节点
                if 'children' in page_config:
                    process_node(page_config['children'], page_name)

        # 初始化根节点日志
        process_node(config_data)
        # log.i(f"拓扑关系: {cls.topology.get(cls.ROOT_PAGE, {})}")



    @classmethod
    def _eval(cls, s):
        """执行代码（安全增强版）"""
        log = _G._G_.Log()
        try:
            if not s:
                log.w("执行空规则")
                return False
            
            # 添加安全环境
            safe_env = {
                'CTools': CTools.CTools_,
                'DoCmd': _CmdMgr._CmdMgr_.do,
                'ToPage': cls.toPage
            }
            
            log.i(f"执行代码：{s}")
            return eval(s, {'__builtins__': None}, safe_env)
        except Exception as e:
            log.ex(e, f"执行规则失败: {s}")
            return False

    @classmethod
    def _safeDoCmd(cls, cmd):
        """安全执行命令的包装方法"""
        log = _G._G_.Log()
        try:
            result = _G._G_.getClass('_CmdMgr').do(cmd)
            # 确保返回可迭代对象
            return result if isinstance(result, (dict, list)) else {}
        except Exception as e:
            log.ex(e, f"执行命令失败: {cmd}")
            return {}
    
    @classmethod
    def _evalStr(cls, s):
        """执行规则（内部方法）"""
        log = _G._G_.Log()
        s = cls._replaceVars(s)
        if re.match(r'^\s*\{.*\}\s*$', s):
            code = re.search(r'\{(.*)\}', s).group(1)
            try:
                return cls._eval(code)
            except Exception as e:
                log.ex(e, f"执行代码失败: {s}")
                return False
        return 'PASS'
    
    @classmethod
    def findCurPage(cls):
        """检测当前页面（安全增强版）"""
        log = _G._G_.Log()
        try:
            CTools.CTools_.refreshScreenInfos()
            for page in cls.pages.values():
                if not page.rules:
                    log.w(f"页面 {page.name} 无有效规则")
                    continue
                # 所有规则必须全部满足
                all_passed = True
                for rule in page.rules:
                    try:
                        ret = cls._evalStr(rule)
                        if ret == 'PASS':
                            # 处理普通文本规则
                            match, _ = CTools.CTools_.matchScreenText(rule)
                            if not match:
                                all_passed = False
                                break
                        else:
                            if not ret:
                                all_passed = False
                                break
                    except Exception as e:
                        log.ex(e, f"规则处理失败: {rule}")
                        all_passed = False
                        break
                if all_passed:
                    return page.name
        except Exception as e:
            log.ex(e, "检测当前页面时发生严重错误")
        return None

    @classmethod
    def _goPage(cls, action, dir, page):
        """执行跳转动作（增强版）"""
        log = _G._G_.Log()
        try:
            if page is None:
                return False
            log.i(f"执行动作 [方向:{dir} 目标:{page}]")
            tools = CTools.CTools_
            ok = True
            # 处理默认动作
            if action is None or action.strip() == '':
                if dir == 'in':
                    # 默认当成屏幕应用来点击
                    ok = tools.click(page, 'LR')
                else:
                    log.i("执行默认返回动作")
                    ok = tools.goBack()                    
            else:
                cls._evalStr(action)
            if ok:
                # 检查是否已到达目标页面
                time.sleep(1)
                curPage = cls.findCurPage()
                if curPage == page:
                    log.i(f"已成功到达目标页面: {page}")
                    cls.currentPage = page
                    return True
            log.w(f"跳转失败")
        except Exception as e:
            log.ex(e, f"执行动作异常")
        return False

    @classmethod
    def findPath(cls, fromPage, toPage):
        """支持多向搜索的BFS（安全增强版）"""
        log = _G._G_.Log()
        if fromPage is None:
            fromPage = cls.ROOT_PAGE
        # 参数校验
        if fromPage not in cls.pages:
            log.e(f"起始页面不存在: {fromPage}")
            return None
        if toPage not in cls.pages:
            log.e(f"目标页面不存在: {toPage}")
            return None
        
        startTime = time.time()
        log.i(f"▄▄▄▄▄ 开始路径查找 {fromPage} → {toPage} ▄▄▄▄▄")
        
        visited = set()
        queue = deque([(fromPage, [fromPage])])
        
        # 调整搜索优先级：子节点 > 父节点 > 兄弟节点 > 旁支
        directions = [
            lambda p: cls.topology[p]['out'],  # 优先子节点
            lambda p: [n for n in cls.topology if p in cls.topology[n]['in']],  # 兄弟节点
            lambda p: cls.topology[p]['in'],   # 最后父节点
        ]
        
        while queue:
            current, path = queue.popleft()
            if current not in cls.topology:  # 新增检查
                log.e(f"发现无效节点: {current}")
                continue
            if current == toPage:
                return path
            if current in visited:
                continue
            visited.add(current)
            
            for getNeighbors in directions:
                for neighbor in getNeighbors(current):
                    queue.append((neighbor, path + [neighbor]))
        
        # cost = (time.time() - startTime) * 1000
        # log.i(f"查找完成，耗时 {cost:.2f}ms")
        return path

    @classmethod
    def _replaceVars(cls, s: str) -> str:
        """替换字符串中的$变量（安全增强版）"""
        # 添加空值防御
        if s is None:
            return s
        log = _G._G_.Log()
        # 正则处理 
        def replacer(match):
            code = match.group(1)
            try:
                val = cls._eval(code)
                return str(val)
            except Exception as e:
                log.ex(e, f"执行变量代码失败: {code}")
                return match.group(0)        
        return re.sub(r'\$\s*([\w\.\(\)]+)', replacer, s)

    toPage:str = None
    @classmethod
    def go(cls, target):
        """跳转到指定页面
        
        Args:
            target: 目标页面名称
            
        Returns:
            bool: 是否跳转成功
        """
        g = _G._G_
        log = g.Log()
        log.i(f"开始跳转到 [{target}]")
        
        # 获取当前页面
        current = cls.currentPage
        log.i(f"当前页面: {current}")
        
        # 如果已经在目标页面，直接返回成功
        if current == target:
            log.i(f"已经在目标页面 [{target}]，无需跳转")
            return True
        
        # 查找从当前页面到目标页面的路径
        log.i(f"开始路径查找 {current} → {target}")
        path = cls.findPath(current, target)
        if not path:
            log.e(f"找不到从 [{current}] 到 [{target}] 的路径")
            return False
        
        # 打印完整路径
        path_str = " → ".join(path)
        log.i(f"导航路径: {path_str}")
        
        # 逐步执行路径
        for i in range(len(path) - 1):
            from_page = path[i]
            to_page = path[i + 1]
            log.i(f"步骤{i+1}: {from_page} → {to_page}")
            
            # 获取从当前页面到下一个页面的动作
            action = cls.getAction(from_page, to_page)
            if not action:
                log.e(f"找不到从 [{from_page}] 到 [{to_page}] 的动作")
                log.i(f"跳转失败于步骤 {i+1}")
                return False
            
            log.i(f"执行动作 [类型:{action.get('type')} 目标:{action.get('target')}]")
            
            # 执行动作
            success = cls.doAction(action)
            
            # 添加详细的动作执行结果日志
            if not success:
                log.e(f"执行动作失败: {action}")
                log.i(f"跳转失败于步骤 {i+1}")
                return False
            
            # 验证是否到达了预期页面
            new_page = cls.currentPage
            log.i(f"执行动作后当前页面: {new_page}")
            
            if new_page != to_page:
                log.e(f"页面跳转失败: 期望 [{to_page}]，实际 [{new_page}]")
                log.i(f"跳转失败于步骤 {i+1}")
                return False
            
            log.i(f"成功到达 [{to_page}] 页面")
        
        log.i(f"成功跳转到 [{target}]")
        return True

    @classmethod
    def doAction(cls, action):
        """执行动作
        
        Args:
            action: 动作配置
            
        Returns:
            bool: 是否执行成功
        """
        g = _G._G_
        tools = CTools.CTools_
        log = g.Log()
        
        action_type = action.get('type')
        target = action.get('target')
        code = action.get('code')
        
        try:
            
            # 根据动作类型执行相应操作
            if action_type == cls.ActionType.CLICK:
                # 点击操作
                log.i(f"点击: {target}")
                result = tools.click(target)
                log.i(f"点击结果: {result}")
                return result
            
            elif action_type == cls.ActionType.OPENAPP:
                # 打开应用
                # 检查是否在主屏幕
                is_home = tools.isHome()
                log.i(f"是否在主屏幕: {is_home}")
                
                if not is_home:
                    log.e("不在主屏幕，无法打开应用")
                    return False
                
                # 尝试点击应用图标
                result = tools.click(target)
                log.i(f"打开应用结果: {result}")
                return result
            
            elif action_type == cls.ActionType.SWIPE:
                # 滑动屏幕
                log.i(f"滑动屏幕: {target}")
                result = tools.swipe(target)
                log.i(f"滑动结果: {result}")
                return result
            
            elif action_type == cls.ActionType.BACK:
                # 返回操作
                log.i("执行返回操作")
                result = tools.goBack()
                log.i(f"返回结果: {result}")
                return result
            
            elif code:
                # 直接执行代码
                log.i(f"执行代码：{code}")
                result = cls._eval(code)
                log.i(f"代码执行结果: {result}")
                return bool(result)
            else:
                log.e(f"未知的动作类型: {action_type}")
                return False
            
        except Exception as e:
            log.ex(e, f"执行动作异常: {action}")
            return False

    @classmethod
    def printTopology(cls):
        """打印完整拓扑结构"""
        log = _G._G_.Log()
        log.d("当前拓扑结构:")
        for page, links in cls.topology.items():
            log.d(f"{page}:")
            log.d(f"  in: {links['in']}")
            log.d(f"  out: {links['out']}")

    @classmethod
    def getAction(cls, fromPage, toPage):
        """获取从一个页面到另一个页面的动作
        
        Args:
            fromPage: 起始页面
            toPage: 目标页面
            
        Returns:
            dict: 包含动作信息的字典，如果没有找到动作则返回None
        """
        try:
            log = _G._G_.Log()
            
            # 检查页面是否存在
            if fromPage not in cls.pages or toPage not in cls.pages:
                log.e(f"页面不存在: {fromPage} 或 {toPage}")
                return None
            
            # 先检查是否有直接跳转关系
            forward = toPage in cls.pages[fromPage].transitions
            backward = cls.pages[toPage].name == cls.pages[fromPage].parent

            if not forward and not backward:
                log.e(f"页面 {fromPage} 和 {toPage} 之间没有直接跳转关系")
                return None

            # 获取动作字符串
            action_str = cls.pages[fromPage].transitions.get(toPage) if forward else None
            emptyAction = action_str is None or (isinstance(action_str, str) and action_str.strip() == '')

            if emptyAction:
                action = {"type": cls.ActionType.CLICK, "target": toPage} if forward else {"type": cls.ActionType.BACK, "target": toPage}
            else:
                # 解析动作字符串
                # 如果是字符串，解析动, 检查是否是简写指令
                if '-' in action_str:
                    action_type_key, target = action_str.split('-', 1)
                    actionType = next((at for at in cls.ActionType if at.value == action_type_key), cls.ActionType.CODE)
                    action = {"type": actionType, "target": target}
                else:
                    # 当作普通代码执行
                    action = {"type": cls.ActionType.CODE, "code": action_str, "target": toPage}
            return action
        except Exception as e:
            log.ex(e, f"获取动作失败: {fromPage} → {toPage}")
            return None

CPageMgr_.init()
