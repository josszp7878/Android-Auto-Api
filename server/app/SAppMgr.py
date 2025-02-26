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
        
    def get_app_names(self) -> list:
        """获取所有应用名称列表
        Returns:
            list: 应用名称列表
        """
        return list(self._apps.keys()) if self._apps else []
        
    def app_exists(self, app_name: str) -> bool:
        """检查应用是否存在
        Args:
            app_name: 应用名称
        Returns:
            bool: 应用是否存在
        """
        return app_name in self._apps if self._apps else False

    def getApp(self, app_name: str) -> str:
        """根据输入的应用名模糊匹配最相近的应用
        Args:
            app_name: 用户输入的应用名
        Returns:
            str: 匹配到的应用名，如果没有匹配到返回None
        """
        try:
            if not app_name or not self._apps:
                return None
            
            # 如果完全匹配，直接返回
            if app_name in self._apps:
                return app_name
            
            # 模糊匹配：检查输入是否是某个应用名的子串
            matches = []
            for name in self._apps.keys():
                # 计算相似度：如果输入是应用名的子串，或应用名是输入的子串
                if app_name in name or name in app_name:
                    # 计算匹配度：子串在全串中的比例
                    similarity = len(app_name) / len(name) if len(name) > 0 else 0
                    matches.append((name, similarity))
            
            # 按相似度排序，取最匹配的
            if matches:
                matches.sort(key=lambda x: x[1], reverse=True)
                Log.i(f"应用[{app_name}]模糊匹配到[{matches[0][0]}]")
                return matches[0][0]
            
            return None
        except Exception as e:
            Log.ex(e, f"模糊匹配应用[{app_name}]失败")
            return None


# 全局单例
appMgr = SAppMgr() 