import _Log
from checker import check, GetMatchVal, GetPos
from CTask import CTask
from CTools import CTools_

# ["观看广告", "广告剩余(?P<seconds>\d+)秒"]
class Check:    
    @staticmethod
    def Ad_Start(task: CTask, params: dict) -> bool:
        strs = params['startMatch']
        region = params['startRegion']
        minScore = params['minScore']
        if strs is None:
            strs = ["看视频.*领\D*(?P<count>\d+)金币"]
        if minScore < 0:
            minScore = 0

        def check_function(ms):
            count = GetMatchVal(ms, 'count')
            count = int(count)            
            _Log.Log_.i(f"{strs[0]}:score={count} minScore={minScore}")
            if count > minScore:
                return True
            pos = GetPos(ms)
            if pos is None:
                _Log.Log_.e(f"未找到{strs[0]}")
                return False
            _Log.Log_.Do(f"点击{strs[0]}")    
            global android
            return android.click(pos[0], pos[1])


        return check(strs, region, check_function)
    
    @staticmethod
    def Ad_Process(task: CTask, params: dict) -> bool:
        sts = params['doMatch']
        region = params['doRegion']
        if sts is None:
            sts = ["(?P<seconds>\d+)秒"]

        def check_function(ms):
            seconds = GetMatchVal(ms, 'seconds')
            seconds = int(seconds)
            if seconds > 0:
                _Log.Log_.i(f"广告剩余{seconds}秒")
                return False
            _Log.Log_.i("广告结束")
            return True

        return check(sts, region, check_function)

    @staticmethod
    def Ad_End(task: CTask, params: dict) -> bool:
        sts = params['endMatch']
        region = params['endRegion']
        if sts is None:
            sts = ["恭喜你获得\+(?P<count>\d+)金币", "完成"]

        def check_function(c):
            count = GetMatchVal(c, 'count')
            if count is not None:
                count = int(count)
                _Log.Log_.i(f"获得{count}金币")
                task.setScore(count)
                return True
            pos = GetPos(c)
            if pos is None:
                _Log.Log_.e("未找到完成按钮")
                return False
            _Log.Log_.Do("点击完成")
            global android
            return android.click(pos[0], pos[1])

        return check(sts, region, check_function)





