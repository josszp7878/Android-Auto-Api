from datetime import datetime
from scripts.tools import TaskState
from .database import db, commit  # 使用统一的 db 实例和 safe_commit
from scripts.logger import Log
from flask import current_app

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
    state = db.Column(db.String(20), default=TaskState.RUNNING.value)  # 使用字符串存储状态
    expectedScore = db.Column(db.Integer, default=100)

    @property
    def deviceMgr(self):
        from .SDeviceMgr import deviceMgr
        return deviceMgr

    def __init__(self, deviceId: str, appName: str, taskName: str):
        self.deviceId = deviceId
        self.appName = appName
        self.taskName = taskName
        self.progress = 0.0
        self.state = TaskState.RUNNING.value
        self.time = datetime.now()

    def start(self):
        """开始任务"""
        self.state = TaskState.RUNNING.value
        commit(self)  # 使用安全提交
        Log.i(f'任务启动: {self.id}-{self.taskName}')

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
            if self.state != TaskState.RUNNING.value:
                Log.i(f"任务 {self.taskName} 不在运行状态，无法更新进度")
                return False
            
            self.progress = min(max(progress, 0), 1)
            if not self.save():
                return False
            
            return STask.refresh(self)
        
        except Exception as e:
            Log.ex(e, '更新任务进度失败')
            return False

    def cancel(self):
        """取消任务，从数据库中删除"""
        try:
            Log.i(f"任务 {self.taskName} 已取消")
            with current_app.app_context():
                # 从数据库中删除
                db.session.delete(self)
                db.session.commit()
            # 设置当前任务为null
            device = self.deviceMgr.get_device(self.deviceId)
            if device and device.taskMgr:
                device.taskMgr.currentTask = None                
        except Exception as e:
            Log.ex(e, '取消任务失败')

    def end(self, data: dict):
        """结束任务"""
        result = data.get('result', True)
        score = data.get('score', 0)
        Log.i(f'任务结束: {self.id}-{self.taskName}, 结果: {"成功" if result else "失败"}, 得分: {score}')
        
        self.state = TaskState.SUCCESS.value if result else TaskState.FAILED.value
        self.score = score
        self.progress = 1.0 if result else self.progress
        commit(self)
        
        STask.refresh(self)

    def stop(self):
        """停止任务"""
        if self.state == TaskState.RUNNING.value:
            self.state = TaskState.PAUSED.value
            commit(self)
            
            STask.refresh(self)
            Log.i(f"任务 {self.id}-{self.taskName} 已暂停，进度: {self.progress*100:.1f}%")

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
                    STask.state == TaskState.SUCCESS.value
                    ).with_entities(func.sum(STask.score)).scalar() or 0
                
                # 获取设备总分
                device = self.deviceMgr.get_device(device_id)
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

    

    def save(self):
        """保存任务到数据库"""
        try:
            session = db.session
            if self in session:
                session.commit()
            else:
                session.merge(self)
                session.commit()
            return True
        except Exception as e:
            Log.ex(e, f'保存任务 {self.taskName} 失败')
            session.rollback()
            return False

    @classmethod
    def refresh(cls, task: 'STask'):
        """刷新任务状态到界面"""
        try:
            from .SDeviceMgr import deviceMgr
            # 发送任务更新事件
            deviceMgr.emit2Console('S2B_TaskUpdate', {
                'deviceId': task.deviceId,
                'task': {
                    'id': task.id,
                    'appName': task.appName,
                    'taskName': task.taskName,
                    'progress': task.progress,
                    'state': task.state,
                    'score': task.score,
                    'expectedScore': task.expectedScore
                } if task else None
            })
        except Exception as e:
            Log.ex(e, f'刷新任务 {task.taskName} 状态失败')