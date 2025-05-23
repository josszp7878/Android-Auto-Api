/**
 * 表格页面管理类
 */
class SheetPage {
    constructor(curDeviceID) {
        // 数据类型枚举定义
        this.DataType = {
            TASKS: 'tasks',
            DEVICES: 'devices',
            LOGS: 'logs'
        };

        // 标签页映射表（中文标签 -> 数据类型）
        this.tabTypeMap = {
            '任务': this.DataType.TASKS,
            '设备': this.DataType.DEVICES,
            '日志': this.DataType.LOGS
        };

        this.devices = []; // 初始化为空数组
        this.tasks = []; // 初始化为空数组
        this.logs = []; // 初始化日志数据
        this.curDeviceID = curDeviceID;
        this.socket = null;
        this.mainTable = null;
        this.contextMenu = document.getElementById('context-menu');
        
        // 如果页面中不存在上下文菜单元素，则创建一个
        if (!this.contextMenu) {
            this.contextMenu = document.createElement('div');
            this.contextMenu.id = 'context-menu';
            this.contextMenu.className = 'context-menu';
            document.body.appendChild(this.contextMenu);
            
            // 添加基本样式
            this.contextMenu.style.position = 'absolute';
            this.contextMenu.style.display = 'none';
            this.contextMenu.style.zIndex = '1000';
            this.contextMenu.style.background = 'white';
            this.contextMenu.style.border = '1px solid #ccc';
            this.contextMenu.style.borderRadius = '4px';
            this.contextMenu.style.boxShadow = '0 2px 5px rgba(0,0,0,0.3)';
            this.contextMenu.style.padding = '5px 0';
            this.contextMenu.style.minWidth = '150px';
        }
        
        this.selectedTaskId = null;
        this.today = new Date().toISOString().split('T')[0]; // 获取当天日期，格式：YYYY-MM-DD
        this.currentTab = null;
        
        // 目标设备列表 - 用于命令发送
        this.targetDevices = [];
        
        // 右键菜单配置
        this.menuConfig = {
            '任务': [
                {
                    label: "执行",
                    action: (e, row) => {
                        const data = row.getData();
                        this.handleTaskAction('execute', data.taskName);
                    },
                    disabled: (row) => row.getData().status !== 'pending'
                },
                {
                    label: "暂停",
                    action: (e, row) => {
                        const data = row.getData();
                        this.handleTaskAction('pause', data.taskName);
                    },
                    disabled: (row) => row.getData().status !== 'running'
                },
                {
                    label: "取消",
                    action: (e, row) => {
                        const data = row.getData();
                        this.handleTaskAction('cancel', data.taskName);
                    },
                    disabled: (row) => !['running', 'paused'].includes(row.getData().status)
                }
            ],
            '设备': [
                {
                    label: "选择/取消目标 (CSpace)",
                    action: (e, row) => {
                        console.log("选择/取消目标 (CSpace)");
                        if (!row) return;
                        let selectedRows = [];
                        try {
                            selectedRows = row.getTable().getSelectedRows();
                            if (selectedRows.length === 0) {
                                selectedRows = [row];
                            }
                        } catch (e) {
                            console.warn("获取选中行出错:", e);
                            if (row) selectedRows = [row];
                        }
                        if (selectedRows.length === 0) {
                            console.warn("没有可操作的行");
                            return;
                        }
                        const deviceIds = selectedRows.map(r => r.getData().deviceId);
                        this.toggleDeviceTarget(deviceIds);
                    }
                },
                {
                    label: "连接",
                    action: (e, row) => {
                        const data = row.getData();
                        this.handleDeviceAction('connect', data.deviceId);
                    },
                    disabled: (row) => row.getData().status !== 'offline'
                },
                {
                    label: "断开",
                    action: (e, row) => {
                        const data = row.getData();
                        this.handleDeviceAction('disconnect', data.deviceId);
                    },
                    disabled: (row) => row.getData().status !== 'online'
                },
                {
                    label: "重启",
                    action: (e, row) => {
                        const data = row.getData();
                        this.handleDeviceAction('restart', data.deviceId);
                    },
                    disabled: (row) => row.getData().status !== 'online'
                }
            ],
            '日志': [
                {
                    label: "复制",
                    action: (e, row) => {
                        this.handleLogAction('copy', row.getData());
                    }
                },
                {
                    label: "导出",
                    action: (e, row) => {
                        this.handleLogAction('export', row.getData());
                    }
                }
            ]
        };
        
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
        this.initTable();
        
        // 初始化上下文菜单
        this.initContextMenu();
        
        // 初始化命令输入区域
        this.initCommandArea();

        //设置当前标签页
        this.switchTab("日志");
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
                paginationButtonsVisibility: "auto",
                paginationButtonCount: 3,
                paginationPosition: "bottom",
                movableColumns: false,
                resizableRows: true,
                placeholder: "暂无数据",
                height: "calc(100% - 5px)",
                persistence: {
                    sort: true,
                    filter: true
                },
                rowContextMenu: this.menuConfig['任务'],
                selectable: true,
                selectableRollingSelection: true,
                selectableRangeMode: "click",
                selectableRowsCheck: () => { return true; },
                selectablePersistence: true,
                selectableRange: true,
                selectableCheckbox: true,
                columns: this.getTaskColumns(),
                data: this.tasks,
                headerFilterLiveFilter: false
            });            
            this._taskTable.dataType = this.DataType.TASKS;
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
                paginationButtonsVisibility: "auto",
                paginationPosition: "bottom",
                movableColumns: false,
                resizableRows: true,
                placeholder: "暂无数据",
                height: "calc(100% - 5px)",
                persistence: {
                    sort: true,
                    filter: true
                },
                rowContextMenu: this.menuConfig['设备'],
                selectable: true,
                selectableRows: true,
                selectableRowsRangeMode:"click",
                selectablePersistence: true,
                selectableRange:true,
                selectableRangeColumns:true,
                selectableRangeRows:true,
                columns: this.getDeviceColumns(),
                data: this.prepareDeviceData(),
                headerFilterLiveFilter: false
            });
            this._deviceTable.dataType = this.DataType.DEVICES;
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
                paginationButtonsVisibility: "auto",
                paginationPosition: "bottom",
                movableColumns: false,
                resizableRows: true,
                placeholder: "暂无数据",
                height: "calc(100% - 5px)",
                persistence: {
                    sort: true,
                    filter: true
                },
                rowContextMenu: this.menuConfig['日志'],
                selectable: true,
                selectableRollingSelection: true,
                selectableRangeMode: "click",
                selectableRowsCheck: () => { return true; },
                selectablePersistence: true,
                selectableRange: true,
                selectableCheckbox: true,
                columns: this.getLogColumns(),
                data: this.logs,
                headerFilterLiveFilter: false,
                tableBuilt: () => {
                    this._logTable.on("pageLoaded", () => {
                        this.userPaged = true;
                    });
                }
            });
            this._logTable.dataType = this.DataType.LOGS;
        }
        return this._logTable;
    }
    
    /**
     * 加载表格数据
     * @param {Tabulator} table - 要加载数据的表格
     */
    _loadDatas(table) {
        if (!table || !table.initialized) return;

        const filters = table.getHeaderFilters() || [];
        const dateFilter = filters.find(filter => filter.field === 'date');
        let currentDate = dateFilter ? dateFilter.value : null;
        if (currentDate === null) {
            // 设置当前的日期过滤为今天
            currentDate = this.today;
            table.setHeaderFilterValue("date", this.today);
        }

        // 如果 lastDateFilter 为 undefined，表示表格未初始化或未切换到此标签页，直接跳过
        if (table.lastDateFilter === undefined) {
            console.log("表格未初始化或未切换到此标签页，跳过数据加载");
            return;
        }

        // 首次加载（lastDateFilter 为 null）或过滤条件变化时触发
        if (table.lastDateFilter === null || currentDate !== table.lastDateFilter) {
            table.lastDateFilter = currentDate;
            console.log("日期过滤条件变化, 获取新的数据", currentDate);

            const filterParams = {};
            if (currentDate) filterParams.date = currentDate;

            const type = table.dataType;
            const tabLabel = Object.keys(this.tabTypeMap).find(
                key => this.tabTypeMap[key] === type
            );
            if (!tabLabel) return;

            console.log(`加载${tabLabel}数据，过滤参数:`, filterParams);
            switch (type) {
                case this.DataType.TASKS:
                    this.socket.emit('B2S_loadTasks', { filters: filterParams });
                    break;
                case this.DataType.DEVICES:
                    this.socket.emit('B2S_loadDevices', { filters: filterParams });
                    break;
                case this.DataType.LOGS:
                    this.socket.emit('B2S_loadLogs', { filters: filterParams });
                    break;
            }
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
                case this.DataType.TASKS:
                    this._updateData(data.data, data.type, this.tasks);
                    break;
                case this.DataType.DEVICES:
                    this._updateData(data.data, data.type, this.devices);
                    break;
                case this.DataType.LOGS:
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
        try {
            // 规整数据，确保符合表格要求
            const sheetData = this.toSheetData(newData, dataType);
            // console.log("sheetData类型:", Array.isArray(sheetData) ? "Array" : typeof sheetData);
            // console.log("sheetData内容:", JSON.stringify(sheetData));

            if (!Array.isArray(sheetData) || sheetData.length === 0) {
                console.warn("无效的sheetData:", sheetData);
                return;
            }

            // 支持增量更新
            sheetData.forEach(newItem => {
                // console.log("newItem：", newItem);
                const existingItemIndex = targetData.findIndex(item => item.id === newItem.id);
                if (existingItemIndex !== -1) {
                    targetData[existingItemIndex] = newItem;
                } else {
                    targetData.push(newItem);
                }
            });

            // 更新当前表格数据
            if (this.mainTable) {
                this.mainTable.setData(targetData);
                // console.log("表格数据已更新，当前行数:", this.mainTable.getDataCount());
            }
        } catch (error) {
            console.error("_updateData出错:", error);
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
            case this.DataType.TASKS:
                columns = this.getTaskColumns();
                break;
            case this.DataType.DEVICES:
                columns = this.getDeviceColumns();
                break;
            case this.DataType.LOGS:
                columns = this.getLogColumns();
                break;
            default:
                return data; // 未知类型，直接返回原数据
        }
        
        const fieldNames = columns.map(col => col.field);
        
        return data.map(item => {
            // 必须包含所有必填字段
            const requiredFields = {
                [this.DataType.TASKS]: ['date', 'taskName', 'deviceId']
            }[dataType] || [];
            
            // 检查必填字段,并将缺少的字段打印出来     
            for (const f of requiredFields) {
                if (!item[f]) {
                    console.error('数据项缺少必填字段:', { 
                        id: item.id, 
                        missing: f,
                        rawData: item 
                    });
                }
            }

            const result = { id: item.id };            
            fieldNames.forEach(field => {
                if (field === 'id') return;
                
                if (item[field] === undefined || item[field] === null) {
                    switch (field) {
                        case 'date':  // 移除默认日期设置
                            console.error('数据项缺少date字段:', item);
                            result[field] = 'INVALID_DATE';
                            break;
                        // 其他字段保持原有默认值逻辑...
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
                                if (dataType === this.DataType.DEVICES) {
                                    const validStatuses = Object.keys(this.deviceStatusMap);
                                    result[field] = validStatuses.includes(item[field]) ? item[field] : 'offline';
                                } else if (dataType === this.DataType.TASKS) {
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
        }).filter(item => {
            // 过滤掉无效日期
            return item !== null && item.date !== 'INVALID_DATE';
        });
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
                deviceId: device.deviceId,
                group: device.group || '',
                status: status,
                currentTask: device.currentTask ? device.currentTask.displayName : '',
                score: device.totalScore || 0,
                isTarget: this.targetDevices.includes(device.deviceId) // 使用deviceId而不是id
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
                this.mainTable = this._taskTable;
                break;
            case "设备":
                this.mainTable = this._deviceTable;
                break;
            case "日志":
                this.mainTable = this._logTable;
                // 切换到日志标签页时重置用户翻页标志
                this.userPaged = false;
                break;
        }
        // 更新命令输入框的占位文本
        this.updateCommandInputPlaceholder();
        // 显式初始化 lastDateFilter
        if (this.mainTable.lastDateFilter === undefined) {
            this.mainTable.lastDateFilter = null;
        }
        this._loadDatas(this.mainTable);
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
                    initial: this.today,
                    defaultValue: this.today,
                    values: [this.today] // 强制设置可选值
                },
                editor: "date",
                editorParams: {
                    format: "YYYY-MM-DD"
                },
                headerFilterLiveFilter: false
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
            {title: "ID", field: "id", visible: false},
            {
                title: "设备ID", 
                field: "deviceId", 
                headerFilter: "input",
                formatter: function(cell, formatterParams) {
                    const value = cell.getValue();
                    const isTarget = cell.getData().isTarget;
                    
                    if (isTarget) {
                        return `<span style="color: #23d160; font-weight: bold;">${value}</span>`;
                    } else {
                        return value;
                    }
                }
            },
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
                headerFilterPlaceholder: "筛选日期...",
                headerFilterParams: {
                    initial: this.today,
                    defaultValue: this.today,
                    values: [this.today] // 强制设置可选值
                },
                editor: false,
                headerFilterLiveFilter: false,
                formatter: function(cell, formatterParams) {
                    return cell.getValue() || "";
                }
            },
            {title: "时间", field: "time", width: 130, 
                headerFilter: "input",
                editor: false,
                formatter: function(cell, formatterParams) {
                    // 简单直接显示时间字符串，避免格式化问题
                    return cell.getValue() || "";
                }
            },
            {title: "标签", field: "tag", width: 120, 
                headerFilter: "list",
                headerFilterParams: {
                    values: function() {
                        // this.table是Tabulator实例
                        const data = this.table.getData();
                        const tags = Array.from(new Set(data.map(row => row.tag).filter(Boolean)));
                        const values = { "": "全部" };
                        tags.forEach(tag => values[tag] = tag);
                        return values;
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
     * 初始化表格
     */
    initTable() {
        // 阻止整个document的右键菜单，测试是否能解决问题
        document.addEventListener('contextmenu', function(e) {
            // 只有当点击在表格区域内时才阻止默认菜单
            if (e.target.closest('.tabulator') || e.target.closest('.tabulator-row')) {
                e.preventDefault();
            }
        });

        // 注册全局快捷键
        this.registerKeyboardShortcuts();
        // 创建所有表格实例（懒加载方式）
        this.taskTable;    // 创建任务表格
        this._initTable(this.taskTable);
        this.deviceTable;  // 创建设备表格
        this._initTable(this.deviceTable);
        this.logTable;     // 创建日志表格
        this._initTable(this.logTable);        
    }

    _initTable(table) {
        table.initialized = true;
        this.initTableFilterListener(table);
    }
    
    /**
     * 注册键盘快捷键
     */
    registerKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            const tableType = this.tabTypeMap[this.currentTab];
            let used = false;
            switch(tableType)
            {
                case this.DataType.TASKS:
                    break;
                case this.DataType.DEVICES:
                    if (e.code === 'Space') {
                        used = true;
                        // 如果当前在设备表并且有选中的设备
                        const selectedRows = this._deviceTable.getSelectedRows();
                        this.toggleDeviceTarget(selectedRows.map(row => row.getData().deviceId));
                    }
                    break;
                case this.DataType.LOGS:
                    break;
            }
            if (used) {
                e.preventDefault(); // 阻止默认行为
                e.stopPropagation(); // 阻止事件传播
            }
        }, true); // 使用捕获阶段，确保事件被首先处理
    }
    
    /**
     * 设置设备为目标
     * @param {string|string[]} deviceIds - 设备ID或设备ID数组
     */
    setDeviceAsTarget(deviceIds) {
        // 确保deviceIds是数组
        const ids = Array.isArray(deviceIds) ? deviceIds : [deviceIds];        
        // 目标设备是否是在线，如果是离线，则不添加到目标设备列表
        ids.forEach(id => {
            const device = this.devices.find(dev => dev.deviceId === id || dev.id === id);
            if (device && device.status !== 'offline') {
                if (!this.targetDevices.includes(device.deviceId)) {
                    this.targetDevices.push(device.deviceId);
                }
            }
        });
        
        console.log("设备已设为目标:", this.targetDevices);
        
        // 更新命令输入框的占位文本
        this.updateCommandInputPlaceholder();
        
        // 刷新设备表以更新目标显示
        if (this._deviceTable) {
            this._deviceTable.setData(this.prepareDeviceData());
        }
    }
    
    /**
     * 取消设备的目标状态
     * @param {string|string[]} deviceIds - 设备ID或设备ID数组
     */
    removeDeviceAsTarget(deviceIds) {
        // 确保deviceIds是数组
        const ids = Array.isArray(deviceIds) ? deviceIds : [deviceIds];
        
        // 将id转换为deviceId
        const deviceIdsToRemove = [];
        ids.forEach(id => {
            const device = this.devices.find(dev => dev.deviceId === id || dev.id === id);
            if (device) {
                deviceIdsToRemove.push(device.deviceId);
            }
        });
        
        // 从目标设备列表中移除
        this.targetDevices = this.targetDevices.filter(id => !deviceIdsToRemove.includes(id));
        
        console.log("设备已取消目标:", this.targetDevices);
        
        // 更新命令输入框的占位文本
        this.updateCommandInputPlaceholder();
        
        // 刷新设备表以更新目标显示
        if (this._deviceTable) {
            this._deviceTable.setData(this.prepareDeviceData());
        }
    }
    
    /**
     * 反转设备的目标状态
     * @param {string|string[]} deviceIds - 设备ID或设备ID数组
     */
    toggleDeviceTarget(deviceIds) {
        // 确保deviceIds是数组
        const ids = Array.isArray(deviceIds) ? deviceIds : [deviceIds];
        const deviceIdsToToggle = [];
        ids.forEach(id => {
            const device = this.devices.find(dev => dev.deviceId === id || dev.id === id);
            if (device) {
                deviceIdsToToggle.push(device.deviceId);
            }
        });

        if (deviceIdsToToggle.length === 0) {
            console.warn("没有有效的设备ID");
            return;
        }

        // 对每个设备单独处理
        deviceIdsToToggle.forEach(deviceId => {
            const isTarget = this.targetDevices.includes(deviceId);
            if (isTarget) {
                this.removeDeviceAsTarget(deviceId);
            } else {
                this.setDeviceAsTarget(deviceId);
            }
        });
    }
    
    /**
     * 显示通知消息
     * @param {string} message - 消息内容
     */
    showNotification(message) {
        // 创建通知元素
        const notification = document.createElement('div');
        notification.className = 'notification';
        notification.textContent = message;
        notification.style.position = 'fixed';
        notification.style.bottom = '20px';
        notification.style.right = '20px';
        notification.style.padding = '10px 15px';
        notification.style.backgroundColor = '#23d160';
        notification.style.color = 'white';
        notification.style.borderRadius = '4px';
        notification.style.boxShadow = '0 2px 5px rgba(0,0,0,0.2)';
        notification.style.zIndex = 1000;
        notification.style.transition = 'opacity 0.5s';
        
        // 添加到文档
        document.body.appendChild(notification);
        
        // 3秒后自动消失
        setTimeout(() => {
            notification.style.opacity = '0';
            setTimeout(() => {
                document.body.removeChild(notification);
            }, 500);
        }, 3000);
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
    }
    
    /**
     * 显示上下文菜单
     */
    showContextMenu(e, row) {
        console.log("显示上下文菜单", this.currentTab, e);
        
        const menuConfig = this.menuConfig[this.currentTab];
        if (!menuConfig) {
            console.warn("未找到对应标签页的菜单配置:", this.currentTab);
            return false;
        }

        const rowData = row.getData();
        console.log("行数据:", rowData);
        
        // 清空现有菜单项
        this.contextMenu.innerHTML = '';
        
        // 添加新的菜单项
        let hasVisibleItems = false;
        menuConfig.forEach(item => {
            try {
                if (item.visible(rowData)) {
                    hasVisibleItems = true;
                    const menuItem = document.createElement('a');
                    menuItem.href = '#';
                    menuItem.className = 'context-menu-item';
                    menuItem.dataset.action = item.id;
                    menuItem.innerHTML = `<i class="${item.icon}"></i> ${item.label}`;
                    menuItem.style.display = 'block';
                    menuItem.style.padding = '8px 15px';
                    menuItem.style.color = '#333';
                    menuItem.style.textDecoration = 'none';
                    menuItem.addEventListener('mouseenter', function() {
                        this.style.backgroundColor = '#f0f0f0';
                    });
                    menuItem.addEventListener('mouseleave', function() {
                        this.style.backgroundColor = 'transparent';
                    });
                    menuItem.addEventListener('click', (e) => {
                        e.preventDefault();
                        this.contextMenu.style.display = 'none';
                        try {
                            item.action(e, row);
                        } catch (err) {
                            console.error("菜单项执行错误:", err);
                        }
                    });
                    this.contextMenu.appendChild(menuItem);
                }
            } catch (err) {
                console.error("处理菜单项出错:", item, err);
            }
        });

        // 如果没有可见的菜单项，不显示菜单
        if (!hasVisibleItems) {
            console.warn("没有可见的菜单项");
            return false;
        }
        
        // 设置菜单位置
        const x = e.pageX;
        const y = e.pageY;
        const windowWidth = window.innerWidth;
        const windowHeight = window.innerHeight;
        
        // 先显示菜单以便获取正确的尺寸
        this.contextMenu.style.display = 'block';
        const menuWidth = this.contextMenu.offsetWidth;
        const menuHeight = this.contextMenu.offsetHeight;
        
        // 确保菜单不会超出窗口边界
        const left = (x + menuWidth > windowWidth) ? (windowWidth - menuWidth - 5) : x;
        const top = (y + menuHeight > windowHeight) ? (windowHeight - menuHeight - 5) : y;
        
        // 应用计算好的位置
        this.contextMenu.style.left = `${left}px`;
        this.contextMenu.style.top = `${top}px`;
        
        // 阻止默认右键菜单
        return false;
    }
    
    /**
     * 处理任务操作
     */
    handleTaskAction(action, taskName) {
        console.log(`处理任务操作: ${action}, 任务名称: ${taskName}`);
        let cmd = '';
        let task = this.tasks.find(t => t.id === this.selectedTaskId);
        
        if (!task) {
            console.warn('未找到对应的任务');
            return;
        }
        
        // 根据操作类型确定命令
        switch (action) {
            case 'execute':
                cmd = 'run';
                break;
            case 'pause':
                cmd = 'stop';
                break;
            case 'cancel':
                cmd = 'cancel';
                break;
            default:
                console.warn(`未知的任务操作: ${action}`);
                return;
        }
        
        this.socket.emit('2S_cmd', { 
            cmd: cmd, 
            taskId: taskName,
            deviceId: this.curDeviceID
        });
    }
    
    /**
     * 处理设备操作
     */
    handleDeviceAction(action, deviceId) {
        console.log(`处理设备操作: ${action}, 设备ID: ${deviceId}`);
        let cmd = '';
        
        switch (action) {
            case 'connect':
                cmd = 'connect';
                break;
            case 'disconnect':
                cmd = 'disconnect';
                break;
            case 'restart':
                cmd = 'restart';
                break;
            default:
                console.warn(`未知的设备操作: ${action}`);
                return;
        }
        
        this.socket.emit('2S_cmd', { 
            cmd: cmd, 
            deviceId: deviceId
        });
    }
    
    /**
     * 处理日志操作
     */
    handleLogAction(action, logData) {
        console.log(`处理日志操作: ${action}`, logData);
        
        switch (action) {
            case 'copy':
                // 复制日志内容到剪贴板
                const text = `${logData.date} ${logData.time} [${logData.level}] ${logData.message}`;
                navigator.clipboard.writeText(text).then(() => {
                    console.log('日志已复制到剪贴板');
                }).catch(err => {
                    console.error('复制失败:', err);
                });
                break;
            case 'export':
                // 导出日志
                const blob = new Blob([JSON.stringify(logData, null, 2)], { type: 'application/json' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `log_${logData.id}.json`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(url);
                break;
            default:
                console.warn(`未知的日志操作: ${action}`);
        }
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
            
            // 初始化占位文本
            this.updateCommandInputPlaceholder();
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
        let deviceIds = [];
        
        if (this.targetDevices.length > 0) {
            // 优先使用目标设备
            deviceIds = this.targetDevices;
        } else {
            // 其次使用选中设备
            const selectedRows = this._deviceTable ? this._deviceTable.getSelectedRows() : [];
            if (selectedRows && selectedRows.length > 0) {
                deviceIds = selectedRows.map(row => row.getData().deviceId);
            } else if (this.lastConnectedDevice) {
                // 最后使用最后连接的设备
                deviceIds = [this.lastConnectedDevice];
            } else {
                // 都没有则使用当前设备ID
                deviceIds = [this.curDeviceID];
            }
        }
        
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
    
    /**
     * 更新命令输入框的占位文本
     */
    updateCommandInputPlaceholder() {
        const commandInput = document.getElementById('commandInput');
        if (!commandInput) return;
        
        let placeholder = '';
        if (this.targetDevices.length > 0) {
            placeholder = `输入命令=>${this.targetDevices.length}个目标`;
        } else {
            placeholder = `输入命令=>服务器`;
        }
        
        commandInput.placeholder = placeholder;
    }

    /**
     * 初始化表格过滤器监听
     * @param {Tabulator} table - 表格实例
     */
    initTableFilterListener(table) {
        table.on("dataFiltered", (filters) => {
            this._loadDatas(table);
        });
    }

} 