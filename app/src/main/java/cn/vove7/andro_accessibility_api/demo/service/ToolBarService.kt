package cn.vove7.andro_accessibility_api.demo.service

import android.annotation.SuppressLint
import android.content.Context
import android.content.SharedPreferences
import android.graphics.Color
import android.graphics.PixelFormat
import android.os.Build
import android.os.Handler
import android.os.Looper
import android.text.Editable
import android.text.Spannable
import android.text.SpannableString
import android.text.style.ForegroundColorSpan
import android.text.method.ScrollingMovementMethod
import android.util.DisplayMetrics
import android.util.Log
import android.view.GestureDetector
import android.view.GestureDetector.SimpleOnGestureListener
import android.view.Gravity
import android.view.KeyEvent
import android.view.LayoutInflater
import android.view.MotionEvent
import android.view.View
import android.view.WindowManager
import android.view.inputmethod.EditorInfo
import android.view.inputmethod.InputMethodManager
import android.widget.AdapterView
import android.widget.ArrayAdapter
import android.widget.Button
import android.widget.EditText
import android.widget.FrameLayout
import android.widget.ImageButton
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.Spinner
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AlertDialog
import androidx.lifecycle.LifecycleService
import cn.vove7.andro_accessibility_api.demo.MainActivity
import cn.vove7.andro_accessibility_api.demo.R
import cn.vove7.andro_accessibility_api.demo.databinding.DSettingBinding
import cn.vove7.andro_accessibility_api.demo.script.PythonServices
import cn.vove7.andro_accessibility_api.demo.script.ScriptEngine
import cn.vove7.andro_accessibility_api.demo.view.CursorView
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import timber.log.Timber
import java.lang.ref.WeakReference
import java.text.SimpleDateFormat
import java.util.ArrayList
import java.util.Date
import java.util.Locale
import java.util.concurrent.Executors

/**
 * @功能:应用外打开Service 有局限性 特殊界面无法显示
 * @User Lmy
 * @Creat 4/15/21 5:28 PM
 * @Compony 永远相信美好的事情即将发生
 */
class ToolBarService : LifecycleService() {
    companion object {
        const val PREFS_NAME = "DevicePrefs"
        const val SERVER_NAME_KEY = "serverName"
        const val DEVICE_NAME_KEY = "deviceName"
        private var instance: WeakReference<ToolBarService>? = null
        
        // 添加日志视图的缓存
    
        
        // 静态 scriptEngine，使用 lazy 初始化
        private val _scriptEngine: ScriptEngine by lazy {
            val service = getInstance()?.get()
            if (service != null) {
                ScriptEngine.getInstance(service)
            } else {
                throw IllegalStateException("ToolBarService实例未初始化")
            }
        }
        
        @JvmStatic
        fun getScriptEngine(): ScriptEngine {
            return _scriptEngine
        }
        
        @JvmStatic
        fun getInstance(): WeakReference<ToolBarService>? {
            return instance
        }




        /**
         * 添加日志，与脚本层的_clientLog函数参数保持一致
         * 作为类方法，可以在没有实例的情况下调用
         * @param tag 日志标签
         * @param level 日志级别 (i, d, e, w)
         * @param content 日志内容
         * @param result 可选的结果信息
         */
        @JvmStatic
        fun log(content: String, tag: String = "", level: String = "i") {
            try {
                if(content.isEmpty())
                    return
                // 统一调用Python脚本层的log函数
                try {
                    getScriptEngine().callPythonFunction("_G._G_.Log().log", content, tag, level)
                } catch (e: Exception) {
                    // 如果调用Python失败，记录到系统日志
                    val logTag = "ToolBarService"
                    val logMessage = "[$tag][$level] $content (Python调用失败: ${e.message})"
                    when (level.lowercase()) {
                        "e", "error" -> Log.e(logTag, logMessage)
                        "w", "warn" -> Log.w(logTag, logMessage)
                        "d", "debug" -> Log.d(logTag, logMessage)
                        "c", "cmd" -> Log.i(logTag, logMessage)
                        else -> Log.i(logTag, logMessage)
                    }
                }
            } catch (e: Exception) {
                Timber.e(e, "记录日志失败")
            }
        }

        @JvmStatic
        fun logE(content: String, tag: String = "") {
            log(content, tag, "e")
        }
        @JvmStatic
        fun logW(content: String, tag: String = "") {
            log(content, tag, "w")
        }
        @JvmStatic
        fun logD(content: String, tag: String = "") {
            log(content, tag, "d")
        }
        @JvmStatic
        fun logI(content: String, tag: String = "") {
            log(content, tag, "i")
        }

        @JvmStatic
        fun logC(content: String, tag: String = "") {
            log(content, tag, "c")
        }
        @JvmStatic
        fun logEx(e: Exception, content: String = "", tag: String = "") {
            val msg = "${content}\n${e.message}\n${e.stackTrace.joinToString("\n")}"
            log(msg, tag, "e")
        }
    }
    

    private lateinit var windowManager: WindowManager
    private var toolbarView: View? = null // 悬浮窗View
    private lateinit var prefs: SharedPreferences
    private var cursorView: CursorView? = null
    
    private var _serverIP: String? = null
    var serverIP: String
        get() {
            if (_serverIP == null) {
                _serverIP = getPrefs().getString(SERVER_NAME_KEY, "192.168.0.103")
            }
            return _serverIP!!
        }
        set(value) {
            if(value != _serverIP){
                _serverIP = value
                getPrefs().edit().putString(SERVER_NAME_KEY, value).apply()                
            }
        }

    private var _deviceName: String? = null
    var deviceName: String
        get() {
            if (_deviceName == null) {
                _deviceName = getPrefs().getString(DEVICE_NAME_KEY, "") ?: ""
            }
            // 如果设备名称为空，使用默认设备名称
            if (_deviceName!!.isEmpty()) {
                _deviceName = getDefaultDeviceName()
                // 保存默认设备名称
                getPrefs().edit().putString(DEVICE_NAME_KEY, _deviceName).apply()
            }
            return _deviceName!!
        }
        set(value) {
            if(value != _deviceName){
                _deviceName = value
                getPrefs().edit().putString(DEVICE_NAME_KEY, value).apply()
            }
        }

    /**
     * 获取设备的默认名称
     * 获取手机的真实设备名称，如果获取不到则使用设备型号
     */
    fun getDefaultDeviceName(): String {
        return try {
            val appContext = applicationContext
            var deviceName: String? = null
            
            // 方法1: 尝试获取系统设置的设备名称 (Android 7.1+)
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N_MR1) {
                try {
                    deviceName = android.provider.Settings.Global.getString(
                        appContext.contentResolver,
                        "device_name"
                    )
                    if (!deviceName.isNullOrEmpty()) {
                        logI("通过Settings.Global获取设备名称: $deviceName")
                        return deviceName
                    }
                } catch (e: Exception) {
                    logW("无法通过Settings.Global获取设备名称: ${e.message}")
                }
            }
            
            // 方法2: 尝试获取蓝牙设备名称
            try {
                deviceName = android.provider.Settings.Secure.getString(
                    appContext.contentResolver,
                    "bluetooth_name"
                )
                if (!deviceName.isNullOrEmpty()) {
                    logI("通过蓝牙名称获取设备名称: $deviceName")
                    return deviceName
                }
            } catch (e: Exception) {
                logW("无法通过蓝牙名称获取设备名称: ${e.message}")
            }
            
            // 方法3: 尝试通过BluetoothAdapter获取设备名称
            try {
                val bluetoothAdapter = android.bluetooth.BluetoothAdapter.getDefaultAdapter()
                if (bluetoothAdapter != null) {
                    deviceName = bluetoothAdapter.name
                    if (!deviceName.isNullOrEmpty()) {
                        logI("通过BluetoothAdapter获取设备名称: $deviceName")
                        return deviceName
                    }
                }
            } catch (e: Exception) {
                logW("无法通过BluetoothAdapter获取设备名称: ${e.message}")
            }
            
            // 方法4: 回退到设备型号 + Android ID
            val model = Build.MODEL ?: "Unknown"
            val androidId = android.provider.Settings.Secure.getString(
                appContext.contentResolver,
                android.provider.Settings.Secure.ANDROID_ID
            ) ?: "000000"
            
            // 取Android ID的前6位作为设备标识
            val deviceId = androidId.take(6)
            val defaultName = "${model}_$deviceId"
            
            logI("使用设备型号生成默认名称: $defaultName")
            defaultName
        } catch (e: Exception) {
            logEx(e, "生成默认设备名称失败")
            "Device_${System.currentTimeMillis().toString().takeLast(6)}"
        }
    }

    private fun getPrefs(): SharedPreferences {
        if (!::prefs.isInitialized) {
            prefs = getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        }
        return prefs
    }

    private val executor = Executors.newSingleThreadExecutor()

    private lateinit var gestureDetector: GestureDetector
    private var touchMonitorView: View? = null

    // 添加自定义悬浮窗相关变量
    private var positionToastView: View? = null
    private var positionToastHideRunnable: Runnable? = null
    private var lastPositionToastUpdateTime = 0L
    private val POSITION_TOAST_AUTO_HIDE_DELAY = 5000L // 5秒后自动隐藏

    // 在类定义中添加新的变量
    private var lastTapTime = 0L
    private val DOUBLE_TAP_TIMEOUT = 300L // 双击超时时间（毫秒）
    private var mainWindowVisible = false

    private val commandHistory = ArrayList<String>()
    private var historyIndex = -1
    private var isExpanded = false
    private var toolbarExpanded = true

    // 添加触摸监控视图相关变量
    private var touchView: View? = null
    private var touchViewVisible = false

    // 在类定义中添加新变量
    private var floatButtonView: View? = null
    
    // 添加长按检测相关变量
    private var longPressRunnable: Runnable? = null
    private var isLongPressed = false
    private val LONG_PRESS_TIMEOUT = 500L // 长按超时时间（毫秒）

    // 添加命令历史持久化功能
    private val COMMAND_HISTORY_KEY = "command_history"
    private val MAX_HISTORY_SIZE = 100

    // 添加成员变量，用于保存悬浮按钮的原始位置
    private var originalButtonX = 100
    private var originalButtonY = 200
    private var buttonParams: WindowManager.LayoutParams? = null

    // 在类的成员变量部分添加这些变量
    private var currentInput = ""  // 保存当前输入，用于从历史返回
    

    override fun onCreate() {
        super.onCreate()
        instance = WeakReference(this)
        windowManager = getSystemService(WINDOW_SERVICE) as WindowManager
        
        // 确保工具栏背景透明
        toolbarView?.setBackgroundColor(Color.TRANSPARENT)
        
        // 加载命令历史
        loadCommandHistory()
        
        // 初始化手势检测器
        gestureDetector = GestureDetector(this, object : SimpleOnGestureListener() {
            override fun onSingleTapUp(e: MotionEvent): Boolean {
                val currentTime = System.currentTimeMillis()
                
                // 检测双击
                if (currentTime - lastTapTime < DOUBLE_TAP_TIMEOUT) {
                    lastTapTime = 0 // 重置，避免连续触发
                } else {
                    lastTapTime = currentTime
                    
                    // 单击时显示坐标（原有功能）
                    val x = e.rawX.toInt()
                    val y = e.rawY.toInt()
                    showClickPosition(x, y)
                }
                
                return false // 不消费事件，确保事件继续传递
            }
        })

        // 显示ToolBar
        showWindow()        
        
        if (serverIP.isEmpty() || deviceName.isEmpty()) {
            // 如果serverIP或deviceName为空，显示设置界面
            showSetting()
        } else {
            // 如果已设置serverIP和deviceName，自动启动脚本引擎
            isRunning = true
            // 服务启动后，将主应用移至后台
            Handler(Looper.getMainLooper()).postDelayed({
                MainActivity.getInstance()?.moveTaskToBack(true)
            }, 500)
        }
        
        // 创建光标视图，但默认隐藏
        addCursorView()
        // 触摸监控视图将在需要时创建
    }

    /**
     * 显示悬浮窗
     */
    @SuppressLint("ClickableViewAccessibility")
    private fun showWindow() {
        // 创建命令输入栏（现在包含了日志视图）
        initializeToolbar()
        // 创建悬浮按钮 - 只在这里创建一次
        createFloatingButton()
        showClick(false)
        toolbarExpanded = false
        showToolbar(toolbarExpanded)
    }

    /**
     * 重命名这个方法，避免冲突
     */
    @SuppressLint("ClickableViewAccessibility")
    private fun initializeToolbar() {
        if (toolbarView != null) return
        val layoutInflater = LayoutInflater.from(this)
        val toolbarView = layoutInflater.inflate(R.layout.toolbar, null)
        // 设置整个视图的背景为透明
        toolbarView.setBackgroundColor(Color.TRANSPARENT)
        touchView = toolbarView?.findViewById<View>(R.id.touchMonitorView)
        // 设置触摸监听器
        touchView?.setOnTouchListener { v, event ->
            // 记录所有触摸事件
            Timber.d("收到触摸事件: ${MotionEvent.actionToString(event.action)} 坐标: (${event.rawX}, ${event.rawY})")
            when (event.action) {
                MotionEvent.ACTION_DOWN -> {
                    Timber.d("触摸坐标: (${event.rawX}, ${event.rawY})")
                    showClickPosition(event.rawX.toInt(), event.rawY.toInt())
                }
            }
            // 返回false以允许事件继续传递
            false
        }
        // 创建布局参数
        val params = WindowManager.LayoutParams(
            WindowManager.LayoutParams.MATCH_PARENT,
            WindowManager.LayoutParams.MATCH_PARENT,
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY
            } else {
                WindowManager.LayoutParams.TYPE_PHONE
            },
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE,
            PixelFormat.TRANSLUCENT
        )
        
        // 设置显示位置 - 全屏显示
        params.gravity = Gravity.TOP or Gravity.START
        

        
        // 设置工具栏按钮点击事件
        val startStopButton = toolbarView.findViewById<ImageButton>(R.id.startStopButton)
        startStopButton?.setOnClickListener {
            isRunning = !isRunning
        }
        
        val syncButton = toolbarView.findViewById<ImageButton>(R.id.syncButton)
        syncButton?.setOnClickListener {
            onSyncButtonClick()
        }
        
        val settingsButton = toolbarView.findViewById<ImageButton>(R.id.settingsButton)
        settingsButton?.setOnClickListener {
            showSetting()
        }
        
        // 获取命令输入相关控件
        val commandInput = toolbarView.findViewById<EditText>(R.id.commandInput)
        val sendButton = toolbarView.findViewById<ImageButton>(R.id.sendButton)
        val historyButton = toolbarView.findViewById<ImageButton>(R.id.historyButton)
        
        // 设置命令输入框点击事件
        commandInput.setOnClickListener {
            // 使输入框可获取焦点
            makeInputFocusable()
        }
        
        // 设置命令输入框回车发送命令
        commandInput.setOnEditorActionListener { _, actionId, event ->
            if (actionId == EditorInfo.IME_ACTION_SEND || 
                actionId == EditorInfo.IME_ACTION_DONE ||
                (event != null && event.keyCode == KeyEvent.KEYCODE_ENTER && event.action == KeyEvent.ACTION_DOWN)) {
                sendCommand(commandInput)
                true
            } else {
                false
            }
        }
        
        // 设置发送按钮点击事件
        sendButton.setOnClickListener {
            sendCommand(commandInput)
            // 发送后恢复不可获取焦点状态
            makeInputUnfocusable()
        }
        
        // 设置历史按钮事件
        historyButton.setOnClickListener {
            browseHistoryUp(commandInput)
        }
        
        historyButton.setOnLongClickListener {
            showCommandHistoryDialog(commandInput)
            true
        }
        
        // 添加到窗口
        windowManager.addView(toolbarView, params)
        
        // 保存引用
        this.toolbarView = toolbarView
        
        // 根据当前日志展开状态更新窗口位置
        updateWindowPosition()
    }

    private var _isRunning = false
    var isRunning: Boolean
        get() = _isRunning
        @SuppressLint("NewApi")
        set(value) {
            try{
                if (_isRunning != value) {
                    _isRunning = value
                    if(value){
                        getScriptEngine().start(deviceName, serverIP)
                    }else{
                        getScriptEngine().end()
                    }
                    // 更新按钮图标
                    val startStopButton = toolbarView?.findViewById<ImageButton>(R.id.startStopButton)
                    if (value) {
                        // 使用系统内置图标
                        startStopButton?.setImageResource(android.R.drawable.ic_media_pause)
                    } else {
                        // 使用系统内置图标
                        startStopButton?.setImageResource(android.R.drawable.ic_media_play)
                    }
                }
            }catch(e:Exception){
                log("Failed to update button icon")
            }
        }



    private fun onStartStopButtonClick() {
        isRunning = !isRunning
    }


    private fun showSetting() {
        val windowManager = getSystemService(Context.WINDOW_SERVICE) as WindowManager
        val layoutParams = WindowManager.LayoutParams(
            WindowManager.LayoutParams.WRAP_CONTENT,
            WindowManager.LayoutParams.WRAP_CONTENT,
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY
            } else {
                WindowManager.LayoutParams.TYPE_PHONE
            },
            WindowManager.LayoutParams.FLAG_NOT_TOUCH_MODAL or WindowManager.LayoutParams.FLAG_WATCH_OUTSIDE_TOUCH,
            PixelFormat.OPAQUE
        )

        val dialogView = LayoutInflater.from(this).inflate(R.layout.d_setting, null)
        val binding = DSettingBinding.bind(dialogView)

        // 设置初始值
        binding.serverNameInput.setText(serverIP)
        binding.deviceNameInput.setText(deviceName)

        // 设置背景不透明
        dialogView.setBackgroundColor(resources.getColor(android.R.color.background_light))

        // 绑定输入逻辑
        binding.serverNameInput.setOnEditorActionListener { v, actionId, event ->
            if (actionId == EditorInfo.IME_ACTION_DONE) {
                serverIP = v.text.toString()
                true
            } else {
                false
            }
        }

        binding.deviceNameInput.setOnEditorActionListener { v, actionId, event ->
            if (actionId == EditorInfo.IME_ACTION_DONE) {
                deviceName = v.text.toString()
                true
            } else {
                false
            }
        }

        // 添加保存按钮逻辑
        binding.root.findViewById<Button>(R.id.saveButton).setOnClickListener {
            serverIP = binding.serverNameInput.text.toString()
            deviceName = binding.deviceNameInput.text.toString()
            windowManager.removeView(dialogView)
            // 保存后立即同步
            getScriptEngine().syncFiles(serverIP)
        }

        // 添加取消按钮逻辑
        binding.root.findViewById<Button>(R.id.cancelButton).setOnClickListener {
            windowManager.removeView(dialogView) // 移除悬浮窗口
        }

        // 设置淡入淡出动画
        dialogView.alpha = 0f
        dialogView.animate().alpha(1f).setDuration(300).start()

        windowManager.addView(dialogView, layoutParams)
    }

    

    // 添加光标视图, 用于显示光标位置
    private fun addCursorView() {
        cursorView = CursorView(this)
        val (cursorWidth, cursorHeight) = cursorView!!.getCursorSize() // 获取光标图片的大小
        val layoutParams = WindowManager.LayoutParams(
            cursorWidth,
            cursorHeight,
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY
            } else {
                WindowManager.LayoutParams.TYPE_PHONE
            },
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or 
            WindowManager.LayoutParams.FLAG_NOT_TOUCH_MODAL or 
            WindowManager.LayoutParams.FLAG_NOT_TOUCHABLE, // 确保不响应触摸事件
            PixelFormat.TRANSLUCENT
        )
        layoutParams.gravity = Gravity.TOP or Gravity.START
        windowManager.addView(cursorView, layoutParams)
    }

    override fun onDestroy() {
        isRunning = false
        super.onDestroy()
        
        // 取消长按检测
        cancelLongPressDetection()
        
        cursorView?.let { windowManager.removeView(it) }
        removeTouchMonitorView()
        hidePositionToast() // 隐藏点击坐标悬浮窗
        executor.shutdown()
        
        // 移除所有视图
        toolbarView?.let {
            try {
                windowManager.removeView(it)
            } catch (e: Exception) {
                Timber.e(e, "移除日志视图失败")
            }
        }
        
        floatButtonView?.let {
            try {
                windowManager.removeView(it)
            } catch (e: Exception) {
                Timber.e(e, "移除悬浮按钮失败")
            }
        }

        // 清除其他资源
        instance = null
    }



    /**
     * 设置光标位置
     * @param x Int 窗口坐标系中的X坐标（已减去状态栏高度）
     * @param y Int 窗口坐标系中的Y坐标（已减去状态栏高度）
     */
    @SuppressLint("InternalInsetResource")
    fun moveCursor(rawX: Int, rawY: Int, isScreen: Boolean = false) {
        Timber.tag("ToolBarService").d("setCursor: $rawX, $rawY (window coordinates)")
        Handler(Looper.getMainLooper()).post {
            cursorView?.let {
                val metrics = DisplayMetrics()
                windowManager.defaultDisplay.getMetrics(metrics)
                
                // 计算实际坐标
                var x = rawX
                var y = rawY
                if(isScreen) {
                    val pair = MainActivity.screenToWindowCoordinates(rawX, rawY)
                    x = pair.first
                    y = pair.second
                }

                // 计算中心对齐的偏移量
                val offsetX = it.width / 2
                val offsetY = it.height / 2

                // 计算考虑了中心对齐的新坐标
                x = (x - offsetX).coerceIn(
                    0,
                    (metrics.widthPixels - it.width)
                )
                y = (y - offsetY).coerceIn(
                    0,
                    (metrics.heightPixels - it.height)
                )

                val params = it.layoutParams as WindowManager.LayoutParams
                params.x = x
                params.y = y

                try {
                    windowManager.updateViewLayout(it, params)
                } catch (e: Exception) {
                    Timber.tag("ToolBarService").e(e, "Failed to update cursor position")
                }
            }
        }
    }

    fun flashCursor() {
        Handler(Looper.getMainLooper()).post {
            cursorView?.flash()
        }
    }



    // 移除触摸监控视图
    private fun removeTouchMonitorView() {
        touchMonitorView?.let {
            try {
                windowManager.removeView(it)
            } catch (e: Exception) {
                Timber.e(e, "Failed to remove touch monitor view")
            }
            touchMonitorView = null
        }
    }

    /**
     * 显示点击坐标
     */
    private fun showClickPosition(x: Int, y: Int) {
        try {
            // 更新最后显示时间
            lastPositionToastUpdateTime = System.currentTimeMillis()
            val pos = "($x, $y)"
            log(pos)
            // 使用Handler确保在主线程上执行
            Handler(Looper.getMainLooper()).post {
                try {
                    // 如果已经有视图，更新文本
                    if (positionToastView != null) {
                        // 使用安全的类型转换
                        val textView = positionToastView?.findViewById<TextView>(R.id.position_toast_text)
                        textView?.text = pos
                        // 重置自动隐藏定时器
                        resetPositionToastAutoHideTimer()
                        return@post
                    }
                    
                    // 创建自定义Toast视图
                    val frameLayout = FrameLayout(this).apply {
                        // 设置背景为半透明黑色，圆角
                        setBackgroundResource(R.drawable.position_toast_background)
                        // 设置内边距
                        setPadding(32, 16, 32, 16)
                    }
                    
                    // 创建文本视图
                    val textView = TextView(this).apply {
                        text = "点击坐标: ($x, $y)"
                        setTextColor(0xFFFFFFFF.toInt()) // 白色文本
                        textSize = 14f // 14sp
                        id = R.id.position_toast_text // 需要在values/ids.xml中定义
                    }
                    
                    // 添加文本视图到布局
                    frameLayout.addView(textView)
                    
                    // 保存视图引用
                    positionToastView = frameLayout
                    
                    // 创建布局参数
                    val params = WindowManager.LayoutParams(
                        WindowManager.LayoutParams.WRAP_CONTENT,
                        WindowManager.LayoutParams.WRAP_CONTENT,
                        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                            WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY
                        } else {
                            WindowManager.LayoutParams.TYPE_PHONE
                        },
                        WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or
                                WindowManager.LayoutParams.FLAG_NOT_TOUCH_MODAL or
                                WindowManager.LayoutParams.FLAG_NOT_TOUCHABLE,
                        PixelFormat.TRANSLUCENT
                    )
                    
                    // 设置显示位置
                    params.gravity = Gravity.TOP or Gravity.CENTER_HORIZONTAL
                    params.y = 100 // 距离顶部100像素
                    
                    // 添加到窗口
                    windowManager.addView(frameLayout, params)
                    
                    // 设置自动隐藏定时器
                    resetPositionToastAutoHideTimer()
                } catch (e: Exception) {
                    Timber.e(e, "显示点击坐标悬浮窗失败")
                }
            }
        } catch (e: Exception) {
            Timber.e(e, "准备点击坐标悬浮窗失败")
        }
    }

    /**
     * 重置自动隐藏定时器
     */
    private fun resetPositionToastAutoHideTimer() {
        // 移除之前的定时器
        if (positionToastHideRunnable != null) {
            Handler(Looper.getMainLooper()).removeCallbacks(positionToastHideRunnable!!)
        }
        
        // 创建新的定时器
        positionToastHideRunnable = Runnable {
            // 检查是否已经过了5秒没有更新
            val currentTime = System.currentTimeMillis()
            if (currentTime - lastPositionToastUpdateTime >= POSITION_TOAST_AUTO_HIDE_DELAY) {
                hidePositionToast()
            } else {
                // 如果还没到5秒，继续等待
                val remainingTime = POSITION_TOAST_AUTO_HIDE_DELAY - (currentTime - lastPositionToastUpdateTime)
                Handler(Looper.getMainLooper()).postDelayed(positionToastHideRunnable!!, remainingTime)
            }
        }
        
        // 启动定时器
        Handler(Looper.getMainLooper()).postDelayed(positionToastHideRunnable!!, POSITION_TOAST_AUTO_HIDE_DELAY)
    }

    /**
     * 隐藏点击坐标悬浮窗
     */
    private fun hidePositionToast() {
        Handler(Looper.getMainLooper()).post {
            try {
                // 移除定时器
                if (positionToastHideRunnable != null) {
                    Handler(Looper.getMainLooper()).removeCallbacks(positionToastHideRunnable!!)
                    positionToastHideRunnable = null
                }
                
                // 移除视图
                if (positionToastView != null) {
                    windowManager.removeView(positionToastView)
                    positionToastView = null
                }
            } catch (e: Exception) {
                Timber.e(e, "隐藏点击坐标悬浮窗失败")
            }
        }
    }


    private fun browseHistoryUp(commandInput: EditText) {
        if (commandHistory.isEmpty()) return
        
        if (historyIndex < 0) {
            // 首次浏览，保存当前输入
            currentInput = commandInput.text.toString()
            historyIndex = commandHistory.size - 1 // 从最新的命令开始
        } else if (historyIndex > 0) {
            // 继续向上浏览（向更早的命令）
            historyIndex--
        }
        
        // 设置命令
        commandInput.setText(commandHistory[historyIndex])
        commandInput.setSelection(commandInput.text.length)
    }

    private fun browseHistoryDown(commandInput: EditText) {
        if (historyIndex < 0) return
        
        if (historyIndex < commandHistory.size - 1) {
            // 向下浏览（向更新的命令）
            historyIndex++
            commandInput.setText(commandHistory[historyIndex])
            commandInput.setSelection(commandInput.text.length)
        } else {
            // 已经到最新的命令，恢复原始输入
            historyIndex = -1
            commandInput.setText(currentInput)
            commandInput.setSelection(commandInput.text.length)
        }
    }

    private fun showCommandHistoryDialog(commandInput: EditText) {
        if (commandHistory.isEmpty()) {
            Toast.makeText(this, "没有命令历史", Toast.LENGTH_SHORT).show()
            return
        }
        
        try {
            // 使用自定义布局创建对话框
            val builder = AlertDialog.Builder(this, R.style.Theme_AppCompat_Dialog_Alert)
            builder.setTitle("命令历史")
            
            // 直接使用命令历史列表，不需要反转
            builder.setItems(commandHistory.toTypedArray()) { _, which ->
                val selectedCommand = commandHistory[which]
                commandInput.setText(selectedCommand)
                commandInput.setSelection(selectedCommand.length)
            }
            
            builder.setNegativeButton("取消", null)
            builder.setNeutralButton("清空历史") { _, _ ->
                commandHistory.clear()
                saveCommandHistory()
                Toast.makeText(this, "命令历史已清空", Toast.LENGTH_SHORT).show()
            }
            
            val dialog = builder.create()
            
            // 设置对话框类型为应用覆盖层
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                dialog.window?.setType(WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY)
            } else {
                dialog.window?.setType(WindowManager.LayoutParams.TYPE_PHONE)
            }
            
            dialog.show()
        } catch (e: Exception) {
            Timber.e(e, "显示命令历史对话框失败")
            Toast.makeText(this, "无法显示命令历史: ${e.message}", Toast.LENGTH_SHORT).show()
        }
    }

    private fun sendCommand(commandInput: EditText?) {
        val command = commandInput?.text?.toString()?.trim() ?: ""
        if (command.isNotEmpty()) {
            // 添加到历史记录
            addCommandToHistory(command)
            // 清空输入框
            commandInput?.setText("")
            // 重置历史浏览索引
            historyIndex = -1
            // 执行命令
            executeCommand(command)
            // 隐藏键盘
            val imm = getSystemService(Context.INPUT_METHOD_SERVICE) as InputMethodManager
            imm.hideSoftInputFromWindow(commandInput?.windowToken, 0)
            
            // 恢复不可获取焦点状态
            makeInputUnfocusable()
        }
    }


    public fun showToolbar(show: Boolean) {
        if (show) {
            // 显示工具栏
            cursorView?.visibility = View.VISIBLE
            toolbarView?.visibility = View.VISIBLE
        } else {
            // 隐藏工具栏
            cursorView?.visibility = View.GONE
            toolbarView?.visibility = View.GONE
        }
    }


    // 修改 showClick 方法，使用布局中的视图
    public fun showClick(enable: Boolean) {
        this.touchView?.visibility = if (enable) View.VISIBLE else View.GONE
    }

    // 添加createLayoutParams方法
    private fun createLayoutParams(outMetrics: DisplayMetrics): WindowManager.LayoutParams {
        val layoutParam = WindowManager.LayoutParams(
            WindowManager.LayoutParams.WRAP_CONTENT,
            WindowManager.LayoutParams.WRAP_CONTENT,
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY
            } else {
                        WindowManager.LayoutParams.TYPE_PHONE
            },
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or
                    WindowManager.LayoutParams.FLAG_NOT_TOUCH_MODAL,
            PixelFormat.TRANSLUCENT
        )
        layoutParam.gravity = Gravity.CENTER
        return layoutParam
    }

    @SuppressLint("ClickableViewAccessibility")
    private fun createFloatingButton() {
        if (floatButtonView != null) {
            // 如果按钮已存在，确保可见
            floatButtonView?.visibility = View.VISIBLE
            return
        }
        
        // 创建悬浮按钮
        val buttonView = LayoutInflater.from(this).inflate(R.layout.float_button, null)
        
        // 直接使用根视图作为按钮
        // 不需要查找toggleButton，因为整个视图就是按钮
        
        // 创建布局参数
        val params = WindowManager.LayoutParams(
            128, // 固定宽度为128dp
            128, // 固定高度为128dp
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY
            } else {
                WindowManager.LayoutParams.TYPE_PHONE
            },
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE,
            PixelFormat.TRANSLUCENT
        )
        
        // 设置初始位置
        params.gravity = Gravity.TOP or Gravity.START
        params.x = originalButtonX
        params.y = originalButtonY
        
        // 保存参数引用
        buttonParams = params
        
        // 添加到窗口
        windowManager.addView(buttonView, params)
        
        // 保存引用
        floatButtonView = buttonView
        
        // 设置触摸监听器 - 简化版，始终可拖动
        touchListener()
    }

    /**
     * 设置简化版悬浮按钮触摸监听器 - 始终可拖动
     */
    private fun touchListener() {
        if (floatButtonView == null || buttonParams == null) return
        
        // 记录触摸事件的初始位置
        var initialTouchX = 0f
        var initialTouchY = 0f
        var initialX = 0
        var initialY = 0
        var isDragging = false
        
        // 设置触摸事件监听，确保全屏拖动功能
        floatButtonView?.setOnTouchListener { v, event ->
            when (event.action) {
                MotionEvent.ACTION_DOWN -> {
                    // 记录初始位置
                    initialX = buttonParams?.x ?: 0
                    initialY = buttonParams?.y ?: 0
                    initialTouchX = event.rawX
                    initialTouchY = event.rawY
                    isDragging = false
                    isLongPressed = false
                    
                    // 开始长按检测
                    startLongPressDetection()
                    true // 返回true表示继续接收后续事件
                }
                MotionEvent.ACTION_MOVE -> {
                    // 计算移动距离
                    val dx = event.rawX - initialTouchX
                    val dy = event.rawY - initialTouchY
                    
                    // 如果移动距离超过阈值，认为是拖动
                    if (!isDragging && (Math.abs(dx) > 5 || Math.abs(dy) > 5)) {
                        isDragging = true
                        // 取消长按检测
                        cancelLongPressDetection()
                    }
                    
                    // 更新位置
                    if (isDragging) {
                        buttonParams?.x = initialX + dx.toInt()
                        buttonParams?.y = initialY + dy.toInt()
                        try {
                            windowManager.updateViewLayout(floatButtonView, buttonParams)
                            
                            // 保存当前位置为原始位置（用于恢复）
                            originalButtonX = buttonParams?.x ?: 0
                            originalButtonY = buttonParams?.y ?: 0
                        } catch (e: Exception) {
                            Timber.e(e, "更新悬浮按钮位置失败")
                        }
                    }
                    true
                }
                MotionEvent.ACTION_UP -> {
                    // 取消长按检测
                    cancelLongPressDetection()
                    
                    if (!isDragging) {
                        if (isLongPressed) {
                            // 长按：切换touchView显示
                            touchViewVisible = !touchViewVisible
                            showClick(touchViewVisible)
                            log("长按切换touchView: ${if (touchViewVisible) "显示" else "隐藏"}")
                        } else {
                            // 短按：切换toolbar显示
                            toolbarExpanded = !toolbarExpanded
                            showToolbar(toolbarExpanded)
                        }
                    }
                    true
                }
                else -> false
            }
        }
    }

    /**
     * 开始长按检测
     */
    private fun startLongPressDetection() {
        cancelLongPressDetection() // 先取消之前的检测
        
        longPressRunnable = Runnable {
            isLongPressed = true
            // 可以在这里添加长按反馈，比如震动或视觉反馈
            log("检测到长按")
        }
        
        Handler(Looper.getMainLooper()).postDelayed(longPressRunnable!!, LONG_PRESS_TIMEOUT)
    }

    /**
     * 取消长按检测
     */
    private fun cancelLongPressDetection() {
        longPressRunnable?.let {
            Handler(Looper.getMainLooper()).removeCallbacks(it)
            longPressRunnable = null
        }
    }

    /**
     * 设置命令输入框可获取焦点
     */
    private fun makeInputFocusable() {
        if (toolbarView == null) return
        
        try {
            // 获取当前布局参数
            val params = (toolbarView?.layoutParams as? WindowManager.LayoutParams) ?: return
            
            // 移除不可获取焦点的标志
            params.flags = params.flags and WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE.inv()
            
            // 更新布局
            windowManager.updateViewLayout(toolbarView, params)
            
            // 获取命令输入框
            val commandInput = toolbarView?.findViewById<EditText>(R.id.commandInput)
            
            // 请求焦点并显示键盘
            commandInput?.requestFocus()
            val imm = getSystemService(Context.INPUT_METHOD_SERVICE) as InputMethodManager
            imm.showSoftInput(commandInput, InputMethodManager.SHOW_IMPLICIT)
        } catch (e: Exception) {
            Timber.e(e, "设置输入框可获取焦点失败")
        }
    }

    /**
     * 设置命令输入框不可获取焦点
     */
    private fun makeInputUnfocusable() {
        if (toolbarView == null) return
        
        try {
            // 获取当前布局参数
            val params = (toolbarView?.layoutParams as? WindowManager.LayoutParams) ?: return
            
            // 添加不可获取焦点的标志
            params.flags = params.flags or WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE
            
            // 更新布局
            windowManager.updateViewLayout(toolbarView, params)
        } catch (e: Exception) {
            Timber.e(e, "设置输入框不可获取焦点失败")
        }
    }

    // 添加保存和加载命令历史的方法
    private fun saveCommandHistory() {
        val prefs = getPrefs()
        val editor = prefs.edit()
        val historySet = LinkedHashSet(commandHistory) // 使用LinkedHashSet去重并保持顺序
        editor.putStringSet(COMMAND_HISTORY_KEY, historySet)
        editor.apply()
    }

    private fun loadCommandHistory() {
        val prefs = getPrefs()
        val historySet = prefs.getStringSet(COMMAND_HISTORY_KEY, null)
        if (historySet != null) {
            commandHistory.clear()
            commandHistory.addAll(historySet)
        }
    }

    /**
     * 设置整个UI的可见性
     * 
     * @param visible true表示恢复之前的UI显示状态，false表示隐藏所有UI
     */
    fun showUI(visible: Boolean) {
        try {
            if (visible) {
                floatButtonView?.visibility = View.VISIBLE
            } else {
                floatButtonView?.visibility = View.GONE
                touchViewVisible = false
                showClick(touchViewVisible)
                toolbarExpanded = false
                showToolbar(toolbarExpanded)
            }
        } catch (e: Exception) {
            Timber.e(e, "设置UI可见性失败")
        }
    }





    // 修改executeCommand方法，移除logTextView参数
    private fun executeCommand(command: String) {
        CoroutineScope(Dispatchers.IO).launch {
            try {
                // 检查脚本引擎是否已初始化
                if (!isRunning) {
                    log("脚本引擎未初始化或未运行，无法执行命令", "", "e")
                    return@launch
                }
                PythonServices.doCommand(command)
            } catch (e: Exception) {
                logEx(e, "执行失败: ${e.message}", "")
            }
        }
    }

    // 修改添加命令到历史的方法
    private fun addCommandToHistory(command: String) {
        // 如果命令为空，不添加到历史
        if (command.isBlank()) return
        
        // 如果命令已存在，先移除旧记录
        commandHistory.remove(command)
        
        // 添加到列表末尾（最新的命令在最后）
        commandHistory.add(command)
        
        // 如果历史记录超过最大数量，移除最旧的记录
        while (commandHistory.size > MAX_HISTORY_SIZE) {
            commandHistory.removeAt(0)
        }
        
        // 保存历史记录
        saveCommandHistory()
    }

    // 添加回onSyncButtonClick方法
    private fun onSyncButtonClick() {
        if (serverIP.isEmpty()) {
            Toast.makeText(this, "请先设置服务器IP", Toast.LENGTH_SHORT).show()
            return
        }
        
        Toast.makeText(this, "正在同步文件...", Toast.LENGTH_SHORT).show()
        
        // 在后台线程中执行文件同步
        Thread {
            try {
                getScriptEngine().syncFiles(serverIP)
                Handler(Looper.getMainLooper()).post {
                    Toast.makeText(this, "文件同步完成", Toast.LENGTH_SHORT).show()
                }
            } catch (e: Exception) {
                Handler(Looper.getMainLooper()).post {
                    Toast.makeText(this, "文件同步失败: ${e.message}", Toast.LENGTH_SHORT).show()
                }
                Timber.e(e, "文件同步失败")
            }
        }.start()
    }

    /**
     * 更新窗口位置
     */
    private fun updateWindowPosition() {
        if (toolbarView == null) return
        
        try {
            // 获取当前布局参数
            val params = (toolbarView?.layoutParams as? WindowManager.LayoutParams) ?: return
            
            // 保持全屏显示
            params.gravity = Gravity.TOP or Gravity.START
            
            // 使用MATCH_PARENT高度确保touchMonitorView全屏
            params.height = WindowManager.LayoutParams.MATCH_PARENT
            
            // 更新布局
            windowManager.updateViewLayout(toolbarView, params)
        } catch (e: Exception) {
            Timber.e(e, "更新窗口位置失败")
        }
    }

}