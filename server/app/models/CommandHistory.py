class CommandHistory(db.Model):
    __tablename__ = 'commandHistory'
    
    id = db.Column(db.Integer, primary_key=True)
    sender = db.Column(db.String(50))
    target = db.Column(db.String(50))
    command = db.Column(db.Text)
    response = db.Column(db.Text)
    level = db.Column(db.String(10))
    created_at = db.Column(db.DateTime, default=datetime.now)
    response_time = db.Column(db.DateTime)  # 新增响应时间字段
    
    @staticmethod
    def create(sender, target, command, level='info'):
        """创建命令历史记录"""
        history = CommandHistory(
            sender=sender,
            target=target,
            command=command,
            level=level,
            created_at=datetime.now()
        )
        db.session.add(history)
        db.session.commit()
        return history 