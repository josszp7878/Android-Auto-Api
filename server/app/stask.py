from datetime import datetime
from enum import Enum
from sqlalchemy import Column, String, Integer, Float, DateTime, Enum as SqlEnum
from .database import db  # 使用统一的 db 实例
from scripts.logger import Log


class STaskState(Enum):
    """任务状态"""
    INIT = "初始化"
    RUNNING = "运行中"
    SUCCESS = "已完成"
    FAILED = "失败"
    CANCELED = "已取消"

class STask(db.Model):
    """服务端任务类"""
    __tablename__ = 'tasks'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    deviceId = db.Column(db.String(50), nullable=False)
    appName = db.Column(db.String(50), nullable=False)
    taskName = db.Column(db.String(50), nullable=False)
    sequence = db.Column(db.Integer, nullable=False)
    time = db.Column(db.DateTime, default=datetime.now)  # 创建时间
    score = db.Column(db.Integer, default=0)
    progress = db.Column(db.Float, default=0.0)
    state = db.Column(SqlEnum(STaskState), default=STaskState.INIT)
    expectedScore = db.Column(Integer, default=100)

    def start(self):
        """开始任务"""
        self.time = datetime.now()
        self.progress = 0.0
        db.session.add(self)
        db.session.commit()
        Log.i(f"任务 {self.taskName} 开始执行")

    def calculateExpectedScore(self):
        """计算预期得分"""
        try:
            # 这里可以根据历史数据和任务类型计算预期得分
            # 暂时返回固定值
            return 100
        except Exception as e:
            Log.ex(e, '计算预期得分失败')
            return 0

    def updateProgress(self, progress: float):
        """更新任务进度"""
        self.progress = min(max(progress, 0), 1)
        Log.i(f'任务 %%%{self.taskName} 进度更新为 {self.progress}')
        db.session.commit()

    def complete(self, score: int):
        """完成任务"""
        self.score = score
        self.progress = 1.0  # 设置进度为100%
        self.state = STaskState.SUCCESS
        db.session.commit()
        Log.i(f"任务 {self.taskName} 已完成，得分: {self.score}")

    def cancel(self):
        """取消任务"""
        db.session.delete(self)  # 直接删除任务记录
        db.session.commit()
        Log.i(f"任务 {self.taskName} 已取消") 