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
import androidx.appcompat.app.AlertDialog
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
import android.view.ContextThemeWrapper
import cn.vove7.andro_accessibility_api.demo.MainActivity
import android.view.inputmethod.EditorInfo

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
    }

    private lateinit var windowManager: WindowManager
    private var floatRootView: View? = null // 悬浮窗View
    private lateinit var prefs: SharedPreferences

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
        Log.d("ToolBarService", "Service created")
        showWindow()
        if (serverIP.isEmpty() || deviceName.isEmpty()) {
            showSetting()
        }
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

    private fun setupButtons(layoutParam: WindowManager.LayoutParams) {
        val toggleButton = floatRootView?.findViewById<Button>(R.id.toggleButton)
        val startStopButton = floatRootView?.findViewById<Button>(R.id.startStopButton)
        val settingsButton = floatRootView?.findViewById<Button>(R.id.settingsButton)

        toggleButton?.setOnClickListener {
            toggleVisibility(startStopButton, settingsButton)
        }

        val touchListener = createTouchListener(layoutParam)
        listOf(startStopButton, settingsButton, toggleButton).forEach { button ->
            button?.setOnTouchListener(touchListener)
        }

        startStopButton?.setOnClickListener { onStartStopButtonClick() }
        settingsButton?.setOnClickListener { showSetting() }
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

    private fun createTouchListener(layoutParam: WindowManager.LayoutParams): View.OnTouchListener {
        return object : View.OnTouchListener {
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
                        return true
                    }
                    MotionEvent.ACTION_MOVE -> {
                        layoutParam.x = initialX + (event.rawX - initialTouchX).toInt()
                        layoutParam.y = initialY + (event.rawY - initialTouchY).toInt()
                        Log.d("ToolBarService", "layoutParam.x: ${layoutParam.x}, layoutParam.y: ${layoutParam.y}")
                        windowManager.updateViewLayout(floatRootView, layoutParam)
                        return true
                    }
                    MotionEvent.ACTION_UP -> {
                        val deltaX = (event.rawX - initialTouchX).toInt()
                        val deltaY = (event.rawY - initialTouchY).toInt()
                        if (Math.abs(deltaX) < clickThreshold && Math.abs(deltaY) < clickThreshold) {
                            v.performClick()
                        }
                        return true
                    }
                }
                return false
            }
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

    override fun onDestroy() {
        if(isRunning){
            end()
        }
        hideWindow() // 销毁服务时隐藏悬浮窗口
        super.onDestroy()
    }
}