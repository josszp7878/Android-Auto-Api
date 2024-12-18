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

## Python API 接口说明

### 屏幕操作
```python
import android_services

# 点击屏幕指定位置
# 参数: x, y 坐标
# 返回: bool 是否点击成功
result = android_services.click_position(x, y)

# 获取屏幕文本
# 返回: List[str] 屏幕上的所有文本列表
texts = android_services.get_screen_text()
```

### 示例代码
```python
def click_and_read():
    # 点击屏幕(100, 200)位置
    if android_services.click_position(100, 200):
        # 获取点击后的屏幕文本
        texts = android_services.get_screen_text()
        for text in texts:
            print(f"Found text: {text}")
```

## 更新日志

### 直接调用Java服务接口

在本阶段，我们简化了Python与Java之间的交互，移除了复杂的模块注册机制，直接在Python中调用Java类的静态方法。以下是主要的更改：

1. **移除模块注册**：
   - 删除了`RegisterPythonService`注解和相关的模块注册代码。
   - 简化了`ScriptEngine`类，去掉了不必要的模块注册逻辑。

2. **直接调用Java类**：
   - 在`PythonServices.kt`中，使用`@JvmStatic`注解标记静态方法，以便在Java和Python中直接调用。
   - 在`main.py`中，直接通过`jclass`导入`PythonServices`类，并调用其静态方法。

3. **示例代码**：
   - 在`main.py`中，提供了如何直接调用`clickPosition`和`getScreenText`方法的示例。

### 如何使用

- 确保在`PythonServices.kt`中，所有需要从Python调用的方法都使用`@JvmStatic`注解。
- 在Python脚本中，使用`jclass`导入Java类，并直接调用静态方法。

### 提交代码

请确保在提交代码之前，所有更改都已测试通过，并且代码库处于稳定状态。使用以下命令提交代码到Git：

```bash
git add .
git commit -m "Simplified Java-Python interaction by removing module registration and using direct class method calls"
git push origin main
```
