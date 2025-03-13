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
        
        # 设置进入动作
        if inAction:
            cls.pages[parent].transitions[child] = inAction
        else:
            # 生成默认动作
            default_action = f"click('{child}')" if parent != cls.ROOT_PAGE else f"打开应用('{child}')"
            cls.pages[parent].transitions[child] = default_action

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
        log.i(f"拓扑关系: {cls.topology.get(cls.ROOT_PAGE, {})}")



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
        """优化后的跳转逻辑"""
        log = _G._G_.Log()
        log.i(f"▄▄▄▄▄ 开始跳转到 [{target}] ▄▄▄▄▄")
        log.d(f"当前页面: {cls.currentPage}")

        # 路径查找阶段
        path = cls.findPath(cls.currentPage, target)
        if not path:
            log.e(f"未找到有效路径: {cls.currentPage} -> {target}")
            return False
        log.i(f"导航路径: {' → '.join(path)}")

        # 执行跳转阶段
        for idx, page in enumerate(path):
            if page == cls.currentPage:
                continue
            
            log.i(f"步骤{idx+1}: {cls.currentPage} → {page}")
            # 智能跳转类型判断（简化版）
            if page in cls.topology[cls.currentPage]['out']:  # 正向跳转
                action = cls.pages[cls.currentPage].transitions[page]
                success = cls._goPage(action, 'in', page)
            elif page == cls.pages[cls.currentPage].parent:  # 返回父级
                action = cls.pages[cls.currentPage].backAction
                success = cls._goPage(action, 'out', page)
            else:
                log.e(f"无效跳转: {cls.currentPage}->{page}")
                return False
            if not success:
                log.e(f"跳转失败于步骤 {idx+1}")
                return False
            
        log.i(f"▄▄▄▄▄ 成功到达 [{target}] ▄▄▄▄▄")
        return True

    @classmethod
    def printTopology(cls):
        """打印完整拓扑结构"""
        log = _G._G_.Log()
        log.d("当前拓扑结构:")
        for page, links in cls.topology.items():
            log.d(f"{page}:")
            log.d(f"  in: {links['in']}")
            log.d(f"  out: {links['out']}")


CPageMgr_.init()
