import _G

# 全局变量存储模式设置
_isServerMode = True

def handleServerRPCCall(data):
    """服务端RPC调用处理器（全局函数）"""
    _handleRPCCall(data, isServer=True)

def handleClientRPCCall(data):  
    """客户端RPC调用处理器（全局函数）"""
    _handleRPCCall(data, isServer=False)

def _handleRPCCall(data, isServer=True):
    """内部RPC调用处理方法
    
    Args:
        data: RPC调用数据
        isServer: 是否为服务端模式
    """
    g = _G._G_
    log = g.Log()
    sid = None
    
    # 服务端模式需要获取session id
    if isServer:
        try:
            from flask import request
            sid = request.sid
        except:
            pass
    
    try:
        # 处理RPC调用
        result = g.handleRPC(data)
        
        # 发送响应
        sio = g.sio()
        if sio:
            if isServer and sid:
                sio.emit('_Result', result, room=sid)
            else:
                sio.emit('_Result', result)
        else:
            if isServer:
                log.e("[RPCHandler] Socket.IO实例为空，无法发送响应")
        
    except Exception as e:
        mode = "SRPCHandler" if isServer else "CRPCHandler"
        log.ex(e, f"[{mode}] 处理RPC调用失败")
        
        # 发送错误响应
        errorResult = {
            'success': False,
            'error': str(e),
            'requestId': data.get('requestId') if data else None
        }
        
        sio = g.sio()
        if sio:
            if isServer and sid:
                sio.emit('_Result', errorResult, room=sid)
            else:
                sio.emit('_Result', errorResult)
        else:
            if isServer:
                log.e("[RPCHandler] Socket.IO实例为空，无法发送错误响应")


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