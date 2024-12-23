class Dashboard {
    constructor(initialDevices) {
        this.app = new Vue({
            el: '#app',
            delimiters: ['[[', ']]'],
            data: {
                devices: initialDevices,
                selectedDevice: null,
                fullScreenshot: null,
                commandInput: '',
                commandLogs: []
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
                },
                showFullScreenshot(device) {
                    if (device.status === 'online' && device.screenshot) {
                        this.fullScreenshot = device.screenshot;
                    }
                },
                sendCommand() {
                    if (!this.commandInput || !this.selectedDevice) return;
                    const device = this.devices[this.selectedDevice];
                    if (!device || device.status !== 'login') {
                        this.addLog('error', '设备离线，无法发送命令');
                        return;
                    }
                    this.addLog('command', this.commandInput, this.selectedDevice);
                    this.socket.emit('send_command', {
                        device_id: this.selectedDevice,
                        command: this.commandInput
                    });
                    this.commandInput = '';
                },
                addLog(type, content, deviceId = null) {
                    this.commandLogs.push({ type, content, deviceId });
                    this.$nextTick(() => {
                        const consoleHistory = this.$refs.consoleHistory;
                        consoleHistory.scrollTop = consoleHistory.scrollHeight;
                    });
                }
            },
            mounted() {
                this.socket = io();
                this.socket.on('connect', () => {
                    console.log('连接到服务器');
                });
                
                this.socket.on('device_list_update', (devices) => {
                    this.updateDeviceList(devices);
                });

                this.socket.on('command_result', (data) => {
                    const resultText = data.result || '';
                    this.addLog('response', resultText);
                });

                this.socket.on('error', (data) => {
                    this.addLog('error', data.message);
                });
            }
        });
    }
} 