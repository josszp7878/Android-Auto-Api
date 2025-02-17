from datetime import datetime
from enum import Enum
from sqlalchemy import Column, String, Integer, Float, DateTime, Enum as SqlEnum
from .database import db, commit  # 使用统一的 db 实例和 safe_commit
from scripts.logger import Log
from flask import current_app
from .SDeviceMgr import deviceMgr
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
    time = db.Column(db.DateTime, default=datetime.now)  # 创建时间
    score = db.Column(db.Integer, default=0)
    progress = db.Column(db.Float, default=0.0)
    state = db.Column(SqlEnum(STaskState), default=STaskState.INIT)
    expectedScore = db.Column(Integer, default=100)

    def start(self):
        """开始任务"""
        self.state = STaskState.RUNNING
        commit(self)  # 使用安全提交
        # 发送任务启动事件
        deviceMgr.emit2Console('S2B_StartTask', {
            'deviceId': self.deviceId,
            'task': {
                'taskName': self.taskName,
                'appName': self.appName,
                'expectedScore': self.expectedScore
            }
        })
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

    def update(self, progress: float):
        """更新任务进度"""
        try:
            progress = min(max(progress, 0), 1)  # 确保进度在0-1之间
            
            # 更新状态和进度
            self.state = STaskState.RUNNING     
            Log.i(f'任务 {self.taskName} 进度更新为 {progress}')
            
            self.progress = progress
            commit(self)  # 使用安全提交
            
            # 发送进度更新事件
            deviceMgr.emit2Console('S2B_UpdateTask', {
                'deviceId': self.deviceId,
                'task': {
                    'appName': self.appName,
                    'taskName': self.taskName,
                    'progress': self.progress,
                    'state': self.state.value,
                    'score': self.score
                }
            })
            return True
        except Exception as e:
            Log.ex(e, '更新任务进度失败')
            return False

    def end(self, score: int):
        """结束任务"""
        # 更新任务状态和得分
        if score > 0:
            self.state = STaskState.SUCCESS
            self.score = score
        else:
            self.state = STaskState.CANCELED
            
        self.progress = 1.0  # 设置进度为100%
        commit(self)  # 提交更改
        
        # 发送任务结束事件到控制台
        deviceMgr.emit2Console('S2B_TaskEnd', {
            'deviceId': self.deviceId,
            'task': {
                'appName': self.appName,
                'taskName': self.taskName,
                'progress': self.progress,
                'state': self.state.value,
                'score': score,
            }
        })
        Log.i(f'任务得分: {score}')
 
    def stop(self):
        """停止任务"""
        self.state = STaskState.CANCELED
        commit(self)  # 使用安全提交
        # 广播任务停止消息到所有控制台
        deviceMgr.emit2Console('S2B_TaskStop', {
            'deviceId': self.deviceId,
            'task': {
                'appName': self.appName,
                'taskName': self.taskName
            }
        })
        Log.i(f"任务 {self.taskName} 已取消") 

    def get_scores(self, device_id):
        """获取设备的得分统计"""
        try:
            today = datetime.now().date()
            with current_app.app_context():
                # 获取今日该任务的总分
                today_task_score = STask.query.filter(
                    STask.deviceId == device_id,
                    STask.time >= today,
                    STask.appName == self.appName,
                    STask.taskName == self.taskName,
                    STask.state == STaskState.SUCCESS
                    ).with_entities(func.sum(STask.score)).scalar() or 0
                
                # 获取设备总分
                device = self.get_device(device_id)
                if device:
                    total_score = device.total_score
                else:
                    total_score = 0

                return {
                    'todayTaskScore': today_task_score,
                    'totalScore': total_score
                }
        except Exception as e:
            Log.ex(e, f'获取设备{device_id}得分统计失败')
            return {'todayTaskScore': 0, 'totalScore': 0}