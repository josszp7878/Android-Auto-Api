"""
RPC远程过程调用使用指南

本指南详细说明如何使用基于装饰器的RPC机制实现客户端和服务端双向调用
"""

import _G
from RPC import RPC
from datetime import datetime

class RPCUsageGuide:
    """RPC使用指南和示例"""
    
    @staticmethod
    def printUsageGuide():
        """打印RPC使用指南"""
        print("""
=== RPC远程过程调用使用指南 ===

1. 定义RPC方法
   使用@RPC()装饰器标记方法为RPC可调用：
   
   @RPC()
   def myMethod(self, param1, param2=None):
       return {'result': 'success', 'data': param1}

2. 注册RPC类
   使用实例获取函数注册类：
   
   g.registerRPC(MyClass, lambda: MyClass.getInstance())

3. 调用RPC方法
   使用统一的RPC接口调用：
   
   # 服务端调用客户端
   result = g.RPC(device_id, 'ClassName', 'methodName', arg1, arg2)
   
   # 客户端调用服务端  
   result = g.RPC(None, 'ClassName', 'methodName', arg1, arg2)
   
   # 本地调用
   result = g.RPC(None, 'ClassName', 'methodName', arg1, arg2)  # 服务端本地
   result = g.RPC('local', 'ClassName', 'methodName', arg1, arg2)  # 客户端本地

4. 调用规则说明：
   - device_id为None：客户端->服务端 或 服务端本地调用
   - device_id不为None：服务端->客户端 或 客户端本地调用
   - 支持位置参数和关键字参数
   - 支持设置超时时间（默认8秒）
   
5. 返回值格式：
   {
       'success': True/False,
       'result': 实际结果,
       'error': 错误信息（如果失败）,
       'timestamp': 时间戳
   }
        """)

# 示例RPC服务类
class ExampleRPCService:
    """示例RPC服务类"""
    
    def __init__(self, name):
        self.name = name
        self.counter = 0
    
    @RPC()
    def ping(self) -> dict:
        """测试连通性"""
        self.counter += 1
        return {
            'success': True,
            'message': f'{self.name} pong #{self.counter}',
            'timestamp': datetime.now().isoformat()
        }
    
    @RPC()
    def getData(self, key: str, default=None) -> dict:
        """获取数据"""
        # 模拟数据获取
        data = {
            'user': 'admin',
            'config': {'timeout': 30, 'retries': 3},
            'status': 'online'
        }
        
        result = data.get(key, default)
        return {
            'success': True,
            'key': key,
            'value': result,
            'available_keys': list(data.keys())
        }
    
    @RPC()
    def processData(self, data: list, operation: str = 'sum') -> dict:
        """处理数据"""
        try:
            if operation == 'sum':
                result = sum(data)
            elif operation == 'max':
                result = max(data)
            elif operation == 'min':
                result = min(data)
            elif operation == 'avg':
                result = sum(data) / len(data)
            else:
                raise ValueError(f"不支持的操作: {operation}")
            
            return {
                'success': True,
                'operation': operation,
                'input': data,
                'result': result
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'operation': operation,
                'input': data
            }
    
    @RPC()
    @classmethod
    def getSystemInfo(cls) -> dict:
        """获取系统信息（类方法示例）"""
        g = _G._G_
        return {
            'success': True,
            'isServer': g.isServer(),
            'platform': 'server' if g.isServer() else 'client',
            'timestamp': datetime.now().isoformat()
        }

def setupExampleRPCService():
    """设置示例RPC服务"""
    # 创建服务实例
    service = ExampleRPCService("ExampleService")
    
    # 注册RPC服务，使用lambda获取实例
    g = _G._G_
    g.registerRPC(ExampleRPCService, lambda: service)
    
    print("示例RPC服务已注册")
    return service

def testRPCCalls():
    """测试RPC调用"""
    g = _G._G_
    log = g.Log()
    
    # 设置示例服务
    service = setupExampleRPCService()
    
    log.i("=== RPC调用测试 ===")
    
    if g.isServer():
        log.i("服务端RPC调用测试:")
        
        # 服务端本地调用
        result = g.RPC(None, 'ExampleRPCService', 'ping')
        log.i(f"本地调用ping: {result}")
        
        result = g.RPC(None, 'ExampleRPCService', 'getData', 'user')
        log.i(f"本地调用getData: {result}")
        
        result = g.RPC(None, 'ExampleRPCService', 'processData', [1, 2, 3, 4, 5], 'avg')
        log.i(f"本地调用processData: {result}")
        
        # 类方法调用
        result = g.RPC(None, 'ExampleRPCService', 'getSystemInfo')
        log.i(f"类方法调用: {result}")
        
        # 模拟向客户端调用（需要真实设备ID）
        # result = g.RPC('device123', 'ExampleRPCService', 'ping')
        # log.i(f"远程调用客户端: {result}")
        
    else:
        log.i("客户端RPC调用测试:")
        
        # 客户端本地调用
        result = g.RPC('local', 'ExampleRPCService', 'ping')
        log.i(f"本地调用ping: {result}")
        
        # 客户端向服务端调用
        result = g.RPC(None, 'ExampleRPCService', 'getData', 'config')
        log.i(f"远程调用服务端: {result}")

if __name__ == "__main__":
    # 打印使用指南
    RPCUsageGuide.printUsageGuide()
    
    # 运行测试
    testRPCCalls() 