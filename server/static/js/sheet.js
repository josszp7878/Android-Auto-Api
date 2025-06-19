/**
 * 表格页面管理类
 */
class SheetPage {
    constructor() {
        // 数据类型枚举定义
        this.DataType = {
            TASKS: 'tasks',
            DEVICES: 'devices',
            LOGS: 'logs'
        };

        // 命令类型枚举定义
        this.CMD = {
            getLogs: 'getLogs'
        };

        // 标签页映射表（中文标签 -> 数据类型）
        this.tabTypeMap = {
            '任务': this.DataType.TASKS,
            '设备': this.DataType.DEVICES,
            '日志': this.DataType.LOGS
        };
        this.defTab = '日志';

        this.devices = []; // 初始化为空数组
        this.tasks = []; // 初始化为空数组
        this.logs = []; // 初始化日志数据
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
        
        this.today = new Date().toISOString().split('T')[0]; // 获取当天日期，格式：YYYY-MM-DD
        this.currentTabName = null;
        
        
        // 目标设备列表 - 用于命令发送
        this.targets = {
            [this.DataType.TASKS]: [],
            [this.DataType.DEVICES]: [],
            [this.DataType.LOGS]: []
        };
        
        // 右键菜单配置
        this.menuConfig = {
            '任务': [
                {
                    label: "目标 (Space)",
                    action: (e, row) => {
                        this.updateTarget();
                    }
                },
                {
                    label: (row) => {
                        const state = row.getData().state;
                        return state == 'running' ? '停止' : '执行';
                    },
                    action: (e, row) => {
                        this.handleTaskAction(row);
                    },
                    // disabled: (row) => ['success', 'failed'].includes(row.getData().state)
                }
            ],
            '设备': [
                {
                    label: "目标 (Space)",
                    action: (e, row) => {
                        this.updateTarget();
                    }
                },
                {
                    label: "获取客户端日志",
                    action: (e, row) => {
                        const data = row.getData();
                        const deviceName = data.name || data.id;
                        // 检查设备是否在线
                        if (data.state === 'offline') {
                            this.showNotification(`设备 ${deviceName} 离线，无法获取日志`);
                            return;
                        }
                        // 发送 getLogs 指令
                        const cmd = this.CMD.getLogs;
                        this.sendCmd(cmd, [data.id]);
                    },
                    visible: (rowData) => rowData.state !== 'offline'
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
        this.userPaged = {
            [this.DataType.TASKS]: false,
            [this.DataType.DEVICES]: false,
            [this.DataType.LOGS]: false
        };
        
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

        // 新增任务状态定义
        this.taskStatusMap = {
            'idle': {
                label: '空闲中',
                color: '#a0aec0',
                icon: 'fas fa-stop',
                formatter: "<span style='color: #a0aec0'><i class='fas fa-stop'></i> 空闲中</span>"
            },
            'running': {
                label: '运行中',
                color: '#23d160',
                icon: 'fas fa-play',
                formatter: "<span style='color: #23d160'><i class='fas fa-play'></i> 运行中</span>"
            },
            'paused': {
                label: '已暂停',
                color: '#ffdd57',
                icon: 'fas fa-pause',
                formatter: "<span style='color: #ffdd57'><i class='fas fa-pause'></i> 已暂停</span>"
            },
            'success': {
                label: '已完成',
                color: '#3273dc',
                icon: 'fas fa-check',
                formatter: "<span style='color: #3273dc'><i class='fas fa-check'></i> 已完成</span>"
            },
            'failed': {
                label: '失败',
                color: '#ff3860',
                icon: 'fas fa-times',
                formatter: "<span style='color: #ff3860'><i class='fas fa-times'></i> 失败</span>"
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

        // 新增加载状态跟踪
        this.isLoading = {
            [this.DataType.TASKS]: false,
            [this.DataType.DEVICES]: false,
            [this.DataType.LOGS]: false
        };

        // 添加上一次过滤器值的记录
        this.lastDateFilters = {
            [this.DataType.TASKS]: null,
            [this.DataType.DEVICES]: null,
            [this.DataType.LOGS]: null
        };

        this.deviceCache = {}; // 新增设备缓存
        
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
        
        // 注册前端命令
        BCmds.onLoad();

        // 先初始化Socket连接
        this.socketer = Socketer.init({
            deviceId: '@:Console1',
            queryParams: { 
                platform: 'web',
                version: '1.2.0'
            }
        });
        
        // 确保socket连接建立后再注册事件
        const socket = Socketer.getSocket();
        if (socket.connected) {
            this.initSocketEvents(socket);
        } else {
            socket.on('connect', () => {
                this.initSocketEvents(socket);
            });
        }
    }
    get curTabType() {
        return this.tabTypeMap[this.currentTabName];
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

                selectable: false,
                selectableRows: true, // 启用行选择
                selectableRollingSelection: true,
                // selectableRangeMode: "click",
                // selectableRowsCheck: () => { return true; },
                // selectablePersistence: true,
                // selectableRange: true,
                
                columns: this.getTaskColumns(),
                data: this.tasks,
                headerFilterLiveFilter: false
            });            
            let type = this.DataType.TASKS;
            this._taskTable.dataType = type;
            this._taskTable.on('cellEdited', (cell) => {
                const colName = cell.getColumn().getField();
                if (colName === 'life') {
                    this.handleCellClick(cell, type);
                }
            });
            
        }
        return this._taskTable;
    }

    handleCellClick(cell, type) {
        const row = cell.getRow();
        const colName = cell.getColumn().getField();
        const params = { [colName]: cell.getValue() };
        
        const data = {
            'target': row.getData().id,
            'type': type,
            'params': params
        };
        this.socketer.emit('B2S_setProp', data);
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
                // selectableRange:true,
                // selectableRangeColumns:true,
                // selectableRangeRows:true,
                columns: this.getDeviceColumns(),
                data: this.devices,
                headerFilterLiveFilter: false,
                initialSort: [
                    {column: "state", dir: "desc"}
                ]
            });
            let type = this.DataType.DEVICES;
            this._deviceTable.dataType = type;
            
            // 修改后的设备表格编辑事件监听
            this._deviceTable.on("cellEdited", (cell) => {
                const colName = cell.getColumn().getField();
                if (colName === 'name') {
                    this.handleCellClick(cell, type);
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
                // selectableRangeMode: "click",
                // selectableRowsCheck: () => { return true; },
                // selectablePersistence: true,
                // selectableRange: true,
                selectableCheckbox: true,
                columns: this.getLogColumns(),
                data: this.logs,
                headerFilterLiveFilter: false                
            });
            this._logTable.dataType = this.DataType.LOGS;
        }
        return this._logTable;
    }
    
    /**
     * 加载表格数据
     */
    _loadDatas(table, force=false) {
        if (!table || !table.initialized) return;
        
        try {
            const filters = table.getHeaderFilters() || [];        
            const dateFilter = filters.find(filter => filter.field === 'date');
            let currentDate = dateFilter ? dateFilter.value : null;
            
            if (table.dataType === this.DataType.TASKS || table.dataType === this.DataType.LOGS) {
                if (currentDate === null) {
                    currentDate = this.today;
                    table.setHeaderFilterValue("date", this.today);
                }
            }

            const filterParams = {};
            if (currentDate) filterParams.date = currentDate;

            const type = table.dataType;
            const tabLabel = Object.keys(this.tabTypeMap).find(
                key => this.tabTypeMap[key] === type
            );
            if (!tabLabel) return;

            const socket = this.socketer;
            switch (type) {
                case this.DataType.TASKS:        
                    socket.emitRet('B2S_loadDatas', { type: 'tasks', filters: filterParams }).then(tasks => {
                        this._updateTable(tasks, this.DataType.TASKS, this.tasks);
                    });
                    break;
                case this.DataType.DEVICES:
                    socket.emitRet('B2S_loadDatas', { type: 'devices', filters: filterParams }).then(devices => {
                        this._updateTable(devices, this.DataType.DEVICES, this.devices);
                    });
                    break;
                case this.DataType.LOGS:
                    socket.emitRet('B2S_loadDatas', { type: 'logs', filters: filterParams }).then(logs => {
                        this._updateTable(logs, this.DataType.LOGS, this.logs);
                    });
                    break;
            }
        } catch (error) {
            console.error('加载数据时出错:', error);
        }
    }
    
    /**
     * Socket事件监听
     */        
    initSocketEvents(sio) {        
        // 监听表格数据更新
        console.log('initSocketEvents', sio);
        if (!sio) {
            console.error('Socket未初始化');
            return;
        }
        sio.on('S2B_sheetUpdate', (data) => { 
            // 统一使用映射表检查类型
            if (!Array.isArray(data.data)) return;
            const targetTab = Object.keys(this.tabTypeMap).find(
                key => this.tabTypeMap[key] === data.type
            );
            if (!targetTab) return;

            let targetData = null;
            // 更新对应数据
            switch (data.type) {
                case this.DataType.TASKS:
                    targetData = this.tasks;
                    break;
                case this.DataType.DEVICES:
                    targetData = this.devices;
                    break;
                case this.DataType.LOGS:
                    targetData = this.logs;
                    break;
            }
            this._updateTable(data.data, data.type, targetData);
        });
    }

    
    /**
     * 更新表格数据
     */
    _updateTable(data, dataType, targetData) {
        try {
            if (!targetData) return;
            // 规整数据，确保符合表格要求
            const sheetData = this.toSheetData(data, dataType);
            if (!Array.isArray(sheetData) || sheetData.length === 0) {
                console.warn("无效的sheetData:", sheetData);
                return;
            }
            console.log('update table data length:', sheetData.length);
            // 支持增量更新
            sheetData.forEach(newItem => {
                const existingItemIndex = targetData.findIndex(item => item.id === newItem.id);
                if (existingItemIndex !== -1) {
                    // console.log('update item:', newItem);
                    Object.assign(targetData[existingItemIndex], newItem);
                } else {
                    // console.log('add item:', newItem);
                    targetData.push(newItem);
                }
            });

            if (dataType === this.curTabType) {
                // 只更新当前表格数据
                this.mainTable?.setData(targetData);
                // console.log("表格数据已更新，当前行数:", this.mainTable.getDataCount());
            } else {
                // 更新其它表格数据
                this._updateOtherTable(data, dataType);
            }

        } finally {
            this.isLoading[dataType] = false; // 数据更新完成后重置状态
        }
    }
    
    _updateOtherTable(data, dataType) {
        try {
            if (dataType === this.DataType.DEVICES) {
                // 获取所有受影响的设备ID
                const deviceIDs = data.map(d => d.id);
                // 遍历所有任务行，找到deviceId匹配的行
                this._taskTable.getRows().forEach(row => {
                    const rowData = row.getData();
                    if (deviceIDs.includes(rowData.deviceId)) {
                        row.reformat(); // 触发重绘
                    }
                });
            }
        } catch (error) {
            console.error('更新其它表格时出错:', error);
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
                return data;
        }
        const fieldNames = columns.map(col => col.field);
        return data.map(item => {
            const result = { id: item.id };
            fieldNames.forEach(field => {
                if (field === 'id') return;
                let value = item[field];
                // 统一处理默认值和合法性
                switch (field) {
                    case 'date':
                        // date字段，优先用item.date，没有则尝试从time中提取，否则today
                        if (!value) {
                            if (item.time && typeof item.time === 'string' && item.time.includes(' ')) {
                                value = item.time.split(' ')[0];
                            } else {
                                value = this.today;
                            }
                        }
                        break;
                    case 'time':
                        // time字段，从item.time提取当天时间部分，没有则空字符串
                        if (item.time && typeof item.time === 'string' && item.time.includes(' ')) {
                            value = item.time.split(' ')[1];
                        } else {
                            value = '';
                        }
                        break;
                    case 'level':
                        value = this._validateEnum(value, this.logLevelMap, 'i');
                        break;
                    case 'tag':
                        value = value || '';
                        break;
                    case 'sender':
                        value = value || '';
                        break;
                    case 'score':
                        value = parseFloat(value);
                        value = isNaN(value) ? 'ERR' : value;
                        break;
                    case 'state':
                        // 分不同表格，使用不同的枚举表
                        switch (dataType) {
                            case this.DataType.TASKS:
                                value = this._validateEnum(value, this.taskStatusMap, 'idle');
                                break;
                            case this.DataType.DEVICES:
                                value = this._validateEnum(value, this.deviceStatusMap, 'offline');
                                break;
                        }
                        break;
                    case 'life':
                        value = value || 0;
                        break;
                    default:
                        // 其它字段直接赋值
                        break;
                }
                result[field] = value;
            });
            // // 检查必填字段
            // const requiredFields = {
            //     [this.DataType.TASKS]: ['time', 'name', 'deviceId'],
            //     [this.DataType.DEVICES]: ['name', 'deviceId'],
            //     [this.DataType.LOGS]: ['time', 'level', 'tag', 'sender']
            // }[dataType] || [];
            // for (const f of requiredFields) {
            //     if (!result[f]) {
            //         console.error('数据项缺少必填字段:', { id: item.id, missing: f, rawData: item });
            //     }
            // }
            return result;
        }).filter(item => item !== null && item.date !== 'INVALID_DATE');
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
            if (tab === this.currentTabName) {
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
        if (tab === this.currentTabName) return;
        this.currentTabName = tab;
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
                break;
        }
        this.userPaged[tabType] = false;
        // 更新命令输入框的占位文本
        this.updateCommandInputPlaceholder();
        // 显式初始化 lastDateFilter
        if (this.mainTable.lastDateFilter === undefined) {
            this.mainTable.lastDateFilter = null;
        }
        this._loadDatas(this.mainTable, true);
    }
    
    /**
     * 获取任务表格列定义
     */
    getTaskColumns() {
        return [
            {title: "ID", field: "id", width: 60, editor: false, headerFilter: "input", hozAlign: "center"},
            {
                title: "目标", 
                field: "isTarget", 
                width: 70, 
                hozAlign: "center",
                formatter: (cell) => {
                    const data = cell.getData();
                    const checked = this.targets[this.DataType.TASKS].includes(data.id);
                    return `<div style="text-align:center">
                        <input type='checkbox' ${checked ? 'checked' : ''} 
                               style='width:18px;height:18px;pointer-events:none;'>
                    </div>`;
                },
                cellClick: (e, cell) => {
                    e.stopPropagation();
                    this.handleTargetClick(cell, this.DataType.TASKS);
                },
                headerSort: false
            },
            {title: "设备", field: "deviceId", width: 160, headerFilter: "input",
                formatter: (cell) => {
                    const deviceId = cell.getValue();
                    const device = this.get(deviceId);
                    if (!device) return deviceId;
                    
                    const deviceName = device.name || `设备${deviceId}`;
                    const state = device.state;
                    const status = this.deviceStatusMap[state] || this.deviceStatusMap['offline'];
                    
                    return `<span style='color: ${status.color}; font-weight: bold;'>${deviceName}(${deviceId})</span>`;
                }
            },
            {
                title: "任务名称", 
                field: "name", 
                headerFilter: "input",
                formatter: (cell) => cell.getValue(),
                editor: "input"
            },
            {
                title: "日期", 
                field: "date", 
                width: 130,
                headerFilter: "input",
                headerFilterPlaceholder: "YYYY-MM-DD",
                headerFilterFunc: "like",
                editor: false,
                headerFilterLiveFilter: false,
                formatter: function(cell) {
                    return cell.getValue() || "";
                }
            },
            {
                title: "进度", 
                field: "progress", 
                width: 150,
                formatter: (cell) => {
                    const data = cell.getData();
                    const progress = Number(data.progress) || 0;
                    const life = Math.abs(Number(data.life)) || 1;
                    // 进度条比例，允许超过100%
                    const percent = Math.round((progress / life) * 100);
                    return `
                        <div style="
                            background: transparent;
                            border-radius: 10px;
                            height: 20px;
                            position: relative;
                            overflow: hidden;
                        ">
                            <div style="
                                width: ${percent}%;
                                height: 100%;
                                background: #388E3C;
                                transition: width 0.3s ease;
                                display: flex;
                                align-items: center;
                                justify-content: center;
                            ">
                                <span style="
                                    color: white;
                                    font-size: 12px;
                                    font-weight: bold;
                                    position: absolute;
                                    left: 50%;
                                    transform: translateX(-50%);
                                ">${progress}</span>
                            </div>
                        </div>
                    `;
                },
                formatterParams: {
                    min: 0,
                    max: 1
                }
            },
            {
                title: "状态", 
                field: "state", 
                width: 120, 
                headerFilter: "list",
                headerFilterParams: {
                    values: {
                        "": "全部",
                        ...Object.fromEntries(
                            Object.entries(this.taskStatusMap).map(([k, v]) => [k, v.label])
                        )
                    }
                },
                formatter: "lookup",
                formatterParams: Object.fromEntries(
                    Object.entries(this.taskStatusMap).map(([k, v]) => [k, v.formatter]) // 显示状态标签
                )
            },
            {
                title: "持续时间/次数",
                field: "life",
                editor: "input",
                width: 100,
                hozAlign: "center",
                headerFilter: "number",
                headerFilterFunc: ">="
            },
            {title: "得分", field: "score", width: 100, headerFilter: "number"},
        ];
    }
    
    /**
     * 获取设备表格列定义
     */
    getDeviceColumns() {
        return [
            {title: "ID", field: "id", width: 60, editor: false, headerFilter: "input", hozAlign: "center"},
            {
                title: "目标", 
                field: "isTarget", 
                width: 70, 
                hozAlign: "center",
                formatter: (cell) => {
                    const data = cell.getData();
                    const checked = this.targets[this.DataType.DEVICES].includes(data.id);
                    const isOffline = data.state === 'offline';
                    
                    return `<div style="text-align:center">
                        <input type='checkbox' ${checked ? 'checked' : ''} 
                               style='width:18px;height:18px;pointer-events:none;
                                      ${isOffline ? 'opacity:0.5;cursor:not-allowed;' : ''}'>
                    </div>`;
                },
                cellClick: (e, cell) => {
                    const data = cell.getData();
                    // 阻止对离线设备的操作
                    if(data.state === 'offline') {
                        return;
                    }
                    e.stopPropagation();
                    this.handleTargetClick(cell, this.DataType.DEVICES);
                },
                headerSort: false
            },
            { 
                title: "设备名称", 
                field: "name",
                editor: "input",
                headerFilter: "input",
                formatter: (cell) => cell.getValue() // 直接返回值
            },
            {
                title: "状态", 
                field: "state", 
                width: 120,
                headerFilter: "list",
                headerFilterParams: {
                    values: {
                        "": "全部",
                        ...Object.fromEntries(
                            Object.entries(this.deviceStatusMap).map(([k, v]) => [k, v.label])
                        )
                    }
                },
                formatter: "lookup",
                formatterParams: Object.fromEntries(
                    Object.entries(this.deviceStatusMap).map(([k, v]) => [k, v.formatter])
                )
            },
            {
                title: "DEBUG", 
                field: "debug", 
                width: 100,
                hozAlign: "center",
                formatter: (cell) => {
                    const value = cell.getValue();
                    const checked = value ? 'checked' : '';
                    return `<input type='checkbox' ${checked} style='width:18px;height:18px;'>`;
                },
                cellClick: (e, cell) => {
                    e.stopPropagation();
                    const currentValue = cell.getValue();
                    const newValue = !currentValue;
                    
                    // 更新本地数据
                    cell.setValue(newValue);
                    
                    // 发送到服务端更新，使用B2S_setProp事件
                    const row = cell.getRow();
                    const data = {
                        'target': row.getData().id,
                        'type': 'devices',
                        'params': { 'debug': newValue }
                    };                    
                    this.socketer.emit('B2S_setProp', data);
                },
                headerSort: false,
                editor: false
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
            {
                title: "日期", 
                field: "date", 
                width: 130,
                headerFilter: "input",
                headerFilterPlaceholder: "YYYY-MM-DD",
                headerFilterFunc: "like",
                editor: false,
                headerFilterLiveFilter: false,
                formatter: function(cell) {
                    return cell.getValue() || "";
                }
            },
            {
                title: "时间", 
                field: "time", 
                width: 100,
                headerFilter: "input",
                headerFilterPlaceholder: "HH:MM:SS",
                editor: false,
                headerFilterLiveFilter: false,
                formatter: function(cell) {
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
                    values: {
                        "": "全部",
                        ...levelFilterValues
                    }
                },
                formatter: function(cell, formatterParams, onRendered) {
                    const value = cell.getValue();
                    if (!value) return "";
                    
                    // 使用预定义的格式化参数
                    return levelFormatterParams[value] || value;
                }
            },
            {
                title: "发送者", 
                field: "sender", 
                width: 150, 
                headerFilter: "input",
                formatter: (cell, formatterParams, onRendered) => {
                    const data = cell.getData();
                    const isTarget = this.targets[this.DataType.LOGS].includes(data.id);
                    return isTarget
                        ? `<span style="color: #23d160; font-weight: bold;">${data.sender}</span>`
                        : data.sender;
                }
            },
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
        
        table.on("tableBuilt", () => {
            this.userPaged[table.dataType] = true;
            if(table.dataType === this.tabTypeMap[this.defTab]) {
                this.switchTab(this.defTab);
            }
        });

        // 为所有表格添加分页监听
        table.on("dataProcessed", () => {
            if (!this.userPaged[table.dataType]) {
                const pageCount = table.getPageMax();
                if (pageCount > 0) {
                    table.setPage(pageCount);
                }
            }
        });
        
        // 使用 dataFiltered 事件，并比较日期值变化
        table.on("dataFiltered", () => {
            const dateFilter = table.getHeaderFilters().find(f => f.field === "date");
            const currentDateValue = dateFilter ? dateFilter.value : null;
            const lastDateValue = this.lastDateFilters[table.dataType];

            // 只有当日期值发生变化时才加载数据
            if (currentDateValue !== lastDateValue) {
                console.log("日期过滤器值改变:", lastDateValue, "->", currentDateValue);
                if (lastDateValue != null)
                    this._loadDatas(table);
                this.lastDateFilters[table.dataType] = currentDateValue;
            }
        });
    }
    
    /**
     * 注册键盘快捷键
     */
    registerKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            if (e.code === 'Space' && e.target.closest('.tabulator')) {
                this.updateTarget();
                e.preventDefault();
            }
        }, true);
    }
    
    /**
     * 新增通用目标管理方法
     */
    updateTarget() {
        const dataType = this.mainTable?.dataType;
        if (!dataType) return;

        // 获取选中行ID
        const ids = this.mainTable.getSelectedRows()
            .map(row => row.getData().id);
        // 更新目标列表
        ids.forEach(id => {
            const index = this.targets[dataType].indexOf(id);
            index === -1 
                ? this.targets[dataType].push(id)
                : this.targets[dataType].splice(index, 1);
        });
        
        // 刷新对应表格
        switch(dataType) {
            case this.DataType.DEVICES:
                this._deviceTable?.setData(this.devices);
                break;
            case this.DataType.TASKS:
                this._taskTable?.setData(this.tasks);
                break;
            case this.DataType.LOGS:
                this._logTable?.setData(this.logs);
                break;
        }
        
        // 更新命令输入提示
        if(dataType === this.DataType.DEVICES){
            this.updateCommandInputPlaceholder();
        }
    }
    
    /**
     * 显示通知消息
     * @param {string} message - 消息内容
     */
    showNotification(message) {
        // 获取现有通知的数量，用于计算位置
        const existingNotifications = document.querySelectorAll('.notification');
        const notificationHeight = 50; // 预估的单个通知高度
        const spacing = 10; // 通知之间的间距
        
        // 创建通知元素
        const notification = document.createElement('div');
        notification.className = 'notification';
        notification.textContent = message;
        notification.style.position = 'fixed';
        notification.style.right = '20px';
        notification.style.padding = '12px 18px';
        notification.style.backgroundColor = '#23d160';
        notification.style.color = 'white';
        notification.style.borderRadius = '6px';
        notification.style.boxShadow = '0 4px 12px rgba(0,0,0,0.15)';
        notification.style.zIndex = 1000;
        notification.style.transition = 'all 0.3s ease-in-out';
        notification.style.maxWidth = '400px';
        notification.style.wordBreak = 'break-word';
        notification.style.fontSize = '14px';
        notification.style.lineHeight = '1.4';
        
        // 计算底部位置，避免遮挡输入框，向上扩展
        const commandArea = document.querySelector('.command-area');
        const commandAreaHeight = commandArea ? commandArea.offsetHeight : 60;
        const baseBottom = commandAreaHeight + 30; // 输入框高度 + 额外间距
        
        // 每个新通知都在上一个通知的上方
        const bottomPosition = baseBottom + (existingNotifications.length * (notificationHeight + spacing));
        notification.style.bottom = `${bottomPosition}px`;
        
        // 初始状态：透明且稍微偏右
        notification.style.opacity = '0';
        notification.style.transform = 'translateX(100%)';
        
        // 添加到文档
        document.body.appendChild(notification);
        
        // 动画显示
        requestAnimationFrame(() => {
            notification.style.opacity = '1';
            notification.style.transform = 'translateX(0)';
        });
        
        // 8秒后自动消失
        const hideNotification = () => {
            notification.style.opacity = '0';
            notification.style.transform = 'translateX(100%)';
            setTimeout(() => {
                if (notification.parentNode) {
                    document.body.removeChild(notification);
                }
                // 重新调整其他通知的位置
                this.adjustNotificationPositions();
            }, 300);
        };
        
        setTimeout(hideNotification, 8000);
        
        // 点击关闭功能
        notification.style.cursor = 'pointer';
        notification.addEventListener('click', hideNotification);
    }

    /**
     * 重新调整通知位置，用于当某个通知消失后重排其他通知
     */
    adjustNotificationPositions() {
        const notifications = document.querySelectorAll('.notification');
        const notificationHeight = 50;
        const spacing = 10;
        
        const commandArea = document.querySelector('.command-area');
        const commandAreaHeight = commandArea ? commandArea.offsetHeight : 60;
        const baseBottom = commandAreaHeight + 30;
        
        notifications.forEach((notification, index) => {
            const bottomPosition = baseBottom + (index * (notificationHeight + spacing));
            notification.style.bottom = `${bottomPosition}px`;
        });
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
        console.log("显示上下文菜单", this.currentTabName, e);
        
        const menuConfig = this.menuConfig[this.currentTabName];
        if (!menuConfig) {
            console.warn("未找到对应标签页的菜单配置:", this.currentTabName);
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
                // 检查菜单项是否可见，如果没有visible函数则默认可见
                const isVisible = item.visible ? item.visible(rowData) : true;
                if (isVisible) {
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
    async handleTaskAction(row) {
        // 获取所有选中行，如果没有则只处理当前行
        let rows = this._taskTable.getSelectedRows();
        if (!rows || rows.length === 0) {
            rows = [row];
        }
        for (const r of rows) {
            const data = r.getData();
            let cmd = '';
            let task = this.tasks.find(t => t.id === data.id);        
            if (!task) {
                console.warn('未找到对应的任务');
                continue;
            }
            // 根据操作类型确定命令
            if (data.state === 'running') {
                cmd = `stopTask ${task.id}`;
            } else {
                cmd = `startTask ${task.id}`;
            }
            this.sendCmd(cmd, [task.deviceId]);
        }
    }

    sendCmd(cmd, targets, params, callback=null) {
        const socket = this.socketer;
        try {
            socket.emitRet('2S_Cmd', { 
                command: cmd, 
                targets: targets,
                params: params
            }).then(result => {
                if(callback) {
                    callback(result);
                } else {
                    this.onCmdResult(cmd, result, targets);
                }
            });
            
        } catch (error) {
            console.error('发送命令失败:', error);
            this.showNotification(`命令执行失败: ${error.message}`);
            throw error;
        }
    }

  
    /**
     * 统一的命令执行结果处理函数
     * @param {string} cmd - 执行的命令
     * @param {*} result - 命令执行结果
     * @param {Array} targets - 目标设备列表
     */
    onCmdResult(cmd, result, targets = []) {
        console.log('命令执行结果:', cmd, result);
        
        // 解析命令类型
        const cmdParts = cmd.trim().split(/\s+/);
        const cmdName = cmdParts[0];
        switch (cmdName) {
            case this.CMD.getLogs:
                this.onGetLogs(result, targets);
                break;
            default:
                // 默认处理：显示结果或错误信息
                if (typeof result === 'string' && result.startsWith('e~')) {
                    this.showNotification(`命令执行失败: ${result.substring(2)}`);
                } else if (result) {
                    console.log('命令执行成功:', result);
                }
                break;
        }
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
        this.sendCmd(cmd, [deviceId]);
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
     * 处理获取日志命令的结果
     * @param {*} result - 命令执行结果
     * @param {Array} targets - 目标设备列表
     */
    onGetLogs(result, targets = []) {
        let target = '@';
        if (targets.length > 0) {
            target = targets[0];
        }
        result = result[target];
        if (typeof result === 'string' && result.startsWith('e~')) {
            const deviceName = targets.length > 0 ? targets[0] : '设备';
            this.showNotification(`获取${deviceName}日志失败: ${result.substring(2)}`);
        } else if (Array.isArray(result)) {
            // 刷新日志表格数据, 只获取第一个元素
            this._updateTable(result, this.DataType.LOGS, this.logs);
            // 设置日期过滤器
            const currentDate = new Date().toISOString().split('T')[0].replace(/-/g, '');
            const formattedDate = currentDate.replace(/(\d{4})(\d{2})(\d{2})/, '$1-$2-$3');
            if (this._logTable) {
                this._logTable.setHeaderFilterValue("date", formattedDate);
            }
            const deviceName = targets.length > 0 ? targets[0] : '服务端';
            this.showNotification(`成功获取${deviceName}的 ${result.length} 条日志`);
        } else {
            const deviceName = targets.length > 0 ? targets[0] : '设备';
            this.showNotification(`${deviceName}没有日志数据`);
        }
    }

    /**
     * 发送命令
     * 命令格式: 目标数组 分类符 命令内容
     * 分类符: # - 客户端指令, @ - 服务端指令, 无 - 前端本地指令
     */
    async sendCommand() {
        const commandInput = document.getElementById('commandInput');
        if (!commandInput || !commandInput.value.trim()) return;
        
        let rawCommand = commandInput.value.trim();
        console.log('发送命令:', rawCommand);
        
        // 添加到历史记录
        this.addCommandToHistory(rawCommand);
        
        // 字符标准化处理
        rawCommand = this.normalizeCharacters(rawCommand);
        
        // 解析命令格式
        const parsedCmd = this.parseCommand(rawCommand);
        console.log('解析结果:', parsedCmd);
        
        if (!parsedCmd.command) {
            this.showNotification('命令内容不能为空');
            return;
        }
        
        try {
            switch (parsedCmd.type) {
                case 'local':
                    // 前端本地指令
                    await this.executeLocalCommand(parsedCmd.command);
                    break;
                    
                case 'client':
                    // 客户端指令 - 发送到设备
                    this.executeClientCommand(parsedCmd.command, parsedCmd.targets);
                    break;
                    
                case 'server':
                    // 服务端指令 - 发送到服务器
                    this.executeServerCommand(parsedCmd.command, parsedCmd.targets);
                    break;
                    
                default:
                    this.showNotification(`未知的命令类型: ${parsedCmd.type}`);
                    return;
            }
        } catch (error) {
            console.error('命令执行出错:', error);
            this.showNotification(`命令执行出错: ${error.message}`);
        }
        
        // 清空输入框
        commandInput.value = '';
        this.historyIndex = -1;
        this._tempCommand = undefined;
    }

    /**
     * 执行前端本地指令
     * @param {string} command - 命令内容
     */
    async executeLocalCommand(command) {
        const cmd = {
            cmd: command,
            params: {
                sheetPage: this
            }
        };
        
        const result = await CmdMgr.do(cmd);
        if (result && result.result) {
            if (typeof result.result === 'string') {
                this.showNotification(result.result);
            } else {
                // 处理对象类型的结果
                console.log('本地命令执行结果:', result.result);
                this.showNotification('命令执行完成，请查看控制台');
            }
        } else {
            this.showNotification('本地命令未找到或执行失败');
        }
    }

    /**
     * 执行客户端指令
     * @param {string} command - 命令内容
     * @param {Array} targets - 目标设备ID数组
     */
    executeClientCommand(command, targets) {
        if (targets.length === 0) {
            this.showNotification('没有指定目标设备');
            return;
        }
        
        console.log(`发送客户端指令到设备 [${targets.join(', ')}]: ${command}`);
        this.sendCmd(command, targets);
        this.showNotification(`客户端指令已发送到 ${targets.length} 个设备`);
    }

    /**
     * 执行服务端指令
     * @param {string} command - 命令内容
     * @param {Array} targets - 目标设备ID数组（服务端指令可能不需要目标）
     */
    executeServerCommand(command, targets) {
        console.log(`发送服务端指令: ${command}`, targets.length > 0 ? `目标: [${targets.join(', ')}]` : '');
        
        // 服务端指令可能不需要目标设备，直接发送到服务器
        this.sendCmd(command, targets);
        
        if (targets.length > 0) {
            this.showNotification(`服务端指令已发送，目标: ${targets.length} 个设备`);
        } else {
            this.showNotification('服务端指令已发送');
        }
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
        if (this.targets[this.DataType.DEVICES].length > 0) {
            placeholder = `输入命令=>${this.targets[this.DataType.DEVICES].length}个目标`;
        } else {
            placeholder = `输入命令=>服务器`;
        }
        
        commandInput.placeholder = placeholder;
    }

    /**
     * 验证枚举类型字段值
     * @param {string} value - 待验证的值
     * @param {Array|Object} validValues - 有效值集合（数组或对象key）
     * @param {string} defaultValue - 默认返回值
     * @returns {string} 验证后的值
     */
    _validateEnum(value, validValues, defaultValue) {
        const validKeys = Array.isArray(validValues) ? validValues : Object.keys(validValues);
        return validKeys.includes(value) ? value : defaultValue;
    }

    /**
     * 字符标准化处理函数
     * @param {string} text - 待处理的文本
     * @param {Object} charMap - 字符映射表，默认为中文标点符号到英文标点符号的映射
     * @returns {string} 处理后的文本
     */
    normalizeCharacters(text, charMap = null) {
        if (!text || typeof text !== 'string') return text;
        
        // 默认字符映射表：中文标点符号 -> 英文标点符号
        const defaultCharMap = {
            '》': '>',
            '：': ':',
            '；': ';',
            '，': ',',
            '。': '.',
            '？': '?',
            '！': '!',
            '（': '(',
            '）': ')',
            '【': '[',
            '】': ']',
            '《': '<',
            '“': '"',
            '”': '"',
            '‘': "'"
        };
        
        // 使用传入的映射表或默认映射表
        const actualCharMap = charMap || defaultCharMap;
        
        let result = text;
        
        // 遍历映射表进行替换
        for (const [from, to] of Object.entries(actualCharMap)) {
            result = result.replace(new RegExp(from, 'g'), to);
        }
        
        return result;
    }

    /**
     * 解析命令格式: 目标数组 分类符 命令内容
     * @param {string} rawCommand - 原始命令字符串
     * @returns {Object} 解析结果 { targets: Array, type: String, command: String }
     */
    parseCommand(rawCommand) {
        if (!rawCommand || typeof rawCommand !== 'string') {
            return { targets: [], type: 'local', command: '' };
        }

        const command = rawCommand.trim();
        
        // 查找分类符的位置
        let separatorIndex = -1;
        let commandType = 'local'; // 默认为本地指令
        
        // 查找 # 或 @ 分类符
        for (let i = 0; i < command.length; i++) {
            const char = command[i];
            if (char === '#') {
                separatorIndex = i;
                commandType = 'client';
                break;
            } else if (char === '@') {
                separatorIndex = i;
                commandType = 'server';
                break;
            }
        }
        
        let targets = [];
        let actualCommand = '';
        
        if (separatorIndex === -1) {
            // 没有找到分类符，整个字符串都是命令内容
            actualCommand = command;
        } else {
            // 找到了分类符，分离目标数组和命令内容
            const targetsPart = command.substring(0, separatorIndex).trim();
            actualCommand = command.substring(separatorIndex + 1).trim();
            
            // 解析目标数组
            if (targetsPart) {
                // 用逗号、空格或分号分隔目标ID
                targets = targetsPart
                    .split(/[,\s;]+/)
                    .map(t => t.trim())
                    .filter(t => t.length > 0);
            }
        }
        
        // 如果没有指定目标，使用当前选中的设备
        if (targets.length === 0 && commandType !== 'local') {
            targets = [...this.targets[this.DataType.DEVICES]];
        }
        
        return {
            targets: targets,
            type: commandType,
            command: actualCommand
        };
    }

    // 在类中添加目标列通用处理方法
    handleTargetClick(cell, dataType) {
        const data = cell.getData();
        const id = data.id;
        const targets = this.targets[dataType];
        const idx = targets.indexOf(id);
        
        // 切换目标状态
        idx === -1 ? targets.push(id) : targets.splice(idx, 1);
        
        // 更新当前行
        cell.getRow().update({isTarget: targets.includes(id)});
        
        // 更新命令输入提示（仅设备目标变化时）
        if(dataType === this.DataType.DEVICES) {
            this.updateCommandInputPlaceholder();
        }
    }

    /**
     * 获取设备数据
     * @param {string|number} id 设备ID
     * @returns {object|null} 设备数据
     */
    get(id) {
        return this.devices.find(d => d.id === id) || null;
    }
    


} 
