import time
from typing import Dict, Any
import _G
import _Log

class CChecker_:
    """页面检查器类，用于验证页面状态并执行相应操作"""
    
    def __init__(self, name: str, config: Dict[str, Any], page: "_Page_" = None):
        """初始化检查器
        
        Args:
            name: 检查器名称
            config: 检查器配置字典，包含term和do等键
            page: 所属页面
        """
        self.name = name
        self.page = page
        self.term = config.get('term', 'in')  # 默认为进入页面时执行
        self._action = config.get('do', '')
        self._check = config.get('check', name)
        self.interval = config.get('interval', 0 if self.term == 'in' else 1)
        self.startTime = 0

    @property
    def pastTime(self) -> int:
        return int(time.time() - self.startTime)


    def check(self) -> bool:
        self.startTime = time.time()
        if self.interval > 0:
            while True:
                if self.doCheck():
                    break
                _Log.c.d(f"check: {self.name} time: {self.pastTime}")
                time.sleep(self.interval)
        else:
            _Log.c.d(f"check: {self.name}")
            return self.doCheck()

    def doCheck(self) -> bool:
        """执行检查逻辑
        Returns:
            bool: 检查是否通过
        """
        try:
            if self._check == '': 
                return True
            g = _G._G_
            tools = g.Tools()
            # 当代码执行，返回结果为PASS时，表示执行成功·
            ret = tools.eval(self, self._check)
            if ret != 'PASS':
                return ret
            # 否则检查文本规则
            # log.d(f"执行检查器文本规则: {rule}")
            ret = tools.matchText(self._check)
            if not ret:
                _Log.c.d(f"检查器文本规则不匹配: {self._check}")
                return False
            return True
        except Exception as e:
            _Log.c.ex(e, f"执行检查器失败: {self._check}")
            return False
        
    def do(self):
        return _G._G_.Tools().eval(self, self._action)
    