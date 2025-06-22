import _G
from datetime import datetime

def testRPCCalls():
    """测试RPC调用示例"""
    g = _G._G_
    log = g.Log()
    
    # 示例1: 调用获取应用列表的类方法
    log.i("=== RPC调用示例 ===")
    
    # 服务端调用客户端的RPC方法
    if g.isServer():
        device_id = "test_device"  # 实际使用时需要真实的设备ID
        
        # 调用获取应用列表
        result = g.RPC(device_id, "_App_", "getAppList")
        log.i(f"获取应用列表结果: {result}")
        
        # 调用获取当前页面信息
        result = g.RPC(device_id, "_App_", "getCurrentPageInfo")
        log.i(f"获取当前页面信息结果: {result}")
        
        # 调用带参数的方法
        result = g.RPC(device_id, "_App_", "getScores", datetime.now())
        log.i(f"获取收益分数结果: {result}")
        
    else:
        # 客户端调用服务端的RPC方法
        result = g.RPC(None, "_App_", "getAppList")
        log.i(f"客户端调用服务端 - 获取应用列表结果: {result}")

def exampleCustomRPCClass():
    """自定义RPC类示例"""
    from RPC import RPC
    
    class MyRPCService:
        def __init__(self, name):
            self.name = name
        
        @RPC()
        def sayHello(self, message: str) -> dict:
            """问候方法"""
            return {
                'success': True,
                'message': f"{self.name} says: {message}",
                'timestamp': datetime.now().isoformat()
            }
        
        @RPC()
        def calculate(self, a: int, b: int, operation: str = 'add') -> dict:
            """计算方法"""
            try:
                if operation == 'add':
                    result = a + b
                elif operation == 'subtract':
                    result = a - b
                elif operation == 'multiply':
                    result = a * b
                elif operation == 'divide':
                    result = a / b if b != 0 else None
                else:
                    raise ValueError(f"不支持的操作: {operation}")
                
                return {
                    'success': True,
                    'result': result,
                    'operation': operation,
                    'operands': [a, b]
                }
            except Exception as e:
                return {
                    'success': False,
                    'error': str(e)
                }
    
    # 创建实例并注册，使用lambda获取实例
    service = MyRPCService("RPCService")
    g = _G._G_
    g.registerRPC(MyRPCService, lambda: service)
    
    # 测试调用示例
    if g.isServer():
        # 服务端调用客户端
        device_id = "test_device"
        result = g.RPC(device_id, "MyRPCService", "sayHello", "Hello from server!")
        print(f"服务端->客户端 sayHello结果: {result}")
        
        result = g.RPC(device_id, "MyRPCService", "calculate", 10, 5, "multiply")
        print(f"服务端->客户端 calculate结果: {result}")
        
        # 服务端本地调用
        result = g.RPC(None, "MyRPCService", "sayHello", "Hello locally!")
        print(f"服务端本地调用结果: {result}")
        
    else:
        # 客户端调用服务端
        result = g.RPC(None, "MyRPCService", "sayHello", "Hello from client!")
        print(f"客户端->服务端 sayHello结果: {result}")
        
        # 客户端本地调用
        result = g.RPC("local", "MyRPCService", "calculate", 20, 4, "divide")
        print(f"客户端本地调用结果: {result}")

# 使用示例
if __name__ == "__main__":
    testRPCCalls()
    exampleCustomRPCClass() 