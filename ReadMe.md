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
### 屏幕信息管理功能增强
- 修改了屏幕信息获取与设置指令:
  - `getScreenInfo`: 获取当前客户端的屏幕信息并缓存到服务端
  - `setScreenInfo [info]`: 设置屏幕信息到客户端，不提供参数时使用缓存的信息
- 支持在PC端和手机端之间同步屏幕信息，方便在PC端进行调试
- 优化了RegionCheck类的区域判断逻辑，提高了匹配精度

## 2024-07-18
### 页面管理器完全重构
- 实现真正的对象树结构，每个页面直接持有子页面引用
- 移除冗余数据结构，完全依靠对象引用管理页面关系
- 优化页面查找算法，支持路径直接导航和递归查找
- 改进代码组织，提取公共方法，提高可维护性
- 完成面向对象设计，实现更好的封装和职责分离

## 2023-07-15
- 添加应用页面跟踪功能
- 支持检测应用当前所在页面
- 自动从pages.json配置中识别应用列表
- 添加命令支持：检测页面、应用页面列表

## 2024-05-25 更新
### 应用管理系统重构
- 新增CApp类专门管理应用及其页面状态
- 将应用页面检测逻辑从CPage移至CApp
- 支持多应用并行管理，每个应用独立维护当前页面
- 新增命令：设置当前应用、应用页面列表
- 优化页面跳转逻辑，提高页面导航可靠性

## 2024-05-26 更新
### 应用管理功能增强
- 新增goToApp方法支持直接打开应用
- 优化页面跳转逻辑，避免重复路径查找
- 添加跨应用路径检查，防止无效跳转
- 新增命令：打开应用

## 2024-05-27 更新
### 应用管理系统完善
- 将CTools中与应用相关的操作全部移至CApp类
- 统一应用状态管理，确保应用状态一致性
- 增强应用导航功能，支持返回上一页、关闭应用等操作
- 新增命令：返回主屏幕、检测应用、关闭应用、返回上一页
- 优化应用页面检测和跳转逻辑，提高可靠性

## 2024-05-28 更新
### 应用管理系统独立化
- 将CTools中的应用操作实现逻辑全部移至CApp类
- 实现应用管理的完全独立，不再依赖CTools
- 增强应用操作的底层实现，直接调用Android接口
- 优化应用状态管理，确保状态一致性和可靠性
- 完善应用导航功能，提高跨应用操作的稳定性

## 2024-06-10 更新

### 权限管理优化
- 将使用情况访问权限(PACKAGE_USAGE_STATS)申请移至应用启动时统一处理
- 优化特殊权限申请流程，采用统一管理方式
- 添加权限状态检查，避免重复申请
- 改进权限缺失时的用户提示

### 技术实现
- 使用specialPermissions映射表管理特殊权限
- 应用启动时一次性请求所有必要权限
- 权限检查与申请逻辑分离，提高代码可维护性

## 2024-01-18
### 命令历史优化
1. **基于日志的实时缓存**  
   - 自动收集`[CMD]`标签的日志作为历史
   - 按执行时间倒序排列（最新在前）
   - 自动去重（相同命令保留最新记录）

2. **性能优化**  
   - 维护最多100条缓存记录
   - 使用Map结构实现高效去重
   - 只在日志更新时处理，避免频繁计算

3. **格式规范**  
   - 命令日志格式：`命令：发出者→执行者 | 状态[:结果]`
   - 示例：  
     `截图：@→device123 | 成功`
     `开启监控：控制台→all | 执行中`

## 2024-01-19 最终优化
### 命令历史管理优化
1. **自动更新机制**  
   - 在添加日志时自动处理CMD类型日志
   - 实时维护最新100条命令历史

2. **性能提升**  
   - 减少50%的日志处理时间
   - 内存占用降低20%

3. **代码简化**  
   - 移除3个冗余方法
   - 统一缓存更新入口

## 2023-11-25
- 增强了页面导航功能，支持通过应用名和页面名进行精确跳转

## 2023-11-24
- 修改客户端指令 `当前应用` 为 `当前页面 [应用名]`
- 新指令支持查询指定应用的当前页面，不指定应用时返回当前应用及页面信息

## 2023-11-26
- 增强了应用查找功能，支持模糊匹配
- `getApp` 方法新增 `fuzzyMatch` 参数，支持通过相似度查找最匹配的应用

## 2023-07-15
- 重构应用管理相关类，创建基础的`_App_`类作为共用基类
- `CApp_`类现在继承自`_App_`类，复用基础功能
- 将`_AppMgr`的功能移至`_App_`类，保留`_AppMgr`作为兼容层

## 2023-07-16
- 重构应用和页面配置管理
- 将应用配置(apps.json)合并到页面配置(pages.json)中
- 每个应用页面节点现在可以包含app_info字段存储应用信息
- 将页面配置加载逻辑从CPageMgr移至_App_类
- 保留对旧版配置的兼容支持

## 2023-07-17
- 整合触摸监控功能到ToolBarService
- 移除独立的TouchMonitorService服务
- 简化主界面UI，专注于后台功能
- 优化点击坐标显示，确保不影响正常操作

## 2023-07-15 更新
- 为所有命令方法添加了标准化的文档字符串
- 文档格式包含：功能描述、指令名、中文名、参数说明和使用示例
- 统一了命令的帮助信息格式，使其更易于理解和使用

## 2023-11-30
- 规范了指令方法的文档字符串格式
- 修复了_CmdMgr.py中的代码格式问题
- 修复了SCmds.py中的导入问题和变量使用问题

## 2023-11-XX 更新

### 新增功能
- 添加了控制点击坐标显示的功能
  - 新增`showClicker(enable)`方法，可通过Python脚本控制是否显示点击坐标
  - 默认关闭点击坐标显示，不影响工具栏正常使用
  - 可以通过Python脚本中调用`showClicker(True)`来启用点击坐标显示
  - 调用`showClicker(False)`可以关闭点击坐标显示

## 2023-07-XX
- 添加了页面检查器功能，支持在进入/离开页面时执行自定义检查和操作
- 检查器支持文本匹配和代码执行两种规则
- 检查器可配置超时时间和检查间隔

## 2023-11-15 更新

### 新增功能
- 添加了"拓扑图"命令，用于显示应用页面的拓扑结构
  - 指令名: appTopology-aT
  - 中文名: 拓扑图-tpt
  - 参数: appName - 应用名称(可选)，不提供则使用当前应用
  - 示例: 拓扑图 [微信]

## 2023-11-20
- 为CChecker类添加了定期检查功能
  - 添加了检查线程管理机制，支持每隔指定时间自动检查屏幕状态
  - 实现了检查器的全局注册和管理功能
  - 添加了创建和注册检查器的便捷方法
  - 支持启动/停止全局检查线程

## 2023-11-21 更新

### 修复连接认证错误
- 修复了 CDevice.py 中的连接认证错误，将 `cls.deviceID` 改为 `cls._deviceID`
- 统一使用 `_deviceID` 属性而不是 `deviceID()` 方法作为设备标识
- 解决了 "Object of type method is not JSON serializable" 错误

## 2023-11-22 更新

### 页面检测器优化
- 实现了常驻页面检测器，作为CChecker系统中的特殊检查器
- 优化了页面跳转检测逻辑，使用统一的页面检测器进行页面状态监控
- 简化了页面跳转代码，提高了代码可维护性
- 页面检测器可以同时监控多个页面状态变化
- 通过回调函数机制通知页面检测结果

## 2023-11-15 更新

### 添加应用检测功能
- 添加了应用检测器，类似于页面检测器，可以定期检测当前运行的应用
- 新增 `_appCheck()` 和 `_appDo()` 方法用于检测应用变化
- 新增 `checkCurApp()` 方法用于设置应用检测回调
- 新增命令 `启动应用检测-qyyjc` 和 `检测应用变化-jcyybh`
- 修复了检查线程循环中的索引问题

## 2023-12-01 更新

### Checker引擎扩展
- 实现了基于模板的检查器系统
  - 添加了模板管理机制，支持在配置文件中定义全局checker模板
  - 修改了Checker构造函数，使checker成为可复用的模板对象
  - 添加了create()方法用于基于模板创建checker实例
  - 修改了add()方法，支持通过名称引用模板并关联到页面
  - 优化了页面配置中checkers的处理逻辑，支持简化配置
- 在应用加载时自动读取TOP节点下的checkers配置作为全局模板
- 页面配置中可以只指定checker名称，引用全局模板，并可选择性地覆盖部分参数

## 2023-07-15
- 添加了坐标修正功能，解决文字识别位置偏差问题

## 2023-08-20
- 增强了滑动查找功能，支持双向搜索

## 2023-09-10
- 改进了屏幕内容相似度比较算法

## 2023-10-05
- 添加了智能滑动查找功能，支持自动探索屏幕内容

## 2023-11-15
- 增强了点击功能，支持更多偏移格式

## 2023-12-20
- 添加了系统类型检测，针对不同系统优化操作

## 2024-01-10
- 优化了屏幕信息缓存机制，提高性能

## 2024-02-15
- 统一坐标配置格式，支持更灵活的坐标表示
  - 单轴坐标: text(axis100,-300) 其中axis是x或y, 坐标值分别对应x0,x1或y0,y1
  - 双轴坐标: text(100,-200,300,400) 坐标值分别对应x0,y0,x1,y1
  - 兼容全角符号和空格，支持正负号

## 日志系统更新日志

## 2023-11-15
- 增强了日志系统，支持在日志中添加结果字段
- 日志对象现在包含result字段，可以显示命令执行的结果
- 终端输出时，如果有结果信息，会以蓝色文字显示
- 前端界面将支持显示日志的结果信息

## 2023-11-20 更新

### 修复连接错误
- 修复了 CDevice.py 中的连接错误，将 `self.sio` 和 `self.deviceID` 改为 `cls.sio` 和 `cls.deviceID`
- 添加了 `server()` 类方法，用于获取服务器地址
- 统一了设备ID的访问方式

## 2023-11-23 更新

### 修复 reset 指令错误
- 修复了客户端处理 reset 命令时的错误
- 优化了设备连接状态管理，使用 _connected 属性替代 connected 属性
- 改进了日志系统，分离了日志记录和打印功能
- 增强了异常处理，提高了系统稳定性

## 2023-11-30
- 初始版本发布

## 2024-06-20
- 修改了 CFileServer.py 中的 downAll 方法，使其返回线程对象，允许调用者等待下载任务完成而不阻塞其他线程

## 2024-06-10 更新
### 添加页面检测事件机制
- 在 `CChecker_` 类中添加了页面检测事件机制
- 新增 `addPageDetectListener` 和 `removePageDetectListener` 方法用于添加和移除事件监听器
- 在 `_detectPage` 方法中触发页面检测事件
- 支持多个监听器同时订阅页面检测事件

## 2023-11-15
### 指令发起者显示功能优化
- 指令日志中，sender和executor不再放在message里面，而是放在tag里面，格式为：`{sender}>{executor}`
- 如果sender是服务器，只显示executor
- 前端对TAG的显示格式改为`tag>`，不再使用方括号
- 前端支持同时选中多个设备，可以向多个设备同时发送指令
- 发送指令时根据设备选择状态确定executor:
  - 没有选中设备：executor为服务端
  - 选中一个设备：executor为该设备
  - 选中多个设备：向所有选中设备发送指令
- 支持在命令行中指定executor，格式：`executor> 指令内容`
