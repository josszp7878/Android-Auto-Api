# Android 自动化工具

基于无障碍服务的 Android 自动化工具，支持 Python 脚本控制。

## 更新日志

### 2023-10-20
#### 代码优化
1. 将CChecker中的registerCommands方法合并到CCmds中
   - 提高代码维护性
   - 使热加载更加方便
   - 集中管理命令注册逻辑

2. 修复Flask应用上下文错误
   - 添加_safe_db_import函数安全导入数据库模块
   - 改进_CmdMgr的错误处理机制
   - 增强registerCommands方法对异常的捕获和处理
   - 防止单个模块的错误影响整个命令注册流程

3. 修复inspect.getmembers导致的SQLAlchemy错误
   - 移除对inspect.getmembers的依赖，使用直接的属性访问代替
   - 优化对registerCommands方法的获取逻辑
   - 在处理SQLAlchemy相关错误时提供更明确的错误消息
   - 确保在没有Flask应用上下文时也能正常注册命令

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
- `CmdMgr` 的 `do` 方法更新，支持处理 `data_params` 参数，并在命令执行时传递给命令处理函数。
- `startTask` 指令中增加了 `progress` 参数，客户端在开始任务时可以从该参数获取初始进度。

### 2024-01-20
- 重构任务分数更新机制
  - 将 todayTaskScore 和 totalScore 的更新逻辑整合到 STask.refresh() 方法中
  - 每次任务状态更新时自动刷新分数信息
  - 优化了前端分数显示的实时更新机制

### 2024-05-15
- 修复命令执行错误问题
  - 修复了执行命令时出现的`unexpected keyword argument 'data'`错误
  - 在传递参数前检查函数是否接受`data`参数，只有当函数定义中包含该参数时才会传递
  - 使用`inspect.signature`检查函数参数列表，提高了命令执行的稳定性

### 2024-05-20
#### 配置文件结构优化
- 将pages.json中的match配置移至Checks.json
  - 重构了页面检测的实现机制
  - 将所有页面匹配条件统一存储在Checks.json中
  - 页面配置通过checkers字段引用相应的检查器
  - 提高了配置复用性和可维护性
  - 简化了pages.json文件结构

### 2024-05-25
#### 页面检查器系统升级
- 将页面的checkers配置统一到CChecker中管理
  - 创建了PageCheckers.json配置文件存储页面与检查器的关联关系
  - 每个页面可以通过命令动态添加、删除检查器
  - 页面匹配检测逻辑优化，支持检查器参数覆盖
  - 提供了一系列命令用于页面检查器管理：
    * `页面检查器 应用名/页面名`：查看页面配置的检查器
    * `添加页面检查器 应用名/页面名 检查器名`：为页面添加检查器
    * `删除页面检查器 应用名/页面名 检查器名`：从页面删除检查器
    * `检查器列表`：查看所有可用的检查器
  - 页面配置进一步简化，只需关注页面之间的跳转关系

### 2024-05-30
#### Checkers结构优化
- 简化了checker配置结构
  - 将checkers从{检查器名: 参数}格式简化为[检查器名]数组格式
  - PageCheckers.json中只保存检查器名称列表，不再存储参数
  - 参数统一在Checks.json中配置，提高复用性
  - 减小了配置文件体积，提高加载效率
  - 命令接口简化，添加检查器不再需要提供参数

### 2024-06-01
#### 完全移除旧配置格式兼容
- 移除了checkers结构的旧格式兼容代码
  - 不再支持字典格式的checkers配置
  - 所有页面配置统一使用数组格式存储检查器列表
  - 更新了pages.json中所有检查器配置为新格式
  - 简化了代码逻辑，提高了可维护性
  - 统一了配置格式，降低了学习成本

### 2025-10-25 更新

#### 日志系统优化
1. **输入区域高度优化**
   - 将输入区域高度固定为两到三行大小，提高界面空间利用率

2. **日志窗口可调整大小**
   - 日志窗口左边边缘设计成可拖动，用户可自由调整窗口大小
   - 添加了平滑的拖动效果和视觉反馈

3. **日志界面结构优化**
   - 日志标题按钮归属于日志页面容器，停靠在上方
   - 改进了日志面板的整体布局和视觉效果

4. **日志搜索过滤功能**
   - 在日志标题同行右侧添加搜索功能，支持输入过滤字符串
   - 实时过滤当前显示的日志内容

5. **多种过滤模式支持**
   - `@设备名`: 按设备名过滤日志
   - `:TAG`: 按照TAG标签过滤日志
   - `*正则`: 使用正则表达式匹配日志
   - 普通文本: 按照包含文本来过滤日志

### 2024-03-20
新增增强版文字查找功能：
- 新增`findText(text, searchDir, distance)`方法
- 支持在滑动屏幕过程中持续查找文字
- 自动处理滑动方向切换和屏幕边界判断
- 支持相似度计算避免无效滑动

### 2024-03-21
新增测试指令：
- `测试查找 文字 [方向] [距离]` 用于验证增强版文字查找功能
- 支持自动滑动屏幕并返回坐标
- 示例：`测试查找 下一步 LR 500`

### 2024-03-22
# 指令系统增强
- 增强指令注册机制，支持两种模式：
  - **传统模式**：`@regCmd(命令, 缩写, 参数正则)` 适合简单指令
  - **完整正则模式**：`@regCmd(完整正则)` 支持自然语言指令
- 自动优先匹配完整正则模式指令
- 支持正则命名捕获组提取参数
- 完全兼容现有指令写法

### 2024-03-21
# 新增功能
- 添加 `appPosition` 指令，支持自然语言格式如"支付宝的位置"
- 优化指令参数解析逻辑

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

## 2023-11-17 更新

### 代码重构
- 将系统工具方法从 `CmdMgr` 移动到 `Tools` 类
  - `isHarmonyOS()`: 检测设备是否运行鸿蒙系统
  - `openApp()`: 智能打开应用，根据系统类型选择最佳方式
  - `_openAppByClick()`: 通过模拟点击方式打开应用（鸿蒙系统专用）
- 优化了代码结构，提高了可维护性和复用性
- 统一了工具方法的调用方式，使用 `Tools.方法名()` 进行调用

## 2023-11-18 更新

### 进一步简化了控制界面
  - 移除了命令历史相关的所有代码和功能
  - 优化了日志显示和处理逻辑
  - 减少了不必要的事件处理和数据传输
  - 提高了界面响应速度和用户体验

## 2023-11-19
- 改进了日志面板的布局和交互
  - 将日志面板从上下展开改为左右展开
  - 日志面板现在位于页面右侧，占据屏幕宽度的三分之一
  - 添加了平滑的过渡动画，提升用户体验
  - 优化了日志面板的样式和可读性

## 2024-03-xx
- 新增"当前应用"指令,用于获取当前正在运行的应用信息
- 支持显示应用名称和包名

## 2024-03-xx
- 修复设备状态显示问题
  - 确保页面刷新时所有设备显示为离线状态
  - 只有收到服务器更新才会显示为在线状态
  - 恢复选中设备的绿色边框高亮效果

## 2024-03-xx
- 优化设备选择状态同步
  - 支持服务器初始化时指定当前设备
  - 页面加载时自动选中当前设备
  - 自动显示当前设备的日志面板

## 2024-03-05 日志系统优化
- 修复前端日志年份显示缺失问题
- 简化日志传输逻辑，服务器直接发送结构化日志数据到前端，前端无需解析日志字符串
- 优化日志显示性能，减少前端处理开销

## 2024-03-06 日志存储优化
- 日志存储格式改为JSON Lines格式（每行一个JSON对象）
- 优化日志文件可读性和解析效率
- 支持更灵活的日志字段扩展
- 保持与旧版日志格式的兼容性

### 2024-03-21 更新

**问题修复：**
- 修复Context获取接口缺失问题
- 完善Android上下文获取机制
- 优化跨语言调用稳定性

### 2024-03-24 更新

**权限问题修复：**
1. 正确跳转使用情况访问设置页
2. 添加权限申请后的自动重试机制
3. 增加明确的用户引导提示

**操作指南：**
1. 当出现权限提示时，请务必在系统设置中：
   - 找到本应用（可能显示为系统服务名称）
   - 开启「允许使用访问记录」开关
   - 返回应用后等待5秒自动重试
2. 如果跳转错误，请手动前往：
   设置 → 应用 → 特殊应用权限 → 使用情况访问权限

### 2024-03-25 更新

**权限系统完善：**
1. 修复使用情况权限跳转问题
2. 添加精准权限名称提示
3. 增强权限重试机制（最多3次）
4. 延长用户操作等待时间至8秒

**必要配置：**
```xml
<!-- 在AndroidManifest.xml中添加 -->
<uses-permission android:name="android.permission.PACKAGE_USAGE_STATS"/>
```

**调试建议：**
```python
# 检查权限状态
has_perm = CTools.android.checkPermission("android.permission.PACKAGE_USAGE_STATS")
print(f"使用情况权限状态: {'已授予' if has_perm else '未授予'}")
```

### 2024-02-20
新增功能：
- 添加屏幕应用分析功能
- 新增`分析屏幕`命令，可识别屏幕上的应用并记录到数据库
- 新增AppModel数据库表存储应用信息

### 2024-02-21 更新
功能优化：
- 增强屏幕应用识别功能
- 使用应用特征库进行精准匹配
- 新增应用管理器(SAppMgr)维护已知应用特征
- 分析结果只记录已知应用

## 2023-07-15 更新

### 新增功能
- 添加获取当前前台应用包名功能 `getCurrentPackage()`
- 添加判断当前是否在桌面的功能 `isOnHomeScreen()`
- 添加获取根节点的功能 `getRootNode()`

### 技术细节
- 使用多种方法检测当前前台应用，提高兼容性
- 通过包名列表和UI特征双重检测桌面状态，适配不同厂商手机
- 支持主流Android厂商的桌面应用检测

## 2024-05-20 更新
### 测试功能增强
- 新增路径查找测试命令 `查找路径 起点->终点`
- 支持查看拓扑结构关系
- 添加性能监控指标
- 示例用法：
  ```
  查找路径 Top->安装页
  查找路径 搜索页->Top
  ```

## 区域配置说明

### 格式规则（新增简写）
1. **传统格式**  
   `[x_min, x_max, y_min, y_max]`  
   - `[100]` → x≥100  
   - `[0,100,50,200]` → 0≤x≤100且50≤y≤200  

2. **Y轴专用格式**（适用于只限制Y轴）  
   - `y100` → y≥100  
   - `y100,200` → 100≤y≤200  

3. **X轴专用格式**（适用于只限制X轴）  
   - `x100` → x≥100  
   - `x100,200` → 100≤x≤200  



### 多行配置说明
1. **数组元素换行**：使用标准JSON数组格式
   ```json
   "check": [
       "生活[y0,300]",
       "同城[y0,300]",
       "关注[y0,300]",
       "发现[y0,300]",
       "我的[y0,300]"
   ]
   ```
2. **单元素多行**：使用反斜杠转义
   ```json
   "check": ["文本\\n带换行[y0,300]"]
   ```
3. **自动处理**：系统会自动去除首尾空白和换行符

### 负数配置说明
- **X轴负值**：表示屏幕宽度减去绝对值  
  `x-100` → 屏幕右侧100像素处
- **Y轴负值**：表示屏幕高度减去绝对值  
  `y-200` → 屏幕底部200像素处

**使用示例：**
```python
# 右侧100像素区域
CTools.check_region(900, 500, "[x-100]")  # 当屏幕宽度为1080时，等效x≥980

# 底部区域
CTools.check_region(500, 1600, "y-200")  # 当屏幕高度为1920时，等效y≥1720

# 混合配置
CTools.check_region(800, 1000, "[x-300,-100 y500,-50]") 
# 解释：
# x范围：屏幕宽度-300 到 屏幕宽度-100
# y范围：500 到 屏幕高度-50
```

## 2023-11-15 更新
- 增加服务器连接超时处理
- 添加连接服务器时的状态提示
- 优化文件同步失败时的错误提示

## 2023-11-20 更新

### 性能优化
- 添加脚本名称缓存功能，优化`getScriptName`调用性能
- 在下载脚本文件后自动清除缓存，确保使用最新的脚本文件

## 2023-07-15
- 添加了客户端eval指令，用于调用CPageMgr中的_eval方法并返回结果
- 使用方法: eval <代码>
- 此功能方便进行代码测试和调试

## 2024-07-16
### 新增功能
- 添加服务端屏幕信息设置指令
  - `setScreenInfo <屏幕信息JSON>`: 设置屏幕信息缓存
  - `getScreenInfo`: 获取当前屏幕信息缓存
- 这些指令主要用于PC端调试，可以将手机上获取的屏幕信息用于PC端模拟测试
- 优化了RegionCheck类的区域判断逻辑，提高了日志可读性

## 2024-07-17
### 新增配置管理功能
- 新增Checks.json配置文件，存储检查器模板配置
- 支持配置的加载、保存、增删改查操作
- 配置项自动过滤默认值，保持文件精简
- 新增check方法快速启动检查器并覆盖参数

### 优化检查器逻辑
- 增加DEFAULT_CONFIG统一管理默认配置
- 初始化时自动合并默认配置和自定义配置
- 支持运行时动态修改检查器参数

## 2024-07-18 更新

### 新增检查器管理指令
1. **检查编辑 [名称]**  
   - 功能：进入检查器编辑模式，创建配置副本
   - 别名：jcbj
   - 示例：检查编辑 每日签到

2. **编辑检查 [规则] [操作]**  
   - 功能：修改当前编辑中的检查规则和操作
   - 别名：bjjc
   - 参数：规则-str 操作-JSON字符串
   - 示例：编辑检查 "广告&成功" '{"立即领取":"click"}'

3. **结束编辑 [取消标志]**  
   - 功能：保存(0)或取消(1)编辑结果
   - 别名：jsbj
   - 示例：结束编辑 0

4. **删除检查 [名称]**  
   - 功能：永久删除指定检查器配置
   - 别名：scjc
   - 示例：删除检查 过期活动

5. **检查列表**  
   - 功能：列出所有已配置的检查器
   - 别名：jclb
   - 示例：检查列表
