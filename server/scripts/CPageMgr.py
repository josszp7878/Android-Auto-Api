import time
import _G
import CPage
import json

class CPageMgr_:
    
    @classmethod
    def init(cls):
        """初始化页面管理器"""
        g = _G._G_
        log = g.Log()
        try:
            configDir = g.configDir()
            log.i(f"加载页面配置: {configDir}/pages.json")
            cls._loadConfig(f"{configDir}/pages.json")
        except Exception as e:
            log.ex(e, f"初始化失败")
    
    @classmethod
    def _loadConfig(cls, configPath):
        """加载页面配置并构建页面树"""
        g = _G._G_
        log = g.Log()
        try:
            with open(configPath, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
        except Exception as e:
            log.ex(e, f"加载配置文件失败: {configPath}")
            return
        
        # 创建根页面
        root = CPage.CPage_(
            name=_G.TOP,
            rules=[],
            parent=None,
        )
        CPage.CPage_.setRoot(root)
        CPage.CPage_.UNKNOWN_PAGE = _G.UNKNOWN
        import CApp
        CApp.CApp_.registerApp(_G.TOP, root)
        
        appList = []
        
        # 处理配置
        def process_node(node, parent=None):
            """处理配置节点，创建页面对象并建立关系
            
            Args:
                node: 节点配置
                parent: 父页面对象
            """
            # 根节点处理
            if parent is None:
                page_name = list(node.keys())[0]  # 应该直接是 "Top"
                page_config = node[page_name]
                current_page = root
                
                # 处理子节点时应该直接处理 "快手极速版"
                children = page_config.get("children", {})
                for child_name, child_config in children.items():
                    # 这里应该创建 "快手极速版" 作为 root 的直接子节点
                    process_node({child_name: child_config}, current_page)
                    
                return current_page
            
            # 正常节点处理
            page_name = list(node.keys())[0]
            page_config = node[page_name]
            
            # 创建新页面
            rules = page_config.get("check", [])
            timeout = page_config.get("timeout", 1.0)
            
            # 创建页面对象
            current_page = CPage.CPage_(
                name=page_name,
                rules=rules,
                parent=parent
            )
            current_page.checkWaitTime = timeout
            
            # 处理页面转换动作
            for action_key, action_value in page_config.items():
                if action_key == "in" and isinstance(action_value, str):
                    # 处理进入该页面的动作
                    if parent:
                        parent.transitions[page_name] = action_value
            
            # 如果是应用根页面，添加到应用列表
            if parent == root and page_name not in appList:
                appList.append(page_name)
                import CApp
                CApp.CApp_.registerApp(page_name, current_page)
            
            # 处理子节点
            children = page_config.get("children", {})
            if children:
                for child_name, child_config in children.items():
                    process_node({child_name: child_config}, current_page)
            
            return current_page
        
        # 开始处理配置
        process_node(config_data, None)
        log.i(f"页面配置加载完成，加载应用：{appList}")

        # 在 _loadConfig 最后调用
        cls.printTopology()
    
    
    @classmethod
    def printTopology(cls):
        """打印页面树结构"""
        log = _G._G_.Log()
        root = CPage.CPage_.getRoot()
        if not root:
            log.e("页面树未初始化")
            return
        
        log.d("页面树结构:")
        cls._printTree(root)
    
    @classmethod
    def _printTree(cls, page, level=0):
        """递归打印页面树"""
        log = _G._G_.Log()
        indent = "  " * level
        log.d(f"{indent}└─ {page.name}")
        for child in page.getAllChildren():
            cls._printTree(child, level + 1)


CPageMgr_.init()
