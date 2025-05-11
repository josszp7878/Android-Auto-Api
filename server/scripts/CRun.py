import time
import threading
from typing import List, Optional
import typing
if typing.TYPE_CHECKING:
    from _App import _App_
    from _Page import _Page_

import _G

class Job:
    """批处理任务对象"""
    def __init__(self, page: '_Page_', life: int, interval: int, onEnd: str):
        self._page = page
        self._life = life
        self._interval = max(interval, 1)
        self._onEnd = onEnd
        self.reset(time.monotonic())

    def reset(self, now: float):
        """重置运行时状态"""
        self._startTime = now
        self._lastRun = now
        self._runCount = 0
        self._process = 0.0

    def _updateProgress(self, now: float) -> None:
        """更新进度并缓存"""
        if self._life < 0:
            self._process = self._runCount / abs(self._life)
        else:
            self._process = (now - self._startTime) / self._life
        if self._process > 1.0:
            self._process = 1.0
        log = _G._G_.Log()
        log.d(f"进度: {self._process}")

    def _doEnd(self):
        """执行回调函数"""
        if not self._onEnd:
            return
        tools = _G._G_.Tools()
        log = _G._G_.Log()
        try:
            log.d(f"执行回调:{self._onEnd}")
            tools.do(self._page, self._onEnd)  # 移除不必要的self参数
        except Exception as e:
            log.ex(e, f"回调执行失败:{self._onEnd}")

    def update(self, app, now: float) -> bool:
        """处理任务完整生命周期"""
        if self._process >= 1.0:
            self._doEnd()
            return True
            
        if now - self._lastRun >= self._interval and not self._page.running:
            if app.goPage(self._page):
                self._lastRun = now
                if self._life < 0:
                    self._runCount += 1
                self._updateProgress(now)
        return False
    

class CRun_:
    def __init__(self, app: "_App_"):
        self.app: "_App_" = app  # 关联的App实例
        self.lock = threading.Lock()
        self.queue: List[Job] = []
        self.current: Optional[Job] = None

    def add(self, pageName: str, life: int, interval: int, onEnd: str) -> bool:
        """添加任务（优化参数处理）"""
        log = _G._G_.Log()
        try:
            if life == 0:
                log.e("无效life参数")
                return False
            with self.lock:
                page = self.app.getPage(pageName)
                if not page:
                    log.e(f"未知页面: {pageName}")
                    return False
                self.queue.append(Job(page, life, interval, onEnd))            
            log.i(f"批处理任务已添加 | 目标:{pageName} 队列数:{len(self.queue)}")
            return True
        except Exception as e:
            log.ex(e, "添加批处理失败")
            return False

    def update(self):
        """状态更新（最终简化版）"""
        with self.lock:
            now = time.monotonic()            
            # 自动处理当前任务或获取新任务
            if not self.current and self.queue:
                self.current = self.queue.pop(0)
                self.current.reset(now)
            if self.current:
                if self.current.update(self.app, now):
                    self.current = None 