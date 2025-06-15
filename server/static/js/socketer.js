class Socketer {
    /** @type {Socketer} */
    static #instance = null;
    static #socket = null;

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

            Socketer.#socket.emit(event, payload);
            return true;
        } catch (e) {
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
}