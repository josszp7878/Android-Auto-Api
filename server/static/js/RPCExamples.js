/**
 * 前端RPC使用示例
 * 本文件提供了各种RPC调用的示例代码
 */

class RPCExamples {
    
    /**
     * 基础RPC调用示例
     */
    static async basicExamples() {
        console.log('=== 基础RPC调用示例 ===');
        
        try {
            // 1. 获取应用列表（服务端类方法）
            console.log('1. 获取应用列表:');
            const appList = await rpc.server('_App_', 'getAppList');
            console.log('应用列表:', appList);
            
            // 2. 获取设备信息（指定实例ID）
            console.log('2. 获取设备信息:');
            const deviceInfo = await rpc.server('SDevice_', 'getDeviceInfo', 'device1');
            console.log('设备信息:', deviceInfo);
            
            // 3. 获取任务列表
            console.log('3. 获取任务列表:');
            const taskList = await rpc.server('STask_', 'getTaskList', null, 1);
            console.log('任务列表:', taskList);
            
        } catch (error) {
            console.error('基础示例执行失败:', error);
        }
    }
    
    /**
     * 设备管理示例
     */
    static async deviceExamples() {
        console.log('=== 设备管理示例 ===');
        
        try {
            // 获取设备信息
            const deviceInfo = await rpc.server('SDevice_', 'getDeviceInfo', 'device1');
            console.log('设备信息:', deviceInfo);
            
            // 发送设备命令
            const cmdResult = await rpc.server('SDevice_', 'sendCommand', 'device1', 'takeScreenshot');
            console.log('命令结果:', cmdResult);
            
            // 截屏
            const screenResult = await rpc.server('SDevice_', 'captureScreen', 'device1');
            console.log('截屏结果:', screenResult);
            
        } catch (error) {
            console.error('设备示例执行失败:', error);
        }
    }
    
    /**
     * 任务管理示例
     */
    static async taskExamples() {
        console.log('=== 任务管理示例 ===');
        
        try {
            // 获取任务信息
            const taskInfo = await rpc.server('STask_', 'getTaskInfo', 'task1');
            console.log('任务信息:', taskInfo);
            
            // 更新任务分数
            const updateResult = await rpc.server('STask_', 'updateTaskScore', 'task1', 100);
            console.log('更新结果:', updateResult);
            
            // 获取设备的任务列表
            const deviceTasks = await rpc.server('STask_', 'getTaskList', null, 1);
            console.log('设备任务:', deviceTasks);
            
        } catch (error) {
            console.error('任务示例执行失败:', error);
        }
    }
    
    /**
     * 应用管理示例
     */
    static async appExamples() {
        console.log('=== 应用管理示例 ===');
        
        try {
            // 获取应用列表
            const appList = await rpc.server('_App_', 'getAppList');
            console.log('应用列表:', appList);
            
            // 获取当前页面信息（需要指定应用实例）
            const pageInfo = await rpc.server('_App_', 'getCurrentPageInfo', 'WeChat');
            console.log('页面信息:', pageInfo);
            
            // 获取收益分数
            const scores = await rpc.server('_App_', 'getScores', 'WeChat', new Date());
            console.log('收益分数:', scores);
            
        } catch (error) {
            console.error('应用示例执行失败:', error);
        }
    }
    
    /**
     * 客户端RPC调用示例（如果有客户端连接）
     */
    static async clientExamples() {
        console.log('=== 客户端RPC调用示例 ===');
        
        try {
            // 获取客户端设备信息
            const clientDeviceInfo = await rpc.client('device1', 'CDevice_', 'getDeviceInfo');
            console.log('客户端设备信息:', clientDeviceInfo);
            
            // 设置客户端设备名称
            const nameResult = await rpc.client('device1', 'CDevice_', 'setDeviceName', null, '新设备名');
            console.log('设备重命名结果:', nameResult);
            
            // 获取客户端任务信息
            const clientTaskInfo = await rpc.client('device1', 'CTask_', 'getTaskInfo', 'task1');
            console.log('客户端任务信息:', clientTaskInfo);
            
        } catch (error) {
            console.error('客户端示例执行失败:', error);
        }
    }
    
    /**
     * 错误处理示例
     */
    static async errorHandlingExamples() {
        console.log('=== 错误处理示例 ===');
        
        try {
            // 调用不存在的方法
            await rpc.server('NonExistentClass', 'nonExistentMethod');
        } catch (error) {
            console.log('预期错误 - 类不存在:', error.message);
        }
        
        try {
            // 调用不存在的实例
            await rpc.server('SDevice_', 'getDeviceInfo', 'nonExistentDevice');
        } catch (error) {
            console.log('预期错误 - 实例不存在:', error.message);
        }
        
        try {
            // 超时测试（设置很短的超时时间）
            await rpc.server('_App_', 'getAppList', null, { timeout: 1 });
        } catch (error) {
            console.log('预期错误 - 超时:', error.message);
        }
    }
    
    /**
     * 批量操作示例
     */
    static async batchExamples() {
        console.log('=== 批量操作示例 ===');
        
        try {
            // 并行获取多个设备信息
            const deviceIds = ['device1', 'device2', 'device3'];
            const devicePromises = deviceIds.map(id => 
                rpc.server('SDevice_', 'getDeviceInfo', id).catch(error => ({ error: error.message, deviceId: id }))
            );
            
            const deviceResults = await Promise.all(devicePromises);
            console.log('批量设备信息:', deviceResults);
            
            // 串行更新多个任务分数
            const taskIds = ['task1', 'task2', 'task3'];
            for (const taskId of taskIds) {
                try {
                    const result = await rpc.server('STask_', 'updateTaskScore', taskId, Math.floor(Math.random() * 100));
                    console.log(`任务 ${taskId} 更新结果:`, result);
                } catch (error) {
                    console.log(`任务 ${taskId} 更新失败:`, error.message);
                }
            }
            
        } catch (error) {
            console.error('批量操作失败:', error);
        }
    }
    
    /**
     * 运行所有示例
     */
    static async runAllExamples() {
        console.log('开始运行所有RPC示例...');
        
        await this.basicExamples();
        await new Promise(resolve => setTimeout(resolve, 1000)); // 等待1秒
        
        await this.deviceExamples();
        await new Promise(resolve => setTimeout(resolve, 1000));
        
        await this.taskExamples();
        await new Promise(resolve => setTimeout(resolve, 1000));
        
        await this.appExamples();
        await new Promise(resolve => setTimeout(resolve, 1000));
        
        await this.errorHandlingExamples();
        await new Promise(resolve => setTimeout(resolve, 1000));
        
        await this.batchExamples();
        
        console.log('所有RPC示例执行完成！');
    }
}

// 全局快捷方法
window.rpcExamples = {
    basic: () => RPCExamples.basicExamples(),
    device: () => RPCExamples.deviceExamples(),
    task: () => RPCExamples.taskExamples(),
    app: () => RPCExamples.appExamples(),
    client: () => RPCExamples.clientExamples(),
    error: () => RPCExamples.errorHandlingExamples(),
    batch: () => RPCExamples.batchExamples(),
    all: () => RPCExamples.runAllExamples()
};

// 在控制台中提供使用提示
console.log(`
=== 前端RPC使用指南 ===

1. 基础调用方法:
   rpc.server(className, methodName, instanceId, ...args)
   rpc.client(deviceId, className, methodName, instanceId, ...args)

2. 快捷示例:
   rpcExamples.basic()    - 基础示例
   rpcExamples.device()   - 设备管理示例
   rpcExamples.task()     - 任务管理示例
   rpcExamples.app()      - 应用管理示例
   rpcExamples.client()   - 客户端调用示例
   rpcExamples.error()    - 错误处理示例
   rpcExamples.batch()    - 批量操作示例
   rpcExamples.all()      - 运行所有示例

3. 命令行调用:
   rpc SDevice_ getDeviceInfo device1
   设备信息 device1
   应用列表
   任务列表 device1

4. 调试工具:
   RPC.getPendingRequestsCount()  - 获取等待中的请求数量
   RPC.clearPendingRequests()     - 清理所有等待中的请求
`); 