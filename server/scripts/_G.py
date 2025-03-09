"""
全局状态管理模块 (兼容服务端和客户端)
"""
import threading

class G:
    # 使用线程安全的存储
    _store = {}
    _lock = threading.Lock()

    @classmethod
    def save(cls, key, value):
        """保存状态"""
        with cls._lock:
            cls._store[key] = value

    @classmethod
    def restore(cls, key, default=None):
        """恢复并删除状态"""
        with cls._lock:
            return cls._store.pop(key, default)
        
    @classmethod
    def get(cls, key, default=None):
        """获取状态"""
        return cls._store.get(key, default)
    
    @classmethod
    def clear(cls):
        """清空状态"""
        with cls._lock:
            cls._store.clear()

    @classmethod
    def Log(cls):
        """获取 Log 实例"""
        if 'Log' not in cls._store:
            import _Log
            v = _Log.Log_
            cls._store['Log'] = v
        return cls._store['Log']
    
    @classmethod
    def Tools(cls, key):
        """获取状态"""
        if key not in cls._store:
            import _Tools
            v = _Tools._Tools
            cls._store['Tools'] = v
        return cls._store['Tools']
    
    @classmethod
    def CTools(cls):
        """获取状态"""
        if 'CTools' not in cls._store:
            import CTools
            v = CTools.CTools_
            cls._store['CTools'] = v
        return cls._store['CTools']
    
    @classmethod
    def PageMgr(cls):
        """获取 PageMgr 实例"""
        if 'PageMgr' not in cls._store:
            import CPageMgr
            v = CPageMgr.CPageMgr_
            cls._store['PageMgr'] = v
        return cls._store['PageMgr']
    
    @classmethod
    def logPerf(cls, key, timeCost):
        """记录性能数据"""
        if not hasattr(cls, '_perfData'):
            cls._perfData = {}
        cls._perfData.setdefault(key, []).append(timeCost)
        
    @classmethod
    def getPerfStats(cls, key):
        """获取性能统计"""
        data = cls._perfData.get(key, [])
        if not data:
            return "无数据"
        avg = sum(data)/len(data)
        return f"平均: {avg:.2f}ms 最大: {max(data):.2f}ms 最小: {min(data):.2f}ms"
    
