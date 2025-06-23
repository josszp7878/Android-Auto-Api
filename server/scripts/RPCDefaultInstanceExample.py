# """
# RPC默认实例获取器使用示例

# 展示如何使用默认的instanceGetter机制，支持App、Device、Task类的动态实例获取
# """

# import _G
# from RPC import RPC
# from datetime import datetime

# def testDefaultInstanceGetters():
#     """测试默认实例获取器"""
#     g = _G._G_
#     log = g.Log()
    
#     log.i("=== 测试默认实例获取器 ===")
    
#     # 1. 测试App类的默认实例获取
#     log.i("1. 测试App类RPC调用")
    
#     if g.isServer():
#         # 服务端本地调用App方法
#         result = g.RPC(None, '_App_', 'getCurrentPageInfo')
#         log.i(f"App默认实例调用: {result}")
        
#         # 服务端调用指定App实例（通过app名称）
#         result = g.RPC(None, '_App_', 'getCurrentPageInfo', instance_id='微信')
#         log.i(f"App指定实例调用: {result}")
        
#     else:
#         # 客户端本地调用App方法
#         result = g.RPC('local', '_App_', 'getCurrentPageInfo')
#         log.i(f"客户端App默认实例调用: {result}")

# def testDeviceInstanceGetters():
#     """测试Device实例获取器"""
#     g = _G._G_
#     log = g.Log()
    
#     log.i("2. 测试Device类RPC调用")
    
#     if g.isServer():
#         # 服务端获取设备信息
#         result = g.RPC(None, 'CDevice_', 'getDeviceInfo')
#         log.i(f"Device默认实例调用: {result}")
        
#         # 服务端获取指定设备信息
#         result = g.RPC(None, 'CDevice_', 'getDeviceInfo', instance_id='device123')
#         log.i(f"Device指定实例调用: {result}")
        
#     else:
#         # 客户端获取设备信息
#         result = g.RPC('local', 'CDevice_', 'getDeviceInfo')
#         log.i(f"客户端Device实例调用: {result}")

# def testTaskInstanceGetters():
#     """测试Task实例获取器"""
#     g = _G._G_
#     log = g.Log()
    
#     log.i("3. 测试Task类RPC调用")
    
#     if g.isServer():
#         # 服务端任务操作
#         result = g.RPC(None, 'CTask_', 'getTaskStatus')
#         log.i(f"Task默认实例调用: {result}")
        
#         # 服务端指定任务操作
#         result = g.RPC(None, 'CTask_', 'getTaskStatus', instance_id='task456')
#         log.i(f"Task指定实例调用: {result}")
        
#     else:
#         # 客户端任务操作
#         result = g.RPC('local', 'CTask_', 'getTaskStatus')
#         log.i(f"客户端Task实例调用: {result}")

# # 创建示例Device类用于测试
# class CDevice_:
#     """示例Device类"""
    
#     def __init__(self, device_id="default"):
#         self.device_id = device_id
#         self.name = f"设备{device_id}"
        
#     @RPC()
#     def getDeviceInfo(self) -> dict:
#         """获取设备信息"""
#         return {
#             'success': True,
#             'deviceId': self.device_id,
#             'deviceName': self.name,
#             'platform': 'Android',
#             'timestamp': datetime.now().isoformat()
#         }
    
#     @RPC()
#     def setDeviceName(self, name: str) -> dict:
#         """设置设备名称"""
#         old_name = self.name
#         self.name = name
#         return {
#             'success': True,
#             'oldName': old_name,
#             'newName': name,
#             'deviceId': self.device_id
#         }

# # 创建示例Task类用于测试
# class CTask_:
#     """示例Task类"""
    
#     def __init__(self, task_id="default_task"):
#         self.task_id = task_id
#         self.status = 'running'
#         self.progress = 0
        
#     @RPC()
#     def getTaskStatus(self) -> dict:
#         """获取任务状态"""
#         return {
#             'success': True,
#             'taskId': self.task_id,
#             'status': self.status,
#             'progress': self.progress,
#             'timestamp': datetime.now().isoformat()
#         }
    
#     @RPC()
#     def updateProgress(self, progress: int) -> dict:
#         """更新任务进度"""
#         old_progress = self.progress
#         self.progress = min(100, max(0, progress))
#         if self.progress >= 100:
#             self.status = 'completed'
#         return {
#             'success': True,
#             'taskId': self.task_id,
#             'oldProgress': old_progress,
#             'newProgress': self.progress,
#             'status': self.status
#         }

# def setupExampleClasses():
#     """设置示例类并注册RPC"""
#     g = _G._G_
    
#     # 注册Device类（使用默认instanceGetter）
#     g.registerRPC(CDevice_)
    
#     # 注册Task类（使用默认instanceGetter）
#     g.registerRPC(CTask_)
    
#     print("示例类已注册到RPC系统")

# def demonstrateUsage():
#     """演示新的RPC使用方式"""
#     g = _G._G_
#     log = g.Log()
    
#     log.i("=== RPC默认实例获取器演示 ===")
    
#     # 设置示例类
#     setupExampleClasses()
    
#     # 演示不同的调用方式
#     log.i("\n1. 使用默认实例调用:")
#     result = g.RPC(None, '_App_', 'getAppList')
#     log.i(f"获取应用列表: {result}")
    
#     log.i("\n2. 使用指定实例ID调用:")
#     result = g.RPC(None, '_App_', 'getCurrentPageInfo', instance_id='微信')
#     log.i(f"获取微信页面信息: {result}")
    
#     log.i("\n3. 设备相关调用:")
#     result = g.RPC(None, 'CDevice_', 'getDeviceInfo')
#     log.i(f"获取默认设备信息: {result}")
    
#     result = g.RPC(None, 'CDevice_', 'getDeviceInfo', instance_id='device123')
#     log.i(f"获取指定设备信息: {result}")
    
#     log.i("\n4. 任务相关调用:")
#     result = g.RPC(None, 'CTask_', 'getTaskStatus')
#     log.i(f"获取默认任务状态: {result}")
    
#     result = g.RPC(None, 'CTask_', 'getTaskStatus', instance_id='task456')
#     log.i(f"获取指定任务状态: {result}")

# if __name__ == "__main__":
#     demonstrateUsage() 