/**
 * 任务表格页面管理类
 */
class TaskPage {
    constructor(initialDevices, tasksData, curDeviceID) {
        this.devices = initialDevices || {};
        this.tasks = Array.isArray(tasksData) ? tasksData : []; // 确保tasks是数组
        this.curDeviceID = curDeviceID;
        this.socket = null;
        this.mainTable = null;
        this.contextMenu = document.getElementById('context-menu');
        this.selectedTaskId = null;
        this.today = new Date().toISOString().split('T')[0]; // 获取当天日期，格式：YYYY-MM-DD
        this.currentTab = "任务"; // 初始化当前页面为"任务"
        
        // 初始化Socket连接
        this.initSocket();
        
        // 初始化标签页
        this.initTabs();
        
        // 初始化表格
        this.initMainTable();
        
        // 初始化上下文菜单
        this.initContextMenu();
    }
    
    /**
     * 初始化Socket连接
     */
    initSocket() {
        this.socket = io();
        
        // 监听任务数据更新
        this.socket.on('tasks_update', (data) => {
            this.tasks = Array.isArray(data) ? data : []; // 确保是数组
            if (this.mainTable && this.currentTab === "任务") {
                // 更新任务数据
                this.mainTable.setData(this.tasks);
            }
        });
        
        // 监听设备数据更新
        this.socket.on('devices_update', (data) => {
            this.devices = data;
            if (this.mainTable && this.currentTab === "设备") {
                // 准备设备数据
                const devicesList = this.prepareDeviceData();
                
                // 更新设备数据
                this.mainTable.setData(devicesList);
            }
        });
        
        // 请求当天任务数据
        this.socket.emit('get_daily_tasks', { date: this.today });
    }
    
    /**
     * 准备设备数据
     */
    prepareDeviceData() {
        return Object.entries(this.devices).map(([id, device]) => {
            // 确保设备状态只能是"online"或"offline"
            const status = device.status === "online" ? "online" : "offline";
            
            return {
                id: id,
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
        tabsContainer.style.cssText = 'display: flex; justify-content: flex-start; background-color: #222; padding: 5px 10px; border-top: 1px solid #333;';
        
        // 创建标签页按钮
        const tabs = ['任务', '设备'];
        tabs.forEach(tab => {
            const tabButton = document.createElement('button');
            tabButton.textContent = tab;
            tabButton.dataset.tab = tab;
            tabButton.className = 'tab-button';
            
            // 设置标签样式：黑底，白字，深绿色边框，选中时粗体和浅色边框
            const isActive = tab === this.currentTab;
            const borderColor = isActive ? '#4caf50' : '#006400'; // 活动标签边框颜色浅一些
            const fontWeight = isActive ? 'bold' : 'normal';
            
            tabButton.style.cssText = `
                margin-right: 0px; 
                padding: 8px 8px; 
                border: 2px solid ${borderColor}; 
                border-radius: 3px; 
                cursor: pointer; 
                background-color: #222; 
                color: white;
                font-weight: ${fontWeight};
                transition: all 0.2s ease;
            `;
            
            tabButton.addEventListener('click', () => this.switchTab(tab), {passive: true});
            tabsContainer.appendChild(tabButton);
        });
        
        // 将标签页添加到表格容器下方
        const tableContainer = document.getElementById('main-table');
        tableContainer.parentNode.insertBefore(tabsContainer, tableContainer.nextSibling);
    }
    
    /**
     * 切换标签页
     */
    switchTab(tab) {
        if (tab === this.currentTab) return;
        
        // 更新当前标签页
        this.currentTab = tab;
        
        // 更新标签按钮样式
        const buttons = document.querySelectorAll('.tab-button');
        buttons.forEach(button => {
            if (button.dataset.tab === tab) {
                button.style.borderColor = '#4caf50'; // 浅绿色边框
                button.style.fontWeight = 'bold';
            } else {
                button.style.borderColor = '#006400'; // 深绿色边框
                button.style.fontWeight = 'normal';
            }
        });
        
        // 更新表格数据和配置
        if (this.mainTable) {
            if (tab === "任务") {
                // 先销毁现有表格
                this.mainTable.destroy();
                
                // 重新创建任务表格
                this.mainTable = new Tabulator("#main-table", {
                    layout: "fitColumns",
                    pagination: "local",
                    paginationSize: 15,
                    paginationSizeSelector: [10, 15, 20, 30, 50],
                    movableColumns: true,
                    resizableRows: true,
                    placeholder: "暂无数据",
                    height: "calc(100% - 40px)",
                    persistence: {
                        sort: true,
                        filter: true
                    },
                    rowContextMenu: this.showContextMenu.bind(this),
                    columns: this.getTaskColumns(),
                    data: this.tasks,
                    tableBuilt: () => {
                        console.log("任务表格构建完成");
                        setTimeout(() => this.applyDateFilter(), 100);
                    }
                });
            } else if (tab === "设备") {
                // 先销毁现有表格
                this.mainTable.destroy();
                
                // 重新创建设备表格
                const devicesList = this.prepareDeviceData();
                this.mainTable = new Tabulator("#main-table", {
                    layout: "fitColumns",
                    pagination: "local",
                    paginationSize: 15,
                    paginationSizeSelector: [10, 15, 20, 30, 50],
                    movableColumns: true,
                    resizableRows: true,
                    placeholder: "暂无数据",
                    height: "calc(100% - 40px)",
                    persistence: {
                        sort: true,
                        filter: true
                    },
                    columns: this.getDeviceColumns(),
                    data: devicesList,
                    tableBuilt: () => {
                        console.log("设备表格构建完成");
                    }
                });
            }
        }
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
                    "pending": "<span style='color: #7a7a7a'><i class='fas fa-clock'></i> 待处理</span>"
                }
            },
            {title: "生命值", field: "life", width: 120, headerFilter: "number"},
            {title: "分数", field: "score", width: 120, headerFilter: "number"}
        ];
    }
    
    /**
     * 获取设备表格列定义
     */
    getDeviceColumns() {
        return [
            {title: "ID", field: "id", headerFilter: "input"},
            {title: "分组", field: "group", headerFilter: "input"},
            {
                title: "状态", 
                field: "status", 
                headerFilter: "list",
                headerFilterParams: {
                    values: {"online": "在线", "offline": "离线"}
                },
                formatter: "lookup",
                formatterParams: {
                    "online": "<span style='color: #23d160'><i class='fas fa-check-circle'></i> 在线</span>",
                    "offline": "<span style='color: #ff3860'><i class='fas fa-times-circle'></i> 离线</span>"
                }
            },
            {title: "当前任务", field: "currentTask", headerFilter: "input"},
            {title: "得分", field: "score", headerFilter: "number"}
        ];
    }
    
    /**
     * 初始化主表格
     */
    initMainTable() {
        // 确保数据是数组
        if (!Array.isArray(this.tasks)) {
            this.tasks = [];
        }
        
        // 创建主表格
        this.mainTable = new Tabulator("#main-table", {
            layout: "fitColumns",
            pagination: "local",
            paginationSize: 15,
            paginationSizeSelector: [10, 15, 20, 30, 50],
            movableColumns: true,
            resizableRows: true,
            placeholder: "暂无数据",
            height: "calc(100% - 40px)", // 设置为100%高度减去标签页高度
            persistence: {
                sort: true,
                filter: true
            },
            rowContextMenu: this.showContextMenu.bind(this),
            columns: this.getTaskColumns(),
            data: this.tasks,
            tableBuilt: () => {
                console.log("表格构建完成");
                // 表格构建后尝试应用过滤器
                setTimeout(() => this.applyDateFilter(), 200);
            }
        });
    }
    
    /**
     * 应用日期过滤器，显示当天任务
     */
    applyDateFilter() {
        // 确保表格已初始化
        if (!this.mainTable) {
            console.log("表格尚未初始化，无法应用过滤器");
            return;
        }
        
        try {
            // 只在任务页面设置过滤器
            if (this.currentTab === "任务") {
                // 获取日期列
                const dateColumn = this.mainTable.getColumn("date");
                if (dateColumn) {
                    dateColumn.setHeaderFilterValue(this.today);
                    console.log("已应用日期过滤器:", this.today);
                } else {
                    console.log("未找到日期列");
                    // 延迟重试
                    setTimeout(() => this.applyDateFilter(), 500);
                }
            }
        } catch (err) {
            console.error("应用日期过滤器时出错:", err);
        }
    }
    
    /**
     * 初始化上下文菜单
     */
    initContextMenu() {
        // 注册上下文菜单点击事件
        this.contextMenu.addEventListener('click', (e) => {
            const action = e.target.closest('.dropdown-item').dataset.action;
            if (action && this.selectedTaskId) {
                this.handleTaskAction(action, this.selectedTaskId);
            }
            this.contextMenu.classList.remove('show');
        }, {passive: true});
    }
    
    /**
     * 显示上下文菜单
     */
    showContextMenu(e, row) {
        // 只在任务标签页显示上下文菜单
        if (this.currentTab !== "任务") {
            return;
        }
        
        e.preventDefault();
        
        // 存储选中的任务ID
        this.selectedTaskId = row.getData().id;
        
        // 显示上下文菜单
        this.contextMenu.style.top = e.pageY + 'px';
        this.contextMenu.style.left = e.pageX + 'px';
        this.contextMenu.classList.add('show');

        // 添加一个点击事件监听器，当点击菜单外部时隐藏菜单
        const clickHandler = (event) => {
            if (!this.contextMenu.contains(event.target)) {
                this.contextMenu.classList.remove('show');
                document.removeEventListener('click', clickHandler);
            }
        };
        
        // 延迟添加事件监听器，避免立即触发
        setTimeout(() => {
            document.addEventListener('click', clickHandler, {passive: true});
        }, 10);
    }
    
    /**
     * 处理任务操作
     */
    handleTaskAction(action, taskId) {
        switch(action) {
            case 'execute':
                this.executeTask(taskId);
                break;
            case 'pause':
                this.pauseTask(taskId);
                break;
            case 'cancel':
                this.cancelTask(taskId);
                break;
        }
    }
    
    /**
     * 执行任务
     */
    executeTask(taskId) {
        this.socket.emit('execute_task', {
            taskId: taskId
        });
    }
    
    /**
     * 暂停任务
     */
    pauseTask(taskId) {
        this.socket.emit('pause_task', {
            taskId: taskId
        });
    }
    
    /**
     * 取消任务
     */
    cancelTask(taskId) {
        this.socket.emit('cancel_task', {
            taskId: taskId
        });
    }
} 