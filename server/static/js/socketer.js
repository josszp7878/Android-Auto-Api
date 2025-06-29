class Socketer {
    /** @type {Socketer} */
    static #instance = null;
    static #socket = null;
    
    /** @type {number} RPC请求ID计数器 */
    static #rpcRequestIdCounter = 0;

    //声明返回类型为Socketer
    /**
     * 初始化Socket单例
     * @param {Object} config 配置参数
     * @returns {Socketer} 返回当前类实例
     */
    static init(config = {}) {
        if (!this.#instance) {
            this.#instance = new Socketer(config);
        }
        return this.#instance;
    }

    constructor({ deviceId = '', queryParams = {} } = {}) {
        if (Socketer.#socket) return Socketer.#instance;

        this.deviceId = deviceId;
        this.queryParams = {
            device_id: deviceId,
            ...queryParams
        };

        Socketer.#socket = io({
            query: this.queryParams,
            reconnection: true,
            reconnectionAttempts: 5
        });

        this.registerCoreEvents();
    }

    registerCoreEvents() {
        Socketer.#socket.on('connect', () => {
            console.debug('Socket connected');
        });

        Socketer.#socket.on('disconnect', () => {
            console.warn('Socket disconnected');
        });
    }

     /**
     * 发送带响应的请求（纯Promise模式）
     * @param {string} event 事件名称（需符合B2S_前缀规范）
     * @param {Object} data 发送数据
     * @param {number} [timeout=5000] 超时时间(ms)
     * @returns {Promise} 返回响应数据
     */
    emitRet(event, data = {}, timeout = 10000) {
            return new Promise((resolve, reject) => {
                const timer = setTimeout(() => {
                    reject(new Error(`请求超时: ${event}`));
                }, timeout);
    
            Socketer.#socket.emit(event, data, (response) => {
                clearTimeout(timer);
                if (response?.error) {
                    reject(new Error(response.error.message || '请求失败'));
                    return;
                }
                // console.log('response', response);
                resolve(response);
            });
        });
    }

    emit(event, data = {}, { sid = null, retries = 3 } = {}) {
        try {
            const payload = sid ? { ...data, _sid: sid } : data;

            if (!sid && this.deviceId) {
                payload.deviceId = this.deviceId;
            }

            // sheet.log(`[DEBUG] Socketer.emit 发送事件: ${event}`, payload);
            // sheet.log(`[DEBUG] Socket连接状态: ${Socketer.#socket.connected}`);
            // sheet.log(`[DEBUG] Socket ID: ${Socketer.#socket.id}`);
            
            Socketer.#socket.emit(event, payload);
            // console.log(`[DEBUG] 事件 ${event} 已发送`);
            return true;
        } catch (e) {
            // console.error(`[DEBUG] 发送事件 ${event} 失败:`, e);
            if (retries > 0) {
                return this.emit(event, data, { sid, retries: retries - 1 });
            }
            console.error(`Event failed after retries: ${event}`, e);
            return false;
        }
    }

    static getSocket() {
        return this.#socket;
    }

    /**
     * 新增: 支持 async/await 的 emitRet 封装
     * 用法: const result = await Socketer.asyncEmit(event, data, timeout)
     */
    static async asyncEmit(event, data = {}, timeout = 5000) {
        return await Socketer.emitRet(event, data, timeout);
    }

    /**
     * 生成唯一RPC请求ID
     * @returns {string} 请求ID
     */
    static #generateRpcRequestId() {
        return `rpc_${++this.#rpcRequestIdCounter}_${Date.now()}`;
    }

    /**
     * RPC调用方法 - 支持前端调用服务端RPC方法
     * @param {string|null} deviceId 设备ID（null表示服务端本地调用）
     * @param {string} className 类名
     * @param {string} methodName 方法名
     * @param {Object} params 参数对象
     * @param {string} params.id 实例ID（可选）
     * @param {Object} params.kwargs 关键字参数对象（可选）
     * @param {number} params.timeout 超时时间（可选，默认10000ms）
     * @returns {Promise<any>} RPC调用结果，出错时返回null
     */
    static async rpcCall(deviceId, className, methodName, params = {}) {
        if (!this.#socket) {
            console.error('RPC调用失败: Socket.IO未连接');
            return null;
        }
        
        const requestId = this.#generateRpcRequestId();
        const timeout = params.timeout || 10000;
        const startTime = Date.now();
        
        const rpcData = {
            requestId,
            deviceId,
            className,
            methodName,
            params
        };
        
        console.log('发送RPC调用:', rpcData);
        
        try {
            // 使用静态方法调用emitRet
            const instance = this.#instance || new Socketer();
            const response = await instance.emitRet('B2S_RPC_Call', rpcData, timeout);
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

    /**
     * 初始化RPC系统
     */
    static initRpc() {
        if (!this.#socket) {
            console.error('RPC初始化失败：Socket.IO未连接');
            return false;
        }
        
        // 监听测试响应
        this.#socket.on('test_rpc_response', (data) => {
            console.log('收到测试RPC响应:', data);
        });
        
        console.log('前端RPC系统已初始化');
        return true;
    }
}

// 全局RPC调用快捷方法 - 保持向下兼容
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
        Socketer.rpcCall(deviceId, className, methodName, params)
};

// 页面加载完成后自动初始化RPC
document.addEventListener('DOMContentLoaded', () => {
    // 延迟初始化，确保Socket.IO已连接
    setTimeout(() => {
        Socketer.initRpc();
    }, 1000);
});

// 发送测试事件
if (typeof io !== 'undefined') {
    const socket = Socketer.getSocket();
    if (socket) {
        socket.emit('test_rpc', {test: 'hello from browser'});
    }
}