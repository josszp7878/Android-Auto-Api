import json
import os
from datetime import datetime
import time
from _G import TaskState
import _G
from typing import TYPE_CHECKING
import socket

if TYPE_CHECKING:
    from _Page import _Page_
    from _App import _App_
    from _Log import _Log_
    from _G import _G_

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
        self._lastInPage = False
        self._id = 0    
        self._name = name
        self._life = None
        self._interval = None
        self._pageName = None
        self._pageData = {}
        self._beginScript = None  # 修改为begin脚本
        self._exitScript = None   # 修改为exit脚本
        self._page: "_Page_" = None  # 目标页面
        
        # 直接使用传入的配置
        self._config = config

    @property
    def id(self):
        """任务ID"""
        return self._id

    @property
    def score(self):
        """任务得分"""
        return self._score
    
    @score.setter
    def score(self, value):
        if self._score != value:
            self._score = value
            self._emitUpdate(self._id, {
                'score': value
            })
    
    @property
    def state(self)->TaskState:
        """任务状态"""
        return self._state

    @state.setter
    def state(self, value: TaskState):
        """任务状态"""
        log = _G.g.Log()
        log.i(f"任务{self._name}状态: self._state={self._state}, ==>value={value}")
        if self._state != value:
            self._state = value
            self._emitUpdate(self._id, {
                'state': value.value
            })


    @classmethod
    def _getConfigPath(cls):
        """获取配置文件路径"""
        import _G
        configDir = os.path.join(_G.g.rootDir(), "config")
        if not os.path.exists(configDir):
            os.makedirs(configDir)
        return os.path.join(configDir, "task.json")
    
    @classmethod
    def loadConfig(cls):
        """加载任务配置"""
        log = _G.g.Log()
        try:
            configPath = cls._getConfigPath()
            if os.path.exists(configPath):
                with open(configPath, "r", encoding="utf-8") as f:
                    configs = json.load(f)
                    cls.taskConfigs.update(configs)
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
            cls.loadConfig()
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
    
    # 检查条件
    @property
    def check(self):
        """检查条件"""
        return self._getProp('check')
    
    # 执行工作
    @property
    def do(self):
        """执行工作"""
        return self._getProp('do')
    
    
    # 生命周期
    # 正数=秒，负数=次数
    @property
    def life(self):
        """生命周期（正数=秒，负数=次数）"""
        if self._life is None:
            self._life = int(self._getProp('life'))
        return self._life

    @life.setter
    def life(self, value):
        self._life = int(value)

    # 执行间隔
    @property
    def interval(self):
        """执行间隔（秒）"""
        if self._interval is None:
            interval = self._getProp('interval')
            if interval:
                self._interval = max(1, int(interval))
            else:
                self._interval = 0
        return self._interval

    # 奖励分数
    @property
    def bonus(self):
        """奖励分数"""
        val = self._getProp('bonus')
        if val is None:
            return self._page.app.bonus_n
        else:
            return int(val)
        

    # 任务名称
    @property
    def name(self):
        """任务名称"""
        return self._name

    # 目标页面名称
    @property
    def pageName(self):
        """目标页面名称"""
        if self._pageName is None:
            self._pageName = self._getProp('page')
        return self._pageName or self.name

    @pageName.setter
    def pageName(self, value):
        self._pageName = str(value)

    # 目标页面数据,用于页面跳转时传递数据
    # 字典，key=属性名，value=属性值
    @property
    def pageData(self):
        """目标页面数据"""
        if self._pageData is None:
            self._pageData = self._getProp('data')
        return self._pageData

    # 开始脚本
    @property
    def beginScript(self):
        """开始脚本"""
        if self._beginScript is None:
            self._beginScript = self._getProp('begin')
        return self._beginScript

    @beginScript.setter
    def beginScript(self, value):
        self._beginScript = str(value)

    # 结束脚本
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
        return self._config.get(prop)
    
    def isCompleted(self):
        """判断任务是否完成"""
        return self.state == TaskState.SUCCESS or self.state == TaskState.FAILED

    def _Do(self, g: "_G_") -> bool:
        """执行任务具体工作"""
        if self.do is not None:
            g.Tools().do(self.do)
        if not self._goPage(g):
            return False
        return True
    
    def fromData(self, data: dict):
        """从数据更新任务"""
        if data is None or not isinstance(data, dict):
            return
        self._id = int(data.get('id'))
        self._progress = float(data.get('progress'))
        self._state = TaskState(data.get('state'))
        self._score = int(data.get('score'))
        self._life = int(data.get('life'))

    def begin(self, life: int = None) -> bool:
        """开始任务，支持继续和正常开始
        Args:
            life: 生命的绝对值，默认为0。当任务已经完成时，如果life比当前self.life的绝对值大，就重新设置self.life并启动任务
        """
        g = _G._G_
        log = g.Log()        
        if life is not None:
            self.life = life
        try:
            if self.state == TaskState.IDLE:            
                # 开始运行
                # 执行begin脚本（使用属性访问）
                if self.beginScript:
                    try:
                        exec(self.beginScript)
                    except Exception as e:
                        log.ex(e, f"执行任务开始脚本失败: {e}")
            self._state = TaskState.RUNNING
            self._startTime = datetime.now()
            self._lastTime = self._startTime
            if not self._Do(g):
                log.e(f"任务{self._name}执行失败")
                return False
            # 发送任务开始事件
            taskData = g.emitRet('C2S_StartTask', {
                'taskName': self.name
            })
            if taskData is None:
                log.e(f"任务{self._name}开始失败")
                return False
            self.fromData(taskData)
            self._app.curTask = self
            return True
        except Exception as e:
            log.ex(e, f"任务开始失败: {e}")
            return False
        
    def _goPage(self, g: "_G_")->bool:
        if not self.pageName:
            # log.e(f"目标页面名称不能为空")
            return True
        page = g.App().go(self.pageName)
        if not page:
            g.Log().e(f"获取目标页面失败: {self.pageName}")
            return False
        data = self.pageData
        if data:
            page.data.update(data)
        self._page = page
        return True
    
    def stop(self):
        """停止任务"""
        self.state = TaskState.PAUSED
        return True
    
    def exitTrigger(self)->bool:
        """判断目标页面_page的退出的那一刻(下降沿)
        通过记录上一次页面状态和当前页面状态比较，检测页面退出的下降沿
        即从当前页面变为非当前页面的那一刻
        Returns:
            bool: 如果检测到页面退出下降沿则返回True，否则返回False
        """
        page = self._page
        if page is None:
            return False
        # 获取当前页面状态
        isCurPage = page == page.app.curPage
        # 如果上一次在页面中，且当前不在页面中，说明检测到下降沿
        if self._lastInPage and not isCurPage:
            self._lastInPage = False
            return True
        # 更新状态
        self._lastInPage = isCurPage
        return False
    
    def update(self, g: "_G_"):
        """任务更新函数"""
        if self.state != TaskState.RUNNING:
            return
        check = g.Tools().check(self.check) if self.check else True
        if check:
            #本次任务完成
            if self.bonus > 0:
                self._score += self.bonus
            # 增加执行计数
            if self._refreshProgress():
                if not self._next(g):
                    return False
        return True

    def _next(self, g: "_G_")->bool:
        if self.interval > 0:
            waitTime = self.interval - self._deltaTime
            if waitTime > 0:
                time.sleep(waitTime)
        if not self._Do(g):
            g.Log().e(f"任务{self._name}执行失败")
            return False
        return True
    
    @property
    def progress(self):
        """任务进度"""
        return self._progress
    
    @progress.setter
    def progress(self, value):
        if self._progress != value:
            self._progress = value
            self._emitUpdate(self._id, {
                'progress': value
            })

    def _refreshProgress(self)->bool:
        """统一处理进度更新        
        考虑任务暂停后再次开始的情况，累计计算进度
        """
        if self.state != TaskState.RUNNING:
            return False
        life = self.life
        if life != 0:
            progress = self.progress
            if life > 0:  # 时间模式
                # 计算当前会话运行时间
                curTime = datetime.now()
                self._deltaTime = (curTime - self._lastTime).total_seconds()
                self._lastTime = curTime
                # 累加到总进度中
                progress += self._deltaTime / life
            else:  # 次数模式
                # 次数模式下，_execCount已经在_do中累加
                progress += 1 / abs(life)
            
            self.progress = min(max(0.0, progress), 1.0)
        else:
            self.progress = 1.0
        _G.g.Log().i(f"任务{self._name}进度: {self.progress:0.2f}")
        # 进度完成处理
        if self.progress >= 1.0:
            self.end()
            return False
        return True

    def end(self):
        # 确定最终状态
        self.state = TaskState.SUCCESS if self._score > 0 else TaskState.FAILED
        # 执行结束脚本（使用属性访问）
        _G.g.Tools().do(self.exitScript)

    @classmethod
    def _emitUpdate(cls, taskID, data):
        """发送任务更新事件"""
        data['id'] = taskID
        log = _G.g.Log()
        log.i(f'发送任务更新事件: {data}')
        _G.g.emit('C2S_UpdateTask', data)