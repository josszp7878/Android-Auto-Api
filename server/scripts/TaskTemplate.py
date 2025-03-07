from typing import Dict, Callable, Tuple, Any
from CTask import CTask

class TaskTemplate:
    """任务模板管理类"""
    
    @classmethod
    def _get_templates(cls) -> Dict[str, Dict]:
        """获取模板字典，如果不存在则创建"""
        if not hasattr(cls, '_templates_dict'):
            cls._templates_dict = {}
        return cls._templates_dict
    
    @classmethod
    def regTask(cls, alias: str):
        """注册任务模板装饰器"""
        def decorator(func: Callable[[dict], Tuple[Callable[[CTask], None], ...]]):
            # 获取函数名作为模板ID
            templateId = func.__name__
            
            # 预先调用 func 以获取返回的函数元组
            funcs = func({})
            if len(funcs) >= 4:
                startFunc, doFunc, endFunc, initFunc = funcs[:4]
            else:
                startFunc, doFunc, endFunc = funcs[:3]
                initFunc = None
            
            # 创建模板对象而不是字典
            class Template:
                def __init__(self):
                    self.taskName = templateId
                    self.alias = alias
                    self.start = startFunc
                    self.do = doFunc
                    self.end = endFunc
                    self.init = initFunc
            
            # 保存模板实例
            templates = cls._get_templates()
            if templateId not in templates:
                templates[templateId] = Template()
                import _Log
                # _Log.Log_.d(f"注册任务模板: {templateId}({alias})")
            
            return func
        return decorator
    
    @classmethod
    def getTemplate(cls, templateId: str) -> Any:
        """获取任务模板,支持模板ID或别名"""
        templates = cls._get_templates()
        
        # 先通过模板ID查找
        template = templates.get(templateId)
        if template:
            return template
            
        # 通过别名查找
        for tmpl in templates.values():
            if tmpl.alias == templateId:
                return tmpl
        return None


# 直接使用类方法作为装饰器
regTask = TaskTemplate.regTask
