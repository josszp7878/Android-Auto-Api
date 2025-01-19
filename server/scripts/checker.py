from typing import Pattern, List, Union, Any, Tuple, Callable, Optional
import re
from logger import Log
from Cmds import matchScreenText

class Checker:
    """屏幕文本检查器,用于匹配屏幕文本并执行相应操作"""
    
    def __init__(self, pattern: Union[str, List[str]], region: list[int] = None):
        """初始化检查器
        Args:
            pattern: 匹配模式,可以是单个字符串或字符串列表,多个模式用|分隔
            region: 搜索区域[left, top, right, bottom]
        """
        # 处理pattern参数
        if isinstance(pattern, str):
            patterns = [p.strip() for p in pattern.split('|')]
        else:
            patterns = pattern
            
        # 编译所有正则表达式
        self.patterns: List[Pattern] = [re.compile(p) for p in patterns]
        self.region = region
        self.matched: List[Tuple[Pattern, Any]] = []
        
    @classmethod
    def create(cls, pattern: Union[str, List[str]], region: list[int] = None) -> 'Checker':
        """创建检查器
        Args:
            pattern: 匹配模式,可以是单个字符串或字符串列表,多个模式用|分隔
            region: 搜索区域[left, top, right, bottom]
        """
        return cls(pattern, region)
        
    def check(self, callback: Optional[Callable[['Checker'], bool]] = None) -> bool:
        """检查当前屏幕文本是否匹配所有模式,并执行回调
        Args:
            callback: 匹配成功后执行的回调函数
        Returns:
            bool: 是否匹配成功并执行了回调
        """
        try:
            # 清空上次的匹配结果
            self.matched.clear()
            
            # 尝试所有模式
            for pattern in self.patterns:
                match, item = matchScreenText(pattern, self.region)
                if match:
                    # 保存匹配信息
                    self.matched.append((pattern, item))
                else:
                    # 如果有任何一个模式没匹配到,返回False
                    return False
                    
            # 如果所有模式都匹配成功
            if callback:
                return callback(self)
            return True
            
        except Exception as e:
            Log.ex(e, "Checker执行异常")
            return False 