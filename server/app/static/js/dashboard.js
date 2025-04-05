class Dashboard {
    constructor(initialDevices, curDeviceID) {
        console.log('初始化Dashboard，设备数据:', initialDevices);
        console.log('当前设备ID:', curDeviceID);
        
        // 确保所有初始设备状态为离线
        for (let deviceId in initialDevices) {
            initialDevices[deviceId].status = 'offline';
        }
        
        // 先创建socket实例
        this.socket = io();
        
        // 再创建LogManager实例
        this.logManager = new LogManager(this.socket);
        
        // 最后注册事件监听
        this.socket.on('connect', () => {
            console.log('控制台已连接');
            this.logManager.addLog('i', 'SYSTEM', '控制台初始化完成');
        });
        
        this.logManager.setCallbacks({
            onLogsUpdated: (logs) => {
                this.systemLogs = logs;
            },
            onStatsUpdated: (stats) => {
                this.logStats = stats;
            }
        });
        
        this.app = new Vue({
            el: '#app',
            delimiters: ['[[', ']]'],
            data: {
                devices: initialDevices || {},  // 使用处理过的初始设备数据
                selectedDevice: curDeviceID || null,  // 使用服务器传来的当前设备ID
                commandInput: '',
                cmdHistoryCache: [],  // 命令日志缓存
                historyIndex: -1,
                lastActivityTime: Date.now(),
                showLogs: curDeviceID ? true : false,  // 如果有当前设备就显示日志
                logsPage: 1,
                loadingLogs: false,
                hasMoreLogs: false,
                isRealtime: true,  // 是否实时显示
                logsPanelWidth: '33.33%',  // 日志面板宽度
                isResizing: false,         // 是否正在调整大小
                startX: 0,                 // 开始拖动的X坐标
                startWidth: 0,             // 开始拖动时的宽度
                logFilter: '',             // 日志过滤字符串
                activeFilter: false,       // 是否有激活的过滤器
                filterType: '',            // 过滤器类型
                filterValue: '',           // 过滤值
                filterRegex: null,         // 正则表达式过滤器
                logDate: new Date().toISOString().split('T')[0], // 当前日期
                availableDates: [new Date().toISOString().split('T')[0]], // 默认只有当前日期
                filteredLogs: [],
                isScrolling: false,
                _scrollTimeout: null,
                _tempCommand: undefined,
                selectedDevices: [], // 存储选中的设备ID列表
                multiDeviceActionDisabled: false,
                showBatchActions: false,
                selectedCount: 0,
                lastSelectedIndex: -1,
            },
            methods: {
                formatTime(time) {
                    return time || '未知';
                },
                selectDevice(deviceId, multiSelect = false) {
                    if (multiSelect) {
                        const index = this.selectedDevices.indexOf(deviceId);
                        if (index !== -1) {
                            // 已选中，则取消选择
                            this.selectedDevices.splice(index, 1);
                            if (this.selectedDevice === deviceId) {
                                this.selectedDevice = this.selectedDevices.length > 0 ? 
                                    this.selectedDevices[0] : null;
                            }
                        } else {
                            // 未选中，则添加到选择
                            this.selectedDevices.push(deviceId);
                            this.selectedDevice = deviceId;
                        }
                    } else {
                        // 单击模式
                        if (this.selectedDevices.length === 1 && this.selectedDevices[0] === deviceId) {
                            // 如果只有这一个设备被选中，则取消选择
                            this.selectedDevices = [];
                            this.selectedDevice = null;
                        } else {
                            // 否则选中这个设备
                            this.selectedDevice = deviceId;
                            this.selectedDevices = [deviceId];
                        }
                    }
                    
                    this.updateDeviceSelectionUI();
                },
                updateDeviceSelectionUI() {
                    // 使用原生 DOM API 替代 jQuery
                    document.querySelectorAll('.device-card').forEach(card => {
                        card.classList.remove('selected');
                    });
                    
                    this.selectedDevices.forEach(deviceId => {
                        const card = document.querySelector(`.device-card[data-device-id="${deviceId}"]`);
                        if (card) {
                            card.classList.add('selected');
                        }
                    });
                    
                    // 更新操作按钮状态
                    const multiDeviceActions = document.querySelectorAll('.multi-device-action');
                    const batchActions = document.querySelectorAll('.batch-action');
                    
                    if (this.selectedDevices.length > 0) {
                        multiDeviceActions.forEach(el => el.classList.remove('disabled'));
                        
                        // 如果选择了多个设备，显示批量操作按钮
                        if (this.selectedDevices.length > 1) {
                            batchActions.forEach(el => el.style.display = 'inline-block');
                        } else {
                            batchActions.forEach(el => el.style.display = 'none');
                        }
                    } else {
                        multiDeviceActions.forEach(el => el.classList.add('disabled'));
                        batchActions.forEach(el => el.style.display = 'none');
                    }
                    
                    // 更新选中设备计数
                    const selectedCountEl = document.getElementById('selected-count');
                    if (selectedCountEl) {
                        selectedCountEl.textContent = this.selectedDevices.length;
                    }
                },
                showFullScreenshot(device) {
                    if (device.status === 'online' && device.screenshot) {
                        this.fullScreenshot = device.screenshot;
                    }
                },
                updateLastActivity() {
                    this.lastActivityTime = Date.now();
                    this.showLogs = true;
                },
                handleBlur() {
                    setTimeout(() => {
                        const timeSinceLastActivity = Date.now() - this.lastActivityTime;
                        if (timeSinceLastActivity > 5000) {  // 5秒无活动
                            this.showLogs = false;
                        }
                    }, 200);
                },
                sendCommand() {
                    if (!this.commandInput) return;
                    
                    console.log('发送命令:', this.commandInput);
                    this.addCommandToHistory(this.commandInput);
                    
                    this.socket.emit('2S_Cmd', {
                        device_ids: this.selectedDevices,
                        command: this.commandInput,
                        params: {}
                    });
                    
                    this.commandInput = '';
                    this.historyIndex = -1;
                },
                handleOutsideClick() {
                    // 取消所有设备选择
                    this.selectedDevices = [];
                    this.updateDeviceSelectionUI();
                },
                handleLogsScroll(e) {
                    if(this.logManager) {
                        this.isScrolling = true;
                        this.logManager.handleScroll(e);
                        
                        clearTimeout(this._scrollTimeout);
                        this._scrollTimeout = setTimeout(() => {
                            this.isScrolling = false;
                        }, 200);
                    }
                    
                    const el = e.target;
                    if (!this.loadingLogs && el.scrollTop <= 30 && !this.isScrolling) {
                        this.loadMoreLogs();
                    }
                },
                loadMoreLogs() {
                    if (this.loadingLogs) return;
                    
                    this.loadingLogs = true;
                    this.logsPage++;
                    
                    this.socket.emit('B2S_GetLogs', {
                        device_id: this.selectedDevice,
                        page: this.logsPage
                    });
                },
                parseLogLine(line) {
                    // 解析日志行，提取时间、标签、级别和消息
                    const match = line.match(/^\[(.*?)\]\s+(\w+)\s+(\w+):\s+(.*)$/);
                    if (match) {
                        return {
                            time: match[1],
                            level: match[2].toLowerCase(),
                            tag: match[3],
                            message: match[4]
                        };
                    }
                    return null;
                },
                toggleLogs() {
                    this.showLogs = !this.showLogs;
                    if (this.showLogs) {
                        // 如果是打开日志，重置宽度为默认值
                        this.logsPanelWidth = '33.33%';
                    }
                },
                updateDeviceTask(data) {
                    const device = this.devices[data.deviceId];
                    if (device) {
                        // 更新任务信息
                        const task = data.task;
                        if (task) {
                            task.progress = Math.min(task.progress, 1);
                            device.currentTask = task;
                        } else {
                            device.currentTask = null;
                        }
                        
                        // 更新分数信息
                        if (data.todayTaskScore !== undefined) {
                            device.todayTaskScore = data.todayTaskScore;
                        }
                        if (data.totalScore !== undefined) {
                            device.totalScore = data.totalScore;
                        }
                        
                        this.$nextTick(() => {
                            const taskInfo = document.querySelector(`#device-${data.deviceId} .task-info`);
                            if (taskInfo) {
                                // 任务名区域点击处理
                                const progressArea = taskInfo.querySelector('.task-header');
                                if (progressArea && !task.completed) {
                                    progressArea.style.cursor = 'pointer';
                                    progressArea.onclick = (e) => {
                                        e.stopPropagation();

                                    };
                                }

                                // 日期区域点击处理
                                const statsArea = taskInfo.querySelector('.task-date');
                                if (statsArea) {
                                    statsArea.style.cursor = 'pointer';
                                    statsArea.onclick = (e) => {
                                        e.stopPropagation();
                                        const datePicker = document.createElement('input');
                                        datePicker.type = 'date';
                                        datePicker.onchange = (e) => {
                                            const selectedDate = e.target.value;
                                            this.socket.emit('2S_Cmd', {
                                                device_id: data.deviceId,
                                                command: `date ${selectedDate}`
                                            });
                                            datePicker.remove();
                                        };
                                        // 添加到DOM并触发点击
                                        document.body.appendChild(datePicker);
                                        datePicker.click();
                                    };
                                }
                                // 进度区域点击处理
                                const taskProgress = taskInfo.querySelector('.task-progress');
                                if (taskProgress) {
                                    taskProgress.style.cursor = 'pointer';
                                    taskProgress.onclick = (e) => {
                                        e.stopPropagation();
                                        if (task.state === 'running') {
                                            console.log("stop task")
                                            this.socket.emit('2S_Cmd', {
                                                device_id: data.deviceId,
                                                command: 'stop'
                                            });
                                        } else if (task.state === 'paused') {
                                            console.log("resume task")
                                            this.socket.emit('2S_Cmd', {
                                                device_id: data.deviceId,
                                                command: 'resume'  
                                            });
                                        }
                                    };
                                }
                                // 任务统计区域点击处理
                                const taskStats = taskInfo.querySelector('.task-stats');
                                if (taskStats) {
                                    taskStats.style.cursor = 'pointer';
                                    taskStats.onclick = (e) => {
                                        e.stopPropagation();
                                        this.socket.emit('2S_Cmd', {
                                            device_id: data.deviceId,
                                            command: 'tasks'
                                        });
                                    };
                                }
                            }
                        });

                        this.$set(device, 'currentTask', task);
                        this.$nextTick(() => {
                            const progressRefs = this.$refs[`progress-${data.deviceId}`];
                            if (progressRefs && progressRefs[0]) {
                                this.drawProgress(data.deviceId, task.progress, task.state === 'running');
                            }
                        });
                    }
                },
                drawProgress(deviceId, progress, isRunning) {
                    const canvas = this.$refs[`progress-${deviceId}`][0];
                    if (!canvas) return;
                    
                    const ctx = canvas.getContext('2d');
                    const centerX = canvas.width / 2;
                    const centerY = canvas.height / 2;
                    const radius = Math.min(centerX, centerY) - 2;
                    
                    // 清除画布
                    ctx.clearRect(0, 0, canvas.width, canvas.height);
                    
                    // 绘制完整的灰色圆
                    ctx.beginPath();
                    ctx.arc(centerX, centerY, radius, 0, Math.PI * 2);
                    ctx.fillStyle = 'rgba(200, 200, 200, 0.2)';
                    ctx.fill();
                    
                    // 绘制进度扇形
                    if (progress > 0) {
                        ctx.beginPath();
                        ctx.moveTo(centerX, centerY);
                        ctx.arc(centerX, centerY, radius, 
                               -Math.PI / 2, 
                               (-Math.PI / 2) + (Math.PI * 2 * progress));
                        ctx.lineTo(centerX, centerY);
                        ctx.fillStyle = isRunning ? '#4CAF50' : '#808080';
                        ctx.fill();
                    }
                    
                    // 绘制进度文本，转换为整数百分比
                    ctx.fillStyle = '#FFFFFF';
                    ctx.font = 'bold 14px Arial';
                    ctx.textAlign = 'center';
                    ctx.textBaseline = 'middle';
                    ctx.fillText(`${Math.round(progress * 100)}%`, centerX, centerY);
                },
                startResize(event) {
                    this.isResizing = true;
                    this.startX = event.clientX;
                    this.startWidth = parseInt(this.logsPanelWidth);
                    
                    // 添加鼠标移动和松开事件监听
                    document.addEventListener('mousemove', this.doResize);
                    document.addEventListener('mouseup', this.stopResize);
                    
                    // 防止文本选择
                    event.preventDefault();
                },
                doResize(event) {
                    if (!this.isResizing) return;
                    
                    // 计算新宽度
                    const offsetX = event.clientX - this.startX;
                    const newWidth = Math.max(20, Math.min(80, this.startWidth - offsetX / window.innerWidth * 100));
                    
                    // 更新宽度
                    this.logsPanelWidth = `${newWidth}%`;
                    
                    // 通知日志管理器宽度变化
                    if (this.logManager) {
                        this.logManager.setWidth(this.logsPanelWidth);
                    }
                },
                stopResize() {
                    this.isResizing = false;
                    
                    // 移除事件监听
                    document.removeEventListener('mousemove', this.doResize);
                    document.removeEventListener('mouseup', this.stopResize);
                },
                applyLogFilter() {
                    const filter = this.logFilter.trim();
                    
                    if (!filter) {
                        // 清除过滤器
                        this.activeFilter = false;
                        this.filterType = '';
                        this.filterValue = '';
                        this.filterRegex = null;
                        return;
                    }
                    
                    this.activeFilter = true;
                    
                    // 根据首字符确定过滤类型
                    if (filter.startsWith('@')) {
                        // 设备名过滤
                        this.filterType = '@';
                        this.filterValue = filter.substring(1).trim();
                    } else if (filter.startsWith(':')) {
                        // TAG过滤
                        this.filterType = ':';
                        this.filterValue = filter.substring(1).trim();
                    } else if (filter.startsWith('*')) {
                        // 正则表达式过滤
                        this.filterType = '*';
                        this.filterValue = filter.substring(1).trim();
                        try {
                            this.filterRegex = new RegExp(this.filterValue, 'i');
                        } catch (e) {
                            console.error('无效的正则表达式:', e);
                            this.logManager.addLog('e', 'Filter', `无效的正则表达式: ${e.message}`);
                            this.filterRegex = null;
                        }
                    } else {
                        // 文本过滤
                        this.filterType = 'text';
                        this.filterValue = filter;
                    }
                },
                loadLogsByDate(event) {
                    const date = event.target.value;
                    this.logManager.loadLogs(date);
                },
                clearLogs() {
                    this.logManager.clearLogs();
                },
                renderLog(log) {
                    // 统一处理所有日志
                    const logClass = `log-${log.level}`;
                    return `
                        <div class="${logClass}">
                            ${log.message}
                        </div>
                    `;
                },
                handleKeydown(e) {
                    const history = this.logManager.getCommandHistory();
                    const historyLength = history.length;
                    if (historyLength === 0) {
                        return;
                    }
                    
                    // 处理方向键导航
                    if (e.key === 'ArrowUp' || e.key === 'ArrowDown') {
                        // 暂存未发送的命令
                        if (this._tempCommand === undefined) {
                            this._tempCommand = this.commandInput;
                        }
                        
                        // 计算新索引
                        let newIndex = this.historyIndex;
                        if (e.key === 'ArrowUp') {
                            newIndex = Math.min(newIndex + 1, historyLength - 1);
                        } else {
                            newIndex = Math.max(newIndex - 1, -1);
                        }
                        
                        // 更新命令输入
                        if (newIndex >= 0) {
                            this.commandInput = history[newIndex];
                        } else {
                            this.commandInput = this._tempCommand || '';
                        }
                        
                        this.historyIndex = newIndex;
                        e.preventDefault();
                    }
                },
                handleSocketEvents() {
                    this.socket = io();                    

                },
                // 处理设备状态更新
                handleDeviceUpdate(device) {
                    if (device.status === 'online') {
                        this.$set(this.devices, device.id, device);
                        // 添加上线日志
                        this.logManager.addLog('i', 'SYSTEM', `${device.id} 已上线`);
                    } else if (device.status === 'offline') {
                        // 添加离线日志
                        this.logManager.addLog('w', 'SYSTEM', `${device.id} 已离线`);
                    }
                },
                
                // 处理截图更新
                handleScreenshotUpdate(data) {
                    if (this.devices[data.device_id]) {
                        this.devices[data.device_id].screenshot = data.screenshot;
                        // 添加截图日志
                        this.logManager.addLog('i', 'SCREEN', `${data.device_id} 截图已更新`);
                    }
                },
                
                // 处理错误信息
                handleError(error) {
                    console.error('发生错误:', error);
                    // 添加错误日志
                    this.logManager.addLog('e', 'ERROR', error.message || error);
                },
                addCommandToHistory(command) {
                    if (this.cmdHistoryCache.length >= 100) {
                        this.cmdHistoryCache.shift();
                    }
                    this.cmdHistoryCache.push(command);
                    this.historyIndex = this.cmdHistoryCache.length - 1;
                },
                handleGlobalClick(event) {
                    // 检查点击是否在设备列表区域内的空白处
                    const devicesContainer = document.querySelector('.devices-container');
                    const isInsideDevicesContainer = devicesContainer && devicesContainer.contains(event.target);
                    
                    // 检查是否点击了设备卡片
                    const isDeviceCard = event.target.closest('.device-card');
                    
                    // 检查是否点击了其他UI元素（按钮、日志窗口等）
                    const isOtherUIElement = event.target.closest('.console-window') || 
                                            event.target.closest('button') ||
                                            event.target.closest('.logs-section') ||
                                            event.target.closest('.logs-toggle');
                    
                    // 只有当点击在设备列表区域内的空白处时，才清除设备选择
                    if (isInsideDevicesContainer && !isDeviceCard && !isOtherUIElement) {
                        // 清除所有设备选择
                        this.selectedDevices = [];
                        this.selectedDevice = null;
                        this.updateDeviceSelectionUI();
                    }
                },
                handleDeviceClick(deviceId, event) {
                    event.stopPropagation();
                    
                    // 获取所有设备ID的数组，用于确定索引
                    // 注意：需要确保设备顺序与DOM中的顺序一致
                    const deviceCards = document.querySelectorAll('.device-card');
                    const deviceIds = Array.from(deviceCards).map(card => card.getAttribute('data-device-id'));
                    const currentIndex = deviceIds.indexOf(deviceId);
                    
                    // 右键点击 - 取消所有选择
                    if (event.button === 2) {
                        this.selectedDevices = [];
                        this.selectedDevice = null;
                        this.updateDeviceSelectionUI();
                        event.preventDefault();
                        return false;
                    }
                    
                    // Shift键 - 连续选择
                    if (event.shiftKey && this.lastSelectedIndex >= 0 && this.lastSelectedIndex !== currentIndex) {
                        const start = Math.min(this.lastSelectedIndex, currentIndex);
                        const end = Math.max(this.lastSelectedIndex, currentIndex);
                        
                        // 清除当前选择
                        this.selectedDevices = [];
                        
                        // 选择范围内的所有设备
                        for (let i = start; i <= end; i++) {
                            if (i < deviceIds.length) {
                                this.selectedDevices.push(deviceIds[i]);
                            }
                        }
                        
                        // 设置当前设备为最后点击的设备
                        this.selectedDevice = deviceId;
                    } 
                    // Ctrl键 - 多选
                    else if (event.ctrlKey) {
                        const index = this.selectedDevices.indexOf(deviceId);
                        if (index !== -1) {
                            // 已选中，则取消选择
                            this.selectedDevices.splice(index, 1);
                            if (this.selectedDevice === deviceId) {
                                this.selectedDevice = this.selectedDevices.length > 0 ? 
                                    this.selectedDevices[0] : null;
                            }
                        } else {
                            // 未选中，则添加到选择
                            this.selectedDevices.push(deviceId);
                            this.selectedDevice = deviceId;
                        }
                    } 
                    // 普通点击 - 单选或取消选择
                    else {
                        if (this.selectedDevices.length === 1 && this.selectedDevices[0] === deviceId) {
                            // 如果只有这一个设备被选中，则取消选择
                            this.selectedDevices = [];
                            this.selectedDevice = null;
                        } else {
                            // 否则选中这个设备
                            this.selectedDevice = deviceId;
                            this.selectedDevices = [deviceId];
                        }
                    }
                    
                    // 更新最后选中的索引
                    this.lastSelectedIndex = currentIndex;
                    
                    // 更新UI
                    this.updateDeviceSelectionUI();
                    
                    // 防止默认行为和冒泡
                    event.preventDefault();
                }
            },
            computed: {
                filterClass() {
                    switch(this.filterType) {
                        case '@': return 'filter-device';
                        case ':': return 'filter-tag';
                        case '*': return 'filter-regex';
                        default: return 'filter-text';
                    }
                }
            },
            mounted() {
                // 连接到服务器，并标识为控制台
                this.socket = io({
                    query: {
                        client_type: 'console'
                    }
                });
                console.log('Vue: 创建 socket 实例');
                
                // 创建日志管理器，传入 socket 实例
                this.logManager = new LogManager(this.socket);
                console.log('Vue: 创建 LogManager 实例');
                
                // 设置回调
                this.logManager.setCallbacks({
                    onLogsUpdated: (logs, loading) => {
                        console.log(`日志更新回调: ${logs.length} 条日志, 加载状态: ${loading}`);
                        // 直接更新 Vue 数据
                        this.filteredLogs = [...logs];
                        this.loadingLogs = loading;
                    },
                    onScrollStateChanged: (isScrolling) => {
                        this.isScrolling = isScrolling;
                    }
                });
                
                // 添加调试日志
                this.socket.onAny((event, ...args) => {
                    console.log('收到Socket事件:', event, args);
                });
                
                this.socket.on('connect', () => {
                    console.log('控制台已连接到服务器');
                    this.logManager.addLog('i', 'Console', '控制台已连接到服务器');
                    // 初始获取日志数据
                    this.logManager.socket.emit('B2S_GetLogs');
                });
                
             
                this.socket.on('error', (data) => {
                    this.updateLastActivity();
                    this.logManager.addLog('e', 'Error', data.message);
                });

                // 获取初始日志数据
                this.socket.emit('B2S_GetLogs');             

                // 设备状态变化处理
                this.socket.on('S2B_DeviceUpdate', (data) => {
                    console.log('设备状态更新:', data);
                    
                    // 更新 Vue 数据
                    if (this.devices[data.deviceId]) {
                        // 更新设备状态
                        this.$set(this.devices[data.deviceId], 'status', data.status);
                        
                        // 如果有截图数据,更新截图
                        if (data.screenshot) {
                            this.$set(this.devices[data.deviceId], 'screenshot', data.screenshot);
                        }
                    }
                    
                    // 更新设备卡片的离线状态
                    const deviceCard = document.querySelector(`[data-device-id="${data.deviceId}"]`);
                    if (deviceCard) {
                        if (data.status === 'offline') {
                            deviceCard.classList.add('offline');
                        } else {
                            deviceCard.classList.remove('offline');
                        }
                    }
                });

                // 任务更新
                this.socket.on('S2B_TaskUpdate', (data) => {
                    console.log('收到任务更新:', data);
                    const deviceId = data.deviceId;                    
                    if (this.devices[deviceId]) {
                        // 使用updateDeviceTask处理任务更新
                        this.updateDeviceTask(data);
                    }
                });

                // 连接状态日志
                this.socket.on('disconnect', () => {
                    console.log('控制台已断开连接');
                    this.logManager.addLog('w', 'Console', '控制台已断开连接');
                });

                this.socket.on('connect_error', (error) => {
                    console.error('连接错误:', error);
                    this.logManager.addLog('e', 'Console', `连接错误: ${error.message}`);
                });

                // 添加窗口大小变化监听
                window.addEventListener('resize', () => {
                    if (this.isResizing) {
                        this.stopResize();
                    }
                });

                // 接收可用的日志日期
                this.socket.on('S2B_AvailableDates', (data) => {
                    if (data.dates && Array.isArray(data.dates)) {
                        this.app.availableDates = data.dates;
                    }
                });

                // 在 mounted 中添加事件监听
                this.socket.on('S2B_SetCurDev', (data) => {
                    console.log('服务器设置当前设备:', data);
                    if (data.device_id) {
                        // 更新选中状态
                        this.selectedDevice = data.device_id;
                        // 显示日志面板
                        this.showLogs = true;
                    }
                });

                // 在 mounted 中添加事件监听
                this.socket.on('S2B_UpdateSelection', (data) => {
                    console.log('服务器更新设备选择:', data);
                    if (data.device_ids) {
                        // 更新选中状态
                        this.selectedDevices = data.device_ids;
                        this.selectedDevice = data.device_ids.length > 0 ? data.device_ids[0] : null;
                        // 更新UI
                        this.updateDeviceSelectionUI();
                    }
                });

                // 验证实例是否创建成功
                if (!this.logManager.addLog) {
                    console.error('LogManager实例创建失败，请检查socket连接');
                }

                // 获取日志容器元素
                this.logsContainer = document.querySelector('.console-logs');
                if (this.logManager && this.logsContainer) {
                    this.logManager._logContainer = this.logsContainer;
                }

                // 添加全局点击事件监听器
                document.addEventListener('click', this.handleGlobalClick);
            },
            beforeDestroy() {
                // 组件销毁前移除事件监听器
                document.removeEventListener('click', this.handleGlobalClick);
            }
        });
    }
}

// 设备选择相关变量
let selectedDevices = [];
let lastSelectedIndex = -1;

/**
 * 初始化设备选择功能
 */
function initDeviceSelection() {
    // 为设备列表添加点击事件
    $(document).on('click', '.device-item', function(e) {
        const deviceId = $(this).data('device-id');
        const index = $(this).index();
        
        // 右键点击 - 取消所有选择
        if (e.button === 2) {
            clearDeviceSelection();
            e.preventDefault();
            return false;
        }
        
        // Shift键 - 连续选择
        if (e.shiftKey && lastSelectedIndex >= 0) {
            clearDeviceSelection();
            const start = Math.min(lastSelectedIndex, index);
            const end = Math.max(lastSelectedIndex, index);
            
            $('.device-item').slice(start, end + 1).each(function() {
                const id = $(this).data('device-id');
                selectDevice(id, $(this));
            });
        } 
        // Ctrl键 - 多选
        else if (e.ctrlKey) {
            // 如果已选中，则取消选择
            if ($(this).hasClass('selected')) {
                deselectDevice(deviceId, $(this));
            } else {
                // 否则添加到选择
                selectDevice(deviceId, $(this));
            }
        } 
        // 普通点击 - 单选
        else {
            clearDeviceSelection();
            selectDevice(deviceId, $(this));
        }
        
        lastSelectedIndex = index;
        updateDeviceSelectionUI();
        e.preventDefault();
    });
    
    // 阻止设备列表的右键菜单
    $(document).on('contextmenu', '.device-item', function(e) {
        e.preventDefault();
        return false;
    });
}

/**
 * 选择设备
 * @param {string} deviceId 设备ID
 * @param {jQuery} $element 设备元素
 */
function selectDevice(deviceId, $element) {
    if (!selectedDevices.includes(deviceId)) {
        selectedDevices.push(deviceId);
        $element.addClass('selected');
    }
}

/**
 * 取消选择设备
 * @param {string} deviceId 设备ID
 * @param {jQuery} $element 设备元素
 */
function deselectDevice(deviceId, $element) {
    const index = selectedDevices.indexOf(deviceId);
    if (index !== -1) {
        selectedDevices.splice(index, 1);
        $element.removeClass('selected');
    }
}

/**
 * 清除所有设备选择
 */
function clearDeviceSelection() {
    selectedDevices = [];
    $('.device-item').removeClass('selected');
}

/**
 * 获取当前选中的设备ID列表
 * @returns {Array} 设备ID数组
 */
function getSelectedDevices() {
    return selectedDevices;
}

// 在页面加载完成后初始化
$(document).ready(function() {
    initDeviceSelection();
    
    // 添加批量操作按钮事件
    $('#batch-screenshot').click(function() {
        if (selectedDevices.length > 0) {
            batchTakeScreenshot(selectedDevices);
        }
    });
    
    $('#batch-refresh').click(function() {
        if (selectedDevices.length > 0) {
            batchRefreshDevices(selectedDevices);
        }
    });
});

/**
 * 批量截图
 * @param {Array} deviceIds 设备ID数组
 */
function batchTakeScreenshot(deviceIds) {
    deviceIds.forEach(deviceId => {
        $.post(`/api/device/${deviceId}/screenshot`, function(response) {
            showToast(response.message);
        });
    });
}

/**
 * 批量刷新设备
 * @param {Array} deviceIds 设备ID数组
 */
function batchRefreshDevices(deviceIds) {
    deviceIds.forEach(deviceId => {
        $.post(`/api/device/${deviceId}/refresh`, function(response) {
            showToast(response.message);
        });
    });
}

