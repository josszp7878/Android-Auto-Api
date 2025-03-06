from datetime import datetime
from _Tools import TaskState, _Tools
from Database import db, Database
import _Log
from flask import current_app
from sqlalchemy import func


class STask(db.Model):
    """服务端任务类"""
    __tablename__ = 'tasks'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    deviceId = db.Column(db.String(50), nullable=False)
    appName = db.Column(db.String(50), nullable=False)
    taskName = db.Column(db.String(50), nullable=False)
    time = db.Column(db.DateTime, default=datetime.now)  # 创建时间
    endTime = db.Column(db.DateTime)  # 添加结束时间字段
    score = db.Column(db.Integer, default=0)
    progress = db.Column(db.Float, default=0.0)
    state = db.Column(db.String(20), default=TaskState.RUNNING.value)
    expectedScore = db.Column(db.Integer, default=100)  # 设置默认值为100

    @property
    def deviceMgr(self):
        from SDeviceMgr import deviceMgr
        return deviceMgr
    
    @property
    def taskId(self):
        return _Tools.toTaskId(self.appName, self.taskName)
    
    @property
    def completed(self):
        return self.state in [TaskState.SUCCESS.value, TaskState.FAILED.value]

    @property
    def device(self):
        """获取任务对应的设备,使用缓存避免重复查询"""
        if not hasattr(self, '_device'):
            from SDeviceMgr import deviceMgr
            self._device = deviceMgr.get_device(self.deviceId)
        return self._device

    def __init__(self, deviceId: str, appName: str, taskName: str):
        """初始化任务"""
        self.deviceId = deviceId
        self.appName = appName
        self.taskName = taskName
        self.progress = 0.0
        self.state = TaskState.RUNNING.value
        self.time = datetime.now()
        self.expectedScore = 100  # 初始化时计算预期分数

    def start(self):
        """开始任务"""
        self.state = TaskState.RUNNING.value
        db.session.commit()
        _Log.Log.i(f'任务启动: {self.id}-{self.taskName}')

    def update(self, progress: float):
        """更新任务进度"""
        try:
            if self.state != TaskState.RUNNING.value:
                _Log.Log.i(f"任务 {self.taskName} 不在运行状态，无法更新进度")
                return False
            # 确保 progress 是 float 类型
            self.progress = float(min(max(progress, 0), 1))
            if Database.commit(self):
                return STask.refresh(self)
            return False
            
        except Exception as e:
            _Log.Log.ex(e, '更新任务进度失败')
            return False

    def cancel(self):
        """取消任务，从数据库中删除"""
        try:
            _Log.Log.i(f"任务 {self.taskName} 已取消")
            device = self.device
            if device and device.taskMgr:
                # 如果是当前任务，先清除
                if device.taskMgr.currentTask == self:
                    device.taskMgr.currentTask = None
            
            # 从数据库中删除
            with current_app.app_context():
                db.session.delete(self)
                db.session.commit()
            
            # 刷新界面（传入None表示清除任务显示）
            from SDeviceMgr import deviceMgr
            deviceMgr.emit2B('S2B_TaskUpdate', {
                'deviceId': self.deviceId,
                'task': None
            })
                
        except Exception as e:
            _Log.Log.ex(e, '取消任务失败')

    def end(self, data: dict):
        """结束任务"""
        try:
            result = data.get('result', True)
            score = data.get('score', 0)
            _Log.Log.i(f'任务结束: {self.id}-{self.taskName}, 结果: {"成功" if result else "失败"}, 得分: {score}')
            
            self.state = TaskState.SUCCESS.value if result else TaskState.FAILED.value
            self.score = score
            self.progress = 1.0 if result else self.progress
            self.endTime = datetime.now()
            if Database.commit(self):
                _Log.Log.i(f"任务结束: 成功")
                return STask.refresh(self)
            return False
            
        except Exception as e:
            _Log.Log.ex(e, '结束任务失败')
            return False

    def stop(self):
        """停止任务"""
        if self.state == TaskState.RUNNING.value:
            self.state = TaskState.PAUSED.value
            db.session.commit()
            STask.refresh(self)
            _Log.Log.i(f"任务 {self.id}-{self.taskName} 已暂停，进度: {self.progress*100:.1f}%")

  
    def to_dict(self):
        """返回任务信息字典"""
        try:
            # 计算任务收益率
            today = datetime.now().date()
            similar_tasks = STask.query.filter(
                STask.deviceId == self.deviceId,
                STask.appName == self.appName,
                STask.taskName == self.taskName,
                func.date(STask.time) == today,
                STask.state == TaskState.SUCCESS.value
            ).all()
            
            total_score = sum(t.score for t in similar_tasks if t.score)
            total_time = sum((t.endTime - t.time).total_seconds() / 3600 
                            for t in similar_tasks if t.endTime)
            
            efficiency = round(total_score / total_time, 1) if total_time > 0 else 0
            
            return {
                'id': self.id or 0,  # 确保id不为null
                'appName': self.appName,
                'taskName': self.taskName,
                'displayName': f'{self.id or 0}:{self.appName}-{self.taskName}',
                'progress': self.progress,
                'state': self.state,
                'score': self.score,
                'expectedScore': self.expectedScore or 100,  # 确保expectedScore不为null
                'efficiency': efficiency
            }
        except Exception as e:
            _Log.Log.ex(e, '获取任务信息失败')
            return {
                'id': self.id or 0,
                'appName': self.appName,
                'taskName': self.taskName,
                'displayName': f'{self.id or 0}:{self.appName}-{self.taskName}',
                'progress': self.progress,
                'state': self.state,
                'score': self.score,
                'expectedScore': self.expectedScore or 100,
                'efficiency': 0
            }

    @classmethod
    def refresh(cls, task: 'STask'):
        """刷新任务状态到界面"""
        try:
            from SDeviceMgr import deviceMgr
            # 如果task为None，直接返回
            _Log.Log.i(f"刷新任务状态1111: 任务：{task}")
            if not task:
                return
            # 获取设备
            device = task.device
            # 获取任务管理器
            taskMgr = device.taskMgr
            today_task_score = taskMgr.getTodayScore()
            # 获取任务管理器统计信息
            stats = taskMgr.getTaskStats()
            
            # 发送任务更新事件，包含分数信息
            deviceMgr.emit2B('S2B_TaskUpdate', {
                'deviceId': task.deviceId,
                'task': {
                    **task.to_dict(),
                    'taskStats': stats,
                } if task else None,
                'todayTaskScore': today_task_score,
                'totalScore': device.total_score
            })
            
        except Exception as e:
            _Log.Log.ex(e, f'刷新任务状态失败')