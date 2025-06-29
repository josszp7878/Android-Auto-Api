import _G

# 全局变量存储模式设置
_isServerMode = True

def handleServerRPCCall(data):
    """服务端RPC调用处理器（全局函数）"""
    return _handleRPCCall(data, isServer=True)

def handleClientRPCCall(data):  
    """客户端RPC调用处理器（全局函数）"""
    return _handleRPCCall(data, isServer=False)

def _handleRPCCall(data, isServer=True):
    """内部RPC调用处理方法
    
    Args:
        data: RPC调用数据
        isServer: 是否为服务端模式
    
    Returns:
        RPC调用结果（直接返回给Socket.IO回调）
    """
    g = _G._G_
    log = g.Log()
    
    try:
        # 处理RPC调用
        result = g.handleRPC(data)
        return result
        
    except Exception as e:
        mode = "SRPCHandler" if isServer else "CRPCHandler"
        log.ex(e, f"[{mode}] 处理RPC调用失败")
        
        # 返回错误结果
        errorResult = {
            'success': False,
            'error': str(e),
            'requestId': data.get('requestId') if data else None
        }
        return errorResult


class RPCHandler:
    """通用RPC事件处理器"""
    
    @classmethod
    def initializeRPCHandlers(cls, isServer=True):
        """初始化RPC事件处理器
        
        Args:
            isServer: 是否为服务端模式，影响响应发送方式
        """
        global _isServerMode
        _isServerMode = isServer
        
        g = _G._G_
        sio = g.sio()
        log = g.Log()
        
        if sio:
            # 根据模式注册全局函数处理器
            if isServer:
                sio.on('RPC_Call')(handleServerRPCCall)
                try:
                    log.i("服务端RPC事件处理器已初始化")
                except Exception as e:
                    log.ex(e, "RPC_Call事件处理器注册失败")
            else:
                sio.on('RPC_Call')(handleClientRPCCall)
                log.i("客户端RPC事件处理器已初始化")
        else:
            if isServer:
                log.e("Socket.IO实例为空，无法注册RPC事件处理器") 