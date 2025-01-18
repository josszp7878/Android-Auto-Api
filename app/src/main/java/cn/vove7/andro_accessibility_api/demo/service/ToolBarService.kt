package cn.vove7.andro_accessibility_api.demo.service

import android.annotation.SuppressLint
import android.content.Context
import android.graphics.PixelFormat
import android.os.Build
import android.util.DisplayMetrics
import android.util.Log
import android.view.Gravity
import android.view.LayoutInflater
import android.view.MotionEvent
import android.view.View
import android.view.ViewGroup.LayoutParams.WRAP_CONTENT
import android.view.WindowManager
import android.widget.Button
import androidx.lifecycle.LifecycleService
import cn.vove7.andro_accessibility_api.demo.R
import cn.vove7.andro_accessibility_api.demo.databinding.DialogDeviceInfoBinding
import cn.vove7.andro_accessibility_api.demo.script.ScriptEngine
import android.content.SharedPreferences
import android.widget.Toast
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import cn.vove7.andro_accessibility_api.demo.MainActivity
import android.view.inputmethod.EditorInfo
import cn.vove7.andro_accessibility_api.demo.view.CursorView
import java.lang.ref.WeakReference
import android.os.Handler
import android.os.Looper
import timber.log.Timber

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
                _serverIP = getPrefs().getString(SERVER_NAME_KEY, "192.168.31.217")
            }
            return _serverIP!!
        }
        set(value) {
            _serverIP = value
            getPrefs().edit().putString(SERVER_NAME_KEY, value).apply()
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
            _deviceName = value
            getPrefs().edit().putString(DEVICE_NAME_KEY, value).apply()
        }

    private fun getPrefs(): SharedPreferences {
        if (!::prefs.isInitialized) {
            prefs = getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        }
        return prefs
    }

    override fun onCreate() {
        super.onCreate()
        instance = WeakReference(this) // 设置实例
        Log.d("ToolBarService", "Service created")
        showWindow()
        if (serverIP.isEmpty() || deviceName.isEmpty()) {
            showSetting()
        }
        addCursorView() // 添加光标视图
    }

    /**
     * 显示悬浮窗
     */
    @SuppressLint("ClickableViewAccessibility")
    fun showWindow() {
        if (floatRootView != null) return

        windowManager = getSystemService(WINDOW_SERVICE) as WindowManager
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
        
        toggleButton?.setOnClickListener {
            toggleVisibility(startStopButton, settingsButton)
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
    }

    private fun toggleVisibility(vararg buttons: Button?) {
        val isVisible = buttons.first()?.visibility == View.VISIBLE
        val targetAlpha = if (isVisible) 0f else 1f
        buttons.forEach { button ->
            button?.animate()?.alpha(targetAlpha)?.setDuration(300)?.withEndAction {
                button.visibility = if (isVisible) View.GONE else View.VISIBLE
            }?.start()
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
            windowManager.removeView(dialogView) // 移除悬浮窗口
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
        hideWindow() // 销毁服务时隐藏悬浮窗口
        super.onDestroy()
        cursorView?.let { windowManager.removeView(it) }
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

}