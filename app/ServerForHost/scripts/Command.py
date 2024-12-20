import re
from functools import wraps

command_registry = []

def command(pattern):
    def decorator(func):
        command_registry.append((pattern, func))
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        return wrapper
    return decorator

def parse_command(command_text):
    for pattern, func in command_registry:
        match = re.match(pattern, command_text)
        if match:
            params = match.groupdict()
            try:
                return func(**params)
            except Exception as e:
                return f"命令执行错误: {str(e)}"
    return "未知命令"

