import json
import os
from datetime import datetime
from enum import Enum
import _G
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from _Page import _Page_
    from _App import _App_
    from _Log import _Log_

class TaskState(Enum):
    """任务状态枚举
    状态转换流程：
    IDLE → RUNNING → (PAUSED/ENDED)
    PAUSED → RUNNING
    """
    IDLE = "空闲"        # 初始/取消状态，可开始新任务
    RUNNING = "运行中"  # 任务执行中，可暂停或完成
    PAUSED = "暂停"    # 暂停状态，可恢复执行
    ENDED = "完成"      # 任务结束（终态）


class CTask_:
    """客户端任务类"""
    
    # 任务配置字典
    taskConfigs = {}
    
    def __init__(self, name: str, config: dict, app: "_App_"):
        """初始化任务"""
        self._app: "_App_" = app
        self._startTime = datetime.now()
        self._endTime = None
        self._score = 0
        self._progress = 0.0
        self._state = TaskState.IDLE
        
        self._name = name
        self._life = None
        self._interval = None
        self._pageName = None
        self._beginScript = None  # 修改为begin脚本
        self._exitScript = None   # 修改为exit脚本
        self._execCount = 0  # 执行计数器
        self._page: "_Page_" = None  # 目标页面
        
        # 直接使用传入的配置
        self._config = config

    @property
    def score(self):
        """任务得分"""
        return self._score
    
    @property
    def state(self):
        """任务状态"""
        return self._state.value

    @classmethod
    def _getConfigPath(cls):
        """获取配置文件路径"""
        import _G
        configDir = os.path.join(_G.g.rootDir(), "config")
        if not os.path.exists(configDir):
            os.makedirs(configDir)
        return os.path.join(configDir, "task.json")
    
    @classmethod
    def _loadConfig(cls):
        """加载任务配置"""
        log = _G.g.Log()
        try:
            configPath = cls._getConfigPath()
            if os.path.exists(configPath):
                with open(configPath, "r", encoding="utf-8") as f:
                    cls.taskConfigs = json.load(f)
        except Exception as e:
            log.ex(e, f"加载任务配置失败: {configPath}")
    
    @classmethod
    def _saveConfig(cls):
        """保存任务配置"""
        log = _G.g.Log()
        try:
            configPath = cls._getConfigPath()
            with open(configPath, "w", encoding="utf-8") as f:
                json.dump(cls.taskConfigs, f, ensure_ascii=False, indent=4)
        except Exception as e:
            log.ex(e, f"保存任务配置失败: {configPath}")
    
    @classmethod
    def _getConfig(cls, taskName):
        """获取任务配置"""
        if not cls.taskConfigs:
            cls._loadConfig()
        return cls.taskConfigs.get(taskName)
    
    @classmethod
    def create(cls, taskName, app):
        """创建任务实例"""
        log = _G.g.Log()
        try:
            config = cls._getConfig(taskName)
            if not config:
                log.e(f"任务配置不存在: {taskName}")
                return None
            return CTask_(taskName, config, app)
        except Exception as e:
            log.ex(e, f"创建任务实例失败: {taskName}")
            return None
    
    @property
    def isExpired(self):
        """判断任务是否过期"""
        life = self.life
        if life == 0:
            return False
            
        if life > 0:  # 正数表示时间
            elapsed = (datetime.now() - self._startTime).total_seconds()
            return elapsed >= abs(life)
        else:  # 负数表示次数
            return self._execCount >= abs(life)
    
    @property
    def life(self):
        """生命周期（正数=秒，负数=次数）"""
        if self._life is None:
            self._life = int(self._getProp('life'))
        return self._life

    @life.setter
    def life(self, value):
        self._life = int(value)

    @property
    def interval(self):
        """执行间隔（秒）"""
        if self._interval is None:
            self._interval = max(1, int(self._getProp('interval')))
        return self._interval

    @interval.setter
    def interval(self, value):
        self._interval = max(1, int(value))

    @property
    def name(self):
        """任务名称"""
        return self._name

    @property
    def pageName(self):
        """目标页面名称"""
        if self._pageName is None:
            self._pageName = self._getProp('page')
        return self._pageName or self.name

    @pageName.setter
    def pageName(self, value):
        self._pageName = str(value)

    @property
    def beginScript(self):
        """开始脚本"""
        if self._beginScript is None:
            self._beginScript = self._getProp('begin')
        return self._beginScript

    @beginScript.setter
    def beginScript(self, value):
        self._beginScript = str(value)

    @property
    def exitScript(self):
        """结束脚本"""
        if self._exitScript is None:
            self._exitScript = self._getProp('exit')
        return self._exitScript

    @exitScript.setter
    def exitScript(self, value):
        self._exitScript = str(value)

    def _getProp(self, prop: str):
        """获取配置属性"""
        return self._config.get(prop, {} if prop == 'begin' else "")
        
    def begin(self)->bool:
        """开始任务"""
        g = _G._G_
        log = g.Log()
        if self._state not in (TaskState.IDLE, TaskState.PAUSED):
            return False
        try:
            self._state = TaskState.RUNNING
            self._startTime = datetime.now()
            self._lastTime = self._startTime
            # 执行begin脚本（使用属性访问）
            if self.beginScript:
                try:
                    exec(self.beginScript)
                except Exception as e:
                    log.ex(e, f"执行任务开始脚本失败: {e}")
            g.emit('TaskStart', {
                'app': self._app.name,
                'task': self._name,
                'life': self.life,
                'interval': self.interval
            })

            if self.pageName:
                # 打开目标应用
                appName, pageName = self._app.parseName(self.pageName)
                app = g.App().open(appName)
                if not app:
                    log.e(f"打开目标应用失败: {appName}")
                    return False
                # 获取目标页面
                self._page = app.getPage(pageName)
                if not self._page:
                    log.e(f"获取目标页面失败: {pageName}")
                    return False
            return True
        except Exception as e:
            log.ex(e, f"任务开始失败: {e}")
            return False
    
    def stop(self, cancel=False, success=None):
        """统一停止/完成任务"""
        if self._state != TaskState.RUNNING:
            return False
            
        self._endTime = datetime.now()
        # 构建通知数据
        data = {'score': self._score} if success else {}
        self._end(cancel=cancel, data=data)
        return True
    
    def update(self):
        """任务更新函数"""
        if self._state != TaskState.RUNNING:
            return            
        now = datetime.now()
        timePassed = (now - self._lastTime).total_seconds()
        if timePassed >= self.interval and not self._page.running:
            self._lastTime = now
            self._do()
    
    def _do(self)->bool:
        """执行任务具体工作"""
        log = _G.g.Log()
        try:
            # log.i(f"执行任务")
            # 进入目标页面
            page = self._app.goPage(self._page)
            if not page:
                log.e("无法重新获取目标页面")
                self.stop(True)
                return False
            # 随机增加任务分数，实际应用中应基于具体任务完成情况
            import random
            scoreInc = random.randint(1, 10)
            self._score += scoreInc
            # 增加执行计数
            self._execCount += 1  # 增加执行计数
            self._refreshProgress(log)  # 合并进度更新逻辑
            return True
        except Exception as e:
            log.ex(e, f"执行任务工作失败: {e}")
            return False
        
    @property
    def progress(self):
        """任务进度"""
        return self._progress
    
    def _refreshProgress(self, log: "_Log_"):
        """统一处理进度更新"""
        if self._state != TaskState.RUNNING:
            return False
        life = self.life
        if life != 0:
            if life > 0:  # 时间模式
                elapsed = (datetime.now() - self._startTime).total_seconds()
                progress = elapsed / life
            else:  # 次数模式
                progress = self._execCount / abs(life)
            
            self._progress = min(max(0.0, progress), 1.0)
        else:
            self._progress = 1.0
        log.i(f"任务%: {self._progress}")
        # 进度完成处理
        if self._progress >= 1.0:
            self._end(cancel=False, data={'score': self._score})
            return True
        # 发送进度通知
        g = _G._G_
        g.emit('TaskUpdate', {
            'appName': self._app.name,
            'taskName': self._name,
            'progress': self._progress
        })
        return True

    def _end(self, cancel, data):
        """统一结束处理"""
        # 确定最终状态
        self._state = TaskState.ENDED
        g = _G._G_
        log = g.Log()
        log.i(f"任务结束, 取消={cancel}, 分数={self._score}")
        # 执行结束脚本（使用属性访问）
        if cancel and self.exitScript:
            try:
                exec(self.exitScript)
            except Exception as e:
                log.ex(e, f"执行任务结束脚本失败: {e}")
        # 发送服务端通知
        g.emit('TaskEnded', {
            'appName': self._app.name,
            'taskName': self._name,
            **data
        })
    