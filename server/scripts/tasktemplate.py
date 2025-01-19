from typing import Dict, Optional, Callable
from dataclasses import dataclass


@dataclass
class TaskTemplate:
    """任务模板类,用于定义任务的基本参数和脚本"""
    
    taskName: str  # 任务名称
    alias: str  # 任务别名
    start: Optional[Callable] = None  # 开始任务的函数
    do: Optional[Callable] = None  # 执行任务的函数
    end: Optional[Callable] = None  # 结束任务的函数
    params: Dict[str, str] = None  # 脚本参数集合
    
    def __post_init__(self):
        """初始化后处理"""
        if self.params is None:
            self.params = {}
            
    def replaceParams(self, script: str) -> str:
        """替换脚本中的参数"""
        if not script:
            return script
        result = script
        for key, value in self.params.items():
            result = result.replace(f"${key}", str(value))
        return result 