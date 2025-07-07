import json
import os
import _G

class Task_:
    """任务配置基类，提供任务配置读取功能"""
    taskConfigs = {}


    @classmethod
    def loadConfig(cls):
        try:
            g = _G._G_
            log = g.Log()
            configPath = g.configDir()
            if os.path.exists(configPath):
                with open(configPath, "r", encoding="utf-8") as f:
                    configs = json.load(f)
                    cls.taskConfigs.update(configs)
        except Exception as e:
            log.ex(e, f"加载任务配置失败")

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
        g = _G._G_
        log = g.Log()
        try:
            configPath = g.configDir()
            with open(configPath, "w", encoding="utf-8") as f:
                json.dump(cls.taskConfigs, f, ensure_ascii=False, indent=4)
        except Exception as e:
            log.ex(e, f"保存任务配置失败: {configPath}")