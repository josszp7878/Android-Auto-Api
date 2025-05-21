/**
 * 表格页面管理类
 */
class SheetPage {
    constructor(curDeviceID) {
        this.devices = []; // 初始化为空数组
        this.tasks = []; // 初始化为空数组
        this.logs = []; // 初始化日志数据
        this.curDeviceID = curDeviceID;
        this.socket = null;
        this.mainTable = null;
        this.contextMenu = document.getElementById('context-menu');
        this.selectedTaskId = null;
        this.today = new Date().toISOString().split('T')[0]; // 获取当天日期，格式：YYYY-MM-DD
        this.currentTab = "任务"; // 初始化当前页面为"任务"
        
        // 命令输入相关
        this.commandInput = '';
        this.commandHistory = [];
        this.historyIndex = -1;
        this._tempCommand = undefined;
        
        // 分页相关
        this.userPaged = false; // 用户是否手动翻页
        
        // 选择相关
        this.selectedTasks = []; // 选中的任务ID列表
        this.selectedDevices = []; // 选中的设备ID列表
        this.selectedLogs = []; // 选中的日志ID列表
        this.lastConnectedDevice = null; // 最后一次连接的设备ID
        
        // 表格缓存
        this._taskTable = null;
        this._deviceTable = null;
        this._logTable = null;
        
        // 唯一映射表定义（中文标签 -> 数据类型）
        this.tabTypeMap = {
            '任务': 'tasks',
            '设备': 'devices',
            '日志': 'logs'
        };

        // 设备状态定义
        this.deviceStatusMap = {
            'online': {
                label: '在线',
                color: '#23d160',
                icon: 'fas fa-circle',
                formatter: "<span style='color: #23d160'><i class='fas fa-circle'></i> 在线</span>"
            },
            'offline': {
                label: '离线',
                color: '#ff3860',
                icon: 'fas fa-circle',
                formatter: "<span style='color: #ff3860'><i class='fas fa-circle'></i> 离线</span>"
            },
            'login': {
                label: '已登录',
                color: '#3273dc',
                icon: 'fas fa-user',
                formatter: "<span style='color: #3273dc'><i class='fas fa-user'></i> 已登录</span>"
            },
            'logout': {
                label: '已登出',
                color: '#b5b5b5',
                icon: 'fas fa-user-slash',
                formatter: "<span style='color: #b5b5b5'><i class='fas fa-user-slash'></i> 已登出</span>"
            }
        };

        // 日志等级定义
        this.logLevelMap = {
            'i': {
                label: '信息',
                color: '#3273dc',
                icon: 'fas fa-info-circle',
                formatter: "<span style='color: #3273dc'><i class='fas fa-info-circle'></i> 信息</span>"
            },
            'w': {
                label: '警告',
                color: '#ffdd57',
                icon: 'fas fa-exclamation-triangle',
                formatter: "<span style='color: #ffdd57'><i class='fas fa-exclamation-triangle'></i> 警告</span>"
            },
            'e': {
                label: '错误',
                color: '#ff3860',
                icon: 'fas fa-times-circle',
                formatter: "<span style='color: #ff3860'><i class='fas fa-times-circle'></i> 错误</span>"
            },
            'd': {
                label: '调试',
                color: '#b5b5b5',
                icon: 'fas fa-bug',
                formatter: "<span style='color: #b5b5b5'><i class='fas fa-bug'></i> 调试</span>"
            },
            'c': {
                label: '命令',
                color: '#23d160',
                icon: 'fas fa-check-circle',
                formatter: "<span style='color: #23d160'><i class='fas fa-check-circle'></i> 命令</span>"
            }
        };

        // 初始化Socket连接
        this.initSocket();
        
        // 创建表格容器 - 必须在初始化标签页之前
        this.createTableContainers();
        
        // 初始化标签页 - 在创建表格容器后执行
        this.initTabs();
        
        // 初始化表格
        this.initMainTable();
        
        // 初始化上下文菜单
        this.initContextMenu();
        
        // 初始化命令输入区域
        this.initCommandArea();
    }
    
    /**
     * 创建表格容器
     */
    createTableContainers() {
        // 获取原始表格容器
        const originalContainer = document.getElementById('tables-container');
        if (!originalContainer) {
            console.error('未找到表格容器元素 #tables-container');
            return;
        }
        
        // 确保容器高度正确
        originalContainer.style.height = 'calc(100vh - 60px)';
        
        // 创建三个独立的表格容器
        const tableTypes = ['任务', '设备', '日志'];
        tableTypes.forEach(type => {
            const tableContainer = document.createElement('div');
            tableContainer.id = `${type}-table`;
            tableContainer.className = 'table-container';
            
            // 默认只显示任务表格
            if (type !== '任务') {
                tableContainer.style.display = 'none';
            }
            
            originalContainer.appendChild(tableContainer);
        });
    }
    
    /**
     * 任务表格访问器 - 懒加载方式
     */
    get taskTable() {
        if (!this._taskTable) {
            this._taskTable = new Tabulator("#任务-table", {
                layout: "fitColumns",
                pagination: "local",
                paginationSize: 15,
                paginationSizeSelector: [10, 15, 20, 30, 50],
                paginationButtonsVisibility: "auto", // 只有多页时才显示分页按钮
                movableColumns: true,
                resizableRows: true,
                placeholder: "暂无数据",
                height: "calc(100% - 5px)",
                persistence: {
                    sort: true,
                    filter: true
                },
                rowContextMenu: this.showContextMenu.bind(this),
                selectable: true, // 启用多选
                selectableRollingSelection: true, // 支持滚动选择
                selectableRangeMode: "click", // 支持点击和拖动选择
                selectableRowsCheck: () => { return true; }, // 所有行可选
                selectablePersistence: false, // 不持久化选择状态
                selectableRange: true, // 启用范围选择
                selectableCheckbox: true, // 显示复选框
                columns: this.getTaskColumns(),
                data: this.tasks,
                tableBuilt: () => {
                    console.log("任务表格构建完成");
                    // 在表格构建完成后设置默认过滤器
                    this.setDefaultFilters(this._taskTable, "任务");
                    // 加载任务数据
                    this.loadSheetData(this._taskTable, "任务");
                    
                    // 恢复选择状态
                    setTimeout(() => {
                        if (this.selectedTasks.length > 0) {
                            this._taskTable.selectRow(this.selectedTasks);
                        }
                    }, 200);
                    
                    // 监听选择变化事件
                    this._taskTable.on("rowSelectionChanged", (data, rows) => {
                        this.selectedTasks = rows.map(row => row.getData().id);
                        console.log("任务选择更新:", this.selectedTasks);
                    });
                }
            });
        }
        return this._taskTable;
    }
    
    /**
     * 设备表格访问器 - 懒加载方式
     */
    get deviceTable() {
        if (!this._deviceTable) {
            this._deviceTable = new Tabulator("#设备-table", {
                layout: "fitColumns",
                pagination: "local",
                paginationSize: 15,
                paginationSizeSelector: [10, 15, 20, 30, 50],
                paginationButtonsVisibility: "auto", // 只有多页时才显示分页按钮
                movableColumns: true,
                resizableRows: true,
                placeholder: "暂无数据",
                height: "calc(100% - 5px)",
                persistence: {
                    sort: true,
                    filter: true
                },
                selectable: true, // 启用多选
                selectableRollingSelection: true, // 支持滚动选择
                selectableRangeMode: "click", // 支持点击和拖动选择
                selectableRowsCheck: () => { return true; }, // 所有行可选
                selectablePersistence: false, // 不持久化选择状态
                selectableRange: true, // 启用范围选择
                selectableCheckbox: true, // 显示复选框
                columns: this.getDeviceColumns(),
                data: this.prepareDeviceData(),
                tableBuilt: () => {
                    console.log("设备表格构建完成");
                    // 在表格构建完成后设置默认过滤器
                    this.setDefaultFilters(this._deviceTable, "设备");
                    // 加载设备数据
                    this.loadSheetData(this._deviceTable, "设备");
                    
                    // 恢复选择状态
                    setTimeout(() => {
                        if (this.selectedDevices.length > 0) {
                            this._deviceTable.selectRow(this.selectedDevices);
                        } else if (this.lastConnectedDevice) {
                            // 如果没有选中的设备，但有最后连接的设备，则自动选中它
                            this._deviceTable.selectRow(this.lastConnectedDevice);
                        }
                    }, 200);
                    
                    // 监听选择变化事件
                    this._deviceTable.on("rowSelectionChanged", (data, rows) => {
                        this.selectedDevices = rows.map(row => row.getData().id);
                        console.log("设备选择更新:", this.selectedDevices);
                    });
                }
            });
        }
        return this._deviceTable;
    }
    
    /**
     * 日志表格访问器 - 懒加载方式
     */
    get logTable() {
        if (!this._logTable) {
            this._logTable = new Tabulator("#日志-table", {
                layout: "fitColumns",
                pagination: "local",
                paginationSize: 15,
                paginationSizeSelector: [10, 15, 20, 30, 50],
                paginationButtonsVisibility: "auto", // 只有多页时才显示分页按钮
                movableColumns: true,
                resizableRows: true,
                placeholder: "暂无数据",
                height: "calc(100% - 5px)",
                persistence: {
                    sort: true,
                    filter: true
                },
                selectable: true, // 启用多选
                selectableRollingSelection: true, // 支持滚动选择
                selectableRangeMode: "click", // 支持点击和拖动选择
                selectableRowsCheck: () => { return true; }, // 所有行可选
                selectablePersistence: false, // 不持久化选择状态
                selectableRange: true, // 启用范围选择
                selectableCheckbox: true, // 显示复选框
                columns: this.getLogColumns(),
                data: this.logs,
                tableBuilt: () => {
                    console.log("日志表格构建完成");
                    // 在表格构建完成后设置默认过滤器
                    this.setDefaultFilters(this._logTable, "日志");
                    // 加载日志数据
                    this.loadSheetData(this._logTable, "日志");
                    
                    // 添加分页事件监听，记录用户是否手动翻页
                    this._logTable.on("pageLoaded", () => {
                        this.userPaged = true;
                    });
                    
                    // 恢复选择状态
                    setTimeout(() => {
                        if (this.selectedLogs.length > 0) {
                            this._logTable.selectRow(this.selectedLogs);
                        }
                    }, 200);
                    
                    // 监听选择变化事件
                    this._logTable.on("rowSelectionChanged", (data, rows) => {
                        this.selectedLogs = rows.map(row => row.getData().id);
                        console.log("日志选择更新:", this.selectedLogs);
                    });
                }
            });
        }
        return this._logTable;
    }
    
    /**
     * 从表格获取过滤参数
     * @param {Tabulator} table - 表格实例
     * @returns {Object} 过滤参数的对象
     */
    getFilterParams(table) {
        const filterParams = {};
        
        if (table) {
            // 获取所有过滤器
            const filters = table.getHeaderFilters();
            
            // 将过滤器转换为键值对
            filters.forEach(filter => {
                if (filter.value !== undefined && filter.value !== "") {
                    filterParams[filter.field] = filter.value;
                }
            });
        }
        
        return filterParams;
    }

    /**
     * 加载表格数据
     * @param {Tabulator} table - 要加载数据的表格
     * @param {string} type - 表格类型（映射后的数据类型："tasks"、"devices"、"logs"）
     */
    loadSheetData(table, type) {
        if (!table) return;
        
        // 获取过滤参数，只保留日期过滤
        const filterParams = {};
        
        if (table.initialized) {
            const filters = table.getHeaderFilters() || [];
            const dateFilter = filters.find(filter => filter.field === "date");
            if (dateFilter) {
                filterParams.dateFilter = dateFilter;
            }
        }
        
        // 使用映射表反向查找中文标签（仅用于事件发射）
        const tabLabel = Object.keys(this.tabTypeMap).find(
            key => this.tabTypeMap[key] === type
        );
        if (!tabLabel) return;

        switch (type) {
            case this.tabTypeMap['任务']:
                this.socket.emit('B2S_loadTasks', { filters: filterParams });
                break;
            case this.tabTypeMap['设备']:
                this.socket.emit('B2S_loadDevices', { filters: filterParams });
                break;
            case this.tabTypeMap['日志']:
                this.socket.emit('B2S_loadLogs', { filters: {} });
                break;
        }
    }
    
    /**
     * Socket事件监听
     */
    initSocket() {        
        this.socket = io({
            query: {
                device_id: '@Console1'
            }
        });               
        // 监听表格数据更新
        this.socket.on('S2B_sheetUpdate', (data) => { 
            // 统一使用映射表检查类型
            if (!Array.isArray(data.data)) return;
            const targetTab = Object.keys(this.tabTypeMap).find(
                key => this.tabTypeMap[key] === data.type
            );
            if (!targetTab) return;
            if (data.type !== this.tabTypeMap[this.currentTab]) return;

            // 更新对应数据
            switch (data.type) {
                case this.tabTypeMap['任务']:
                    this._updateData(data.data, data.type, this.tasks);
                    break;
                case this.tabTypeMap['设备']:
                    this._updateData(data.data, data.type, this.devices);
                    break;
                case this.tabTypeMap['日志']:
                    this._updateData(data.data, data.type, this.logs);
                    break;
            }
        });
        
        // 设备状态更新事件
        this.socket.on('S2B_DeviceUpdate', (data) => {
            console.log("设备状态更新:", data);
            if (data.status === 'online') {
                this.lastConnectedDevice = data.deviceId;
                
                // 如果没有选中的设备，并且设备表格已经初始化，则自动选中最后连接的设备
                if (this.selectedDevices.length === 0 && this._deviceTable) {
                    setTimeout(() => {
                        this._deviceTable.selectRow(this.lastConnectedDevice);
                    }, 200);
                }
            }
        });
    }
    
    /**
     * 通用数据更新方法
     */
    _updateData(newData, dataType, targetData) {
        // 规整数据，确保符合表格要求
        const sheetData = this.toSheetData(newData, dataType);
        
        // 支持增量更新
        sheetData.forEach(newItem => {
            const existingItemIndex = targetData.findIndex(item => item.id === newItem.id);
            if (existingItemIndex !== -1) {
                targetData[existingItemIndex] = newItem; // 更新现有数据
            } else {
                targetData.push(newItem); // 添加新数据
            }
        });
        
        // 更新当前表格数据
        if (this.mainTable) {
            this.mainTable.setData(targetData);
            
            // 如果是日志表格，且用户没有手动翻页，则滚动到最后一页
            if (this.currentTab === "日志" && !this.userPaged && this.mainTable.getPageMax && this.mainTable.getPageMax() > 1) {
                setTimeout(() => {
                    this.mainTable.setPage(this.mainTable.getPageMax());
                }, 100);
            }
        }
    }
    
    /**
     * 将数据规整为表格所需格式
     * @param {Array} data - 原始数据
     * @param {string} dataType - 数据类型（tasks, devices, logs）
     * @returns {Array} 规整后的数据
     */
    toSheetData(data, dataType) {
        if (!Array.isArray(data)) return [];
        
        // 获取对应表格的列定义
        let columns = [];
        switch (dataType) {
            case "tasks":
                columns = this.getTaskColumns();
                break;
            case "devices":
                columns = this.getDeviceColumns();
                break;
            case "logs":
                columns = this.getLogColumns();
                break;
            default:
                return data; // 未知类型，直接返回原数据
        }
        
        // 提取列字段名
        const fieldNames = columns.map(col => col.field);
        
        // 规整每个数据项
        return data.map(item => {
            // 必须有id字段
            if (!item.id) {
                console.warn('警告: 数据项缺少id字段', item);
                return null;
            }
            
            const result = { id: item.id };
            
            // 只提取列中定义的字段
            fieldNames.forEach(field => {
                if (field === 'id') return; // id已处理
                
                // 如果字段不存在，设置默认值
                if (item[field] === undefined || item[field] === null) {
                    // 根据字段类型设置默认值
                    switch (field) {
                        case 'progress':
                            result[field] = 0;
                            break;
                        case 'status':
                            result[field] = dataType === 'devices' ? 'offline' : 'pending';
                            break;
                        case 'score':
                            result[field] = 0;
                            break;
                        case 'date':
                            result[field] = this.today;
                            break;
                        case 'time':
                            result[field] = new Date().toTimeString().split(' ')[0];
                            break;
                        default:
                            result[field] = '';
                    }
                } else {
                    // 验证字段值的合法性
                    try {
                        // 针对不同类型字段的验证
                        switch (field) {
                            case 'progress':
                                const progress = parseFloat(item[field]);
                                result[field] = isNaN(progress) ? 'ERR' : Math.min(Math.max(progress, 0), 100);
                                break;
                            case 'status':
                                // 验证状态值
                                if (dataType === 'devices') {
                                    const validStatuses = Object.keys(this.deviceStatusMap);
                                    result[field] = validStatuses.includes(item[field]) ? item[field] : 'offline';
                                } else if (dataType === 'tasks') {
                                    result[field] = ['running', 'paused', 'success', 'failed', 'pending'].includes(item[field]) ? 
                                        item[field] : 'pending';
                                } else {
                                    result[field] = item[field];
                                }
                                break;
                            case 'score':
                                const score = parseFloat(item[field]);
                                result[field] = isNaN(score) ? 'ERR' : score;
                                break;
                            case 'level':
                                const validLevels = Object.keys(this.logLevelMap);
                                result[field] = validLevels.includes(item[field]) ? 
                                    item[field] : 'i';
                                break;
                            default:
                                result[field] = item[field];
                        }
                    } catch (e) {
                        console.error(`字段${field}处理出错:`, e);
                        result[field] = 'ERR';
                    }
                }
            });
            
            return result;
        }).filter(item => item !== null); // 过滤掉无效项
    }
    
    /**
     * 准备设备数据
     */
    prepareDeviceData() {
        return this.devices.map(device => {
            // 确保设备状态只能是预定义的值或空字符串
            const validStatuses = Object.keys(this.deviceStatusMap);
            const status = validStatuses.includes(device.status) ? device.status : "";
            
            return {
                id: device.id,
                group: device.group || '',
                status: status,
                currentTask: device.currentTask ? device.currentTask.displayName : '',
                score: device.totalScore || 0
            };
        });
    }
    
    /**
     * 初始化标签页
     */
    initTabs() {
        // 创建标签页容器
        const tabsContainer = document.createElement('div');
        tabsContainer.className = 'table-tabs';
        
        // 创建标签页按钮
        const tabs = ['任务', '设备', '日志'];
        tabs.forEach(tab => {
            const tabButton = document.createElement('button');
            tabButton.textContent = tab;
            tabButton.dataset.tab = tab;
            tabButton.className = 'tab-button';
            
            // 设置当前活动标签样式
            if (tab === this.currentTab) {
                tabButton.classList.add('active');
            }
            
            tabButton.addEventListener('click', () => this.switchTab(tab), {passive: true});
            tabsContainer.appendChild(tabButton);
        });
        
        // 直接将标签页添加到body底部，固定位置
        document.body.appendChild(tabsContainer);
    }
    
    /**
     * 切换标签页
     */
    switchTab(tab) {
        if (tab === this.currentTab) return;
        this.currentTab = tab;
        const tabType = this.tabTypeMap[tab]; // 获取映射后的数据类型
        
        // 更新标签按钮样式
        document.querySelectorAll('.tab-button').forEach(button => {
            button.classList.toggle('active', button.dataset.tab === tab);
        });
        
        // 隐藏所有表格容器，显示当前表格
        document.querySelectorAll('.table-container').forEach(container => {
            container.style.display = 'none';
        });
        const currentContainer = document.getElementById(`${tab}-table`);
        if (currentContainer) currentContainer.style.display = 'block';
        
        // 设置当前主表格
        switch (tab) {
            case "任务":
                this.mainTable = this.taskTable;
                break;
            case "设备":
                this.mainTable = this.deviceTable;
                break;
            case "日志":
                this.mainTable = this.logTable;
                // 切换到日志标签页时重置用户翻页标志
                this.userPaged = false;
                break;
        }
        
        // 刷新数据（传入映射后的数据类型）
        this.loadSheetData(this.mainTable, tabType);
    }
    
    /**
     * 获取任务表格列定义
     */
    getTaskColumns() {
        return [
            {title: "ID", field: "id", visible: false},
            {title: "设备", field: "deviceId", width: 120, headerFilter: "input"},
            {title: "任务名称", field: "taskName", headerFilter: "input"},
            {
                title: "日期", 
                field: "date", 
                width: 130, 
                headerFilter: "input",
                headerFilterPlaceholder: "筛选日期...",
                headerFilterParams: {
                    initial: this.today
                },
                editor: "date", // 使用日期编辑器
                editorParams: {
                    format: "YYYY-MM-DD"
                }
            },
            {title: "分组", field: "group", width: 120, headerFilter: "input"},
            {
                title: "进度", 
                field: "progress", 
                width: 150, 
                formatter: "progress", 
                formatterParams: {
                    min: 0,
                    max: 100,
                    color: ["#ff3860", "#ffdd57", "#23d160"],
                    legend: true
                },
                headerFilter: "number"
            },
            {
                title: "状态", 
                field: "status", 
                width: 120, 
                headerFilter: "list",
                headerFilterParams: {
                    values: {
                        "": "全部",
                        "running": "运行中",
                        "paused": "已暂停",
                        "success": "已完成",
                        "failed": "失败",
                        "pending": "待处理"
                    }
                },
                formatter: "lookup",
                formatterParams: {
                    "running": "<span style='color: #23d160'><i class='fas fa-play'></i> 运行中</span>",
                    "paused": "<span style='color: #ffdd57'><i class='fas fa-pause'></i> 已暂停</span>",
                    "success": "<span style='color: #3273dc'><i class='fas fa-check'></i> 已完成</span>",
                    "failed": "<span style='color: #ff3860'><i class='fas fa-times'></i> 失败</span>",
                    "pending": "<span style='color: #ffbd4a'><i class='fas fa-clock'></i> 待处理</span>"
                }
            },
            {
                title: "开始时间", 
                field: "startTime", 
                width: 160, 
                headerFilter: "input",
                editor: "datetime", // 使用日期时间编辑器
                editorParams: {
                    format: "YYYY-MM-DD HH:mm:ss"
                }
            },
            {
                title: "完成时间", 
                field: "endTime", 
                width: 160, 
                headerFilter: "input",
                editor: "datetime", // 使用日期时间编辑器
                editorParams: {
                    format: "YYYY-MM-DD HH:mm:ss"
                }
            },
            {title: "得分", field: "score", width: 100, headerFilter: "number"},
        ];
    }
    
    /**
     * 获取设备表格列定义
     */
    getDeviceColumns() {
        // 构建状态过滤器选项和格式化参数
        const statusFilterValues = { "": "全部" };
        const statusFormatterParams = { "": "<span style='color: #b5b5b5'><i class='fas fa-question'></i> 未知</span>" };
        
        // 从设备状态映射中获取值
        Object.keys(this.deviceStatusMap).forEach(status => {
            const statusInfo = this.deviceStatusMap[status];
            statusFilterValues[status] = statusInfo.label;
            statusFormatterParams[status] = statusInfo.formatter;
        });
        
        return [
            {title: "ID", field: "id", headerFilter: "input"},
            {title: "设备ID", field: "deviceId", width: 120, headerFilter: "input"},
            {title: "分组", field: "group", width: 120, headerFilter: "input"},
            {
                title: "状态", 
                field: "status", 
                width: 120, 
                headerFilter: "list",
                headerFilterParams: {
                    values: statusFilterValues
                },
                formatter: "lookup",
                formatterParams: statusFormatterParams
            },
            {title: "当前任务", field: "currentTask", width: 200, headerFilter: "input"},
            {title: "累计得分", field: "score", width: 120, headerFilter: "number"}
        ];
    }

    /**
     * 获取日志表格列定义
     */
    getLogColumns() {
        // 构建等级过滤器选项和格式化参数
        const levelFilterValues = { "": "全部" };
        const levelFormatterParams = {};
        
        // 从日志等级映射中获取值
        Object.keys(this.logLevelMap).forEach(level => {
            const levelInfo = this.logLevelMap[level];
            levelFilterValues[level] = levelInfo.label;
            levelFormatterParams[level] = levelInfo.formatter;
        });

        return [
            {title: "ID", field: "id", visible: false},
            {title: "日期", field: "date", width: 130, 
                headerFilter: "input",
                editor: "date", // 使用日期编辑器
                editorParams: {
                    format: "YYYY-MM-DD"
                }
            },
            {title: "时间", field: "time", width: 130, 
                headerFilter: "input",
                editor: "time", // 使用时间编辑器
                editorParams: {
                    format: "HH:mm:ss"
                }
            },
            {title: "标签", field: "tag", width: 120, 
                headerFilter: "list",
                headerFilterParams: {
                    values: {
                        "": "全部",
                        "CMD": "命令",
                        "SCMD": "服务器命令",
                        "@": "服务器"
                    }
                }
            },
            {title: "等级", field: "level", width: 100, 
                headerFilter: "list",
                headerFilterParams: {
                    values: levelFilterValues
                },
                formatter: function(cell, formatterParams, onRendered) {
                    const value = cell.getValue();
                    if (!value) return "";
                    
                    // 使用预定义的格式化参数
                    return levelFormatterParams[value] || value;
                }
            },
            {title: "发送者", field: "sender", width: 150, headerFilter: "input"},
            {title: "内容", field: "message", headerFilter: "input"},
        ];
    }
    
    /**
     * 初始化主表格
     */
    initMainTable() {
        // 创建所有表格实例（懒加载方式）
        this.taskTable;    // 创建任务表格
        this.deviceTable;  // 创建设备表格
        this.logTable;     // 创建日志表格
        
        // 设置当前主表格
        switch (this.currentTab) {
            case "任务":
                this.mainTable = this._taskTable;
                break;
            case "设备":
                this.mainTable = this._deviceTable;
                break;
            case "日志":
                this.mainTable = this._logTable;
                break;
        }
    }
    
    /**
     * 设置表格默认过滤条件
     * @param {Tabulator} table - 表格实例
     * @param {string} type - 表格类型："任务", "设备", "日志"
     */
    setDefaultFilters(table, type) {
        if (!table || !table.initialized) return;
        
        // 清除现有过滤器
        table.clearHeaderFilter();
        
        // 根据表格类型设置默认过滤器
        switch (type) {
            case "任务":
                // 为任务表设置当天日期过滤
                table.setHeaderFilterValue("date", this.today);
                break;
            case "日志":
                // 为日志表设置当天日期过滤
                table.setHeaderFilterValue("date", this.today);
                break;
            case "设备":
                // 设备表不设置过滤
                break;
        }
    }
    
    /**
     * 初始化上下文菜单
     */
    initContextMenu() {
        // 当点击其他地方时关闭菜单
        document.addEventListener('click', (e) => {
            if (!this.contextMenu.contains(e.target)) {
                this.contextMenu.style.display = 'none';
            }
        }, { passive: true });
        
        // 给菜单中的每个项目添加点击事件
        this.contextMenu.querySelectorAll('a[data-action]').forEach(item => {
            item.addEventListener('click', (e) => {
                const action = e.currentTarget.dataset.action;
                if (this.selectedTaskId) {
                    task = this.tasks.find(task => task.getData().id === this.selectedTaskId);
                    if (task) {
                        this.handleTaskAction(action, task.getData().taskName);
                    }
                }
                this.contextMenu.style.display = 'none';
            }, { passive: true });
        });
    }
    
    /**
     * 显示上下文菜单
     */
    showContextMenu(e, row) {
        if (this.currentTab !== "任务") return false; // 只在任务表格中启用上下文菜单
        
        this.selectedTaskId = row.getData().id;
        
        // 设置菜单位置
        const menu = this.contextMenu;
        const x = e.pageX;
        const y = e.pageY;
        const windowWidth = window.innerWidth;
        const windowHeight = window.innerHeight;
        const menuWidth = menu.offsetWidth;
        const menuHeight = menu.offsetHeight;
        
        // 确保菜单不会超出窗口边界
        const left = (x + menuWidth > windowWidth) ? (windowWidth - menuWidth) : x;
        const top = (y + menuHeight > windowHeight) ? (windowHeight - menuHeight) : y;
        
        // 应用计算好的位置并显示菜单
        menu.style.left = `${left}px`;
        menu.style.top = `${top}px`;
        menu.style.display = 'block';
        
        // 阻止默认右键菜单
        return false;
    }
    
    /**
     * 处理任务操作
     */
    handleTaskAction(action, taskName) {
        console.log(`处理任务操作: ${action}, 任务名称: ${taskName}`);
        let cmd = ''
        switch (action) {
            case 'execute':
                cmd = 'run'
                break;
            case 'pause':
                cmd = 'stop'
                break;
            case 'cancel':
                cmd = 'cancel'
                break;
            default:
                console.warn(`未知的任务操作: ${action}`);
                return
        }
        this.socket.emit('2S_cmd', { 
            cmd: cmd, 
            taskId: taskName,
            deviceId: this.curDeviceID
        });
    }
    
    /**
     * 初始化命令输入区域
     */
    initCommandArea() {
        // 获取命令输入元素
        const commandInput = document.getElementById('commandInput');
        const sendButton = document.querySelector('.command-area button');
        
        if (commandInput && sendButton) {
            // 设置命令输入事件
            commandInput.addEventListener('keydown', (e) => this.handleKeydown(e));
            commandInput.addEventListener('keyup', (e) => {
                if (e.key === 'Enter') {
                    this.sendCommand();
                }
            });
            
            // 设置发送按钮事件
            sendButton.addEventListener('click', () => this.sendCommand());
        }
    }
    
    /**
     * 处理按键事件，主要用于历史命令导航
     */
    handleKeydown(e) {
        const history = this.commandHistory;
        const historyLength = history.length;
        if (historyLength === 0) {
            return;
        }
        
        // 处理方向键导航
        if (e.key === 'ArrowUp' || e.key === 'ArrowDown') {
            // 暂存未发送的命令
            const commandInput = document.getElementById('commandInput');
            if (commandInput) {
                if (this._tempCommand === undefined) {
                    this._tempCommand = commandInput.value;
                }
                
                // 计算新索引
                let newIndex = this.historyIndex;
                if (e.key === 'ArrowUp') {
                    // 向上键获取更早的命令（索引增加）
                    newIndex = Math.min(newIndex + 1, historyLength - 1);
                } else {
                    // 向下键获取更新的命令（索引减少）
                    newIndex = Math.max(newIndex - 1, -1);
                }
                
                // 更新命令输入
                if (newIndex >= 0) {
                    commandInput.value = history[newIndex];
                } else {
                    commandInput.value = this._tempCommand || '';
                }
                
                this.historyIndex = newIndex;
                e.preventDefault();
            }
        }
    }
    
    /**
     * 发送命令
     */
    sendCommand() {
        const commandInput = document.getElementById('commandInput');
        if (!commandInput || !commandInput.value.trim()) return;
        
        const command = commandInput.value.trim();
        console.log('发送命令:', command);
        
        // 添加到历史记录
        this.addCommandToHistory(command);
        
        // 确定目标设备ID列表
        let deviceIds = this.selectedDevices.length > 0 
            ? this.selectedDevices 
            : (this.lastConnectedDevice ? [this.lastConnectedDevice] : [this.curDeviceID]);
        
        console.log("命令目标设备:", deviceIds);
        
        // 发送命令到服务器
        this.socket.emit('2S_Cmd', {
            device_ids: deviceIds,
            command: command,
            params: {}
        });
        
        // 清空输入框
        commandInput.value = '';
        this.historyIndex = -1;
        this._tempCommand = undefined;
    }
    
    /**
     * 添加命令到历史记录
     */
    addCommandToHistory(command) {
        if (!command) return;
        
        // 如果命令已存在于历史记录中，先删除它
        const index = this.commandHistory.indexOf(command);
        if (index !== -1) {
            this.commandHistory.splice(index, 1);
        }
        
        // 将命令添加到历史记录开头
        this.commandHistory.unshift(command);
        
        // 限制历史记录长度
        if (this.commandHistory.length > 50) {
            this.commandHistory.pop();
        }
    }
} 