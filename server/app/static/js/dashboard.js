class Dashboard {
    constructor(initialDevices) {
        console.log('初始化Dashboard，设备数据:', initialDevices);
        this.app = new Vue({
            el: '#app',
            delimiters: ['[[', ']]'],
            data: {
                devices: initialDevices || {},  // 确保有默认值
                selectedDevice: null,
                commandInput: '',
                commandLogs: [],
                showHistory: false,
                commandHistory: [],
                currentHistoryIndex: -1,
                lastActivityTime: Date.now(),
                currentPage: 1,
                hasMoreHistory: false,
                loadingHistory: false,
                activeTab: 'history',  // 当前激活的标签页
                systemLogs: [],        // 系统日志数据
                logsPage: 1,
                loadingLogs: false,
                hasMoreLogs: false,
                isRealtime: true,  // 是否实时显示
                logStats: {
                    start: 0,
                    end: 0,
                    total: 0
                }
            },
            methods: {
                formatTime(time) {
                    // 直接返回时间字符串
                    return time || '未知';
                },
                selectDevice(deviceId) {
                    const oldDevice = this.selectedDevice;
                    this.selectedDevice = this.selectedDevice === deviceId ? null : deviceId;
                    
                    if (this.selectedDevice) {  // 选中新设备
                        this.showHistory = true;
                        
                        // 通知后端设置当前设备ID
                        this.socket.emit('set_current_device', {
                            device_id: deviceId
                        });
                    } else if (oldDevice) {  // 取消选中设备
                        this.showHistory = false;
                    }
                },
                showFullScreenshot(device) {
                    if (device.status === 'online' && device.screenshot) {
                        this.fullScreenshot = device.screenshot;
                    }
                },
                toggleHistory() {
                    this.showHistory = !this.showHistory;
                },
                hideHistoryOnBlur(event) {
                    const recentActivity = this.commandLogs.length > 0 && 
                        Date.now() - this._lastActivityTime < 5000; // 5秒内的活动

                    const historyBtn = event.relatedTarget;
                    if (!historyBtn || !historyBtn.classList.contains('history-toggle')) {
                        if (!recentActivity) {
                            this.showHistory = false;
                        }
                    }
                },
                updateLastActivity() {
                    this.lastActivityTime = Date.now();
                    this.showHistory = true;
                },
                handleBlur() {
                    setTimeout(() => {
                        const timeSinceLastActivity = Date.now() - this.lastActivityTime;
                        if (timeSinceLastActivity > 5000) {  // 5秒无活动
                            this.showHistory = false;
                        }
                    }, 200);
                },
                keepHistoryOpen() {
                    this.updateLastActivity();
                },
                sendCommand() {
                    if (!this.commandInput) return;
                    
                    const isServerCommand = this.commandInput.startsWith('@');
                    const deviceId = isServerCommand ? '@' : this.selectedDevice;
                    
                    if (!isServerCommand) {
                        const device = this.devices[this.selectedDevice];
                        if (!device || device.status !== 'login') {
                            this.addLog('e', 'Server', '设备离线，无法发送命令');
                            return;
                        }
                    }

                    // 立即添加命令到历史记录
                    const currentTime = new Date().toLocaleString('zh-CN', {
                        year: 'numeric',
                        month: '2-digit',
                        day: '2-digit',
                        hour: '2-digit',
                        minute: '2-digit',
                        second: '2-digit',
                        hour12: false
                    });

                    this.commandLogs.push({
                        timestamp: currentTime,
                        sender: 'Server',
                        target: this.selectedDevice,
                        command: this.commandInput,
                        response: '',
                        level: 'i'
                    });

                    this.updateLastActivity();
                    this.socket.emit('B2S_DoCmd', {
                        device_id: deviceId,
                        command: this.commandInput
                    });

                    // 保存到命令历史
                    this.commandHistory.push(this.commandInput);
                    this.currentHistoryIndex = this.commandHistory.length;
                    
                    // 清空输入
                    this.commandInput = '';
                    // 发送命令后滚动到底部
                    setTimeout(() => this.scrollToBottom(), 100);
                },
                prevCommand() {
                    if (this.currentHistoryIndex > 0) {
                        this.currentHistoryIndex--;
                        this.commandInput = this.commandHistory[this.currentHistoryIndex];
                    }
                },
                nextCommand() {
                    if (this.currentHistoryIndex < this.commandHistory.length - 1) {
                        this.currentHistoryIndex++;
                        this.commandInput = this.commandHistory[this.currentHistoryIndex];
                    } else {
                        this.currentHistoryIndex = this.commandHistory.length;
                        this.commandInput = '';
                    }
                },
                addLog(tag, level, content) {
                    const log = {
                        tag,
                        level,
                        content
                    };
                    this.systemLogs.push(log);
                    this.$nextTick(() => {
                        const consoleEl = this.$refs.consoleLogs;
                        if (consoleEl) {
                            consoleEl.scrollTop = consoleEl.scrollHeight;
                        }
                    });
                },               
                addCmd(type, content, source) {
                    const cmd = {
                        type,
                        content,
                        source,
                        timestamp: new Date()
                    };
                    
                    this.commandLogs.push(cmd);
                    
                    this.$nextTick(() => {
                        const consoleEl = this.$refs.consoleHistory;
                        if (consoleEl) {
                            consoleEl.scrollTop = consoleEl.scrollHeight;
                        }
                    });
                },
                handleOutsideClick() {
                    if (this.showHistory) {
                        this.showHistory = false;
                    }
                },
                loadCommandHistory() {
                    if (this.loadingHistory || !this.selectedDevice) return;
                    
                    console.log('Loading history for device:', this.selectedDevice, 'page:', this.currentPage);
                    this.loadingHistory = true;
                    this.socket.emit('load_command_history', {
                        device_id: this.selectedDevice,
                        page: this.currentPage
                    });
                    // 首次加载时滚动到底部
                    if (this.currentPage === 1) {
                        setTimeout(() => this.scrollToBottom(), 100);
                    }
                },
                handleHistoryScroll(e) {
                    const el = e.target;
                    if (this.hasMoreHistory && 
                        !this.loadingHistory && 
                        el.scrollTop <= 30) {  // 接近顶部时加载更多
                        this.currentPage++;
                        this.loadCommandHistory();
                    }
                },
                handleLogsScroll(e) {
                    const el = e.target;
                    // 当滚动到顶部时加载更多日志
                    if (!this.loadingLogs && el.scrollTop <= 30) {
                        this.loadMoreLogs();
                    }
                },
                loadMoreLogs() {
                    if (this.loadingLogs) return;
                    
                    this.loadingLogs = true;
                    this.logsPage++;
                    
                    this.socket.emit('B2S_GetLogs', {
                        device_id: this.selectedDevice,
                        page: this.logsPage,
                        date: this.currentDate  // 添加日期参数
                    });
                },
                switchToLogs() {
                    this.activeTab = 'logs';
                    // 如果日志为空，重新获取
                    if (this.systemLogs.length === 0) {
                        this.socket.emit('B2S_GetLogs');
                    }
                    // 切换标签页后立即滚动到底部
                    this.$nextTick(() => {
                        this.scrollToBottom();
                    });
                },
                parseLogLine(logLine) {
                    // 使用##分隔符分割日志行
                    const parts = logLine.split('##');
                    if (parts.length === 4) {
                        const [time, tag, level, message] = parts;
                        return {
                            time,
                            tag,
                            level,
                            message
                        };
                    } else {
                        console.warn('无法解析日志行:', logLine);
                        return null;
                    }
                },
                updateLogs(logs, isRealtime = true) {
                    this.systemLogs = logs;
                    this.isRealtime = isRealtime;
                    setTimeout(() => this.scrollToBottom(), 100);
                },
                handleLogMessage(data) {
                    if (this.isRealtime) {
                        this.systemLogs.push({
                            time: data.time,  // 保持为字符串
                            level: data.level,
                            tag: data.tag,
                            message: data.message
                        });
                        this.updateLogs(this.systemLogs);
                    }
                },
                scrollToBottom() {
                    const consoleHistory = this.$refs.consoleHistory;
                    const consoleLogs = this.$refs.consoleLogs;
                    
                    // 禁用平滑滚动，直接跳转
                    if (this.activeTab === 'history' && consoleHistory) {
                        consoleHistory.style.scrollBehavior = 'auto';
                        consoleHistory.scrollTop = consoleHistory.scrollHeight;
                        consoleHistory.style.scrollBehavior = 'smooth';  // 恢复平滑滚动，用于用户手动滚动
                    } else if (this.activeTab === 'logs' && consoleLogs) {
                        consoleLogs.style.scrollBehavior = 'auto';
                        consoleLogs.scrollTop = consoleLogs.scrollHeight;
                        consoleLogs.style.scrollBehavior = 'smooth';
                    }
                },
                filterByCurrentDevice() {
                    if (this.selectedDevice) {
                        // 使用设备ID作为过滤条件
                        this.socket.emit('B2S_GetLogs', {
                            filter: this.selectedDevice
                        });
                    }
                },
                drawProgress(deviceId, progress, isRunning = true) {
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
                                            this.socket.emit('2S_Command', {
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
                                            this.socket.emit('2S_Command', {
                                                device_id: data.deviceId,
                                                command: 'stop'
                                            });
                                        } else if (task.state === 'paused') {
                                            console.log("resume task")
                                            this.socket.emit('2S_Command', {
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
                                        this.socket.emit('2S_Command', {
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
                }
            },
            mounted() {
                this._lastActivityTime = Date.now();
                
                // 连接到服务器，并标识为控制台
                this.socket = io({
                    query: {
                        client_type: 'console'
                    }
                });
                
                // 添加调试日志
                this.socket.onAny((event, ...args) => {
                    console.log('收到Socket事件:', event, args);
                });
                
                this.socket.on('connect', () => {
                    console.log('控制台已连接到服务器');
                    this.addLog('i', 'Console', '控制台已连接到服务器');
                    // 初始获取日志数据
                    this.socket.emit('B2S_GetLogs');
                    // 初始化时滚动到底部
                    this.$nextTick(this.scrollToBottom);
                });
                
                // this.socket.on('S2B_CmdResult', (data) => {
                //     const content = data.result || '';
                //     let level = data.level || 'i';
                    
                //     // 更新最后一条命令的响应
                //     if (this.commandLogs.length > 0) {
                //         const lastLog = this.commandLogs[this.commandLogs.length - 1];
                //         lastLog.response = content;
                //         lastLog.level = level;
                //     }
                    
                //     this.updateLastActivity();
                // });

                this.socket.on('error', (data) => {
                    this.updateLastActivity();
                    this.addCmd('response', data.message, this.selectedDevice);
                    this.loadingHistory = false;
                });

                this.socket.on('command_history', (data) => {
                    console.log('Received command history:', data);
                    const commands = data.commands;
                    this.hasMoreHistory = data.has_next;
                    
                    const logs = commands.map(cmd => {
                        // 解析响应level和内容
                        let level = 'i';
                        let content = cmd.response || '';
                        if(content.includes('##')) {
                            [level, content] = content.split('##');
                        }
                        
                        // 格式化时间
                        const timestamp = new Date(cmd.created_at).toLocaleString('zh-CN', {
                            year: 'numeric',
                            month: '2-digit',
                            day: '2-digit',
                            hour: '2-digit',
                            minute: '2-digit',
                            second: '2-digit',
                            hour12: false
                        });
                        
                        return {
                            timestamp: timestamp,
                            sender: cmd.sender,
                            target: cmd.target,
                            command: cmd.command,
                            response: content,
                            level: level
                        };
                    });
                    
                    // 更新命令历史
                    if (this.currentPage > 1) {
                        // 分页加载时，添加到现有历史
                        this.commandLogs = [...this.commandLogs, ...logs];
                    } else {
                        // 首次加载时，替换全部历史
                        this.commandLogs = logs;
                    }
                    
                    // 首次加载时滚动到底部
                    if (this.currentPage === 1) {
                        this.$nextTick(() => {
                            this.scrollToBottom();
                        });
                    }
                });

                this.socket.on('clear_history', (data) => {
                    const deviceId = data.device_id;
                    if (this.selectedDevice === deviceId) {
                        this.commandLogs = [];  // 清空当前设备的命令历史
                        console.log(`设备 ${deviceId} 的指令历史已清除`);
                    }
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
                    
                    // 滚动处理...
                });


                // 添加滚动到底部的处理
                this.socket.on('scroll_logs', () => {
                    this.$nextTick(() => {
                        const consoleEl = this.$refs.consoleLogs;
                        if (consoleEl) {
                            consoleEl.scrollTop = consoleEl.scrollHeight;
                        }
                    });
                });

                // 修改日志消息监听
                this.socket.on('S2B_AddLog', (data) => {
                    console.log('收到日志数据:', data);
                    const content = data.message;
                    const parsed = this.parseLogLine(content);
                    if (parsed) {
                        const log = {
                            time: parsed.time,
                            tag: parsed.tag,
                            level: parsed.level,
                            message: parsed.message
                        };
                        
                        // 使用 push 而不是 unshift
                        this.systemLogs.push(log);
                        
                        this.$nextTick(() => {
                            const consoleEl = this.$refs.consoleLogs;
                            if (consoleEl) {
                                consoleEl.scrollTop = consoleEl.scrollHeight;
                            }
                        });
                    } else {
                        console.warn('Failed to parse log:', content);
                    }
                });

                // 修改设备状态更新处理
                this.socket.on('S2B_DeviceUpdate', (data) => {
                    console.log('收到设备状态更新:', data);
                    if (!this.devices[data.deviceId]) {
                        // 创建新设备
                        this.$set(this.devices, data.deviceId, {
                            status: data.status || 'offline',
                            screenshot: data.screenshot || '/static/screenshots/default.jpg',  // 使用默认截图
                            screenshotTime: data.screenshotTime || '',
                            todayTaskScore: data.todayTaskScore || 0,
                            totalScore: data.totalScore || 0
                        });
                    } else {
                        // 更新现有设备
                        const device = this.devices[data.deviceId];
                        Object.keys(data).forEach(key => {
                            if (data[key] !== undefined) {
                                // 确保截图不为null
                                if (key === 'screenshot' && !data[key]) {
                                    data[key] = '/static/screenshots/default.jpg';
                                }
                                this.$set(device, key, data[key]);
                            }
                        });
                    }
                    
                    // 强制更新设备卡片的样式
                    this.$nextTick(() => {
                        const deviceCard = document.querySelector(`#device-${data.deviceId}`);
                        if (deviceCard) {
                            // 移除所有状态相关的类
                            deviceCard.classList.remove('offline', 'online', 'login');
                            // 添加当前状态的类
                            deviceCard.classList.add(data.status);
                            
                            // 更新背景图
                            const screenshot = data.screenshot || '/static/screenshots/default.jpg';
                            deviceCard.style.backgroundImage = `url(${screenshot})`;
                            deviceCard.style.backgroundColor = 'transparent';
                        }
                    });
                });

                this.socket.on('response', function(data) {
                    let result = data.result;
                    if (typeof result === 'string') {
                        // 将HTML换行转换为实际显示
                        result = result.replace(/<br>/g, '\n');
                    }
                    // 更新显示
                    console.log(result);
                });

                this.socket.on('clear_logs', () => {
                    // 清空系统日志显示
                    this.systemLogs = [];
                });

                // 更新日志统计信息
                this.socket.on('S2B_LogCount', (data) => {
                    this.logStats = {
                        start: data.start,
                        end: data.end,
                        total: data.total
                    };
                });

                // 更新设备卡片显示
                this.updateDeviceCard = function(deviceId) {
                    const device = this.devices[deviceId];
                    if (!device) return;

                    const cardElement = document.querySelector(`#device-${deviceId}`);
                    if (!cardElement) return;

                    // 更新任务状态显示
                    const taskStatusElement = cardElement.querySelector('.task-status');
                    if (taskStatusElement) {
                        if (device.currentTask) {
                            const task = device.currentTask;
                            taskStatusElement.innerHTML = `
                                <div class="task-info">
                                    <span class="task-name">${task.appName}/${task.taskName}</span>
                                    <div class="progress">
                                        <div class="progress-bar" role="progressbar" 
                                             style="width: ${task.progress}%" 
                                             aria-valuenow="${task.progress}" 
                                             aria-valuemin="0" 
                                             aria-valuemax="100">
                                            ${task.progress}%
                                        </div>
                                    </div>
                                </div>
                            `;
                        } else {
                            taskStatusElement.innerHTML = '<span class="no-task">无任务运行</span>';
                        }
                    }
                };
                // 统一处理任务更新事件
                this.socket.on('S2B_TaskUpdate', (data) => {
                    console.log('收到任务更新:', data);
                    const deviceId = data.deviceId;                    
                    if (this.devices[deviceId]) {
                        // 使用updateDeviceTask处理任务更新
                        this.updateDeviceTask(data);
                    }
                });

                // 添加连接状态日志
                this.socket.on('disconnect', () => {
                    console.log('控制台已断开连接');
                    this.addLog('w', 'Console', '控制台已断开连接');
                });

                this.socket.on('connect_error', (error) => {
                    console.error('连接错误:', error);
                    this.addLog('e', 'Console', `连接错误: ${error.message}`);
                });
            }
        });
    }
}

