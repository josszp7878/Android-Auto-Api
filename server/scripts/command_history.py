from datetime import datetime
from SDatabase import db


class CommandHistory(db.Model):
    """命令历史记录"""
    __tablename__ = 'command_history'
    
    id = db.Column(db.Integer, primary_key=True)
    sender = db.Column(db.String(50), nullable=False)  # 发送者ID
    target = db.Column(db.String(50), nullable=False)  # 目标设备ID
    command = db.Column(db.Text, nullable=False)       # 命令内容
    response = db.Column(db.Text)                      # 响应内容
    level = db.Column(db.String(10))                   # 日志级别
    created_at = db.Column(db.DateTime, default=datetime.now)  # 创建时间
    response_time = db.Column(db.DateTime)             # 响应时间

    @classmethod
    def create(cls, sender, target, command, level='info', response=None):
        """创建新的命令记录"""
        history = cls(
            sender=sender,
            target=target,
            command=command,
            level=level,
            response=response,
            response_time=datetime.now()
        )
        db.session.add(history)
        db.session.commit()
        return history

    def update_response(self, response):
        """更新命令响应"""
        self.response = response
        self.response_time = datetime.now()
        db.session.commit()

    @staticmethod
    def getHistory(device_id, page=1, per_page=30):
        """获取设备的命令历史
        Args:
            device_id: 设备ID
            page: 页码
            per_page: 每页数量
        Returns:
            dict: {
                'commands': [...],  # 命令列表
                'has_next': bool    # 是否有下一页
            }
        """
        # 查询该设备相关的所有命令
        query = CommandHistory.query.filter(
            (CommandHistory.sender == device_id) | 
            (CommandHistory.target == device_id)
        ).order_by(CommandHistory.created_at.desc())
        
        # 分页
        offset = (page - 1) * per_page
        commands = query.offset(offset).limit(per_page + 1).all()
        
        # 检查是否有下一页
        has_next = len(commands) > per_page
        if has_next:
            commands = commands[:-1]  # 移除多查询的一条
        
        # 转换为字典格式
        result = []
        for cmd in commands:
            result.append({
                'id': cmd.id,
                'sender': cmd.sender,
                'target': cmd.target,
                'command': cmd.command,
                'response': cmd.response,
                'level': cmd.level,
                'created_at': cmd.created_at.isoformat(),
                'response_time': (cmd.response_time.isoformat() 
                               if cmd.response_time else None)
            })
            
        return {
            'commands': result,
            'has_next': has_next
        }


    @classmethod
    def add(cls, command_id, result, device_id):
        """处理命令执行结果"""
        try:
            print(f"@@@@@ command_id= {command_id}")
            if command_id:
                cmd = cls.query.get(command_id)
                if cmd:
                    # 格式化响应
                    cmd.update_response(result)
            return True 
        except Exception as e:
            import _Log
            _Log._Log_.ex(e, '处理命令结果出错')
            return False
    
    