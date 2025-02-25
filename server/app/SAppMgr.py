import json
from pathlib import Path
from scripts.logger import Log


class SAppMgr:
    """应用管理类"""
    _instance = None
    _apps = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._apps is None:
            self._load_config()
    
    def _load_config(self):
        """加载应用配置"""
        try:
            config_path = Path(__file__).parent.parent / 'config' / 'apps.json'
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                self._apps = config.get('apps', {})
            Log.i(f"已加载{len(self._apps)}个应用配置")
        except Exception as e:
            Log.ex(e, "加载应用配置失败")
            self._apps = {}
    
    def getRatio(self, app_name: str) -> float:
        """获取应用的积分换算比例
        Args:
            app_name: 应用名称
        Returns:
            float: 换算比例，如果应用不存在返回默认值0.01
        """
        try:
            app = self._apps.get(app_name)
            if app:
                return float(app['ratio'])
            Log.w(f"应用[{app_name}]未配置，使用默认比例0.01")
            return 0.01
        except Exception as e:
            Log.ex(e, f"获取应用[{app_name}]换算比例失败")
            return 0.01
    
    def get_app_info(self, app_name: str) -> dict:
        """获取应用信息
        Args:
            app_name: 应用名称
        Returns:
            dict: 应用信息，不存在返回None
        """
        return self._apps.get(app_name)


# 全局单例
appMgr = SAppMgr() 