import json
import os
from datetime import datetime
import time
from _G import TaskState
import _G
from typing import TYPE_CHECKING
import socket
from Task import TaskBase
from Base import Base_
from RPC import RPC

if TYPE_CHECKING:
    from _Page import _Page_
    from _App import _App_
    from _Log import _Log_
    from _G import _G_

class CTask_(TaskBase, Base_):
    """客户端任务类"""
    
    def __init__(self, name: str, config: dict, app: "_App_"):
        """初始化任务"""
        super().__init__()
        self._app: "_App_" = app
        self._startTime = datetime.now()
        self._score: int = 0
        self._progress: int = 0
        self._state: TaskState = TaskState.IDLE
        self._lastInPage: bool = False
        self._id: int = 0    
        self._name: str = name
        self._life: int = None
        self._interval: int = None
        self._deltaTime: int = 0
        self._lastTime: datetime = None
        self._pageName: str = None
        self._pageData: dict = {}
        self._beginScript = None  # 修改为begin脚本
        self._exitScript = None   # 修改为exit脚本
        self._page: "_Page_" = None  # 目标页面
        self._config = config
        self.oldValues = {
            'score': self._score,
            'state': self._state.value,  # 存储枚举值
            'progress': self._progress
        }

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
            self._isDirty = True  # 标记为脏
    
    @property
    def state(self)->TaskState:
        """任务状态"""
        return self._state

    @state.setter
    def state(self, value: TaskState):
        """任务状态"""
        log = _G.g.Log()
        # log.i(f"任务{self._name}状态: self._state={self._state}, ==>value={value}")
        if self._state != value:
            self._state = value
            self._isDirty = True  # 标记为脏
            self._emitUpdate(self._id, {
                'state': value.value
            })

    @property
    def progress(self)->int:
        """任务进度"""
        return self._progress
    
    @progress.setter
    def progress(self, value:int):
        if self._progress != value:
            self._progress = value
            self._isDirty = True  # 标记为脏

    @classmethod
    def _getConfigPath(cls):
        """获取配置文件路径"""
        import _G
        configDir = os.path.join(_G.g.rootDir(), "config")
        if not os.path.exists(configDir):
            os.makedirs(configDir)
        return os.path.join(configDir, "task.json")
    
    
    @classmethod
    def _getConfig(cls, taskName):
        """获取任务配置"""
        return TaskBase.getConfig(taskName)
    
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
    
    @RPC()
    def getTaskInfo(self) -> dict:
        """获取任务信息 - RPC方法"""
        try:
            return {
                'success': True,
                'id': self._id,
                'name': self._name,
                'state': self._state.value,
                'progress': self._progress,
                'score': self._score,
                'life': self._life,
                'interval': self._interval,
                'pageName': self.pageName,
                'isCompleted': self.isCompleted(),
                'startTime': self._startTime.isoformat() if self._startTime else None
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    @RPC()
    def startTask(self, life: int = None) -> dict:
        """开始任务 - RPC方法"""
        try:
            result = self.begin(life)
            return {
                'success': True,
                'taskId': self._id,
                'state': result.value if result else None,
                'message': f'任务 {self._name} 已开始'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    @RPC()
    def stopTask(self, state: int = None) -> dict:
        """停止任务 - RPC方法"""
        try:
            if state is not None:
                stop_state = TaskState(state)
            else:
                stop_state = TaskState.PAUSED
            result = self.stop(stop_state)
            return {
                'success': True,
                'taskId': self._id,
                'state': result.value if result else None,
                'message': f'任务 {self._name} 已停止'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

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
        self._progress = int(data.get('progress'))
        self._state = TaskState(data.get('state'))
        self._score = int(data.get('score'))
        self._life = int(data.get('life'))

    def begin(self, life: int = None) -> TaskState:
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
                return None
            device = _G._G_.CDevice()
            device.setCurTask(self)
            self._emitUpdate(self._id, {
                'state': self._state.value
            })
            return self._state
        except Exception as e:
            log.ex(e, f"任务开始失败: {e}")
            return None
        
    def stop(self, state: TaskState = TaskState.PAUSED)->TaskState:
        """停止任务"""
        self.state = state
        log = _G._G_.Log()
        log.i(f"任务{self._name}停止@@@@@@@@@@@: {state}")
        self._emitUpdate(self._id, {
            'state': self._state.value,
            'progress': self._progress
        })
        return self._state
    
        
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
    
    def _updateStateChanged(self, g: "_G_"):
        """更新任务状态"""
        changed = {}
        if self._isDirty:
            # 检查所有被追踪字段
            values = {
                'score': self._score,
                'state': self._state.value,  # 获取枚举值
                'progress': self._progress
            }
            
            for field in ['score', 'state', 'progress']:
                current = values[field]
                prev = self.oldValues[field]
                
                if current != prev:
                    changed[field] = current
                    self.oldValues[field] = current  # 更新存储值
            
            # 如果有变化则发送事件
            if changed:
                log = g.Log()
                # log.i(f'任务{self._name}更新: {changed}')
                self._emitUpdate(self._id, changed)
                self._isDirty = False  # 重置标记
    
    def update(self, g: "_G_"):
        """任务更新函数"""
        if self.state != TaskState.RUNNING:
            return        
        # 原有业务逻辑保持不变
        check = g.Tools().check(self.check) if self.check else True
        if check:
            bonus = self.bonus or 0
            if bonus > 0:
                self.score += bonus
            if self._updateProgress():
                if not self._next(g):
                    return False
        self._updateStateChanged(g)
        return True

    def _next(self, g: "_G_")->bool:
        if self.interval > 0:
            waitTime = self.interval - self._deltaTime or 0
            if waitTime > 0:
                time.sleep(waitTime)
        if not self._Do(g):
            g.Log().e(f"任务{self._name}执行失败")
            return False
        return True
    
    def _updateProgress(self)->bool:
        """统一处理进度更新        
        考虑任务暂停后再次开始的情况，累计计算进度
        """
        if self.state != TaskState.RUNNING:
            return False
        g = _G._G_
        # log = g.Log()
        life = self.life
        progress = self.progress
        if life > 0:  # 时间模式
            # 计算当前会话运行时间
            curTime = datetime.now()
            self._deltaTime = (curTime - self._lastTime).total_seconds()
            self._lastTime = curTime
            # 累加到总进度中
            progress += int(self._deltaTime)
        else:  # 次数模式
            # 次数模式
            progress += 1
        self.progress = int(progress)
        # log.i(f"任务{self._name}进度: {percent:0.2f}")
        # 进度完成处理
        if life != 0:
            percent = progress / float(abs(life))
            if percent >= 1.0:
                self.stop(TaskState.SUCCESS)
                # 执行结束脚本（使用属性访问）
                g.Tools().do(self.exitScript)
                return False
        return True

    @classmethod
    def _emitUpdate(cls, taskID, data):
        """发送任务更新事件"""
        data['id'] = taskID
        log = _G.g.Log()
        log.i(f'发送任务更新事件: {data}')
        _G.g.emit('C2S_UpdateTask', data)

    def _onProp(self, key, value):
        """CTask特殊处理"""
        if key in ['score', 'state', 'progress']:
            # 标记为脏，触发更新事件
            self._isDirty = True

   