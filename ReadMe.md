# Android Auto API

## 更更新日志

### 2025-01-23 - 设备应用加载逻辑优化

#### SDevice应用初始化流程重构
- #优化_loadApps()方法：统一应用创建和数据初始化流程
  - 步骤0：获取数据库应用数据 `records = AppModel_.all(deviceId)`
  - 步骤1：根据应用名称列表创建所有应用 `appNames = _App_.getAppNames()`
  - 步骤2：用数据库记录初始化对应应用的数据
  - 流程优化：确保所有配置的应用都被创建，不管数据库是否有记录

#### 应用数据初始化策略调整
- #从条件分支改为统一流程：移除if-else分支判断
  - 原逻辑：有records则从数据库加载，无records则从配置创建
  - 新逻辑：先统一创建所有应用，再用数据库数据初始化存在的应用
  - 优势：确保应用列表完整性，避免因数据库状态导致应用缺失

#### 数据字典优化
- #使用recordsDict提升查找效率：`{record['name']: record for record in records}`
  - 性能提升：从O(n*m)降低到O(n+m)的查找复杂度
  - 代码简洁：通过字典查找替代嵌套循环
  - 内存优化：一次构建字典，多次高效查找

#### 日志完善
- #增强日志输出：提供更详细的初始化过程信息
  - 数据库记录数量：显示从数据库获取的记录数
  - 应用创建过程：记录每个应用的创建状态
  - 数据初始化统计：显示成功初始化数据的应用数量
  - 最终统计：显示总共加载的应用实例数量

#### 错误处理优化
- #保持异常处理机制：确保初始化失败不影响设备功能
  - 创建失败记录：单个应用创建失败不影响其他应用
  - 数据初始化安全：使用字典查找避免KeyError异常
  - 整体异常捕获：保持原有的异常处理和日志记录

### 2025-01-23 - 应用配置文件化管理

#### 新增Apps.json配置文件
- #创建Apps.json配置文件：统一管理项目支持的所有应用名称
  - 文件位置：`server/config/Apps.json`
  - 数据格式：JSON数组，包含所有支持的应用名称
  - 应用列表：微信、支付宝、抖音、快手、淘宝、京东、拼多多等20个主流应用
  - 维护方式：统一在配置文件中添加或删除支持的应用

#### 应用名称获取方式重构
- #重构_App_.getAppNames()方法：从配置文件加载应用名称并缓存
  - 变更前：`return list(cls.apps().keys())` - 从应用模板字典获取
  - 变更后：从Apps.json文件加载并缓存到类变量`_appNames`
  - 缓存机制：首次加载后缓存到类变量，提高后续访问效率
  - 错误处理：文件不存在或解析失败时返回空列表，记录警告日志

#### 新增应用名称加载方法
- #新增_App_._loadAppNames()静态方法：专门处理应用名称加载
  - 文件读取：使用UTF-8编码读取Apps.json文件
  - JSON解析：自动解析JSON数组格式的应用名称
  - 路径获取：使用`g.configDir('Apps.json')`获取配置文件路径
  - 日志记录：加载成功时记录应用数量，失败时记录异常信息

#### 设备应用初始化优化
- #优化SDevice_._loadApps()方法：应用创建逻辑简化
  - 变更前：`templates = _App_.apps()` / `for name, _ in templates.items()`
  - 变更后：`appNames = _App_.getAppNames()` / `for name in appNames`
  - 逻辑简化：直接使用应用名称列表创建，无需获取完整应用模板
  - 性能提升：避免创建不必要的应用模板对象
  - 依赖减少：减少对_App_.apps()方法的依赖

#### 配置文件管理优势
- #统一配置管理：所有应用配置集中在一个文件中
  - 易于维护：添加新应用只需在JSON文件中添加名称
  - 版本控制：配置文件可以纳入版本控制，方便追踪变更
  - 部署灵活：不同环境可以使用不同的应用配置文件
  - 热更新：配置文件变更后重启服务即可生效

#### 向下兼容
- #保持现有API接口不变：getAppNames()方法签名和返回值格式保持一致
  - 接口一致：`_App_.getAppNames()` 调用方式不变
  - 返回格式：仍然返回list类型的应用名称列表
  - 业务逻辑：其他依赖getAppNames()的代码无需修改

### 2025-01-23 - 客户端实时信息显示指令

#### 新增客户端实时状态指令
- #添加current()指令：显示客户端当前实时状态信息
  - 指令名：`current`、`当前信息`、`dqxx`
  - 功能：获取并显示设备、应用、任务的实时状态
  - 无参数：直接调用即可获取完整状态信息
  - 异常处理：完整的错误处理和异常捕获机制

#### 实时信息显示格式
- #标准化信息显示格式：提供结构化的状态信息展示
  - 设备信息：`设备：设备名（设备ID）`
  - 应用状态：`显示：当前应用名-当前的页面名`
  - 任务信息：`任务：任务名（任务状态，进度百分比%）`
  - 容错处理：当信息不可用时显示合理的默认值

#### 多重访问安全
- #使用getattr安全访问对象属性：防止属性不存在导致的异常
  - 设备属性：安全获取设备名称和ID，默认显示"未知设备"/"未知ID"
  - 应用属性：安全获取应用名称和页面名称，默认显示"未知应用"/"未知页面"
  - 任务属性：安全获取任务状态和进度，默认显示"无任务"
  - 状态处理：智能判断任务状态类型，支持枚举和字符串显示

#### 使用示例
- #支持的调用方式：
  ```
  # 中文指令
  当前信息
  
  # 中文缩写
  dqxx
  
  # 英文指令
  current
  ```

#### 输出示例
- #标准输出格式：
  ```
  设备：测试设备（device_001）
  显示：微信-聊天页面
  任务：签到任务（运行中，75%）
  ```

### 2025-01-23 - 前端RPC参数解析增强

#### 智能参数解析系统
- #完善RPC命令参数解析逻辑：支持多种参数格式和自动类型转换
  - JSON格式：`@SDevice_.getInfo {"id":"device1","timeout":5000}`
  - 键值对格式：`@SDevice_.getInfo id=device1,timeout=5000,name="测试设备"`
  - 混合格式：`@SDevice_.method param1,param2=value2,param3=123`
  - 容错处理：解析失败时自动降级为字符串参数

#### 参数分类和路由
- #智能参数分类：根据参数名自动分配到正确的位置
  - 特殊参数：`id`, `timeout` 直接放在params根级别
  - 业务参数：其他键值对参数放在`kwargs`对象中
  - 位置参数：无键名的参数放在`args`数组中
  - 格式示例：`{id: "123", timeout: 5000, args: ["param1"], kwargs: {name: "test"}}`

#### 自动类型转换
- #`_parseParamValue`方法：智能识别并转换参数数据类型
  - 字符串：支持单引号和双引号包围的字符串
  - 数字：自动识别整数和浮点数，支持负数
  - 布尔值：`true`/`false` 转换为布尔类型
  - 特殊值：`null`, `undefined` 转换为对应的JavaScript值
  - 数组：`[1,2,3]` 格式自动解析为数组
  - 对象：`{key:value}` 格式自动解析为对象

#### 使用示例
- #支持的RPC命令格式：
  ```
  # JSON格式参数
  @SDevice_.getInfo {"id":"device1","timeout":5000}
  
  # 键值对格式参数
  @SDevice_.updateName id=device1,name="新设备名",timeout=3000
  
  # 混合格式参数
  @STask_.updateScore device1,score=100,reason="完成任务"
  
  # 纯位置参数
  @SApp_.getScores device1,app1
  
  # 复杂参数类型
  @SDevice_.setBatch ids=[1,2,3],config={"auto":true},timeout=10000
  ```

#### 错误处理和容错
- #参数解析容错机制：确保命令执行的稳定性
  - JSON解析失败：自动降级为键值对解析
  - 键值对解析异常：将原始字符串作为args参数
  - 类型转换失败：保持原字符串形式
  - 警告日志：解析失败时记录警告信息，不中断命令执行

#### 向下兼容
- #保持现有RPC调用格式完全兼容：无需修改现有代码
  - 简单调用：`@SDevice_.getInfo` 无参数调用保持不变
  - 原有格式：所有现有的参数格式继续有效
  - 扩展支持：新增的格式作为增强功能，不影响原有使用

### 2025-01-23 - RPC功能整合到Socketer类

#### 代码结构优化
- #将RPC.js功能整合到Socketer类：简化前端代码结构，减少文件数量
  - 移除文件：删除独立的`RPC.js`文件
  - 功能迁移：将所有RPC相关功能迁移到`socketer.js`中的Socketer类
  - 类结构：添加静态方法`Socketer.rpcCall()`处理RPC调用
  - 向下兼容：保持全局`window.rpc.call()`接口不变

#### RPC功能重构
- #RPC请求ID管理：添加静态计数器`#rpcRequestIdCounter`
  - 唯一ID生成：`#generateRpcRequestId()`方法生成格式`rpc_{counter}_{timestamp}`
  - 避免冲突：确保每个RPC请求都有唯一标识符
  - 调试支持：便于在日志中跟踪特定的RPC调用

- #核心RPC调用方法：`Socketer.rpcCall(deviceId, className, methodName, params)`
  - 参数验证：检查Socket连接状态，连接失败时直接返回null
  - 超时控制：支持自定义超时时间，默认10000ms
  - 错误处理：统一处理RPC调用异常，返回null并记录错误日志
  - 性能监控：记录RPC调用执行时间，便于性能分析

- #RPC初始化：`Socketer.initRpc()`静态方法
  - 事件监听：注册`test_rpc_response`事件监听器
  - 状态检查：验证Socket连接状态
  - 日志输出：初始化成功时输出确认信息

#### 向下兼容保证
- #保持全局RPC接口：`window.rpc.call()`方法保持不变
  - 接口一致：现有的`rpc.call(deviceId, className, methodName, params)`调用方式完全兼容
  - 内部重定向：全局方法内部调用`Socketer.rpcCall()`
  - 无缝升级：现有代码无需修改，自动使用新的实现

#### 文件更新
- #HTML模板更新：移除对RPC.js的引用
  - `sheet.html`：移除`<script src="/static/js/RPC.js"></script>`
  - `rpc_test.html`：移除RPC.js引用，修正socketer.js路径大小写
  - 加载顺序：确保socketer.js在其他依赖脚本之前加载

#### 自动初始化
- #页面加载时自动初始化RPC系统
  - DOM就绪：使用`DOMContentLoaded`事件确保页面加载完成
  - 延迟初始化：1秒延迟确保Socket.IO连接建立
  - 测试事件：自动发送测试RPC事件验证连接

#### 影响范围
- #现有RPC调用保持不变：所有使用`rpc.call()`的代码继续正常工作
  - `sheet.js`：表格管理中的RPC调用
  - `BCmds.js`：前端命令中的RPC调用  
  - `rpc_test.html`：RPC测试页面
  - 其他模块：所有依赖RPC功能的前端代码

### 2025-01-23 - 客户端应用类CApp创建

#### 应用架构重构
- #创建专门的客户端应用类CApp_：分离客户端和服务端应用逻辑
  - 继承关系：CApp_继承自_App_，专门处理客户端特有功能
  - 文件位置：新建server/scripts/CApp.py文件
  - 设计目标：将客户端特有的方法从通用_App_类中分离出来
  - 好处：代码职责更加清晰，客户端和服务端逻辑分离

#### 客户端特有方法迁移
- #迁移LoadScore方法到CApp_：客户端收益数据加载功能
  - 功能：导航到收益页面，读取本地result.json文件
  - 特点：涉及页面导航和本地文件读取，明显的客户端操作
  - 实现：使用CScore_.loadScore()解析收益数据
  - 应用：只在客户端环境下有效的收益统计功能

- #迁移客户端版本_doUpdate方法：添加任务更新逻辑
  - 客户端特有：包含curTask = g.CDevice().curTask()和任务更新
  - 与通用版本区别：通用版本移除了客户端特有的任务更新部分
  - 更新流程：页面检测 → 路径处理 → 页面更新 → 任务更新
  - 职责分离：客户端处理本地任务，服务端处理全局管理

- #迁移客户端版本getScores RPC方法：实现客户端收益获取
  - RPC分工：服务端调用客户端获取数据，客户端执行实际操作
  - 客户端逻辑：直接调用LoadScore()方法获取收益数据
  - 服务端逻辑：保留在_App_类中，通过RPC调用客户端方法
  - 数据流向：客户端本地获取 → RPC传输 → 服务端处理存储

#### CDevice设备管理更新
- #修改CDevice_.setApps方法：使用CApp_替代_App_
  - 变更前：from _App import _App_ / app = _App_(data)
  - 变更后：from CApp import CApp_ / app = CApp_(data)  
  - 一致性：与_createApp方法保持一致，都使用CApp_
  - 影响：客户端创建的所有应用实例都是CApp_类型

#### _App_通用类简化
- #移除_App_类中的客户端特有方法：保持通用性
  - 移除LoadScore方法：纯客户端功能，不应在通用类中
  - 简化_doUpdate方法：移除客户端特有的任务更新逻辑
  - 保留getScores方法：改为服务端版本，通过RPC调用客户端
  - 通用性：_App_类现在只包含通用的应用管理功能

#### 页面更新逻辑迁移
- #迁移页面和更新相关方法到CApp_：进一步分离客户端和服务端逻辑
  - 迁移_ToPage方法：页面导航功能，涉及Android操作，纯客户端功能
  - 迁移_clearPath方法：路径清理功能，配合页面导航使用
  - 迁移_updateGoPath方法：页面跳转逻辑处理，客户端页面管理核心
  - 迁移_update方法：全局应用更新循环，只在客户端环境下运行
  - 迁移update方法：启动更新循环线程，客户端应用生命周期管理

#### 服务端_App_类精简
- #移除服务端不需要的页面操作方法：保持通用类的纯净性
  - 移除页面导航：服务端不需要Android页面操作
  - 移除更新循环：服务端不需要持续的页面检测和更新
  - 保留配置管理：页面配置、应用管理等通用功能保留
  - 保留RPC方法：服务端仍需要提供RPC接口调用客户端

#### 向下兼容性保证
- #保持现有接口和功能不变：确保系统稳定运行
  - API兼容：所有RPC方法接口保持不变
  - 功能一致：客户端应用功能完全保持原有行为
  - 继承关系：CApp_继承_App_，拥有所有通用方法
  - 透明升级：现有代码无需修改，自动使用新的类结构

## 更更新日志

### 2025-01-23 - 屏幕信息管理RPC重构

#### 安全性改进：移除eval调用
- #将不安全的eval T.getScreenInfo(True)调用改为RPC调用：提升系统安全性
  - 问题：SCmds.py中直接使用eval执行客户端代码，存在安全风险
  - 原因：eval调用可能被恶意代码利用，造成安全漏洞
  - 解决：完全移除eval调用，改用安全的RPC通信机制
  - 好处：消除代码注入风险，提高系统安全性

#### RPC架构重构
- #在SDevice上实现屏幕信息管理RPC方法：统一服务端屏幕信息处理逻辑
  - 新增：`@classmethod @RPC() def getScreenInfo(cls, deviceID: int, pageName: str = None) -> dict`
  - 新增：`@classmethod @RPC() def setScreenInfo(cls, deviceID: int, pageName: str = None) -> dict`
  - 功能：通过RPC调用客户端方法，获取和设置屏幕信息
  - 文件管理：自动保存屏幕信息到JSON文件，支持页面名称区分
  - 错误处理：完整的异常处理和错误消息返回

- #在CDevice上实现屏幕信息RPC方法：提供客户端屏幕信息访问接口
  - 新增：`@RPC() def getScreenInfo(self) -> dict`：调用_Tools.getScreenInfo()获取实时屏幕信息
  - 新增：`@RPC() def setScreenInfo(self, screenInfos: list) -> dict`：调用_Tools.setScreenInfo()设置屏幕缓存
  - 封装：屏蔽底层工具类调用细节，提供统一的RPC接口
  - 验证：参数验证和工具类可用性检查

#### 文件管理优化
- #重构屏幕信息文件存储逻辑：提高文件操作的可靠性
  - 拆分方法：将原有方法拆分为`_saveScreenInfoToFile()`和`_loadScreenInfoFromFile()`
  - 目录管理：自动创建screenshots目录，确保文件路径有效
  - JSON处理：统一JSON格式化和解析逻辑，提高数据一致性
  - 缓存机制：维护`_lastScreenInfo`缓存，提高访问性能

#### 服务端指令更新
- #修改SCmds.py中的截屏和设置屏幕信息指令：改用RPC调用方式
  - getScreenInfo指令：改为调用`SDevice_.getScreenInfo` RPC方法
  - setScreenInfo指令：改为调用`SDevice_.setScreenInfo` RPC方法
  - 简化逻辑：移除复杂的回调处理，直接使用RPC返回值
  - 错误处理：统一的错误处理和用户友好的错误消息

#### 数据流向优化
- #建立完整的屏幕信息数据流：服务端 ↔ 客户端 ↔ 工具类
  - 获取流程：SCmds → SDevice RPC → CDevice RPC → _Tools.getScreenInfo() → 保存文件
  - 设置流程：SCmds → SDevice RPC → 加载文件 → CDevice RPC → _Tools.setScreenInfo()
  - 统一接口：所有屏幕信息操作都通过RPC接口，确保一致性
  - 错误传播：完整的错误信息传播链，便于问题诊断

#### 向下兼容性
- #保持用户指令接口不变：用户无需修改使用方式
  - 指令格式：`#截屏 页面名` 和 `#设置屏幕信息 页面名` 保持不变
  - 功能行为：屏幕信息获取和设置功能完全一致
  - 文件格式：JSON文件存储格式保持兼容
  - 性能提升：移除eval调用后，执行性能更好

### 2025-01-23 - 前端通知COPY功能增强

#### 通知界面COPY按钮功能
- #为前端showNotification方法添加COPY按钮：增强用户体验和内容管理功能
  - 界面改进：通知显示区域现在包含消息内容和COPY按钮
  - 布局优化：使用flex布局，消息内容和按钮分离显示
  - 按钮样式：蓝色COPY按钮，支持鼠标悬停效果
  - 交互流程：点击COPY按钮 → 复制到剪贴板 → 询问是否保存文件

#### 剪贴板操作支持
- #实现完整的剪贴板复制功能：支持现代浏览器和兼容性处理
  - 现代API：优先使用`navigator.clipboard.writeText()`方法
  - 兼容性处理：当现代API不可用时，自动回退到`document.execCommand('copy')`
  - 临时元素：创建不可见的textarea元素进行备用复制
  - 错误处理：复制失败时显示错误提示，引导用户手动复制

#### 文件保存功能
- #添加通知内容保存为文件功能：支持用户自定义文件名
  - 自动命名：默认文件名格式`notification_时间戳.txt`
  - 用户交互：使用prompt弹窗让用户输入文件名
  - 文件下载：通过Blob和URL.createObjectURL实现浏览器下载
  - 资源清理：下载完成后自动清理临时URL对象

#### 用户提示系统
- #实现临时提示消息系统：提供操作反馈和状态通知
  - 提示类型：成功(绿色)、错误(红色)、信息(蓝色)三种类型
  - 显示位置：固定在页面右上角，不遮挡其他内容
  - 自动消失：2秒后自动淡出并移除，无需用户手动关闭
  - 状态反馈：复制成功、文件保存成功、操作失败等状态及时反馈

#### 增强的用户体验
- #完整的操作流程设计：从内容显示到保存的完整用户体验
  - 一键复制：点击COPY按钮自动复制到剪贴板
  - 询问保存：复制成功后询问用户是否需要保存文件
  - 灵活选择：用户可以只复制不保存，或者同时完成两个操作
  - 错误恢复：任何步骤失败都有相应的错误提示和处理

#### 技术实现细节
- #使用现代Web API和向下兼容处理
  - Clipboard API：优先使用现代异步剪贴板API
  - File API：使用Blob和Object URL实现文件下载
  - DOM操作：动态创建UI元素和事件处理
  - 异步处理：使用async/await处理异步操作
  - 异常处理：完善的try-catch错误处理机制

## 更更新日志

### 2025-01-22 - 数据库模型返回值修复

#### 核心数据库错误修复
- #修复SModels.py中所有数据库方法的返回值问题
  - 问题：所有数据库操作方法（`load`、`get`、`updateStats`）没有返回数据库操作结果
  - 根本原因：调用`self.SQL(db_operation)`后没有`return`语句，导致方法返回`None`
  - 错误链：`DeviceModel_.all()` → `None` → `SDevice_.all()` → `TypeError: 'NoneType' object is not iterable`
  - 影响范围：设备加载、任务管理、App管理等所有数据库操作

#### 修复的方法列表
- #SModel_.load方法：添加`return self.SQL(db_operation)`
  - 修复前：`self.SQL(db_operation)` - 返回None
  - 修复后：`return self.SQL(db_operation)` - 返回数据库查询结果列表
  - 影响：所有模型的数据加载操作

- #DeviceModel_.get方法：添加`return cls.model.SQL(db_operation)`
  - 修复前：`self.SQL(db_operation)` - 返回None  
  - 修复后：`return cls.model.SQL(db_operation)` - 返回设备记录字典
  - 影响：设备查询和创建操作

- #TaskModel_.get方法：添加`return cls.model.SQL(db_operation)`
  - 修复前：`self.SQL(db_operation)` - 返回None
  - 修复后：`return cls.model.SQL(db_operation)` - 返回任务记录字典
  - 影响：任务查询和创建操作

- #AppModel_.get方法：添加`return cls.model.SQL(db_operation)`
  - 修复前：`self.SQL(db_operation)` - 返回None
  - 修复后：`return cls.model.SQL(db_operation)` - 返回App记录字典
  - 影响：App查询和创建操作

- #AppModel_.updateStats方法：添加`return cls.model.SQL(db_operation)`
  - 修复前：`cls.model.SQL(db_operation)` - 返回None
  - 修复后：`return cls.model.SQL(db_operation)` - 返回更新操作结果布尔值
  - 影响：App统计数据更新操作

#### SDevice_.all方法防护加强
- #增强设备列表获取的异常处理
  - 问题：当`DeviceModel_.all()`返回`None`时，for循环抛出TypeError
  - 解决：添加None检查和异常捕获机制
  - 防护逻辑：`if deviceDatas is None: deviceDatas = []`
  - 异常处理：捕获所有异常并返回空列表，确保不会中断系统运行
  - 日志记录：异常发生时记录详细错误信息

#### 错误场景重现和验证
- #B2S_loadDatas请求处理流程
  - 触发场景：浏览器请求加载设备数据
  - 错误路径：`onB2S_loadDatas` → `deviceMgr.devices` → `self._devices` → `SDevice_.all()` → `DeviceModel_.all()`
  - 错误原因：`DeviceModel_.all()`返回None而不是列表
  - 修复验证：确保所有数据库操作都能正确返回预期的数据类型

#### 数据库操作一致性
- #统一数据库操作返回值模式
  - 查询操作：返回字典（单条记录）或列表（多条记录）
  - 更新操作：返回布尔值表示成功/失败
  - 异常处理：数据库异常时返回None或False，业务层进行防护
  - 空数据处理：查询无结果时返回None（单条）或空列表（多条）

### 2025-01-22 - RPC类型转换自动化

#### RPC参数类型自动转换系统
- #实现RPC层面的参数类型自动转换：解决datetime等复杂类型JSON序列化问题
  - 问题：datetime类型无法直接JSON序列化，RPC调用时被转换为字符串
  - 原因：前端发送JSON数据时，datetime对象被序列化为字符串
  - 解决：在RPC.py中添加`_convertRpcTypes()`方法，自动转换参数类型
  - 技术：使用Python的`inspect`模块解析方法签名，识别参数类型注解
  - 实现：在`callRpcMethod()`调用实际方法前自动转换参数类型

#### 支持的类型转换
- #字符串转datetime：自动调用`_G.DateHelper.toDate()`转换
  - 支持格式：'2025-01-15'、'2025.01.15'、'2025/01/15'、'20250115'、'2025-01-15 10:30:45'
  - 容错处理：转换失败时返回原值，不影响RPC调用
  - 空值处理：None值保持不变
  - 重复处理：已经是datetime对象的值保持不变

- #字符串转date：自动转换为date对象
  - 先转换为datetime，再提取date部分
  - 支持所有datetime支持的格式
  - 与datetime转换逻辑保持一致

#### 转换机制设计
- #智能参数解析：`_convertRpcTypes()`方法
  - 位置参数转换：根据方法签名中的参数位置自动转换
  - 关键字参数转换：根据参数名匹配方法签名进行转换
  - self/cls参数跳过：自动识别并跳过实例和类方法的第一个参数
  - 类型注解识别：使用`inspect.signature()`获取方法的参数类型注解

- #单值转换逻辑：`_convertSingleType()`方法
  - 类型匹配检查：只有当类型注解明确时才进行转换
  - 异常安全：转换失败时返回原值，记录错误日志
  - 扩展性设计：可以轻松添加新的类型转换支持

#### CScore.py错误修复
- #修复CScore.py中的AttributeError
  - 问题：`amount.get('amount_str')`调用失败，因为`amount`已被重新赋值为浮点数
  - 原因：第185行`amount = float(...)`重新赋值后，异常处理仍使用`amount.get()`
  - 修复：将转换后的值保存为`amount_value`，保持原始`amount`字典不变
  - 影响：解决了在解析OCR数据时的变量名冲突问题

#### CTask.py更新间隔优化
- #任务更新间隔时间控制：避免频繁更新影响性能
  - 新增属性：`_updateInterval = 5`（默认5秒）、`_lastUpdateTime = 0`
  - 新增方法：`updateInterval`属性getter/setter，支持动态调整间隔
  - 更新逻辑：只有距离上次更新超过指定间隔才发送更新事件
  - 性能优化：减少网络通信和UI更新频率，提高系统响应速度

#### 向后兼容性
- #无需修改现有RPC方法：现有代码无需任何修改即可享受类型转换
  - 自动识别：基于方法的类型注解自动进行转换
  - 渐进式支持：只有添加了类型注解的方法才会进行转换
  - 错误安全：转换失败时不影响RPC调用的正常进行
  - 开发友好：提高开发效率，减少手动类型转换代码

#### Socket.IO JSON序列化修复
- #修复Socket.IO发送数据时的JSON序列化错误
  - 问题：datetime对象无法被JSON序列化，导致Socket.IO发送失败
  - 原因：Python的datetime对象不是JSON原生支持的数据类型
  - 解决：在`_G.py`的`emit`方法中添加`_serializeForJson()`预处理
  - 功能：递归转换数据结构中的datetime和date对象为ISO格式字符串
  - 格式：datetime转换为`2025-01-22T10:30:45`，date转换为`2025-01-22`

- #智能数据序列化：`_serializeForJson()`方法
  - 支持类型：datetime、date、dict、list、tuple、set
  - 递归处理：深度遍历嵌套的数据结构
  - 保持结构：不改变原始数据结构，只转换不兼容的类型
  - 性能优化：只处理需要转换的数据，其他数据保持原样

#### 测试验证
- #完整的类型转换测试：验证各种场景下的转换正确性
  - 基础转换：字符串成功转换为datetime对象
  - 空值处理：None值保持不变
  - 重复处理：datetime对象保持不变
  - 格式支持：各种日期字符串格式都能正确转换
  - 错误处理：转换失败时安全降级到原值

- #JSON序列化测试：验证Socket.IO数据发送兼容性
  - 简单对象：datetime和date对象正确转换为字符串
  - 嵌套结构：复杂数据结构中的日期对象正确处理
  - JSON兼容：处理后的数据可以成功进行JSON序列化
  - 结构保持：原始数据结构完整保持，只有类型发生转换

### 2025-01-22 - 关键错误修复

#### SQL语法错误修复
- #修复SModels.py中的SQL WHERE子句构建错误
  - 问题：当只有where参数时，生成错误SQL：`SELECT ... FROM apps AND deviceId = '84'`
  - 原因：`load()`方法中AND和WHERE关键字使用错误
  - 修复：重构SQL构建逻辑，使用`where_clauses`列表收集条件
  - 结果：生成正确SQL：`SELECT ... FROM apps WHERE deviceId = '84'`
  - 影响：修复了AppModel_.all()方法的数据库查询异常

#### 无限递归错误修复
- #修复_App.py中的__getattr__方法无限递归问题
  - 问题：访问`self._data`时触发无限递归调用，导致栈溢出
  - 原因：`__getattr__`方法内部访问`_data`属性，但属性不存在时又触发`__getattr__`
  - 修复：添加防护逻辑，防止对`_data`的递归访问
  - 技术：使用`hasattr()`检查属性存在性，避免循环依赖
  - 影响：解决了SDevice._loadApps()方法中的递归调用崩溃

#### 变量名冲突修复
- #修复__getattr__方法中的变量名冲突问题
  - 问题：局部变量`type`与内置函数`type()`冲突
  - 原因：同时使用`type(self)`和定义局部变量`type`
  - 修复：重命名局部变量为`value_type`，使用`self.__class__.__name__`
  - 结果：消除了UnboundLocalError异常

#### 字符串分割错误修复
- #修复_App.get()方法中的字符串分割问题
  - 问题：`84.快手极速版`等包含`.`的应用名称导致分割异常
  - 原因：`key.split('.')`会将所有`.`都作为分割点
  - 修复：使用`key.split('.', 1)`限制最多分割成2部分
  - 结果：支持应用名中包含`.`的情况，如`84.快手极速版`正确分割为设备ID=84，应用名=快手极速版
  - 影响：解决了前端发送getScores指令时的RPC调用异常

#### 修复验证和测试
- #完整的错误修复验证
  - SQL测试：验证WHERE条件正确生成
  - 递归测试：验证_App_实例正常创建和属性访问
  - 字符串分割测试：验证各种格式的key都能正确处理
  - 集成测试：确保修复不影响其它功能
  - 错误处理：所有异常场景都得到妥善处理

### 2025-01-22 - 设备App管理系统

#### 创建设备App管理基类`_DeviceAppMgr_`
- #实现设备级App管理：创建`_DeviceAppMgr_`基类提供统一的App管理功能
  - 功能覆盖：App查询、创建、跟踪当前app、使用统计
  - 数据结构：App列表、当前App、使用历史、统计数据
  - RPC接口：`getAppList()`、`createApp()`、`setCurrentApp()`、`getCurrentApp()`、`getAppStats()`
  - 统计功能：使用次数、创建时间、最后使用时间追踪

#### 设备类继承App管理功能
- #服务端设备继承：`SDevice_`继承`SModelBase_`和`_DeviceAppMgr_`
  - 导入优化：添加`from _DeviceAppMgr import _DeviceAppMgr_`
  - 多继承实现：`class SDevice_(SModelBase_, _DeviceAppMgr_)`
  - 初始化完善：`_DeviceAppMgr_.__init__(self)`显式初始化App管理功能

- #客户端设备继承：`CDevice_`继承`Base_`和`_DeviceAppMgr_`
  - 架构统一：保持与服务端相同的继承模式
  - 单例兼容：在单例模式基础上扩展App管理能力
  - 功能同步：客户端设备具备完整的App管理功能

#### 完整的三端指令支持

##### 服务端指令（SCmds.py）
- #设备应用列表：`#设备应用列表|sbyylb <设备名>`
  - 功能：获取指定设备的App列表，显示名称、描述、是否当前
  - 格式化输出：表格式显示App信息和统计
- #创建设备应用：`#创建设备应用|cjsbyy <设备名> <App名> [描述]`
  - 功能：为指定设备创建新的App，支持可选描述
- #设置当前应用：`#设置当前应用|szdqyy <设备名> <App名>`
  - 功能：设置设备的当前跟踪App，自动更新使用统计
- #获取当前应用：`#获取当前应用|hqdqyy <设备名>`
  - 功能：获取设备当前设置的App信息
- #应用统计：`#应用统计|yytj <设备名>`
  - 功能：显示设备App使用统计和历史记录

##### 客户端指令（CCmds.py）
- #我的应用列表：`#我的应用列表|wdyylb`
  - 功能：获取当前客户端设备的App列表
- #创建应用：`#创建应用|cjyy <App名> [描述]`
  - 功能：在当前客户端设备创建新App
- #设置当前应用：`#设置当前应用|szdqyy <App名>`
  - 功能：设置客户端当前App
- #当前应用：`#当前应用|dqyy`
  - 功能：获取客户端当前App信息
- #应用统计：`#应用统计|yytj`
  - 功能：获取客户端App使用统计

##### 前端指令（BCmds.js）
- #设备应用列表：`#设备应用列表 [设备ID]`
  - 功能：获取设备App列表，支持选中设备或指定设备ID
- #创建设备应用：`#创建设备应用 <设备ID> <App名> [描述]`
  - 功能：为指定设备创建新App
- #设置设备当前应用：`#设置设备当前应用 <设备ID> <App名>`
  - 功能：设置设备当前App
- #获取设备当前应用：`#获取设备当前应用 [设备ID]`
  - 功能：获取设备当前App，支持选中设备或指定设备
- #设备应用统计：`#设备应用统计 [设备ID]`
  - 功能：获取设备App使用统计

#### 技术实现特点
- #多继承架构：设备类同时继承模型基类和App管理基类
  - 职责分离：数据模型管理与App功能管理分开
  - 代码复用：服务端和客户端共享App管理逻辑
  - 扩展性强：可独立扩展App管理功能而不影响设备基础功能

- #统一RPC接口：所有App管理方法都标记为RPC可调用
  - 远程调用：前端可以直接调用设备的App管理方法
  - 返回格式：统一success/error响应格式，便于错误处理
  - 参数验证：完整的输入验证和错误消息返回

- #数据持久化设计：为未来数据持久化预留接口
  - 抽象方法：`_loadApps()`和`_saveApps()`供子类重写
  - 字典转换：`toDict()`和`fromDict()`方法支持数据序列化
  - 状态管理：App使用历史和统计数据的完整记录

#### App管理功能亮点
- #智能使用统计：自动记录App使用次数和最后使用时间
- #历史记录管理：维护最近20个App的使用历史
- #当前App跟踪：支持设置和获取设备当前关注的App
- #完整错误处理：所有操作都有详细的错误信息和成功确认
- #三端指令一致性：服务端、客户端、前端指令功能对应，使用方式统一

### 2025-01-22 - 前端指令架构解耦优化

#### 优化前端指令管理模块BCmds.js
- #修正前端指令实现：使用JavaScript而不是Python
  - 前端指令位于`server/static/js/BCmds.js`（JavaScript文件）
  - 与服务端Python指令分离，采用不同的技术栈
  - 使用`regCmd`函数注册前端JavaScript指令
  - 通过RPC调用与服务端进行数据交互

#### 实现getScores前端指令
- #前端主动获取收益数据：`#获取收益 设备ID 应用名 [日期]`
  ```javascript
  regCmd("#获取收益 (?<deviceId>\\S+)\\s+(?<appName>\\S+)\\s*(?<date>\\S+)?", 'BCmds')
  async function getScores({ deviceId, appName, date, sheetPage })
  ```
  - 支持设备ID、应用名称和可选日期参数
  - 默认日期为当天，格式为YYYY-MM-DD
  - 通过RPC调用服务端设备的getScores方法
  - 获取成功后自动刷新前端任务表格

#### 服务端推送逻辑解耦
- #移除SDevice.py中的主动推送代码
  - 注释掉 `g.emit('S2B_sheetUpdate', {'type': 'tasks', 'data': data})`
  - 保留核心收益获取和数据库更新逻辑
  - 服务端专注于数据处理，不再关心前端更新时机
  - 减少服务端对前端的直接依赖

#### 架构优势和解耦效果
- #前端主动拉取模式
  - 前端按需获取数据，提高响应速度
  - 避免服务端频繁推送造成的性能开销
  - 前端可以控制数据更新的时机和频率
  - 更好的用户体验，数据获取更加精准

- #职责分离明确
  - 服务端：专注数据处理和存储，提供RPC接口
  - 前端：主动调用指令，自主处理数据显示和更新
  - 减少组件间的耦合，提高系统的可维护性
  - 为后续功能扩展提供更灵活的架构基础

#### 返回数据格式标准化
```javascript
// 成功返回格式
{
  "success": true,
  "message": "获取收益成功: 设备ID 应用名 日期",
  "deviceId": "设备ID",
  "appName": "应用名称", 
  "date": "日期"
}

// 错误返回格式  
{
  "success": false,
  "error": "错误信息描述"
}
```

#### 项目架构理解修正
- #修正技术栈理解
  - **Android客户端**：`app/` 目录，Java + Android SDK
  - **服务端**：`server/scripts/` 目录，Python + Flask + Socket.IO
  - **前端**：`server/static/js/` 目录，JavaScript + HTML，由服务端提供
  - 前端指令使用JavaScript而非Python，通过浏览器执行
  - 三个部分通过Socket.IO协议进行实时通信

### 2025-01-22 - 前端RPC命令格式重构

#### 全新的RPC命令格式设计
- #新格式定义：`@设备ID或者名字:类名.方法名 参数列表`
  - 格式规范：以`@`开头，冒号分隔设备标识和RPC调用
  - 示例：`@68:SDevice_.getDeviceInfo` (指定设备68)
  - 示例：`@!:_App_.getAppList` (当前选中设备)  
  - 示例：`@STask_.updateScore {"id": 1, "score": 100}` (服务器RPC)

#### 智能设备识别和路由规则
- #设备标识解析规则
  1. **无设备标识**：`@类名.方法名` → 服务器RPC调用
  2. **感叹号标识**：`@!:类名.方法名` → 当前选中的目标设备的第一个
  3. **具体标识**：`@设备ID或名字:类名.方法名` → 指定设备，支持ID和名字查找
  
- #错误检测和用户友好提示
  - 设备不存在检测：实时验证设备ID或名字的有效性
  - 未选择设备警告：使用`!`时检查是否有选中的目标设备
  - 解析错误处理：命令格式错误时显示详细的错误信息
  - 前端临时日志：所有错误信息直接显示在日志表格中

#### 完整的命令解析重构
- #新增解析方法架构
  ```javascript
  parseCommand()           // 主解析入口，格式检测分发
  ├── parseRPCCommand()    // 新RPC格式解析
  ├── parseLegacyCommand() // 兼容旧格式解析  
  └── findDeviceByIdOrName() // 设备查找辅助方法
  ```

- #设备查找优化
  - 优先按ID查找：`devices.find(d => d.id.toString() === idOrName)`
  - 备用按名字查找：`devices.find(d => d.name === idOrName)`
  - 支持数字ID和字符串名字的混合查找
  - 实时设备列表同步，确保查找数据最新

#### 执行流程和反馈优化
- #命令执行优化
  - 错误类型识别：解析错误时阻止命令执行，避免无效调用
  - 设备标识传递：完整传递deviceTarget信息到执行层
  - 智能通知文案：根据设备类型显示不同的执行通知
    - 服务器：`服务端RPC调用: 类名.方法名`
    - 选中设备：`客户端RPC调用: 选中设备 -> 类名.方法名`
    - 指定设备：`客户端RPC调用: 设备名 -> 类名.方法名`

- #向后兼容保证
  - 完全保留旧命令格式：`目标数组 分类符 命令内容`
  - 自动格式检测：根据是否以`@`开头选择解析方式
  - 无缝切换：用户可以混用新旧格式，互不影响
  - 渐进式迁移：可以逐步将常用命令迁移到新格式

#### 技术实现亮点
- #解析效率优化
  - 单次字符串扫描确定格式类型
  - 提前短路：错误情况下避免不必要的处理
  - 智能缓存：设备查找结果可复用于后续调用
  
- #用户体验提升
  - 即时错误反馈：解析错误立即显示在前端日志
  - 智能提示：根据解析结果生成有意义的通知信息
  - 调试友好：详细的解析日志便于问题排查

### 2025-01-22 - 日志表格选中复制功能完善

#### 完整的表格交互功能实现
- #增强选中机制配置
  - `selectableRows: true` - 启用行选择
  - `selectableRowsRangeMode: "click"` - 支持点击范围选择
  - `selectablePersistence: true` - 选择状态持久化
  - `selectableRange: true` - 启用范围选择
  - `selectableRangeColumns: true` - 启用列范围选择
  - `selectableRangeRows: true` - 启用行范围选择

- #全列复制功能支持
  - 为所有重要列添加 `clipboard: true` 属性
  - 日期、时间、标签、等级、发送者、内容列均支持复制
  - 内容列特别设置 `headerClipboard: "message"` 便于批量操作
  - 与其他表格(设备、任务)保持一致的交互体验

- #用户操作体验
  - 支持单个或多个行选择
  - 支持鼠标拖拽选择范围
  - 支持右键点击复制单元格内容
  - 支持 Ctrl+C 复制选中内容
  - 选择状态自动保持，便于批量操作

### 2025-01-22 - RPC系统优化和类导入机制改进

#### 采用getClassLazy延迟导入机制优化RPC注册
- #改进导入方式：使用经过验证的`_G_.getClassLazy`方法替代原始导入
  - 原始方式：使用`__import__`和多层备用导入机制，代码复杂且不稳定
  - 新方式：采用`g.getClassLazy(module_name)`统一延迟导入，避免循环引用问题
  - 技术优势：getClassLazy内置缓存机制、路径查找和错误处理，经过充分测试
  - 代码简化：移除30+行复杂的备用导入代码，替换为简洁的3行核心逻辑
- #修复lambda闭包问题：`instanceGetter = lambda target_cls=cls: getInst(target_cls)`
  - 问题：原始lambda闭包导致所有实例获取器绑定到最后一个类
  - 解决：使用默认参数技巧确保每个实例获取器正确绑定到对应类
  - 结果：每个RPC类都有独立正确的实例获取器

#### 实现客户端和服务端RPC类分离机制
- #问题分析：之前所有RPC类都注册到客户端和服务端，造成不必要的资源占用
  - 服务端不需要`CDevice_`、`CTask_`等客户端专用类
  - 客户端不需要`SDevice_`、`STask_`等服务端专用类
  - `_App_`类作为通用类，两端都需要注册
- #分离策略：根据运行环境动态选择注册的RPC类
  ```python
  # 服务端RPC类
  server_rpc_classes = [
      ('_App', '_App_'),        # 应用管理类 - 通用
      ('SDevice', 'SDevice_'),  # 服务端设备管理
      ('STask', 'STask_'),      # 服务端任务管理
  ]
  
  # 客户端RPC类
  client_rpc_classes = [
      ('_App', '_App_'),        # 应用管理类 - 通用
      ('CDevice', 'CDevice_'),  # 客户端设备管理
      ('CTask', 'CTask_'),      # 客户端任务管理
  ]
  ```
- #实现细节
  - 自动环境检测：通过`g.isServer()`判断运行环境
  - 动态类选择：根据环境自动选择合适的RPC类列表
  - 清晰的日志：区分显示"注册服务端RPC类"和"注册客户端RPC类"
  - 资源优化：减少不必要的类注册，提高启动效率

#### 增强RPC调试和监控能力
- #新增调试功能：`debugRPCRegistry()`函数提供完整的注册状态信息
  - 显示已注册类数和方法总数的统计信息
  - 列出每个类的所有RPC方法列表
  - 特别检查关键方法如`_App_.getAppList`的注册状态
  - 提供方法详情包括类型和可调用性验证
- #修复效果总结
  - ✅ 解决了`_App_.getAppList`等RPC方法不存在的问题
  - ✅ 采用经过验证的延迟导入机制，提高稳定性
  - ✅ 实现客户端和服务端类分离，优化资源使用
  - ✅ 提供详细的RPC系统调试信息和状态监控
  - ✅ 简化了代码结构，提高了可维护性

### 2025-01-22 - 前端表格滚动错误完全修复

#### 彻底解决Tabulator表格滚动错误问题
- #问题分析：前端出现 "Scroll Error - Row not visible" 错误，来源复杂
  - 主要错误：`Renderer.js:200` - Tabulator库内部渲染器的滚动冲突
  - 次要错误：`sheet.js` addTempLog方法的滚动时机问题
  - 根本原因：表格异步渲染与滚动操作的时序冲突，导致未捕获的Promise错误
  - 影响范围：控制台错误频繁出现，影响开发调试体验

#### 三层防护的解决方案
- #第一层：优化表格操作流程
  - 使用 `blockRedraw()` 和 `restoreRedraw()` 控制表格重绘时机
  - 延迟时间从50ms增加到100ms，确保DOM完全稳定
  - 分离数据更新和滚动操作，避免并发冲突
  
- #第二层：实现安全滚动机制 `safeScrollToRow()`
  ```javascript
  // 多重验证的安全滚动
  - 表格存在性检查
  - 过滤器状态验证  
  - 行对象存在性确认
  - 主滚动方法 + 备用滚动方法
  - 完整的错误捕获和降级处理
  ```

- #第三层：全局错误拦截器 `setupScrollErrorHandler()`
  ```javascript
  // 三种错误捕获机制
  - window.addEventListener('unhandledrejection') // Promise错误
  - window.addEventListener('error')              // 普通错误  
  - console.error重写                            // 控制台错误过滤
  ```

#### 技术实现细节
- #表格操作优化
  - 使用表格阻塞重绘机制避免渲染冲突
  - 增加操作间隔时间，确保异步操作完成
  - 分离关注点：数据更新、表格渲染、滚动操作独立处理
  
- #多级滚动策略
  - 第一次尝试：`scrollToRow(tempId, "top", false)` 精确定位
  - 备用方法：`scrollToRow(row, "nearest", false)` 就近显示
  - 兜底机制：静默失败，不影响其他功能

- #全局错误处理
  - 智能识别滚动相关错误，过滤非关键错误信息
  - 保留重要错误的正常报告机制
  - 提供调试友好的警告信息

#### 修复效果
- ✅ 完全消除 "Scroll Error - Row not visible" 控制台错误
- ✅ 保持日志滚动功能的正常工作
- ✅ 提供更稳定的表格操作体验  
- ✅ 不影响其他表格功能和性能
- ✅ 增强了整体前端错误处理能力

## 更新日志

### 2025-01-15 - 统一RPC初始化系统

#### 实现统一的RPC类注册和初始化机制
- #问题分析：之前每个RPC类需要单独注册，容易遗漏
  - `_App`类通过`onLoad()`注册，但依赖延迟导入机制
  - `STask`类通过模块末尾的代码注册，分散管理
  - 缺乏统一的RPC系统初始化入口
- #解决方案：创建统一的RPC初始化函数
  - 新增`RPC.init()`函数，统一注册所有RPC类
  - 新增`RPC.initializeRPCHandlers()`函数，整合类注册和事件处理器初始化
  - 支持服务端和客户端的统一初始化流程
- #实现细节
  - 在`RPC.py`中定义需要注册的RPC类列表：`_App_`, `SDevice_`, `STask_`, `CDevice_`, `CTask_`
  - 动态导入模块并注册RPC类，避免循环依赖
  - 提供详细的注册日志，显示注册类数和方法数
  - 统一的错误处理和状态报告
- #调用位置更新
  - 服务端：`Server.py` 中的 `initSocketIO()` 函数
  - 客户端：`CClient.py` 中的 `Begin()` 函数
  - 替换原有的分散注册调用为统一的 `initializeRPCHandlers()`
- #清理重复代码
  - 删除`STask.py`末尾的重复RPC注册代码
  - 删除`_App.py`末尾的`onLoad()`调用
  - 移除各模块中的分散RPC注册逻辑
- #优势
  - 集中管理所有RPC类注册，避免遗漏
  - 统一的初始化时机，确保所有RPC方法可用
  - 更好的错误处理和日志记录
  - 便于维护和扩展新的RPC类
- #文件变更
  - 修改：`server/scripts/RPC.py` - 添加统一初始化函数
  - 修改：`server/scripts/Server.py` - 使用统一RPC初始化
  - 修改：`server/scripts/CClient.py` - 使用统一RPC初始化
  - 修改：`server/scripts/STask.py` - 删除重复注册代码
  - 修改：`server/scripts/_App.py` - 删除onLoad调用

### 2025-01-15 - 前端临时日志功能

### 2025-01-15 - RPC系统简化和专用指令重构

#### 优化SDevice任务属性为懒加载机制
- #将SDevice._tasks封装为懒加载属性
  - 重构`self._tasks`为私有属性`self.__tasks`，避免外部直接访问
  - 创建`tasks`属性子(property)，实现懒加载机制，默认加载当天任务
  - 自动缓存管理：检查缓存有效性，只在需要时重新加载任务
  - 新增`clearTasksCache()`方法，支持强制刷新任务缓存
- #改进的访问方式和性能优化
  - 所有访问任务的代码统一使用`self.tasks`属性
  - 自动判断缓存是否过期（跨天自动刷新）
  - 减少不必要的数据库查询，提高性能
  - 保持向后兼容，`getTasks(date)`方法仍可指定具体日期
- #代码简化和维护性提升
  - 移除手动缓存管理的复杂逻辑
  - 统一的任务访问接口，减少代码重复
  - 私有属性保护，防止意外的缓存破坏
  - 清晰的缓存生命周期管理

#### 简化RPC调用接口，统一使用call方法
- #简化前端RPC.js接口，移除冗余的server和client方法
  - 删除`RPC.server()`和`RPC.client()`方法，统一使用`RPC.call()`
  - 更新全局rpc对象，只保留`rpc.call(deviceId, className, methodName, params)`
  - 服务端调用：`rpc.call(null, className, methodName, params)`
  - 客户端调用：`rpc.call(deviceId, className, methodName, params)`
  - 减少接口数量，降低学习成本，提高代码一致性

#### 创建专用的@开头RPC指令类型
- #将RPC从#指令升级为专用的@指令类型
  - 删除`#rpc`指令，避免与普通命令混淆
  - 新增@开头的RPC专用指令，类似于`>`客户端指令和`:`服务端指令
  - 命令格式：`@className.methodName [params...]`
  - 支持服务端RPC调用：`@SDevice_.getDeviceInfo device1`
  - 支持客户端RPC调用：`device1 @_App_.getAppList`
- #智能参数解析和调用逻辑
  - 支持JSON格式参数：`@STask_.updateScore {"id": "task1", "args": [100]}`
  - 支持简化参数格式：`@SDevice_.getDeviceInfo device1`（自动识别为instance id）
  - 支持多参数：`@STask_.createTask task1 100 "测试任务"`（自动作为args数组）
  - 自动区分服务端和客户端调用，无目标设备时默认为服务端调用
- #完整的RPC执行反馈
  - 发送通知：显示RPC调用已发送的确认信息
  - 结果通知：自动显示RPC调用的执行结果
  - 错误处理：详细的错误信息和参数解析失败提示
  - 批量调用：支持向多个设备同时发送RPC调用，显示成功率统计
- #文件变更
  - 修改：`server/static/js/RPC.js` - 简化接口，移除server和client方法
  - 修改：`server/static/js/BCmds.js` - 删除#rpc指令，更新所有RPC调用为新格式
  - 修改：`server/static/js/sheet.js` - 添加RPC指令类型解析和executeRPCCommand方法
  - 修改：`server/scripts/RPC.py` - 修复设备ID到sid的转换逻辑
- #用户体验改进
  - 专用@指令提供清晰的RPC调用标识，避免与普通命令混淆
  - 智能参数解析支持多种格式，适应不同使用习惯
  - 统一的调用接口减少学习成本，提高开发效率
  - 完整的执行反馈让用户清楚了解RPC调用状态和结果

#### 合并重复的RPC处理器类，提高代码维护性
- #合并SRPCHandler_和CRPCHandler_类为统一的RPCHandler类
  - 消除代码重复，两个类的功能基本相同
  - 通过isServer参数区分服务端和客户端模式
  - 服务端模式使用room参数进行Socket.IO消息发送
  - 客户端模式直接发送消息，不指定room
- #统一的RPC事件处理接口
  - `RPCHandler.initializeRPCHandlers(isServer=True)` - 初始化，isServer指定模式
  - `RPCHandler.handleRPCCall(data, isServer=True)` - 处理RPC调用
  - 自动判断服务端/客户端模式，应用相应的处理逻辑
  - 保持原有的错误处理和日志记录功能
- #文件变更和重构
  - 新增：`server/scripts/RPCHandler.py` - 统一的RPC处理器类
  - 删除：`server/scripts/SRPCHandler.py` - 已合并到RPCHandler
  - 删除：`server/scripts/CRPCHandler.py` - 已合并到RPCHandler
  - 修改：`server/scripts/Server.py` - 更新为RPCHandler.initializeRPCHandlers(isServer=True)
  - 修改：`server/scripts/CClient.py` - 更新为RPCHandler.initializeRPCHandlers(isServer=False)
- #代码质量改进
  - 减少代码重复，提高维护效率
  - 统一的错误处理和日志记录逻辑
  - 更清晰的代码结构和命名规范

### 2024-12-19 - RPC参数格式重构（重大更新）

#### 将RPC参数从*args, **kwargs格式重构为统一的dict参数格式
- #重构RPC调用接口，提高参数传递的清晰度和安全性
  - 统一参数格式：`g.RPC(device_id, className, methodName, params)` 
  - 参数字典结构：`{'id': 'instance_id', 'args': [arg1, arg2], 'kwargs': {key: value}, 'timeout': 8}`
  - 参数命名简化：`instance_id` → `id`，更简洁的命名风格
  - 强制使用命名参数，避免参数位置混淆和传递错误
- #智能方法调用机制，完美支持类方法和实例方法
  - 增强`_callMethod`方法，智能识别和调用不同类型的方法
  - 完美支持`@classmethod`装饰的类方法调用
  - 正确处理实例方法、静态方法和装饰器组合
  - 自动处理方法绑定和参数传递，确保调用正确性
- #前端RPC.js同步更新，保持前后端一致性
  - 更新前端RPC调用接口，支持新的dict参数格式
  - 向后兼容：旧的调用方式仍然支持，平滑迁移
  - 新格式示例：`rpc.server('_App_', 'getAppList', {id: 'app1', args: [param1]})`
  - 旧格式兼容：`rpc.server('_App_', 'getAppList', 'app1', param1)` 仍可用
- #全面的RPC调用格式示例
  ```python
  # 类方法调用（无需实例ID）
  g.RPC(None, '_App_', 'getAppList')
  
  # 实例方法调用（新格式）
  g.RPC(None, 'SDevice_', 'getDeviceInfo', {'id': 'device1'})
  
  # 带参数的方法调用
  g.RPC(None, 'STask_', 'updateTaskScore', {
      'id': 'task1', 
      'args': [100],
      'kwargs': {'reason': '完成任务'},
      'timeout': 15
  })
  
  # 前端调用（新格式）
  await rpc.server('SDevice_', 'getDeviceInfo', {id: 'device1'})
  
  # 前端调用（向后兼容）
  await rpc.server('SDevice_', 'getDeviceInfo', 'device1')
  ```
- #创建迁移指南和测试工具
  - 新增：`server/scripts/RPC_Migration_Guide.py` - 详细的迁移指南和示例
  - 新增：`server/templates/rpc_test.html` - RPC测试页面，验证新旧API
  - 提供自动化迁移辅助工具和正则表达式模式
  - 完整的迁移检查清单，确保平滑过渡
- #技术优势和改进
  - 参数传递更安全：避免参数位置错误和类型混淆
  - 代码可读性提升：参数含义明确，易于理解和维护  
  - 调试友好：参数结构清晰，便于问题定位和调试
  - 扩展性增强：可轻松添加新的参数选项，向前兼容
  - 向后兼容：旧代码无需立即修改，支持渐进式迁移
- #文件变更
  - 修改：`server/scripts/RPC.py` - 重构所有RPC相关函数签名
  - 修改：`server/scripts/_G.py` - 更新RPC函数接口
  - 修改：`server/static/js/RPC.js` - 前端RPC接口同步更新
  - 修改：`server/static/js/BCmds.js` - 前端命令适配新格式
  - 新增：`server/scripts/RPC_Migration_Guide.py` - 迁移指南
  - 新增：`server/templates/rpc_test.html` - API测试页面
  - 修改：`server/scripts/_App.py` - 更新RPC调用示例
  - 修改：`server/scripts/SDevice.py` - 更新RPC调用示例

### 2024-12-19 - RPC远程过程调用功能

#### 实现基于装饰器的RPC机制，支持客户端和服务端双向RPC调用
- #新增RPC装饰器和调用系统
  - 创建`@RPC()`装饰器标记方法为RPC可调用方法
  - 统一调用接口：`g.RPC(device_id, className, methodName, *args, instance_id=None, **kwargs)`进行远程调用
  - 默认实例获取器：自动支持App、Device、Task类的默认实例获取，无需手动注册
  - 动态实例管理：支持通过instance_id参数获取特定实例，适应复杂场景
  - 双向RPC支持：完整支持服务端↔客户端、本地调用的所有场景
  - 错误处理和超时：完整的异常处理和调用超时机制
- #技术特性
  - 基于现有Socket.IO通信协议，无需额外网络配置  
  - 支持同步和异步调用模式，适应不同使用场景
  - 参数自动序列化/反序列化，支持复杂数据类型传输
  - 支持类方法、实例方法和静态方法的远程调用
  - 线程安全的RPC管理器，支持并发调用
  - 智能调用路由：自动判断本地调用和远程调用
- #RPC调用规则
  ```python
  # 服务端调用客户端
  result = g.RPC(device_id, 'ClassName', 'methodName', args)
  
  # 客户端调用服务端
  result = g.RPC(None, 'ClassName', 'methodName', args)
  
  # 服务端本地调用
  result = g.RPC(None, 'ClassName', 'methodName', args)
  
  # 客户端本地调用
  result = g.RPC('local', 'ClassName', 'methodName', args)
  ```
- #使用示例
  ```python
  # 1. 定义RPC方法
  @RPC()
  def getScores(self, date=None):
      scores = self.LoadScore(date)
      return {'success': True, 'scores': scores}

  # 2. 注册RPC类（使用默认实例获取器）
  g.registerRPC(_App_)  # 自动使用默认instanceGetter
  
  # 3. 远程调用
  result = g.RPC(device_id, '_App_', 'getScores', datetime.now())
  
  # 4. 使用instance_id获取特定实例
  result = g.RPC(device_id, '_App_', 'getCurrentPageInfo', instance_id='微信')
  ```
- #文件变更
  - 新增: `server/scripts/RPC.py` - RPC核心实现和装饰器
  - 新增: `server/scripts/SRPCHandler.py` - 服务端RPC事件处理器
  - 新增: `server/scripts/CRPCHandler.py` - 客户端RPC事件处理器
  - 新增: `server/scripts/RPCExample.py` - RPC使用示例和测试代码
  - 新增: `server/scripts/RPCUsageGuide.py` - 完整的RPC使用指南
  - 新增: `server/scripts/RPCDefaultInstanceExample.py` - 默认实例获取器使用示例
  - 修改: `server/scripts/_App.py` - 添加RPC方法示例和默认注册
  - 修改: `server/scripts/_G.py` - 直接集成RPC相关方法到全局类
  - 修改: `server/scripts/RPC.py` - 实现默认实例获取器机制
- #架构优势
  - 简化远程调用语法，提高开发效率
  - 默认实例获取器：自动支持App、Device、Task类，零配置使用
  - 动态实例管理：支持通过instance_id获取特定实例，灵活性强
  - 完整的双向调用支持，满足所有通信需求
  - 统一的错误处理和超时机制，增强系统稳定性
  - 智能路由机制，自动选择最优调用方式
  - 支持任意类的RPC注册，具有良好的扩展性
  - 基于现有通信基础设施，保持系统架构简洁

### 2025-01-14

#### 实现统一的属性更新架构，解决跨端同步问题
- #创建统一的属性修改处理中心，解决前后端数据同步问题
  - 所有属性修改统一通过服务端处理，确保数据一致性
  - 支持客户端指令（如 81>name aa.test3）和前端指令（name . aa.test3）统一处理
  - 服务端自动通知客户端和前端更新，消除手动同步的遗漏
  - 设计通用的属性更新机制，支持任意实体类型和属性，不限于name属性
- #增强服务端onB2S_setProp函数为属性更新处理中心
  - 统一处理来自前端和客户端的属性更新请求
  - 自动通知在线客户端更新本地属性（通过S2C_updateDevice事件）
  - 自动通知前端实时更新表格数据（通过现有的S2B_sheetUpdate事件）
  - 提供详细的处理结果反馈，包含成功状态和错误信息
- #新增C2S_SetProp事件支持客户端属性更新
  - 客户端name命令改为通过服务端统一处理，发送C2S_SetProp事件
  - 复用onB2S_setProp处理逻辑，保持前后端行为一致
  - 支持异步处理和结果返回，提供用户友好的反馈信息
- #前端简化为直接发送更新请求，服务器统一刷新
  - 前端name命令直接发送B2S_setProp事件，不等待结果
  - 服务器统一处理后通过S2B_sheetUpdate事件刷新前端表格
  - 简化前端逻辑，避免复杂的异步处理和结果等待
  - 充分利用现有的表格更新机制，保持架构简洁统一
- #技术架构优势
  - 完全解决前后端数据不同步问题，实现真正的统一状态管理
  - 支持离线设备的属性修改，服务端保存状态待设备上线时同步
  - 通用设计支持扩展到任意属性和实体类型，为后续功能奠定基础
  - 简化的事件处理机制，充分复用现有基础设施
  - 服务器统一刷新策略，保证前端数据的一致性和及时性

#### 优化前端通知系统，区分命令发送和执行结果显示，支持日志级别颜色
- #修改showNotification函数支持不同类型的通知样式和日志级别解析
  - 添加type参数区分通知类型：'command'(命令发送) 和 'result'(命令结果)
  - 命令发送通知：暗灰色背景 + 浅绿色字体 (#404040 + #90EE90)
  - 命令执行结果通知：根据日志级别显示不同颜色，暗灰色背景统一
  - 保持原有的动画效果和自动消失功能，确保界面协调统一
- #添加parseLevel函数解析日志级别标记
  - 仿照_Log.py的_parseLevel方法实现JavaScript版本
  - 支持解析 [dDiIwWEecC]~ 格式的级别前缀
  - 自动提取级别标记并返回清理后的内容
  - 默认级别为'i'（信息级别）
- #添加getLevelColor函数映射日志级别到颜色
  - 'e'(错误)：红色 (#FF6B6B) + 红色左边框
  - 'w'(警告)：黄色 (#FFD93D) + 黄色左边框
  - 'i'(信息)：白色 (#FFFFFF)
  - 'd'(调试)：青色 (#4ECDC4)
  - 'c'(成功)：绿色 (#51CF66) + 绿色左边框
  - 错误和警告级别添加4px彩色左边框强调显示
- #完善onCmdResult函数自动显示命令执行结果
  - 自动判断命令执行结果成功或失败，分别显示对应通知
  - 成功结果限制显示长度为100字符，避免通知过长影响界面
  - 错误结果自动提取错误信息，去掉'e~'前缀显示用户友好的错误信息
  - 支持字符串、对象等多种结果类型的智能格式化显示
- #统一更新所有showNotification调用点的类型参数
  - 命令发送相关通知统一使用'command'类型：客户端指令发送、服务端指令发送等
  - 命令结果相关通知统一使用'result'类型：执行失败、日志获取结果、本地命令结果等
  - 确保所有通知都有正确的颜色标识，用户可以直观区分命令发送和执行结果
- #技术实现优势
  - 双色通知系统提高用户操作反馈的直观性和可读性
  - 暗灰色背景与当前表格界面风格完美协调，避免视觉冲突
  - 自动化的结果通知显示，无需手动添加每个命令的结果处理
  - 智能的内容长度控制和格式化，保证通知内容的可读性
- #用户体验提升
  - 命令发送和执行结果有明确的颜色区分，操作状态一目了然
  - 执行结果自动弹出通知，用户无需查看控制台即可了解命令执行情况
  - 错误信息友好显示，便于用户理解和处理问题
  - 保持与现有界面风格的一致性，提供协调的视觉体验

### 2025-01-14

#### 实现设备名称同步到Android SharedPreferences，完善设备管理功能
- #添加设备名称属性到CDevice类，支持动态修改设备名称
  - 在CDevice.py中添加name属性的getter和setter方法
  - 设置设备名称时自动同步到Android底层SharedPreferences
  - 实现多重同步方案确保兼容性：直接API调用、Context.getSharedPreferences、PreferenceManager
  - 创建_syncNameToAndroid()方法处理Android层面的数据持久化
- #创建内部命令_syncDeviceName处理Android SharedPreferences同步
  - 在CCmds.py中添加_syncDeviceName内部命令
  - 支持多种Android API调用方式：android.setDeviceName()、SharedPreferences、PreferenceManager
  - 使用commit()方法确保数据立即写入，提高可靠性
  - 完善错误处理和日志记录，便于问题诊断
- #修复前端name命令匹配问题，统一命令注册格式
  - 修复BCmds.js中name命令的正则表达式，解决命令无法匹配的问题
  - 统一所有命令的注册格式，去掉重复的别名定义
  - 修复CmdMgr.processParamSpaces()函数的空格处理逻辑
  - 修复Cmd类构造函数中的命名组匹配问题，支持JavaScript风格的(?<name>...)语法
- #优化help命令显示格式，提供详细的命令信息
  - 重构CmdMgr.getHelp()方法，提取函数注释中的文档信息
  - 显示命令的正则表达式模式，方便调试和问题定位
  - 格式化显示功能描述、参数说明和使用示例
  - 创建_extractFunctionDoc()方法解析函数注释中的结构化信息
- #完善前端设备名称修改功能，支持批量操作
  - 前端name命令支持单个设备和批量设备名称修改
  - 支持使用"."表示当前选中的设备，提高操作便利性
  - 多设备时自动添加序号（如：测试机1、测试机2），避免名称冲突
  - 实时更新设备表格显示，同步发送到服务端更新
- #技术实现优势
  - 无需修改Android底层代码，通过脚本层反射调用实现功能
  - 多重备用方案确保在不同Android环境下的兼容性
  - 统一的命令处理架构，前后端保持一致的用户体验
  - 完善的错误处理和日志记录，便于问题诊断和维护
  - 支持批量操作和智能命名，提高用户操作效率

### 2025-01-14

#### 修复Python 3.8 SSL递归错误，解决服务器启动失败问题
- #问题分析：Python 3.8与urllib3库存在已知兼容性问题
  - 错误信息：RecursionError: maximum recursion depth exceeded
  - 根本原因：ssl.SSLContext.minimum_version属性的setter方法中存在无限递归
  - 影响范围：导致服务器无法正常启动，系统完全无法使用
- #多重修复方案实施
  - 固定urllib3版本为1.26.18，避免问题版本的兼容性问题
  - 添加certifi>=2021.5.25依赖，确保SSL证书链的正确处理
  - 在SMain.py中实现fix_ssl_recursion()修复函数，采用三层防护
  - 方法1：禁用SSL验证，设置ssl._create_default_https_context
  - 方法2：修复TLS版本设置的递归问题，使用属性descriptor重新定义
  - 方法3：设置环境变量PYTHONHTTPSVERIFY=0和CURL_CA_BUNDLE=''
- #创建自动化修复工具
  - 创建fix_ssl_error.bat批处理脚本，一键修复SSL错误
  - 自动升级pip并卸载冲突的库版本
  - 安装经过测试的稳定版本组合
  - 提供DEBUG_MODE环境变量选项，可在调试模式下运行
- #技术实现优势
  - 在导入任何网络模块前预先执行SSL修复，确保修复生效
  - 多层防护机制，即使某个修复方法失效也有备用方案
  - 兼容调试模式和生产模式，提供灵活的运行环境选择
  - 自动化脚本降低用户修复成本，一键解决环境问题
- #稳定性提升
  - 消除服务器启动失败的根本原因
  - 确保在不同Windows环境下的兼容性
  - 为后续升级Python版本提供经验参考
  - 建立完善的环境问题诊断和修复流程

### 2025-01-14

#### 实现前端命令注册和解释框架，大幅提升用户操作体验
- #创建JavaScript版本的命令管理器CmdMgr
  - 仿照Python版本的_CmdMgr.py实现完整的命令注册和解释框架
  - 支持正则表达式命令匹配和参数提取功能
  - 提供命令注册装饰器regCmd()，支持模块化命令管理
  - 实现命令优先级管理和雷同检测机制
  - 支持命名组参数解析，兼容Python版本的(?P<name>pattern)语法
  - 提供完整的帮助系统和错误处理机制
- #创建BCmds.js前端命令模块，类似SCmds.py结构
  - 将所有前端命令集中管理在BCmds.js文件中
  - 采用模块化设计，便于维护和扩展
  - 每个命令都有完整的文档注释和使用示例
  - 统一的命令注册和错误处理机制
- #集成前端命令框架到Sheet页面
  - 修改sendCommand()方法优先尝试本地命令执行
  - 本地命令未找到时自动回退到服务端命令处理
  - 在HTML模板中引入cmdmgr.js和BCmds.js脚本文件
  - 在SheetPage构造函数中调用BCmds.onLoad()初始化命令
- #注册丰富的前端命令集
  - 帮助命令：#帮助|help|bz [命令名] - 查看命令帮助信息
  - 清屏命令：#清屏|clear|cls - 清空控制台输出
  - 刷新命令：#刷新|refresh|sx [目标] - 刷新当前或指定表格数据
  - 切换命令：#切换|switch|qh [标签页] - 快速切换任务/设备/日志标签页
  - 选择命令：#选择|select|xz [目标ID列表] - 批量选择表格目标
  - 清空选择命令：#清空选择|clearselect|qkxz - 清空当前目标选择
  - 时间命令：#时间|time|sj - 显示当前时间（多种格式）
  - 状态命令：#状态|status|zt - 显示当前页面状态和统计信息
  - 统计命令：#统计|stats|tj - 显示详细的设备和任务状态统计
  - 搜索命令：#搜索|search|ss [关键词] - 在当前表格中搜索内容
  - 导出命令：#导出|export|dc [格式] - 导出表格数据为CSV或JSON格式
- #技术实现优势
  - 统一的命令处理架构，前后端保持一致的用户体验
  - 支持中文和英文命令别名，提高输入效率
  - 模块化设计，易于扩展新命令功能
  - 完整的参数验证和错误处理机制
  - 异步命令执行支持，不阻塞用户界面
  - 自动补全命令名和缩写功能
- #用户体验提升
  - 无需切换操作界面，直接通过命令行快速操作
  - 支持命令历史记录和方向键导航功能
  - 实时反馈命令执行结果和错误信息
  - 提供丰富的帮助信息和使用说明
  - 统一的命令语法和参数格式
  - 支持表格数据导出和搜索等高级功能

#### 优化任务表设备列显示格式，提升用户体验
- #修改任务表中设备列显示格式为"设备名(设备ID)"
  - 原来只显示设备ID，不够直观
  - 现在显示为"设备名(设备ID)"格式，方便用户识别设备
  - 当设备名称不存在时，自动显示为"设备[ID]([ID])"格式
  - 保持设备状态颜色标识功能不变
  - 调整设备列宽度从120px增加到160px，适应新的显示内容
- #技术实现
  - 前端通过get(deviceId)方法获取完整设备信息
  - 使用device.name || `设备${deviceId}`作为设备名称显示
  - 服务端数据结构保持不变，仍然传输设备ID
  - 前端负责根据设备ID查找设备名称并格式化显示
- #用户体验优化
  - 设备信息更加直观易读
  - 保持原有的状态颜色和筛选功能
  - 兼容设备名称为空的情况，提供默认显示格式

#### 修复日志系统日期格式比较Bug，统一日期格式处理
- #创建DateHelper统一日期处理工具类
  - 新增DateHelper类用于统一处理各种日期格式转换和比较
  - 支持多种输入格式：'2025-06-19'、'20250619'、datetime对象、None等
  - 标准化输出格式为'YYYYMMDD'，确保所有日期比较使用统一格式
  - 提供normalize()方法统一转换日期格式
  - 提供isToday()方法准确判断是否为今天
  - 提供format_display()方法转换为可读的显示格式
- #修复getLogs方法中的日期格式比较Bug
  - 问题：前端过滤器传入'2025-06-19'格式，但系统内部使用'20250619'格式比较
  - 解决：使用DateHelper.normalize()统一转换所有日期参数
  - 修复_Log_.py中getLogs方法的日期比较逻辑，确保缓存正确命中
  - 修复SCmds.py和CCmds.py中的getLogs命令，统一使用DateHelper处理日期
  - 所有日期相关的操作都使用统一的格式标准，避免格式不一致导致的比较错误
- #优化日志加载性能和用户体验
  - 缓存日期比较更加准确，避免重复加载相同日期的日志
  - 日志加载信息显示更加友好，包含格式化的日期显示
  - 命令参数文档更新，明确支持多种日期格式输入
  - 返回数据包含标准化日期和显示格式日期，方便前端使用
- #技术实现优势
  - 统一的日期处理工具类，提高代码复用性和维护性
  - 支持多种日期格式输入，提升用户体验和系统兼容性
  - 彻底解决日期格式不一致导致的缓存失效问题
  - 为后续其他日期相关功能提供了统一的处理基础

### 2025-01-14

#### 配置Cursor MEMORIES功能，支持跨会话记忆
- #配置项目级别的MCP服务器以启用MEMORIES功能
  - 创建.cursor/mcp.json配置文件，启用@anthropic-ai/memories服务
  - 配置内存文件存储路径：E:/Project/AndoirdClicker/.cursor/memories.jsonl
  - 使用npx方式动态安装和运行memories包，无需本地安装
  - 支持跨Cursor会话保持项目相关的上下文记忆
- #建立MEMORIES使用规则和项目特定配置
  - 创建rules/memories.mdc规则文件，定义内存管理策略
  - 自动在任务开始前读取已存储的记忆信息
  - 任务完成后自动更新实体、关系和观察记录
  - 集成项目特定信息：Socket.IO通信、事件命名规范、服务器重启命令等
- #技术优势
  - Cursor现在能够记住项目架构、代码风格和之前的讨论内容
  - 减少重复解释项目结构和技术选择的时间
  - 提高开发效率和代码一致性维护
  - 跨会话的上下文连续性，避免丢失重要项目知识

### 2025-01-14

#### 优化前端命令执行架构，统一异步处理逻辑
- #重构sendCmd方法，内部统一处理命令结果
  - 修改sendCmd方法在内部调用onCmdResult统一处理命令执行结果
  - 移除所有调用处的.then()和.catch()链式调用，简化代码结构
  - 在sendCmd内部统一处理错误情况，显示错误通知
  - 消除代码重复，所有命令执行都使用相同的结果处理流程
- #简化命令调用方式，提高代码一致性
  - loadClientLogs方法简化为直接调用sendCmd，无需额外的异步处理
  - sendCommand方法简化为直接调用sendCmd，统一命令执行逻辑
  - handleDeviceAction方法保持简洁的命令调用方式
  - 删除onCmdResult中对已废弃getClientLogs命令的处理逻辑
- #技术优势
  - 统一的异步处理逻辑，减少代码维护成本
  - 错误处理集中化，提高用户体验一致性
  - 简化的调用方式，降低开发复杂度
  - 为后续功能扩展提供更好的架构基础

#### 修复日志前台显示问题
- #修复Server.py中onB2S_loadDatas函数的变量名冲突问题
  - 问题：log变量与_Log_.gets(date)返回的日志对象混淆导致toSheetData()调用失败
  - 解决：将变量名从log改为Log，日志遍历中使用logItem避免冲突
  - 修复后前台可以正常显示日志数据
- #优化日志系统初始化，支持预加载当天日志
  - 在onLoad方法中增加服务端环境的今日日志预加载
  - 使用延迟加载机制，避免在系统初始化时调用emit导致的错误
  - 通过独立线程延迟2秒后加载今日日志，确保系统完全初始化
  - 确保前台页面打开时能看到历史日志数据
- #优化日志数据结构，去除冗余字段
  - 删除日志数据中的date字段，统一使用time字段存储完整时间
  - 修改date属性从time字段中提取日期部分，减少数据冗余
  - 优化前台日志表格列配置，日期和时间列都从time字段获取数据
  - 日期列显示'2025-01-14'格式，时间列显示'10:30:45'格式
  - 减少日志文件大小，提高存储和传输效率
- #优化日志获取命令结构，明确区分服务端和客户端
  - 服务端getLogs命令简化为只获取服务端日志，无需deviceId参数
  - 客户端getLogs命令保持不变，用于获取客户端本地日志
  - 前端统一使用getLogs命令，通过目标设备列表区分服务端和客户端
  - 移除不必要的S2B_switchTab事件和页面切换逻辑
- #重构前端命令执行架构，统一处理逻辑
  - 新增onCmdResult统一命令结果处理函数，支持不同命令的专门处理
  - 新增handleGetLogsResult专门处理getLogs命令结果
  - 修改sendCommand方法，统一使用onCmdResult处理命令结果
  - 简化loadClientLogs方法，使用统一的命令执行和结果处理逻辑
  - 消除代码重复，提高可维护性和扩展性
  - 为后续添加更多命令处理逻辑提供统一框架

#### 日志系统统一架构重构
- #统一服务端和客户端日志保存策略，全部改为本地文件存储
  - 移除服务端数据库存储依赖，删除SModelBase_和LogModel_相关代码
  - 统一使用本地文件保存方式，服务端和客户端代码逻辑完全一致
  - 简化_Log_类继承结构，直接继承object而非动态继承
  - 保留服务端90天、客户端30天的差异化清理策略
  - 优化缓存大小为100条，提高批量写入效率
- #优化日志文件存储结构，按设备分类管理
  - 日志文件路径改为二级目录结构：logDir/设备名/日期.log
  - 服务端日志保存在logDir/server/目录下
  - 客户端日志保存在logDir/设备ID/目录下
  - 自动创建对应设备目录，避免不同设备日志混合
  - 便于按设备查看和管理日志文件
- #增加服务端和客户端测试命令，便于日志系统调试
  - 在SCmds.py和CCmds.py中都添加saveLog命令(#保存日志|bcrz)
  - 支持服务端和客户端都能手动触发日志缓存保存到文件，便于测试
  - 返回详细的保存路径信息，方便定位日志文件
  - 客户端和服务端使用相同的命令格式，保持一致性
- #简化日志处理流程，提升系统性能
  - 移除createLogData等冗余方法，统一使用add方法创建日志
  - 优化_save方法，统一处理dirty日志的文件写入逻辑
  - 简化_loadLogs方法，统一从文件系统加载日志数据
  - 保持前端数据刷新机制，服务端日志仍可实时推送到前端
  - 消除服务端数据库压力，减少I/O依赖和复杂度
- #代码维护优势
  - 客户端服务端代码统一，减少维护工作量
  - 消除数据库依赖错误，提高系统稳定性
  - 文件存储方式便于日志备份和迁移
  - 简化的代码结构更易于理解和扩展

### 2025-01-14

#### 修复日志系统递归错误和设备debug属性优化
- #修复_Log_类中的无限递归错误
  - 问题：__getattr__方法中使用hasattr(self, '_model')会触发自身递归调用
  - 解决：使用object.__getattribute__直接访问属性，避免递归调用
  - 修复toDict方法中的类似递归问题，确保日志系统稳定运行
  - 修正onLoad方法的初始化逻辑，保证服务端和客户端正确初始化
- #优化设备debug属性为临时属性
  - 将SDevice的debug属性改为一般属性，不保存到数据库
  - debug属性默认为False，作为临时开关控制日志发送
  - 修改setDebug方法，直接设置内存属性而不是数据库字段
  - 在toSheetData中包含debug状态，确保前端能正确显示
  - 通过onS2C_updateDevice机制同步debug状态到客户端
- #优化日志缓存机制为当天专用
  - _cache只缓存当天日志，提高缓存效率和内存使用
  - _loadLogsInternal方法直接返回日志列表，不操作缓存
  - getLogs方法智能判断：当天日志使用缓存，其他日期直接加载
  - 当天日志首次访问时自动加载并缓存，后续访问直接返回缓存
  - 非当天日志不缓存，避免内存占用过多
  - 服务端当天日志加载后自动更新前台日志表格数据
  - 为_Log_类添加toSheetData方法支持前台数据格式
- #技术实现优势
  - debug开关响应更快，无需数据库读写操作
  - 重启后自动恢复默认状态，避免遗留调试设置
  - 减少数据库存储压力，提高系统性能
  - 保持前端和客户端的状态同步机制完整
  - 当天日志缓存机制提升频繁访问的性能
  - 历史日志按需加载，减少内存占用和数据库压力
  - 简化的缓存逻辑，代码更清晰易维护

#### 日志系统架构统一重构
- #统一客户端和服务端日志结构，使用统一的_cache缓存
  - 移除_clientLogCache专用列表，客户端和服务端都使用_cache
  - 修改addToCache方法支持统一的日志对象缓存
  - 优化saveFile方法使用log.toDict()保存日志数据
  - 增强toDict方法支持服务端模型和客户端字典两种数据源
- #完善日志加载机制，支持客户端文件和服务端数据库
  - 重构getLogs方法统一处理客户端文件加载和服务端数据库加载
  - 在onLoad初始化时自动加载当天日志到缓存
  - gets方法简化为getLogs的兼容调用
  - 支持日期缓存机制，避免重复加载相同日期的日志
- #优化日志对象属性访问，支持模型和字典双重数据源
  - 增强__getattr__方法支持_model和data两种属性访问方式
  - 完善add方法的错误处理和日志对象创建逻辑
  - 统一日志系统初始化流程，提供详细的加载反馈

#### Android客户端日志系统重构完成
- #移除底层logToConsole方法，统一调用脚本日志接口
  - 删除ToolBarService.kt中的logToConsole方法，避免直接显示到手机端VIEW
  - 修改所有底层日志调用统一使用ToolBarService.log方法
  - log方法内部调用Python脚本层的_G._G_.Log().log函数
  - 实现底层→脚本层→服务端的统一日志流向
- #移除手机端日志显示VIEW，保留命令输入功能
  - 删除toolbar.xml中的日志区域(logArea)、日志滚动视图(logScrollView)、日志文本视图(logTextView)
  - 删除日志过滤相关UI组件：过滤按钮、过滤输入框、TAG选择器
  - 移除"展开/收起日志"按钮(toggleLogsButton)
  - 保留命令输入区域和工具栏按钮，维持基本操作功能
- #清理相关代码和方法
  - 删除所有日志VIEW相关方法：filterLogs、initLogSystem、setupConsoleView、updateTagList等
  - 移除日志展开状态变量logsExpanded和相关控制逻辑
  - 简化窗口布局参数，统一使用WRAP_CONTENT高度
  - 修改PythonServices.showLog方法为兼容性存根，避免脚本调用错误
- #技术实现优势
  - 手机端界面更简洁，减少资源占用和UI复杂度
  - 日志统一通过服务端管理，支持远程查看和分析
  - 保持命令输入功能，维持调试和控制能力
  - 客户端日志本地缓存机制完整保留，支持离线日志记录
- #代码清理和优化
  - 删除PythonServices.kt中无用的log相关接口方法
  - 将cGetLog命令从CCmds.py移动到SCmds.py，更符合服务端命令分类
  - 删除Server.py中冗余的onB2S_getClientLogs事件处理器
  - 前端调用优化为直接使用服务端命令，简化调用链路
- #用户体验优化
  - 修复ToolBarService.kt命令输入框回车发送功能，支持多种发送方式
  - 将"获取客户端日志"菜单从日志表移动到设备表，更符合逻辑
  - 优化客户端日志获取：只针对选中设备，自动切换到日志页面显示结果
  - 增加离线设备检查，避免向离线设备发送无效请求

### 2025-01-14

#### 修复日志系统动态继承错误
- #修复_Log_类动态继承SModelBase_时的TypeError错误
  - 问题：动态修改类的__bases__属性在Python中有严格限制，当deallocator不兼容时会报错
  - 解决方案：重构_Log_类，使用组合模式替代动态继承
  - 新的_Log_类通过组合SModelBase_实例来实现功能，避免了运行时类修改
  - 增加__getattr__方法实现属性委托，保持API兼容性
  - 支持服务端和客户端环境的自适应初始化
  - 消除了"__bases__ assignment: 'SModelBase_' deallocator differs from 'object'"错误

#### 修复日志系统循环调用问题
- #解决客户端日志系统的无限循环调用错误
  - 问题：ToolBarService.log调用Python的log函数，Python的log_又调用android.log，形成循环
  - 解决方案：修改Python的log_方法，避免调用android.log，直接使用_PCLog_输出
  - 重新启用ToolBarService中的系统日志输出，确保日志能正确显示到logcat
  - 保持Python和Kotlin日志系统的功能完整性，消除循环调用

### 2025-01-13

#### 设备调试日志控制系统
- #增加设备debug状态字段，支持远程控制客户端日志输出
  - DeviceModel_新增debug字段(bool类型，默认False)，用于控制设备日志是否发送到服务端
  - 修改_Log.py中的log函数，检查设备debug状态决定是否向服务端发送日志
  - 客户端Kotlin代码集成Python脚本log函数调用，统一使用服务端日志系统
  - 前端表格视图增加DEBUG列，支持点击切换设备debug状态
  - 服务端新增updateDevice事件处理器，实时同步debug状态修改到数据库和客户端
- #技术实现细节
  - 客户端log函数调用PythonServices.callPythonFunction("_G._G_.Log().log")向服务端发送日志
  - 服务端根据设备debug状态过滤日志，只在debug=True时存储到数据库
  - 前端表格checkbox点击后通过socket.emit('updateDevice')实时更新设备状态
  - 支持通过后台界面远程控制任意客户端的日志监控开关
  - 便于调试特定设备问题，避免所有设备日志混合造成干扰

### 2025-01-12  

#### 修复isRectIn函数参数错误
- #修复了matchText函数中调用isRectIn时的参数类型错误
  - 问题：当屏幕信息的bounds字段为空字符串时，使用*i['b']解包会导致参数错误
  - 解决：增加类型和长度检查，确保i['b']是包含至少4个元素的列表才调用isRectIn
  - 避免了因bounds数据格式不正确导致的运行时错误

#### 从GIT历史恢复丢失的swipe函数
- #从git历史中成功恢复了在CTools.py合并到_Tools.py时丢失的swipe相关函数
  - 使用git show命令从提交197645c^版本恢复了完整的swipe和swipeTo函数代码
  - swipe函数支持坐标格式"x1,y1 > x2,y2 [duration]"和方向枚举"方向 [duration]"两种调用方式
  - 支持8个方向的滑动操作：CR/CL/CU/CD(中心)和ER/EL/EU/ED(边缘)
  - swipeTo函数提供智能滑动查找功能，支持单向(L/R/U/D)和双向(LR/UD)搜索
  - 新增isScreenSimilar函数用于屏幕内容相似度比较，判断是否到达滑动边界
  - 修复了findTextPos函数中调用swipe的错误，改为调用swipeTo函数
  - 完整恢复了滑动相关的所有功能，确保脚本兼容性

### 2025-01-12

#### 脚本同步机制优化 
- #改进syncFiles方法为"清空+重新同步"模式
  - 废弃原有的版本比对增量同步方式，避免旧文件干扰模块加载
  - 新增clearLocalScripts()方法，彻底清空本地scripts目录和根目录.py文件
  - 采用简化的全量同步策略，确保本地和服务端完全一致
  - 添加递归删除功能deleteRecursively()，安全处理目录清理
  - 增强同步结果反馈，显示成功和失败的文件数量
  - 保留单个文件热加载机制处理零散更新
- #优化用户体验
  - 同步过程中显示清空和下载进度信息
  - 完成后Toast提示同步结果统计
  - 增强日志记录，便于问题排查和性能监控

#### Android客户端Flask依赖错误修复
- #修复手机端运行客户端时的ModuleNotFoundError: No module named 'flask'错误
  - 问题根源：_Log.py模块被客户端和服务端共用，但直接导入了服务端模块SModels和SModelBase
  - SModels导入链：SModels → SDatabase → flask，在Android环境中导致导入失败
  - 修复方案：将_Log.py中的服务端模块导入改为条件性导入机制
  - 添加_initServerModules()函数，只在服务端环境中导入数据库相关模块
  - 客户端环境中跳过所有数据库操作，使用简化的日志处理
  - 通过_G._G_.isServer()判断运行环境，实现环境隔离
  - 保持日志API完全兼容，客户端和服务端代码无需修改
- #技术实现细节
  - 使用try/except ImportError机制安全处理模块导入失败
  - 客户端环境使用字典结构代替数据库模型对象
  - 动态继承机制处理类的继承关系差异
  - 确保所有数据库相关方法在客户端环境中安全跳过

### 2025-01-12

#### 客户端连接稳定性修复
- #修复客户端连接服务端后频繁断开的问题
  - 修复_G.py中emitRet方法的死循环问题，添加超时控制机制
  - 优化客户端socketio配置，启用心跳超时和重连参数
  - 增强服务端socketio配置，设置合适的心跳间隔和超时时间
  - 依赖SocketIO内置的ping/pong心跳机制保持连接活跃
  - 添加连接状态监控和日志记录，便于问题排查
  - 提高登录超时时间，避免因网络延迟导致的登录失败
  - 改进错误处理和异常捕获，增强连接的稳定性
- #SocketIO心跳机制配置
  - 服务端ping_interval=25秒，ping_timeout=60秒
  - 客户端只配置重连参数，依赖服务端的心跳设置
  - 使用SocketIO/Engine.IO内置心跳机制，无需手动实现心跳线程
  - 移除客户端不支持的ping参数，避免初始化错误
  - 增强连接的稳定性和可靠性

### 2025-01-12

#### 服务端收益获取系统设计与实现
- #重新设计服务端getScores函数
  - 实现完整的客户端调用→任务更新→前端同步流程
  - 增强错误处理和日志记录，提供详细的执行反馈
  - 支持收益数据验证，过滤无效任务名和分数
  - 自动获取或创建任务记录，支持跨日期任务管理
  - 返回详细的处理结果：总分数、任务数量、更新详情
- #任务模型增强
  - 为STask_类新增get类方法，支持设备ID和任务名查询
  - 集成TaskModel_的数据库操作，实现数据持久化
  - 自动触发前端表格刷新，确保UI实时更新
  - 支持任务分数的历史对比，记录新旧分数变化
- #数据库操作修复
  - 修复Flask应用上下文未初始化导致的任务创建失败问题
  - 统一所有数据库模型使用Database.sql()进行上下文管理
  - 优化TaskModel_、DeviceModel_的get/commit/all方法
  - 确保所有数据库操作在正确的Flask应用上下文中执行
- #前端自动更新机制
  - 利用SModelBase_的refresh方法自动推送任务表更新
  - 通过S2B_sheetUpdate事件实现前端表格实时同步
  - 无需手动刷新页面，任务数据变更立即可见

#### OCR智能比较与收益合并优化
- #在_G_类中新增OCR容易出错的字符对映射
  - 定义常见OCR识别错误字符对：市↔币、全↔金、奖↔将、励↔历等40+字符对
  - 支持中文繁简转换：专↔專、属↔屬、频↔頻等
  - 涵盖形似字符：广↔店、告↔苦、视↔规、开↔間等
- #新增ocrCompare智能字符串比较函数
  - 支持最大错误字符数限制，默认允许2个字符差异
  - 智能识别OCR容易出错的字符对，提高匹配准确率
  - 严格要求字符串长度相等，确保比较结果可靠性
  - 位置对应比较，只允许OCR错误字符对不一致
- #收益解析算法增强
  - 在parseScore中集成OCR比较和合并逻辑
  - 自动识别"看广告金市奖励"和"看广告金币奖励"为同一任务
  - 智能合并相同任务的多条记录，累加金额总数
  - 保留第一条记录的日期和任务名称作为合并结果
  - 显著减少重复数据，提高收益统计准确性

### 2024-03-22

#### 收益解析算法重构
- #完全重写parseScore收益记录解析逻辑：
  - 采用智能定位匹配算法，替代原有的简单行分析
  - 根据OCR文本的边界框信息，建立空间关系分析
  - 为每个金额项目寻找最匹配的日期和任务名称
  - 优化名字匹配策略：优先匹配同行左方的任务名称
  - 增强UI元素过滤：排除"明细"、"去切换"等界面元素
  - 添加文本有效性验证：长度>=3且包含汉字或字母
  - 支持垂直和水平布局的OCR数据解析
  - 大幅提升收益记录提取的准确性和完整性

#### 命令系统重大改进
- #优化正则表达式生成机制：所有参数统一设为可选模式
- 参数转换：`(?P<param>\S+)` → `(?:\s+(?P<param>\S+))?`
- 支持参数在调用时传入，而非仅从命令字符串解析
- #新增必须参数验证机制：在do方法中检查函数签名
- 对于没有默认值的参数，动态验证是否有值传入
- 缺少必须参数时自动显示错误信息，提高用户体验
- 实现了命令模式匹配与参数验证的完全分离
- 增强了命令系统的灵活性和健壮性

### 2024-03-19
- 新增收益读取功能：
  - 客户端命令 GetScores(appName, date)：获取指定应用指定日期所有任务收益
  - 服务端命令 GetScores(deviceId, appName, date)：调用客户端命令，写入任务表并返回当天/前天总收益

## 2024-03-21
### 功能优化
- 设备表格默认排序优化
  - 设置设备表格状态列默认降序排序
  - 在线和已登录设备优先显示在前面
  - 保持用户手动排序的灵活性

### 修复
- 修复了多线程环境下日志保存时的数据库会话冲突问题
  - 在保存日志到数据库时，创建新的日志对象而不是重用现有对象
  - 避免了同一个对象被多个会话同时使用的问题

### 数据库管理优化
- 改进了数据库session管理机制
- 修复了对象与session解绑导致的提交错误
- 统一使用Database.sql()函数管理事务和应用上下文
- 优化了数据库操作的错误处理机制

### 2024-03-19
- 优化客户端启动功能
  - #调整参数顺序为[设备ID] [客户端数量]
  - 设备ID为空时默认为Test
  - 客户端数量为空或小于1时默认为1
  - 单个客户端时使用设备ID_序号作为客户端ID
  - 多个客户端时使用test序号作为客户端ID

### 2024-08-08
- 增强表格分页功能
  - #实现所有表格自动滚动到最新数据
  - 任务表、设备表、日志表在数据更新后自动跳转至末页
  - 新增分页状态跟踪，用户手动翻页后停止自动跳转
  - 优化数据更新后的页面定位体验

### 2024-08-07
- 优化键盘快捷键功能
  - #修复空格快捷键在命令输入框中依然生效的问题
  - #确保空格快捷键只在表格区域具有焦点时触发

### 2024-08-06
- 优化设备表及目标设备管理机制
  - 隐藏设备表ID列，保留id属性用于后台识别
  - 修改目标设备机制，使用deviceId而非id存储目标设备
  - 启用表格选择状态持久化机制，移除冗余的选择状态跟踪
  - 优化发送命令流程，优先使用目标设备，其次使用选中设备

### 2024-08-05
- 修复设备表相关问题
  - 修复设备表缺少ID列显示的问题，在prepareDeviceData函数中增加deviceId字段
  - 解决设置设备为目标后设备ID列内容消失的问题
  - 确保设备ID列在设备变为目标设备后仍能正常显示

### 2024-07-29
- 重构控制台连接管理机制
  - 将控制台连接也作为SDevice_类型进行管理，设备ID以@开头
  - 将_consoles从set改为Dict[str, SDevice_]，键为SID，值为SDevice_实例
  - 数据库加载时过滤掉控制台ID，不加载到普通设备列表中
  - 为控制台添加单独的状态管理，支持显示在线/离线/登录状态
  - 改进handleB2SLoadDevices，分别发送设备和控制台数据
  - 支持控制台登录功能，登录后状态从online变为login
  - 控制台设备变更时自动发送S2B_sheetUpdate事件更新前端
  - 提高了控制台连接的可跟踪性和可管理性

### 2024-07-28
- 优化设备状态管理
  - 创建统一的设备状态定义(deviceStatusMap)，包含状态值、标签、颜色和图标
  - 修正设备状态处理逻辑，确保正确显示"login"和"logout"状态
  - 改进状态过滤器，从统一定义中动态构建过滤选项
  - 统一状态显示格式，提高代码可维护性
  - 动态生成状态格式化参数，确保UI呈现与状态定义一致
  - 修复在状态处理中缺失login/logout导致显示问题的bug
  - 优化数据验证逻辑，使用统一的有效状态列表
- 优化日志等级管理
  - 创建统一的日志等级定义(logLevelMap)，包含等级值、标签、颜色和图标
  - 使用统一定义生成等级过滤器选项和格式化参数
  - 简化formatter函数实现，直接使用预定义格式化模板
  - 改进等级验证逻辑，使用统一的有效等级列表
  - 统一等级显示风格，提高视觉一致性和代码可维护性
  - 修复日志等级验证中的默认值设置

### 2024-07-27
- 优化表格过滤器功能
  - 为设备状态、日志标签和日志等级过滤器添加"全部"选项
  - 设备状态过滤器增加"已登录"和"已登出"选项
  - 日志标签过滤器改为下拉选择模式，包含所有可能的标签类型
  - 将日志标签和设备状态转为枚举类型，增加代码可维护性
  - 优化过滤器默认行为，支持查看全部数据
  - 提升数据筛选的灵活性和用户体验

### 2024-07-26
- 增强Socket.IO事件调试功能
  - 添加通用事件监听器，记录所有接收到的未处理事件
  - 在服务启动时打印所有已注册的事件处理器列表
  - 增加Socket.IO事件处理函数的调试日志
  - 添加请求源信息和SID记录，帮助定位事件来源
  - 改进handleB2SLoadLogs函数，添加明确的响应反馈
  - 发送S2B_logsLoadStatus事件通知前端请求处理状态
  - 增强异常处理，确保错误信息正确传回前端

### 2024-07-25
- 修复表格日期过滤器错误
  - 解决"No such editor found: date/datetime"错误
  - 将自定义过滤器类型(dateInput, datetimeInput, timeInput)替换为标准input类型
  - 保留日期和时间格式提示，在占位符中显示格式说明
  - 为所有日期时间过滤器添加格式提示，如"YYYY-MM-DD"
  - 保留单元格编辑器的日期和时间格式化功能
  - 确保与现有的默认过滤器设置兼容
  - 提高表格过滤功能的兼容性和稳定性

- 修复日志系统中的Eventlet协程错误
  - 解决"Cannot switch to MAINLOOP from MAINLOOP"错误
  - 将标准线程(threading.Thread)替换为Eventlet的协程(eventlet.spawn)
  - 修改日志保存和加载方法中的异步处理逻辑
  - 避免在Eventlet主循环中启动可能阻塞的线程
  - 完善错误处理和日志记录
  - 提高了在Eventlet环境下的兼容性和稳定性
  - 确保Socket.IO服务器能够正常关闭而不抛出异常

### 2024-07-24
- 改进表格日期和时间过滤功能
  - 将日期列过滤器从普通文本输入改为日期选择器(dateInput)
  - 将时间列过滤器从普通文本输入改为时间选择器(timeInput)
  - 将日期时间列过滤器改为日期时间选择器(datetimeInput)
  - 为所有日期和时间过滤器添加输入格式配置
  - 为过滤器添加占位符提示，提高用户体验
  - 确保与现有的默认过滤器设置兼容
  - 提升了日期和时间筛选功能的易用性和准确性

### 2024-07-23
- 优化日志系统，移除本地文件存储
  - 移除与本地日志文件加载和保存相关的逻辑，全部使用数据库存储
  - 删除_path方法和APP_LOGS常量，不再需要本地文件路径
  - 使用线程执行数据库操作，避免Socket.IO主事件循环中的阻塞操作
  - 修复服务器停止时出现的"do not call blocking functions from the mainloop"错误
  - 改进handleB2SLoadLogs函数，使用异步方式加载日志数据
  - 确保Socket.IO连接正确设置client_type参数
  - 提高日志系统稳定性和性能

### 2024-07-22
- 优化日志系统，解决循环引用问题
  - 将LogModel_类集成到_Log.py文件中，不再从SModels导入
  - 修改日志查找机制，使用循环遍历替代get方法
  - 添加日志重复检测和计数功能，重复日志增加count字段
  - 完善日志ID生成算法，基于tag+level+message+time计算哈希值
  - 增加条件检查，确保只有在必要时才发送Socket通知
  - 优化数据库查询逻辑，使用Database.sql方法执行查询
  - 修复缺失time参数时的默认处理逻辑

### 2024-07-21
- 增强数据验证和规整功能
  - 新增toSheetData方法，确保数据符合表格列定义要求
  - 自动过滤不需要的数据字段，只保留表格列定义中的字段
  - 为缺失字段设置合适的默认值，如状态、进度、得分等
  - 对数据字段进行类型和值范围验证，标记错误数据为"ERR"
  - 过滤掉没有id字段的无效数据项
  - 确保状态字段值在预定义范围内
  - 为数值字段(progress, score)添加类型转换和范围限制
  - 在控制台记录数据处理中的警告和错误
  - 修改updateData方法，使用toSheetData处理输入数据

### 2024-07-20
- 优化表格页面初始化逻辑
  - 移除SheetPage构造函数中的initialDevices和tasksData参数
  - 所有数据集统一初始化为空数组
  - 完全依赖Socket通信机制获取数据，实现数据更新与渲染分离
  - 减少构造函数参数，提高代码清晰度
  - 使界面渲染与数据加载更加独立，符合关注点分离原则
  - 简化页面初始化流程，统一数据获取方式

### 2024-07-19
- 统一数据结构，简化数据处理逻辑
  - 所有数据统一使用数组格式，移除对象格式的支持
  - 简化updateData方法，专注处理数组类型数据
  - 对初始设备数据添加类型检查，确保始终为数组格式
  - 优化prepareDeviceData方法，无需处理多种数据格式
  - 统一表格数据更新逻辑，直接使用原始数据更新表格
  - 移除多余的条件判断，使代码更加简洁高效

### 2024-07-18
- 优化数据更新相关代码
  - 将三个数据更新方法(updateTasksData, updateDevicesData, updateLogsData)合并为一个通用的updateData方法
  - 通过参数区分不同的数据类型和处理逻辑
  - 新增getTabNameByDataType工具方法，根据数据类型获取对应的标签页名称
  - 减少代码冗余，提高代码复用性和可维护性
  - 统一数据更新逻辑，简化条件判断流程
  - 保持相同的功能，同时提高了代码质量

### 2024-07-17
- 优化Socket通信机制
  - 将多个更新事件(S2B_tasksUpdate, S2B_deviceUpdate, S2B_logsUpdate)合并为统一的S2B_sheetUpdate事件
  - 实现根据数据类型(tasks, devices, logs)自动更新对应数据集的功能
  - 添加支持增量更新的机制，根据对象ID判断是更新还是新增
  - 任务操作命令(执行、暂停、取消)统一改为B2S_cmd格式，并指定设备ID
  - 简化B2S_loadTasks等加载事件的过滤器，仅保留日期过滤
  - 新增updateTasksData、updateDevicesData和updateLogsData方法处理不同类型数据更新
  - 优化数据更新流程，提高前后端数据同步效率

### 2024-07-16
- 重构表格数据类型管理
  - 添加 DataType 枚举定义，规范化数据类型的使用
  - 修改所有使用字符串类型的地方，改用枚举值
  - 优化 tabTypeMap 映射表，使用枚举值作为数据类型
  - 更新所有表格相关方法，统一使用 DataType 枚举
  - 修复过滤器事件处理，改用 dataFiltered 事件
  - 完善过滤器参数收集逻辑，支持所有类型的过滤条件

### 2024-07-15
- 重构表格相关文件命名和功能
  - 将 Tasks.js 和 Tasks.html 重命名为 Sheet.js 和 Sheet.html
  - 在表格中添加新的"日志"标签页，显示系统日志数据
  - 为所有表格中的日期和时间字段启用专用的日期和时间编辑器
  - 任务表中的进度已使用进度条显示（之前已存在）
  - 重命名相关类名，从 TaskPage 改为 SheetPage
  - 优化日志表结构，包含日期、时间、标签、等级、发送者和内容字段
  - 添加Socket事件监听，支持日志数据的实时更新
- 修复表格初始化问题：解决在表格完全构建前调用getHeaderFilters方法导致的错误
- 优化表格数据加载流程，确保在表格初始化完成后再加载数据
- 改进过滤器处理逻辑，增强表格组件的稳定性

### 2024-07-11
- 优化事件监听器性能
  - 添加 {passive: true} 选项到所有事件监听器
  - 消除浏览器"non-passive event listener"警告
  - 提高页面滚动性能和响应速度
  - 优化了标签页切换按钮、上下文菜单和外部点击事件处理
  - 遵循现代浏览器最佳实践，避免阻塞滚动线程

### 2024-07-10
- 修复设备表格状态显示和标签切换问题
  - 修复设备表状态列lookup格式化器的"Missing display value for offline"错误
  - 改进设备数据处理，确保状态值始终为"online"或"offline"
  - 完全重构标签页切换逻辑，采用表格重建方式而非动态更新列和数据
  - 解决了修改列定义和加载数据顺序导致的问题
  - 优化表格初始化流程，确保数据和列定义完全匹配
  - 使用destroy()和重建表格的方式，替代之前不可靠的setColumns和setData调用

### 2024-07-09
- 修复标签页布局和数据加载问题
  - 将标签页按钮靠左对齐排列，而非居中
  - 修复切换标签页后数据消失的bug
  - 优化数据加载流程，使用setTimeout和Promise确保数据正确加载
  - 移除冗余的clearData调用，防止数据丢失
  - 添加左侧内边距，提升标签页整体布局美观度
  - 调整标签按钮使用margin-right而非margin来保持一致的间距

### 2024-07-08
- 优化自定义标签页风格和结构
  - 简化标签页，移除设备视图标签，仅保留任务和设备两个标签
  - 重新设计标签页风格，采用深色主题与表格匹配：黑底白字，深绿色边框
  - 当前选中标签使用粗体字体和浅绿色边框提供视觉反馈
  - 添加过渡动画效果，提升用户体验
  - 调整标签页间距和内边距，优化整体布局
  - 减少不必要的代码逻辑，提高性能

### 2024-07-07
- 重构表格视图，用自定义标签页替代spreadsheet模式
  - 移除spreadsheet模式，改用自定义标签页UI实现多视图切换
  - 在表格底部添加切换按钮（任务、设备、设备视图）
  - 恢复分页功能，支持每个视图独立分页
  - 使用setColumns和setData动态切换表格内容
  - 增加标签页切换视觉反馈（颜色变化）
  - 重组代码结构，抽取设备数据和列定义为独立方法
  - 在标签切换时自动应用过滤器
  - 设置表格高度为calc(100% - 40px)，为标签栏预留空间

### 2024-07-06
- 修复表格视图模块兼容性问题
  - 解决了错误：The spreadsheet module is not compatible with the pagination module
  - 移除了pagination配置，包括pagination、paginationSize和paginationSizeSelector
  - 保留表格的spreadsheet模式，确保任务和设备表格标签页正常工作
  - 优化表格显示，实现任务和设备数据的切换显示
  - 确保过滤和排序功能继续工作

### 2024-07-05
- 修复表格视图数据类型错误
  - 修复了表格数据非数组类型导致的"s.forEach is not a function"错误
  - 在TaskPage类中增加数据类型检查和转换，确保tasks始终是数组类型
  - 在构造函数和socket事件监听中增加数据类型检查和转换
  - 在initMainTable方法中添加额外的数组检查，防止非数组数据导致的错误
  - 优化了数据处理逻辑，提高表格渲染的稳定性和可靠性

### 2024-07-01
- 改进表格视图，使用Tabulator原生标签页API
  - 修复表格视图同时显示任务表和设备表的问题，改为使用原生标签页
  - 使用spreadsheet:true和spreadsheetSheetTabs:true开启标签页功能 
  - 将标签页位置从顶部移到底部，符合Tabulator电子表格默认布局
  - 删除自定义标签页样式，使用Tabulator库的默认黑色主题
  - 优化表格布局，使其填满整个可用空间
  - 修改applyDateFilter方法，使用getModule("spreadsheet")获取标签页

### 2024-12-35
- 优化任务表格视图界面
  - 修复表格视图同时显示任务表和设备表的问题，改为默认只显示任务表
  - 使用Tabulator库自带的标签页功能，替代自定义HTML标签页
  - 应用Tabulator的默认表格样式，提供更一致的用户体验
  - 优化表格布局，使其填满整个可用空间，消除空白区域
  - 修改HTML容器类为container-fluid，确保全屏显示
  - 调整表格高度计算，使用calc(100vh - 20px)最大化利用空间
  - 将自定义格式化器替换为Tabulator内置的lookup格式化器
  - 增加initialPage配置，确保默认加载"任务"标签页

### 2024-12-34
- 将默认导航视图改为表格视图
  - 将index.html改名为deviceList.html
  - 修改路由配置，使任务表格成为默认主页
  - 添加/device路由用于访问设备列表视图
  - 调整导航链接，确保可以在视图间正确切换
  - 优化导航结构和用户体验

### 2024-12-33
- 新增表格视图功能，支持任务和设备数据表格化展示
  - 集成Tabulator表格库，实现高级表格功能
  - 添加新的表格视图界面，与设备视图并存
  - 实现任务表和设备表两种表格展示
  - 每个字段支持排序和过滤功能
  - 生命列支持直接编辑
  - 进度列以进度条方式显示
  - 右键菜单支持任务执行、暂停、取消操作
  - 设备和任务表格数据实时同步更新
  - 优化表格UI，提供更直观的数据展示

### 2024-12-32
- 后台日志输出到数据库功能
  - 创建新的LogModel数据库模型，用于存储后台日志
  - 保留前台日志输出到JSON文件的功能不变
  - 修改_Log.py中的Blog方法，支持将日志同时保存到数据库
  - 添加_save_log_to_db和_update_log_in_db方法，实现日志数据库操作
  - 优化日志重复判断逻辑，在数据库中也保持日志计数功能
  - 增强了日志系统与平台日志显示的兼容性
  - 通过数据库存储，提高了日志的查询性能和稳定性

### 2024-12-31
- 优化任务管理机制，修复任务暂停和恢复问题
  - 修改CTask_类的begin方法，确保在恢复任务时重置_lastTime并调用_goPage
  - 优化_refreshProgress方法，支持任务暂停后再次开始时累计计算进度
  - 在时间模式下，使用当前会话运行时间累加到总进度中
  - 在次数模式下，利用_execCount的累加特性计算进度
  - 增强了stop方法的注释，明确说明暂停任务的功能和返回值
  - 提高了任务暂停和恢复功能的可靠性和准确性

- 统一客户端和服务端任务状态管理
  - 将TaskState枚举类移至_G.py中作为共享枚举
  - 修改CTask_类和STask_类，统一使用_G中的TaskState枚举
  - 将toTaskId方法从_Tools移至_G中，保证任务ID一致性
  - 修改_end方法，根据任务返回结果决定是设置SUCCESS还是FAILED状态
  - 提高了客户端和服务端任务状态的一致性
  - 简化了代码维护，减少了状态不一致的潜在问题

- 简化CTask_类的begin方法
  - 移除lifeExtRatio参数，不再支持任务生命周期延长功能
  - 优化方法结构，只保留继续任务和正常开始两种逻辑
  - 添加任务继续运行的日志提示
  - 提高了代码可读性和维护性

### 2024-12-30
- 优化任务执行机制，修复重复执行BUG
  - 在_Page_类中添加onExit事件回调支持
  - 添加_pageExitEvt标志，通过页面退出事件控制任务执行
  - 在页面退出时触发onExit回调，更新_pageExitEvt状态
  - 任务只有在页面完全退出后才会执行下一次
  - 解决了页面切换过程中可能出现的任务重复执行问题
  - 提供了基于事件的任务执行控制机制，更加可靠和清晰

### 2024-12-36
- 实现前端RPC功能，支持前端直接调用服务端RPC方法
  - 创建前端RPC.js模块，基于Socket.IO实现RPC通信
  - 支持前端调用服务端RPC方法：`rpc.server(className, methodName, instanceId, ...args)`
  - 支持前端调用客户端RPC方法：`rpc.client(deviceId, className, methodName, instanceId, ...args)`
  - 在BCmds.js中添加RPC相关命令：
    - `rpc` - 通用RPC调用命令
    - `设备信息` - 获取设备信息
    - `应用列表` - 获取应用列表
    - `任务列表` - 获取任务列表
  - 提供全局快捷方法window.rpc，简化RPC调用
  - 创建RPCExamples.js示例文档，提供各种RPC使用示例
  - 支持Promise/async-await语法，提供完善的错误处理
  - 支持超时控制和批量操作
  - 在sheet.html中引入RPC.js，确保前端页面可以使用RPC功能
  - 实现了前端与服务端的无缝RPC通信，大大简化了前端与后端的交互

- 增强任务生命周期管理功能
  - 在begin方法中添加lifeExtendRatio参数，默认值为1
  - 支持在任务开始时动态延长任务生命周期
  - 生命周期延长比例适用于时间模式(正数)和次数模式(负数)
  - 保持原有符号，只增加绝对值大小
  - 添加日志记录，跟踪任务生命周期的变化


### 2024-12-26
- 优化计数器功能设计，改为实例级别管理
  - 将计数器从类级别静态字典改为每个应用实例的成员变量
  - 在App实例初始化时创建独立的_counters字典
  - 修改count和_increaseCount类方法，使其通过当前应用实例访问计数器
  - 直接在_setCurrentPage方法中操作实例级别的计数器
  - 在_doEvent方法中使用应用实例的计数器记录事件触发
  - 每个应用实例现在拥有独立的计数统计，互不干扰
  - 通过App.count(name)方法仍可方便地获取当前应用的计数值

### 2024-12-25
- 新增计数器功能，统计页面访问和事件触发次数
  - 在_App_类中添加_counters静态字典，用于存储各类计数
  - 实现count方法，用于获取指定名称的计数值
  - 添加_increaseCount内部方法，用于增加计数
  - 在_setCurrentPage方法中增加对页面访问次数的统计
  - 在_doEvent方法中增加对事件触发次数的统计
  - 页面计数使用"page_页面名"作为键名
  - 事件计数使用"event_事件名"作为键名
  - 通过App.count(name)方法可以获取任意名称的计数值

### 2024-12-21
- 增强屏幕信息命令的功能
  - 支持设置负数超时值，实现文本被查找到N次后自动清除的功能
  - 屏幕信息命令格式: `屏幕信息 文本内容 -N`，表示文本在被查找到N次后自动清除
  - 提升了屏幕模拟的智能性和易用性
  - 无需手动清理屏幕元素，系统会在达到指定查找次数后自动处理
  - 适用于需要精确控制屏幕元素生命周期的场景

### 2024-08-22
- 完善页面检测机制，增加页面类型区分
  - 新增ePageType枚举类，支持normal(正常页面)、alert(弹窗)和temp(临时页面)三种类型
  - 修改_Page_类的type属性，使用新的枚举类型替代原有字符串类型
  - 改进detectPage方法的检测逻辑，优先检测当前应用中的alert类型页面
  - 不再检测exitPages列表和其他应用的页面，保持导航逻辑的独立性
  - 明确了exit仅用于定义页面间跳转关系，不用于页面检测
  - 增加类型安全检查，确保页面类型设置正确
  - 提升了异常情况下的页面识别能力，特别是对弹窗的处理

### 2024-08-21
- 合并CJob_功能到CTask_类
  - 移除了独立的CJob_类，将其功能直接集成到CTask_类中
  - 添加了任务执行相关的属性：_pageName、_life、_interval、_isRunning、_lastExecTime
  - 增加了isExpired属性和_doWork方法，直接在CTask_中实现任务执行逻辑
  - 优化了begin方法，直接解析参数并执行页面跳转
  - 重构了update方法，实现了定时执行任务的功能
  - 重写了stop和complete方法，增加对任务结束脚本的处理
  - 添加了addScore方法，支持直接增加任务分数
  - 简化了整体代码结构，减少了不必要的对象创建和管理

### 2024-08-20
- 优化任务配置结构
  - 将任务配置改为字典格式，提高可读性和可维护性
  - _begin字段现在是字典格式，直接包含pageName、life、interval参数
  - 简化了_parseBeginScript方法，直接从字典中获取参数
  - 提供了标准化的task.json格式示例
  - 移除了复杂的正则表达式解析逻辑
  - 将配置文件task.json移至config目录下
  - 添加_getConfigPath方法，统一管理配置路径

### 2024-08-19
- 新增CJob_类用于任务的具体执行
  - 将任务执行逻辑独立为单独的类，提高代码复用性和可维护性
  - 支持配置任务目标页面、生命周期、执行间隔和结束脚本
  - 实现任务自动跳转到目标页面、定期执行和自动结束功能
  - 优化了CTask_类，通过解析begin脚本创建对应的CJob实例
  - 任务的begin, update和end工作现在由CJob_类负责处理
  - 添加了Create静态方法，方便创建CJob实例
  - 支持自动更新任务进度和分数，与服务端保持同步

### 2024-08-18
- 新增CTask_类用于客户端任务管理
  - 任务属性包含名称、所属APP、时间、进度、分数等
  - 支持任务配置从task.json加载和保存
  - 实现任务生命周期管理：开始、停止、更新、完成
  - 支持任务脚本执行，通过begin和exit属性配置
  - 任务状态与服务端同步，通过APP通信接口发送
  - 在_App_类中添加了任务管理接口：启动、获取、当前任务
  - APP定期在_update中调用当前任务的update方法

### 2023-10-13
- 新增Page类click方法，用于PC平台模拟Android端点击效果
  - 调用tools.click的同时，在PC平台额外执行指定操作
  - 支持三种操作格式：
    - < : 页面跳转到上一页
    - >pageName: 跳转到pageName指定的页面
    - +d: 收获d金币，如果d不是数字，则收获this.d金币
  - 提高了PC平台测试的真实性和便捷性
  - 简化了跨平台开发和调试流程

### 2023-10-12
- 增强页面timeout属性的功能
  - timeout配置值不再只是数字，而是支持字符串格式："等待时间长度&执行的操作"
  - 新增页面的_timeout和_timeoutOp属性，分别存储超时时间和超时操作
  - 在timeout的getter中实现lazy初始化，自动解析timeout字符串
  - 将timeout处理从App._update移动到Page.update中
  - 超时时执行指定的操作，如果没有指定操作则执行退出逻辑
  - 提高了页面超时处理的灵活性和可控性

### 2023-10-11
- 优化页面引用机制和安全性
  - 将exitPages改为私有变量_exitPages，通过属性访问器提供安全访问
  - 完善getInst方法实现，支持正确创建页面实例和配置复制
  - 优化参数处理，区分配置项和数据项
  - 简化App.getPage中的公共页面处理逻辑，直接返回公共页面
  - 修复了引用页面不存在时的错误日志类型

### 2023-10-10
- 优化页面配置和检测机制
  - 移除commonPages配置，改为使用更灵活的页面引用机制
  - 新增页面引用功能，支持在exit配置中使用#开头的引用页面
  - 引用格式：#引用页面名{参数JSON}，参数部分可选
  - 添加_Page_类的exitPages属性，存储当前页面可跳转的目标页面
  - 优化detectPage方法，只检测当前页面的exitPages中的页面，提高性能
  - 页面引用支持参数传递，可以根据不同场景定制页面行为
  - 引用页面只在公共页面中查找，确保引用的一致性

### 2023-10-09
- 增加应用公共页面配置功能
  - 在root配置中添加commonPages配置项，用于定义要加入到应用的公共页面
  - 修改_loadConfig方法，支持自动加载commonPages中定义的公共页面
  - 利用现有getPage方法的includeCommon参数加载公共页面
  - 公共页面会从TOP应用中复制并添加到当前应用
  - 提高了页面复用性，减少重复配置工作

### 2023-10-08
- 优化_doEvent方法实现
  - 移除了不再需要的子页面事件（P-页面名格式）处理逻辑
  - 简化了用户事件检查，确保app.userEvents始终存在
  - 重构了条件检查流程，提高了代码可读性
  - 统一了execute变量的初始化和设置逻辑
  - 为延时和无条件执行添加了明确的execute=True设置

### 2023-10-07
- 进一步优化用户事件处理机制
  - 将用户事件逻辑移入_doEvent方法，统一事件处理流程
  - 简化Page.update方法，不再单独检查用户事件
  - 减少了代码冗余，提高了事件处理效率
  - 优化了_doEvent方法的流程，使其处理逻辑更清晰

### 2023-10-06
- 优化了事件处理和用户事件机制
  - 重构了事件处理流程，移除了重复的检查逻辑
  - 将userEvents从页面属性改为应用实例变量，使其成为字符串列表
  - 添加了App.addUserEvent和App.clearUserEvents方法，用于管理用户事件
  - 在App._update中添加自动清空用户事件的逻辑，防止事件被重复触发
  - 简化了Page.update方法，直接调用_doEvent处理事件逻辑
  - 提高了用户事件处理的效率和可靠性
  - 减少了冗余代码，提升了代码可维护性

### 2023-09-02
- 重构了页面自动执行逻辑设计和优化
  - 添加了App._update方法检测当前页面并调用页面更新函数
  - 添加了全局App.update循环方法实现自动检测应用和页面
  - 实现了Page.update方法处理事件检测、页面跳转和用户事件
  - 将页面跳转处理从Page.update移至App._update
  - 改进了App.goPage方法，使其只设置目标页面
  - 实现了路径跳转，每次更新循环只跳转一步
  - 简化了路径缓存，直接存储当前目标路径
  - 优化了路径判断逻辑，检测当前页面是否在预定路径中
  - 在事件匹配过程中同步检查用户事件
  - 用户事件可以直接触发匹配的KEY事件
  - 移除了子页面(children)相关的代码
  - 删除了_startChild和_stopAllChildren方法

### 2023-09-01
- 优化了页面更新机制
  - 移除了Page.update中的循环逻辑，简化为单次执行
  - 适应App驱动的更新模式，提高执行效率
  - 修复了超时计算逻辑，使用页面创建时间而非更新开始时间
  - 简化了代码结构，提高了可维护性
  - 减少了内存和CPU资源消耗

### 2023-08-30
- 改进了用户事件处理逻辑
  - 在事件匹配过程中同步检查用户事件，提高响应效率
  - 用户事件现在可以直接触发匹配的KEY事件，无需额外处理
  - 精简了事件处理代码，减少冗余检查
  - 更明确的事件处理日志，便于调试
  - 提高了用户交互反馈的及时性和准确性

### 2023-08-25
- 进一步简化页面跳转逻辑
  - 将路径缓存从键值对改为直接存储当前目标路径
  - 移除不必要的缓存查找和路径重计算
  - 优化了路径判断逻辑，清晰检测当前页面是否在预定路径中
  - 减少了冗余代码，提高了执行效率
  - 更明确的错误处理，当页面不在路径上时直接报错

### 2023-08-20
- 优化了页面跳转性能
  - 添加路径缓存机制，避免重复计算页面间路径
  - 简化了goPage函数逻辑，专注于设置目标页面和路径缓存
  - 在App._update中利用缓存路径进行页面跳转
  - 增加缓存失效处理，当路径跳转失败时自动清除缓存
  - 大幅提高了复杂页面导航的性能和响应速度

### 2023-08-15
- 优化了页面跳转逻辑
  - 将页面跳转处理从Page.update移至App._update
  - 改进了App.goPage方法，使其只设置目标页面而不直接执行跳转
  - 在App._update中实现路径跳转，每次更新循环只跳转一步
  - 增强了页面间跳转的稳定性和效率，支持复杂路径自动导航
  - 优化了错误处理和日志记录，更易于调试和监控

### 2023-08-10
- 新增页面自动执行循环逻辑
  - 添加应用级_update方法，负责检测当前页面并调用页面更新函数
  - 新增全局update循环方法，实现自动检测当前应用和页面
  - 添加页面update方法，实现三大功能：
    - 检测事件是否满足条件KEY，使用tools.check检查并执行ACTION
    - 通过应用的_targetPage属性处理页面跳转逻辑
    - 检测用户事件，通过event.items()处理用户交互
  - 修改App.goPage方法，使用_targetPage属性设置跳转目标
  - 提高了应用自动化执行的灵活性和稳定性

### 2023-07-26
- 增强matchText函数功能
  - 支持&（与）和|（或）逻辑操作符，实现复杂条件匹配
  - 添加空括号()继承功能，可以继承前一个条件的区域范围
  - 示例："推荐(x300,500)&新剧()&VIP抢先|排行榜"
  - 完善逻辑表达式解析和评估算法
  - 提高了屏幕元素检测的灵活性和精确性

### 2023-07-25
- 增加了Page页面的父子关系支持
  - 添加了parent成员变量，用于存储父页面引用
  - 添加了setParent方法，用于设置父子页面关系并自动建立父页面退出到子页面的链接
  - 修改了getInst方法，支持在创建页面时设置父页面
  - 修改了_begin方法，在执行页面前确保与父页面的关系已正确设置

### 2023-12-10
- 改进了CRun模块的页面重入判断逻辑
- 现在批处理任务会根据页面的运行状态来判断是否可以重新进入，而不是简单地比较当前页面是否为目标页面
- 在Page类中添加了_running状态标志，用于跟踪页面是否正在运行
- 页面的begin方法会将_running设为True，end方法和_end方法会在页面结束时将_running设为False

### 2024-11-29
- 修复正则表达式匹配方法中的参数错误
  - 移除`fullmatch`方法中不正确的`re.IGNORECASE`参数
  - 将忽略大小写标志移至`re.compile`阶段
  - 解决了导致命令无法匹配的关键问题
  - 正确处理了正则表达式的编译和匹配过程

### 2024-11-30
- 优化命令匹配逻辑，简化代码结构
  - 移除了不必要的正则表达式匹配备用路径
  - 统一使用预编译的正则表达式进行命令匹配
  - 减少了条件判断，提高了执行效率
  - 简化了错误处理流程

### 2024-11-30
- 修复命令参数间空格处理问题
  - 使用已有的专用方法`processParamSpaces`处理参数间空格
  - 解决了类似`current page aa`这样多参数命令无法匹配的问题
  - 统一了参数空格处理逻辑，提高了代码复用性
  - 确保命令模式中参数之间都有`\s*`匹配空白字符

### 2024-12-01
- 修复命令参数空格处理方法
  - 修正`processParamSpaces`方法，确保保留原始参数匹配模式
  - 采用迭代方式处理参数间空格，避免修改参数本身
  - 只在纯空白的参数间距添加`\s*`匹配，保留其他内容
  - 提高了处理的准确性，不再修改参数的实际匹配字符
  - 增加了对参数数量的检查，优化处理流程

### 2023-11-21
- 扩展了宏变量替换功能，增加宏命令支持
  - 添加了宏命令映射表(MACRO_MAP)，支持常用命令的简化表示
  - 宏命令支持正则表达式捕获组，可以提取参数
  - 支持的宏命令包括：
    - `>pageName`: 跳转到指定页面，等同于`app.gotoPage(pageName)`
    - `<<`: 返回主页，等同于`app.home()`
    - `<`: 返回上一页，等同于`app.last().back()`
    - `->text pageName`: 点击文本并跳转，等同于`it.click('text','@app.gotoPage(pageName)')`
  - 优化了宏替换逻辑，先进行符号替换，将全角符号转为半角
  - 宏命令使用全匹配模式，忽略大小写

### 2023-11-20
- 添加了宏变量支持，使用格式 `%变量名` 可在文本匹配和脚本中引用变量值
- 简化了命令处理逻辑，移除了`:开头`的特殊命令支持
- 优化了代码结构，提高了可维护性

### 2024-03-21
- 优化toast配置功能
  - 将toast配置名称改为toasts，更符合复数形式规范
  - 将toast检查逻辑从_update方法移至detectPage方法中
  - 在检测alert类型页面后立即检查toast配置
  - 删除了_Page_类中不再使用的schedule相关代码
  - 简化了配置结构，提高了代码可维护性
  - 优化了toast检测的时机，使其与页面检测逻辑更加协调

### 功能更新日志

## 2024-03-21
1. 任务系统改造
   - 将expectedScore字段改为life字段，用于表示任务的预期生命
   - life字段含义：
     - 负数：表示任务可执行次数
     - 正数：表示任务可执行时间长度（秒）
     - 0：表示无生命约束，任务可以一直执行
   - 移除appName字段，将应用名称整合到taskName中
   - 优化任务显示格式，简化任务ID显示

### 修复
- 修复了多线程环境下日志保存时的数据库会话冲突问题
  - 在保存日志到数据库时，创建新的日志对象而不是重用现有对象
  - 避免了同一个对象被多个会话同时使用的问题

### 之前的更新
<!-- 此处保留之前的更新记录 -->

### 2024-05-30
- 重构日志系统，解决循环引用问题
  - 将LogModel_类从SModels模块移至_Log_模块内部
  - 优化日志ID计算算法，现在基于tag+level+time+message计算哈希值
  - 改进日志查找机制，采用线性搜索查找匹配ID的日志
  - 修复了缓存数据查找和更新相关的bug
  - 完善了数据库存储检查机制，避免重复插入
  - 重新启用日志过滤和日期获取功能
  - 增强Socket通信的健壮性，添加更多空值检查
  - 优化了日志数据结构和格式化方法

### 2024-05-27
- 优化服务器日志系统
  - 改进日志缓存机制，缓存数据改为LogModel数组而非字典
  - 实现按需保存到数据库的功能，只有显式调用save方法时才同步到数据库
  - 新增日志ID计算算法，ID基于tag+level+message的哈希值
  - 添加_cacheModified标志，跟踪日志缓存是否被修改
  - 优化日志加载和过滤方法，直接操作LogModel对象
  - 增强前端通信安全性，添加各种防御性检查
  - 简化了日志重复性检测逻辑，使用哈希ID快速判断
  - 添加日志备份功能，在保存到数据库的同时备份到JSON文件

### 2024-05-25
- 统一使用S2B_sheetUpdate事件机制
- 确保所有设备/任务/日志相关的增删改操作都触发S2B_sheetUpdate事件，实现前端数据实时更新

### 2024-05-18
- 完善了表格数据处理功能
- 添加了设备、任务和日志的表格数据加载API

### 2024-12-20
- 添加了设备实时状态监控
- 优化了任务调度算法

### 2024-12-15
- 完善了任务管理系统
- 添加了日志记录功能

### 2024-12-10
- 初始化项目基础架构
- 添加了基本的设备管理功能
- 实现了Socket.IO通信框架

### 2023-07-15
- 修复了一些已知问题
- 添加了新的API支持

### 2023-07-30
- 新增自动连接功能
- 优化了日志显示

### 2023-11-15
- 修复系统兼容性问题
- 优化操作界面

### 2023-12-25
- 修复网络连接稳定性问题
- 增强安全性

### 2024-07-15
- 修复表格初始化问题：解决在表格完全构建前调用getHeaderFilters方法导致的错误
- 优化表格数据加载流程，确保在表格初始化完成后再加载数据
- 改进过滤器处理逻辑，增强表格组件的稳定性

## 2023-11-15 更新日志

### 服务端任务管理优化
1. 重构了STask_类，添加了任务缓存功能，不再依赖STaskMgr
2. 添加了任务缓存列表和缓存管理机制，控制服务器内存压力
3. 实现了get()方法，支持按设备ID、任务名称和日期获取任务，支持自动创建
4. 实现了gets()方法，支持按设备ID和日期批量获取任务
5. 添加了handleB2SLoadTasks()事件处理，返回缓存中的任务数据

## 2023-11-16 更新日志

### 任务缓存机制优化
1. 重构了STask_.gets()方法，移除了deviceId参数，以日期为单位缓存任务
2. 添加了最近一次缓存日期的记录功能，避免重复查询数据库
3. 优化了缓存逻辑，相同日期直接返回缓存，不同日期清除缓存并重新加载
4. 改进了handleB2SLoadTasks方法，支持在内存中按设备ID筛选任务
5. 提高了系统性能，减少了数据库查询次数

## 2023-07-14
- 初始版本
- 支持基础自动化操作

## 2023-08-21
- 增加支持多任务并行执行
- 优化日志处理

## 2023-09-30
- 增加图像识别功能
- 支持自定义脚本运行

## 2023-11-18
- 优化UI界面
- 增加任务监控功能

## 2024-03-05
- 修复脚本运行Bug
- 增强设备管理功能

## 2024-06-11
- 集成命令输入区域到表格页面(sheet.html)
- 保留了命令历史和上下键命令导航功能
- 从任务表格中移除了备注列

## 2024-06-12
- 优化sheet.html页面的代码结构
- 移除对logManager.js的依赖，使用sheet.js自身的命令历史功能
- 减少文件依赖，简化代码结构

## 2024-06-13
- 优化表格分页功能
- 日志表格自动滚动到最后一页，除非用户手动翻页
- 所有表格在只有一页数据时自动隐藏分页按钮
- 添加用户翻页状态跟踪，优化用户体验

## 2024-06-14
- 增加表格多选功能和命令目标管理
- 所有表格支持多选，并在切换表格时保持选择状态
- 设备表格中选中的设备作为命令的目标设备
- 如果没有选中设备，自动使用最后一次连接的设备
- 增加设备状态更新监听，实时追踪最新连接的设备

### 2023-07-05
- 初始化项目结构
- 添加基本设备管理功能

### 2023-07-17
- 优化数据库连接管理
- 添加设备分组功能

### 2024-07-04
- 合并DeviceModel和SDevice_类，将所有设备管理功能整合到一个类中
- 优化了数据库模型，减少了冗余代码
- 简化了属性访问，提高了代码可维护性

### 2024-06-09
- 新增任务配置读取基类TaskBase，统一管理任务配置。
- STask和CTask均继承TaskBase，任务配置读取逻辑统一。
- 设备登录时，若当天任务列表为空，自动根据配置生成当天任务并保存到数据库。
- onB2S_loadDatas获取任务时，遍历所有设备，获取每台设备当天任务，在线设备优先。

### 2024-03-21
- 优化表格过滤功能：
  - 将日期过滤器改为服务端过滤，其他过滤器保持本地过滤
  - 只有日期过滤器变化时才会向服务端请求新数据
  - 启用本地实时过滤，提高其他过滤器的响应速度
  - 减少了服务器负载，优化了数据传输量

### 优化表格数据加载机制
- 修改了表格数据加载的触发方式，从dataFiltered事件改为headerFilterChanged事件
- 移除了isLoading状态检查机制，改用事件驱动方式
- 优化了数据加载逻辑，避免循环加载问题
- 添加了错误处理机制

### 2024-03-21
### 设备ID更新机制优化
1. 将B2_updateDevice改为B2S_updateDevice，只发送给服务器
2. 新增S2C_updateDevice事件，用于服务器通知客户端更新设备ID
3. 在SDevice_类中添加set方法统一处理设备属性更新
4. 优化了CDevice_类中的事件监听注册逻辑

### 设备表格功能增强
1. 增加设备分组和设备名称的单元格编辑功能
   - 分组列支持下拉选择和手动输入
   - 设备名称列支持直接编辑
2. 分组列的过滤器支持从现有分组中选择或手动输入
3. 设备ID（GROUP:NAME）自动同步更新
   - 服务端和客户端同步更新设备ID
   - 实时通知所有连接的客户端

### 2024-07-12
# 前台表格功能增强
- 任务表格和设备表格均增加了"ID"只读列，方便查看唯一标识。
- 任务表格和设备表格均增加了"目标"checkbox列，可直接勾选/取消，表示当前是否为target，支持直接编辑，状态与目标列表同步。

## 2024-07-09
- # 任务(TaskModel/相关逻辑)的 deviceId 字段由设备名称改为设备ID（DeviceModel.id），所有相关操作、查询、缓存、命令等全部用设备ID，保证设备重命名后任务数据不丢失。

### 2024-08-09
- CDevice_ 现在也维护自己的 state（offline/online/login/logout），与 SDevice_ 机制一致
  - 避免了重复连接，只有在状态为 offline/logout 时才会发起连接
  - 断连、登录、登出时，state 会同步变更，消息发送逻辑与状态保持一致
  - 新增 CDevice_.state() 方法可获取当前状态

### 2024-06-02
- 修复日志表格和设备视图日志面板日期过滤器默认值问题
  - 每次页面加载或表格初始化时，都会强制将日期过滤器重置为当天，避免出现默认值为昨天的情况。

### 2024-06-03
- 客户端和服务端所有设备连接状态相关逻辑，全部统一为 _G.py 里的 ConnectState 枚举，避免魔法字符串，提升代码规范性和可维护性。

## 2024-06-09
1. 服务端断开无心跳客户端时，自动通知前端刷新设备表。
2. 前端任务表格去掉分组列。

## 2024-06-15
1. 前端设备表格数据缓存到SheetPage.deviceCache，并提供get(id)方法。
2. 任务表格设备ID列根据设备状态显示不同颜色。

## 2024-06-16
1. 客户端CDevice_类实现了onLogin方法，支持用服务端返回的taskList初始化本地任务表。
2. 客户端任务管理接口(getTaskByID、getTasks)迁移到CDevice_，统一管理。

## 2024-03-21
### 连接稳定性优化
- 开启Socket.IO客户端自动重连机制
  - 设置最大重连尝试次数为5次
  - 重连延迟时间为1秒
  - 心跳超时时间设置为10秒
- 增加详细的连接状态日志，便于问题追踪

### 命令匹配逻辑优化
- 全面重构命令注册的正则表达式生成策略
  - 采用嵌套可选结构：`命令名(?:\s+参数1(?:\s+参数2)?)?`
  - 支持无参数、单参数、多参数的灵活匹配
  - 命令名与参数间支持多个空格（`\s+`）
  - 整个参数部分可选，完美支持纯命令调用
  - 添加命令开始`^`和结束`\s*$`锚点（支持末尾空格容错）
- 修复了`getScores 快手极速版`类型命令匹配失败的问题
- 大幅提升了命令解析的准确性和用户友好性



**注意**：这是一个基于 Mem0 的自定义 MCP 服务器实现，提供了完整的记忆管理功能，完全免费使用！
