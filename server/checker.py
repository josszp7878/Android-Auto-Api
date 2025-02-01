from typing import Pattern, List, Tuple, Any, Callable
import re
from logger import Log
import time
from tools import Tools, tools

# 定义固定的region
UP_REGION = [-1, 0, -1, 0.2]
MID_REGION = [-1, 0.4, -1, 0.6]
DOWN_REGION = [-1, 0.8, -1, 1]
LEFT_REGION = [0, -1, 0.2, -1]
RIGHT_REGION = [0.8, -1, 1, -1]
CENTER_REGION = [0.4, 0.4, 0.6, 0.6]

def GetMatchVal(param: List[Tuple[re.Match, dict]], key: str = None, index: int = 0) -> str:
    m = GetMatch(param, index)
    if m is None:
        return None
    if key is None:
        return m.group()
    else:
        return m.group(key)

def GetMatch(param: List[Tuple[re.Match, dict]], index: int = 0) -> re.Match:
    if index < 0 or index >= len(param):
        return None
    return param[index][0]
          
def GetItem(param: List[Tuple[re.Match, dict]], index: int = 0) -> dict:
    if index < 0 or index >= len(param):
        return None
    return param[index][1]

def GetPos(param: List[Tuple[re.Match, dict]], index: int = 0) -> Tuple[float, float]:
    if index < 0 or index >= len(param):
        return None
    return tools.toPos(param[index][1])

def _doCheck(patterns: List[Pattern], region: List[float] = None) -> List[Tuple[re.Match, dict]]:
    try:
        matched = []
        for pattern in patterns:
            match, item = tools.matchScreenText(pattern, region)
            if match is not None:
                matched.append((match, item))
            else:
                return None
        return matched
    except Exception as e:
        Log.ex(e, "Checker执行异常")
        return None

def check(patterns: List[str], region: List[float] = None,
           callback: Callable[[Any], None] = None, timeout: int = 10, interval: int = 1) -> bool:
    try:
        patterns = [re.compile(p) for p in patterns]
        start_time = time.time()
        while True:
            time.sleep(interval)
            matched = _doCheck(patterns, region)
            if matched is not None:
                callback(matched)
                return True
            if time.time() - start_time > timeout:
                return False
    except Exception as e:
        Log.ex(e, "Checker执行异常")
        return False
