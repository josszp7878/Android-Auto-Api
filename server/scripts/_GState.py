"""
全局状态管理模块 (兼容服务端和客户端)
"""
import threading

class GState:
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
# 创建模块级实例方便使用
gState = GState() 