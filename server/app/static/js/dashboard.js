class Dashboard {
    constructor(initialDevices) {
        this.app = new Vue({
            el: '#app',
            delimiters: ['[[', ']]'],
            data: {
                devices: initialDevices,
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
            },
            methods: {
                formatTime(timestamp) {
                    if (!timestamp) return '未知';
                    // 如果是ISO格式字符串，先转换为Date对象
                    const date = typeof timestamp === 'string' ? new Date(timestamp) : timestamp;
                    return date.toLocaleString();
                },
                updateDeviceList(devices) {
                    console.log('设备列表更新:', devices);
                    const selected = this.selectedDevice;
                    this.devices = devices;
                    this.selectedDevice = selected;
                },
                selectDevice(deviceId) {
                    const oldDevice = this.selectedDevice;
                    this.selectedDevice = this.selectedDevice === deviceId ? null : deviceId;
                    
                    if (this.selectedDevice && this.selectedDevice !== oldDevice) {
                        this.commandLogs = [];  // 清空历史
                        this.currentPage = 1;   // 重置页码
                        this.showHistory = true;  // 显示历史窗口
                        this.loadCommandHistory();  // 加载新设备的历史
                        
                        // 通知后端设置当前设备ID
                        this.socket.emit('set_current_device', { device_id: this.selectedDevice });
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
                            this.addLog('response', '设备离线，无法发送命令', 'Server', 'error');
                            return;
                        }
                    }

                    this.updateLastActivity();
                    this.addLog('command', this.commandInput, 'Server');
                    this.socket.emit('send_command', {
                        device_id: deviceId,
                        command: this.commandInput
                    });

                    this.commandHistory.push(this.commandInput);
                    this.currentHistoryIndex = this.commandHistory.length;
                    
                    this.commandInput = '';
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
                addLog(type, content, source, level = 'info') {
                    const log = {
                        type,
                        content,
                        source,
                        level,
                        timestamp: new Date()
                    };

                    if (type === 'log') {
                        // 系统日志添加到 systemLogs
                        this.systemLogs.unshift(log);
                    } else {
                        // 命令历史添加到 commandLogs
                        this.commandLogs.push(log);
                    }

                    this.$nextTick(() => {
                        const consoleEl = type === 'log' ? 
                            this.$refs.consoleLogs : 
                            this.$refs.consoleHistory;
                        
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
                    if (this.hasMoreLogs && 
                        !this.loadingLogs && 
                        el.scrollTop <= 30) {
                        this.loadMoreLogs();
                    }
                },
                loadMoreLogs() {
                    if (this.loadingLogs) return;
                    
                    this.loadingLogs = true;
                    this.logsPage++;
                    
                    this.socket.emit('get_logs', {
                        page: this.logsPage
                    });
                },
                switchToLogs() {
                    this.activeTab = 'logs';
                    this.isRealtime = true;
                    // 清空现有日志
                    this.systemLogs = [];
                    // 重新获取最新日志
                    this.socket.emit('get_logs');
                },
                parseLogLine(line) {
                    const match = line.match(/\[(.*?)\] \[(.*?)\] (.*?): (.*)/);
                    if (match) {
                        return {
                            timestamp: match[1],
                            level: match[2],
                            source: match[3],
                            message: match[4]
                        };
                    }
                    return null;
                },
                updateLogs(logs, isRealtime = true) {
                    this.systemLogs = logs;
                    this.isRealtime = isRealtime;
                    
                    // 滚动到底部
                    this.$nextTick(() => {
                        const consoleEl = this.$refs.consoleLogs;
                        if (consoleEl) {
                            consoleEl.scrollTop = consoleEl.scrollHeight;
                        }
                    });
                },
                handleLogMessage(data) {
                    if (this.isRealtime) {
                        this.systemLogs.push({
                            timestamp: data.timestamp,
                            level: data.level,
                            source: data.source,
                            message: data.message
                        });
                        this.updateLogs(this.systemLogs);
                    }
                }
            },
            mounted() {
                this._lastActivityTime = Date.now();
                
                this.socket = io();
                this.socket.on('connect', () => {
                    console.log('连接到服务器');
                });
                
                this.socket.on('device_list_update', (devices) => {
                    this.updateDeviceList(devices);
                });

                this.socket.on('command_result', (data) => {
                    const resultText = data.result || '';
                    this.updateLastActivity();
                    let level = 'info';
                    if (resultText.toLowerCase().startsWith('error')) {
                        level = 'error';
                    } else if (resultText.toLowerCase().startsWith('warning')) {
                        level = 'warning';
                    }
                    this.addLog('response', resultText, data.device_id, level);
                });

                this.socket.on('error', (data) => {
                    this.updateLastActivity();
                    this.addLog('response', data.message, this.selectedDevice, 'error');
                    this.loadingHistory = false;  // 重置加载状态
                });

                this.socket.on('command_history', (data) => {
                    console.log('Received command history:', data);
                    const commands = data.commands;
                    this.hasMoreHistory = data.has_next;
                    
                    // 转换为日志格式
                    const logs = commands.map(cmd => {
                        const entries = [];
                        
                        // 添加命令
                        entries.push({
                            type: 'command',
                            content: cmd.command,
                            deviceId: cmd.sender,  // 显示发起者
                            timestamp: cmd.created_at
                        });
                        
                        // 如果有响应,添加响应记录
                        if (cmd.response) {
                            entries.push({
                                type: 'response',
                                content: cmd.response,
                                deviceId: cmd.target,  // 显示响应者
                                level: cmd.level,
                                timestamp: cmd.created_at
                            });
                        }
                        
                        return entries;
                    }).flat();
                    
                    // 按时间排序，确保最近的在最下面
                    logs.sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
                    
                    // 添加到历史记录
                    this.commandLogs.push(...logs);
                    this.loadingHistory = false;
                });

                this.socket.on('clear_history', (data) => {
                    const deviceId = data.device_id;
                    if (this.selectedDevice === deviceId) {
                        this.commandLogs = [];  // 清空当前设备的命令历史
                        console.log(`设备 ${deviceId} 的指令历史已清除`);
                    }
                });

                // 添加日志监听
                this.socket.on('log_message', (data) => {
                    console.log('收到日志消息:', data);  // 调试信息
                    this.addLog('log', data.message, data.source, data.level);
                });

                // 获取初始日志数据
                this.socket.emit('get_logs');
                
                // 修改日志数据处理
                this.socket.on('logs_data', (data) => {
                    const logs = data.logs
                        .map(line => this.parseLogLine(line))
                        .filter(log => log !== null);
                    this.updateLogs(logs, data.is_realtime);
                });

                // 修改实时日志处理
                this.socket.on('log_message', (data) => {
                    this.handleLogMessage(data);
                });

                // 修改日志显示处理
                this.socket.on('show_logs', (data) => {
                    const logs = data.logs
                        .map(line => this.parseLogLine(line))
                        .filter(log => log !== null);
                    this.updateLogs(logs, false);
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
            }
        });
    }
} 