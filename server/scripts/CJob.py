import time
from datetime import datetime


class CJob_:
    """任务执行器类，负责执行具体的任务逻辑"""
    
    def __init__(self, pageName, life, interval, onEnd=None):
        """初始化任务执行器
        
        Args:
            pageName: 目标页面名称
            life: 任务生命周期(秒)，0表示无限生命周期
            interval: 任务执行间隔(秒)
            onEnd: 任务结束时执行的脚本
        """
        self._pageName = pageName
        self._life = life
        self._interval = max(1, interval)  # 最小间隔1秒
        self._onEnd = onEnd
        self._startTime = datetime.now()
        self._lastExecTime = None
        self._app = None
        self._task = None
        self._isRunning = False
        self._score = 0
        
    @property
    def pageName(self):
        """获取任务目标页面名称"""
        return self._pageName
        
    @property
    def isRunning(self):
        """获取任务是否正在运行"""
        return self._isRunning
        
    @property
    def score(self):
        """获取任务得分"""
        return self._score
        
    @property
    def isExpired(self):
        """判断任务是否已过期"""
        # life为0表示无限生命周期
        if self._life <= 0:
            return False
        
        # 计算任务已运行时间
        elapsedTime = (datetime.now() - self._startTime).total_seconds()
        return elapsedTime >= self._life
        
    @classmethod
    def Create(cls, pageName, life=0, interval=1, onEnd=None):
        """创建任务执行器
        
        Args:
            pageName: 目标页面名称
            life: 任务生命周期(秒)，0表示无限生命周期
            interval: 任务执行间隔(秒)
            onEnd: 任务结束时执行的脚本
            
        Returns:
            CJob_: 任务执行器实例
        """
        return cls(pageName, life, interval, onEnd)
        
    def begin(self, app, task):
        """开始任务
        
        Args:
            app: 所属应用
            task: 所属任务
            
        Returns:
            bool: 是否成功开始
        """
        try:
            self._app = app
            self._task = task
            self._isRunning = True
            self._startTime = datetime.now()
            self._lastExecTime = None
            
            # 尝试跳转到目标页面
            if self._pageName:
                from _App import _App_
                result = _App_.go(self._pageName)
                if not result:
                    print(f"跳转到页面 {self._pageName} 失败")
                    return False
            
            return True
        except Exception as e:
            print(f"开始任务执行器失败: {e}")
            return False
            
    def update(self):
        """更新任务执行器"""
        if not self._isRunning:
            return
            
        # 检查任务是否过期
        if self.isExpired:
            self.end()
            return
            
        # 检查是否到达执行间隔
        now = datetime.now()
        if self._lastExecTime is None or (now - self._lastExecTime).total_seconds() >= self._interval:
            self._lastExecTime = now
            self._doWork()
            
    def end(self):
        """结束任务执行器"""
        if not self._isRunning:
            return
            
        self._isRunning = False
        
        # 执行结束脚本
        if self._onEnd:
            try:
                exec(self._onEnd)
            except Exception as e:
                print(f"执行任务结束脚本失败: {e}")
                
        # 更新任务结果
        if self._task:
            self._task.complete(True, self._score)
            
    def _doWork(self):
        """执行任务具体工作，子类需要重写此方法"""
        # 这里只是示例，实际应用中可能需要更复杂的逻辑
        try:
            # 检查是否在目标页面
            if self._pageName and self._app:
                from _App import _App_
                app = _App_.cur()
                if app and app.curPage and app.curPage.name != self._pageName:
                    # 尝试重新跳转到目标页面
                    _App_.go(self._pageName)
                    
            # 随机增加任务分数，实际应用中应基于具体任务完成情况
            import random
            scoreInc = random.randint(1, 10)
            self._score += scoreInc
            
            # 更新任务进度
            if self._task and self._life > 0:
                elapsedTime = (datetime.now() - self._startTime).total_seconds()
                progress = min(elapsedTime / self._life, 1.0)
                self._task.updateProgress(progress)
                
        except Exception as e:
            print(f"执行任务工作失败: {e}")
            
    def addScore(self, score):
        """添加任务分数
        
        Args:
            score: 要添加的分数
            
        Returns:
            int: 添加后的总分数
        """
        self._score += score
        return self._score 