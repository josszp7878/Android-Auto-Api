# Android 自动化工具

基于无障碍服务的 Android 自动化工具，支持 Python 脚本控制。

## 更新日志

### 2024-12-19
#### 新增功能
1. 系统智能适配
   - 支持 Android/鸿蒙系统自动识别
   - 根据系统类型自动选择最佳启动方式
   - Android：使用系统服务接口
   - 鸿蒙：使用模拟点击方式

2. 电池优化
   - 添加电池优化白名单申请
   - 优化后台运行稳定性

3. Python 脚本增强
   - 新增 Tools 工具类
   - 智能应用启动接口
   - 完善异常处理和日志

## 使用说明

### Python 脚本示例
```python
from tools import Tools

# 打开应用（自动适配系统类型）
Tools.openApp("应用名称")
```

### 必要权限
1. 无障碍服务权限
2. 电池优化白名单
3. `QUERY_ALL_PACKAGES`：用于获取应用列表

### 系统要求
- Android 7.0+
- Python 3.x

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

### 新增功能

1. **截屏指令**：
   - 新增了“截屏”指令，允许通过Python脚本触发截屏操作。
   - 在`commands.py`中实现了指令解析。
   - 在`PythonServices.kt`中实现了截屏功能。

### 新的截屏功能

- 使用 `ScreenCapture` 服务进行截屏，不再依赖无障碍服务。
- 截屏结果以 Base64 编码的字符串形式返回，便于在应用中使用。

### 如何使用

1. 确保应用具有必要的权限，包括 `FOREGROUND_SERVICE` 和 `MEDIA_PROJECTION`。
2. 在需要截屏的地方调用 `PythonServices.takeScreenshot()` 方法。
3. 截屏结果将以 Base64 编码的字符串形式返回，可以用于显示或保存。

### 注意事项

- 确保在调用截屏功能之前，已经正确处理了 `MediaProjection` 的权限请求。
- `ScreenCapture` 服务需要在前台运行，以确保稳定性。

### 最近更新

## 2024-12-30 改进认证和日志系统

### 认证机制改进
- 移除了复杂的 auth 认证机制
- 改用 URL 查询参数直接传递设备 ID
- 简化了连接流程，提高了可靠性

### 事件处理优化
- 将 Socket.IO 事件处理器注册移至初始化阶段
- 使用装饰器直接绑定类方法
- 避免了重复注册，提升了性能

### 日志系统统一
- 统一了客户端和服务器端的日志实现
- 使用单例模式重构了日志类
- 支持文件日志和实时日志推送
- 移除了数据库日志存储，简化了架构

### 代码优化
- 清理了冗余代码和注释
- 统一了命名和编码风格
- 改进了错误处理

### 日志系统优化

### 1. 日志统一管理
- 将所有日志统一保存在服务器端
- 实现了日志的实时显示和历史查询
- 支持按设备ID筛选日志

### 2. 异常日志增强
- 添加了 Log.ex() 方法用于打印异常堆栈
- 统一了异常处理格式
- 提供了更详细的错误信息

### 3. Bug修复
1. 修复了设备状态判断问题
   - 设备登录状态(login)时才允许发送命令
   - 优化了状态切换逻辑

2. 修复了设备列表显示问题
   - 使用 Vue.set 确保响应式更新
   - 修复了设备状态和截图更新不及时的问题

3. 修复了日志显示问题
   - 支持查看离线设备的历史日志
   - 优化了日志实时刷新机制

### 4. 代码优化
1. 统一了日志接口
   ```python
   Log.i()  # 信息日志
   Log.w()  # 警告日志
   Log.e()  # 错误日志
   Log.ex() # 异常日志(带堆栈)
   ```

2. 优化了设备管理器
   - 使用单例模式确保状态一致性
   - 优化了设备状态同步机制

3. 改进了前端交互
   - 优化了设备状态显示
   - 改进了日志展示界面

## 重要更新
- CmdMgr类改进:
  - PythonServices改名为androidServices并设为私有成员变量
  - 添加androidServices的getter方法
  - 统一Android服务访问管理
  - 完善错误处理机制
