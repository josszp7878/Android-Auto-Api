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
    /** @type {Map<string, Function>} 等待响应的请求 */
    static #pendingRequests = new Map();
    
    /** @type {number} 请求ID计数器 */
    static #requestIdCounter = 0;
    
    /**
     * 初始化RPC系统
     */
    static init() {
        const socket = Socketer.getSocket();
        if (!socket) {
            console.error('RPC初始化失败：Socket.IO未连接');
            return false;
        }
        
        // 监听RPC响应事件
        socket.on('_Result', this.#handleRPCResponse.bind(this));
        
        // 监听测试响应
        socket.on('test_rpc_response', (data) => {
            console.log('收到测试RPC响应:', data);
        });
        
        console.log('前端RPC系统已初始化');
        return true;
    }
    
    /**
     * 处理RPC响应
     * @param {Object} response RPC响应数据
     */
    static #handleRPCResponse(response) {
        const requestId = response.requestId;
        if (!requestId) {
            console.warn('收到无效RPC响应：缺少requestId', response);
            return;
        }
        
        const resolver = this.#pendingRequests.get(requestId);
        if (resolver) {
            this.#pendingRequests.delete(requestId);
            resolver(response);
        } else {
            console.warn('收到未知请求的RPC响应:', requestId, response);
        }
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
        // console.log('Socket连接状态:', socket.connected);
        
        return new Promise((resolve) => {
            // 设置超时
            const timeoutId = setTimeout(() => {
                this.#pendingRequests.delete(requestId);
                const executionTime = Date.now() - startTime;
                sheet.addTempLog(`RPC调用超时: ${className}.${methodName} (${timeout}ms), 执行时间: ${executionTime}ms`, 'e', 'RPC', 'Browser');
                resolve(null);
            }, timeout);
            
            // 保存请求解析器
            this.#pendingRequests.set(requestId, (response) => {
                clearTimeout(timeoutId);
                const executionTime = Date.now() - startTime;
                // console.log('收到RPC响应:', response);
                
                // 如果有错误，显示错误信息并返回null
                if (response.error) {
                    sheet.addTempLog(`RPC调用出错: ${className}.${methodName} - ${response.error}, 执行时间: ${executionTime}ms`, 'e', 'RPC', 'Browser');
                    resolve(null);
                } else if (response.success === false) {
                    sheet.addTempLog(`RPC调用失败: ${className}.${methodName}, 执行时间: ${executionTime}ms`, 'e', 'RPC', 'Browser');
                    resolve(null);
                } else {
                    // 成功时返回结果
                    resolve(response.result);
                }
            });
            
            // 发送RPC请求
            socket.emit('RPC_Call', rpcData);
        });
    }
    

    
    /**
     * 获取等待中的请求数量（用于调试）
     * @returns {number} 等待中的请求数量
     */
    static getPendingRequestsCount() {
        return this.#pendingRequests.size;
    }
    
    /**
     * 清理所有等待中的请求（用于重置）
     */
    static clearPendingRequests() {
        this.#pendingRequests.clear();
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