# Android Accessibility API Demo

## 目录结构

```
server/
  └── scripts/           # Python脚本目录
       ├── main.py       # 主入口脚本
       ├── task_manager.py  # 任务管理器
       └── tasks/        # 具体任务实现目录
```

## 架构设计

项目采用双层架构设计:

### 1. 服务层 (Java/Kotlin)
提供底层基础功能服务接口:
- 界面操作 (点击、滑动、输入文本等)
- 系统功能 (截屏、文字识别、应用切换、应用安装等)
- 无障碍服务管理
- 权限管理

### 2. 业务层 (Python)
- 通过Python脚本实现具体业务逻辑
- 统一入口函数main()
- 可以调用服务层提供的所有功能接口
- 支持模块化任务组织

## 脚本执行流程
1. 应用启动初始化ScriptEngine
2. 加载Python运行环境
3. 自动执行main()入口函数
4. Python脚本可调用所有已注册的Java服务接口

## Python脚本开发指南

### 目录说明
- main.py: 主入口文件，包含main()函数
- task_manager.py: 任务管理器实现
- tasks/: 存放具体任务实现的目录

### 任务管理
- 使用TaskManager类管理所有任务
- 通过register_task注册新任务
- 使用run_task执行指定任务

### 示例代码

```python
def my_task():
    # 实现任务逻辑
    return "Task result"

# 注册任务
task_manager.register_task("my_task", my_task)

# 执行任务
result = task_manager.run_task("my_task")
```

### 日志记录
使用Android日志系统记录信息：
```python
from android.util.Log import i, d, e
i("TAG", "Info message")
d("TAG", "Debug message")
e("TAG", "Error message")
```
