@staticmethod
def handCmdResult(data):
    """处理命令响应"""
    try:
        result = data.get('result')
        device_id = data.get('device_id')
        command = data.get('command')
        cmdName = data.get('cmdName')  # 获取命令方法名
        sender = "@"
        level = result.split('#')[0] if '#' in result else 'i'
        
        deviceMgr = DeviceManager()
        
        # 根据命令方法名处理响应
        if cmdName == 'screenText':  # 使用方法名而不是命令文本判断
            if isinstance(result, str) and result.startswith('data:image'):
                device = deviceMgr.get_device(device_id)
                if device is None:
                    Log.e(f'设备 {device_id} 不存在')
                    return
                saved_path = device.saveScreenshot(result)
                if saved_path:
                    deviceMgr.emit2Console('S2B_UpdateScreenshot', {
                        'device_id': device_id,
                        'path': saved_path
                    })
                    result = f"截图已保存: {saved_path}"
                else:
                    result = "保存截图失败"
                    level = 'e'

        # 创建命令历史记录
        CommandHistory.create(
            sender=sender,
            target=device_id,
            command=command,
            level=level,
            response=result
        )
            
    except Exception as e:
        result = Log.formatEx('处理命令响应出错', e)
        
    deviceMgr.emit2Console('S2B_CmdResult', {
        'result': result,
        'level': level,
    }) 