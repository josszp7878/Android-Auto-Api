package cn.vove7.andro_accessibility_api.demo.service

import android.annotation.SuppressLint
import android.content.Context
import android.content.Intent
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
import cn.vove7.andro_accessibility_api.demo.databinding.DialogDeviceInfoBinding
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
        private var cachedLogTextView: WeakReference<TextView>? = null
        
        @JvmStatic
        fun getInstance(): WeakReference<ToolBarService>? {
            return instance
        }
        @JvmStatic
        fun logEx(e: Exception, content: String = "", tag: String = "", result: String? = null) {
            val msg = "${content}\n${e.message}\n${e.stackTrace.joinToString("\n")}"
            log(msg, tag, "e", result)
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
        fun log(content: String, tag: String = "", level: String = "i", result: String? = null) {
            try {
                if(content.isEmpty())
                    return
                // 如果有有效的logTextView，输出到日志窗口
                val logTextView = cachedLogTextView?.get()            
                if (logTextView != null) {
                    val timestamp = SimpleDateFormat("HH:mm:ss", Locale.getDefault()).format(Date())
                    val logEntry = if (result != null) {
                        if (tag.isEmpty()) {
                            "$timestamp $content\n => $result\n"
                        } else {
                            "$timestamp[$tag] $content\n => $result\n"
                        }
                    } else {
                        if (tag.isEmpty()) {
                            "$timestamp $content\n"
                        } else {
                            "$timestamp[$tag] $content\n"
                        }
                    }
                    
                    val spannable = SpannableString(logEntry)
                    val color = when (level.lowercase()) {
                        "e", "error" -> Color.RED
                        "w", "warn" -> Color.YELLOW
                        "d", "debug" -> Color.GRAY
                        "result" -> Color.CYAN
                        "c" -> Color.GREEN
                        else -> Color.WHITE
                    }
                    spannable.setSpan(ForegroundColorSpan(color), 0, logEntry.length, Spannable.SPAN_EXCLUSIVE_EXCLUSIVE)
                    
                    // 在UI线程更新日志
                    Handler(Looper.getMainLooper()).post {
                        logTextView.append(spannable)
                        
                        // 滚动到底部
                        val parent = logTextView.parent
                        if (parent is ScrollView) {
                            parent.post {
                                parent.fullScroll(View.FOCUS_DOWN)
                            }
                        }
                        
                        // 如果有非空TAG，更新TAG列表
                        if (tag.isNotEmpty() && tag != "System" && tag != "cmd") {
                            // 获取ToolBarService实例
                            val service = instance?.get()
                            if (service != null) {
                                // 更新TAG列表
                                service.updateTagList(tag)
                            }
                        }
                    }
                }
                //打印系统日志
                val logTag = "ToolBarService"
                val logMessage = if (tag.isEmpty()) {
                    "[$level] $content" + (result?.let { " Result: $it" } ?: "")
                } else {
                    "[$tag][$level] $content" + (result?.let { " Result: $it" } ?: "")
                }
                when (level.lowercase()) {
                    "e", "error" -> Log.e(logTag, logMessage)
                    "w", "warn" -> Log.w(logTag, logMessage)
                    "d", "debug" -> Log.d(logTag, logMessage)
                    "c", "cmd" -> Log.i(logTag, logMessage)
                    else -> Log.i(logTag, logMessage)
                }
            } catch (e: Exception) {
                Timber.e(e, "记录日志失败")
            }
        }
    }

    private lateinit var windowManager: WindowManager
    private var floatRootView: View? = null // 悬浮窗View
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
            return _deviceName!!
        }
        set(value) {
            if(value != _deviceName){
                _deviceName = value
                getPrefs().edit().putString(DEVICE_NAME_KEY, value).apply()
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
    private var logsExpanded = true
    private val commandHistory = ArrayList<String>()
    private var historyIndex = -1
    private var isExpanded = false
    private var toolbarExpanded = true

    // 添加触摸监控视图相关变量
    private var touchView: View? = null

    // 在类定义中添加新变量
    private var floatButtonView: View? = null
    private var initialX = 0
    private var initialY = 0
    private var initialTouchX = 0f
    private var initialTouchY = 0f

    // 添加点击坐标显示相关变量
    private var clickerEnabled = false

    // 添加命令历史持久化功能
    private val COMMAND_HISTORY_KEY = "command_history"
    private val MAX_HISTORY_SIZE = 100

    // 添加新的成员变量
    private var commandInputBarView: View? = null

    // 添加成员变量，用于保存悬浮按钮的原始位置
    private var originalButtonX = 100
    private var originalButtonY = 200
    private var buttonParams: WindowManager.LayoutParams? = null
    private var isButtonDocked = false

    // 在类的成员变量部分添加这些变量
    private var currentInput = ""  // 保存当前输入，用于从历史返回

    override fun onCreate() {
        super.onCreate()
        instance = WeakReference(this)
        windowManager = getSystemService(WINDOW_SERVICE) as WindowManager
        
        // 确保工具栏背景透明
        floatRootView?.setBackgroundColor(Color.TRANSPARENT)
        
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
        
        Log.d("ToolBarService", "Service created")
        
        // 显示ToolBar
        showWindow()
        
        // 设置控制台视图
        setupConsoleView()
        
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
        val outMetrics = DisplayMetrics()
        windowManager.defaultDisplay.getMetrics(outMetrics)
        
        // 创建命令输入栏（现在包含了日志视图）
        initializeToolbar()
        
        // 创建悬浮按钮 - 只在这里创建一次
        createFloatingButton()
        
        // 初始状态设置
        if (!toolbarExpanded) {
            // 如果初始状态是收起的，隐藏主界面
            floatRootView?.visibility = View.GONE
        } else {
            // 确保日志区域正确显示
            updateLogsVisibility()
        }
    }

    /**
     * 重命名这个方法，避免冲突
     */
    private fun initializeToolbar() {
        if (floatRootView != null) return        
        val layoutInflater = LayoutInflater.from(this)
        val unifiedView = layoutInflater.inflate(R.layout.command_input_bar, null)
        
        // 设置整个视图的背景为透明
        unifiedView.setBackgroundColor(Color.TRANSPARENT)
        
        // 创建布局参数
        val params = WindowManager.LayoutParams(
            WindowManager.LayoutParams.MATCH_PARENT,
            if (logsExpanded) WindowManager.LayoutParams.MATCH_PARENT else WindowManager.LayoutParams.WRAP_CONTENT,
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY
            } else {
                WindowManager.LayoutParams.TYPE_PHONE
            },
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE,
            PixelFormat.TRANSLUCENT
        )
        
        // 设置显示位置 - 始终底部对齐
        params.gravity = Gravity.BOTTOM or Gravity.CENTER_HORIZONTAL
        
        // 设置过滤按钮点击事件
        val filterButton = unifiedView.findViewById<ImageButton>(R.id.filterButton)
        filterButton?.setOnClickListener {
            val filterInput = unifiedView.findViewById<EditText>(R.id.filterInput)
            filterInput?.let {
                if (it.visibility == View.VISIBLE) {
                    it.visibility = View.GONE
                } else {
                    it.visibility = View.VISIBLE
                    it.requestFocus()
                    val imm = getSystemService(Context.INPUT_METHOD_SERVICE) as InputMethodManager
                    imm.showSoftInput(it, InputMethodManager.SHOW_IMPLICIT)
                }
            }
        }
        
        // 设置清除过滤按钮点击事件
        val clearFilterButton = unifiedView.findViewById<ImageButton>(R.id.clearFilterButton)
        clearFilterButton?.setOnClickListener {
            val filterInput = unifiedView.findViewById<EditText>(R.id.filterInput)
            filterInput?.setText("")
            val logTextView = unifiedView.findViewById<TextView>(R.id.logTextView)
            filterLogs("", logTextView)
        }
        
        // 设置过滤输入框动作监听
        val filterInput = unifiedView.findViewById<EditText>(R.id.filterInput)
        filterInput?.setOnEditorActionListener { textView, actionId, event ->
            if (actionId == EditorInfo.IME_ACTION_DONE) {
                val logTextView = unifiedView.findViewById<TextView>(R.id.logTextView)
                filterLogs(textView.text.toString(), logTextView)
                
                // 隐藏键盘
                val imm = getSystemService(Context.INPUT_METHOD_SERVICE) as InputMethodManager
                imm.hideSoftInputFromWindow(textView.windowToken, 0)
                return@setOnEditorActionListener true
            }
            false
        }
        
        // 设置工具栏按钮点击事件
        val startStopButton = unifiedView.findViewById<ImageButton>(R.id.startStopButton)
        startStopButton?.setOnClickListener {
            isRunning = !isRunning
        }
        
        val syncButton = unifiedView.findViewById<ImageButton>(R.id.syncButton)
        syncButton?.setOnClickListener {
            onSyncButtonClick()
        }
        
        val settingsButton = unifiedView.findViewById<ImageButton>(R.id.settingsButton)
        settingsButton?.setOnClickListener {
            showSetting()
        }
        
        // 获取命令输入相关控件
        val commandInput = unifiedView.findViewById<EditText>(R.id.commandInput)
        val sendButton = unifiedView.findViewById<ImageButton>(R.id.sendButton)
        val historyButton = unifiedView.findViewById<ImageButton>(R.id.historyButton)
        val toggleLogsButton = unifiedView.findViewById<ImageButton>(R.id.toggleLogsButton)
        
        // 设置命令输入框点击事件
        commandInput.setOnClickListener {
            // 使输入框可获取焦点
            makeInputFocusable()
        }
        
        // 设置发送按钮点击事件
        sendButton.setOnClickListener {
            val logTextView = unifiedView.findViewById<TextView>(R.id.logTextView)
            sendCommand(commandInput, logTextView)
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
        
        // 设置日志切换按钮事件
        toggleLogsButton?.setOnClickListener { 
            toggleLogsVisibility() 
        }
        
        // 初始化日志切换按钮图标
        updateLogsToggleButton(toggleLogsButton)
        
        // 添加到窗口
        windowManager.addView(unifiedView, params)
        
        // 保存引用
        floatRootView = unifiedView
        commandInputBarView = unifiedView
        
        // 缓存日志视图
        val logTextView = unifiedView.findViewById<TextView>(R.id.logTextView)
        cachedLogTextView = WeakReference(logTextView)
        
        // 初始化日志系统
        initLogSystem(logTextView)
        
        // 初始化过滤系统
        initFilterSystem(unifiedView)
        
        // 根据当前日志展开状态更新窗口位置
        updateWindowPosition()
    }

    /**
     * 初始化过滤系统
     */
    private fun initFilterSystem(rootView: View) {
        val filterInput = rootView.findViewById<EditText>(R.id.filterInput)
        val clearFilterButton = rootView.findViewById<ImageButton>(R.id.clearFilterButton)
        val filterButton = rootView.findViewById<ImageButton>(R.id.filterButton)
        val tagFilterSpinner = rootView.findViewById<Spinner>(R.id.tagFilterSpinner)
        
        // 设置过滤输入框监听
        filterInput?.addTextChangedListener(object : android.text.TextWatcher {
            override fun beforeTextChanged(s: CharSequence?, start: Int, count: Int, after: Int) {}
            override fun onTextChanged(s: CharSequence?, start: Int, before: Int, count: Int) {}
            override fun afterTextChanged(s: Editable?) {
                filterLogs(s.toString(), rootView.findViewById(R.id.logTextView))
            }
        })
        
        // 设置清除过滤按钮
        clearFilterButton?.setOnClickListener {
            filterInput?.setText("")
        }
        
        // 设置过滤按钮
        filterButton?.setOnClickListener {
            // 切换过滤输入框的可见性
            if (filterInput?.visibility == View.VISIBLE) {
                filterInput.visibility = View.GONE
                clearFilterButton?.visibility = View.GONE
            } else {
                filterInput?.visibility = View.VISIBLE
                clearFilterButton?.visibility = View.VISIBLE
            }
        }
        
        // 初始化TAG过滤下拉框
        if (tagFilterSpinner != null) {
            // 创建适配器
            val adapter = ArrayAdapter<String>(
                this,
                android.R.layout.simple_spinner_item,
                mutableListOf("全部", "System", "cmd")
            )
            adapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item)
            tagFilterSpinner.adapter = adapter
            
            // 设置选择监听器
            tagFilterSpinner.onItemSelectedListener = object : AdapterView.OnItemSelectedListener {
                override fun onItemSelected(parent: AdapterView<*>?, view: View?, position: Int, id: Long) {
                    val selectedTag = parent?.getItemAtPosition(position) as String
                    if (selectedTag == "全部") {
                        // 显示所有日志
                        filterLogs("", rootView.findViewById(R.id.logTextView))
                    } else {
                        // 按TAG过滤
                        filterLogs("[$selectedTag]", rootView.findViewById(R.id.logTextView))
                    }
                }
                
                override fun onNothingSelected(parent: AdapterView<*>?) {
                    // 不做任何处理
                }
            }
        }
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
                        scriptEngine.start(deviceName, serverIP)
                    }else{
                        scriptEngine.end()
                    }
                    // 更新按钮图标
                    val startStopButton = floatRootView?.findViewById<ImageButton>(R.id.startStopButton)
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

    private var _scriptEngine: ScriptEngine? = null
    var scriptEngine: ScriptEngine
        get() {
            if (_scriptEngine == null) {
                _scriptEngine = ScriptEngine.getInstance(this)
            }
            return _scriptEngine!!
        }
        set(value) {
            _scriptEngine = value
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

        val dialogView = LayoutInflater.from(this).inflate(R.layout.dialog_device_info, null)
        val binding = DialogDeviceInfoBinding.bind(dialogView)

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
            scriptEngine.syncFiles(serverIP)
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
        cursorView?.let { windowManager.removeView(it) }
        removeTouchMonitorView()
        hidePositionToast() // 隐藏点击坐标悬浮窗
        executor.shutdown()
        
        // 移除所有视图
        floatRootView?.let {
            try {
                windowManager.removeView(it)
            } catch (e: Exception) {
                Timber.e(e, "移除日志视图失败")
            }
        }
        
        commandInputBarView?.let {
            try {
                windowManager.removeView(it)
            } catch (e: Exception) {
                Timber.e(e, "移除命令输入栏失败")
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
        cachedLogTextView = null
    }

    // 新增方法：隐藏光标
    fun hideCursor() {
        // 确保在主线程执行
        Handler(Looper.getMainLooper()).post {
            cursorView?.visibility = View.GONE
        }
    }

    // 新增方法：显示光标
    fun showCursor() {
        // 确保在主线程执行
        Handler(Looper.getMainLooper()).post {
            cursorView?.visibility = View.VISIBLE
        }
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



    // 修改添加触摸监控覆盖层的方法
    @SuppressLint("ClickableViewAccessibility")
    private fun addTouchMonitorOverlay() {
        // 如果已经添加过，先移除
        removeTouchMonitorView()
        
        // 创建一个透明的全屏覆盖层
        touchMonitorView = FrameLayout(this).apply {
            // 设置为完全透明
            setBackgroundColor(0x00000000)
        }
        
        // 添加到窗口，确保在ToolBar之下
        val params = WindowManager.LayoutParams(
            WindowManager.LayoutParams.MATCH_PARENT,
            WindowManager.LayoutParams.MATCH_PARENT,
            WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY,
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or
                    WindowManager.LayoutParams.FLAG_NOT_TOUCH_MODAL, // 允许事件传递到下层窗口
            PixelFormat.TRANSLUCENT
        )
        params.gravity = Gravity.START or Gravity.TOP
        
        // 设置触摸监听
        touchMonitorView?.setOnTouchListener { _, event ->
            // 将事件传递给手势检测器
            gestureDetector.onTouchEvent(event)
            
            // 返回false让事件继续传递
            false
        }
        
        // 添加到窗口
        windowManager.addView(touchMonitorView, params)
        
        // 确保ToolBar在覆盖层之上
        if (floatRootView != null) {
            try {
                // 移除并重新添加ToolBar，确保它在覆盖层之上
                windowManager.removeView(floatRootView)
                val outMetrics = DisplayMetrics()
                windowManager.defaultDisplay.getMetrics(outMetrics)
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
                windowManager.addView(floatRootView, layoutParam)
            } catch (e: Exception) {
                Timber.e(e, "Failed to reorder views")
            }
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

    fun showClicker(enable: Boolean) {
        clickerEnabled = enable
        
        if (enable) {
            // 启用点击坐标显示，添加全屏透明背景以捕获点击事件
            showTouchMonitorView()
        } else {
            // 禁用点击坐标显示，移除背景
            hideTouchMonitorView()
        }
        
        log("点击坐标显示已" + (if (enable) "启用" else "禁用"), "System", "i")
    }   

    /**
     * 显示点击坐标
     */
    private fun showClickPosition(x: Int, y: Int) {
        try {
            // 更新最后显示时间
            lastPositionToastUpdateTime = System.currentTimeMillis()
            
            // 使用Handler确保在主线程上执行
            Handler(Looper.getMainLooper()).post {
                try {
                    // 如果已经有视图，更新文本
                    if (positionToastView != null) {
                        // 使用安全的类型转换
                        val textView = positionToastView?.findViewById<TextView>(R.id.position_toast_text)
                        textView?.text = "点击坐标: ($x, $y)"
                        
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


    /**
     * 切换主窗口显示状态
     */
    private fun toggleMainWindow(isExpanded: Boolean) {
        try {
            // 创建并发送广播
            val intent = Intent("cn.vove7.auto.ACTION_TOGGLE_MAIN_WINDOW")
            // 传递工具栏状态
            intent.putExtra("isExpanded", isExpanded)
            intent.setPackage(packageName)
            sendBroadcast(intent)
        } catch (e: Exception) {
            // 记录错误
            Log.e("ToolBarService", "切换主窗口显示状态失败", e)
        }
    }

    // 修改toggleLogsVisibility方法
    private fun toggleLogsVisibility() {
        logsExpanded = !logsExpanded
        updateLogsVisibility()
    }

    // 修改updateLogsVisibility方法
    private fun updateLogsVisibility() {
        val logArea = floatRootView?.findViewById<LinearLayout>(R.id.logArea)
        logArea?.visibility = if (logsExpanded) View.VISIBLE else View.GONE
        
        // 更新窗口位置和大小
        updateWindowPosition()
        
        // 更新切换按钮图标
        val toggleLogsButton = floatRootView?.findViewById<ImageButton>(R.id.toggleLogsButton)
        updateLogsToggleButton(toggleLogsButton)
    }

    /**
     * 更新日志切换按钮图标
     */
    private fun updateLogsToggleButton(button: ImageButton?) {
        button?.setImageResource(
            if (logsExpanded) android.R.drawable.arrow_down_float
            else android.R.drawable.arrow_up_float
        )
    }

    private fun filterLogs(filterText: String, logTextView: TextView?) {
        if (logTextView == null) return
        
        // 获取原始日志文本
        val originalText = logTextView.text.toString()
        
        // 如果过滤文本为空，显示所有日志
        if (filterText.isEmpty()) {
            // 重新初始化日志系统，显示所有日志
            initLogSystem(logTextView)
            return
        }
        
        // 清空当前日志
        logTextView.text = ""
        
        // 按行分割日志
        val lines = originalText.split("\n")
        
        // 遍历每一行，查找包含过滤文本的日志
        for (line in lines) {
            if (line.lowercase().contains(filterText.lowercase())) {
                // 创建带颜色的文本
                val spannable = SpannableString("$line\n")
                
                // 根据日志级别设置颜色
                val color = when {
                    line.contains("[e]") || line.contains("[error]") -> Color.RED
                    line.contains("[w]") || line.contains("[warn]") -> Color.YELLOW
                    line.contains("[d]") || line.contains("[debug]") -> Color.GREEN
                    line.contains("[result]") -> Color.CYAN
                    line.contains("[c]") -> Color.GREEN
                    else -> Color.WHITE
                }
                
                spannable.setSpan(ForegroundColorSpan(color), 0, spannable.length, Spannable.SPAN_EXCLUSIVE_EXCLUSIVE)
                
                // 添加到日志视图
                logTextView.append(spannable)
            }
        }
        
        // 滚动到底部
        val parent = logTextView.parent
        if (parent is ScrollView) {
            parent.post {
                parent.fullScroll(View.FOCUS_DOWN)
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

    private fun sendCommand(commandInput: EditText?, logTextView: TextView?) {
        val command = commandInput?.text?.toString()?.trim() ?: ""
        if (command.isNotEmpty()) {
            // 添加到历史记录
            addCommandToHistory(command)
            // 清空输入框
            commandInput?.setText("")
            // 重置历史浏览索引
            historyIndex = -1
            // 执行命令
            executeCommand(command, logTextView)
            // 隐藏键盘
            val imm = getSystemService(Context.INPUT_METHOD_SERVICE) as InputMethodManager
            imm.hideSoftInputFromWindow(commandInput?.windowToken, 0)
            
            // 恢复不可获取焦点状态
            makeInputUnfocusable()
        }
    }

    private fun initLogSystem(logTextView: TextView?) {
        if (logTextView == null) return
        // 清空日志
        logTextView.text = ""
    }

    // 实现TAG过滤方法
    private fun filterLogsByTag(tag: String, logTextView: TextView?) {
        if (logTextView == null) return
        
        // 获取原始日志文本
        val originalText = logTextView.text.toString()
        
        // 如果选择"全部"，则显示所有日志
        if (tag.isEmpty()) {
            // 重新初始化日志系统，显示所有日志
            initLogSystem(logTextView)
            return
        }
        
        // 清空当前日志
        logTextView.text = ""
        
        // 按行分割日志
        val lines = originalText.split("\n")
        
        // 遍历每一行，查找包含指定TAG的日志
        for (line in lines) {
            if (line.contains("[$tag]")) {
                // 创建带颜色的文本
                val spannable = SpannableString("$line\n")
                
                // 根据日志级别设置颜色
                val color = when {
                    line.contains("[e]") || line.contains("[error]") -> Color.RED
                    line.contains("[w]") || line.contains("[warn]") -> Color.YELLOW
                    line.contains("[d]") || line.contains("[debug]") -> Color.GREEN
                    line.contains("[result]") -> Color.CYAN
                    line.contains("[c]") -> Color.GREEN
                    else -> Color.WHITE
                }
                
                spannable.setSpan(ForegroundColorSpan(color), 0, spannable.length, Spannable.SPAN_EXCLUSIVE_EXCLUSIVE)
                
                // 添加到日志视图
                logTextView.append(spannable)
            }
        }
        
        // 滚动到底部
        val parent = logTextView.parent
        if (parent is ScrollView) {
            parent.post {
                parent.fullScroll(View.FOCUS_DOWN)
            }
        }
    }

    // 添加收集TAG的方法
    private fun collectTags(logTextView: TextView?, tagList: ArrayList<String>) {
        if (logTextView == null) return
        
        // 获取原始日志文本
        val originalText = logTextView.text.toString()
        
        // 使用正则表达式匹配所有TAG
        val tagPattern = Regex("\\[(\\w+)\\]")
        val matches = tagPattern.findAll(originalText)
        
        // 收集所有唯一的TAG
        val uniqueTags = HashSet<String>()
        for (match in matches) {
            val tag = match.groupValues[1]
            // 排除日志级别标签
            if (tag != "e" && tag != "w" && tag != "i" && tag != "d" && tag != "c" && 
                tag != "error" && tag != "warn" && tag != "info" && tag != "debug" && tag != "cmd") {
                uniqueTags.add(tag)
            }
        }
        
        // 清空并重新添加TAG列表
        tagList.clear()
        tagList.add("全部") // 默认选项
        tagList.addAll(uniqueTags)
    }

    // 统一工具栏可见性控制方法，移除_toggleVisibility方法
    private fun toggleVisibility() {
        toolbarExpanded = !toolbarExpanded
        
        if (toolbarExpanded) {
            // 显示工具栏
            floatRootView?.visibility = View.VISIBLE
            
            // 更新日志区域可见性
            updateLogsVisibility()
        } else {
            // 隐藏工具栏
            floatRootView?.visibility = View.GONE
        }
    }

    // 简化updateToolbarVisibility方法，专注于更新UI状态
    private fun updateToolbarVisibility() {
        if (floatRootView == null) {
            initializeToolbar()
        }
        
        // 根据当前状态更新UI
        if (toolbarExpanded) {
            // 显示工具栏
            floatRootView?.visibility = View.VISIBLE
            commandInputBarView?.visibility = View.VISIBLE
            // 更新日志区域可见性
            updateLogsVisibility()
        } else {
            // 隐藏工具栏
            floatRootView?.visibility = View.GONE
        }
    }

    // 修改setVisibility方法，使用更新后的方法
    public fun setVisibility(visibility: Boolean) {
        toolbarExpanded = visibility
        updateToolbarVisibility()
    }

    // 修改showTouchMonitorView方法
    private fun showTouchMonitorView() {
        if (touchView != null) {
            touchView?.visibility = View.VISIBLE
            return
        }
        
        Timber.d("正在创建触摸监控视图...")
        
        val outMetrics = DisplayMetrics()
        windowManager.defaultDisplay.getMetrics(outMetrics)
        
        touchView = View(this).apply {
            setBackgroundColor(Color.TRANSPARENT)
            setOnTouchListener { v, event ->
                Timber.d("收到触摸事件: ${MotionEvent.actionToString(event.action)}")
                when (event.action) {
                    MotionEvent.ACTION_DOWN -> {
                        Timber.d("触摸坐标: (${event.rawX}, ${event.rawY})")
                        if (clickerEnabled) {
                            showClickPosition(event.rawX.toInt(), event.rawY.toInt())
                        }
                    }
                }
                false
            }
        }

        val params = WindowManager.LayoutParams(
            WindowManager.LayoutParams.MATCH_PARENT,
            WindowManager.LayoutParams.MATCH_PARENT,
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY
            } else {
                WindowManager.LayoutParams.TYPE_PHONE
            },
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or
                    WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN or
                    WindowManager.LayoutParams.FLAG_WATCH_OUTSIDE_TOUCH,  // 添加此flag
            PixelFormat.TRANSLUCENT
        )

        try {
            windowManager.addView(touchView, params)
            Timber.d("触摸监控视图已添加")
        } catch (e: Exception) {
            Timber.e(e, "添加触摸监控视图失败")
        }
    }

    // 添加隐藏触摸监控视图的方法
    private fun hideTouchMonitorView() {
        touchView?.let {
            try {
                windowManager.removeView(it)
                touchView = null
            } catch (e: Exception) {
                Timber.e(e, "移除触摸监控视图失败")
            }
        }
    }

    // 修改 enableTouchMonitor 方法，按需创建触摸监控视图
    public fun enableTouchMonitor(enable: Boolean) {
        if (enable) {
            if (touchView == null) {
                // 只有在需要时才创建触摸监控视图
                showTouchMonitorView()
            } else {
                touchView?.visibility = View.VISIBLE
            }
            log("触摸监控已启用")
        } else {
            // 如果已创建，则隐藏；如果未创建，则不做任何操作
            touchView?.visibility = View.GONE
            log("触摸监控已禁用")
        }
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
        setupSimpleFloatingButtonTouchListener()
    }

    /**
     * 设置简化版悬浮按钮触摸监听器 - 始终可拖动
     */
    private fun setupSimpleFloatingButtonTouchListener() {
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
                    true // 返回true表示继续接收后续事件
                }
                MotionEvent.ACTION_MOVE -> {
                    // 计算移动距离
                    val dx = event.rawX - initialTouchX
                    val dy = event.rawY - initialTouchY
                    
                    // 如果移动距离超过阈值，认为是拖动
                    if (!isDragging && (Math.abs(dx) > 5 || Math.abs(dy) > 5)) {
                        isDragging = true
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
                    if (!isDragging) {
                        // 如果不是拖动，则是点击，切换工具栏可见性
                        toggleVisibility()
                    }
                    true
                }
                else -> false
            }
        }
    }

    /**
     * 设置命令输入框可获取焦点
     */
    private fun makeInputFocusable() {
        if (floatRootView == null) return
        
        try {
            // 获取当前布局参数
            val params = (floatRootView?.layoutParams as? WindowManager.LayoutParams) ?: return
            
            // 移除不可获取焦点的标志
            params.flags = params.flags and WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE.inv()
            
            // 更新布局
            windowManager.updateViewLayout(floatRootView, params)
            
            // 获取命令输入框
            val commandInput = floatRootView?.findViewById<EditText>(R.id.commandInput)
            
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
        if (floatRootView == null) return
        
        try {
            // 获取当前布局参数
            val params = (floatRootView?.layoutParams as? WindowManager.LayoutParams) ?: return
            
            // 添加不可获取焦点的标志
            params.flags = params.flags or WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE
            
            // 更新布局
            windowManager.updateViewLayout(floatRootView, params)
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
     * @param visible true表示显示UI，false表示隐藏UI
     */
    fun setUIVisibility(visible: Boolean) {
        try {
            // 隐藏/显示悬浮按钮
            floatButtonView?.visibility = if (visible) View.VISIBLE else View.GONE
            
            // 隐藏/显示工具栏
            if (!visible) {
                // 如果需要隐藏，直接隐藏工具栏
                floatRootView?.visibility = View.GONE
            } else if (toolbarExpanded) {
                // 如果需要显示，且工具栏处于展开状态，则显示工具栏
                floatRootView?.visibility = View.VISIBLE
                // 更新日志区域可见性
                updateLogsVisibility()
            }
            
            // 隐藏/显示触摸监控视图
            touchView?.visibility = if (visible) View.VISIBLE else View.GONE
            
            // 隐藏/显示点击位置显示
            cursorView?.visibility = if (visible) View.VISIBLE else View.GONE
        } catch (e: Exception) {
            Timber.e(e, "设置UI可见性失败")
        }
    }

    private fun setupConsoleView() {
        try {
            // 初始化日志视图
            val logTextView = floatRootView?.findViewById<TextView>(R.id.logTextView)
            if (logTextView != null) {
                // 设置日志文本视图的属性
                logTextView.movementMethod = ScrollingMovementMethod.getInstance()
                
                // 缓存日志视图引用
                cachedLogTextView = WeakReference(logTextView)
                
                // 初始化TAG过滤下拉框
                val tagFilterSpinner = floatRootView?.findViewById<Spinner>(R.id.tagFilterSpinner)
                if (tagFilterSpinner != null) {
                    // 创建适配器
                    val adapter = ArrayAdapter<String>(
                        this,
                        android.R.layout.simple_spinner_item,
                        mutableListOf("全部", "System", "cmd")
                    )
                    adapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item)
                    tagFilterSpinner.adapter = adapter
                    
                    // 设置选择监听器
                    tagFilterSpinner.onItemSelectedListener = object : AdapterView.OnItemSelectedListener {
                        override fun onItemSelected(parent: AdapterView<*>?, view: View?, position: Int, id: Long) {
                            val selectedTag = parent?.getItemAtPosition(position) as String
                            if (selectedTag == "全部") {
                                // 显示所有日志
                                filterLogs("", logTextView)
                            } else {
                                // 按TAG过滤
                                filterLogs("[$selectedTag]", logTextView)
                            }
                        }
                        
                        override fun onNothingSelected(parent: AdapterView<*>?) {
                            // 不做任何处理
                        }
                    }
                }
            }
            
            // 初始化命令输入框
            val commandInput = commandInputBarView?.findViewById<EditText>(R.id.commandInput)
            if (commandInput != null) {
                // 设置命令输入框的属性
                commandInput.setOnEditorActionListener { v, actionId, event ->
                    if (actionId == EditorInfo.IME_ACTION_SEND || 
                        (event != null && event.keyCode == KeyEvent.KEYCODE_ENTER && event.action == KeyEvent.ACTION_DOWN)) {
                        sendCommand(commandInput, logTextView)
                        true
                    } else {
                        false
                    }
                }
            }
            
            log("控制台视图初始化完成", "System", "i")
        } catch (e: Exception) {
            Timber.e(e, "初始化控制台视图失败")
        }
    }

    // 添加更新TAG列表的方法
    fun updateTagList(newTag: String) {
        // 获取TAG过滤下拉框
        val tagFilterSpinner = floatRootView?.findViewById<Spinner>(R.id.tagFilterSpinner) ?: return
        
        // 获取当前适配器
        val adapter = tagFilterSpinner.adapter as? ArrayAdapter<String> ?: return
        
        // 检查TAG是否已存在
        for (i in 0 until adapter.count) {
            if (adapter.getItem(i) == newTag) {
                return // TAG已存在，不需要添加
            }
        }
        
        // 添加新TAG
        adapter.add(newTag)
        adapter.notifyDataSetChanged()
    }

    // 修改executeCommand方法，添加空值检查
    private fun executeCommand(command: String, logTextView: TextView?) {
        CoroutineScope(Dispatchers.IO).launch {
            try {
                // 检查脚本引擎是否已初始化
                if (isRunning) {
                    log("脚本引擎未初始化或未运行，无法执行命令", "", "e")
                    return@launch
                }
                PythonServices.doCommand(command)
            } catch (e: Exception) {
                logEx(e, "执行失败: ${e.message}", "", "")
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
                scriptEngine.syncFiles(serverIP)
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
        if (floatRootView == null) return
        
        try {
            // 获取当前布局参数
            val params = (floatRootView?.layoutParams as? WindowManager.LayoutParams) ?: return
            
            // 无论日志是否展开，都保持底部对齐
            params.gravity = Gravity.BOTTOM or Gravity.CENTER_HORIZONTAL
            
            // 根据日志展开状态调整高度
            if (logsExpanded) {
                // 日志展开时，使用MATCH_PARENT高度
                params.height = WindowManager.LayoutParams.MATCH_PARENT
            } else {
                // 日志收起时，使用WRAP_CONTENT高度
                params.height = WindowManager.LayoutParams.WRAP_CONTENT
            }
            
            // 更新布局
            windowManager.updateViewLayout(floatRootView, params)
        } catch (e: Exception) {
            Timber.e(e, "更新窗口位置失败")
        }
    }

}