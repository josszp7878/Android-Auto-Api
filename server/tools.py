try:
    from logger import Log, android
except:
    from scripts.logger import Log, android

from typing import Pattern, List

class Tools:
    _instance = None
    TAG = "Tools"
    port = 5000
    
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            _instance = super(Tools, cls).__new__(cls)
            _instance._screenInfoCache = ""
            cls._instance = _instance
        return cls._instance
   

    def printCallStack(self):
        """打印调用栈"""
        import traceback
        print('\n保存日志调用栈:')
        for line in traceback.format_stack()[:-1]:
            print(line.strip())


    @staticmethod
    def toPos(item: dict):
        bounds = [int(x) for x in item['b'].split(',')]
        centerX = (bounds[0] + bounds[2]) // 2
        centerY = (bounds[1] + bounds[3]) // 2
        return (centerX, centerY)
    
    ##############################
    # 屏幕文字相关
    ##############################
    def screenInfos(self):
        return self._screenInfoCache

    def refreshScreenInfos(self) -> list:
        """获取并解析屏幕信息,支持缓存
        Args:
            forceUpdate: 是否强制更新缓存
        Returns:
            list: 屏幕文本信息列表
        """
        try:
            info = android.getScreenInfo()
            size = info.size()
            result = []
            
            for i in range(size):
                item = info.get(i)
                result.append({
                    't': item.get('t'),
                    'b': item.get('b')
                })
                
            # 更新缓存
            self._screenInfoCache = result
            return result
            
        except Exception as e:
            Log.ex(e, "获取屏幕信息失败")
            return []
    
    def matchScreenText(self, regex: Pattern, region: List[int] = None):
        """查找匹配文本的位置
        Args:
            pattern: 匹配模式(正则表达式)
            region: 搜索区域[left, top, right, bottom], None表示全屏搜索
            forceUpdate: 是否强制更新缓存
        Returns:
            tuple: (x, y) 匹配文本的中心坐标,未找到返回None
        """
        try:
            # 使用缓存的屏幕信息
            screenInfo = self.screenInfos()        
            # 遍历屏幕信息，查找匹配的文本
            for item in screenInfo:
                # 解析当前文本的边界
                bounds = [int(x) for x in item['b'].split(',')]
                
                # 如果指定了区域,检查文本是否在区域内
                if region is not None:
                    # 检查是否有重叠
                    if (bounds[2] < region[0] or  # 文本在区域左边
                        bounds[0] > region[2] or  # 文本在区域右边
                        bounds[3] < region[1] or  # 文本在区域上边
                        bounds[1] > region[3]):   # 文本在区域下边
                        continue
                match = regex.search(item['t'])
                if match:
                    return match, item
            return None, None
            
        except Exception as e:
            Log.ex(e, "FindUI 指令执行失败")
            return None, None    
        
tools = Tools()