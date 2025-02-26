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

### 2025-01-10 新增功能

#### 新增 FindUI 指令
- 新增了 `FindUI(pattern)` 指令，用于获取屏幕上符合指定文字模式的中心位置。
- 如果未找到符合条件的文字，返回 `None`。
- 该功能增强了对屏幕元素的识别和定位能力，便于自动化操作。

### 2025-10-15 更新
- 将设置服务器 IP 和设备名的逻辑从 `MainActivity` 移动到 `ToolBarService`。
- `ToolBarService` 启动时会检查是否已设置设备信息，未设置则自动弹出设置对话框。
- `ToolBarService` 的按钮点击事件已实现：`startStopButton` 用于启动/停止脚本引擎，`settingsButton` 用于打开设置对话框。

### 2025-10-16 更新
- 将 `SERVER_NAME_KEY` 和 `DEVICE_NAME_KEY` 移动到 `ToolBarService`。
- 将 `MainActivity` 中的 `enter` 方法逻辑移动到 `ToolBarService`，并重命名为 `startScriptEngine`。

### 2025-10-20 更新
- 修改了悬浮工具栏的样式：
  - 将按钮文字替换为图标。
  - 工具栏支持收缩和展开功能，默认显示一个按钮，点击后展开，再次点击收缩。
  - 添加了收缩和展开的动画效果。

### 2025-10-21 更新

1. **`ToolBarService.kt` 更新**
   - 将 `isRunning` 属性包装成一个带有自定义 `setter` 的属性，并在 `setter` 中更新按钮图标。
   - 确保点击工具栏上的开始按钮后，按钮图标会切换为停止图标。

2. **`MainActivity.kt` 更新**
   - 恢复了 `startAccessibilityService()` 函数，用于启动或检查 `AppAccessibilityService` 的状态。
   - 确保在应用启动时检查无障碍服务的状态，并在未启用时引导用户到设置页面。

3. **`Cmds.py` 更新**
   - 修改了 `click` 函数的逻辑：
     - 参数匹配改为能匹配任何字符串。
     - 解析参数为坐标形式（两个隔开的数字），如果匹配成功，执行现有的点击逻辑。
     - 如果坐标匹配失败，将参数当成 UI 名称处理，使用 `findUI` 获取坐标并执行点击操作。
   - 修复了 `_findUI` 函数中 `position` 的定义错误，将其从 `set` 改为 `tuple`，以便通过索引访问。

这些更新提高了应用的功能性和稳定性，确保在不同场景下的正确操作。

### 2023-10-XX
- 新增 `STask` 类与数据库表的映射。
  - 使用 SQLAlchemy 将 `STask` 类映射到数据库表 `tasks`。
  - 支持任务的创建、更新进度、完成和取消操作。

### 2023-10-15
- 客户端 `onS2C_DoCmd` 函数更新，支持从服务端接收 `data` 参数。
- `CCmdMgr` 的 `do` 方法更新，支持处理 `data_params` 参数，并在命令执行时传递给命令处理函数。
- `startTask` 指令中增加了 `progress` 参数，客户端在开始任务时可以从该参数获取初始进度。

### 2024-01-20
- 重构任务分数更新机制
  - 将 todayTaskScore 和 totalScore 的更新逻辑整合到 STask.refresh() 方法中
  - 每次任务状态更新时自动刷新分数信息
  - 优化了前端分数显示的实时更新机制

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
   - 新增了"截屏"指令，允许通过Python脚本触发截屏操作。
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

## 2024-01-04 命令历史显示优化

### 功能更新
1. 重新设计了命令历史的显示格式
   - 每条命令记录显示为两行
   - 第一行: `时间 命令发出者->命令执行者: 命令内容`
   - 第二行: `-- 执行结果`

2. 调整了显示样式
   - 时间和发送者信息使用白色粗体显示
   - 命令内容使用绿色显示
   - 执行结果根据级别显示不同颜色:
     * 普通信息(i): 灰色
     * 警告信息(w): 黄色
     * 错误信息(e): 红色

3. 优化了命令响应处理
   - 响应格式: `level##content`
   - level: i(info), w(warning), e(error)
   - 自动根据响应内容判断级别

### 代码变更
1. 修改了CSS样式
   - 重新设计了命令历史的布局结构
   - 统一了颜色方案
   - 优化了时间戳显示

2. 更新了前端逻辑
   - 优化了命令发送和响应的处理流程
   - 统一了时间格式为 YYYY-MM-DD HH:mm:ss
   - 改进了命令历史的数据结构

3. 后端更新
   - 增加了响应级别的自动判断
   - 统一了响应格式

### 文件变更
- `server/app/static/css/dashboard.css`: 更新样式
- `server/app/static/js/dashboard.js`: 优化命令处理逻辑
- `server/app/templates/index.html`: 更新显示模板
- `server/app/command_history.py`: 增加响应级别处理

### 截图功能优化

1. 截图保存与显示
- 支持实时截图保存到服务器
- 自动更新设备监控界面的截图显示
- 使用时间戳命名避免缓存问题

2. 数据处理优化  
- 支持 base64 格式的图片数据
- 添加数据格式校验
- 优化图片存储路径管理

3. 界面交互改进
- 实时刷新设备截图
- 添加图片加载状态提示
- 支持点击查看大图

### Tesseract OCR 配置

为了支持中文识别，请确保在项目的 `assets/tessdata` 目录中包含以下语言数据文件：

- `chi_sim.traineddata`：用于简体中文识别

#### 配置步骤

1. 在 `app/src/main` 目录下创建 `assets` 目录。
2. 在 `assets` 目录下创建 `tessdata` 目录。
3. 将 `chi_sim.traineddata` 文件放置在 `tessdata` 目录中。

在代码中使用 Tesseract OCR 时，指定语言为 `chi_sim` 以进行中文识别。

## 2025-01-09 使用 Google ML Kit 实现 OCR

### 功能更新
1. 使用 Google ML Kit 实现 OCR，成功获取文字位置信息。
2. 更新了 `PythonServices.kt` 和 `Cmds.py` 以支持新的 OCR 功能。

## 2024-01-02 新增屏幕文本检查器

### 1. Checker类
- 支持正则表达式匹配屏幕文本
- 回调函数可访问完整匹配信息
- 支持链式调用创建检查器
- 集成错误处理和日志记录

### 2. 使用示例
```python
def handleMatch(checker: Checker) -> bool:
    amount = checker.matchParams.get('amount')
    print(f"匹配文本: {checker.matchText}")
    print(f"参数: {amount}")
    return True

checker = Checker.create(r"领取(?P<amount>\d+)金币").action(handleMatch)
checker.check()
```

### 3. 主要特性
- 支持命名捕获组提取参数
- 回调函数可访问完整匹配信息
- 自动处理异常并记录日志

## 2024-01-09 新增屏幕监控功能

### 功能说明
1. 新增屏幕监控指令
   - `开始监控 [间隔秒数]`: 启动定时截屏监控
   - `停止监控`: 停止屏幕监控
   - 默认监控间隔为5秒

2. 监控功能特性
   - 支持自定义监控间隔时间
   - 实时更新设备截图显示
   - 后台线程执行，不影响其他操作
   - 自动保存截图历史

3. 使用方法
   ```
   开始监控     # 使用默认5秒间隔
   开始监控 10  # 使用10秒间隔
   停止监控     # 停止当前监控
   ```

4. 注意事项
   - 建议根据网络状况调整监控间隔
   - 过于频繁的监控可能影响设备性能
   - 监控期间产生的截图会占用存储空间

## 2024-03-21 更新
### 新增功能
- 添加收益记录表(earnings)用于记录设备的积分和现金收益
- 字段包括:设备ID、应用名、收益类型(score/cash)、收益数量、时间
- 提供Add方法用于添加收益记录
- 提供Load方法用于加载和统计收益记录

## 2023-11-15 更新

### 新增功能
- 添加了打开应用指令 `@openapp <应用名>`
  - 检查应用是否存在
  - 向客户端发送打开应用命令
  - 设置当前设备的当前应用名

## 2023-11-16 更新

### 新增功能
- 扩充应用配置数据库，新增多款流行的刷广告赚金币应用：
  - 抖音极速版 (33000:1)
  - 快手极速版 (10000:1)
  - 今日头条极速版 (33000:1)
  - 番茄小说 (10000:1)
  - 趣头条 (9000:1)
  - 淘宝特价版 (10000:1)
  - 京东极速版 (10000:1)
  - 以及更多热门应用...
- 优化了应用管理器，支持更多应用的自动化操作
- 使用 `@apps` 命令可以查看所有支持的应用列表
