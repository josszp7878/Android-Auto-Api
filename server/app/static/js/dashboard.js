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
                this.$nextTick(() => {
                    const container = this.$refs.consoleLogs;
                    if (container && this.logManager.autoScroll) {
                        container.scrollTop = container.scrollHeight;
                    }
                });
            },
            onStatsUpdated: (stats) => {
                this.logStats = stats;
            },
            onScrollToBottom: () => {
                this.scrollToBottom();
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
                _tempCommand: undefined
            },
            methods: {
                formatTime(time) {
                    return time || '未知';
                },
                selectDevice(deviceId) {
                    const oldDevice = this.selectedDevice;
                    this.selectedDevice = this.selectedDevice === deviceId ? null : deviceId;
                    
                    if (this.selectedDevice) {  // 选中新设备
                        this.showLogs = true;
                        
                        // 通知后端设置当前设备ID
                        this.socket.emit('B2S_SetCurDev', {
                            device_id: deviceId
                        });
                    } else if (oldDevice) {  // 取消选中设备
                        this.showLogs = false;
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
                    this.socket.emit('2S_Cmd', {
                        command: this.commandInput,
                        device_id: this.selectedDevice || '控制台'
                    });
                    this.historyIndex = -1;
                    this._tempCommand = undefined;
                    this.commandInput = '';
                    this.scrollToBottom();
                },
                handleOutsideClick() {
                    if (this.showLogs) {
                        this.showLogs = false;
                    }
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
                startResize(e) {
                    this.isResizing = true;
                    this.startX = e.clientX;
                    this.startWidth = parseFloat(this.logsPanelWidth);
                    
                    // 添加事件监听
                    document.addEventListener('mousemove', this.doResize);
                    document.addEventListener('mouseup', this.stopResize);
                    
                    // 防止选中文本
                    e.preventDefault();
                },
                doResize(e) {
                    if (!this.isResizing) return;
                    
                    // 计算新宽度
                    const windowWidth = window.innerWidth;
                    const dx = this.startX - e.clientX;
                    let newWidth = this.startWidth + (dx / windowWidth * 100);
                    
                    // 限制最小和最大宽度
                    newWidth = Math.max(20, Math.min(80, newWidth));
                    
                    // 更新宽度
                    this.logsPanelWidth = `${newWidth}%`;
                },
                stopResize() {
                    this.isResizing = false;
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
                scrollToBottom() {
                    this.$nextTick(() => {
                        const container = this.$refs.consoleLogs;
                        if (container) {
                            container.scrollTop = container.scrollHeight;
                            this.logManager.autoScroll = true;
                        }
                    });
                },
                handleSocketEvents() {
                    this.socket = io();
                    
                    // 接收新日志
                    this.socket.on('S2B_AddLog', (log) => {
                        this.logManager.addLog(log.level, log.tag, log.message);
                    });
                    
                    // 接收日志列表
                    this.socket.on('S2B_LoadLogs', (data) => {
                        this.logManager.parseAndFilterLogs();
                    });
                    
                    // 其他事件处理...
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
                    // 初始化时滚动到底部
                    this.$nextTick(this.scrollToBottom);
                });
                
                // // 命令结果处理
                // this.socket.on('S2B_CmdResult', (data) => {
                //     const content = data.result || '';
                //     let level = data.level || 'i';
                    
                //     // 添加到日志
                //     this.addLog(level, 'Command', content);
                    
                //     this.updateLastActivity();
                //     // 滚动到底部显示结果
                //     this.$nextTick(this.scrollToBottom);
                // });

                this.socket.on('error', (data) => {
                    this.updateLastActivity();
                    this.logManager.addLog('e', 'Error', data.message);
                });

                // 获取初始日志数据
                this.socket.emit('B2S_GetLogs');
                
                // 修改日志数据处理
                this.socket.on('S2B_RefreshLogs', (data) => {
                    console.log('收到日志数据:', data);
                    const logs = data.logs
                        .map(line => this.parseLogLine(line.trim()))
                        .filter(log => log !== null);
                        
                    if (this.logsPage > 1) {
                        // 分页加载时，将新日志添加到开头
                        this.systemLogs.unshift(...logs);
                    } else {
                        // 首次加载或刷新时，替换全部日志
                        this.systemLogs = logs;
                    }
                    
                    // 更新统计信息
                    this.logStats = {
                        start: data.start || 1,
                        end: data.end || this.systemLogs.length,
                        total: data.total || this.systemLogs.length
                    };
                    
                    this.loadingLogs = false;
                    this.hasMoreLogs = data.has_more;
                    
                    // 滚动到底部
                    this.$nextTick(this.scrollToBottom);
                });

                // 添加滚动到底部的处理
                this.socket.on('scroll_logs', () => {
                    this.$nextTick(this.scrollToBottom);
                });

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

                // 验证实例是否创建成功
                if (!this.logManager.addLog) {
                    console.error('LogManager实例创建失败，请检查socket连接');
                }
            }
        });
    }
}

