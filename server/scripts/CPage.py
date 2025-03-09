class CPage:
    def __init__(self, name, rules, parent=None):
        self.name = name
        # 直接存储原始规则字符串
        self.rules = rules  
        self.parent = parent  # 父节点
        self.transitions = {} # 子节点:inAction
        self.backAction = ""  # 返回父节点的动作

    @property
    def hierarchy(self):
        """生成层级路径（调试用）"""
        path = []
        current = self
        while current:
            path.append(current.name)
            current = current.parent_page  # 需要添加parent_page属性
        return ' → '.join(reversed(path))
