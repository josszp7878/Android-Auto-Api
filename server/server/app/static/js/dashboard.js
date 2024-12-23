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
                lastActivityTime: Date.now()
            },
            methods: {
                formatTime(timestamp) {
                    if (!timestamp) return '未知';
                    return new Date(timestamp).toLocaleString();
                },
                updateDeviceList(devices) {
                    console.log('设备列表更新:', devices);
                    const selected = this.selectedDevice;
                    this.devices = devices;
                    this.selectedDevice = selected;
                },
                selectDevice(deviceId) {
                    this.selectedDevice = this.selectedDevice === deviceId ? null : deviceId;
                    this.showHistory = false;
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
                    if (!this.commandInput || !this.selectedDevice) return;
                    
                    const device = this.devices[this.selectedDevice];
                    if (!device || device.status !== 'login') {
                        this.addLog('error', '设备离线，无法发送命令');
                        return;
                    }

                    this.updateLastActivity();
                    this.addLog('command', this.commandInput, this.selectedDevice);
                    this.socket.emit('send_command', {
                        device_id: this.selectedDevice,
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
                addLog(type, content, deviceId = null) {
                    this.commandLogs.push({ type, content, deviceId });
                    if (type === 'response' || type === 'error') {
                        this.updateLastActivity();
                    }
                    this.$nextTick(() => {
                        const consoleHistory = this.$refs.consoleHistory;
                        if (consoleHistory) {
                            consoleHistory.scrollTop = consoleHistory.scrollHeight;
                        }
                    });
                },
                handleOutsideClick() {
                    if (this.showHistory) {
                        this.showHistory = false;
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
                    this.addLog('response', resultText);
                });

                this.socket.on('error', (data) => {
                    this.updateLastActivity();
                    this.addLog('error', data.message);
                });
            }
        });
    }
} 