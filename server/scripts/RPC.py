import functools
import threading
import time
import uuid
import inspect
from typing import Dict, Any, Optional, Callable
from datetime import datetime
import _G

class RPCManager:
    """RPC管理器 - 处理RPC方法注册和调用"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._rpcMethods: Dict[str, Dict[str, Callable]] = {}  # {className: {methodName: method}}
        self._rpcClasses: Dict[str, type] = {}  # {className: class}
        self._pendingCalls: Dict[str, Any] = {}  # {requestId: result}
        self._callLock = threading.Lock()
        self._initialized = True
    
    def registerRpcClass(self, cls):
        """注册RPC类
        
        Args:
            cls: 要注册的类
        """
        className = cls.__name__
        if className not in self._rpcMethods:
            self._rpcMethods[className] = {}
        
        # 存储类对象
        self._rpcClasses[className] = cls
        
        # 扫描类中的RPC方法
        for methodName in dir(cls):
            method = getattr(cls, methodName)
            if hasattr(method, '_is_rpc_method'):
                self._rpcMethods[className][methodName] = method
                
    def getRpcMethod(self, className: str, methodName: str) -> Optional[Callable]:
        """获取RPC方法"""
        # 先尝试获取方法
        call = self._rpcMethods.get(className, {}).get(methodName)
        # 如果方法不存在，则尝试获取带下划线的方法
        if not call and not className.endswith('_'):
            call = self._rpcMethods.get(className + '_', {}).get(methodName)
        return call    
    
    def callRpcMethod(self, className: str, methodName: str, id: str, args: list, kwargs: dict):
        """调用RPC方法"""
        import inspect
        g = _G._G_
        log = g.Log()
        
        try:
            method = self.getRpcMethod(className, methodName)
            if not method:
                # log.e(f"RPC方法不存在: {className}.{methodName}")
                return {
                    'error': f'RPC方法不存在: {className}.{methodName}'
                }
            
            # 获取实例 - 直接使用通用的getInst函数
            cls_obj = self._rpcClasses.get(className)
            if cls_obj:
                try:
                    instance = getInst(cls_obj, id)
                except Exception as e:
                    log.ex(e, f"获取RPC实例异常: {className}, instance_id={id}")
                    instance = None
            else:
                log.e(f"RPC类未注册: {className}")
                instance = None
            
            if id and instance is None:
                return {
                    'error': f'RPC实例不存在: {className}, instance_id={id}'
                }
            
            # 自动类型转换处理
            if cls_obj:
                original_method = getattr(cls_obj, methodName, None)
                if original_method:
                    args, kwargs = self._convertRpcTypes(original_method, args, kwargs)
            
            # 智能方法调用逻辑：根据方法类型选择合适的调用方式
            if cls_obj:
                # 从类对象获取原始方法定义
                original_method = getattr(cls_obj, methodName, None)
                if original_method:
                    result = self._callMethod(original_method, cls_obj, instance, args, kwargs)
                else:
                    # 回退到使用注册时获取的method
                    result = self._callMethod(method, cls_obj, instance, args, kwargs)
            else:
                # 没有类对象，直接调用method
                result = self._callMethod(method, None, instance, args, kwargs)
            
            # 检查方法返回值是否已经是标准格式
            if isinstance(result, dict) and ('error' in result or 'result' in result):
                return result
            else:
                # 包装为标准格式
                return {
                    'result': result,
                }
        except Exception as e:
            log.ex(e, f"RPC方法调用失败: {className}.{methodName}")
            return {
                'error': str(e),
            }
    
    def _convertRpcTypes(self, method, args: list, kwargs: dict):
        """自动转换RPC参数类型
        
        Args:
            method: 目标方法对象
            args: 位置参数列表  
            kwargs: 关键字参数字典
            
        Returns:
            转换后的(args, kwargs)元组
        """
        import inspect
        from datetime import datetime, date
        
        try:
            # 获取方法签名
            sig = inspect.signature(method)
            params = sig.parameters
            param_names = list(params.keys())
            
            # 转换位置参数
            converted_args = []
            for i, arg in enumerate(args):
                if i < len(param_names):
                    param_name = param_names[i]
                    param = params[param_name]
                    # 跳过self/cls参数的类型转换
                    if param_name in ['self', 'cls']:
                        converted_args.append(arg)
                    else:
                        converted_arg = self._convertSingleType(arg, param.annotation)
                        converted_args.append(converted_arg)
                else:
                    converted_args.append(arg)
            
            # 转换关键字参数
            converted_kwargs = {}
            for key, value in kwargs.items():
                if key in params:
                    param = params[key]
                    converted_value = self._convertSingleType(value, param.annotation)
                    converted_kwargs[key] = converted_value
                else:
                    converted_kwargs[key] = value
            
            return converted_args, converted_kwargs
            
        except Exception as e:
            # 如果类型转换失败，返回原始参数
            g = _G._G_
            g.Log().ex(e, f"RPC类型转换失败: {method}")
            return args, kwargs
    
    def _convertSingleType(self, value, annotation):
        """转换单个值的类型
        
        Args:
            value: 要转换的值
            annotation: 目标类型注解
            
        Returns:
            转换后的值
        """
        from datetime import datetime, date
        import _G
        
        # 如果没有类型注解或值为None，直接返回
        if annotation == inspect.Parameter.empty or value is None:
            return value
        
        # 如果已经是目标类型，直接返回
        if isinstance(value, annotation):
            return value
        
        # 字符串转datetime
        if annotation == datetime and isinstance(value, str):
            try:
                return _G.DateHelper.toDate(value)
            except:
                return value
        
        # 字符串转date
        if annotation == date and isinstance(value, str):
            try:
                dt = _G.DateHelper.toDate(value)
                return dt.date() if dt else value
            except:
                return value
        
        # 其他类型转换可以在这里添加
        # ...
        
        return value
    
    def _callMethod(self, method, cls_obj, instance, args: list, kwargs: dict):
        """智能调用方法，根据方法类型选择合适的调用方式
        
        Args:
            method: 要调用的方法
            cls_obj: 类对象（可选）
            instance: 实例对象（可选）
            args: 位置参数列表
            kwargs: 关键字参数字典
        
        Returns:
            方法调用结果
        """
        import inspect
        
        # 检查是否是已绑定的类方法
        if hasattr(method, '__self__') and inspect.isclass(method.__self__):
            # 已绑定的类方法，直接调用
            return method(*args, **kwargs)
        
        # 检查是否是已绑定的实例方法
        elif hasattr(method, '__self__') and not inspect.isclass(method.__self__):
            # 已绑定的实例方法，直接调用
            return method(*args, **kwargs)
        
        # 检查原始方法是否是classmethod
        elif hasattr(method, '__func__') and isinstance(method, classmethod):
            # 未绑定的classmethod，需要手动绑定类
            if cls_obj:
                return method.__func__(cls_obj, *args, **kwargs)
            else:
                raise Exception("类方法需要类对象，但未提供")
        
        # 检查是否是被装饰器包装的方法
        elif hasattr(method, '__wrapped__'):
            # 递归调用被包装的方法
            return self._callMethod(method.__wrapped__, cls_obj, instance, args, kwargs)
        
        # 尝试从类对象获取未装饰的原始方法
        elif cls_obj and hasattr(cls_obj, method.__name__ if hasattr(method, '__name__') else ''):
            raw_method = getattr(cls_obj, method.__name__)
            
            # 检查原始方法是否是classmethod
            if hasattr(raw_method, '__self__') and inspect.isclass(raw_method.__self__):
                # 绑定的类方法
                return raw_method(*args, **kwargs)
            elif instance:
                # 实例方法，需要实例
                return raw_method(instance, *args, **kwargs)
            else:
                # 静态方法或无需实例的方法
                return raw_method(*args, **kwargs)
        
        # 默认调用方式
        else:
            if instance:
                # 尝试作为实例方法调用
                return method(instance, *args, **kwargs)
            else:
                # 尝试作为静态方法或函数调用
                return method(*args, **kwargs)

# 全局RPC管理器实例
rpcManager = RPCManager()

def getInst(cls, id=None):
    """默认实例获取器，支持App、Device、Task类的实例获取
    
    Args:
        cls: 类对象
        id: 实例ID（可选）
        
    Returns:
        对应类的实例
    """
    g = _G._G_
    log = g.Log()
    
    try:
        className = cls.__name__
        
        # App类实例获取
        if className in ['_App_', 'SApp_']:
            from _App import _App_
            return _App_.get(id)
        # Device类实例获取
        elif className in ['CDevice_', 'SDevice_', 'Device_']:
            from _Device import _Device_
            return _Device_.get(id)
        
        # Task类实例获取  
        elif className in ['CTask_', 'STask_', 'Task_']:
            return _getTaskInst(id)
        
        else:
            log.w(f"不支持的默认实例获取器类型: {className}")
            return None
            
    except Exception as e:
        log.ex(e, f"获取默认实例失败: {className}")
        return None

def _getTaskInst(id=None):
    """获取Task实例"""
    g = _G._G_
    try:
        if id is None:
            return None
        if g.isServer():
            from STask import STask_
            task = STask_.getByID(id)
            return task
        else:
            # 客户端获取当前任务实例
            device = g.CDevice()
            return device.getTask(id) if device else None
    except Exception as e:
        g.Log().ex(e, f"获取Task实例失败: {id}")
        return None

def RPC(className: str = None):
    """RPC装饰器 - 标记方法为RPC可调用方法
    
    Args:
        className: 可选的类名，用于区分同名方法
    """
    def decorator(func):
        # 标记为RPC方法
        func._is_rpc_method = True
        func._rpc_class_name = className
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        
        wrapper._is_rpc_method = True
        wrapper._rpc_class_name = className
        return wrapper
    
    return decorator

def registerRPC(cls):
    """注册RPC类
    
    Args:
        cls: 要注册的类
    """
    rpcManager.registerRpcClass(cls)

def callRPC(deviceID: str, className: str, methodName: str, params: dict = None):
    """远程调用RPC方法
    
    Args:
        deviceID: 设备ID（为None时表示客户端调用服务端）
        className: 类名
        methodName: 方法名
        params: 参数字典，支持以下键：
            - id: 实例ID（可选）
            - args: 位置参数列表（可选）
            - kwargs: 关键字参数字典（可选）
            - timeout: 超时时间（可选，默认8秒）
    
    Returns:
        RPC调用结果或None（如果出错）
        
    Examples:
        # 类方法调用
        callRPC(None, '_App_', 'getAppList')
        
        # 实例方法调用
        callRPC(None, 'SDevice_', 'getDeviceInfo', {'id': 'device1'})
        
        # 带参数的方法调用
        callRPC(None, 'STask_', 'updateTaskScore', {
            'id': 'task1', 
            'args': [100]
        })
    """
    g = _G._G_
    log = g.Log()
    
    try:
        # 解析参数
        if params is None:
            params = {}
        
        # 解析参数用于远程调用
        id = params.get('id')
        args = params.get('args', [])
        kwargs = params.get('kwargs', {})
        timeout = params.get('timeout', 8)
        
        request_id = str(uuid.uuid4())
        
        # 构造RPC调用数据
        rpcData = {
            'requestId': request_id,
            'className': className,
            'methodName': methodName,
            'id': id,
            'args': args,
            'kwargs': kwargs,
            'timestamp': datetime.now().isoformat()
        } 
        
        # 根据是否为服务端选择调用方式
        if g.isServer():
            if deviceID:
                # 服务端向指定客户端发送RPC调用
                raw_result = _callRpcToClient(deviceID, rpcData, timeout)
            else:
                log.e("缺少必要参数deviceID")
                return None
        else:
            # 客户端向服务端发送RPC调用
            raw_result = _callRpcToServer(rpcData, timeout)
        
        # 处理标准化的RPC返回格式
        if isinstance(raw_result, dict):
            # 检查是否有错误
            if 'error' in raw_result and raw_result['error']:
                log.e(f"RPC调用失败: {className}.{methodName} - {raw_result['error']}")
                return None
            # 返回实际结果
            if 'result' in raw_result:
                return raw_result['result']
            
            # 如果没有错误但也没有result，返回整个字典
            return raw_result
        else:
            # log.e(f"RPC调用失败, 返回值不是字典 : {className}.{methodName} - {raw_result}")
            return None
            
    except Exception as e:
        log.ex(e, f"RPC调用失败: {className}.{methodName}")
        return None

def _callRpcToClient(strDeviceID: str, rpcData: dict, timeout: int):
    """服务端向客户端发送RPC调用"""
    g = _G._G_
    log = g.Log()
    
    try:
        # 先根据deviceID获取Device对象
        deviceMgr = g.SDeviceMgr()
        devices = deviceMgr.devices
        deviceID = int(strDeviceID)
        device = next((d for d in devices if d.id == deviceID and d.isConnected()), None)
        if not device:
            return {
                'success': False,
                'error': f'设备不存在: {strDeviceID}',
                'timestamp': datetime.now().isoformat()
            }
        
        # 获取设备的sid
        sid = device.sid
        if not sid:
            return {
                'success': False,
                'error': f'设备未连接: {strDeviceID}',
                'timestamp': datetime.now().isoformat()
            }
        
        # 使用sid发送RPC调用
        result = g.emitRet('RPC_Call', rpcData, sid, timeout)
        return result
        
    except Exception as e:
        log.ex(e, f"向客户端发送RPC调用失败: {strDeviceID}")
        return {
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }

def _callRpcToServer(rpcData: dict, timeout: int):
    """客户端向服务端发送RPC调用"""
    g = _G._G_
    log = g.Log()
    
    try:
        # 使用现有的emit机制发送RPC调用
        result = g.emitRet('RPC_Call', rpcData, None, timeout)
        return result
    except Exception as e:
        log.ex(e, "向服务端发送RPC调用失败")
        return {
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }

def handleRpcCall(data: dict):
    """处理RPC调用请求"""
    g = _G._G_
    log = g.Log()
    
    try:
        request_id = data.get('requestId')
        device_id = data.get('deviceId')
        className = data.get('className')
        methodName = data.get('methodName')
        instanceID = data.get('id')
        args = data.get('args', [])
        kwargs = data.get('kwargs', {})
        timeout = data.get('timeout', 8)
        
        log.i_(f"处理RPC调用: deviceId={device_id}, {className}.{methodName}")
        
        # 路由判断：根据deviceId决定本地处理还是转发到客户端
        if device_id is None or device_id == '':
            # 服务端本地调用
            result = rpcManager.callRpcMethod(className, methodName, instanceID, args, kwargs)
        else:
            # 转发到指定客户端
            log.i(f"转发RPC调用到客户端设备 {device_id}: {className}.{methodName}")            
            # 构造转发数据（去掉deviceId，避免客户端递归）
            forward_data = {
                'requestId': request_id,
                'className': className,
                'methodName': methodName,
                'id': instanceID,
                'args': args,
                'kwargs': kwargs,
                'timestamp': data.get('timestamp')
            }
            
            # 调用客户端转发函数
            result = _callRpcToClient(device_id, forward_data, timeout)
        
        # 确保结果包含请求ID
        if isinstance(result, dict):
            result['requestId'] = request_id
        else:
            result = {
                'success': True,
                'result': result,
                'requestId': request_id
            }
        
        return result
        
    except Exception as e:
        log.ex(e, f"处理RPC调用失败: {data}")
        return {
            'success': False,
            'error': str(e),
            'requestId': data.get('requestId'),
            'timestamp': datetime.now().isoformat()
        }

# RPC功能已直接集成到_G_类中，无需额外扩展
def initRPC():
    """统一初始化所有RPC类注册
    
    这个函数会导入并注册所有包含RPC方法的类，确保RPC系统完整初始化
    """
    g = _G._G_
    log = g.Log()
    
    try:
        log.i("开始初始化RPC系统...")
        
        # 动态获取所有模块名
        g = _G._G_
        module_names = g.getScriptNames()
        
        log.i(f"发现{len(module_names)}个模块: {module_names}")
        
        # 根据运行环境过滤模块
        if g.isServer():
            log.i("注册服务端RPC类...")
        else:
            log.i("注册客户端RPC类...")
        
        registered_count = 0
        isServer = g.isServer()
        for module_name in module_names:
            try:
                # 根据模块名推导类名（添加后缀_）
                class_name = f"{module_name}_"
                
                # 环境过滤：根据运行环境选择合适的模块
                if isServer:
                    # 服务端跳过客户端特定模块
                    if module_name.startswith('C') and module_name not in ['_App']:
                        continue
                else:
                    # 客户端跳过服务端特定模块
                    if module_name.startswith('S') and module_name not in ['_App']:
                        continue
                
                # 使用_G_.getClassLazy延迟导入机制
                cls = g.getClassLazy(module_name)
                if cls:
                    registerRPC(cls)
                    registered_count += 1
                    # log.i(f"已注册RPC类: {class_name} (来自模块 {module_name})")
                    
            except Exception as e:
                log.ex(e, f"注册RPC类 {class_name} 失败")

        # 然后初始化RPC事件处理器
        from RPCHandler import RPCHandler
        RPCHandler.initializeRPCHandlers(isServer)

        log.i(f"RPC系统初始化完成:")
        
        # 显示注册统计
        # total_classes = len(rpcManager._rpcClasses)
        # total_methods = sum(len(methods) for methods in rpcManager._rpcMethods.values())
        
        # log.i(f"  - 本次注册类数: {registered_count}")
        # log.i(f"  - 总注册类数: {total_classes}")
        # log.i(f"  - 总RPC方法数: {total_methods}")
        
        # # 输出详细的注册信息
        # for class_name, methods in rpcManager._rpcMethods.items():
        #     method_names = list(methods.keys())
        #     log.d(f"  - {class_name}: {method_names}")
        
        return True
        
    except Exception as e:
        log.ex(e, "RPC系统初始化失败")
        return False


def debugRPCRegistry():
    """调试RPC注册状态"""
    g = _G._G_
    log = g.Log()
    
    log.i("=== RPC注册状态调试 ===")
    # log.i(f"已注册类数: {len(rpcManager._rpcClasses)}")
    log.i(f"已注册方法总数: {sum(len(methods) for methods in rpcManager._rpcMethods.values())}")
    
    for class_name, methods in rpcManager._rpcMethods.items():
        method_names = list(methods.keys())
        # log.i(f"类 {class_name}: {method_names}")
        
        # 检查特定的getAppList方法
        if class_name == '_App_' and 'getAppList' in methods:
            method = methods['getAppList']
            log.i(f"  getAppList方法详情: {method}")
            log.i(f"  方法类型: {type(method)}")
            log.i(f"  是否可调用: {callable(method)}")
    
    # 测试特定方法的存在性
    app_method = rpcManager.getRpcMethod('_App_', 'getAppList')
    log.i(f"getRpcMethod('_App_', 'getAppList'): {app_method}")
    
    log.i("=== RPC注册状态调试结束 ===")
