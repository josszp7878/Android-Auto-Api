package cn.vove7.andro_accessibility_api.demo.service

import android.annotation.SuppressLint
import android.content.Context
import android.content.SharedPreferences
import android.graphics.PixelFormat
import android.os.Build
import android.os.Handler
import android.os.Looper
import android.util.DisplayMetrics
import android.util.Log
import android.view.GestureDetector
import android.view.GestureDetector.SimpleOnGestureListener
import android.view.Gravity
import android.view.LayoutInflater
import android.view.MotionEvent
import android.view.View
import android.view.ViewGroup.LayoutParams.WRAP_CONTENT
import android.view.WindowManager
import android.view.inputmethod.EditorInfo
import android.widget.Button
import android.widget.FrameLayout
import android.widget.LinearLayout
import android.widget.TextView
import android.widget.Toast
import androidx.lifecycle.LifecycleService
import cn.vove7.andro_accessibility_api.demo.MainActivity
import cn.vove7.andro_accessibility_api.demo.R
import cn.vove7.andro_accessibility_api.demo.databinding.DialogDeviceInfoBinding
import cn.vove7.andro_accessibility_api.demo.script.ScriptEngine
import cn.vove7.andro_accessibility_api.demo.utils.UIUtils
import cn.vove7.andro_accessibility_api.demo.view.CursorView
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import timber.log.Timber
import java.lang.ref.WeakReference
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

        @JvmStatic
        fun getInstance(): WeakReference<ToolBarService>? {
            return instance
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

    private var isToolbarExpanded = false

    // 添加自定义悬浮窗相关变量
    private var positionToastView: View? = null
    private var positionToastHideRunnable: Runnable? = null
    private var lastPositionToastUpdateTime = 0L
    private val POSITION_TOAST_AUTO_HIDE_DELAY = 5000L // 5秒后自动隐藏

    override fun onCreate() {
        super.onCreate()
        instance = WeakReference(this)
        
        // 初始化手势检测器
        gestureDetector = GestureDetector(this, object : SimpleOnGestureListener() {
            override fun onSingleTapUp(e: MotionEvent): Boolean {
                val x = e.rawX.toInt()
                val y = e.rawY.toInt()
                
                // 显示点击坐标
                showClickPosition(x, y)
                
                return false // 不消费事件，确保事件继续传递
            }
        })
        
        Log.d("ToolBarService", "Service created")
        
        // 初始化windowManager
        windowManager = getSystemService(WINDOW_SERVICE) as WindowManager
        
        // 先添加触摸监控覆盖层，确保它在z-index较低的位置
        // 初始时不启用，等ToolBar展开时再启用
        
        // 显示ToolBar
        showWindow()
        if (serverIP.isEmpty() || deviceName.isEmpty()) {
            showSetting()
        }
        addCursorView()
    }

    /**
     * 显示悬浮窗
     */
    @SuppressLint("ClickableViewAccessibility")
    fun showWindow() {
        if (floatRootView != null) return

        val outMetrics = DisplayMetrics()
        windowManager.defaultDisplay.getMetrics(outMetrics)
        val layoutParam = createLayoutParams(outMetrics)

        floatRootView = LayoutInflater.from(this).inflate(R.layout.floating_toolbar, null)
        setupButtons(layoutParam)

        // 确保按钮在 CursorView 之上
        layoutParam.type = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY
        } else {
            WindowManager.LayoutParams.TYPE_PHONE
        }
        layoutParam.flags = WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or WindowManager.LayoutParams.FLAG_NOT_TOUCH_MODAL
        layoutParam.format = PixelFormat.TRANSLUCENT

        windowManager.addView(floatRootView, layoutParam)
        
        // 延迟初始化，确保UI元素已经正确加载
        Handler(Looper.getMainLooper()).postDelayed({
            val expandedButtons = floatRootView?.findViewById<LinearLayout>(R.id.expandedButtons)
            expandedButtons?.visibility = View.GONE
            Log.d("ToolBarService", "Initial setup of expandedButtons: GONE")
        }, 100)
    }

    private fun createLayoutParams(outMetrics: DisplayMetrics): WindowManager.LayoutParams {
        return WindowManager.LayoutParams().apply {
            type = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY
            } else {
                WindowManager.LayoutParams.TYPE_PHONE
            }
            format = PixelFormat.RGBA_8888
            flags = WindowManager.LayoutParams.FLAG_NOT_TOUCH_MODAL or WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE
            width = WRAP_CONTENT
            height = WRAP_CONTENT
            gravity = Gravity.TOP or Gravity.END
            x = 0
            y = outMetrics.heightPixels / 2 - height / 2
        }
    }

    @SuppressLint("ClickableViewAccessibility")
    private fun setupButtons(layoutParam: WindowManager.LayoutParams) {
        val toggleButton = floatRootView?.findViewById<Button>(R.id.toggleButton)
        val startStopButton = floatRootView?.findViewById<Button>(R.id.startStopButton)
        val settingsButton = floatRootView?.findViewById<Button>(R.id.settingsButton)
        val syncButton = floatRootView?.findViewById<Button>(R.id.syncButton)
        val expandedButtons = floatRootView?.findViewById<LinearLayout>(R.id.expandedButtons)
        
        toggleButton?.setOnClickListener(null) // 清除之前的点击监听器
        toggleButton?.setOnClickListener {
            val expandedButtons = floatRootView?.findViewById<LinearLayout>(R.id.expandedButtons)
            if (expandedButtons != null) {
                val newVisibility = if (expandedButtons.visibility == View.VISIBLE) View.GONE else View.VISIBLE
                expandedButtons.visibility = newVisibility
            } else {
                Log.e("ToolBarService", "expandedButtons is null")
            }
        }

        val touchListener = object : View.OnTouchListener {
            private var initialX = 0
            private var initialY = 0
            private var initialTouchX = 0f
            private var initialTouchY = 0f
            private val clickThreshold = 10

            override fun onTouch(v: View, event: MotionEvent): Boolean {
                when (event.action) {
                    MotionEvent.ACTION_DOWN -> {
                        initialX = layoutParam.x
                        initialY = layoutParam.y
                        initialTouchX = event.rawX
                        initialTouchY = event.rawY
                        moveCursor(event.rawX.toInt(), event.rawY.toInt(),true)
                        return true
                    }
                    MotionEvent.ACTION_MOVE -> {
                        val deltaX = (event.rawX - initialTouchX).toInt()
                        val deltaY = (event.rawY - initialTouchY).toInt()
                        
                        // X轴偏移取反，因为是END对齐
                        layoutParam.x = initialX - deltaX
                        layoutParam.y = initialY + deltaY
                        
                        Log.d("ToolBarService", "deltaX: ${-deltaX}, deltaY: $deltaY")
                        try {
                            windowManager.updateViewLayout(floatRootView, layoutParam)
                            moveCursor(event.rawX.toInt(), event.rawY.toInt(), true)
                        } catch (e: Exception) {
                            Log.e("ToolBarService", "Failed to update toolbar position", e)
                        }
                        return true
                    }
                    MotionEvent.ACTION_UP -> {
                        val deltaX = Math.abs(event.rawX - initialTouchX)
                        val deltaY = Math.abs(event.rawY - initialTouchY)
                        if (deltaX < clickThreshold && deltaY < clickThreshold) {
                            v.performClick()
                        }
                        return true
                    }
                }
                return false
            }
        }

        listOf(startStopButton, settingsButton, toggleButton).forEach { button ->
            button?.setOnTouchListener(touchListener)
        }

        startStopButton?.setOnClickListener {
            onStartStopButtonClick()
            flashCursor() // 闪烁光标
        }
        settingsButton?.setOnClickListener {
            showSetting()
            flashCursor() // 闪烁光标
        }

        syncButton?.setOnClickListener {
            if (serverIP.isEmpty()) {
                Toast.makeText(this, "请先设置服务器IP", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
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
    }

    // 添加一个辅助方法来切换可见性
    private fun toggleVisibility(vararg views: View?) {
        val expandedButtons = floatRootView?.findViewById<LinearLayout>(R.id.expandedButtons)
        if (expandedButtons == null) {
            Log.e("ToolBarService", "expandedButtons is null in toggleVisibility")
            return
        }
        
        // 切换可见性
        if (expandedButtons.visibility == View.VISIBLE) {
            expandedButtons.visibility = View.GONE
            Log.d("ToolBarService", "Hiding expanded buttons (from toggleVisibility)")
        } else {
            expandedButtons.visibility = View.VISIBLE
            Log.d("ToolBarService", "Showing expanded buttons (from toggleVisibility)")
        }
    }

    /**
     * 隐藏悬浮窗
     */
    fun hideWindow() {
        if (floatRootView != null) {
            windowManager.removeView(floatRootView)
            floatRootView = null
        }
    }

    private var _isRunning = false
    var isRunning: Boolean
        get() = _isRunning
        set(value) {
            _isRunning = value
            updateButtonIcon() // 在设置 isRunning 时更新按钮图标
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
        isRunning = if (isRunning) {
            end()
            false
        } else {
            begin()
            true
        }
    }

    private fun updateButtonIcon() {
        val startStopButton = floatRootView?.findViewById<Button>(R.id.startStopButton)
        if (isRunning) {
            startStopButton?.setBackgroundResource(android.R.drawable.ic_media_pause) // 停止图标
        } else {
            startStopButton?.setBackgroundResource(android.R.drawable.ic_media_play) // 开始图标
        }
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

    private fun begin(): Boolean {
        if (isRunning) {
            Toast.makeText(this, "脚本引擎已启动", Toast.LENGTH_SHORT).show()
            return false
        }
        if (serverIP.isEmpty() || deviceName.isEmpty()) {
            Toast.makeText(this, "请先设置设备名和服务器名", Toast.LENGTH_SHORT).show()
            return false
        }
        CoroutineScope(Dispatchers.IO).launch {
            try {
                scriptEngine.init(deviceName, serverIP)
                withContext(Dispatchers.Main) {
                    Toast.makeText(this@ToolBarService, "脚本引擎已启动", Toast.LENGTH_SHORT).show()
                    isRunning = true
                    MainActivity.getInstance()?.moveTaskToBack(true)
                }
            } catch (e: Exception) {
                withContext(Dispatchers.Main) {
                    Toast.makeText(this@ToolBarService, "脚本引擎启动失败: ${e.message}", Toast.LENGTH_SHORT).show()
                }
            }
        }
        return true
    }

    private fun end() {
        if (!isRunning) {
            return
        }
        scriptEngine.uninit()
        isRunning = false
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
        if(isRunning){
            end()
        }
        hideWindow()
        super.onDestroy()
        cursorView?.let { windowManager.removeView(it) }
        removeTouchMonitorView()
        hidePositionToast() // 隐藏点击坐标悬浮窗
        executor.shutdown()
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
                windowManager.addView(floatRootView, createLayoutParams(outMetrics))
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
        // 确保在主线程上执行UI操作
        Handler(Looper.getMainLooper()).post {
            if(enable) {
                addTouchMonitorOverlay()
            } else {
                removeTouchMonitorView()
            }
        }
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

}