import json
import os

class TaskBase:
    """任务配置基类，提供任务配置读取功能"""
    taskConfigs = {}

    @classmethod
    def _getConfigPath(cls):
        from _G import g
        configDir = os.path.join(g.rootDir(), "config")
        if not os.path.exists(configDir):
            os.makedirs(configDir)
        return os.path.join(configDir, "task.json")

    @classmethod
    def loadConfig(cls):
        try:
            configPath = cls._getConfigPath()
            if os.path.exists(configPath):
                with open(configPath, "r", encoding="utf-8") as f:
                    configs = json.load(f)
                    cls.taskConfigs.update(configs)
        except Exception as e:
            print(f"加载任务配置失败: {e}")

    @classmethod
    def getConfig(cls, taskName=None):
        if not cls.taskConfigs:
            cls.loadConfig()
        if taskName:
            return cls.taskConfigs.get(taskName)
        return cls.taskConfigs 
    

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