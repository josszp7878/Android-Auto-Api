from datetime import datetime
import json
from flask import current_app
from .models import db

class CommandHistory(db.Model):
    """命令历史记录"""
    __tablename__ = 'command_history'
    
    id = db.Column(db.Integer, primary_key=True)
    sender = db.Column(db.String(64), nullable=False)  # 命令发起者
    target = db.Column(db.String(64))  # 命令响应者
    command = db.Column(db.Text, nullable=False)
    response = db.Column(db.Text)
    level = db.Column(db.String(20), default='info')
    created_at = db.Column(db.DateTime, default=datetime.now)

    def to_dict(self):
        """转换为字典格式,处理显示名称"""
        server_id = current_app.config['SERVER_ID']
        return {
            'id': self.id,
            'sender': 'S' if self.sender == server_id else self.sender,
            'target': 'S' if self.target == server_id else self.target,
            'command': self.command,
            'response': self.response,
            'level': self.level,
            'created_at': self.created_at
        }
    
    @classmethod
    def getHistory(cls, device_id, page, per_page):
        """获取设备的命令历史"""
        history = cls.query.filter(
            (cls.sender == device_id) | 
            (cls.target == device_id)
        ).order_by(cls.created_at.desc())\
         .paginate(page=page, per_page=per_page)
            
        commands = [cmd.to_dict() for cmd in history.items]
        print(f'找到 {len(commands)} 条历史记录')
            
        # 使用 DateTimeEncoder 序列化数据
        from .websocket import DateTimeEncoder
        response_data = json.loads(json.dumps({
            'commands': commands,
            'has_next': history.has_next,
            'total': history.total
        }, cls=DateTimeEncoder))
        
        return response_data 
    
    