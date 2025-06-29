/**
 * 前端RPC模块 - 支持前端调用服务端RPC方法
 * 基于Socket.IO实现
 * 
 * 使用示例：
 * const result = await rpc.call('device123', 'SDevice', 'getInfo', {});
 * if (result) {
 *     console.log('调用成功:', result);
 * } else {
 *     console.log('调用失败，请查看控制台错误信息');
 * }
 */
class RPC {
    /** @type {number} 请求ID计数器 */
    static #requestIdCounter = 0;
    
    /**
     * 初始化RPC系统（现在使用emitRet方式，不需要监听_Result事件）
     */
    static init() {
        const socket = Socketer.getSocket();
        if (!socket) {
            console.error('RPC初始化失败：Socket.IO未连接');
            return false;
        }
        
        // 监听测试响应
        socket.on('test_rpc_response', (data) => {
            console.log('收到测试RPC响应:', data);
        });
        
        console.log('前端RPC系统已初始化');
        return true;
    }
    

    
    /**
     * 生成唯一请求ID
     * @returns {string} 请求ID
     */
    static #generateRequestId() {
        return `rpc_${++this.#requestIdCounter}_${Date.now()}`;
    }
    
    /**
     * 调用RPC方法
     * @param {string|null} deviceId 设备ID（null表示服务端本地调用）
     * @param {string} className 类名
     * @param {string} methodName 方法名
     * @param {Object} params 参数对象
     * @param {string} params.id 实例ID（可选）
     * @param {Array} params.args 位置参数列表（可选）
     * @param {Object} params.kwargs 关键字参数对象（可选）
     * @param {number} params.timeout 超时时间（可选，默认10000ms）
     * @returns {Promise<any>} RPC调用结果，出错时返回null
     */
    static async call(deviceId, className, methodName, params = {}) {
        const socket = Socketer.getSocket();
        if (!socket) {
            console.error('RPC调用失败: Socket.IO未连接');
            return null;
        }
        
        const requestId = this.#generateRequestId();
        const timeout = params.timeout || 10000;
        const startTime = Date.now();
        
        const rpcData = {
            requestId,
            deviceId,
            className,
            methodName,
            id: params.id,
            args: params.args || [],
            kwargs: params.kwargs || {},
            timestamp: startTime
        };
        
        console.log('发送RPC调用:', rpcData);
        
        try {
            // 使用emitRet方式直接获取响应
            const response = await Socketer.emitRet('B2S_RPC_Call', rpcData, timeout);
            const executionTime = Date.now() - startTime;
            
            // 如果有错误，显示错误信息并返回null
            if (response && response.error) {
                sheet.log(`RPC调用出错: ${className}.${methodName} - ${response.error}, 执行时间: ${executionTime}ms`, 'e');
                return null;
            } else if (response && response.success === false) {
                sheet.log(`RPC调用失败: ${className}.${methodName}, 执行时间: ${executionTime}ms`, 'e');
                return null;
            } else {
                // 成功时返回结果
                return response ? response.result : response;
            }
        } catch (error) {
            const executionTime = Date.now() - startTime;
            sheet.log(`RPC调用异常: ${className}.${methodName} - ${error.message}, 执行时间: ${executionTime}ms`, 'e');
            return null;
        }
    }
    

    

}

// 全局RPC调用快捷方法
window.rpc = {
    /**
     * 通用RPC调用
     * @param {string|null} deviceId 设备ID，null表示服务端调用
     * @param {string} className 类名
     * @param {string} methodName 方法名
     * @param {Object} params 参数对象
     * @returns {Promise<any>} 返回结果数据，出错时返回null（错误信息会在控制台显示）
     */
    call: (deviceId, className, methodName, params = {}) => 
        RPC.call(deviceId, className, methodName, params)
};

// 页面加载完成后自动初始化
document.addEventListener('DOMContentLoaded', () => {
    // 延迟初始化，确保Socket.IO已连接
    setTimeout(() => {
        RPC.init();
    }, 1000);
});

// 发送测试事件
const socket = Socketer.getSocket();
socket.emit('test_rpc', {test: 'hello from browser'}); 