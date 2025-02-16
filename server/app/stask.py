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

    id = db.Column(Integer, primary_key=True, autoincrement=True)
    deviceId = db.Column(String(50), nullable=False)
    appName = db.Column(String(50), nullable=False)
    taskName = db.Column(String(50), nullable=False)
    sequence = db.Column(Integer, nullable=False)
    startTime = db.Column(DateTime, default=datetime.now)
    score = db.Column(Integer, default=0)
    progress = db.Column(Float, default=0.0)
    state = db.Column(SqlEnum(STaskState), default=STaskState.INIT)
    expectedScore = db.Column(Integer, default=100)
    lastUpdateTime = db.Column(DateTime)  # 添加最后更新时间
    resumeData = db.Column(db.JSON)  # 存储任务的上下文数据

    def start(self):
        """开始任务"""
        if self.state != STaskState.RUNNING:  # 只有非运行状态才重新初始化
            self.startTime = datetime.now()
            self.state = STaskState.RUNNING
            self.expectedScore = self.calculateExpectedScore()
            self.progress = 0.0
            self.resumeData = None
        db.session.commit()
        Log.i(f"任务 {self.taskName} 开始执行, 进度: {self.progress}%")

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
        """更新任务进度和上下文数据"""
        self.progress = min(max(progress, 0), 100)
        self.lastUpdateTime = datetime.now()
        db.session.commit()
        Log.i(f"任务 {self.taskName} 进度更新: {self.progress}%")

    def complete(self, score: int):
        """完成任务"""
        self.score = score
        self.state = STaskState.SUCCESS
        db.session.commit()
        Log.i(f"任务 {self.taskName} 已完成，得分: {self.score}")

    def cancel(self):
        """取消任务"""
        self.state = STaskState.CANCELED
        db.session.commit()
        Log.i(f"任务 {self.taskName} 已取消") 