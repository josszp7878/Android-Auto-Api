/**
 * 前端浏览器命令集 (Browser Commands)
 * 类似于Python版本的SCmds.py
 */

class BCmds {
    /**
     * 注册所有前端命令
     */
    static registerCommands() {
        console.log('开始注册前端命令...');
        
        // 设置模块优先级
        CmdMgr.setModulePriority('BCmds', 10);
        
        // 帮助命令
        regCmd("#帮助 (?<command>.+)?", 'BCmds')(
            function help({ command }) {
                /**
                 * 功能：显示命令帮助信息
                 * 指令名：help
                 * 中文名：帮助
                 * 参数：
                 *   command - 要查询的命令名称，可选
                 * 示例：帮助
                 * 示例：帮助 刷新
                 */
                const commandName = command ? command.trim() : null;
                const helpText = CmdMgr.getHelp(commandName);
                
                if (!commandName) {
                    // 显示前端命令使用说明
                    return `前端命令系统使用说明：

格式：命令名 [参数]

可用命令：
- 帮助 [命令名] - 显示帮助信息
- 清屏 - 清空控制台
- 刷新 [目标] - 刷新表格数据  
- 切换 [标签页] - 切换标签页
- 选择 [ID列表] - 选择目标
- 清空选择 - 清空当前选择
- 时间 - 显示当前时间
- 状态 - 显示页面状态
- 统计 - 显示详细统计
- 搜索 [关键词] - 搜索表格内容
- 导出 [格式] - 导出表格数据
- 修改名称 [设备] [新名称] - 修改设备名称

输入 "帮助 命令名" 查看具体命令的详细说明。
如果命令在前端未找到，将自动发送到服务端处理。`;
                }
                
                return helpText;
            }
        );
        
        // 清屏命令
        regCmd("#清屏", 'BCmds')(
            function clear() {
                /**
                 * 功能：清空浏览器控制台
                 * 指令名：clear
                 * 中文名：清屏
                 * 参数：无
                 * 示例：清屏
                 * 示例：clear
                 */
                console.clear();
                return "控制台已清空";
            }
        );
        
        // 刷新命令
        regCmd("#刷新 (?<target>\\S+)?", 'BCmds')(
            function refresh({ target, sheetPage }) {
                /**
                 * 功能：刷新表格数据
                 * 指令名：refresh
                 * 中文名：刷新
                 * 参数：
                 *   target - 刷新目标，可选值：任务|设备|日志|tasks|devices|logs
                 * 示例：刷新
                 * 示例：刷新 设备
                 * 示例：refresh tasks
                 */
                const tabType = sheetPage.curTabType;
                
                if (target) {
                    // 指定目标刷新
                    const targetMap = {
                        '任务': 'tasks',
                        'tasks': 'tasks',
                        'task': 'tasks',
                        '设备': 'devices', 
                        'devices': 'devices',
                        'device': 'devices',
                        '日志': 'logs',
                        'logs': 'logs',
                        'log': 'logs'
                    };
                    
                    const targetType = targetMap[target.toLowerCase()];
                    if (targetType === 'tasks') {
                        sheetPage._loadDatas(sheetPage.taskTable, true);
                        return "任务表格已刷新";
                    } else if (targetType === 'devices') {
                        sheetPage._loadDatas(sheetPage.deviceTable, true);
                        return "设备表格已刷新";
                    } else if (targetType === 'logs') {
                        sheetPage._loadDatas(sheetPage.logTable, true);
                        return "日志表格已刷新";
                    } else {
                        return `无效的刷新目标: ${target}。可用目标: 任务、设备、日志`;
                    }
                } else {
                    // 刷新当前表格
                    const currentTable = sheetPage.mainTable;
                    if (currentTable) {
                        sheetPage._loadDatas(currentTable, true);
                        return `${sheetPage.currentTabName}表格已刷新`;
                    } else {
                        return "没有可刷新的表格";
                    }
                }
            }
        );
        
        // 切换标签页命令
        regCmd("#切换 (?<tabName>\\S+)", 'BCmds')(
            function switchTab({ tabName, sheetPage }) {
                /**
                 * 功能：切换标签页
                 * 指令名：switch
                 * 中文名：切换
                 * 参数：
                 *   tabName - 标签页名称，可选值：任务|设备|日志|tasks|devices|logs
                 * 示例：切换 设备
                 * 示例：switch logs
                 */
                const tabMap = {
                    '任务': '任务',
                    'tasks': '任务',
                    'task': '任务',
                    '设备': '设备',
                    'devices': '设备',
                    'device': '设备',
                    '日志': '日志',
                    'logs': '日志',
                    'log': '日志'
                };
                
                const targetTab = tabMap[tabName.toLowerCase()];
                if (targetTab) {
                    sheetPage.switchTab(targetTab);
                    return `已切换到${targetTab}标签页`;
                } else {
                    return `无效的标签页名称: ${tabName}。可用标签页: 任务、设备、日志`;
                }
            }
        );
        
        // 选择目标命令
        regCmd("#选择 (?<targetIds>.+)", 'BCmds')(
            function selectTarget({ targetIds, sheetPage }) {
                /**
                 * 功能：选择表格目标
                 * 指令名：select
                 * 中文名：选择
                 * 参数：
                 *   targetIds - 目标ID列表，用逗号或空格分隔
                 * 示例：选择 device001,device002
                 * 示例：select task001 task002
                 */
                const tabType = sheetPage.curTabType;
                const targets = sheetPage.targets[tabType];
                
                // 解析目标ID列表
                const ids = targetIds.split(/[,\s]+/).map(id => id.trim()).filter(id => id);
                
                if (ids.length === 0) {
                    return "请提供有效的目标ID";
                }
                
                // 清空现有选择
                targets.length = 0;
                
                // 添加新选择
                targets.push(...ids);
                
                // 更新表格显示
                sheetPage.updateTarget();
                
                return `已选择${ids.length}个目标: ${ids.join(', ')}`;
            }
        );
        
        // 清空选择命令
        regCmd("#清空选择", 'BCmds')(
            function clearSelect({ sheetPage }) {
                /**
                 * 功能：清空当前标签页的目标选择
                 * 指令名：clearSelect
                 * 中文名：清空选择
                 * 参数：无
                 * 示例：清空选择
                 */
                const tabType = sheetPage.curTabType;
                const targets = sheetPage.targets[tabType];
                const count = targets.length;
                
                // 清空选择
                targets.length = 0;
                
                // 更新表格显示
                sheetPage.updateTarget();
                
                return `已清空${count}个目标选择`;
            }
        );
        
        // 时间命令
        regCmd("#时间", 'BCmds')(
            function time() {
                /**
                 * 功能：显示当前时间
                 * 指令名：time
                 * 中文名：时间
                 * 参数：无
                 * 示例：时间
                 */
                const now = new Date();
                return {
                    timestamp: now.toLocaleString('zh-CN'),
                    iso: now.toISOString(),
                    unix: Math.floor(now.getTime() / 1000)
                };
            }
        );
        
        // 状态命令
        regCmd("#状态", 'BCmds')(
            function status({ sheetPage }) {
                /**
                 * 功能：显示页面状态信息
                 * 指令名：status
                 * 中文名：状态
                 * 参数：无
                 * 示例：状态
                 */
                const tabType = sheetPage.curTabType;
                const targets = sheetPage.targets[tabType];
                
                return {
                    currentTab: sheetPage.currentTabName,
                    currentTabType: tabType,
                    targetCount: targets.length,
                    selectedTargets: targets,
                    totalDevices: sheetPage.devices.length,
                    totalTasks: sheetPage.tasks.length,
                    totalLogs: sheetPage.logs.length,
                    onlineDevices: sheetPage.devices.filter(d => d.state === 'online').length,
                    runningTasks: sheetPage.tasks.filter(t => t.state === 'running').length
                };
            }
        );
        
        // 统计命令
        regCmd("#统计", 'BCmds')(
            function stats({ sheetPage }) {
                /**
                 * 功能：显示详细统计信息
                 * 指令名：stats
                 * 中文名：统计
                 * 参数：无
                 * 示例：统计
                 */
                // 设备状态统计
                const deviceStats = {};
                sheetPage.devices.forEach(device => {
                    const state = device.state || 'unknown';
                    deviceStats[state] = (deviceStats[state] || 0) + 1;
                });
                
                // 任务状态统计
                const taskStats = {};
                sheetPage.tasks.forEach(task => {
                    const state = task.state || 'unknown';
                    taskStats[state] = (taskStats[state] || 0) + 1;
                });
                
                return {
                    devices: {
                        total: sheetPage.devices.length,
                        byState: deviceStats
                    },
                    tasks: {
                        total: sheetPage.tasks.length,
                        byState: taskStats
                    },
                    logs: {
                        total: sheetPage.logs.length
                    },
                    timestamp: new Date().toLocaleString('zh-CN')
                };
            }
        );
        
        // 搜索命令
        regCmd("#搜索 (?<keyword>.+)", 'BCmds')(
            function search({ keyword, sheetPage }) {
                /**
                 * 功能：在当前表格中搜索关键词
                 * 指令名：search
                 * 中文名：搜索
                 * 参数：
                 *   keyword - 搜索关键词
                 * 示例：搜索 device001
                 * 示例：search error
                 */
                const currentTable = sheetPage.mainTable;
                if (!currentTable) {
                    return "没有可搜索的表格";
                }
                
                // 获取表格数据
                const data = currentTable.getData();
                const results = [];
                
                // 搜索匹配的行
                data.forEach((row, index) => {
                    const rowText = JSON.stringify(row).toLowerCase();
                    if (rowText.includes(keyword.toLowerCase())) {
                        results.push({
                            index: index + 1,
                            data: row
                        });
                    }
                });
                
                if (results.length > 0) {
                    return `在${sheetPage.currentTabName}表格中找到${results.length}条匹配记录`;
                } else {
                    return `在${sheetPage.currentTabName}表格中未找到包含"${keyword}"的记录`;
                }
            }
        );
        
        // 导出命令
        regCmd("#导出 (?<format>\\S+)?", 'BCmds')(
            function exportData({ format, sheetPage }) {
                /**
                 * 功能：导出当前表格数据
                 * 指令名：export
                 * 中文名：导出
                 * 参数：
                 *   format - 导出格式，可选值：csv|json，默认csv
                 * 示例：导出
                 * 示例：导出 json
                 */
                const currentTable = sheetPage.mainTable;
                if (!currentTable) {
                    return "没有可导出的表格";
                }
                
                const exportFormat = format || 'csv';
                const tabName = sheetPage.currentTabName;
                
                try {
                    if (exportFormat.toLowerCase() === 'json') {
                        currentTable.download("json", `${tabName}_${new Date().toISOString().split('T')[0]}.json`);
                    } else {
                        currentTable.download("csv", `${tabName}_${new Date().toISOString().split('T')[0]}.csv`);
                    }
                    return `${tabName}表格数据已导出为${exportFormat.toUpperCase()}格式`;
                } catch (e) {
                    return `导出失败: ${e.message}`;
                }
            }
        );
        
        // 修改设备名命令
        regCmd("#命名|mm (?<deviceParam>\\S+) (?<newName>.+)", 'BCmds')(
            function name({ deviceParam, newName, sheetPage }) {
                /**
                 * 功能：修改设备名称
                 * 指令名：name
                 * 中文名：修改名称
                 * 参数：
                 *   deviceParam - 设备标识，可以是设备ID、设备名或"."(当前选中的设备)
                 *   newName - 新的设备名称
                 * 示例：修改名称 device001 新设备名
                 * 示例：name . 测试设备
                 * 示例：修改名称 测试设备1 新名称
                 */
                
                if (!deviceParam || !newName) {
                    return "参数不完整，请提供设备标识和新名称";
                }
                
                newName = newName.trim();
                if (!newName) {
                    return "新名称不能为空";
                }
                
                let targetDevices = [];
                
                if (deviceParam === '.') {
                    // 当前选中的设备
                    const selectedDeviceIds = sheetPage.targets[sheetPage.DataType.DEVICES];
                    if (selectedDeviceIds.length === 0) {
                        return "没有选中任何设备";
                    }
                    
                    // 根据ID查找设备对象
                    targetDevices = selectedDeviceIds.map(id => 
                        sheetPage.devices.find(d => d.id === id)
                    ).filter(d => d);
                    
                    if (targetDevices.length === 0) {
                        return "选中的设备未找到";
                    }
                } else {
                    // 如果deviceParam是数字，则认为是ID
                    if(!isNaN(deviceParam)) {
                        deviceParam = parseInt(deviceParam);
                    }
                    // 单个设备 - 可能是ID或名称
                    let device = sheetPage.devices.find(d => 
                        d.id === deviceParam || d.name === deviceParam
                    );
                    
                    if (!device) {
                        return `设备未找到: ${deviceParam}`;
                    }
                    
                    targetDevices = [device];
                }
                
                // 执行名称修改
                let results = [];
                
                targetDevices.forEach((device, index) => {
                    let finalName;
                    if (targetDevices.length > 1) {
                        // 多个设备时添加序号
                        finalName = `${newName}${index + 1}`;
                    } else {
                        // 单个设备直接使用新名称
                        finalName = newName;
                    }
                    
                    // 更新本地数据
                    device.name = finalName;
                    
                    // 发送到服务端更新
                    const data = {
                        'target': device.id,
                        'type': 'devices', 
                        'params': { 'name': finalName }
                    };
                    sheetPage.socketer.emit('B2S_setProp', data);
                    
                    results.push(`设备 ${device.id} 名称已修改为: ${finalName}`);
                });
                
                // 刷新设备表格显示
                if (sheetPage._deviceTable) {
                    sheetPage._deviceTable.replaceData(sheetPage.devices);
                }
                
                return results.join('\n');
            }
        );
        
        console.log('前端命令注册完成');
    }
    
    /**
     * 模块加载时调用
     */
    static onLoad() {
        BCmds.registerCommands();
        return true;
    }
}

// 导出
if (typeof module !== 'undefined' && module.exports) {
    module.exports = BCmds;
} else {
    window.BCmds = BCmds;
} 